"""Chunks del RAG desde el documento final vigente (encuesta, prueba y entrevista)."""
from __future__ import annotations

import re

from shared.models.version_conocimiento import VersionConocimiento

from services import chunks_documento
from services.chroma_indexer import VENTANA
from tests.test_indice import JSON_APROBADO, _guardar_json, _sembrar

KPI = {
    "kpi_id": "KPI-07", "nombre": "Satisfacción estudiantil", "definicion": "Grado de satisfacción con la carrera.",
    "que_mide": "Mide la satisfacción.", "justificacion": "p01 pregunta por la satisfacción con los profesores.",
    "evidencia": [{"pregunta_id": "INS-0001-p01", "similitud": 0.6}],
}
LIKERT = ["Totalmente en desacuerdo", "En desacuerdo", "Neutral", "De acuerdo", "Totalmente de acuerdo"]


def _encuesta(n: int = 30) -> dict:
    preguntas = [
        {"id": f"INS-0001-p{k:02d}", "seccion_id": "INS-0001-s1", "texto": f"Pregunta larga número {k} sobre la experiencia en la carrera universitaria",
         "tipo": "likert", "kpis_relacionados": ["KPI-07"] if k == 1 else [],
         "resumen": {"n_validas": n, "n_sin_respuesta": 0, "distribucion": [{"significado": s, "n": 6, "pct": 20.0} for s in LIKERT],
                     "por_nivel": {"acuerdo": 40.0, "desacuerdo": 40.0, "neutral": 20.0}, "interpretacion": "Opiniones divididas."}}
        for k in range(1, 13)
    ]
    respondentes = [
        {"id": f"INS-0001-R{i:03d}", "contexto": {"turno": "Vespertino" if i % 2 else "Matutino", "correo": None},
         "respuestas": [{"pregunta_id": p["id"], "pregunta": p["texto"], "estado": "respondida", "valor": 4, "significado": "De acuerdo",
                         "nivel": "acuerdo"} for p in preguntas]}
        for i in range(1, n + 1)
    ]
    respondentes[0]["respuestas"][1] = {"pregunta_id": preguntas[1]["id"], "pregunta": preguntas[1]["texto"], "estado": "sin_respuesta",
                                        "motivo": "no_sabe"}
    return {"esquema_version": "1.0",
            "instrumento": {"id": "INS-0001", "tipo": "encuesta", "titulo": "Experiencia 2026", "objetivo": "Conocer la satisfacción.",
                            "temas": ["satisfacción"], "poblacion": "Estudiantes", "n_respondentes": n},
            "kpis_asociados": [KPI], "secciones": [{"id": "INS-0001-s1", "nombre": "Experiencia"}],
            "preguntas": preguntas, "respondentes": respondentes, "avisos": []}


PRUEBA = {
    "esquema_version": "1.0",
    "instrumento": {"id": "INS-0002", "tipo": "prueba_estandarizada", "titulo": "Diagnóstico", "n_alumnos": 2},
    "kpis_asociados": [], "secciones": [],
    "reactivos": [{"id": "INS-0002-r01", "texto": "¿Cuánto es 7 × 8?", "tipo_reactivo": "opcion_multiple", "calificable": True,
                   "opciones": {"A": "56", "B": "54"}, "respuesta_correcta": "A", "kpis_relacionados": [],
                   "resumen": {"n_alumnos": 2, "pct_acierto": 50.0, "distribucion": {"A": {"n": 1, "pct": 50.0}, "B": {"n": 1, "pct": 50.0}},
                               "distractor_mas_elegido": {"opcion": "B", "significado": "54", "pct": 50.0}, "dificultad": 0.5,
                               "discriminacion": 1.0}}],
    "alumnos": [{"id": "INS-0002-A001", "contexto": {}, "puntaje": 1, "total": 1, "porcentaje": 100.0,
                 "respuestas": [{"reactivo_id": "INS-0002-r01", "respuesta": "A", "correcta": True, "significado": "56"}]}],
    "avisos": [],
}

ENTREVISTA = {
    "esquema_version": "2.0",
    "instrumento": {"id": "INS-0003", "tipo": "entrevista", "titulo": "Entrevistas sobre evaluación"},
    "kpis_asociados": [], "preguntas": [{"id": "INS-0003-p01", "texto": "¿Cómo te evalúan?", "kpis_relacionados": []}],
    "entrevistas": [{"participante": "INS-0003-E02", "intercambios": [
        {"pregunta_id": "INS-0003-p01", "pregunta": "¿Cómo te evalúan?", "respuesta": "Con exámenes y proyectos. " * 40}]}],
    "avisos": [],
}


