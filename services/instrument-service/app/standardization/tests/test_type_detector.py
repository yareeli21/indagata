"""Tabla de casos del detector de tipos (diseño §1.3)."""
from __future__ import annotations

from app.parsing.raw_table import RawTable
from app.standardization import type_detector as td


def _detectar_una(header: str, valores: list[str]) -> td.TipoPreguntaDetectado:
    tabla = RawTable(headers=[header], rows=[[v] for v in valores])
    return td.detectar_tipos(tabla)[0]


def test_binaria_si_no():
    d = _detectar_una("¿Trabajas?", ["Sí", "No", "No", "Sí"])
    assert d.type == td.TIPO_BINARIA
    assert d.confianza == td.CONFIANZA_ALTA


def test_binaria_0_1():
    d = _detectar_una("activo", ["0", "1", "1", "0"])
    assert d.type == td.TIPO_BINARIA


def test_likert_1_5():
    d = _detectar_una("claridad", ["1", "2", "3", "4", "5", "3", "2"])
    assert d.type == td.TIPO_LIKERT
    assert d.scale_min == 1
    assert d.scale_max == 5
    assert d.options == ["1", "2", "3", "4", "5"]


def test_likert_no_arranca_en_uno_es_numerica():
    # Rango 2..6 no arranca en 1 -> no es likert; enteros -> numerica_continua.
    d = _detectar_una("puntaje", ["2", "3", "4", "5", "6"])
    assert d.type == td.TIPO_NUMERICA_CONTINUA


def test_numerica_continua_floats():
    d = _detectar_una("promedio", ["7.5", "8.2", "9.1", "6.4"])
    assert d.type == td.TIPO_NUMERICA_CONTINUA


def test_numerica_rango_mayor_a_7():
    d = _detectar_una("edad", ["18", "22", "30", "45", "19", "27"])
    assert d.type == td.TIPO_NUMERICA_CONTINUA


def test_opcion_multiple():
    valores = ["15-29", "30-49", "15-29", "50-79", "15-29", "30-49", "No sé", "50-79"]
    d = _detectar_una("tamaño", valores)
    assert d.type == td.TIPO_OPCION_MULTIPLE
    # Opciones ordenadas por frecuencia descendente: "15-29" es la más frecuente.
    assert d.options[0] == "15-29"
    assert set(d.options) == {"15-29", "30-49", "50-79", "No sé"}


def test_abierta_alta_cardinalidad():
    valores = [f"respuesta libre número {i}" for i in range(20)]
    d = _detectar_una("comentario", valores)
    assert d.type == td.TIPO_ABIERTA
    assert d.confianza == td.CONFIANZA_BAJA


def test_columna_vacia_es_abierta_con_nota():
    d = _detectar_una("q9", ["", "", ""])
    assert d.type == td.TIPO_ABIERTA
    assert d.confianza == td.CONFIANZA_BAJA
    assert d.notas


def test_es_demografica_por_diccionario():
    d = _detectar_una("Edad", ["18", "22", "30", "45", "19", "27"])
    assert d.es_demografica is True


def test_no_demografica():
    d = _detectar_una("claridad", ["1", "2", "3", "4", "5"])
    assert d.es_demografica is False


def test_orden_y_question_ids_estables():
    tabla = RawTable(
        headers=["edad", "claridad", "comentario"],
        rows=[
            ["18", "1", "texto a"],
            ["22", "5", "texto b"],
            ["30", "3", "texto c"],
        ],
    )
    detectados = td.detectar_tipos(tabla)
    assert [p.question_id for p in detectados] == ["q1", "q2", "q3"]
    assert [p.text for p in detectados] == ["edad", "claridad", "comentario"]
