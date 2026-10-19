"""Tests del Rol 3. Ejecutar:  python -m pytest tests -q   (o python tests/test_rol3.py)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from src import rol3_operadores as op

D = 14


def _pob(n=40, seed=0):
    rng = np.random.default_rng(seed)
    return rng.random((n, D)), rng


def test_hijos_siempre_validos():
    pob, rng = _pob()
    fit = -np.sum((pob - 0.3) ** 2, axis=1)
    for cfg in op.COMBINACIONES.values():
        for t in range(0, 50, 10):
            h = op.reproducir(pob, fit, cfg, t, 50, rng)
            assert h.shape == pob.shape
            assert np.all((h >= 0) & (h <= 1)), cfg


def test_blend_extremos_se_reparan():
    rng = np.random.default_rng(1)
    p1, p2 = np.zeros(D), np.ones(D)
    for _ in range(200):
        h1, h2 = op.cruce_blend(p1, p2, rng, alpha=1.0)
        assert h1.min() >= 0 and h1.max() <= 1 and h2.min() >= 0 and h2.max() <= 1


def test_uniforme_solo_recombina():
    rng = np.random.default_rng(2)
    p1, p2 = np.full(D, .1), np.full(D, .9)
    h1, h2 = op.cruce_uniforme(p1, p2, rng)
    assert set(np.round(h1, 6)) <= {0.1, 0.9}
    assert np.allclose(h1 + h2, 1.0)  # los genes se reparten complementarios


def test_torneo_presion_selectiva():
    pob, rng = _pob(100)
    fit = np.arange(100.0)
    sel = op.seleccion_torneo(pob, fit, 5000, rng, k=3)
    idx = [np.where((pob == s).all(1))[0][0] for s in sel[:2000]]
    # con k=3 la media de rangos esperada es 0.75·n
    assert 70 < np.mean(idx) < 80


def test_ruleta_y_sus_proporcionales():
    rng = np.random.default_rng(3)
    pob = np.eye(3)
    fit = np.array([1.0, 2.0, 3.0])  # desplazado: 0,1,2 -> P = 0, 1/3, 2/3
    for f in (op.seleccion_ruleta, op.seleccion_sus):
        sel = f(pob, fit, 3000, rng)
        frec = sel.mean(0)
        assert np.allclose(frec, [0, 1 / 3, 2 / 3], atol=0.03), (f.__name__, frec)


def test_no_uniforme_paso_decrece():
    rng = np.random.default_rng(4)
    x = np.full(D, 0.5)
    paso_ini = np.mean([np.abs(op.mutacion_no_uniforme(x, rng, 1.0, 0, 100) - x).mean() for _ in range(200)])
    paso_fin = np.mean([np.abs(op.mutacion_no_uniforme(x, rng, 1.0, 95, 100) - x).mean() for _ in range(200)])
    assert paso_fin < paso_ini / 5


def test_reproducible_con_semilla():
    pob, _ = _pob()
    fit = pob.sum(1)
    a = op.reproducir(pob, fit, None, 3, 10, np.random.default_rng(7))
    b = op.reproducir(pob, fit, None, 3, 10, np.random.default_rng(7))
    assert np.array_equal(a, b)


def test_diversidad():
    rng = np.random.default_rng(5)
    assert 0.9 < op.diversidad(rng.random((500, D))) < 1.1
    assert op.diversidad(np.full((50, D), .4)) < 1e-9


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f(); print("OK", n)
