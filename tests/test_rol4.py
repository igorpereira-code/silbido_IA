"""Tests del Rol 4. Ejecutar:  python -m pytest tests -q   (o python tests/test_rol4.py)

Se usa un fitness de juguete (rápido, con óptimo conocido) para probar el ciclo del AG
sin depender del fitness real del Rol 2.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from src import rol3_operadores as op
from src import rol4_ag as ag

D = 6
OBJETIVO = np.linspace(0.2, 0.8, D)


def fit_toy(x):
    """Mayor = mejor. Máximo = 1.0 en OBJETIVO."""
    return float(1.0 - np.mean(np.abs(x - OBJETIVO)))


C3 = op.COMBINACIONES["C3 Balance (torneo + blend α=0.5 + no-uniforme)"]


def _cfg(**kw):
    base = {"poblacion": 20, "n_genes": D, "generaciones": 15, "elitismo": 2, "operadores": C3}
    base.update(kw)
    return base


def test_formato_del_resultado():
    r = ag.ejecutar_ag(_cfg(), fit_toy, 0)
    assert {"mejor", "mejor_fit", "mejor_gen0", "historial"} <= set(r)
    assert r["mejor"].shape == (D,) and r["mejor_gen0"].shape == (D,)
    h = r["historial"]
    assert set(h) == set(ag.CLAVES_HISTORIAL)
    assert all(len(h[k]) == 16 for k in h)            # generaciones 0..15


def test_evaluaciones_acumuladas():
    n, e, T = 20, 2, 15
    h = ag.ejecutar_ag(_cfg(poblacion=n, elitismo=e, generaciones=T), fit_toy, 1)["historial"]["evaluaciones"]
    assert h[0] == n
    assert h[-1] == n + T * (n - e)                    # presupuesto que usa el baseline del Rol 5
    assert all(b > a for a, b in zip(h, h[1:]))        # estrictamente creciente


def test_cuenta_real_de_llamadas_a_fitness():
    llamadas = []
    def contado(x):
        llamadas.append(1); return fit_toy(x)
    r = ag.ejecutar_ag(_cfg(), contado, 2)
    assert len(llamadas) == r["historial"]["evaluaciones"][-1]


def test_reproducible_con_semilla():
    a = ag.ejecutar_ag(_cfg(), fit_toy, 7)
    b = ag.ejecutar_ag(_cfg(), fit_toy, 7)
    c = ag.ejecutar_ag(_cfg(), fit_toy, 8)
    assert np.array_equal(a["mejor"], b["mejor"]) and a["historial"] == b["historial"]
    assert not np.array_equal(a["mejor"], c["mejor"])


def test_mismo_gen0_con_misma_semilla_y_distintos_operadores():
    a = ag.ejecutar_ag(_cfg(operadores=op.COMBINACIONES[list(op.COMBINACIONES)[0]]), fit_toy, 3)
    b = ag.ejecutar_ag(_cfg(operadores=op.COMBINACIONES[list(op.COMBINACIONES)[1]]), fit_toy, 3)
    assert np.array_equal(a["mejor_gen0"], b["mejor_gen0"])
    assert a["historial"]["max"][0] == b["historial"]["max"][0]


def test_elitismo_nunca_empeora_el_maximo():
    for e in (1, 2, 6):
        mx = ag.ejecutar_ag(_cfg(elitismo=e), fit_toy, 4)["historial"]["max"]
        assert all(b >= a - 1e-12 for a, b in zip(mx, mx[1:])), e


def test_mejor_historico_con_elitismo_cero():
    r = ag.ejecutar_ag(_cfg(elitismo=0, generaciones=30), fit_toy, 5)
    assert r["mejor_fit"] >= max(r["historial"]["max"]) - 1e-12
    assert abs(fit_toy(r["mejor"]) - r["mejor_fit"]) < 1e-12


def test_individuos_siempre_validos():
    r = ag.ejecutar_ag(_cfg(), fit_toy, 6)
    for x in (r["mejor"], r["mejor_gen0"], *r["poblacion_final"]):
        assert np.all((x >= 0) & (x <= 1))


def test_el_ag_mejora_y_se_acerca_al_optimo():
    r = ag.ejecutar_ag(_cfg(poblacion=30, generaciones=60), fit_toy, 0)
    assert r["mejor_fit"] > fit_toy(r["mejor_gen0"])
    assert r["mejor_fit"] > 0.97


def test_parada_por_estancamiento():
    constante = lambda x: 0.5                              # nunca mejora
    r = ag.ejecutar_ag(_cfg(generaciones=100, paciencia=5), constante, 0)
    assert r["motivo_parada"] == "estancamiento" and r["gen_final"] == 5
    assert len(r["historial"]["max"]) == 6                 # gen 0 + 5 generaciones
    r2 = ag.ejecutar_ag(_cfg(generaciones=10), constante, 0)
    assert r2["motivo_parada"] == "generaciones" and r2["gen_final"] == 10


def test_inmigrantes_se_cuentan_en_las_evaluaciones():
    cfg = _cfg(generaciones=5, inmigrantes={"umbral": 2.0, "fraccion": 0.25})   # umbral 2.0: siempre se activa
    r = ag.ejecutar_ag(cfg, fit_toy, 0)
    m = round(0.25 * 20)
    assert r["inmigraciones"] == [1, 2, 3, 4, 5]
    assert r["historial"]["evaluaciones"][-1] == 20 + 5 * (20 - 2) + 5 * m
    llamadas = []
    ag.ejecutar_ag(cfg, lambda x: (llamadas.append(1), fit_toy(x))[1], 0)
    assert len(llamadas) == r["historial"]["evaluaciones"][-1]


def test_inmigrantes_no_pierden_al_mejor():
    cfg = _cfg(generaciones=20, inmigrantes={"umbral": 2.0, "fraccion": 0.9})
    mx = ag.ejecutar_ag(cfg, fit_toy, 0)["historial"]["max"]
    assert all(b >= a - 1e-12 for a, b in zip(mx, mx[1:]))


def test_sin_opciones_reproduce_el_ciclo_provisional():
    """Con la config básica el ciclo es el mismo que usaron los Roles 3 y 5 (provisional)."""
    from src import _provisional as prov
    cfg = _cfg()
    a, b = ag.ejecutar_ag(cfg, fit_toy, 11), prov.ejecutar_ag(cfg, fit_toy, 11)
    assert np.array_equal(a["mejor"], b["mejor"]) and a["mejor_fit"] == b["mejor_fit"]
    for k in ag.CLAVES_HISTORIAL:
        assert np.allclose(a["historial"][k], b["historial"][k])


def test_config_invalida():
    for malo in ({"elitismo": 20}, {"elitismo": -1}, {"poblacion": 1}, {"generaciones": 0}, {"paciencia": 0}):
        try:
            ag.ejecutar_ag(_cfg(**malo), fit_toy, 0)
        except ValueError:
            continue
        raise AssertionError(f"debió fallar con {malo}")
    try:
        ag.ejecutar_ag({"poblacion": 10, "generaciones": 5}, fit_toy, 0)
    except KeyError:
        pass
    else:
        raise AssertionError("debió fallar sin n_genes")


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f(); print("OK", n)
