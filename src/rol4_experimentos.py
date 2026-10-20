"""
Rol 4 — Experimentos de dinámica poblacional.

Uso (en el notebook):
    from src import rol4_experimentos as e4
    cfgs = e4.configuraciones(config_base)                  # 15 configuraciones
    df, hist, mejores = e4.correr_configuraciones(rol4.ejecutar_ag, rol2.fitness, cfgs, seeds=range(5))
    tabla = e4.tabla_resumen(df)                            # promedio por configuración + Δ vs base
    e4.graficar_convergencia(hist, ["base", "pob=10", "pob=60"], carpeta="results/graficos")

Idea central: el tamaño de la población cambia el NÚMERO DE EVALUACIONES (= costo). Por eso cada
hiperparámetro se compara de dos maneras:
    (a) con las mismas generaciones            -> ¿qué pasa si solo cambio el parámetro?
    (b) con el mismo presupuesto de evaluaciones -> ¿cuál es mejor usando el mismo costo?
"""
from __future__ import annotations

import copy
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

UMBRAL_DIVERSIDAD = 0.05     # por debajo de esto consideramos que la población "colapsó"
TOL_PREMATURA = 0.01         # a cuánto del mejor conocido debe quedar para NO ser prematura


# ------------------------------------------------------------ configuraciones
def generaciones_para_presupuesto(presupuesto, poblacion, elitismo):
    """Generaciones T tales que  poblacion + T*(poblacion-elitismo)  ≈ presupuesto."""
    return max(1, int(round((presupuesto - poblacion) / (poblacion - elitismo))))


def configuraciones(base: dict) -> dict:
    """Devuelve {nombre: config}. Cada una cambia UN solo hiperparámetro de la base
    (excepto las de 'igual presupuesto', que además ajustan las generaciones)."""
    n0, e0, T0 = base["poblacion"], base["elitismo"], base["generaciones"]
    presupuesto = n0 + T0 * (n0 - e0)

    def var(**cambios):
        cfg = copy.deepcopy(base)
        for k, v in cambios.items():
            if k == "pm":
                cfg["operadores"] = {**cfg["operadores"], "pm": v}
            else:
                cfg[k] = v
        return cfg

    cfgs = {"base": copy.deepcopy(base)}
    # (a) mismas generaciones: población y elitismo
    for n in (10, 20, 60):
        cfgs[f"pob={n}"] = var(poblacion=n)
    for e in (0, 1, 5, 10):
        cfgs[f"elit={e}"] = var(elitismo=e)
    # criterio de parada: máximo de generaciones
    for T in (25, 100):
        cfgs[f"gen={T}"] = var(generaciones=T)
    # tasa de mutación (se reutiliza el operador del Rol 3)
    for pm in (0.02, 0.30):
        cfgs[f"pm={pm}"] = var(pm=pm)
    # opcionales del ciclo
    cfgs["inmigrantes"] = var(inmigrantes={"umbral": UMBRAL_DIVERSIDAD, "fraccion": 0.2})
    cfgs["paciencia=10"] = var(paciencia=10, generaciones=200)
    # (b) mismo presupuesto de evaluaciones que la base
    for n in (10, 60):
        cfgs[f"pob={n} (=presup.)"] = var(poblacion=n,
                                          generaciones=generaciones_para_presupuesto(presupuesto, n, e0))
    # (c) caso PROVOCADO de convergencia prematura y sus remedios (población chica + casi sin mutación)
    prem = var(poblacion=8, pm=0.01)
    cfgs["prem: pob=8 pm=0.01"] = prem
    cfgs["prem + inmigrantes"] = {**copy.deepcopy(prem),
                                  "inmigrantes": {"umbral": UMBRAL_DIVERSIDAD, "fraccion": 0.25}}
    cfgs["prem + pm=0.15"] = {**copy.deepcopy(prem), "operadores": {**prem["operadores"], "pm": 0.15}}
    cfgs["prem + pob=30"] = {**copy.deepcopy(prem), "poblacion": 30}
    return cfgs


