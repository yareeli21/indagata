"""Documento final de una entrevista: solo preguntas y respuestas en texto.

Una entrevista es texto plano: el documento NO lleva estadísticas ni conteos, solo
lo que sirve como insumo del RAG:
  - `preguntas`: las del guion (o del entrevistador), con los KPIs que las citan.
  - `entrevistas`: una por persona entrevistada, con sus intercambios
    {pregunta_id?, pregunta, respuesta}.

Cómo se arman los intercambios:
  - Si la limpieza trae la columna `participante` (varias entrevistas en un archivo,
    «RESPONDENTE: R0001»), cada bloque es una entrevista. Si no, cada hablante
    entrevistado es una entrevista.
  - Los turnos del entrevistador forman la PREGUNTA (si habla varias veces seguidas,
    antes de preguntar, todo es la misma pregunta); lo que dice el entrevistado hasta la siguiente
    pregunta es SU respuesta.
  - Las preguntas sin respuesta no generan intercambio.

Privacidad: las personas se anonimizan (E01, E02… por orden de aparición) y los
nombres de los hablantes se reemplazan también dentro de los textos. El contexto de
cada persona (las líneas «Edad: 21 | Turno: matutino» de su bloque) entra al documento
como en las encuestas: sin datos personales (nombre, correo, matrícula…), que se avisan.
Antes no entraba, y el chat no podía responder «¿en qué turno estudia?» (Fase 6, 2 nov;
decisión de la investigadora). Otros nombres mencionados en el texto libre NO se pueden
detectar con certeza: se avisa.
"""
from __future__ import annotations

import re
from typing import Any

from services.documento import comun
from services.estructura import Estructura
from services.interpretacion.privacidad import es_dato_personal
from services.original import UMBRAL_PARECIDO, parecido

ESQUEMA_VERSION = "2.0"
_SIN_PREGUNTA = "(sin pregunta previa del entrevistador)"
_GENERICAS = {"e", "p", "r", "desconocido", "entrevistador", "entrevistadora", "entrevistado", "entrevistada"}


def _anonimizar(texto: str, reemplazos: list[tuple[re.Pattern[str], str]]) -> str:
    for patron, id_corto in reemplazos:
        texto = patron.sub(id_corto, texto)
    return texto


