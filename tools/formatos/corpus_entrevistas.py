"""Corpus SINTÉTICO de entrevistas para la matriz de aceptación (respuestas que divagan).

Una entrevista breve (4 participantes × 4 preguntas sobre el MOMENTO ACTUAL) con
respuestas reales en forma: relatos del pasado, digresiones y posturas ambivalentes, al
estilo de «Cuando iba en la primaria no lo pensaba así […] pero ahora creo que sí».

Cada respuesta lleva su ANOTACIÓN DE REFERENCIA (hecha a mano, revisable por la
investigadora): la postura respecto a la pregunta y una frase clave que debe quedar en el
núcleo (lo que responde), y la frase que es contexto de otro momento o digresión.

La misma entrevista se escribe en cinco formatos (ver `documentación/02_Desarrollo.md`, X.5.3).

Uso: python tools/formatos/corpus_entrevistas.py → tools/formatos/corpus/entrevistas/
"""
from __future__ import annotations

import json
from pathlib import Path

DESTINO = Path(__file__).resolve().parent / "corpus" / "entrevistas"
TITULO = "Entrevista sobre vida universitaria y actividades extracurriculares"

PREGUNTAS = [
    "¿Consideras que las actividades extracurriculares actualmente tienen impacto en tus calificaciones?",
    "¿Hoy en día usas el servicio de tutorías de la universidad?",
    "¿Actualmente trabajas mientras estudias?",
    "¿Te sientes parte de la comunidad universitaria en este momento?",
]

# (respuesta, postura de referencia, frase del núcleo, frase de contexto/digresión o "")
RESPUESTAS: dict[str, list[tuple[str, str, str, str]]] = {
    "Mariana Ruiz": [
        ("Cuando iba en la primaria no lo pensaba así, yo las practicaba porque me gustaba jugar y me divertía, pero ahora "
         "creo que sí, me llenan de energía por querer seguir manteniendo la beca deportiva, entonces diría que sí, aunque "
         "antes no porque antes lo veía como juego.", "si", "beca deportiva", "primaria"),
        ("En primer semestre iba cada semana porque reprobé cálculo, pero ahora ya no voy, ya no lo necesito.",
         "no", "ahora ya no voy", "primer semestre"),
        ("Antes trabajaba en una tienda los fines de semana, pero lo dejé; hoy solo estudio.", "no", "hoy solo estudio", "tienda"),
        ("Al principio me sentía muy sola, la verdad, pero ahora sí, tengo mi equipo de futbol y mis amigas.",
         "si", "equipo de futbol", "al principio"),
    ],
    "Jorge Salinas": [
        ("Sinceramente no; ahora me quitan tiempo para estudiar y mis calificaciones bajaron este semestre. De niño sí me "
         "ayudaban a concentrarme.", "no", "me quitan tiempo", "de niño"),
        ("Sí, voy cada martes con mi tutora de estadística, me ha servido mucho.", "si", "cada martes", ""),
        ("Sí, trabajo como mesero en las noches, unas veinte horas a la semana.", "si", "mesero", ""),
        ("Más o menos; con algunos compañeros sí, pero con la universidad en general no tanto, porque casi no vengo por el "
         "trabajo.", "ambivalente", "no tanto", ""),
    ],
    "Lucía Herrera": [
        ("Depende; en semestres tranquilos sí me ayudan, pero en exámenes finales me estresan. Hablando de otra cosa, el "
         "comedor está carísimo.", "ambivalente", "exámenes finales", "comedor"),
        ("No, nunca he ido; no sabía que existía hasta ahora.", "no", "nunca he ido", ""),
        ("Cuando estaba en la prepa trabajaba con mi papá, pero ahorita no, me dedico solo a la escuela.",
         "no", "solo a la escuela", "prepa"),
        ("Sí, completamente, participo en el consejo estudiantil.", "si", "consejo estudiantil", ""),
    ],
    "Andrés Mejía": [
        ("Sí, el teatro me enseñó a organizar mi tiempo y ahora entrego todo a tiempo.", "si", "entrego todo a tiempo", ""),
        ("Antes iba porque era obligatorio en primer semestre, pero hoy ya no.", "no", "hoy ya no", "obligatorio"),
        ("Sí, doy clases particulares de inglés por las tardes.", "si", "clases particulares", ""),
        ("No mucho, la verdad; desde la pandemia todo se siente lejano, aunque antes de eso sí me sentía parte.",
         "no", "todo se siente lejano", "antes de eso"),
    ],
}
ENTREVISTADORA = "Paola García"
PERSONAS = list(RESPUESTAS)


def _original() -> str:
    lineas = [f"# {TITULO}", "", "Guion de la entrevista semiestructurada (momento actual del estudiante).", ""]
    lineas += [f"{i}. {p}" for i, p in enumerate(PREGUNTAS, start=1)]
    return "\n".join(lineas) + "\n"