# ------------------------------------------------------------ corridas
def _fitness_con_presupuesto(h, presupuesto):
    """Mejor fitness (max acumulado) usando a lo sumo `presupuesto` evaluaciones."""
    ev = np.array(h["evaluaciones"])
    ok = np.where(ev <= presupuesto)[0]
    return float(np.max(h["max"][: ok[-1] + 1])) if len(ok) else float("nan")


def _primera_gen_colapso(h):
    d = np.array(h["diversidad"])
    idx = np.where(d < UMBRAL_DIVERSIDAD)[0]
    return int(idx[0]) if len(idx) else np.nan


def correr_configuraciones(ag_fn, fitness_fn, cfgs, seeds=range(5), presupuesto_comun=400):
    """Corre cada configuración con cada semilla. Devuelve
    (df por corrida, historiales {nombre: [hist por semilla]}, mejores {nombre: [x por semilla]})."""
    filas, historiales, mejores = [], {}, {}
    for nombre, cfg in cfgs.items():
        historiales[nombre], mejores[nombre] = [], []
        for s in seeds:
            r = ag_fn(cfg, fitness_fn, s)
            h = r["historial"]
            historiales[nombre].append(h)
            mejores[nombre].append(np.asarray(r["mejor"]))
            filas.append({
                "config": nombre, "semilla": s,
                "poblacion": cfg["poblacion"], "elitismo": cfg["elitismo"],
                "generaciones": len(h["max"]) - 1,
                "fitness_gen0": h["max"][0],
                "fitness_final": r["mejor_fit"],
                "evaluaciones": h["evaluaciones"][-1],
                f"fit_{presupuesto_comun}ev": _fitness_con_presupuesto(h, presupuesto_comun),
                "div_gen10": h["diversidad"][min(10, len(h["diversidad"]) - 1)],
                "div_final": h["diversidad"][-1],
                "gen_colapso": _primera_gen_colapso(h),
                "inmigraciones": len(r.get("inmigraciones", [])),
            })
    df = pd.DataFrame(filas)
    mejor_conocido = df["fitness_final"].max()
    df["prematura"] = (df["div_final"] < UMBRAL_DIVERSIDAD) & (df["fitness_final"] < mejor_conocido - TOL_PREMATURA)
    return df, historiales, mejores


def tabla_resumen(df, presupuesto_comun=400):
    """Una fila por configuración: medias sobre las semillas y Δ respecto a 'base'."""
    col_pres = f"fit_{presupuesto_comun}ev"
    g = df.groupby("config", sort=False)
    t = pd.DataFrame({
        "poblacion": g["poblacion"].first(), "elitismo": g["elitismo"].first(),
        "generaciones": g["generaciones"].mean().round(0),
        "evaluaciones": g["evaluaciones"].mean().round(0),
        "fit_final": g["fitness_final"].mean(),
        "desv": g["fitness_final"].std(ddof=1),
        col_pres: g[col_pres].mean(),
        "div_final": g["div_final"].mean(),
        "gen_colapso": g["gen_colapso"].mean(),
        "% prematura": g["prematura"].mean() * 100,
    })
    t["Δ vs base"] = t["fit_final"] - t.loc["base", "fit_final"]
    return t.round(4)


# ------------------------------------------------------------ gráficos
def _guardar(fig, carpeta, nombre):
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)
        fig.savefig(os.path.join(carpeta, nombre), dpi=130, bbox_inches="tight")


def _matriz(hists, clave, largo=None):
    """Apila historiales (pueden tener largos distintos si hubo parada anticipada: se rellena
    repitiendo el último valor para poder promediar)."""
    largo = largo or max(len(h[clave]) for h in hists)
    return np.array([np.pad(h[clave], (0, largo - len(h[clave])), mode="edge") for h in hists])


