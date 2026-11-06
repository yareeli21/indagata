"""Segundo corpus SINTÉTICO de entrevistas, de OTRO TEMA: docentes hablando de evaluación.

Sirve para comprobar que el análisis de respuestas no depende del tema: las mismas reglas
(marco temporal, función y postura respecto a la pregunta) aplicadas a otra población y
otro contenido. Misma forma que `corpus_entrevistas.py`: 4 docentes × 4 preguntas sobre el
momento actual, respuestas con relatos del pasado, digresiones y posturas ambivalentes, y
su anotación de referencia hecha a mano (revisable por la investigadora).

Uso: python tools/formatos/corpus_docentes.py → tools/formatos/corpus/entrevistas_docentes/
"""
from __future__ import annotations

import json
from pathlib import Path

DESTINO = Path(__file__).resolve().parent / "corpus" / "entrevistas_docentes"
TITULO = "Entrevista a docentes sobre prácticas de evaluación"

PREGUNTAS = [
    "¿Actualmente usas rúbricas para evaluar a tus estudiantes?",
    "¿Hoy en día consideras que los exámenes escritos reflejan lo que aprenden tus alumnos?",
    "¿En este momento recibes capacitación sobre evaluación por parte de la institución?",
    "¿Actualmente das retroalimentación individual a cada estudiante?",
]

# (respuesta, postura de referencia, frase del núcleo, frase de contexto/digresión o "")
RESPUESTAS: dict[str, list[tuple[str, str, str, str]]] = {
    "Rosa Méndez": [
        ("Cuando empecé a dar clases calificaba todo a ojo, la verdad, pero desde hace dos años sí uso rúbricas en todos "
         "los proyectos.", "si", "sí uso rúbricas", "a ojo"),
        ("No del todo; un examen te dice si memorizaron, pero no si saben aplicar lo que vimos.", "no", "no si saben aplicar", ""),
        ("Antes nos daban cursos cada verano, pero ahora ya no hay presupuesto, entonces no.", "no", "ahora ya no hay presupuesto", "cada verano"),
        ("Sí, a cada uno le dejo comentarios escritos en sus trabajos.", "si", "comentarios escritos", ""),
    ],
    "Héctor Vázquez": [
        ("Más o menos; en las prácticas de laboratorio sí, pero en los exámenes no las necesito.", "ambivalente", "en los exámenes no", ""),
        ("Sí, yo creo que sí, si el examen está bien diseñado refleja muy bien lo que saben. Por cierto, el estacionamiento "
         "de la escuela está imposible.", "si", "refleja muy bien", "estacionamiento"),
        ("Sí, este semestre tomo un diplomado de evaluación por competencias.", "si", "diplomado", ""),
        ("Con grupos de cuarenta es imposible; hace años, cuando eran quince, sí lo hacía, pero ahora no.",
         "no", "ahora no", "eran quince"),
    ],
    "Patricia Olvera": [
        ("No, nunca me han convencido; prefiero listas de cotejo.", "no", "listas de cotejo", ""),
        ("Depende de la materia; en matemáticas sí, pero en las materias de redacción no tanto.", "ambivalente", "no tanto", ""),
        ("No, y la última vez que hubo fue antes de la pandemia.", "no", "No", "antes de la pandemia"),
        ("Sí, cada quince días tengo una pequeña entrevista con cada estudiante.", "si", "cada quince días", ""),
    ],
    "Ernesto Lara": [
        ("Sí, me ayudaron mucho a que los estudiantes supieran qué se espera de ellos.", "si", "qué se espera de ellos", ""),
        ("Antes pensaba que sí, pero ahora creo que no, porque muchos copian o memorizan sin entender.",
         "no", "ahora creo que no", "antes pensaba que sí"),
        ("No, la institución no ofrece nada de eso actualmente.", "no", "no ofrece nada", ""),
        ("A veces; cuando tengo tiempo sí, pero en época de cierre de calificaciones no alcanzo.", "ambivalente", "no alcanzo", ""),
    ],
}
PERSONAS = list(RESPUESTAS)
CHAT = {
    "pregunta_postura": "¿Cuántos docentes entrevistados usan rúbricas actualmente para evaluar a sus estudiantes?",
    "pregunta_dijo": "¿Qué dijo el participante E02 sobre la capacitación?",
    "dijo_contiene": "diplomado",
}


def _original() -> str:
    lineas = [f"# {TITULO}", "", "Guion de la entrevista semiestructurada a docentes (prácticas actuales).", ""]
    return "\n".join(lineas + [f"{i}. {p}" for i, p in enumerate(PREGUNTAS, start=1)]) + "\n"


def _etiquetas() -> str:
    salida = [f"INSTRUMENTO: {TITULO}", ""]
    for n, persona in enumerate(PERSONAS, start=1):
        salida += [f"RESPONDENTE: D{n:04d}", ""]
        for pregunta, (respuesta, *_r) in zip(PREGUNTAS, RESPUESTAS[persona]):
            salida += [f"Entrevistadora: {pregunta}", f"Docente: {respuesta}", ""]
    return "\n".join(salida)


def _zoom() -> str:
    salida, minuto = [], 0
    for i, pregunta in enumerate(PREGUNTAS):
        salida += [f"Hablante 1   {minuto:02d}:05", pregunta]
        for k, persona in enumerate(PERSONAS, start=2):
            minuto += 1
            salida += [f"Hablante {k}   {minuto:02d}:10", ("Mmm, " if k % 2 else "") + RESPUESTAS[persona][i][0]]
    return "\n".join(salida) + "\n"


if __name__ == "__main__":
    DESTINO.mkdir(parents=True, exist_ok=True)
    (DESTINO / "guion_original.txt").write_text(_original(), encoding="utf-8")
    variantes = [
        {"clave": "D01", "descripcion": "Docentes: etiquetas «Entrevistadora:/Docente:» y bloques", "nivel": "ideal",
         "archivo": "D01_transcripcion.txt", "original": "guion_original.txt", "participantes": 4, **CHAT},
        {"clave": "D02", "descripcion": "Docentes: transcripción de Zoom, grupal", "nivel": "aceptado",
         "archivo": "D02_zoom.txt", "original": "guion_original.txt", "participantes": 4, **CHAT},
    ]
    (DESTINO / "D01_transcripcion.txt").write_text(_etiquetas(), encoding="utf-8")
    (DESTINO / "D02_zoom.txt").write_text(_zoom(), encoding="utf-8")
    (DESTINO / "variantes.json").write_text(json.dumps(variantes, ensure_ascii=False, indent=2), encoding="utf-8")
    referencia = [{"persona": f"E{n:02d}", "pregunta": i + 1, "postura": r[1], "nucleo_contiene": r[2], "contexto_contiene": r[3]}
                  for n, persona in enumerate(PERSONAS, start=1) for i, r in enumerate(RESPUESTAS[persona])]
    (DESTINO / "referencia.json").write_text(json.dumps(referencia, ensure_ascii=False, indent=2), encoding="utf-8")
    for v in variantes:
        print(v["clave"], v["descripcion"])
