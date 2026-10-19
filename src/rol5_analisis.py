"""
Rol 5 — El Analista: meta-evaluación (¿funciona bien? ¿es robusto?).

Todo recibe las piezas de los otros roles como parámetros (ag_fn, fitness_fn,
sintetizar...), así este módulo no depende de cómo estén implementadas.

Contenido
---------
entorno_reproducible     : fija semillas e imprime versiones
busqueda_aleatoria       : baseline con el MISMO presupuesto de evaluaciones
corridas_semillas        : 5–10 corridas -> tabla + varianza
ag_vs_aleatoria          : AG vs baseline, test de Mann-Whitney + tamaño de efecto
graficar_boxplot, graficar_curvas_vs_baseline
sensibilidad_hiperparametros / sensibilidad_genes + graficar_tornado
comparacion_auditiva     : reproductores + espectrogramas lado a lado
crear_encuesta / analizar_encuesta : encuesta ciega a 5–10 personas
"""
from __future__ import annotations

import copy
import json
import os
import platform

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from scipy.signal import stft


# ------------------------------------------------------- reproducibilidad
def entorno_reproducible(seed=42):
    """Fija la semilla global (por si alguna librería usa np.random) y muestra versiones."""
    import matplotlib, scipy
    np.random.seed(seed)
    info = {"python": platform.python_version(), "numpy": np.__version__,
            "scipy": scipy.__version__, "pandas": pd.__version__,
            "matplotlib": matplotlib.__version__, "semilla": seed}
    try:
        import librosa
        info["librosa"] = librosa.__version__
    except ImportError:
        pass
    print(" | ".join(f"{k}={v}" for k, v in info.items()))
    return info


# ----------------------------------------------------------------- baseline
def busqueda_aleatoria(fitness_fn, n_genes, n_evals, seed):
    """Baseline: muestrea n_evals individuos U(0,1)^d y se queda con el mejor.
    curva[i] = mejor fitness encontrado tras i+1 evaluaciones."""
    rng = np.random.default_rng(seed)
    mejor_f, mejor_x, curva = -np.inf, None, np.empty(n_evals)
    for i in range(n_evals):
        x = rng.random(n_genes)
        f = fitness_fn(x)
        if f > mejor_f:
            mejor_f, mejor_x = f, x
        curva[i] = mejor_f
    return {"mejor": mejor_x, "mejor_fit": float(mejor_f), "curva": curva}


# --------------------------------------------------------- corridas / semillas
def corridas_semillas(ag_fn, config, fitness_fn, seeds=range(10)):
    """Corre el AG con varias semillas. Devuelve (df, lista de resultados)."""
    res = [ag_fn(config, fitness_fn, s) for s in seeds]
    df = pd.DataFrame({
        "semilla": list(seeds),
        "fitness_final": [r["mejor_fit"] for r in res],
        "fitness_gen0": [r["historial"]["max"][0] for r in res],
        "evaluaciones": [r["historial"]["evaluaciones"][-1] for r in res],
        "diversidad_final": [r["historial"]["diversidad"][-1] for r in res],
    })
    return df, res


def resumen_varianza(df, col="fitness_final"):
    x = df[col].to_numpy()
    return pd.Series({"n": len(x), "media": x.mean(), "desv": x.std(ddof=1),
                      "CV_%": 100 * x.std(ddof=1) / abs(x.mean()),
                      "min": x.min(), "mediana": np.median(x), "max": x.max()}).round(5)


