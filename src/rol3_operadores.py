"""
Rol 3 — El Motor Evolutivo: operadores genéticos.

Convención del grupo: cada individuo es un np.ndarray de floats en [0, 1]
(los genes físicos se obtienen con rol1.decodificar). Todas las funciones
reciben un `rng = np.random.default_rng(seed)` para ser reproducibles.

Contenido
---------
Selección : seleccion_torneo (k=3), seleccion_ruleta, seleccion_sus
Cruce     : cruce_blend (BLX-α), cruce_uniforme
Mutación  : mutacion_gaussiana, mutacion_uniforme, mutacion_no_uniforme
Validez   : reparar  (garantiza hijos dentro de [0, 1])
Métrica   : diversidad
Integración con Rol 4: reproducir(pob, fit, cfg, t, T, rng) -> hijos
"""
from __future__ import annotations

import numpy as np

LIM_INF, LIM_SUP = 0.0, 1.0


# ---------------------------------------------------------------- validez
def reparar(x: np.ndarray) -> np.ndarray:
    """Garantiza hijos válidos: recorta cada gen al rango [0, 1]."""
    return np.clip(x, LIM_INF, LIM_SUP)


# -------------------------------------------------------------- selección
def seleccion_torneo(pob, fit, n, rng, k=3):
    """Torneo de tamaño k: se toman k individuos al azar y gana el de mayor fitness.
    Devuelve una matriz (n, d) con copias de los ganadores."""
    fit = np.asarray(fit)
    competidores = rng.integers(0, len(pob), size=(n, k))
    ganadores = competidores[np.arange(n), np.argmax(fit[competidores], axis=1)]
    return pob[ganadores].copy()


def _probabilidades(fit):
    """Ruleta/SUS necesitan valores positivos: se desplaza el fitness por el mínimo."""
    fit = np.asarray(fit, dtype=float)
    f = fit - fit.min() + 1e-12
    return f / f.sum()


def seleccion_ruleta(pob, fit, n, rng):
    """Ruleta: P(i) proporcional al fitness (desplazado para ser > 0)."""
    idx = rng.choice(len(pob), size=n, replace=True, p=_probabilidades(fit))
    return pob[idx].copy()


def seleccion_sus(pob, fit, n, rng):
    """Stochastic Universal Sampling: una sola ruleta con n punteros
    equiespaciados -> menos varianza que n giros independientes."""
    acumulada = np.cumsum(_probabilidades(fit))
    acumulada[-1] = 1.0
    inicio = rng.uniform(0, 1.0 / n)
    punteros = inicio + np.arange(n) / n
    idx = np.searchsorted(acumulada, punteros)
    rng.shuffle(idx)  # que el orden no correlacione con el ranking
    return pob[idx].copy()


# ------------------------------------------------------------------ cruce
def cruce_blend(p1, p2, rng, alpha=0.5):
    """BLX-α: cada gen hijo ~ U[min - α·d, max + α·d], con d = |p1 - p2|.
    α > 0 permite salir del segmento entre padres (exploración)."""
    lo, hi = np.minimum(p1, p2), np.maximum(p1, p2)
    d = hi - lo
    a, b = lo - alpha * d, hi + alpha * d
    h1 = rng.uniform(a, b)
    h2 = rng.uniform(a, b)
    return reparar(h1), reparar(h2)


def cruce_uniforme(p1, p2, rng, p=0.5):
    """Uniforme: cada gen se hereda de p1 o p2 con probabilidad p.
    No crea valores nuevos, solo recombina los existentes."""
    mascara = rng.random(p1.shape) < p
    h1 = np.where(mascara, p1, p2)
    h2 = np.where(mascara, p2, p1)
    return h1.copy(), h2.copy()


# --------------------------------------------------------------- mutación
def mutacion_gaussiana(x, rng, pm, sigma=0.05):
    """Cada gen, con prob. pm, recibe ruido N(0, σ). Paso local (explotación)."""
    x = x.copy()
    m = rng.random(x.shape) < pm
    x[m] += rng.normal(0.0, sigma, size=m.sum())
    return reparar(x)


def mutacion_uniforme(x, rng, pm):
    """Cada gen, con prob. pm, se reemplaza por U(0, 1). Salto global (exploración)."""
    x = x.copy()
    m = rng.random(x.shape) < pm
    x[m] = rng.uniform(LIM_INF, LIM_SUP, size=m.sum())
    return x


