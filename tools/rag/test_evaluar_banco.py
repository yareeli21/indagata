"""Pruebas de las funciones del evaluador del banco (sin la app: datos de ejemplo).

    .venv\\Scripts\\python.exe -m pytest tools/rag/test_evaluar_banco.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evaluar_banco as eb  # noqa: E402

PREGUNTA = {"cifras_clave": ["13.3", "4", "30"], "hechos_clave": ["vespertino"], "aceptables": []}


def test_exacta_compara_cifras_como_numeros_y_hechos_sin_acentos():
    assert eb.exacta("El 13.3 % (4 de 30) del turno Vespertino está de acuerdo. [Fuente 1]", PREGUNTA) is True
    assert eb.exacta("El 13,30 % (4 de 30) del turno vespertino", PREGUNTA) is True  # coma decimal y cero final
    assert eb.exacta("El 23.3 % (4 de 30) del turno vespertino", PREGUNTA) is False  # la cifra inventada del 17 oct
    assert eb.exacta("El 13.3 % del turno vespertino", PREGUNTA) is False  # omitió «4 de 30»


def test_la_cifra_se_compara_con_la_precision_de_la_esperada():
    pregunta = {"cifras_clave": ["27.2"], "hechos_clave": [], "aceptables": []}
    assert eb.exacta("El promedio es de 27.23 horas por semana.", pregunta) is True
    assert eb.exacta("El promedio es de 27.3 horas por semana.", pregunta) is False


def test_los_ids_y_las_citas_no_cuentan_como_cifras():
    pregunta = {"cifras_clave": ["1"], "hechos_clave": [], "aceptables": []}
    assert eb.exacta("Según R001 en p01 [Fuente 1], INS-0012", pregunta) is False


def test_aceptables_basta_una_y_pregunta_sin_nada_verificable():
    pregunta = {"cifras_clave": [], "hechos_clave": [], "aceptables": ["R002", "R012"]}
    assert eb.exacta("El respondente R012 está en desacuerdo en p01, p02 y p03.", pregunta) is True
    assert eb.exacta("El respondente R003 está en desacuerdo.", pregunta) is False
    assert eb.exacta("Lo que sea", {"cifras_clave": [], "hechos_clave": [], "aceptables": []}) is None


def test_recuperacion_hit_y_rango_reciproco():
    contexto = [{"tipo": "resultado", "texto": "x"},
                {"tipo": "fragmento", "instrumentoId": "109", "texto": "Pregunta sobre la beca"},
                {"tipo": "fragmento", "instrumentoId": "109", "texto": "¿Cuál es tu principal medio de transporte?"}]
    r = eb.recuperacion(contexto, [{"instrumentoId": "109", "contiene": "medio de transporte"}])
    assert r == {"hit": True, "rr": 0.5, "k": 2, "rango": 2}  # el resultado calculado no cuenta como fragmento
    assert eb.recuperacion(contexto, [{"instrumentoId": "61", "contiene": "transporte"}])["hit"] is False
    assert eb.recuperacion(contexto, []) is None


def test_f1_macro_y_falsas_aceptaciones():
    pares = [("dentro", "dentro"), ("dentro", "sin_informacion"), ("privacidad", "privacidad"), ("fuera", "fuera")]
    assert 0 < eb._f1_macro(pares) < 1
    assert eb._f1_macro([("dentro", "dentro"), ("fuera", "fuera")]) == 1.0