def _etiquetas() -> str:
    """I01: «RESPONDENTE: R000n» + «Entrevistador:» / «Entrevistado:»."""
    salida = [f"INSTRUMENTO: {TITULO}", ""]
    for n, persona in enumerate(PERSONAS, start=1):
        salida += [f"RESPONDENTE: R{n:04d}", ""]
        for pregunta, (respuesta, *_r) in zip(PREGUNTAS, RESPUESTAS[persona]):
            salida += [f"Entrevistador: {pregunta}", f"Entrevistado: {respuesta}", ""]
    return "\n".join(salida)


def _numeradas() -> str:
    """I02: «P1:» / «R:» por bloque (como ent_01)."""
    salida = [f"INSTRUMENTO: {TITULO}", ""]
    for n, persona in enumerate(PERSONAS, start=1):
        salida += [f"RESPONDENTE: R{n:04d}", ""]
        for i, (pregunta, (respuesta, *_r)) in enumerate(zip(PREGUNTAS, RESPUESTAS[persona]), start=1):
            salida += [f"P{i}: {pregunta}", f"R: {respuesta}", ""]
    return "\n".join(salida)


def _zoom() -> str:
    """I03: transcripción de Zoom (grupo): «Hablante n   mm:ss» y el texto abajo, con muletillas."""
    salida, minuto = [], 0
    for i, pregunta in enumerate(PREGUNTAS):
        salida += [f"Hablante 1   {minuto:02d}:05", pregunta]
        for k, persona in enumerate(PERSONAS, start=2):
            minuto += 1
            respuesta = RESPUESTAS[persona][i][0]
            salida += [f"Hablante {k}   {minuto:02d}:10", ("Eh, " if k % 2 else "") + respuesta]
    return "\n".join(salida) + "\n"


def _vtt() -> str:
    """I04: WebVTT de Teams con voces «<v Nombre>» (los nombres se anonimizan en el documento)."""
    salida, cue, segundo = ["WEBVTT", "", "NOTE Transcripción generada automáticamente", ""], 1, 0

    def marca(s: int) -> str:
        return f"00:{s // 60:02d}:{s % 60:02d}.000"

    for i, pregunta in enumerate(PREGUNTAS):
        for quien, texto in [(ENTREVISTADORA, pregunta)] + [(p, RESPUESTAS[p][i][0]) for p in PERSONAS]:
            salida += [str(cue), f"{marca(segundo)} --> {marca(segundo + 4)}", f"<v {quien}>{texto}</v>", ""]
            cue, segundo = cue + 1, segundo + 5
    return "\n".join(salida)


def _sin_etiquetas() -> str:
    """I05: una sola persona, sin marcar quién habla (párrafos)."""
    salida = ["Entrevista realizada en la biblioteca central.", ""]
    for pregunta, (respuesta, *_r) in zip(PREGUNTAS, RESPUESTAS[PERSONAS[0]]):
        salida += [pregunta, "", respuesta, ""]
    return "\n".join(salida)


VARIANTES = [
    ("I01", "Etiquetas «Entrevistador:/Entrevistado:» y bloques «RESPONDENTE»", "ideal", "I01_transcripcion.txt", _etiquetas, 4),
    ("I02", "Preguntas numeradas «P1:» y «R:» por bloque", "ideal", "I02_transcripcion.txt", _numeradas, 4),
    ("I03", "Transcripción de Zoom («Hablante n  mm:ss», muletillas), grupal", "aceptado", "I03_zoom.txt", _zoom, 4),
    ("I04", "WebVTT de Teams con voces «<v Nombre>», grupal", "aceptado", "I04_teams.vtt", _vtt, 4),
    ("I05", "Sin etiquetas de hablante (una persona, párrafos)", "aceptado", "I05_sin_etiquetas.txt", _sin_etiquetas, 1),
]


def referencia() -> list[dict]:
    """Anotación de referencia: por persona (en orden E01…) y pregunta."""
    return [{"persona": f"E{n:02d}", "pregunta": i + 1, "postura": r[1], "nucleo_contiene": r[2], "contexto_contiene": r[3]}
            for n, persona in enumerate(PERSONAS, start=1) for i, r in enumerate(RESPUESTAS[persona])]


if __name__ == "__main__":
    DESTINO.mkdir(parents=True, exist_ok=True)
    (DESTINO / "guion_original.txt").write_text(_original(), encoding="utf-8")
    meta = []
    for clave, descripcion, nivel, archivo, fn, personas in VARIANTES:
        (DESTINO / archivo).write_text(fn(), encoding="utf-8")
        meta.append({"clave": clave, "descripcion": descripcion, "nivel": nivel, "archivo": archivo,
                     "original": "guion_original.txt", "participantes": personas})
        print(clave, nivel, descripcion)
    (DESTINO / "variantes.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (DESTINO / "referencia.json").write_text(json.dumps(referencia(), ensure_ascii=False, indent=2), encoding="utf-8")
