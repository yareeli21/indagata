"""Integración con cleaning-service: metadata-service usa el CSV LIMPIO y el
reporte_limpieza de la última versión confirmada, ya no el archivo crudo.
"""
from __future__ import annotations

import pytest

from shared.models.instrumento_procesado import InstrumentoProcesado

# Crudo SUCIO: si metadata lo leyera, verían «Marca temporal» como pregunta.
CRUDO = "Marca temporal,¿Qué tan satisfecho estás?\n2024-05-01,Muy satisfecho\n"

LIMPIO_ENCUESTA = (
    "edad;carrera;satisfaccion_general;comentarios\n"
    "19;Pedagogía;4;Todo bien\n20;Derecho;5;\n21;Pedagogía;3;Regular\n"
)
REPORTE_ENCUESTA = {
    "esquema": "reporte_limpieza/1",
    "version_servicio": "1.0.0",
    "fecha_confirmacion": "2026-10-15T10:00:00+00:00",
    "metricas": {"antes": {"n_duplicados": 2, "pct_nulos": 0.3}, "despues": {"n_duplicados": 0, "pct_nulos": 0.0833}},
    "avisos": [],
    "estadistica": {
        "antes": {},
        "despues": {
            "columnas": [{"id": "satisfaccion_general", "numerico": {"n": 3, "media": 4.0}, "frecuencias": {"moda": "Satisfecho"}}],
            "fiabilidad": [{"bloque": "Todas las escalas Likert", "alfa": 0.81, "interpretacion": "buena"}],
        },
    },
    "especifico": {
        "encuesta": {
            "columnas": [
                {"id": "marca_temporal", "etiqueta": "Marca temporal", "rol": None, "tipo_canonico": "categorica", "estado": "eliminada"},
                {"id": "edad", "etiqueta": "Edad", "rol": "contexto", "tipo_canonico": "calificacion", "estado": "conservada"},
                {"id": "carrera", "etiqueta": "Carrera", "rol": "contexto", "tipo_canonico": "categorica", "estado": "conservada"},
                {
                    "id": "satisfaccion_general",
                    "etiqueta": "¿Qué tan satisfecho estás con la carrera?",
                    "rol": "pregunta",
                    "tipo_canonico": "likert",
                    "estado": "conservada",
                    "likert": {"escala": "satisfaccion", "puntos": 5, "etiquetas": ["Muy insatisfecho", "Insatisfecho", "Neutral", "Satisfecho", "Muy satisfecho"], "neutral": 3, "excluidos": [], "invertido": False, "codigos": {}},
                },
                {"id": "comentarios", "etiqueta": "Comentarios adicionales sobre tu experiencia", "rol": "pregunta", "tipo_canonico": "texto_corto", "estado": "conservada"},
            ]
        }
    },
}


@pytest.fixture()
def exigir(monkeypatch):
    monkeypatch.setenv("METADATA_EXIGIR_LIMPIEZA", "true")


def test_instrumento_nuevo_sin_limpieza_confirmada_no_pasa_a_metadatos(cliente, ana, crear_instrumento, exigir):
    id_crudo = crear_instrumento("encuesta.csv", CRUDO)
    r = cliente.get(f"/api/metadata/{id_crudo}/propuesta", headers=ana)
    assert r.status_code == 409 and "limpieza" in r.json()["detail"]
    assert cliente.get(f"/api/enrichment/{id_crudo}/propuesta", headers=ana).status_code == 409


def test_instrumento_anterior_a_la_limpieza_sigue_con_el_crudo(cliente, ana, crear_instrumento, db, exigir):
    id_crudo = crear_instrumento("encuesta.csv", CRUDO)
    db.query(InstrumentoProcesado).filter_by(id_crudo=id_crudo).update({"estado": "estandarizado"})
    db.commit()
    assert cliente.get(f"/api/metadata/{id_crudo}/propuesta", headers=ana).status_code == 200