def graficar_convergencia(historiales, nombres, carpeta=None, nombre="rol4_convergencia.png"):
    """Para cada configuración elegida: fitness máximo y medio (con ±1 desv. entre semillas)
    y diversidad, todo contra la generación."""
    fig, ax = plt.subplots(1, 3, figsize=(15, 4))
    for i, n in enumerate(nombres):
        c = f"C{i}"
        mx, md, dv = (_matriz(historiales[n], k) for k in ("max", "media", "diversidad"))
        g = np.arange(mx.shape[1])
        ax[0].plot(g, mx.mean(0), color=c, label=n)
        ax[0].fill_between(g, mx.mean(0) - mx.std(0), mx.mean(0) + mx.std(0), color=c, alpha=0.15)
        ax[1].plot(g, md.mean(0), color=c, label=n)
        ax[2].plot(g, dv.mean(0), color=c, label=n)
    ax[0].set(title="Fitness máximo (media de semillas ±1 desv.)", xlabel="generación")
    ax[1].set(title="Fitness medio de la población", xlabel="generación")
    ax[2].set(title="Diversidad genética", xlabel="generación")
    ax[2].axhline(UMBRAL_DIVERSIDAD, color="k", ls="--", lw=1, label="umbral 0.05")
    for a in ax:
        a.grid(alpha=0.3)
    ax[0].legend(fontsize=8)
    fig.tight_layout()
    _guardar(fig, carpeta, nombre)
    return fig


def graficar_todas(historiales, carpeta=None, nombre="rol4_convergencia_todas.png", columnas=4):
    """Una curva de convergencia POR CONFIGURACIÓN (máximo y media, ±1 desv. del máximo entre semillas)
    con la diversidad en el eje derecho."""
    nombres = list(historiales)
    filas = int(np.ceil(len(nombres) / columnas))
    fig, axs = plt.subplots(filas, columnas, figsize=(4.2 * columnas, 3.2 * filas), sharey=True)
    axs = np.atleast_1d(axs).ravel()
    for a, n in zip(axs, nombres):
        mx, md, dv = (_matriz(historiales[n], k) for k in ("max", "media", "diversidad"))
        g = np.arange(mx.shape[1])
        a.plot(g, mx.mean(0), color="C0", label="máx")
        a.fill_between(g, mx.mean(0) - mx.std(0), mx.mean(0) + mx.std(0), color="C0", alpha=0.2)
        a.plot(g, md.mean(0), color="C1", label="media")
        b = a.twinx(); b.plot(g, dv.mean(0), color="C2", ls="--", lw=1); b.set_ylim(0, 1)
        a.set_title(n, fontsize=9); a.grid(alpha=0.3); a.set_xlabel("generación", fontsize=8)
    for a in axs[len(nombres):]:
        a.axis("off")
    axs[0].legend(fontsize=7, loc="lower right")
    fig.suptitle("Convergencia por configuración (azul: máx, naranja: media, verde punteado: diversidad)", y=1.0)
    fig.tight_layout()
    _guardar(fig, carpeta, nombre)
    return fig


def graficar_vs_evaluaciones(historiales, nombres, carpeta=None, nombre="rol4_vs_evaluaciones.png"):
    """Fitness máximo contra EVALUACIONES acumuladas: comparación justa de costo."""
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for i, n in enumerate(nombres):
        hs = historiales[n]
        ev = np.mean([h["evaluaciones"] for h in hs], axis=0) if len({len(h["max"]) for h in hs}) == 1 \
            else np.array(hs[0]["evaluaciones"])
        mx = _matriz(hs, "max", len(ev)).mean(0)
        ax.plot(ev, mx, color=f"C{i}", label=n)
    ax.set(title="Fitness máximo vs evaluaciones (mismo costo = misma x)",
           xlabel="evaluaciones de fitness acumuladas", ylabel="fitness máximo")
    ax.grid(alpha=0.3); ax.legend(fontsize=8)
    _guardar(fig, carpeta, nombre)
    return fig


