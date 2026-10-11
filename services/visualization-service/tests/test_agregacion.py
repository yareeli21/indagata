"""Tests unitarios de app/core/agregacion.py (diseño §10 unit)."""
from __future__ import annotations

import math

from app.core.agregacion import (
    HallazgoDimension,
    ResumenItem,
    _num,
    agregar_categorica,
    agregar_likert,
    agregar_numerica,
    redactar_hallazgo,
    redactar_resumen_global,
)


def _r(**answers) -> dict:
    return {"answers": dict(answers)}


# ── _num ────────────────────────────────────────────────────────────────────
def test_num_excluye_bool():
    assert _num(True) is None
    assert _num(False) is None


def test_num_acepta_int_float_y_str_con_coma():
    assert _num(4) == 4.0
    assert _num(3.5) == 3.5
    assert _num("4") == 4.0
    assert _num("3,5") == 3.5
    assert _num("  2 ") == 2.0


def test_num_rechaza_str_no_numerico():
    assert _num("hola") is None
    assert _num(None) is None
    assert _num([1]) is None


# ── agregar_likert ──────────────────────────────────────────────────────────
def test_agregar_likert_media_de_y_pct_alto():
    items = [("q1", "Ítem uno", 1, 5), ("q2", "Ítem dos", 1, 5)]
    respondents = [
        _r(q1=5, q2=5),
        _r(q1=4, q2=4),
        _r(q1=3, q2=1),
    ]
    h = agregar_likert(items, respondents, "Motivación")
    assert h is not None
    assert h.n == 3
    # vector = [5,5,4,4,3,1] -> media 3.6667, de poblacional
    vector = [5, 5, 4, 4, 3, 1]
    assert math.isclose(h.media, sum(vector) / len(vector), rel_tol=1e-9)
    # pct_alto: umbral tercio superior 1..5 = 1 + 2*4/3 = 3.6667 -> valores >= 3.667: 5,5,4,4 = 4/6
    assert math.isclose(h.pct_alto, 4 / 6 * 100.0, rel_tol=1e-9)
    # item más alto = q1 (media 4), más bajo = q2 (media 3.3333)
    assert h.item_mas_alto.question_id == "q1"
    assert h.item_mas_bajo.question_id == "q2"


def test_agregar_likert_todos_none_devuelve_none():
    items = [("q1", "Ítem uno", 1, 5)]
    respondents = [_r(q1=None), _r(q1="x"), _r(q1=True)]
    assert agregar_likert(items, respondents, "Dim") is None


def test_agregar_likert_un_solo_respondente():
    items = [("q1", "Ítem uno", 1, 5)]
    h = agregar_likert(items, [_r(q1=4)], "Dim")
    assert h is not None
    assert h.n == 1
    assert h.media == 4.0
    assert h.de == 0.0


def test_agregar_likert_escala_no_1_5_umbral_tercio_superior():
    # escala 0..10, umbral = 0 + 2*10/3 = 6.6667
    items = [("q1", "Ítem", 0, 10)]
    respondents = [_r(q1=10), _r(q1=7), _r(q1=5), _r(q1=0)]
    h = agregar_likert(items, respondents, "Dim")
    assert h is not None
    # valores >= 6.667: 10 y 7 -> 2/4
    assert math.isclose(h.pct_alto, 2 / 4 * 100.0, rel_tol=1e-9)


def test_agregar_likert_str_con_coma_decimal():
    items = [("q1", "Ítem", 1, 5)]
    h = agregar_likert([("q1", "Ítem", 1, 5)], [_r(q1="4,5"), _r(q1="3,5")], "Dim")
    assert h is not None
    assert math.isclose(h.media, 4.0, rel_tol=1e-9)


# ── agregar_numerica ──────────────────────────────────────────────────────────
def test_agregar_numerica():
    respondents = [_r(q6=3.0), _r(q6=1.5), _r(q6=4.0)]
    h = agregar_numerica("q6", "GPA", respondents)
    assert h is not None
    assert h.n == 3
    assert h.minimo == 1.5
    assert h.maximo == 4.0