def ag_vs_aleatoria(resultados_ag, fitness_fn, n_genes, seeds=None):
    """Compara cada corrida del AG contra una búsqueda aleatoria con el MISMO
    número de evaluaciones y la misma semilla.

    Métricas: fitness final de cada método, test de Mann-Whitney U unilateral
    (H1: AG > aleatoria) y A12 de Vargha-Delaney (P(AG > aleatoria); 0.5 = empate,
    >0.71 = efecto grande)."""
    seeds = seeds if seeds is not None else range(len(resultados_ag))
    filas, curvas = [], []
    for s, r in zip(seeds, resultados_ag):
        presupuesto = int(r["historial"]["evaluaciones"][-1])
        b = busqueda_aleatoria(fitness_fn, n_genes, presupuesto, seed=10_000 + s)
        filas += [{"metodo": "AG", "semilla": s, "fitness": r["mejor_fit"], "evaluaciones": presupuesto},
                  {"metodo": "Aleatoria", "semilla": s, "fitness": b["mejor_fit"], "evaluaciones": presupuesto}]
        curvas.append(b["curva"])
    df = pd.DataFrame(filas)
    ag = df.query("metodo=='AG'")["fitness"].to_numpy()
    al = df.query("metodo=='Aleatoria'")["fitness"].to_numpy()
    u = stats.mannwhitneyu(ag, al, alternative="greater")
    a12 = (np.sum(ag[:, None] > al[None, :]) + 0.5 * np.sum(ag[:, None] == al[None, :])) / (len(ag) * len(al))
    prueba = {"media_AG": ag.mean(), "media_aleatoria": al.mean(),
              "mejora_%": 100 * (ag.mean() - al.mean()) / abs(al.mean()),
              "U": float(u.statistic), "p_valor": float(u.pvalue), "A12": float(a12),
              "AG_gana_en": f"{int(np.sum(ag > al))}/{len(ag)} semillas"}
    return df, prueba, curvas


# ----------------------------------------------------------------- gráficos
def _guardar(fig, carpeta, nombre):
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)
        fig.savefig(os.path.join(carpeta, nombre), dpi=130, bbox_inches="tight")


def graficar_boxplot(df_comp, carpeta=None):
    fig, ax = plt.subplots(figsize=(5.5, 4))
    grupos = [df_comp.query("metodo==@m")["fitness"] for m in ("AG", "Aleatoria")]
    ax.boxplot(grupos, tick_labels=["AG", "Búsqueda aleatoria"], widths=0.5)
    for i, g in enumerate(grupos, 1):
        ax.scatter(np.full(len(g), i) + np.random.default_rng(0).uniform(-.08, .08, len(g)),
                   g, s=18, alpha=0.7, zorder=3)
    ax.set(title=f"Fitness final en {len(grupos[0])} semillas (mismo presupuesto)", ylabel="fitness")
    ax.grid(alpha=0.3, axis="y")
    _guardar(fig, carpeta, "rol5_boxplot_ag_vs_aleatoria.png")
    return fig


def graficar_curvas_vs_baseline(resultados_ag, curvas_aleatorias, carpeta=None):
    """Mejor fitness vs nº de evaluaciones (eje común justo para ambos métodos)."""
    fig, ax = plt.subplots(figsize=(7, 4))
    for i, r in enumerate(resultados_ag):
        h = r["historial"]
        ax.plot(h["evaluaciones"], np.maximum.accumulate(h["max"]), color="C0",
                alpha=0.6, label="AG" if i == 0 else None)
    for i, c in enumerate(curvas_aleatorias):
        ax.plot(np.arange(1, len(c) + 1), c, color="C1", alpha=0.6,
                label="Aleatoria" if i == 0 else None)
    ax.set(title="Mejor fitness vs evaluaciones", xlabel="evaluaciones de fitness", ylabel="mejor fitness")
    ax.grid(alpha=0.3); ax.legend()
    _guardar(fig, carpeta, "rol5_curvas_ag_vs_aleatoria.png")
    return fig


# ------------------------------------------------------- sensibilidad (tornado)
def _set(cfg, clave, valor):
    """Asigna claves anidadas con punto: 'operadores.sigma'."""
    d = cfg
    partes = clave.split(".")
    for p in partes[:-1]:
        d = d.setdefault(p, {})
    d[partes[-1]] = valor


