"""Capa de interpretación: una prueba por tipo de pregunta, niveles, privacidad y pruebas."""
from __future__ import annotations

import pytest

from conftest import limpieza
from services.interpretacion import encuestas, escalas, pruebas
from services.interpretacion.privacidad import es_dato_personal

ACUERDO = ["Totalmente en desacuerdo", "En desacuerdo", "Ni de acuerdo ni en desacuerdo", "De acuerdo", "Totalmente de acuerdo"]


def _likert(etiquetas=ACUERDO, escala="acuerdo", invertido=False) -> dict:
    return {"tipo_canonico": "likert", "likert": {"escala": escala, "etiquetas": etiquetas, "invertido": invertido}}


# ── Niveles ────────────────────────────────────────────────────────────────────


def test_niveles_por_posicion_y_por_escala():
    assert [escalas.nivel(p, 5, "acuerdo") for p in range(1, 6)] == ["desacuerdo", "desacuerdo", "neutral", "acuerdo", "acuerdo"]
    assert [escalas.nivel(p, 5, "frecuencia") for p in (1, 3, 5)] == ["baja", "media", "alta"]
    # Número par de puntos: sin nivel medio.
    assert [escalas.nivel(p, 4, "acuerdo") for p in range(1, 5)] == ["desacuerdo", "desacuerdo", "acuerdo", "acuerdo"]
    assert [escalas.nivel(p, 7, None) for p in (1, 3, 4, 5, 7)] == ["baja", "baja", "media", "alta", "alta"]
    assert escalas.nivel(6, 5, "acuerdo") is None
    assert escalas.mapa_niveles([1, 2, 3, 4, 5], "acuerdo") == {"desacuerdo": [1, 2], "neutral": [3], "acuerdo": [4, 5]}


# ── Likert y cuadrícula ────────────────────────────────────────────────────────


def test_likert_codigo_a_etiqueta_y_nivel():
    col = encuestas.interpretar_columna(_likert(), ["2", "5", "", "3"])
    assert col.respuestas[0] == {"estado": "respondida", "valor": 2, "significado": "En desacuerdo", "nivel": "desacuerdo"}
    assert col.respuestas[1]["significado"] == "Totalmente de acuerdo" and col.respuestas[1]["nivel"] == "acuerdo"
    assert col.respuestas[2] == {"estado": "sin_respuesta"}  # nunca se omite
    assert col.respuestas[3]["nivel"] == "neutral"
    assert col.escala == {
        "puntos": 5, "etiquetas": {str(i + 1): e for i, e in enumerate(ACUERDO)},
        "niveles": {"desacuerdo": [1, 2], "neutral": [3], "acuerdo": [4, 5]}, "invertida": False,
    }


def test_likert_invertido_conserva_lo_respondido_y_agrega_recodificado():
    col = encuestas.interpretar_columna(_likert(invertido=True), ["1", "4"])
    r = col.respuestas[0]
    assert r["significado"] == "Totalmente en desacuerdo" and r["nivel"] == "desacuerdo" and r["valor_recodificado"] == 5
    assert col.respuestas[1]["valor_recodificado"] == 2 and col.escala["invertida"] is True


def test_likert_numerica_con_y_sin_anclas():
    spec = _likert(etiquetas=["0", "1", "2", "3", "4"], escala="numerica")
    col = encuestas.interpretar_columna(spec, ["0", "4"], anclas={0: "Nunca", 4: "Siempre"})
    assert col.respuestas[0]["significado"] == "Nunca" and col.respuestas[0]["nivel"] == "baja"
    assert col.escala["etiquetas"]["2"] == "2 en escala 0–4" and col.escala["anclas"] == {"0": "Nunca", "4": "Siempre"}
    assert encuestas.interpretar_columna(spec, ["3"]).respuestas[0]["significado"] == "3 en escala 0–4"


def test_no_se_y_no_aplica_se_distinguen_de_las_vacias():
    col = encuestas.interpretar_columna(_likert(), ["No sé", "", "No aplica", "Prefiero no responder", "4"])
    assert col.respuestas[0] == {"estado": "sin_respuesta", "valor": "No sé", "significado": "No sé", "motivo": "no_sabe"}
    assert col.respuestas[1] == {"estado": "sin_respuesta"}  # en blanco: sin motivo
    assert col.respuestas[2]["motivo"] == "no_aplica" and col.respuestas[3]["motivo"] == "prefiere_no_responder"
    assert col.respuestas[4]["nivel"] == "acuerdo" and col.no_interpretadas == 0


