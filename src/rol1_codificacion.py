"""
Rol 1 — El Codificador: representación del cromosoma.

Un individuo del AG es un vector x de N_GENES floats en [0, 1]. El AG (Roles 3 y 4)
solo mezcla y muta esos números; nunca ve valores físicos. La traducción
[0, 1] <-> valores físicos (segundos, Hz, amplitudes) se hace SOLO aquí:

    decodificar(x)      : [0, 1]  -> dict físico   (lo usa el Rol 2 para sintetizar)
    codificar(params)   : dict físico -> [0, 1]    (su inversa exacta)

Contenido
---------
GENES        : tabla de genes (nombre, mín, máx, unidad), en el orden del cromosoma
ESCALA_LOG   : genes que se mapean en escala logarítmica (los tiempos del ADSR)
codificar, decodificar
extraer_notas: silbido .wav -> (notas MIDI, duraciones en s)
"""
from __future__ import annotations

import numpy as np

# ------------------------------------------------------------ tabla de genes
# (nombre, mínimo, máximo, unidad). El orden de esta lista ES el orden de los
# genes dentro del vector x: x[0] = amp_h1, x[1] = amp_h2, ..., x[13] = vib_prof.
GENES = (
    # Timbre: amplitud relativa de los 8 primeros armónicos (h·f0).
    [(f"amp_h{h}", 0.0, 1.0, "lineal") for h in range(1, 9)]
    # Envolvente ADSR: cómo nace, cae, se sostiene y se apaga cada nota.
    + [("ataque", 0.005, 0.30, "s"),
       ("decaimiento", 0.02, 1.0, "s"),
       ("sostenido", 0.0, 1.0, "lineal"),
       ("liberacion", 0.02, 0.5, "s"),
       # Vibrato: oscilación periódica de la frecuencia.
       ("vib_frec", 0.0, 8.0, "Hz"),
       ("vib_prof", 0.0, 0.02, "fracción f0")]
)
N_GENES = len(GENES)
NOMBRES = [g[0] for g in GENES]

# Genes de tiempo: el oído percibe cambios RELATIVOS (5 -> 10 ms se nota mucho,
# 300 -> 305 ms nada), así que el gen recorre el rango de forma geométrica.
# Requiere mín > 0 (log(0) no existe), por eso los rangos de tiempo no parten de 0.
ESCALA_LOG = {"ataque", "decaimiento", "liberacion"}


# ------------------------------------------------- codificar / decodificar
def decodificar(x: np.ndarray) -> dict:
    """[0, 1]^N_GENES -> dict {nombre_gen: valor físico}.

    Lineal:      valor = mín + x·(máx − mín)
    Logarítmica: valor = mín · (máx/mín)^x     (x=0 -> mín, x=1 -> máx)
    """
    x = np.clip(np.asarray(x, dtype=float), 0.0, 1.0)
    if x.shape != (N_GENES,):
        raise ValueError(f"se esperaban {N_GENES} genes, llegó un vector de forma {x.shape}")
    params = {}
    for (nombre, lo, hi, _), v in zip(GENES, x):
        if nombre in ESCALA_LOG:
            params[nombre] = float(lo * (hi / lo) ** v)
        else:
            params[nombre] = float(lo + v * (hi - lo))
    return params


def codificar(params: dict) -> np.ndarray:
    """dict físico -> vector en [0, 1]. Inversa exacta de decodificar.

    Lineal:      x = (valor − mín) / (máx − mín)
    Logarítmica: x = log(valor/mín) / log(máx/mín)
    """
    x = np.empty(N_GENES)
    for i, (nombre, lo, hi, _) in enumerate(GENES):
        v = float(np.clip(params[nombre], lo, hi))
        if nombre in ESCALA_LOG:
            x[i] = np.log(v / lo) / np.log(hi / lo)
        else:
            x[i] = (v - lo) / (hi - lo)
    return x


# ------------------------------------------------------- extracción de notas
SR = 22050
HOP = 256                 # salto entre frames: 256/22050 ≈ 11.6 ms de resolución
FRAME = 2048              # ventana de análisis ≈ 93 ms (≥ 2 periodos de 500 Hz)
FMIN, FMAX = 500.0, 3000.0  # rango típico de un silbido humano
UMBRAL_CONFIANZA = 0.5    # prob. mínima de pyin para aceptar un frame como nota
DUR_MIN = 0.08            # notas más cortas que 80 ms se consideran temblor/ruido
FILTRO_MEDIANA = 21       # frames (≈ 0.24 s): borra temblores de afinación más
                          # cortos que ~0.12 s; una nota silbada dura 0.3–0.6 s


