"""
Rol 4 — El Estratega: dinámica poblacional (ciclo completo del AG).

Este módulo ejecuta el ciclo evolutivo. NO implementa operadores: para crear hijos
llama a `rol3_operadores.reproducir` (selección -> cruce -> mutación -> reparar) y para
medir diversidad usa `rol3_operadores.diversidad`. Lo que decide el Rol 4 es:

    * tamaño de la población            config["poblacion"]
    * elitismo                          config["elitismo"]
    * criterio de parada                config["generaciones"] (máximo)  y  config["paciencia"] (estancamiento)
    * (opcional) inmigrantes aleatorios config["inmigrantes"] cuando la diversidad cae demasiado
    * medir la convergencia             historial: máximo, media, desviación, diversidad, evaluaciones

Convención del grupo (README): cada individuo es un np.ndarray de floats en [0, 1],
el fitness es "mayor = mejor" y toda la aleatoriedad sale de np.random.default_rng(seed).

Firma obligatoria (la usan los notebooks de los Roles 3 y 5):

    ejecutar_ag(config, fitness_fn, seed) -> {
        "mejor": np.ndarray, "mejor_fit": float,
        "mejor_gen0": np.ndarray,            # el mejor de la población inicial (audio "Gen 0")
        "historial": {"max": [...], "media": [...], "std": [...],
                      "diversidad": [...], "evaluaciones": [...]},   # una entrada por generación
    }

Claves de `config`
------------------
Obligatorias : "poblacion", "n_genes", "generaciones"
Con defecto  : "elitismo" (2), "operadores" (None -> los defectos del Rol 3)
Opcionales   : "paciencia" (None = sin parada por estancamiento) y "tolerancia" (1e-4),
               "inmigrantes" (None = desactivado) como {"umbral": 0.05, "fraccion": 0.2}

Con las claves opcionales ausentes el ciclo es el generacional con elitismo clásico,
igual al que ya usaban los notebooks del Rol 3 y 5.
"""
from __future__ import annotations

import numpy as np

from . import rol3_operadores as op

CLAVES_HISTORIAL = ("max", "media", "std", "diversidad", "evaluaciones")


# ------------------------------------------------------------------ utilidades
def _validar_config(config: dict) -> dict:
    """Revisa la configuración y devuelve una copia con los valores por defecto aplicados."""
    for clave in ("poblacion", "n_genes", "generaciones"):
        if clave not in config:
            raise KeyError(f"Falta '{clave}' en config")
    cfg = {"elitismo": 2, "operadores": None, "paciencia": None,
           "tolerancia": 1e-4, "inmigrantes": None, **config}

    n, T, e = cfg["poblacion"], cfg["generaciones"], cfg["elitismo"]
    if n < 2:
        raise ValueError("poblacion debe ser >= 2")
    if cfg["n_genes"] < 1:
        raise ValueError("n_genes debe ser >= 1")
    if T < 1:
        raise ValueError("generaciones debe ser >= 1")
    if not 0 <= e < n:
        raise ValueError("elitismo debe cumplir 0 <= elitismo < poblacion "
                         "(si no, no quedaría lugar para hijos)")
    if cfg["paciencia"] is not None and cfg["paciencia"] < 1:
        raise ValueError("paciencia debe ser >= 1 (o None para desactivarla)")
    if cfg["inmigrantes"] is not None:
        cfg["inmigrantes"] = {"umbral": 0.05, "fraccion": 0.2, **cfg["inmigrantes"]}
    return cfg


def _evaluar(fitness_fn, pob: np.ndarray) -> np.ndarray:
    """Fitness de cada individuo (una llamada a fitness_fn por individuo)."""
    return np.array([fitness_fn(x) for x in pob], dtype=float)