def test_cuadricula_se_interpreta_con_su_escala():
    spec = dict(_likert(etiquetas=["Nunca", "Casi nunca", "A veces", "Casi siempre", "Siempre"], escala="frecuencia"), tipo_canonico="cuadricula")
    r = encuestas.interpretar_columna(spec, ["4"]).respuestas[0]
    assert (r["significado"], r["nivel"]) == ("Casi siempre", "alta")


def test_valor_fuera_de_la_escala_queda_no_interpretado():
    col = encuestas.interpretar_columna(_likert(), ["9", "Mucho"])
    assert [r["estado"] for r in col.respuestas] == ["no_interpretada", "no_interpretada"]
    assert col.respuestas[0]["valor"] == "9" and col.no_interpretadas == 2


# ── Opciones ───────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(("valores", "esperado"), [
    (["Sí", "no", "SI", "No"], ["Sí", "No", "Sí", "No"]),
    (["1", "0"], ["Sí", "No"]),
    (["True", "false"], ["Sí", "No"]),
    (["S", "N"], ["Sí", "No"]),
])
def test_binaria_unifica_si_no(valores, esperado):
    col = encuestas.interpretar_columna({"tipo_canonico": "binaria"}, valores)
    assert [r["significado"] for r in col.respuestas] == esperado
    assert {r["nivel"] for r in col.respuestas} == {"si", "no"} and col.opciones == ["Sí", "No"]


def test_binaria_que_no_es_si_no_conserva_la_categoria():
    col = encuestas.interpretar_columna({"tipo_canonico": "binaria"}, ["matutino", "Matutino", "Vespertino", "Matutino"])
    assert [r["significado"] for r in col.respuestas] == ["Matutino", "Matutino", "Vespertino", "Matutino"]
    assert "nivel" not in col.respuestas[0]


def test_categorica_normaliza_la_etiqueta():
    col = encuestas.interpretar_columna({"tipo_canonico": "categorica"}, ["Pedagogía", "  pedagogia ", "Derecho", "PEDAGOGÍA", "Pedagogía", ""])
    assert [r.get("significado") for r in col.respuestas] == ["Pedagogía", "Pedagogía", "Derecho", "Pedagogía", "Pedagogía", None]
    assert col.opciones == ["Pedagogía", "Derecho"] and col.respuestas[1]["valor"] == "pedagogia"


def test_opcion_multiple_lista_de_seleccionadas():
    col = encuestas.interpretar_columna({"tipo_canonico": "opcion_multiple_varias"}, ["Biblioteca, Cafetería", "cafeteria; Gimnasio", "Biblioteca, biblioteca"])
    assert col.respuestas[0]["seleccion"] == ["Biblioteca", "Cafetería"]
    assert col.respuestas[1]["seleccion"] == ["Cafetería", "Gimnasio"]  # grafía canónica
    assert col.respuestas[2]["seleccion"] == ["Biblioteca"] and col.respuestas[0]["significado"] == "Biblioteca, Cafetería"


def test_ranking_lista_ordenada():
    r = encuestas.interpretar_columna({"tipo_canonico": "ranking"}, ["Docencia > Instalaciones > Horarios"]).respuestas[0]
    assert r["seleccion"] == ["Docencia", "Instalaciones", "Horarios"]
    assert r["significado"] == "1.º Docencia, 2.º Instalaciones, 3.º Horarios"


# ── Números y texto ────────────────────────────────────────────────────────────


def test_escala_lineal_con_y_sin_anclas():
    spec = {"tipo_canonico": "escala_lineal", "rango": [1, 5]}
    con = encuestas.interpretar_columna(spec, ["4"], anclas={1: "Nada", 5: "Mucho"}).respuestas[0]
    assert con["significado"] == "4 en escala 1–5, donde 1 = Nada y 5 = Mucho" and con["nivel"] == "alta"
    sin = encuestas.interpretar_columna(spec, ["4", "7"])
    assert sin.respuestas[0]["significado"] == "4 de 5" and sin.respuestas[1]["estado"] == "no_interpretada"
    assert sin.escala["rango"] == [1, 5] and sin.escala["puntos"] == 5


def test_calificacion_y_numerica_con_rango_o_unidad():
    cal = encuestas.interpretar_columna({"tipo_canonico": "calificacion", "rango": [0, 10]}, ["8.5", "9"])
    assert [r["significado"] for r in cal.respuestas] == ["8.5 (escala 0–10)", "9 (escala 0–10)"] and cal.respuestas[1]["valor"] == 9
    horas = encuestas.interpretar_columna({"tipo_canonico": "numerica", "etiqueta": "horas_trabajo_semana"}, ["14", "x"])
    assert horas.respuestas[0]["significado"] == "14 horas" and horas.escala == {"unidad": "horas"}
    assert horas.respuestas[1]["estado"] == "no_interpretada"
    assert encuestas.interpretar_columna({"tipo_canonico": "numerica", "etiqueta": "Ingreso"}, ["8000"]).respuestas[0]["significado"] == "8000"


