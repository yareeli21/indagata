"""Documentos finales de ejemplo (encuesta con turno, prueba y entrevista) para las pruebas del chat.

Tienen la misma forma que los que genera knowledge-service; los valores están
elegidos para que cada consulta tenga un resultado conocido y verificable a mano.
"""
from __future__ import annotations

ESCALA = {"1": "Totalmente en desacuerdo", "2": "En desacuerdo", "3": "Ni de acuerdo ni en desacuerdo", "4": "De acuerdo",
          "5": "Totalmente de acuerdo"}
NIVEL = {1: "desacuerdo", 2: "desacuerdo", 3: "neutral", 4: "acuerdo", 5: "acuerdo"}
TEXTOS = {
    1: "Los profesores explican con claridad",
    2: "La evaluación es justa",
    3: "Recibo retroalimentación oportuna",
    4: "Me siento motivado para continuar mis estudios",
    5: "La biblioteca tiene los libros que necesito",
    6: "Las instalaciones son adecuadas",
    7: "Recomendaría la carrera",
}
# Respuestas por respondente (p01..p07) y su turno. R003 está en desacuerdo en p3, p5 y p7.
RESPUESTAS = [
    ("Matutino", [4, 4, 3, 5, 4, 4, 5]),
    ("Vespertino", [2, 3, 4, 4, 2, 3, 4]),
    ("Vespertino", [3, 2, 1, 2, 2, 3, 1]),
    ("Vespertino", [5, 4, 4, 2, 4, 5, 4]),
    ("Matutino", [1, 2, 2, 1, 1, 2, 2]),
]


def encuesta(ins: str = "INS-0001") -> dict:
    preguntas = [
        {"id": f"{ins}-p{k:02d}", "seccion_id": f"{ins}-s1", "texto": t, "tipo": "likert",
         "kpis_relacionados": ["KPI-07"] if k in (4, 7) else [],
         "resumen": {"n_validas": 5, "n_sin_respuesta": 0, "interpretacion": f"Resumen de p{k:02d}."}}
        for k, t in TEXTOS.items()
    ]
    respondentes = []
    for i, (turno, valores) in enumerate(RESPUESTAS, start=1):
        respondentes.append({
            "id": f"{ins}-R{i:03d}", "contexto": {"Turno": turno},
            "respuestas": [{"pregunta_id": f"{ins}-p{k:02d}", "pregunta": TEXTOS[k], "estado": "respondida", "valor": v,
                            "significado": ESCALA[str(v)], "nivel": NIVEL[v]} for k, v in enumerate(valores, start=1)],
        })
    return {
        "esquema_version": "1.0",
        "instrumento": {"id": ins, "tipo": "encuesta", "titulo": "Experiencia estudiantil", "n_respondentes": 5},
        "kpis_asociados": [{
            "kpi_id": "KPI-07", "nombre": "Satisfacción estudiantil", "definicion": "Grado de satisfacción con la carrera.",
            "dimension": "Aumentar", "que_mide": "Mide la satisfacción.", "similitud": 0.61,
            "evidencia": [{"pregunta_id": f"{ins}-p04", "similitud": 0.55}, {"pregunta_id": f"{ins}-p07", "similitud": 0.52}],
            "justificacion": "p04 y p07 preguntan por la motivación y la recomendación de la carrera.",
        }],
        "secciones": [{"id": f"{ins}-s1", "nombre": "Experiencia"}],
        "preguntas": preguntas, "respondentes": respondentes, "avisos": [],
    }


def prueba(ins: str = "INS-0002") -> dict:
    return {
        "esquema_version": "1.0",
        "instrumento": {"id": ins, "tipo": "prueba_estandarizada", "titulo": "Diagnóstico de matemáticas", "n_alumnos": 2},
        "kpis_asociados": [], "secciones": [],
        "reactivos": [
            {"id": f"{ins}-r01", "texto": "¿Cuánto es 7 × 8?", "tipo_reactivo": "opcion_multiple", "calificable": True,
             "opciones": {"A": "56", "B": "54"}, "respuesta_correcta": "A", "kpis_relacionados": [],
             "resumen": {"pct_acierto": 84.6, "distractor_mas_elegido": {"opcion": "B", "significado": "54", "pct": 15.4}}},
            {"id": f"{ins}-r02", "texto": "¿Cuál es el resultado de 144 ÷ 12?", "tipo_reactivo": "opcion_multiple", "calificable": True,
             "opciones": {"C": "12", "D": "11"}, "respuesta_correcta": "C", "kpis_relacionados": [],
             "resumen": {"pct_acierto": 46.2, "distractor_mas_elegido": {"opcion": "D", "significado": "11", "pct": 23.1}}},
        ],
        "alumnos": [{"id": f"{ins}-A001", "contexto": {}, "puntaje": 1, "total": 2, "porcentaje": 50.0,
                     "respuestas": [{"reactivo_id": f"{ins}-r01", "respuesta": "A", "correcta": True},
                                    {"reactivo_id": f"{ins}-r02", "respuesta": "D", "correcta": False}]}],
        "avisos": [],
    }