# ------------------------------------------------------------------ ciclo del AG
def ejecutar_ag(config: dict, fitness_fn, seed) -> dict:
    """Ciclo generacional con elitismo. Devuelve el resultado con la firma acordada.

    Pasos de cada generación t = 0 .. T-1
        1. Se ordenan los individuos por fitness (mayor = mejor).
        2. Los `elitismo` mejores pasan SIN cambios a la siguiente generación.
        3. El resto (poblacion - elitismo) son hijos creados con rol3_operadores.reproducir.
        4. Se evalúan solo los hijos (los elites conservan su fitness: no se re-evalúan).
        5. (opcional) si la diversidad cayó bajo el umbral, los peores se reemplazan por
           individuos aleatorios (inmigrantes).
        6. Se registran las estadísticas y se revisa el criterio de parada.

    Notas de diseño
        * Se guarda el mejor individuo HISTÓRICO. Con elitismo >= 1 coincide con el mejor de la
          última población; con elitismo = 0 podría perderse, por eso se guarda aparte.
        * La población inicial depende solo de la semilla (se genera antes de usar ningún
          operador), así que dos configuraciones con la misma semilla parten del mismo Gen 0.
        * historial tiene T+1 entradas (generaciones 0..T) si no hay parada anticipada.
        * historial["evaluaciones"] es el número ACUMULADO de evaluaciones de fitness; el
          baseline de búsqueda aleatoria del Rol 5 usa su último valor como presupuesto.
    """
    cfg = _validar_config(config)
    rng = np.random.default_rng(seed)
    n, d, T, elite = cfg["poblacion"], cfg["n_genes"], cfg["generaciones"], cfg["elitismo"]

    # --- generación 0: población aleatoria uniforme en [0, 1]^d
    pob = rng.random((n, d))
    fit = _evaluar(fitness_fn, pob)
    evaluaciones = n

    i0 = int(np.argmax(fit))
    mejor_gen0 = pob[i0].copy()
    mejor_x, mejor_f = pob[i0].copy(), float(fit[i0])

    historial = {k: [] for k in CLAVES_HISTORIAL}

    def registrar():
        historial["max"].append(float(fit.max()))
        historial["media"].append(float(fit.mean()))
        historial["std"].append(float(fit.std()))
        historial["diversidad"].append(op.diversidad(pob))
        historial["evaluaciones"].append(int(evaluaciones))

    registrar()

    referencia = mejor_f          # último valor que contó como "mejora" (para la parada)
    gens_sin_mejora = 0
    inmigraciones = []            # generaciones en las que se inyectaron inmigrantes
    motivo = "generaciones"
    gen_final = 0

    for t in range(T):
        orden = np.argsort(fit)[::-1]                      # de mejor a peor

        # --- 1) reproducción (rol3_operadores) de los individuos no elite
        hijos = op.reproducir(pob, fit, cfg["operadores"], t, T, rng, n_hijos=n - elite)
        fit_hijos = _evaluar(fitness_fn, hijos)
        evaluaciones += len(hijos)

        # --- 2) nueva población: elites + hijos
        pob = np.vstack([pob[orden[:elite]], hijos])
        fit = np.concatenate([fit[orden[:elite]], fit_hijos])

        # --- 3) (opcional) inmigrantes si la diversidad se desplomó
        inm = cfg["inmigrantes"]
        if inm is not None and op.diversidad(pob) < inm["umbral"]:
            m = int(min(max(1, round(inm["fraccion"] * n)), n - 1))
            peores = np.argsort(fit)[:m]                   # nunca incluye al mejor (m <= n-1)
            pob[peores] = rng.random((m, d))
            fit[peores] = _evaluar(fitness_fn, pob[peores])
            evaluaciones += m
            inmigraciones.append(t + 1)

        # --- 4) mejor histórico
        j = int(np.argmax(fit))
        if fit[j] > mejor_f:
            mejor_x, mejor_f = pob[j].copy(), float(fit[j])

        registrar()
        gen_final = t + 1

        # --- 5) criterio de parada por estancamiento
        if cfg["paciencia"] is not None:
            if mejor_f > referencia + cfg["tolerancia"]:
                referencia, gens_sin_mejora = mejor_f, 0
            else:
                gens_sin_mejora += 1
            if gens_sin_mejora >= cfg["paciencia"]:
                motivo = "estancamiento"
                break

    return {
        "mejor": mejor_x, "mejor_fit": mejor_f, "mejor_gen0": mejor_gen0,
        "historial": historial,
        # --- información extra (los notebooks de Rol 3 y 5 no la necesitan)
        "poblacion_final": pob.copy(),
        "gen_final": gen_final,
        "motivo_parada": motivo,
        "inmigraciones": inmigraciones,
    }
