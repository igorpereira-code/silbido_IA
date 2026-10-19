"""
PROVISIONAL: versiones mínimas de las piezas de los Roles 1, 2 y 4, solo para que
Rol 3 y Rol 5 puedan probar su código desde el Día 1 sin esperar a nadie.

>>> Cada rol reemplaza esto por su módulo real (rol1_codificacion.py,
>>> rol2_fitness.py, rol4_ag.py) respetando LAS MISMAS FIRMAS.
>>> El notebook final NO debe importar este archivo.
"""
from __future__ import annotations

import numpy as np
from scipy.signal import stft

from . import rol3_operadores as op

SR = 22050

# ------------------------------------------------ Rol 1 (provisional)
GENES = (
    [(f"amp_h{h}", 0.0, 1.0, "lineal") for h in range(1, 9)]
    + [("ataque", 0.005, 0.30, "s"), ("decaimiento", 0.02, 1.0, "s"),
       ("sostenido", 0.0, 1.0, "lineal"), ("liberacion", 0.02, 0.5, "s"),
       ("vib_frec", 0.0, 8.0, "Hz"), ("vib_prof", 0.0, 0.02, "fracción f0")]
)
N_GENES = len(GENES)


def decodificar(x):
    return {n: lo + v * (hi - lo) for (n, lo, hi, _), v in zip(GENES, x)}


def codificar(params):
    return np.array([(params[n] - lo) / (hi - lo) for n, lo, hi, _ in GENES])


def crear_silbido_prueba(ruta, sr=SR):
    """Silbido sintético (sinusoide pura + algo de ruido) con 'Do Re Mi Fa Sol'
    en la octava del silbido. Solo para probar mientras no haya grabación real."""
    import soundfile as sf
    rng = np.random.default_rng(0)
    notas, durs = [84, 86, 88, 89, 91, 91], [0.35, 0.35, 0.35, 0.35, 0.5, 0.5]
    partes = []
    for m, d in zip(notas, durs):
        t = np.arange(int(d * sr)) / sr
        f = 440 * 2 ** ((m - 69) / 12)
        env = np.minimum(1, np.minimum(t, d - t) / 0.03)
        partes.append(0.5 * env * np.sin(2 * np.pi * f * t) + 0.01 * rng.normal(size=t.size))
    sf.write(ruta, np.concatenate(partes), sr, subtype="PCM_16")
    return notas, durs


def extraer_notas(ruta):
    """Pitch muy simple: pico de FFT por ventana de 46 ms -> MIDI, y se agrupan
    ventanas consecutivas con la misma nota. (El Rol 1 usa librosa.pyin.)"""
    import soundfile as sf
    y, sr = sf.read(ruta)
    hop, win = 512, 1024
    midis = []
    for i in range(0, len(y) - win, hop):
        w = y[i:i + win] * np.hanning(win)
        if np.sqrt(np.mean(w ** 2)) < 0.02:
            midis.append(None); continue
        esp = np.abs(np.fft.rfft(w, 4 * win))
        f = np.argmax(esp) * sr / (4 * win)
        midis.append(int(round(69 + 12 * np.log2(f / 440))))
    notas, durs = [], []
    for m in midis:
        if m is not None and notas and notas[-1] == m and durs[-1] is not None:
            durs[-1] += hop / sr
        elif m is not None:
            notas.append(m); durs.append(hop / sr)
    # fusiona notas espurias muy cortas
    filtradas = [(n, d) for n, d in zip(notas, durs) if d >= 0.08]
    return [n for n, _ in filtradas], [d for _, d in filtradas]


# ------------------------------------------------ Rol 2 (provisional)
def _adsr(n, g, sr=SR):
    a, d, r = (int(g[k] * sr) for k in ("ataque", "decaimiento", "liberacion"))
    s = g["sostenido"]
    env = np.full(n, s)
    a = max(1, min(a, n)); env[:a] = np.linspace(0, 1, a)
    d = min(d, n - a)
    if d > 0:
        env[a:a + d] = np.linspace(1, s, d)
    r = min(r, n)
    env[n - r:] *= np.linspace(1, 0, r)
    return env