def test_encuesta_usa_csv_limpio_etiquetas_y_tipos_del_reporte(cliente, ana, crear_instrumento, crear_limpieza, storage, exigir):
    id_crudo = crear_instrumento("encuesta.csv", CRUDO)
    ruta = crear_limpieza(id_crudo, LIMPIO_ENCUESTA, REPORTE_ENCUESTA)
    r = cliente.post(f"/api/metadata/{id_crudo}/vista-previa", json={"dublin_core": {}, "enriquecidos": {}}, headers=ana)
    assert r.status_code == 200, r.text
    data = r.json()["json_estandarizado"]
    preguntas = [q for s in data["instrument"]["sections"] for q in s["questions"]]
    # Solo las columnas «pregunta», con su texto original; no la marca temporal ni los datos de contexto.
    assert [q["text"] for q in preguntas] == ["¿Qué tan satisfecho estás con la carrera?", "Comentarios adicionales sobre tu experiencia"]
    assert preguntas[0]["type"] == "likert" and preguntas[0]["options"][-1] == "Muy satisfecho"
    assert preguntas[1]["type"] == "texto_corto"
    stats = data["statistics"]
    assert stats["global"]["n_registros"] == 3 and stats["global"]["n_duplicados"] == 2
    assert stats["global"]["pct_vacios"] == 0.0833
    # Trazabilidad: qué limpieza originó estos datos.
    assert data["cleaning"]["version"] == 1 and data["cleaning"]["archivo_limpio"] == ruta
    assert data["source_files"]["limpio"] == ruta
    # Medidas estadísticas de la limpieza: por pregunta y fiabilidad global.
    assert stats["per_question"][preguntas[0]["question_id"]]["numerico"]["media"] == 4.0
    assert stats["reliability"][0]["alfa"] == 0.81

    dc = cliente.get(f"/api/metadata/{id_crudo}/propuesta", headers=ana).json()
    assert any("archivo limpio" in n for n in dc["notas"])


def test_entrevista_preguntas_desde_turnos_del_entrevistador(cliente, ana, crear_instrumento, crear_limpieza, exigir):
    id_crudo = crear_instrumento("entrevista.txt", "texto crudo con ruido [00:01]", tipo="entrevista")
    limpio = (
        "n_turno;hablante;rol;texto\n"
        "1;Entrevistador;entrevistador;¿Qué te motivó a elegir la carrera?\n"
        "2;Ana;entrevistado;Siempre me gustó enseñar.\n"
        "3;Entrevistador;entrevistador;¿Cómo fue tu experiencia en línea?\n"
        "4;Ana;entrevistado;Difícil al principio.\n"
    )
    crear_limpieza(id_crudo, limpio, {"especifico": {"entrevista": {"estructura_reconocida": True}}})
    data = cliente.post(f"/api/metadata/{id_crudo}/vista-previa", json={"dublin_core": {}, "enriquecidos": {}}, headers=ana).json()["json_estandarizado"]
    preguntas = [q["text"] for s in data["instrument"]["sections"] for q in s["questions"]]
    assert preguntas == ["¿Qué te motivó a elegir la carrera?", "¿Cómo fue tu experiencia en línea?"]
    assert "[00:01]" not in data["instrument"]["contenido"]
    assert data["statistics"]["global"]["n_registros"] == 4