def sensibilidad_hiperparametros(ag_fn, config_base, fitness_fn, factores, seeds=range(3)):
    """Tornado de hiperparámetros: cada factor se lleva a su valor bajo y alto
    (los demás quedan en la base) y se mide el fitness final medio.
    factores = {"poblacion": (10, 60), "operadores.pm": (0.01, 0.3), ...}"""
    def medir(cfg):
        return float(np.mean([ag_fn(cfg, fitness_fn, s)["mejor_fit"] for s in seeds]))

    base = medir(copy.deepcopy(config_base))
    filas = []
    for clave, (bajo, alto) in factores.items():
        valores = {}
        for etiqueta, v in (("bajo", bajo), ("alto", alto)):
            cfg = copy.deepcopy(config_base)
            _set(cfg, clave, v)
            valores[etiqueta] = medir(cfg)
        filas.append({"factor": clave, "valor_bajo": bajo, "valor_alto": alto,
                      "fitness_bajo": valores["bajo"], "fitness_alto": valores["alto"],
                      "base": base, "rango": abs(valores["alto"] - valores["bajo"])})
    return pd.DataFrame(filas).sort_values("rango", ascending=False).reset_index(drop=True)


def sensibilidad_genes(fitness_fn, x, nombres, delta=0.2):
    """Tornado de genes: alrededor del mejor individuo x, mueve cada gen ±delta
    y mide el fitness. Muestra qué genes del cromosoma pesan más."""
    base = fitness_fn(x)
    filas = []
    for i, n in enumerate(nombres):
        lo, hi = x.copy(), x.copy()
        lo[i] = max(0.0, x[i] - delta); hi[i] = min(1.0, x[i] + delta)
        fb, fa = fitness_fn(lo), fitness_fn(hi)
        filas.append({"factor": n, "valor_bajo": round(lo[i], 3), "valor_alto": round(hi[i], 3),
                      "fitness_bajo": fb, "fitness_alto": fa, "base": base,
                      "rango": max(abs(fa - base), abs(fb - base))})
    return pd.DataFrame(filas).sort_values("rango", ascending=False).reset_index(drop=True)


def graficar_tornado(df, titulo="Análisis de sensibilidad", carpeta=None, nombre="rol5_tornado.png"):
    df = df.iloc[::-1]  # el más sensible arriba
    base = df["base"].iloc[0]
    fig, ax = plt.subplots(figsize=(7, 0.45 * len(df) + 1.5))
    y = np.arange(len(df))
    ax.barh(y + 0.2, df["fitness_bajo"] - base, left=base, height=0.4, color="C3", label="valor bajo")
    ax.barh(y - 0.2, df["fitness_alto"] - base, left=base, height=0.4, color="C0", label="valor alto")
    ax.axvline(base, color="k", lw=1)
    ax.set_yticks(y, [f"{f}  ({b} / {a})" for f, b, a in
                      zip(df["factor"], df["valor_bajo"], df["valor_alto"])])
    ax.set(title=titulo, xlabel="fitness final (línea = configuración base)")
    ax.legend(loc="lower right"); ax.grid(alpha=0.3, axis="x")
    _guardar(fig, carpeta, nombre)
    return fig


# ------------------------------------------------------ comparación auditiva
def espectrograma_db(y, sr):
    f, t, Z = stft(y, fs=sr, nperseg=1024, noverlap=768)
    db = 20 * np.log10(np.abs(Z) + 1e-10)
    return f, t, np.maximum(db - db.max(), -80)


def comparacion_auditiva(audios: dict, sr=22050, carpeta=None, fmax=5000):
    """audios = {"Silbido": y, "Gen 0": y, "Referencia": y, "Mejor evolucionado": y}
    Muestra un reproductor por audio (en Jupyter) y sus espectrogramas lado a lado."""
    try:
        from IPython.display import Audio, display, Markdown
        for n, y in audios.items():
            display(Markdown(f"**{n}**")); display(Audio(y, rate=sr))
    except ImportError:
        pass
    fig, ejes = plt.subplots(1, len(audios), figsize=(4 * len(audios), 3.4), sharey=True)
    ejes = np.atleast_1d(ejes)
    for ax, (n, y) in zip(ejes, audios.items()):
        f, t, db = espectrograma_db(y, sr)
        m = f <= fmax
        ax.pcolormesh(t, f[m], db[m], shading="auto", cmap="magma", vmin=-80, vmax=0)
        ax.set(title=n, xlabel="tiempo (s)")
    ejes[0].set_ylabel("frecuencia (Hz)")
    fig.tight_layout()
    _guardar(fig, carpeta, "rol5_espectrogramas.png")
    return fig


