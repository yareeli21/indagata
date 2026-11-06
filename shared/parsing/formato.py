"""Contrato de formato de las encuestas (ver `documentación/02_Desarrollo.md`, X.5.2).

Revisa la tabla de respuestas al subirla y devuelve el motivo de rechazo, o None si se
acepta. Solo rechaza lo que el sistema NO puede procesar bien; lo demás se acepta y se
avisa en la limpieza o el perfil:

  - **Formato largo** (una fila por respuesta: respondente, pregunta, valor): cada
    pregunta debe ser una columna.
  - **Sin fila de encabezados**: la primera fila trae respuestas, no nombres de columna.
  - **Encabezados en código sin el instrumento original** («P1», «Q12», «G01Q03»,
    «Evaluación_item3»): sin el original las preguntas serían solo esos códigos.

Compartido por instrument-service (al subir) y probado desde cleaning-service.
"""
from __future__ import annotations

import re
import unicodedata

# «P1», «Q12_3», «G01Q03», «G01Q03[SQ001]», «Evaluación_item3», «item_12», «Reactivo 4».
_RE_CODIGO = re.compile(
    r"^(?:[a-z]{1,3}\d+(?:[_.]\d+)*"
    r"|g\d+q\d+(?:\[[^\]]*\])?"
    r"|q\d+(?:_\d+)*(?:\[[^\]]*\])?"
    r"|[^\s]{1,40}?[_.\-](?:item|reactivo)?[_.\-]?\d{1,3}"
    r"|(?:item|reactivo|pregunta)[_\s.\-]?\d{1,3})$"
)
# Columnas de datos de quien responde o del sistema: no cuentan como preguntas.
_RE_NO_PREGUNTA = re.compile(
    r"^(id|uuid|folio|respondente|respondent|participante|encuestado|matricula|edad|sexo|genero|turno|semestre|"
    r"grupo|carrera|escuela|plantel|campus|nombre|correo|email|e-mail|fecha|hora|marca temporal|timestamp|"
    r"submitdate|lastpage|startlanguage|seed|startdate|datestamp|refurl|ipaddr|token)\b"
)
_RE_PREGUNTA_LARGO = re.compile(r"^(pregunta|item|ítem|reactivo|question|variable|codigo|código)$")
_RE_VALOR_LARGO = re.compile(r"^(respuesta|valor|value|answer|opcion|opción)$")
_ESCALA = {"totalmente de acuerdo", "de acuerdo", "en desacuerdo", "totalmente en desacuerdo",
           "ni de acuerdo ni en desacuerdo", "si", "no", "nunca", "siempre", "a veces"}


def _norm(texto: str) -> str:
    sin = "".join(c for c in unicodedata.normalize("NFD", texto or "") if unicodedata.category(c) != "Mn")
    return " ".join(sin.lower().split())


def es_codigo(encabezado: str) -> bool:
    return bool(_RE_CODIGO.match(_norm(encabezado)))


def columnas_de_pregunta(encabezados: list[str]) -> list[str]:
    return [h for h in encabezados if h.strip() and not _RE_NO_PREGUNTA.match(_norm(h))]


def motivo_rechazo_encuesta(encabezados: list[str], filas: list[list[str]], hay_original: bool) -> str | None:
    """Motivo por el que la tabla de una encuesta no se puede procesar, o None."""
    normales = [_norm(h) for h in encabezados]
    # Formato largo: pocas columnas, una de «pregunta» y otra de «respuesta/valor».
    if len(encabezados) <= 6 and any(_RE_PREGUNTA_LARGO.match(h) for h in normales) \
            and any(_RE_VALOR_LARGO.match(h) for h in normales):
        return ("El archivo está en formato largo (una fila por respuesta). Conviértelo a una fila por "
                "respondente y una columna por pregunta (en Excel: tabla dinámica con las preguntas como columnas).")
    # Sin encabezados: la primera fila son respuestas (números o etiquetas de escala).
    no_vacios = [h for h in normales if h]
    if no_vacios and sum(h.replace(".", "", 1).isdigit() or h in _ESCALA for h in no_vacios) >= 0.6 * len(no_vacios):
        return ("La primera fila no tiene nombres de columna: parece una fila de respuestas. "
                "Agrega una fila de encabezados con el texto (o el código) de cada pregunta.")
    preguntas = columnas_de_pregunta(encabezados)
    if not hay_original and preguntas and sum(es_codigo(h) for h in preguntas) >= 0.5 * len(preguntas):
        return ("Los encabezados son códigos (por ejemplo «" + next(h for h in preguntas if es_codigo(h)) + "») "
                "y no se subió el instrumento original. Sube también el instrumento original (PDF, DOCX o TXT "
                "con las preguntas) para saber qué pregunta cada columna.")
    return None