def test_agregar_numerica_sin_valores_devuelve_none():
    assert agregar_numerica("q6", "GPA", [_r(q6=None), _r(q6="x")]) is None


# ── agregar_categorica ──────────────────────────────────────────────────────
def test_agregar_categorica_distribucion():
    respondents = [
        _r(q=" privada "),
        _r(q="privada"),
        _r(q="pública"),
        _r(q=""),
        _r(q=None),
    ]
    h = agregar_categorica("q", "tipo de universidad", "opcion_multiple", respondents)
    assert h is not None
    assert h.n == 3
    categorias = dict(h.distribucion)
    assert math.isclose(categorias["privada"], 2 / 3 * 100.0, rel_tol=1e-9)


def test_agregar_categorica_binaria_si_no():
    respondents = [_r(q="True"), _r(q="False"), _r(q="True")]
    h = agregar_categorica("q", "trabaja", "binaria", respondents)
    assert h is not None
    categorias = dict(h.distribucion)
    assert "sí" in categorias
    assert "no" in categorias


def test_agregar_categorica_vacio_devuelve_none():
    assert agregar_categorica("q", "x", "opcion_multiple", [_r(q=""), _r(q=None)]) is None


# ── redacción ────────────────────────────────────────────────────────────────
def test_redactar_hallazgo_likert_formato_espanol():
    h = HallazgoDimension(
        dimension="Motivación",
        tipo="likert",
        n=180,
        media=4.12,
        de=0.83,
        pct_alto=72.0,
        item_mas_alto=ResumenItem("q3", "Me esfuerzo más", 4.4, 0.5, 180),
        item_mas_bajo=ResumenItem("q2", "Encuentro significativo", 3.6, 0.6, 180),
    )
    texto = redactar_hallazgo(h)
    assert "Motivación" in texto
    assert "4.1/5" in texto  # 1 decimal
    assert "DE 0.8" in texto
    assert "72 %" in texto  # porcentaje entero
    assert "n = 180 respondentes." in texto
    assert "nan" not in texto


def test_redactar_hallazgo_numerica():
    h = HallazgoDimension(
        dimension="GPA", tipo="numerica", n=180, media=3.14, de=0.5, minimo=1.5, maximo=4.0
    )
    texto = redactar_hallazgo(h)
    assert "3.1" in texto
    assert "mínimo 1.5" in texto
    assert "máximo 4.0" in texto


def test_redactar_hallazgo_categorica():
    h = HallazgoDimension(
        dimension="tipo de universidad",
        tipo="categorica",
        n=180,
        distribucion=[("privada", 54.0), ("pública", 33.0), ("mixta", 13.0)],
    )
    texto = redactar_hallazgo(h)
    assert "54 %" in texto
    assert "n = 180" in texto


def test_redactar_resumen_global_sin_likert_ni_numericas():
    hallazgos = [
        HallazgoDimension(dimension="tipo", tipo="categorica", n=10, distribucion=[("a", 100.0)])
    ]
    texto = redactar_resumen_global(hallazgos, 10, "Instrumento X")
    assert "10 respondentes" in texto
    assert "media más alta" not in texto
    assert "nan" not in texto


def test_redactar_resumen_global_hallazgos_vacio():
    texto = redactar_resumen_global([], 42, "Instrumento X")
    assert "42 respondentes" in texto
    assert "No se registraron dimensiones" in texto
    assert "nan" not in texto


def test_redactar_resumen_global_con_likert_y_numerica():
    hallazgos = [
        HallazgoDimension(dimension="A", tipo="likert", n=5, media=4.5, de=0.1),
        HallazgoDimension(dimension="B", tipo="likert", n=5, media=2.1, de=0.2),
        HallazgoDimension(dimension="GPA", tipo="numerica", n=5, media=3.0, de=0.3),
    ]
    texto = redactar_resumen_global(hallazgos, 5, "Inst")
    assert "más alta fue A" in texto
    assert "más baja B" in texto
    assert "GPA" in texto
