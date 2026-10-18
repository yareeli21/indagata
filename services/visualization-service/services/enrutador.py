"""Enrutador de consultas del chat: ruta ESTRUCTURADA (cálculo exacto) o semántica.

Las preguntas que piden un dato puntual o una cuenta («¿qué respondió R017 en la
pregunta 4?», «un respondente en desacuerdo en p3, p5 y p7», «% del turno
vespertino de acuerdo con p4», «reactivo con menor acierto», «qué dijo E02 sobre
la evaluación», «por qué el KPI X…») NO se responden con búsqueda semántica: aquí
se detecta la intención con reglas (sin LLM) y se calcula el resultado con
`shared/conocimiento/consultas.py` sobre el DOCUMENTO FINAL VIGENTE de cada
instrumento del alcance. Los porcentajes se cuentan sobre la tabla
`respuesta_interpretada` cuando el instrumento ya tiene filas (y si no, sobre el
documento: mismo resultado).

El LLM solo redacta: recibe el `RESULTADO CALCULADO` con la orden de no recalcular.
Si el resultado es «no existe», la respuesta se arma aquí sin LLM (más fiable que
pedirle a un modelo pequeño que comunique una ausencia sin inventar).

Si ninguna intención aplica, o el alcance no tiene instrumentos del tipo necesario,
`resolver` devuelve None y el chat sigue por la ruta semántica.
"""
from __future__ import annotations

import json
import logging
import re
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from shared.conocimiento import consultas
from shared.models.respuesta_interpretada import RespuestaInterpretada
from shared.models.version_conocimiento import VersionConocimiento

from services import storage_client
from services.dominio import normalizar

logger = logging.getLogger("visualization-service")

_MAX_INSTRUMENTOS = 10  # tope de documentos que se leen por consulta
_MAX_LINEAS_PERSONA = 15

_TIPO_UI = {"encuesta": "Encuesta", "entrevista": "Entrevista", "prueba_estandarizada": "Prueba estandarizada"}

# ── Documentos vigentes ────────────────────────────────────────────────────────


@dataclass
class Instrumento:
    id_crudo: str
    titulo: str
    tipo: str  # tipo del documento: encuesta | prueba_estandarizada | entrevista
    doc: dict[str, Any]

    @property
    def tipo_ui(self) -> str:
        return _TIPO_UI.get(self.tipo, "Encuesta")


_cache_docs: OrderedDict[str, dict[str, Any]] = OrderedDict()  # key del artefacto → documento (inmutable)


def _leer_documento(ruta: str) -> dict[str, Any] | None:
    if ruta in _cache_docs:
        _cache_docs.move_to_end(ruta)
        return _cache_docs[ruta]
    try:
        doc = json.loads(storage_client.descargar(ruta).contenido.decode("utf-8"))
    except (storage_client.StorageError, ValueError) as exc:
        logger.warning("No se pudo leer el documento vigente %s: %s", ruta, exc)
        return None
    _cache_docs[ruta] = doc
    if len(_cache_docs) > 32:
        _cache_docs.popitem(last=False)
    return doc


def cargar_documentos(sesion: Session, ids: list[str] | None) -> list[Instrumento]:
    """Documentos finales vigentes del alcance (todos los del acervo si `ids` está vacío)."""
    consulta = sesion.query(VersionConocimiento).filter(VersionConocimiento.estado == "vigente")
    numericos = [int(i) for i in ids or [] if str(i).isdigit()]
    if ids:
        consulta = consulta.filter(VersionConocimiento.id_crudo.in_(numericos))
    instrumentos: list[Instrumento] = []
    for fila in consulta.order_by(VersionConocimiento.id_crudo).limit(_MAX_INSTRUMENTOS):
        doc = _leer_documento(fila.ruta_documento) if fila.ruta_documento else None
        if doc:
            ins = doc.get("instrumento") or {}
            instrumentos.append(Instrumento(str(fila.id_crudo), ins.get("titulo") or f"Instrumento {fila.id_crudo}",
                                            ins.get("tipo") or "", doc))
    return instrumentos


# ── Detección de la intención (reglas, sin LLM) ────────────────────────────────