def entrevista(ins: str = "INS-0003") -> dict:
    return {
        "esquema_version": "2.0",
        "instrumento": {"id": ins, "tipo": "entrevista", "titulo": "Entrevistas sobre evaluación"},
        "kpis_asociados": [],
        "preguntas": [{"id": f"{ins}-p01", "texto": "¿Cómo te evalúan tus profesores?", "kpis_relacionados": []},
                      {"id": f"{ins}-p02", "texto": "¿Qué servicios usas?", "kpis_relacionados": []}],
        "entrevistas": [
            {"participante": f"{ins}-E01", "intercambios": [
                {"pregunta_id": f"{ins}-p01", "pregunta": "¿Cómo te evalúan tus profesores?", "respuesta": "Con exámenes."}]},
            {"participante": f"{ins}-E02", "intercambios": [
                {"pregunta_id": f"{ins}-p01", "pregunta": "¿Cómo te evalúan tus profesores?",
                 "respuesta": "La evaluación es con proyectos y rúbricas claras."},
                {"pregunta_id": f"{ins}-p02", "pregunta": "¿Qué servicios usas?", "respuesta": "La biblioteca."}]},
        ],
        "avisos": [],
    }


# Encuesta de carga académica (consultas con filtro): una pregunta con variantes de «Sí»,
# una sí/no, una categórica con frases y una numérica. Valores por respondente:
# (turno, reprobado, dificultades, carga laboral, horas de estudio)
CARGA = [
    ("Matutino", "Sí, una vez", "Sí", "No trabajo", 12),
    ("Vespertino", "Sí, varias veces", "Sí", "Trabajo más de 30h", 4),
    ("Vespertino", "No, nunca", "No", "Trabajo menos de 20h", 25),
    ("Matutino", "Casi lo hago", "No", "No trabajo", 30),
    ("Vespertino", "Sí, una vez", "No", "Trabajo más de 30h", 8),
]
TEXTOS_CARGA = {
    1: ("¿Has reprobado alguna materia por falta de tiempo para estudiar?", "opcion_multiple"),
    2: ("¿Tienes dificultades para equilibrar trabajo y estudios?", "binaria"),
    3: ("¿Cuál es tu carga laboral actual?", "categorica"),
    4: ("¿Cuántas horas por semana dedicas al estudio fuera de clases? (número)", "numerica"),
}


def encuesta_carga(ins: str = "INS-0004") -> dict:
    preguntas = [{"id": f"{ins}-p{k:02d}", "seccion_id": f"{ins}-s1", "texto": t, "tipo": tipo, "kpis_relacionados": [],
                  "resumen": {"n_validas": 5}} for k, (t, tipo) in TEXTOS_CARGA.items()]
    respondentes = []
    for i, (turno, *valores) in enumerate(CARGA, start=1):
        respuestas = []
        for k, v in enumerate(valores, start=1):
            respuestas.append({"pregunta_id": f"{ins}-p{k:02d}", "pregunta": TEXTOS_CARGA[k][0], "estado": "respondida",
                               "valor": v, "significado": f"{v} horas" if k == 4 else v})
        respondentes.append({"id": f"{ins}-R{i:03d}", "contexto": {"Turno": turno}, "respuestas": respuestas})
    return {
        "esquema_version": "1.0",
        "instrumento": {"id": ins, "tipo": "encuesta", "titulo": "Encuesta de carga académica y gestión del tiempo",
                        "n_respondentes": 5},
        "kpis_asociados": [], "secciones": [{"id": f"{ins}-s1", "nombre": "Carga"}],
        "preguntas": preguntas, "respondentes": respondentes, "avisos": [],
    }
