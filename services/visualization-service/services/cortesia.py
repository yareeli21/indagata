"""Saludos, cortesía, consejos personales y malestar en el chat (7 nov 2026, Fase 3).

Se detectan con reglas, sin gastar la interpretación, y se responden con un mensaje fijo que dice con qué
instrumento se trabaja y da ejemplos de preguntas sacados del catálogo de ESE instrumento (no ejemplos fijos: en la
prueba de la investigadora, «hola» recibía el mensaje de fuera de dominio con «¿qué respondió R017?» en una entrevista).

  cortesia   «hola», «¿qué tal?», «¿qué puedes hacer?», «gracias», «adiós».
  consejo    consejos o recomendaciones personales («¿qué carrera me recomiendas?»). No se dan: es una herramienta de
             investigación. «¿Qué recomendarían los estudiantes?» o «¿qué cambiaría la participante?» SÍ se responden:
             piden datos, no un consejo para quien pregunta.
  malestar   la persona dice que se siente mal («estoy muy estresada con mis exámenes»): respuesta amable, sin
             consejos propios, con la sugerencia de acudir a los servicios de apoyo de su institución.
  sin_calificar  con una prueba en el alcance, «¿cuántos aprobaron?», «¿cuál fue el promedio?» sin nombrar un reactivo:
             las pruebas no se califican; se ofrece lo que sí hay (qué eligieron en cada reactivo).
"""
from __future__ import annotations

import re
from typing import Any

from services.dominio import normalizar

CORTESIA, CONSEJO, MALESTAR, SIN_CALIFICAR = "cortesia", "consejo", "malestar", "sin_calificar"

_SALUDO = re.compile(r"^(?:hola|buen(?:os|as) (?:dias|tardes|noches)|buenas|que tal|hey|saludos|que onda)\b")
_CAPACIDAD = re.compile(r"\b(?:que (?:puedes|sabes) hacer|en que (?:me )?(?:puedes|podrias) ayudar|como funcionas|"
                        r"que (?:te )?puedo preguntar|para que sirves|que haces)\b")
_GRACIAS = re.compile(r"^(?:muchas |mil )?gracias\b|^(?:te )?agradezco\b|^(?:ok|vale|perfecto|excelente),? gracias\b")
_ADIOS = re.compile(r"^(?:adios|hasta (?:luego|pronto|manana)|nos vemos|bye|chao)\b")
_MAX_PALABRAS_CORTESIA = 8

_CONSEJO = re.compile(
    r"\b(?:que|cual|cuales) (?:\w+ )?(?:me )?(?:recomiendas|recomendarias|aconsejas|aconsejarias|sugieres)\b"
    r"|\bme (?:recomiendas|aconsejas|sugieres|recomendarias)\b|\b(?:recomiendame|aconsejame|sugiereme)\b"
    r"|\bdame (?:un |unos |algun )?consejos?\b|\bque (?:debo|deberia|puedo) hacer (?:para|si|con)\b")
# Lo que sí se responde aunque diga «recomiendas»: análisis de los datos, el instrumento o la plataforma.
_SOBRE_LOS_DATOS = re.compile(r"\b(?:analisis|analizar|prueba estadistica|grafic\w*|instrumento|encuesta|entrevista|"
                              r"pregunta|reactivo|kpi|indicador|dato|datos|resultado|resultados|plataforma|indagata)\b")
_MALESTAR = re.compile(
    r"\b(?:estoy|me siento|ando|me encuentro)\s+(?:muy\s+|bien\s+|super\s+|demasiado\s+|bastante\s+)?"
    r"(?:estresad|ansios|deprimid|triste|agobiad|abrumad|desesperad|cansad|nervios|preocupad|angustiad|mal\b)\w*"
    r"|\bno puedo mas\b|\bya no aguanto\b")

_CALIFICACION = re.compile(r"\b(?:aprob\w*|reprob\w*|promedio|calificacion\w*|puntaje\w*|nota final|aciertos?)\b")
_REACTIVO = re.compile(r"\breactivo\b|\br\s?\d{1,3}\b|\bpregunta\s+\d")


def detectar(pregunta: str, tipos: set[str]) -> str | None:
    texto = normalizar(pregunta)
    palabras = len(texto.split())
    if _MALESTAR.search(texto):
        return MALESTAR
    if _CONSEJO.search(texto) and not _SOBRE_LOS_DATOS.search(texto):
        return CONSEJO
    if palabras <= _MAX_PALABRAS_CORTESIA and (_SALUDO.search(texto) or _GRACIAS.search(texto) or _ADIOS.search(texto)):
        return CORTESIA
    if _CAPACIDAD.search(texto):
        return CORTESIA
    if tipos == {"prueba_estandarizada"} and _CALIFICACION.search(texto) and not _REACTIVO.search(texto):
        return SIN_CALIFICAR
    return None


# ── Ejemplos sacados del catálogo ─────────────────────────────────────────────


def _corto(id_completo: str) -> str:
    return str(id_completo or "").rsplit("-", 1)[-1]


def _recorte(texto: Any, n: int = 60) -> str:
    texto = " ".join(str(texto or "").split()).rstrip("?¿.: ")
    texto = texto.lstrip("¿")
    return texto if len(texto) <= n else texto[: n - 1].rstrip() + "…"


