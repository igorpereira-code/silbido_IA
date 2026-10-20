"""Rol 2: síntesis aditiva y evaluación de una nota de piano (La4, MIDI 69).

La referencia y sus características se calculan una vez al importar. El fitness
principal compara STFT en dB en bandas activas; el secundario compara croma.
No se usa MSE de la onda: penalizaría cambios de fase que apenas se oyen.
"""
from pathlib import Path
from importlib import import_module
import warnings

import numpy as np
import soundfile as sf
from scipy.signal import stft

try:
    rol1 = import_module(".rol1_codificacion", __package__)
except ModuleNotFoundError as exc:
    if exc.name != f"{__package__}.rol1_codificacion":
        raise
    from . import _provisional as rol1
    warnings.warn("Rol 2: se usa la codificación provisional hasta integrar Rol 1.",
                  RuntimeWarning, stacklevel=2)

SR = 22050
NOTA_REFERENCIA = 69
RUTA_REFERENCIA = Path(__file__).resolve().parents[1] / "data" / "referencia.wav"


def _adsr(n, gen, sr):
    """ADSR dentro de la duración de la nota, con extremos en cero.

    Si ataque + decaimiento + liberación no caben, se acortan en proporción.
    La liberación no añade muestras ni cambia el ritmo de la melodía.
    """
    if n < 3:
        return np.zeros(n)
    a, d, r = (float(gen[k]) for k in ("ataque", "decaimiento", "liberacion"))
    fin = (n - 1) / sr
    escala = min(1.0, fin / (a + d + r)) if a + d + r else 1.0
    a, d, r = a * escala, d * escala, r * escala
    # Un mínimo de una muestra evita saltos incluso con tiempos cero.
    a = max(a, 1 / sr)
    r = max(r, 1 / sr)
    d = min(d, max(0.0, fin - a - r))
    return np.interp(np.arange(n) / sr,
                     [0, a, a + d, max(a + d, fin - r), fin],
                     [0, 1, gen["sostenido"], gen["sostenido"], 0])


def sintetizar_instrumento(notas, duraciones, gen: dict, sr=SR) -> np.ndarray:
    """Ocho armónicos + ADSR + vibrato; mono, finito y normalizado a [-1, 1].

    Las notas son MIDI (0..127); None representa un silencio. La duración
    incluye la liberación. Se omiten armónicos que alcanzarían Nyquist.
    """
    if not isinstance(sr, (int, np.integer)) or sr <= 0:
        raise ValueError("sr debe ser un entero positivo")
    notas, duraciones = list(notas), np.asarray(list(duraciones), dtype=float)
    if duraciones.ndim != 1 or len(notas) != len(duraciones):
        raise ValueError("notas y duraciones deben tener la misma longitud")
    if not np.all(np.isfinite(duraciones)) or np.any(duraciones < 0):
        raise ValueError("Las duraciones deben ser finitas y no negativas")
    claves = [f"amp_h{h}" for h in range(1, 9)] + [
        "ataque", "decaimiento", "sostenido", "liberacion", "vib_frec", "vib_prof"]
    g = {k: float(gen[k]) for k in claves}
    if not all(np.isfinite(v) and v >= 0 for v in g.values()):
        raise ValueError("Los parámetros deben ser finitos y no negativos")
    if g["sostenido"] > 1 or g["vib_prof"] > 1:
        raise ValueError("sostenido y vib_prof deben estar en [0, 1]")
    partes = []
    for midi, dur in zip(notas, duraciones):
        n = int(dur * sr)
        y = np.zeros(n)
        if midi is not None:
            if not np.isfinite(midi) or not 0 <= midi <= 127:
                raise ValueError("Las notas deben ser MIDI entre 0 y 127, o None")
            t = np.arange(n) / sr
            f0 = 440.0 * 2 ** ((midi - 69) / 12)
            frecuencia = f0 * (1 + g["vib_prof"] * np.sin(2 * np.pi * g["vib_frec"] * t))
            fase = 2 * np.pi * np.cumsum(frecuencia) / sr
            for h in range(1, 9):
                if h * f0 * (1 + g["vib_prof"]) < sr / 2:
                    y += g[f"amp_h{h}"] * np.sin(h * fase)
            y *= _adsr(n, g, sr)
        partes.append(y)
    salida = np.concatenate(partes) if partes else np.empty(0)
    pico = np.max(np.abs(salida), initial=0.0)
    return salida / pico if pico > 0 else salida