def mutacion_no_uniforme(x, rng, pm, t, T, b=2.0):
    """No uniforme (Michalewicz): el tamaño del paso decrece con la generación t.
    Δ(t, y) = y · (1 - r^((1 - t/T)^b)).  Explora al inicio, afina al final."""
    x = x.copy()
    frac = (1.0 - min(t, T) / T) ** b
    for i in np.where(rng.random(x.shape) < pm)[0]:
        r = rng.random()
        if rng.random() < 0.5:
            x[i] += (LIM_SUP - x[i]) * (1.0 - r ** frac)
        else:
            x[i] -= (x[i] - LIM_INF) * (1.0 - r ** frac)
    return reparar(x)


# ---------------------------------------------------------------- métrica
def diversidad(pob) -> float:
    """Diversidad genotípica: desviación estándar media por gen, normalizada por
    la de U(0,1) (=0.2887). ≈1 en población aleatoria, → 0 si convergió."""
    return float(np.mean(np.std(pob, axis=0)) / np.sqrt(1 / 12))


def diversidad_pares(pob) -> float:
    """Distancia euclidiana media entre pares, normalizada por sqrt(d)."""
    d = pob.shape[1]
    dif = pob[:, None, :] - pob[None, :, :]
    dist = np.sqrt((dif ** 2).sum(-1))
    n = len(pob)
    return float(dist.sum() / (n * (n - 1)) / np.sqrt(d))


# ------------------------------------------------- integración con Rol 4
SELECCION = {"torneo": seleccion_torneo, "ruleta": seleccion_ruleta, "sus": seleccion_sus}

CONFIG_DEFECTO = {
    "seleccion": "torneo", "k": 3,
    "cruce": "blend", "alpha": 0.5, "pc": 0.9,
    "mutacion": "gaussiana", "pm": None, "sigma": 0.05, "b": 2.0,
}


def reproducir(pob, fit, cfg, t, T, rng, n_hijos=None):
    """Una generación de reproducción: selección -> cruce -> mutación -> reparar.
    El Rol 4 la llama dentro de su ciclo (el elitismo lo decide el Rol 4).

    pob : (n, d) en [0,1] | fit : (n,) mayor = mejor | t, T : gen. actual y máxima
    """
    c = {**CONFIG_DEFECTO, **(cfg or {})}
    n, d = pob.shape
    n_hijos = n if n_hijos is None else n_hijos
    pm = c["pm"] if c["pm"] is not None else 1.0 / d

    n_pad = n_hijos + (n_hijos % 2)
    if c["seleccion"] == "torneo":
        padres = seleccion_torneo(pob, fit, n_pad, rng, k=c["k"])
    else:
        padres = SELECCION[c["seleccion"]](pob, fit, n_pad, rng)

    hijos = np.empty_like(padres)
    for i in range(0, n_pad, 2):
        p1, p2 = padres[i], padres[i + 1]
        if rng.random() < c["pc"]:
            if c["cruce"] == "blend":
                h1, h2 = cruce_blend(p1, p2, rng, alpha=c["alpha"])
            else:
                h1, h2 = cruce_uniforme(p1, p2, rng)
        else:
            h1, h2 = p1.copy(), p2.copy()
        hijos[i], hijos[i + 1] = h1, h2

    for i in range(n_pad):
        if c["mutacion"] == "gaussiana":
            hijos[i] = mutacion_gaussiana(hijos[i], rng, pm, sigma=c["sigma"])
        elif c["mutacion"] == "uniforme":
            hijos[i] = mutacion_uniforme(hijos[i], rng, pm)
        else:
            hijos[i] = mutacion_no_uniforme(hijos[i], rng, pm, t, T, b=c["b"])
    return reparar(hijos[:n_hijos])


# ----------------------------- las 3 combinaciones que se comparan
COMBINACIONES = {
    "C1 Explotación (torneo + blend α=0.3 + gaussiana σ=0.03)": {
        "seleccion": "torneo", "k": 3, "cruce": "blend", "alpha": 0.3,
        "mutacion": "gaussiana", "sigma": 0.03},
    "C2 Exploración (ruleta + uniforme + mut. uniforme)": {
        "seleccion": "ruleta", "cruce": "uniforme", "mutacion": "uniforme"},
    "C3 Balance (torneo + blend α=0.5 + no-uniforme)": {
        "seleccion": "torneo", "k": 3, "cruce": "blend", "alpha": 0.5,
        "mutacion": "no_uniforme", "b": 2.0},
}