_NIVELES = [  # el orden importa: «desacuerdo» contiene «acuerdo»
    ("neutral", r"\b(neutral|neutrales|ni de acuerdo ni en desacuerdo|indiferentes?)\b"),
    ("desacuerdo", r"\b(en desacuerdo|desacuerdo|totalmente en desacuerdo)\b"),
    ("acuerdo", r"\b(de acuerdo|acuerdo)\b"),
    ("insatisfaccion", r"\b(insatisfech[oa]s?|insatisfaccion)\b"),
    ("satisfaccion", r"\b(satisfech[oa]s?|satisfaccion)\b"),
]
# IDs anónimos. «R17»/«A5» con pocos dígitos se confunden con reactivos o con
# palabras («a 3 preguntas»): se exigen 3+ dígitos (2+ en E) o la palabra completa.
_PERSONA = [
    ("R", re.compile(r"\br-?0*(\d{1,4})\b"), 3, re.compile(r"\br-?\d{3,5}\b")),
    ("A", re.compile(r"\ba-?0*(\d{1,4})\b"), 3, re.compile(r"\ba-?\d{3,5}\b")),
    ("E", re.compile(r"\be-?0*(\d{1,4})\b"), 2, re.compile(r"\be-?\d{2,5}\b")),
]
_PERSONA_PALABRA = re.compile(r"\b(respondente|encuestad[oa]|alumn[oa]|participante|entrevistad[oa])\s+(?:numero\s+|#\s*)?0*(\d{1,4})\b")
_PREGUNTA_SUELTA = re.compile(r"\b(?:p|q|pregunta|item|reactivo|r(?=\d{1,2}\b))\s?-?0*(\d{1,3})\b")
_PREGUNTAS_LISTA = re.compile(r"\b(?:preguntas|items|reactivos)\s+((?:p?\d{1,3}(?:\s*(?:,|y|e)\s*)?)+)")
_TEMA = re.compile(r"\b(?:sobre|acerca de|respecto a|respecto de|en relacion con)\s+(?:el |la |los |las |lo )?(.+?)\s*[?.!]*$")
_PORCENTAJE = re.compile(r"\b(porcentaje|por ciento|proporcion|cuantos|cuantas|que parte)\b|%")
_ALGUIEN = re.compile(r"\b(un|una|algun|alguna|algunos|que|cual|cuales|hay)\s+(respondente|persona|estudiante|encuestad[oa]|alumn[oa])s?\b")
_DIFICIL = re.compile(r"\b(menor|mas bajo|peor)\s+(porcentaje|%|indice|tasa)\s+de\s+acierto|\breactivo\s+mas\s+(dificil|fallado)|\bmas\s+dificil\b|\bmenos\s+acertad")
_KPI = re.compile(r"\b(kpi|kpis|indicador|indicadores)\b")
_KPI_PREGUNTAS = re.compile(r"\b(que|cuales)\s+(preguntas|reactivos|items)\b|\bcomo\s+respondieron\b")
_STOP = set("que cual cuales como donde cuando para por con sin sobre los las del una uno unos unas este esta estos estas "
            "pregunta preguntas respondio respondieron respondente dijo dice instrumento kpi kpis mide miden relacionado "
            "relacionada porque esta estan tiene tienen hay cuanto cuantos".split())


@dataclass
class Intencion:
    tipo: str  # respuesta | persona | respondente_con_nivel | pct_nivel | kpi | kpi_preguntas | reactivo_dificil | dijo
    persona: tuple[str, int] | None = None
    preguntas: list[int] = field(default_factory=list)
    nivel: str | None = None
    tema: str = ""
    texto: str = ""  # pregunta normalizada (para grupos y KPIs por nombre)


def _persona(texto: str) -> tuple[str, int] | None:
    for letra, patron, _ancho, estricto in _PERSONA:
        if estricto.search(texto) and (m := patron.search(texto)):
            return letra, int(m.group(1))
    if m := _PERSONA_PALABRA.search(texto):
        letra = {"respondente": "R", "encuestado": "R", "encuestada": "R", "alumno": "A", "alumna": "A"}.get(m.group(1), "E")
        return letra, int(m.group(2))
    return None


