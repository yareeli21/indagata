"""Contrato de formatos de encuestas (shared/parsing): exportes de plataformas y rechazos."""
from __future__ import annotations

import json

from shared.parsing import read_tabular
from shared.parsing.formato import es_codigo, motivo_rechazo_encuesta

_TEXTOS = ["Los criterios de evaluación se explican con claridad", "Me siento seguro dentro de la escuela"]


def test_qualtrics_usa_la_fila_del_texto_y_descarta_importid():
    filas = [
        ["StartDate", "IPAddress", "Q1", "Q2"],
        ["Start Date", "IP Address", *_TEXTOS],
        [json.dumps({"ImportId": "startDate"}), json.dumps({"ImportId": "ipAddress"}),
         json.dumps({"ImportId": "QID1"}), json.dumps({"ImportId": "QID2"})],
        ["2026-10-01 10:00:00", "10.0.0.1", "4", "5"],
        ["2026-10-01 11:00:00", "10.0.0.2", "3", "2"],
    ]
    csv = "\n".join(",".join(f'"{c.replace(chr(34), chr(34) * 2)}"' for c in f) for f in filas).encode("utf-8")
    tabla = read_tabular(csv, ".csv")
    assert tabla.headers == ["Start Date", "IP Address", *_TEXTOS]
    assert tabla.rows == [["2026-10-01 10:00:00", "10.0.0.1", "4", "5"], ["2026-10-01 11:00:00", "10.0.0.2", "3", "2"]]
    assert any("Qualtrics" in n for n in tabla.notes)


def test_un_csv_normal_no_cambia():
    tabla = read_tabular("turno,P1\nMatutino,4\n".encode("utf-8"), ".csv")
    assert tabla.headers == ["turno", "P1"] and tabla.rows == [["Matutino", "4"]]


def test_codigos_reconocidos():
    for c in ("P1", "Q12_3", "G01Q03", "G01Q03[SQ001]", "Evaluación_item3", "item_12", "Reactivo 4"):
        assert es_codigo(c), c
    for t in (*_TEXTOS, "turno", "¿Cuántas horas trabajas a la semana?", "Califica del 1 al 10", "Semestre 5"):
        assert not es_codigo(t), t


def test_codigos_sin_original_se_rechazan_y_con_original_no():
    encabezados = ["id_respondente", "turno", "P1", "P2", "P3"]
    motivo = motivo_rechazo_encuesta(encabezados, [], hay_original=False)
    assert motivo and "instrumento original" in motivo and "P1" in motivo
    assert motivo_rechazo_encuesta(encabezados, [], hay_original=True) is None


def test_texto_completo_sin_original_se_acepta():
    assert motivo_rechazo_encuesta(["Marca temporal", "Turno", *_TEXTOS], [], hay_original=False) is None


def test_formato_largo_se_rechaza():
    motivo = motivo_rechazo_encuesta(["respondente", "pregunta", "respuesta"], [["R1", "P1", "4"]], hay_original=True)
    assert motivo and "formato largo" in motivo


def test_sin_encabezados_se_rechaza():
    motivo = motivo_rechazo_encuesta(["Matutino", "4", "De acuerdo", "3", "5"], [], hay_original=True)
    assert motivo and "encabezados" in motivo