# --------------------------------------------------------- encuesta informal
PREGUNTAS = [
    ("instrumento", "¿Qué instrumento escuchas? (piano / flauta / violín / guitarra / otro)"),
    ("melodia_1a5", "¿Reconoces la melodía del silbido? 1 = nada, 5 = totalmente"),
    ("parecido_1a5", "¿Qué tan parecido suena al instrumento real (Referencia)? 1 = nada, 5 = igual"),
]


def crear_encuesta(rutas_audios: dict, carpeta="results/encuesta", seed=0):
    """Encuesta CIEGA: renombra los audios a clips A, B, C... en orden aleatorio
    (la clave queda en clave.json, no se le muestra al encuestado) y genera la
    plantilla respuestas.csv para llenar con 5–10 personas.
    rutas_audios = {"Gen 0": "results/audios/gen0.wav", "Mejor evolucionado": ...}"""
    import shutil
    os.makedirs(carpeta, exist_ok=True)
    nombres = list(rutas_audios)
    orden = np.random.default_rng(seed).permutation(len(nombres))
    clave = {}
    for letra, i in zip("ABCDEFGH", orden):
        destino = os.path.join(carpeta, f"clip_{letra}.wav")
        shutil.copy(rutas_audios[nombres[i]], destino)
        clave[letra] = nombres[i]
    with open(os.path.join(carpeta, "clave.json"), "w", encoding="utf-8") as fh:
        json.dump(clave, fh, ensure_ascii=False, indent=2)
    filas = [{"persona": f"P{p}", "clip": c, **{k: "" for k, _ in PREGUNTAS}}
             for p in range(1, 11) for c in sorted(clave)]
    pd.DataFrame(filas).to_csv(os.path.join(carpeta, "respuestas.csv"), index=False)
    with open(os.path.join(carpeta, "instrucciones.md"), "w", encoding="utf-8") as fh:
        fh.write("# Encuesta informal (5–10 personas)\n\nEscucha primero `Referencia` "
                 "(el instrumento real) y el silbido original. Luego escucha cada clip "
                 "(A, B, C…) sin saber cuál es cuál y responde:\n\n"
                 + "\n".join(f"- **{k}**: {q}" for k, q in PREGUNTAS)
                 + "\n\nAnota las respuestas en `respuestas.csv` (una fila por persona y clip). "
                 "Borra las filas de personas que no participaron.\n")
    return clave


def analizar_encuesta(carpeta="results/encuesta", instrumento_objetivo="piano"):
    """Lee respuestas.csv + clave.json -> tabla por audio y conclusión en texto."""
    with open(os.path.join(carpeta, "clave.json"), encoding="utf-8") as fh:
        clave = json.load(fh)
    df = pd.read_csv(os.path.join(carpeta, "respuestas.csv"), dtype={"instrumento": str})
    df = df.dropna(subset=["melodia_1a5"])
    if df.empty:
        return None, "Encuesta aún sin respuestas: llena results/encuesta/respuestas.csv"
    df["audio"] = df["clip"].map(clave)
    df["acierta_instrumento"] = df["instrumento"].str.strip().str.lower() == instrumento_objetivo.lower()
    tabla = df.groupby("audio").agg(
        personas=("persona", "nunique"),
        reconoce_instrumento_pct=("acierta_instrumento", lambda s: 100 * s.mean()),
        melodia_media=("melodia_1a5", "mean"), parecido_media=("parecido_1a5", "mean"),
    ).round(2).sort_values("parecido_media", ascending=False)
    lineas = [f"Participaron {df['persona'].nunique()} personas (encuesta ciega)."]
    if {"Mejor evolucionado", "Gen 0"} <= set(tabla.index):
        m, g = tabla.loc["Mejor evolucionado"], tabla.loc["Gen 0"]
        lineas.append(
            f"El mejor evolucionado fue identificado como {instrumento_objetivo} por el "
            f"{m.reconoce_instrumento_pct:.0f}% (Gen 0: {g.reconoce_instrumento_pct:.0f}%), "
            f"parecido medio {m.parecido_media:.1f}/5 vs {g.parecido_media:.1f}/5 y melodía "
            f"reconocible {m.melodia_media:.1f}/5.")
    return tabla, " ".join(lineas)