def _repartidas(items: list[dict[str, Any]], n: int) -> list[dict[str, Any]]:
    """n elementos repartidos a lo largo de la lista (primero, en medio, al final)."""
    if len(items) <= n:
        return items
    return [items[round(k * (len(items) - 1) / max(1, n - 1))] for k in range(n)]


def ejemplos(ins: Any) -> list[str]:
    """Tres preguntas de ejemplo con las preguntas, opciones y personas de ESE instrumento."""
    doc = ins.doc or {}
    if ins.tipo == "encuesta":
        preguntas = [p for p in doc.get("preguntas") or [] if p.get("texto") and p.get("tipo") != "sin_datos"]
        salida = []
        for p in _repartidas(preguntas, 3):
            dist = (p.get("resumen") or {}).get("distribucion") or []
            if p.get("escala") or p.get("tipo") in ("likert", "escala") or not dist:
                salida.append(f"¿Cómo se reparten las respuestas de «{_recorte(p['texto'])}» ({_corto(p['id'])})?")
            else:
                salida.append(f"¿Cuántos respondieron «{dist[0]['significado']}» en «{_recorte(p['texto'])}»?")
        if len(preguntas) >= 2:
            salida[-1] = f"¿Qué es lo más preocupante de los resultados de «{_recorte(ins.titulo, 50)}»?"
        return salida
    if ins.tipo == "prueba_estandarizada":
        reactivos = _repartidas(doc.get("reactivos") or [], 2)
        alumnos = doc.get("alumnos") or []
        salida = [f"¿Qué opción eligieron más en el reactivo {_corto(r['id'])} («{_recorte(r.get('texto'))}»)?" for r in reactivos]
        if alumnos:
            salida.append(f"¿Qué respondió el alumno {_corto(alumnos[0]['id'])}?")
        return salida[:3]
    if ins.tipo == "entrevista":
        guia = _repartidas(doc.get("preguntas") or [], 2)
        participantes = doc.get("entrevistas") or []
        quien = _corto(participantes[0]["participante"]) if participantes else "la participante"
        salida = [f"¿Qué dijo {quien} sobre «{_recorte(g.get('texto'))}»?" for g in guia]
        salida.append("¿Cuáles son los hallazgos principales de la entrevista?")
        return salida[:3]
    return []


def _instrumentos(instrumentos: list[Any]) -> str:
    nombres = [f"«{i.titulo}» ({i.tipo_ui.lower()})" for i in instrumentos[:3]]
    if not nombres:
        return ""
    return nombres[0] if len(nombres) == 1 else ", ".join(nombres[:-1]) + " y " + nombres[-1]


def _lista_ejemplos(instrumentos: list[Any]) -> str:
    vistos: list[str] = []
    for ins in instrumentos[:2]:
        vistos += [e for e in ejemplos(ins) if e not in vistos]
    return "\n".join(f"- {e}" for e in vistos[:3])


# ── Respuestas ────────────────────────────────────────────────────────────────


def responder(tipo: str, pregunta: str, instrumentos: list[Any]) -> str:
    texto = normalizar(pregunta)
    con = _instrumentos(instrumentos)
    trabajo = f"Estás trabajando con {con}." if con else "Aún no tienes instrumentos seleccionados en esta investigación."
    lista = _lista_ejemplos(instrumentos)
    pide = f"\n\nPor ejemplo, puedes preguntarme:\n{lista}" if lista else ""
    if tipo == CORTESIA:
        if _GRACIAS.search(texto):
            return "¡Con gusto! Si quieres, sigue preguntando sobre tus instrumentos."
        if _ADIOS.search(texto):
            return "¡Hasta luego! La conversación queda guardada en esta investigación."
        if _CAPACIDAD.search(texto):
            return (f"Soy el asistente de investigación de INDAGATA. {trabajo} Puedo:\n"
                    "- darte datos: cuántos o qué porcentaje respondió algo, y quiénes (con IDs anónimos);\n"
                    "- comparar grupos o preguntas;\n"
                    "- explicarte el instrumento: de qué trata, sus preguntas, opciones y KPIs;\n"
                    "- en entrevistas, decirte qué contó cada participante, con sus palabras." + pide)
        return f"¡Hola! Soy el asistente de investigación de INDAGATA. {trabajo}" + pide
    if tipo == CONSEJO:
        return ("No doy consejos ni recomendaciones personales: soy una herramienta de investigación sobre los "
                f"instrumentos cargados. {trabajo} Lo que sí puedo hacer es consultar sus datos." + pide)
    if tipo == MALESTAR:
        return ("Lamento que te sientas así. No puedo darte consejos porque soy una herramienta de investigación, pero "
                "te sugiero acudir a los servicios de apoyo psicológico o de orientación de tu institución. Cuando "
                "quieras, puedo seguir con tus consultas sobre los instrumentos.")
    if tipo == SIN_CALIFICAR:
        return ("Indagata no califica las pruebas: no tiene clave de respuestas, así que no hay aprobados, promedios ni "
                "puntajes. Lo que sí puedo mostrarte es qué eligieron los alumnos en cada reactivo, cuántos los "
                "dejaron en blanco y cómo se repartieron las respuestas." + pide)
    return ""