def test_texto_tal_cual():
    col = encuestas.interpretar_columna({"tipo_canonico": "texto_largo"}, ["  Más prácticas  ", ""])
    assert col.respuestas == [{"estado": "respondida", "valor": "Más prácticas", "texto": "Más prácticas"}, {"estado": "sin_respuesta"}]


def test_encuesta_real_sin_respuestas_no_interpretadas():
    """Con la limpieza real de la encuesta de ejemplo, todo se interpreta (nada queda fuera)."""
    datos = limpieza("encuesta")
    columnas = {c["id"]: c for c in datos["reporte"]["especifico"]["encuesta"]["columnas"]}
    encabezados = datos["csv"]["headers"]
    for j, h in enumerate(encabezados):
        valores = [f[j] for f in datos["csv"]["rows"]]
        col = encuestas.interpretar_columna(columnas[h], valores)
        assert len(col.respuestas) == len(valores) and col.no_interpretadas == 0, h
    j = encabezados.index("me_siento_motivado_para_continuar_mis_es")
    r = encuestas.interpretar_columna(columnas[encabezados[j]], [datos["csv"]["rows"][0][j]]).respuestas[0]
    assert (r["valor"], r["significado"], r["nivel"]) == (1, "Totalmente en desacuerdo", "desacuerdo")


# ── Pruebas estandarizadas ─────────────────────────────────────────────────────


def test_pruebas_letra_a_opcion_correcta_estado_y_motivo():
    letras = {"A": "56", "B": "54"}
    assert pruebas.interpretar({"respuesta": "A", "correcta": "1", "estado": "valida", "motivo": ""}, letras) == {
        "respuesta": "A", "correcta": True, "estado": "valida", "significado": "56"}
    assert pruebas.interpretar({"respuesta": "c", "correcta": "0", "estado": "valida"}, letras)["significado"] == "Opción C"
    nula = pruebas.interpretar({"respuesta": "AB", "correcta": "0", "estado": "nula", "motivo": "respuesta_multiple"}, letras)
    assert nula == {"respuesta": "AB", "correcta": False, "estado": "nula", "motivo": "respuesta_multiple", "significado": "Respuesta múltiple (AB)"}
    nr = pruebas.interpretar({"respuesta": "", "correcta": "0", "estado": "NR", "motivo": "no_respondida"}, letras)
    assert nr == {"respuesta": None, "correcta": False, "estado": "sin_respuesta", "motivo": "no_respondida"}
    assert pruebas.interpretar({"respuesta": "*", "estado": "nula", "motivo": "ilegible"}, {})["significado"] == "Ilegible (*)"


# ── Privacidad ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("encabezado", ["ID", "id_alumno", "Nombre completo", "Nombre", "correo_institucional", "Correo electrónico",
                                        "Matrícula", "Teléfono", "CURP", "Número de cuenta", "e-mail"])
def test_datos_personales_por_palabra_completa(encabezado):
    assert es_dato_personal(encabezado)


@pytest.mark.parametrize("encabezado", ["Idioma", "Identidad de género", "Ideas para mejorar", "Turno", "Semestre",
                                        "¿Cuentas con beca?", "Nombramiento del docente", "Correspondencia con el tutor"])
def test_no_son_datos_personales(encabezado):
    assert not es_dato_personal(encabezado)


def test_escala_numerica_con_anclas_del_original():
    anclas = {1: "Totalmente en desacuerdo / Nunca", 2: "En desacuerdo / Pocas veces", 3: "Ni de acuerdo ni en desacuerdo / A veces",
              4: "De acuerdo / Frecuentemente", 5: "Totalmente de acuerdo / Siempre"}
    assert escalas.escala_por_anclas(anclas) == "acuerdo"
    assert escalas.escala_por_anclas({1: "Rojo", 2: "Azul"}) is None
    spec = _likert(etiquetas=["1", "2", "3", "4", "5"], escala="numerica")
    r = encuestas.interpretar_columna(spec, ["4", "2"], anclas=anclas).respuestas
    assert (r[0]["significado"], r[0]["nivel"]) == ("De acuerdo / Frecuentemente", "acuerdo")
    assert r[1]["nivel"] == "desacuerdo"