def _preguntas(texto: str) -> list[int]:
    numeros: list[int] = []
    for m in _PREGUNTAS_LISTA.finditer(texto):
        numeros += [int(n) for n in re.findall(r"\d{1,3}", m.group(1))]
    sin_personas = texto
    for _letra, _patron, _ancho, estricto in _PERSONA:
        sin_personas = estricto.sub(" ", sin_personas)
    numeros += [int(n) for n in _PREGUNTA_SUELTA.findall(sin_personas)]
    return list(dict.fromkeys(numeros))


def _nivel(texto: str) -> str | None:
    for nivel, patron in _NIVELES:
        if re.search(patron, texto):
            return nivel
    return None


def detectar(pregunta: str) -> Intencion | None:
    """Intención estructurada de la pregunta, o None si es una pregunta abierta."""
    texto = normalizar(pregunta)
    persona, preguntas, nivel = _persona(texto), _preguntas(texto), _nivel(texto)
    tema = (m.group(1).strip() if (m := _TEMA.search(texto)) else "")
    base = {"persona": persona, "preguntas": preguntas, "nivel": nivel, "tema": tema, "texto": texto}
    if _DIFICIL.search(texto):
        return Intencion("reactivo_dificil", **base)
    if _KPI.search(texto):
        return Intencion("kpi_preguntas" if _KPI_PREGUNTAS.search(texto) else "kpi", **base)
    if persona and persona[0] == "E":
        return Intencion("dijo", **base)
    if nivel and _PORCENTAJE.search(texto) and (preguntas or tema):
        return Intencion("pct_nivel", **base)
    if nivel and preguntas and (_ALGUIEN.search(texto) or not persona):
        return Intencion("respondente_con_nivel", **base)
    if persona:
        return Intencion("respuesta" if (preguntas or tema) else "persona", **base)
    return None


# ── Utilidades sobre el documento ──────────────────────────────────────────────


def _corto(id_completo: str) -> str:
    return str(id_completo or "").rsplit("-", 1)[-1]