def test_prueba_reactivos_desde_la_clave_con_estadisticas(cliente, ana, crear_instrumento, crear_limpieza, exigir):
    id_crudo = crear_instrumento("respuestas.csv", "matricula,P1\nA1,A\n", tipo="prueba_estandarizada")
    limpio = (
        "id_alumno;pregunta;respuesta;respuesta_correcta;correcta;estado;motivo\n"
        "A1;P1;A;A;1;valida;\nA1;P2;AB;B;0;nula;respuesta_multiple\n"
        "A2;P1;C;A;0;valida;\nA2;P2;;B;0;NR;no_respondida\n"
    )
    reporte = {
        "especifico": {
            "prueba_estandarizada": {
                "clave": {"P1": "A", "P2": "B"},
                "opciones_validas": ["A", "B", "C", "D", "NR"],
                "conteos": {"valida": 2, "nula": 1, "NR": 1},
                "n_alumnos": 2,
            }
        },
        "estadistica": {
            "despues": {
                "reactivos": [{"pregunta": "P1", "respuesta_correcta": "A", "dificultad": 0.5, "nivel_discriminacion": "buena"}],
                "fiabilidad": {"kr20": 0.42, "interpretacion": "inaceptable"},
            }
        },
    }
    crear_limpieza(id_crudo, limpio, reporte)
    data = cliente.post(f"/api/metadata/{id_crudo}/vista-previa", json={"dublin_core": {}, "enriquecidos": {}}, headers=ana).json()["json_estandarizado"]
    preguntas = [q for s in data["instrument"]["sections"] for q in s["questions"]]
    assert [q["question_id"] for q in preguntas] == ["P1", "P2"]
    assert preguntas[0]["options"] == ["A", "B", "C", "D"]
    p1 = data["statistics"]["per_question"]["P1"]
    assert p1["respuesta_correcta"] == "A" and p1["pct_correctas"] == 0.5
    assert p1["dificultad"] == 0.5 and p1["nivel_discriminacion"] == "buena"
    assert data["statistics"]["reliability"]["kr20"] == 0.42
    assert data["statistics"]["per_question"]["P2"]["pct_no_respondidas"] == 0.5
    assert data["statistics"]["global"]["n_registros"] == 2


def test_usa_la_ultima_version_confirmada(cliente, ana, crear_instrumento, crear_limpieza, exigir):
    id_crudo = crear_instrumento("encuesta.csv", CRUDO)
    crear_limpieza(id_crudo, LIMPIO_ENCUESTA, REPORTE_ENCUESTA, version=1)
    otro = dict(REPORTE_ENCUESTA)
    crear_limpieza(id_crudo, "edad;satisfaccion_general\n19;4\n", otro, version=2)
    data = cliente.post(f"/api/metadata/{id_crudo}/vista-previa", json={"dublin_core": {}, "enriquecidos": {}}, headers=ana).json()["json_estandarizado"]
    assert data["cleaning"]["version"] == 2
    assert data["statistics"]["global"]["n_registros"] == 1


def test_carrera_solo_desde_la_columna_de_carrera_no_de_preguntas_que_la_mencionan():
    from services.analizador import _desde_tabla, es_columna_carrera

    # Una escala que menciona «carrera» no es la columna de carreras (antes sus códigos
    # 2, 5, 4… terminaban como «Estudiantes de 2, 5, 4»).
    assert not es_columna_carrera("Valora tu experiencia en la carrera [Profesores]", ["2", "5", "4"])
    assert not es_columna_carrera("¿Qué tan satisfecho estás con la carrera que elegiste este semestre?", ["Mucho"])
    assert not es_columna_carrera("Carrera", ["1", "2", "3"])  # códigos numéricos
    assert es_columna_carrera("Carrera", ["Pedagogía", "Derecho"])
    assert es_columna_carrera("Programa educativo", ["Psicología"])

    tabla = {
        "headers": ["Valora tu experiencia en la carrera [Profesores]", "Carrera"],
        "rows": [["4", "Pedagogía"], ["2", "Derecho"], ["5", "Pedagogía"]],
    }
    analisis = _desde_tabla(tabla, "encuesta", "enc.csv", "")
    assert analisis.carreras == ["Pedagogía", "Derecho"]
    assert analisis.hallazgos["poblacion"] == "Estudiantes de Pedagogía, Derecho"
    sin_carrera = _desde_tabla({"headers": tabla["headers"][:1], "rows": [["4"], ["2"]]}, "encuesta", "enc.csv", "")
    assert sin_carrera.carreras == [] and "poblacion" not in sin_carrera.hallazgos


def test_titulo_salta_lineas_decorativas_y_de_ficha():
    from services.analizador import _titulo_documento

    texto = "=" * 70 + "\nINSTRUMENTO: Escala RAU de Rendimiento Académico\nID: enc_05\n" + "=" * 70 + "\n1. Pregunta"
    assert _titulo_documento(texto, "enc_05.csv") == "Escala RAU de Rendimiento Académico"
    assert _titulo_documento("ID: x\n-----\n", "encuesta_docentes.csv") != "-----"
