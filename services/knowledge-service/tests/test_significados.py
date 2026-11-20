"""Microdatos: el documento final usa el texto de las preguntas en código y el significado de sus códigos.

El significado viene del reporte de limpieza (`especifico.<tipo>.significados`), que se llena con el
diccionario de datos o con lo que escribió la investigadora.
"""
from __future__ import annotations

from services import estructura
from services.documento import encuesta as doc_encuesta
from services.interpretacion import encuestas, pruebas


def _likert_numerica(puntos: int = 5) -> dict:
    return {"tipo_canonico": "likert", "likert": {"escala": "numerica", "etiquetas": [str(i) for i in range(1, puntos + 1)]}}


# ── Interpretación ─────────────────────────────────────────────────────────────


def test_codigos_de_categoria_se_traducen_aunque_parezcan_escala():
    # La limpieza tomó «turno» (1/2/3) por una escala; con sus etiquetas es una categoría.
    spec = dict(_likert_numerica(3), etiquetas_valor={"1": "Matutino", "2": "Vespertino", "3": "Mixto"})
    col = encuestas.interpretar_columna(spec, ["2", "", "1", "2"])
    assert col.tipo == "categorica"
    assert col.respuestas[0] == {"estado": "respondida", "valor": "2", "significado": "Vespertino"}
    assert col.respuestas[1] == {"estado": "sin_respuesta"}
    assert col.opciones == ["Matutino", "Vespertino"]  # en el orden del diccionario, solo las que aparecen


def test_codigo_sin_etiqueta_se_conserva():
    col = encuestas.interpretar_columna({"tipo_canonico": "categorica", "etiquetas_valor": {"1": "Hombre", "2": "Mujer"}},
                                        ["1", "9", "02"])
    assert [r["significado"] for r in col.respuestas] == ["Hombre", "9", "Mujer"]  # «02» es el código 2


def test_etiquetas_de_una_escala_son_sus_anclas():
    etiquetas = {"1": "Nunca", "2": "Casi nunca", "3": "A veces", "4": "Casi siempre", "5": "Siempre"}
    col = encuestas.interpretar_columna(dict(_likert_numerica(), etiquetas_valor=etiquetas), ["1", "5", "3"])
    assert col.tipo is None  # sigue siendo una escala, con sus niveles
    assert col.respuestas[0]["significado"] == "Nunca" and col.respuestas[1]["nivel"] == "alta"
    # Solo los extremos también describen una escala.
    col = encuestas.interpretar_columna(dict(_likert_numerica(), etiquetas_valor={"1": "Nada", "5": "Mucho"}), ["1", "3", "5"])
    assert col.respuestas[0]["significado"] == "Nada" and col.respuestas[1]["significado"] == "3 en escala 1–5"


def test_binaria_en_codigos_reconoce_si_y_no():
    col = encuestas.interpretar_columna({"tipo_canonico": "binaria", "etiquetas_valor": {"1": "Sí", "2": "No"}}, ["1", "2"])
    assert col.respuestas[0] == {"estado": "respondida", "valor": "1", "significado": "Sí", "nivel": "si"}
    assert col.respuestas[1]["significado"] == "No"


def test_etiquetas_que_no_son_de_los_valores_se_ignoran():
    # Escala de texto («De acuerdo»): sus valores no son los códigos del diccionario.
    spec = {"tipo_canonico": "categorica", "etiquetas_valor": {"1": "Uno"}}
    assert encuestas.interpretar_columna(spec, ["Pedagogía"]).respuestas[0]["significado"] == "Pedagogía"


def test_seleccion_multiple_en_codigos():
    spec = {"tipo_canonico": "opcion_multiple_varias", "etiquetas_valor": {"1": "Libros", "2": "Videos", "3": "Apuntes"}}
    col = encuestas.interpretar_columna(spec, ["1,3"])
    assert col.respuestas[0]["seleccion"] == ["Libros", "Apuntes"] and col.respuestas[0]["significado"] == "Libros, Apuntes"


def test_escala_de_una_prueba_con_su_significado():
    r = pruebas.interpretar({"respuesta": "3", "estado": "valida"}, {"3": "A veces"}, "escala", 5)
    assert r["significado"] == "3 (A veces) en escala 1–5"


# ── Estructura y documento final ───────────────────────────────────────────────


def _reporte() -> dict:
    columnas = [
        {"id": "p1", "etiqueta": "P1", "rol": "pregunta", "tipo_canonico": "binaria", "estado": "conservada"},
        {"id": "p2", "etiqueta": "P2", "rol": "pregunta", "tipo_canonico": "likert", "estado": "conservada",
         "likert": {"escala": "numerica", "etiquetas": ["1", "2", "3"]}},
        {"id": "p3", "etiqueta": "P3", "rol": "contexto", "tipo_canonico": "categorica", "estado": "conservada"},
    ]
    significados = {
        "p1": {"pregunta": "¿Tienes beca?", "valores": {"1": "Sí", "2": "No"}},
        "p2": {"pregunta": "¿En qué turno estudias?", "valores": {"1": "Matutino", "2": "Vespertino", "3": "Mixto"}},
        "p3": {"pregunta": "Carrera", "valores": {"10": "Pedagogía", "20": "Psicología"}},
    }
    return {"especifico": {"encuesta": {"columnas": columnas, "significados": significados}}}


def test_estructura_toma_el_texto_de_las_preguntas_en_codigo():
    est = estructura.encuesta(5, _reporte(), None)
    assert [p.texto for p in est.preguntas] == ["¿Tienes beca?", "¿En qué turno estudias?"]
    assert est.preguntas[1].opciones == []  # P2 es escala para la limpieza: sus etiquetas no son opciones…
    assert {s.nombre for s in est.secciones} == {"Preguntas del instrumento"}  # «P» no es una sección
    assert not any(a["codigo"] == "sin_original" for a in est.avisos)


def test_documento_final_responde_con_significados():
    reporte = _reporte()
    est = estructura.encuesta(5, reporte, None)
    filas = [{"p1": "1", "p2": "2", "p3": "10"}, {"p1": "2", "p2": "3", "p3": "20"}]
    perfil = {"instrumento_id": "INS-0005", "tipo": "encuesta", "kpis_asociados": []}
    doc = doc_encuesta.construir(perfil, est, reporte, filas)
    turno = next(p for p in doc["preguntas"] if p["texto"] == "¿En qué turno estudias?")
    assert turno["tipo"] == "categorica" and turno["opciones"] == ["Vespertino", "Mixto"]  # …pero sí son categorías
    r1 = doc["respondentes"][0]
    assert r1["contexto"] == {"Carrera": "Pedagogía"}
    assert [r["significado"] for r in r1["respuestas"]] == ["Sí", "Vespertino"]