def sintetizar_instrumento(notas, duraciones, gen, sr=SR):
    """Síntesis aditiva: 8 armónicos + ADSR + vibrato. gen = dict físico."""
    salida = []
    for midi, dur in zip(notas, duraciones):
        n = int(dur * sr)
        t = np.arange(n) / sr
        f0 = 440.0 * 2 ** ((midi - 69) / 12)
        vib = 1 + gen["vib_prof"] * np.sin(2 * np.pi * gen["vib_frec"] * t)
        fase = 2 * np.pi * np.cumsum(f0 * vib) / sr
        y = sum(gen[f"amp_h{h}"] * np.sin(h * fase) for h in range(1, 9)
                if h * f0 < sr / 2)
        y = y * _adsr(n, gen, sr)
        salida.append(y)
    y = np.concatenate(salida)
    m = np.max(np.abs(y))
    return y / m if m > 0 else y


def _espectro_db(y):
    _, _, Z = stft(y, fs=SR, nperseg=1024, noverlap=768)
    db = 20 * np.log10(np.abs(Z) + 1e-10)
    return np.maximum(db - db.max(), -80.0)


GEN_REFERENCIA = {  # "piano" sintético con genes conocidos (para validar)
    **{f"amp_h{h}": a for h, a in zip(range(1, 9), [1, .55, .35, .25, .12, .08, .05, .02])},
    "ataque": 0.008, "decaimiento": 0.45, "sostenido": 0.15, "liberacion": 0.25,
    "vib_frec": 0.0, "vib_prof": 0.0,
}
NOTA_PRUEBA = ([69], [0.8])
REF_DB = _espectro_db(sintetizar_instrumento(*NOTA_PRUEBA, GEN_REFERENCIA))


def fitness(x, ref_db=REF_DB):
    """1 - error medio absoluto en dB / 80  -> rango [0, 1], mayor = mejor."""
    db = _espectro_db(sintetizar_instrumento(*NOTA_PRUEBA, decodificar(x)))
    return float(1.0 - np.mean(np.abs(db - ref_db)) / 80.0)


# ------------------------------------------------ Rol 4 (provisional)
def ejecutar_ag(config, fitness_fn, seed):
    """Ciclo generacional mínimo con elitismo. Firma acordada con el Rol 4."""
    rng = np.random.default_rng(seed)
    n, d, T = config["poblacion"], config["n_genes"], config["generaciones"]
    elite = config.get("elitismo", 2)
    pob = rng.random((n, d))
    fit = np.array([fitness_fn(x) for x in pob])
    hist = {"max": [], "media": [], "std": [], "diversidad": [], "evaluaciones": []}
    evals = n
    mejor_gen0 = pob[np.argmax(fit)].copy()
    for t in range(T):
        hist["max"].append(fit.max()); hist["media"].append(fit.mean())
        hist["std"].append(fit.std()); hist["diversidad"].append(op.diversidad(pob))
        hist["evaluaciones"].append(evals)
        orden = np.argsort(fit)[::-1]
        hijos = op.reproducir(pob, fit, config.get("operadores"), t, T, rng,
                              n_hijos=n - elite)
        fit_h = np.array([fitness_fn(x) for x in hijos])
        evals += len(hijos)
        pob = np.vstack([pob[orden[:elite]], hijos])
        fit = np.concatenate([fit[orden[:elite]], fit_h])
    for k, v in (("max", fit.max()), ("media", fit.mean()), ("std", fit.std()),
                 ("diversidad", op.diversidad(pob)), ("evaluaciones", evals)):
        hist[k].append(v)
    i = int(np.argmax(fit))
    return {"mejor": pob[i].copy(), "mejor_fit": float(fit[i]),
            "mejor_gen0": mejor_gen0, "historial": hist}