def _magnitud(y):
    return np.abs(stft(y, fs=SR, window="hann", nperseg=1024,
                       noverlap=768, boundary="zeros", padded=True)[2])


def _a_db(magnitud):
    pico = magnitud.max()
    if pico <= 0:
        return np.full_like(magnitud, -80.0)
    return np.maximum(20 * np.log10(np.maximum(magnitud / pico, 1e-4)), -80.0)


def _similitud_db(candidato, referencia):
    """MAE/80 en la unión de bandas activas, para penalizar armónicos extra.

    Banda activa: alcanza -60 dB en algún instante en cualquiera de los audios.
    Se conservan TODOS los instantes para medir también ataque y decaimiento.
    """
    if np.all(candidato == -80):
        return 0.0
    bandas = np.maximum(candidato.max(axis=1), referencia.max(axis=1)) > -60
    if not np.any(bandas):
        return 0.0
    error = np.mean(np.abs(candidato[bandas] - referencia[bandas]))
    return float(np.clip(1 - error / 80, 0, 1))


def _croma(magnitud):
    """Agrupa potencia de STFT en 12 clases de nota; no requiere librosa.

    Se descartan frecuencias bajo 50 Hz por la resolución de la STFT.
    """
    frecuencias = np.fft.rfftfreq(1024, 1 / SR)
    validas = frecuencias >= 50
    clases = np.rint(69 + 12 * np.log2(frecuencias[validas] / 440)).astype(int) % 12
    croma = np.zeros((12, magnitud.shape[1]))
    np.add.at(croma, clases, magnitud[validas] ** 2)
    norma = np.linalg.norm(croma)
    return croma / norma if norma > 0 else croma


def _decodificar(x):
    x = np.asarray(x, dtype=float)
    if x.shape != (len(rol1.GENES),) or not np.all(np.isfinite(x)):
        raise ValueError("Se esperaba un vector finito con un valor por gen")
    if np.any((x < 0) | (x > 1)):
        raise ValueError("El cromosoma debe estar en [0, 1]")
    return rol1.decodificar(x)


def fitness(x: np.ndarray) -> float:
    """STFT en dB: 1 - MAE/80 en bandas activas. Mayor = mejor, rango [0, 1]."""
    y = sintetizar_instrumento([NOTA_REFERENCIA], [DURACION_REFERENCIA], _decodificar(x))
    return _similitud_db(_a_db(_magnitud(y)), REF_DB)


def fitness_croma(x: np.ndarray) -> float:
    """Similitud coseno de croma-tiempo, en [0, 1]; silencio obtiene cero.

    Útil para contrastar, pero menos sensible al timbre: agrupa octavas.
    """
    y = sintetizar_instrumento([NOTA_REFERENCIA], [DURACION_REFERENCIA], _decodificar(x))
    return float(np.clip(np.sum(_croma(_magnitud(y)) * REF_CROMA), 0, 1))


# Ruta independiente del directorio de ejecución (también funciona en notebooks/).
# Fallar explícitamente si falta el audio evita optimizar otra referencia sin aviso.
REFERENCIA, _sr = sf.read(RUTA_REFERENCIA, dtype="float64")
if _sr != SR or REFERENCIA.ndim != 1 or len(REFERENCIA) < 1024:
    raise ValueError("referencia.wav debe ser mono, 22050 Hz y al menos 1024 muestras")
if not np.all(np.isfinite(REFERENCIA)) or np.max(np.abs(REFERENCIA)) == 0:
    raise ValueError("referencia.wav debe contener audio finito y no silencioso")
DURACION_REFERENCIA = len(REFERENCIA) / SR
_ref_magnitud = _magnitud(REFERENCIA)
REF_DB = _a_db(_ref_magnitud)
REF_CROMA = _croma(_ref_magnitud)
