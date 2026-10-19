"""
Rol 3 — Experimentos: comparar 3 combinaciones de operadores con datos.

Uso (en el notebook, con las piezas reales de los Roles 1, 2 y 4):
    from src import rol3_experimentos as e3
    df, hist = e3.comparar_combinaciones(rol4.ejecutar_ag, rol2.fitness, config_base, seeds=range(5))
    e3.tabla_resumen(df);  e3.graficar(hist, "results/graficos")
"""
from __future__ import annotations

import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .rol3_operadores import COMBINACIONES


def comparar_combinaciones(ag_fn, fitness_fn, config_base, seeds=range(5),
                           combinaciones=COMBINACIONES):
    """Corre el AG con cada combinación y cada semilla (mismo presupuesto).
    Devuelve (df por corrida, historiales {combo: [hist por semilla]})."""
    filas, historiales = [], {}
    for nombre, ops in combinaciones.items():
        historiales[nombre] = []
        for s in seeds:
            cfg = {**config_base, "operadores": ops}
            r = ag_fn(cfg, fitness_fn, s)
            h = r["historial"]
            mx = np.array(h["max"])
            objetivo = mx[0] + 0.95 * (mx[-1] - mx[0])
            filas.append({
                "combinacion": nombre, "semilla": s,
                "fitness_final": mx[-1],
                "media_final": h["media"][-1],
                "gen_al_95%": int(np.argmax(mx >= objetivo)),
                "diversidad_gen10": h["diversidad"][min(10, len(mx) - 1)],
                "diversidad_final": h["diversidad"][-1],
            })
            historiales[nombre].append(h)
    return pd.DataFrame(filas), historiales


def tabla_resumen(df):
    """Tabla comparativa (media ± desv.) por combinación, ordenada por fitness."""
    agg = df.groupby("combinacion").agg(
        fitness_media=("fitness_final", "mean"), fitness_std=("fitness_final", "std"),
        mejor=("fitness_final", "max"), peor=("fitness_final", "min"),
        gen_al_95=("gen_al_95%", "mean"),
        div_gen10=("diversidad_gen10", "mean"), div_final=("diversidad_final", "mean"),
    )
    return agg.sort_values("fitness_media", ascending=False).round(4)


def graficar(historiales, carpeta=None, sufijo=""):
    """Dos gráficos: fitness máx vs generación y diversidad vs generación
    (línea = media entre semillas, banda = ±1 desv.)."""
    fig, ejes = plt.subplots(1, 2, figsize=(12, 4.2))
    for nombre, hs in historiales.items():
        etiqueta = nombre.split(" (")[0]
        for eje, clave in zip(ejes, ("max", "diversidad")):
            m = np.array([h[clave] for h in hs])
            mu, sd = m.mean(0), m.std(0)
            g = np.arange(len(mu))
            eje.plot(g, mu, label=etiqueta)
            eje.fill_between(g, mu - sd, mu + sd, alpha=0.2)
    ejes[0].set(title="Fitness máximo vs generación", xlabel="generación", ylabel="fitness")
    ejes[1].set(title="Diversidad vs generación", xlabel="generación",
                ylabel="diversidad (1 = aleatoria)")
    for e in ejes:
        e.grid(alpha=0.3); e.legend()
    fig.tight_layout()
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)
        fig.savefig(os.path.join(carpeta, f"rol3_operadores{sufijo}.png"), dpi=130)
    return fig
