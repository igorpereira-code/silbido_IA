"""Pruebas de síntesis, métricas e integración del Rol 2 (pytest)."""
import numpy as np
import pytest
from src import rol2_fitness as r2
from src import _provisional


def gen_prueba():
    return {**{f"amp_h{h}": 1 / h for h in range(1, 9)},
            "ataque": .01, "decaimiento": .2, "sostenido": .3,
            "liberacion": .1, "vib_frec": 0., "vib_prof": 0.}


def test_sintesis_duracion_limites_y_reproducibilidad():
    args = ([60, None, 69], [.2, .1, .3], gen_prueba())
    y = r2.sintetizar_instrumento(*args)
    assert y.shape == (sum(int(d * r2.SR) for d in args[1]),)
    assert np.all(np.isfinite(y)) and np.max(np.abs(y)) <= 1
    assert np.array_equal(y, r2.sintetizar_instrumento(*args))
    assert y[0] == y[-1] == 0
    assert np.all(y[4410:6615] == 0)


def test_vacio_corto_y_silencio():
    g = gen_prueba()
    assert r2.sintetizar_instrumento([], [], g).size == 0
    for dur in [0, 1 / r2.SR, 2 / r2.SR, .001]:
        y = r2.sintetizar_instrumento([69], [dur], g)
        assert np.all(np.isfinite(y))
    for h in range(1, 9):
        g[f"amp_h{h}"] = 0
    x = r2.rol1.codificar(g)
    assert r2.fitness(x) == r2.fitness_croma(x) == 0


def test_no_aliasing_sobre_nyquist():
    assert np.all(r2.sintetizar_instrumento([127], [.1], gen_prueba(), sr=8000) == 0)


def test_fundamental_correcta():
    g = gen_prueba()
    for h in range(2, 9):
        g[f"amp_h{h}"] = 0
    y = r2.sintetizar_instrumento([69], [1.0], g)
    pico = np.fft.rfftfreq(len(y), 1 / r2.SR)[np.argmax(np.abs(np.fft.rfft(y)))]
    assert abs(pico - 440) < 2


def test_referencia_sintetica_da_uno(monkeypatch):
    x = r2.rol1.codificar(gen_prueba())
    y = r2.sintetizar_instrumento([69], [r2.DURACION_REFERENCIA], r2.rol1.decodificar(x))
    mag = r2._magnitud(y)
    monkeypatch.setattr(r2, "REF_DB", r2._a_db(mag))
    monkeypatch.setattr(r2, "REF_CROMA", r2._croma(mag))
    assert r2.fitness(x) == pytest.approx(1.0)
    assert r2.fitness_croma(x) == pytest.approx(1.0)
    otro = np.random.default_rng(2).random(len(x))
    assert r2.fitness(otro) < r2.fitness(x)


def test_referencia_real_y_no_lectura_por_evaluacion(monkeypatch):
    assert r2.REFERENCIA.shape == (22050,)
    def prohibido(*args, **kwargs):
        raise AssertionError("No se debe leer el WAV en cada evaluación")
    monkeypatch.setattr(r2.sf, "read", prohibido)
    rng = np.random.default_rng(1)
    for x in [np.zeros(14), np.ones(14), *rng.random((20, 14))]:
        for fn in [r2.fitness, r2.fitness_croma]:
            assert 0 <= fn(x) <= 1
            assert fn(x) == fn(x)


@pytest.mark.parametrize("x", [np.zeros(13), np.full(14, np.nan), np.full(14, 1.1)])
def test_cromosomas_invalidos(x):
    with pytest.raises(ValueError):
        r2.fitness(x)


@pytest.mark.parametrize("notas,durs", [([69], []), ([69], [-1]), ([69], [np.nan]), ([128], [.1])])
def test_melodias_invalidas(notas, durs):
    with pytest.raises(ValueError):
        r2.sintetizar_instrumento(notas, durs, gen_prueba())


def test_integracion_ag_existente():
    config = {"poblacion": 6, "n_genes": 14, "generaciones": 2, "elitismo": 1}
    for fn in [r2.fitness, r2.fitness_croma]:
        res = _provisional.ejecutar_ag(config, fn, seed=5)
        assert res["mejor"].shape == (14,)
        assert res["mejor_fit"] == fn(res["mejor"])
        assert np.all(np.diff(res["historial"]["max"]) >= 0)