def test_encuesta_un_chunk_por_pregunta_respondente_y_kpi():
    chunks = chunks_documento.construir(_encuesta(), "Encuesta")
    assert chunks[0].seccion == "encabezado" and "KPIs asociados: Satisfacción estudiantil" in "".join(
        c.texto for c in chunks if c.seccion == "encabezado")
    assert {c.pregunta_id for c in chunks if c.seccion == "pregunta"} == {f"INS-0001-p{k:02d}" for k in range(1, 13)}
    # Cada respondente tiene al menos un chunk y todos sus chunks repiten quién es y su contexto.
    por_persona: dict[str, list] = {}
    for c in chunks:
        if c.seccion == "respondente":
            por_persona.setdefault(c.extra["respondenteId"], []).append(c)
    assert len(por_persona) == 30
    r001 = por_persona["INS-0001-R001"]
    assert len(r001) > 1 and all(c.texto.startswith("Respondente R001 (turno: Vespertino)") for c in r001)
    texto_r001 = "\n".join(c.texto for c in r001)
    assert "p01 «" in texto_r001 and ": De acuerdo" in texto_r001 and "sin respuesta (no_sabe)" in texto_r001
    # Significado, nunca el código: no aparece «: 4».
    assert not re.search(r"»: 4\b", texto_r001)
    kpi = next(c for c in chunks if c.seccion == "kpi")
    assert "Por qué se asoció" in kpi.texto and "p01 «Pregunta larga número 1" in kpi.texto and kpi.extra["kpiId"] == "KPI-07"


def test_ningun_chunk_excede_la_ventana_ni_parte_lineas_de_una_lista():
    for doc, tipo in ((_encuesta(), "Encuesta"), (PRUEBA, "Prueba estandarizada"), (ENTREVISTA, "Entrevista")):
        for c in chunks_documento.construir(doc, tipo):
            assert len(c.texto) <= VENTANA, (c.seccion, len(c.texto))
            if c.seccion == "respondente":  # cada línea es una respuesta completa
                assert all(re.match(r"p\d\d «", linea) for linea in c.texto.splitlines()[1:])


def test_prueba_reactivo_con_acierto_y_distractor_y_alumno():
    chunks = chunks_documento.construir(PRUEBA, "Prueba estandarizada")
    reactivo = next(c for c in chunks if c.seccion == "reactivo")
    assert "Porcentaje de acierto: 50.0 %" in reactivo.texto and "Distractor más elegido: B (54), 50.0 %" in reactivo.texto
    alumno = next(c for c in chunks if c.seccion == "alumno")
    assert alumno.texto.startswith("Alumno A001") and "r01: A (56) correcta" in alumno.texto
    assert alumno.extra["respondenteId"] == "INS-0002-A001"


def test_entrevista_intercambio_largo_repite_participante_y_pregunta():
    chunks = [c for c in chunks_documento.construir(ENTREVISTA, "Entrevista") if c.seccion == "intercambio"]
    assert len(chunks) > 1
    assert all(c.texto.startswith("Participante E02, pregunta p01: ¿Cómo te evalúan?") for c in chunks)
    assert {c.extra["respondenteId"] for c in chunks} == {"INS-0003-E02"} and {c.pregunta_id for c in chunks} == {"INS-0003-p01"}


def test_indexa_desde_el_documento_vigente(cliente, servicio, db, chroma):
    id_crudo, _ = _sembrar(db, aprobado=True)
    _guardar_json(cliente, servicio, id_crudo, JSON_APROBADO)  # JSON técnico (no debe usarse)
    r = cliente.post("/almacenamiento/json", headers=servicio,
                     json={"instrumentoId": str(id_crudo), "tipo": "documento", "contenido": _encuesta(4)})
    assert r.status_code == 200, r.text
    db.add(VersionConocimiento(id_crudo=id_crudo, version=1, estado="vigente", perfil={}, ruta_documento=r.json()["key"]))
    db.commit()

    r = cliente.post(f"/almacenamiento/indice/instrumentos/{id_crudo}", headers=servicio)
    assert r.status_code == 200, r.text
    puntos = chroma.colecciones["instrumentos"].puntos.values()
    assert {p["metadata"]["fuente"] for p in puntos} == {"documento"}
    assert {p["metadata"]["titulo"] for p in puntos} == {"Experiencia 2026"}
    assert any(p["metadata"]["respondenteId"] == "INS-0001-R003" for p in puntos)
    assert not any("Calidad académica" in p["document"] for p in puntos)


def test_sin_documento_vigente_usa_el_json_tecnico(cliente, servicio, db, chroma):
    id_crudo, _ = _sembrar(db, aprobado=True)
    _guardar_json(cliente, servicio, id_crudo, JSON_APROBADO)
    r = cliente.post("/almacenamiento/json", headers=servicio,
                     json={"instrumentoId": str(id_crudo), "tipo": "documento", "contenido": _encuesta(4)})
    db.add(VersionConocimiento(id_crudo=id_crudo, version=1, estado="borrador", perfil={}, ruta_documento=r.json()["key"]))
    db.commit()
    assert cliente.post(f"/almacenamiento/indice/instrumentos/{id_crudo}", headers=servicio).status_code == 200
    puntos = chroma.colecciones["instrumentos"].puntos.values()
    assert {p["metadata"]["fuente"] for p in puntos} == {"json_tecnico"}
