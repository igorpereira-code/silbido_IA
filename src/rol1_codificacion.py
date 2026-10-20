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
extraer_notas: silbido .wav -> (notas MIDI, duraciones en s)   [pendiente]
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