def graficar_estancamiento(historiales, nombre_cfg, carpeta=None, nombre="rol4_estancamiento.png"):
    """Fitness y diversidad de UNA configuración, una línea por semilla: se ve la convergencia
    prematura (diversidad ~0 con fitness aún bajo)."""
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    for i, h in enumerate(historiales[nombre_cfg]):
        ax[0].plot(h["max"], color=f"C{i}", label=f"semilla {i}")
        ax[1].plot(h["diversidad"], color=f"C{i}")
    ax[1].axhline(UMBRAL_DIVERSIDAD, color="k", ls="--", lw=1)
    ax[0].set(title=f"{nombre_cfg}: fitness máximo", xlabel="generación")
    ax[1].set(title=f"{nombre_cfg}: diversidad", xlabel="generación")
    for a in ax:
        a.grid(alpha=0.3)
    ax[0].legend(fontsize=8)
    fig.tight_layout()
    _guardar(fig, carpeta, nombre)
    return fig


# ------------------------------------------------------------ análisis
def deriva_por_gen(mejores, nombres_genes, nombre_cfg="base"):
    """Desviación estándar de cada gen del mejor individuo ENTRE semillas. Si el gen importa, todas las
    corridas convergen a valores parecidos (desv. baja); si es casi neutral, cada corrida lo fija
    en un valor al azar (deriva genética: desv. alta ≈ 0.29, la de un uniforme en [0,1])."""
    X = np.array(mejores[nombre_cfg])
    return (pd.DataFrame({"gen": nombres_genes, "desv_entre_semillas": X.std(axis=0, ddof=1),
                          "media": X.mean(axis=0)})
            .sort_values("desv_entre_semillas").reset_index(drop=True).round(3))


def efecto_hiperparametros(df, presupuesto_comun=400):
    """Efecto de cada hiperparámetro = diferencia de fitness entre su valor alto y bajo (ambas
    lecturas: mismas generaciones y mismo presupuesto). Formato compatible con
    rol5_analisis.graficar_tornado (columnas factor, valor_bajo, valor_alto, fitness_bajo/alto, base)."""
    m = df.groupby("config")["fitness_final"].mean()
    mp = df.groupby("config")[f"fit_{presupuesto_comun}ev"].mean()
    base = m["base"]
    def fila(factor, lo, hi, serie, b):
        return {"factor": factor, "valor_bajo": lo.split("=")[1], "valor_alto": hi.split("=")[1],
                "fitness_bajo": serie[lo], "fitness_alto": serie[hi], "base": b,
                "rango": abs(serie[hi] - serie[lo])}
    pares = [("poblacion", "pob=10", "pob=60"), ("elitismo", "elit=0", "elit=10"),
             ("generaciones", "gen=25", "gen=100"), ("mutación pm", "pm=0.02", "pm=0.3")]
    mismas_gen = pd.DataFrame([fila(f, a, b, m, base) for f, a, b in pares])
    mismo_pres = pd.DataFrame([fila(f, a, b, mp, mp["base"]) for f, a, b in pares if f != "generaciones"])
    # población a igual presupuesto (lectura justa del tamaño de población)
    igual = pd.DataFrame([{"factor": "poblacion (=presup.)", "valor_bajo": "10", "valor_alto": "60",
                           "fitness_bajo": m["pob=10 (=presup.)"], "fitness_alto": m["pob=60 (=presup.)"],
                           "base": base,
                           "rango": abs(m["pob=60 (=presup.)"] - m["pob=10 (=presup.)"])}])
    return (mismas_gen.sort_values("rango", ascending=False).reset_index(drop=True),
            mismo_pres.sort_values("rango", ascending=False).reset_index(drop=True),
            igual)