def _tramos_con_voz(voz):
    """Lista de (inicio, fin) de cada tramo continuo de frames con voz."""
    tramos, i, n = [], 0, len(voz)
    while i < n:
        if voz[i]:
            j = i
            while j < n and voz[j]:
                j += 1
            tramos.append((i, j))
            i = j
        else:
            i += 1
    return tramos


def _suavizar(midi_cont, voz, ventana):
    """Filtro de mediana SOLO dentro de cada tramo con voz, para no mezclar el
    tono con los silencios (así los silencios cortos entre notas repetidas
    —p. ej. Sol-Sol— se conservan y las notas no se fusionan)."""
    import scipy.signal
    out = midi_cont.copy()
    for ini, fin in _tramos_con_voz(voz):
        k = min(ventana, fin - ini if (fin - ini) % 2 else fin - ini - 1)  # impar y <= largo
        if k >= 3:
            out[ini:fin] = scipy.signal.medfilt(midi_cont[ini:fin], k)
    return out


def _segmentos(midi, voz):
    """Agrupa frames consecutivos con la misma nota. Devuelve una lista de
    [nota, frame_inicio, frame_fin) solo para tramos con voz."""
    segs, i, n = [], 0, len(midi)
    while i < n:
        if not voz[i]:
            i += 1
            continue
        j = i
        while j < n and voz[j] and midi[j] == midi[i]:
            j += 1
        segs.append([int(midi[i]), i, j])
        i = j
    return segs


def _limpiar(segs, min_frames):
    """Absorbe los segmentos cortos (< min_frames) en un vecino PEGADO a él
    (sin silencio de por medio); si está aislado entre silencios, se descarta.
    Luego une segmentos pegados que quedaron con la misma nota."""
    cambio = True
    while cambio:
        cambio = False
        for k, (nota, ini, fin) in enumerate(segs):
            if fin - ini >= min_frames:
                continue
            pegado_ant = k > 0 and segs[k - 1][2] == ini
            pegado_sig = k + 1 < len(segs) and segs[k + 1][1] == fin
            if pegado_ant and (not pegado_sig or
                               segs[k - 1][2] - segs[k - 1][1] >= segs[k + 1][2] - segs[k + 1][1]):
                segs[k - 1][2] = fin          # lo absorbe la nota anterior (la más larga)
            elif pegado_sig:
                segs[k + 1][1] = ini          # lo absorbe la nota siguiente
            del segs[k]                       # aislado o ya absorbido
            cambio = True
            break
        # une vecinos pegados con la misma nota (p. ej. 89 | 88 corto | 89)
        k = 0
        while k + 1 < len(segs):
            if segs[k][0] == segs[k + 1][0] and segs[k][2] == segs[k + 1][1]:
                segs[k][2] = segs[k + 1][2]
                del segs[k + 1]
                cambio = True
            else:
                k += 1
    return segs


def extraer_notas(ruta_wav):
    """Silbido .wav -> (notas_midi: list[int], duraciones_s: list[float]).

    1. Carga mono a 22050 Hz.
    2. pyin (fmin 500, fmax 3000): f0 por frame + probabilidad de que haya nota.
    3. Se aceptan solo frames con voz y probabilidad >= UMBRAL_CONFIANZA (quita ruido).
    4. Corrección de afinación: se resta el desvío medio del silbido respecto a
       la afinación estándar (La = 440 Hz) para que las notas no caigan entre
       dos semitonos.
    5. f0 -> MIDI: midi = 69 + 12·log2(f0/440), filtro de mediana (por tramo
       con voz) para borrar temblores, y redondeo al semitono más cercano.
    6. Se agrupan frames consecutivos con la misma nota y los tramos < 80 ms
       se absorben en la nota vecina o se descartan si están aislados.
    """
    import librosa

    y, sr = librosa.load(ruta_wav, sr=SR, mono=True)
    f0, voz, prob = librosa.pyin(y, fmin=FMIN, fmax=FMAX, sr=sr,
                                 frame_length=FRAME, hop_length=HOP)
    voz = voz & (prob >= UMBRAL_CONFIANZA) & np.isfinite(f0)
    if not voz.any():
        return [], []

    midi_cont = np.full(len(f0), np.nan)
    midi_cont[voz] = librosa.hz_to_midi(f0[voz])       # MIDI con decimales: 69 + 12·log2(f0/440)
    afinacion = librosa.pitch_tuning(midi_cont[voz])   # desvío medio, en fracción de semitono
    midi_cont = _suavizar(midi_cont - afinacion, voz, FILTRO_MEDIANA)
    midi = np.where(voz, np.round(midi_cont), -1).astype(int)

    min_frames = int(np.ceil(DUR_MIN * sr / HOP))
    segs = _limpiar(_segmentos(midi, voz), min_frames)
    notas = [nota for nota, _, _ in segs]
    duraciones = [round((fin - ini) * HOP / sr, 3) for _, ini, fin in segs]
    return notas, duraciones