def _items(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return doc.get("preguntas") or doc.get("reactivos") or []


def _por_numero(doc: dict[str, Any], numero: int) -> dict[str, Any] | None:
    """Pregunta (o reactivo) cuyo ID corto termina en ese número: 4 → «p04»/«r04»."""
    return next((p for p in _items(doc) if re.fullmatch(rf"[a-z]+0*{numero}", _corto(p["id"]))), None)


def _tokens(texto: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", normalizar(texto)) if len(t) >= 4 and t not in _STOP}


def _por_texto(doc: dict[str, Any], texto: str) -> dict[str, Any] | None:
    """La pregunta que comparte más palabras con `texto` (al menos una significativa)."""
    buscadas = _tokens(texto)
    mejor, puntos = None, 0
    for p in _items(doc):
        comunes = len(buscadas & _tokens(p.get("texto", "")))
        if comunes > puntos:
            mejor, puntos = p, comunes
    return mejor


def _resolver_pregunta(doc: dict[str, Any], intencion: Intencion) -> dict[str, Any] | None:
    if intencion.preguntas:
        return _por_numero(doc, intencion.preguntas[0])
    return _por_texto(doc, intencion.tema or intencion.texto)


def _id_persona(persona: tuple[str, int]) -> str:
    letra, numero = persona
    ancho = next(a for l, _p, a, _e in _PERSONA if l == letra)
    return f"{letra}{numero:0{ancho}d}"


def _grupo(doc: dict[str, Any], texto: str) -> dict[str, str]:
    """Filtro de contexto mencionado en la pregunta: «del turno vespertino» → {turno: Vespertino}."""
    personas = doc.get("respondentes") or doc.get("alumnos") or []
    for clave, valor in {(k, str(v)) for p in personas for k, v in (p.get("contexto") or {}).items() if v not in (None, "")}:
        if len(valor) >= 3 and not valor.isdigit() and re.search(rf"\b{re.escape(normalizar(valor))}\b", texto):
            return {clave: valor}
    return {}


def _conteo(sesion: Session, ins: Instrumento, pregunta_id: str, nivel: str, contexto: dict[str, str]) -> tuple[int, int]:
    """(en el nivel, total) desde `respuesta_interpretada`; si no hay filas, desde el documento."""
    filas = (
        sesion.query(RespuestaInterpretada)
        .filter(RespuestaInterpretada.id_crudo == int(ins.id_crudo), RespuestaInterpretada.pregunta_id == pregunta_id)
        .all()
    )
    if not filas:
        return consultas.conteo_nivel(ins.doc, pregunta_id, nivel, contexto)
    filtro = {normalizar(k): normalizar(v) for k, v in contexto.items()}
    total = en_nivel = 0
    for f in filas:
        ctx = {normalizar(k): normalizar(v) for k, v in (f.contexto or {}).items() if v is not None}
        if any(ctx.get(k) != v for k, v in filtro.items()) or f.estado != "respondida":
            continue
        total += 1
        en_nivel += f.nivel == nivel
    return en_nivel, total


def _lista_ids(ids: list[str]) -> str:
    cortos = [_corto(i) for i in ids]
    return cortos[0] if len(cortos) == 1 else ", ".join(cortos[:-1]) + " y " + cortos[-1]


_FRASE_NIVEL = {"acuerdo": "de acuerdo", "desacuerdo": "en desacuerdo", "neutral": "en posición neutral",
                "satisfaccion": "satisfecho", "insatisfaccion": "insatisfecho"}


# ── Ejecución ──────────────────────────────────────────────────────────────────


@dataclass
class Resultado:
    consulta: str
    encontrado: bool
    # Por instrumento: (instrumento, líneas del resultado calculado, ¿encontró algo?)
    partes: list[tuple[Instrumento, list[str], bool]]
    # «Qué dijo E02 sobre X» sin ninguna mención literal de X: se le dan al modelo todas
    # las respuestas de la persona y es VÁLIDO que concluya que no habló de X.
    admite_negativa: bool = False

    @property
    def instrumentos(self) -> list[Instrumento]:
        return [p[0] for p in self.partes]

    def texto(self, numeros: dict[str, int]) -> str:
        """Bloque RESULTADO CALCULADO para el prompt (con el [Fuente n] de cada instrumento)."""
        bloques = []
        for ins, lineas, _ in self.partes:
            bloques.append(f"[Fuente {numeros.get(ins.id_crudo, '?')}] {ins.titulo} ({ins.tipo_ui}):\n" + "\n".join(f"- {l}" for l in lineas))
        return "\n\n".join(bloques)

    def respuesta_directa(self, numeros: dict[str, int]) -> str:
        """Respuesta sin LLM (cuando nada se encontró): las líneas, con su fuente."""
        return "\n".join(f"{l} [Fuente {numeros.get(ins.id_crudo, '?')}]" for ins, lineas, _ in self.partes for l in lineas)


def _ejecutar_en(intencion: Intencion, ins: Instrumento, sesion: Session) -> tuple[list[str], bool] | None:
    """Líneas del resultado y si se encontró, o None si la consulta no aplica a este instrumento."""
    doc, t = ins.doc, intencion.tipo
    if t == "reactivo_dificil":
        if ins.tipo != "prueba_estandarizada":
            return None
        r = consultas.reactivo_mas_dificil(doc)
        if r is None:
            return ["La prueba no tiene reactivos calificables con porcentaje de acierto."], False
        d = r["distractor_mas_elegido"]
        distractor = f" El distractor más elegido fue {d['opcion']} ({d.get('significado')}) con {d['pct']} %." if d else " No hubo un distractor elegido."
        return [f"El reactivo con menor acierto es {_corto(r['reactivo_id'])} «{r['texto']}»: {r['pct_acierto']} % de acierto.{distractor}"], True

    if t in ("kpi", "kpi_preguntas"):
        kpi = _kpi_mencionado(doc, intencion.texto)
        if kpi is None:
            return None
        if t == "kpi":
            info = consultas.info_kpi(doc, kpi["kpi_id"])
            lineas = [f"KPI «{info['nombre']}»: {info['definicion']}", f"Qué mide: {info['que_mide']}",
                      f"Por qué se asoció a este instrumento: {info['justificacion']}"]
            for e in info["evidencia"]:
                interpretacion = (e.get("resumen") or {}).get("interpretacion") or ""
                lineas.append(f"Pregunta de evidencia {_corto(e['pregunta_id'])} «{e.get('texto')}» (similitud {e['similitud']}). {interpretacion}".strip())
            return lineas, True
        preguntas = consultas.preguntas_de_kpi(doc, kpi["kpi_id"])
        if not preguntas:
            return [f"Ninguna pregunta de este instrumento está marcada como evidencia del KPI «{kpi['nombre']}»."], False
        lineas = [f"Preguntas que miden el KPI «{kpi['nombre']}»:"]
        for p in preguntas:
            res = p.get("resumen") or {}
            como = res.get("interpretacion") or (f"{res.get('pct_acierto')} % de acierto" if res.get("pct_acierto") is not None else "")
            lineas.append(f"{_corto(p['pregunta_id'])} «{p['texto']}»: {como}".rstrip(": "))
        return lineas, True

    if t == "dijo":
        if ins.tipo != "entrevista":
            return None
        quien = _id_persona(intencion.persona)
        intercambios = consultas.dijo(doc, quien, intencion.tema) if intencion.tema else []
        existe = any(e["participante"].endswith(f"-{quien}") for e in doc.get("entrevistas") or [])
        if not existe:
            return [f"No existe el participante {quien} en esta entrevista."], False
        literal = bool(intercambios)
        if not intercambios:  # sin coincidencia literal del tema: todas sus respuestas (el LLM elige)
            e = next(x for x in doc["entrevistas"] if x["participante"].endswith(f"-{quien}"))
            intercambios = [{"pregunta_id": i.get("pregunta_id"), "pregunta": i["pregunta"], "respuesta": i["respuesta"]} for i in e["intercambios"]]
        nota = [] if literal or not intencion.tema else [f"(Ninguna respuesta de {quien} menciona literalmente «{intencion.tema}»; estas son todas sus respuestas.)"]
        return nota + [f"{quien}, pregunta {_corto(i.get('pregunta_id') or '') or '-'} «{i['pregunta']}»: «{i['respuesta']}»"
                       for i in intercambios[:_MAX_LINEAS_PERSONA]], True

    if ins.tipo not in ("encuesta", "prueba_estandarizada") or (t != "persona" and t != "respuesta" and ins.tipo != "encuesta"):
        return None

    if t == "pct_nivel":
        p = _resolver_pregunta(doc, intencion)
        if p is None:
            return [f"No existe la pregunta {intencion.preguntas[0] if intencion.preguntas else intencion.tema} en este instrumento."], False
        grupo = _grupo(doc, intencion.texto)
        en_nivel, total = _conteo(sesion, ins, p["id"], intencion.nivel, grupo)
        quienes = f" del grupo {', '.join(f'{k} = {v}' for k, v in grupo.items())}" if grupo else ""
        if not total:
            return [f"Nadie{quienes} respondió válidamente la pregunta {_corto(p['id'])} «{p['texto']}»."], False
        pct = round(100 * en_nivel / total, 1)
        return [f"En la pregunta {_corto(p['id'])} «{p['texto']}», el {pct} % ({en_nivel} de {total}) de quienes respondieron{quienes} "
                f"está {_FRASE_NIVEL.get(intencion.nivel, intencion.nivel)}."], True

    if t == "respondente_con_nivel":
        ids = [p["id"] for n in intencion.preguntas if (p := _por_numero(doc, n))]
        if len(ids) != len(intencion.preguntas):
            return [f"No existen todas las preguntas {', '.join(map(str, intencion.preguntas))} en este instrumento."], False
        frase = _FRASE_NIVEL.get(intencion.nivel, intencion.nivel)
        quien = consultas.respondente_con_nivel(doc, ids, intencion.nivel)
        if quien is None:
            return [f"No existe ningún respondente que esté {frase} en {_lista_ids(ids)} a la vez."], False
        return [f"El respondente {_corto(quien)} está {frase} en {_lista_ids(ids)}."], True

    # respuesta / persona (encuesta: respondente R###; prueba: alumno A###)
    quien = _id_persona(intencion.persona)
    # Los respondentes (R) son de encuestas y los alumnos (A), de pruebas.
    if quien[0] != ("A" if ins.tipo == "prueba_estandarizada" else "R"):
        return None
    personas = doc.get("respondentes") or doc.get("alumnos") or []
    persona = next((x for x in personas if x["id"].endswith(f"-{quien}")), None)
    if persona is None:
        return [f"No existe {quien} en este instrumento."], False
    contexto = "; ".join(f"{k}: {v}" for k, v in (persona.get("contexto") or {}).items() if v not in (None, ""))
    encabezado = f"{quien}" + (f" ({contexto})" if contexto else "")
    if ins.tipo == "prueba_estandarizada":
        lineas = [f"{encabezado}: puntaje {persona.get('puntaje')} de {persona.get('total')} ({persona.get('porcentaje')} %)."]
        for x in persona["respuestas"][:_MAX_LINEAS_PERSONA]:
            marca = "correcta" if x.get("correcta") is True else "incorrecta" if x.get("correcta") is False else x.get("estado", "")
            lineas.append(f"{_corto(x['reactivo_id'])}: {x.get('respuesta') or 'sin respuesta'} {marca}")
        return lineas, True
    if t == "respuesta":
        p = _resolver_pregunta(doc, intencion)
        if p is None:
            return [f"No existe la pregunta {intencion.preguntas[0] if intencion.preguntas else intencion.tema} en este instrumento."], False
        r = consultas.respuesta(doc, quien, pregunta_id=p["id"])
        if r is None:
            return [f"{quien} no tiene respuesta registrada en la pregunta {_corto(p['id'])}."], False
        if r.get("estado") != "respondida":
            return [f"{encabezado} no respondió la pregunta {_corto(p['id'])} «{p['texto']}» ({r.get('motivo') or r.get('estado')})."], True
        nivel = f" (nivel: {r['nivel']})" if r.get("nivel") else ""
        return [f"{encabezado} respondió «{r.get('significado') or r.get('valor')}»{nivel} en la pregunta {_corto(p['id'])} «{p['texto']}»."], True
    lineas = [f"Respuestas de {encabezado}:"]
    for x in persona["respuestas"][:_MAX_LINEAS_PERSONA]:
        valor = x.get("significado") or x.get("valor") if x.get("estado") == "respondida" else f"sin respuesta ({x.get('motivo') or x.get('estado')})"
        lineas.append(f"{_corto(x['pregunta_id'])} «{x['pregunta']}»: {valor}")
    return lineas, True


def _kpi_mencionado(doc: dict[str, Any], texto: str) -> dict[str, Any] | None:
    """KPI asociado al documento que la pregunta menciona (por ID «KPI-07» o por nombre)."""
    kpis = doc.get("kpis_asociados") or []
    if m := re.search(r"\bkpi[-\s]?0*(\d+)\b", texto):
        return next((k for k in kpis if re.fullmatch(rf"kpi-?0*{m.group(1)}", normalizar(str(k["kpi_id"])))), None)
    palabras = _tokens(texto)
    mejor, puntos = None, 0
    for k in kpis:
        comunes = len(palabras & _tokens(k.get("nombre", "")))
        if comunes > puntos:
            mejor, puntos = k, comunes
    return mejor


def resolver(pregunta: str, sesion: Session, ids: list[str] | None) -> Resultado | None:
    """Resultado calculado para la pregunta, o None si va por la ruta semántica."""
    intencion = detectar(pregunta)
    if intencion is None:
        return None
    partes: list[tuple[Instrumento, list[str], bool]] = []
    for ins in cargar_documentos(sesion, ids):
        try:
            salida = _ejecutar_en(intencion, ins, sesion)
        except (KeyError, TypeError, ValueError) as exc:  # documento con una forma inesperada
            logger.warning("Consulta %s falló en el instrumento %s: %s", intencion.tipo, ins.id_crudo, exc)
            continue
        if salida is not None:
            partes.append((ins, *salida))
    if not partes:
        return None
    # Si en algún instrumento sí se encontró, los «no existe» de los demás sobran.
    if any(encontro for _, _, encontro in partes):
        partes = [p for p in partes if p[2]]
    sin_coincidencia = intencion.tipo == "dijo" and any(l.startswith("(Ninguna respuesta") for _, ls, _ in partes for l in ls)
    return Resultado(intencion.tipo, any(p[2] for p in partes), partes, admite_negativa=sin_coincidencia)