def _contextos(reporte: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """{participante del bloque: contexto} del reporte de limpieza («Edad: 21 | Turno: matutino»), sin datos personales
    (la misma regla que el contexto de las encuestas). Las claves quitadas quedan en «__personales__» para el aviso."""
    especifico = reporte.get("especifico") or {}
    participantes = (especifico.get("entrevista") or especifico).get("participantes") or []
    salida: dict[str, dict[str, Any]] = {}
    for p in participantes:
        contexto = {str(k): v for k, v in (p.get("contexto") or {}).items() if v not in (None, "")}
        personales = [k for k in contexto if es_dato_personal(k)]
        limpio: dict[str, Any] = {k: v for k, v in contexto.items() if k not in personales}
        if personales:
            limpio["__personales__"] = personales
        if limpio:
            salida[str(p.get("id") or "").strip()] = limpio
    return salida


def construir(perfil: dict[str, Any], estructura: Estructura, reporte: dict[str, Any], filas: list[dict[str, str]]) -> dict[str, Any]:
    ins = perfil["instrumento_id"]
    kpis_de = comun.kpis_por_pregunta(perfil.get("kpis_asociados") or [])
    avisos: list[dict[str, Any]] = []
    con_bloques = any((f.get("participante") or "").strip() for f in filas)

    def hablante(f: dict[str, str]) -> str:
        return (f.get("hablante") or "").strip() or "desconocido"

    def es_entrevistador(f: dict[str, str]) -> bool:
        return (f.get("rol") or "").strip() == "entrevistador"

    def persona(f: dict[str, str]) -> str:
        return (f.get("participante") or "").strip() if con_bloques else hablante(f)

    # Texto sin hablante (rol «desconocido») en una entrevista que sí tiene entrevistador: es un
    # preámbulo («Entrevista realizada en la biblioteca…»), no otra persona entrevistada.
    hay_entrevistador = any(es_entrevistador(f) for f in filas)

    def fuera(f: dict[str, str]) -> bool:
        return hay_entrevistador and (f.get("rol") or "").strip() in ("", "desconocido")

    omitidas = sum(1 for f in filas if fuera(f) and (f.get("texto") or "").strip())

    # IDs anónimos por orden de aparición de cada persona entrevistada.
    ids: dict[str, str] = {}
    for f in filas:
        if not es_entrevistador(f) and not fuera(f) and (clave := persona(f)) and clave not in ids:
            ids[clave] = f"{ins}-E{len(ids) + 1:02d}"
    # Los nombres de los hablantes (más largos primero) se reemplazan dentro de los textos.
    nombres = {hablante(f): ids.get(persona(f), "") for f in filas if not con_bloques and not es_entrevistador(f)}
    reemplazos = [
        (re.compile(rf"(?<!\w){re.escape(h)}(?!\w)", re.IGNORECASE), i.split("-", 2)[-1])
        for h, i in sorted(nombres.items(), key=lambda x: -len(x[0]))
        if i and len(h) >= 2 and h.lower() not in _GENERICAS
    ]

    guia = estructura.preguntas

    def pregunta_guia(texto: str):  # noqa: ANN202
        mejor = max(((parecido(texto, g.texto), g) for g in guia), default=(0.0, None), key=lambda x: x[0])
        return mejor[1] if mejor[0] >= UMBRAL_PARECIDO else None

    entrevistas: dict[str, list[dict[str, Any]]] = {}
    pregunta, bloque, ultimo = _SIN_PREGUNTA, None, None  # ultimo: (persona, intercambio) para unir turnos
    pregunta_continua = False
    for f in filas:
        texto = " ".join((f.get("texto") or "").split())
        if not texto or fuera(f):
            continue
        if con_bloques and persona(f) != bloque:
            bloque, pregunta, ultimo, pregunta_continua = persona(f), _SIN_PREGUNTA, None, False
        if es_entrevistador(f):
            # «Gracias.» + «¿Y la escuela?» es una sola pregunta; dos preguntas seguidas
            # sin respuesta en medio (P2 sin contestar, luego P3) no se unen.
            pregunta = f"{pregunta} {texto}" if pregunta_continua and "?" not in pregunta else texto
            pregunta_continua, ultimo = True, None
            continue
        pregunta_continua = False
        clave = persona(f)
        if ultimo is not None and ultimo[0] == clave:
            ultimo[1]["respuesta"] = f"{ultimo[1]['respuesta']} {_anonimizar(texto, reemplazos)}"
            continue
        item: dict[str, Any] = {}
        g = pregunta_guia(pregunta) if pregunta != _SIN_PREGUNTA else None
        if g is not None:
            item["pregunta_id"] = g.id
        item["pregunta"] = _anonimizar(pregunta, reemplazos)
        item["respuesta"] = _anonimizar(texto, reemplazos)
        entrevistas.setdefault(clave, []).append(item)
        ultimo = (clave, item)

    contextos = _contextos(reporte) if con_bloques else {}
    if quitados := sorted({k for c in contextos.values() for k in c.pop("__personales__", [])}):
        avisos.append({"codigo": "contexto_personal", "mensaje": f"Datos personales del contexto no incluidos: {', '.join(quitados)}."})

    if omitidas:
        avisos.append({"codigo": "texto_sin_hablante", "mensaje": f"{omitidas} fragmento(s) sin hablante (por ejemplo, un preámbulo) no se tomaron como respuestas."})
    if ids:
        avisos.append({"codigo": "texto_libre", "mensaje": "Las personas entrevistadas se identifican con un ID anónimo; otros nombres mencionados en el texto libre podrían seguir presentes."})
    if not any(es_entrevistador(f) for f in filas):
        avisos.append({"codigo": "sin_entrevistador", "mensaje": "No se identificó al entrevistador: los intercambios no tienen pregunta."})

    return {
        "esquema_version": ESQUEMA_VERSION,
        "instrumento": comun.instrumento(perfil),
        "kpis_asociados": perfil.get("kpis_asociados") or [],
        "preguntas": [{"id": g.id, "texto": g.texto, "kpis_relacionados": kpis_de.get(g.id, [])} for g in guia],
        "entrevistas": [{"participante": ids[k], **({"contexto": contextos[k]} if contextos.get(k) else {}), "intercambios": v}
                        for k, v in entrevistas.items()],
        "avisos": avisos,
    }
