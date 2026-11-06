"""Enrutador de consultas del chat: ruta ESTRUCTURADA (cálculo exacto) o semántica.

Las preguntas que piden un dato puntual o una cuenta («¿qué respondió R017 en la
pregunta 4?», «un respondente en desacuerdo en p3, p5 y p7», «% del turno
vespertino de acuerdo con p4», «qué eligieron en el reactivo 3», «qué dijo E02 sobre
la evaluación», «por qué el KPI X…») NO se responden con búsqueda semántica: aquí
se detecta la intención con reglas (sin LLM) y se calcula el resultado con
`shared/conocimiento/consultas.py` sobre el DOCUMENTO FINAL VIGENTE de cada
instrumento del alcance. Los porcentajes se cuentan sobre la tabla
`respuesta_interpretada` cuando el instrumento ya tiene filas (y si no, sobre el
documento: mismo resultado).

El LLM solo redacta: recibe el `RESULTADO CALCULADO` con la orden de no recalcular.
Si el resultado es «no existe», la respuesta se arma aquí sin LLM (más fiable que
pedirle a un modelo pequeño que comunique una ausencia sin inventar).

Las consultas con FILTRO («uno de los estudiantes que sí reprobaron por falta de
tiempo», «cuántos trabajan más de 30 horas») arman sus condiciones con reglas sobre el
catálogo de preguntas y opciones del propio documento; si las reglas no alcanzan,
`filtro_llm` le pide a Ollama SOLO la condición (pregunta y opciones), que se valida
contra ese catálogo antes de contar. Nunca se ejecuta SQL generado por el modelo.

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

from shared.conocimiento import consultas, sugerencias
from shared.db.core.config import settings
from shared.models.limpieza_ejecucion import LimpiezaEjecucion
from shared.models.respuesta_interpretada import RespuestaInterpretada
from shared.models.version_conocimiento import VersionConocimiento

from services import storage_client
from services.dominio import es_definicion, normalizar

logger = logging.getLogger("visualization-service")

_MAX_INSTRUMENTOS = 10  # tope de documentos que se leen por consulta
_MAX_LINEAS_PERSONA = 15
_MAX_LINEAS_FILTRO = 40  # «dame todas las respuestas de uno de…»: la persona completa
_MAX_IDS_LISTA = 30

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
    if ids:  # en el orden en que se eligieron, para que «el primer instrumento» sea el primero de la selección
        orden = {str(i): n for n, i in enumerate(ids)}
        instrumentos.sort(key=lambda i: orden.get(i.id_crudo, len(orden)))
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
# Postura de los entrevistados («¿cuántos dicen que sí…?», «¿qué motivos dan?»): solo si el alcance tiene entrevistas.
_POSTURA_ENT = re.compile(
    r"\b(cuant[oa]s|quienes|que motivos|por que|cuales son los motivos|que razones)\b.*"
    r"\b(entrevistad\w*|participantes?|dicen|dijeron|creen|consideran|opinan|piensan|respondieron|a favor|en contra)\b"
    r"|\b(motivos|razones)\b"
)
_PORCENTAJE = re.compile(r"\b(porcentaje|por ciento|proporcion|cuantos|cuantas|que parte)\b|%")
_ALGUIEN = re.compile(r"\b(un|una|algun|alguna|algunos|que|cual|cuales|hay)\s+(respondente|persona|estudiante|encuestad[oa]|alumn[oa])s?\b")
# Indagata no califica las pruebas (no hay clave): preguntas por aciertos, respuestas correctas o puntajes
# se contestan con esa aclaración y con lo que sí se sabe, la opción más elegida de cada reactivo.
_CALIFICACION = re.compile(
    r"\b(aciertos?|acert\w*|respuestas? correctas?|respuestas? incorrectas?|calificacion\w*|calificad[oa]s?|puntajes?"
    r"|reactivo\s+mas\s+(?:dificil|facil|fallado)|mas\s+dificil|mas\s+facil|menos\s+acertad\w*|distractor\w*"
    # «¿Cuántos aprobaron la prueba?»; con «la prueba» para no tocar filtros de encuestas («los que reprobaron…»).
    r"|(?:aprob|reprob|pas)\w*\s+(?:la|esta)\s+prueba)\b"
)
# Calidad de los datos y sugerencias de análisis (medidas de la limpieza).
_CALIDAD = re.compile(
    r"\b(alfa|cronbach|confiabilidad|confiables?|fiabilidad|fiables?|consistencia interna|calidad de (?:los )?datos"
    r"|que tan (?:buenos|limpios|completos) son (?:los|estos) datos"
    r"|que analisis|analisis (?:me )?(?:sugieres|recomiendas|puedo|conviene)|sugerencias? de analisis"
    r"|como (?:lo |la )?analizo|que prueba estadistica|linea recta"
    # Lo que la limpieza hizo con ESTE instrumento («¿qué se corrigió?»); «¿cómo limpio…?» es ayuda de la plataforma
    # (Fase 6: gemma la mandó a la ayuda, consulta 1495, y qwen a la búsqueda, 1532).
    r"|que (?:se )?(?:corrigio|corrigieron|arreglo|arreglaron|limpio|limpiaron)"
    r"|que (?:se )?(?:modifico|modificaron|cambio|cambiaron) en (?:la limpieza|los datos)"
    r"|(?:que|cuales) (?:correcciones|cambios|ajustes) (?:se )?(?:hicieron|hizo|tuvo|hubo|aplicaron)"
    r"|que (?:se )?hizo (?:en )?la limpieza|que hizo la limpieza|como se limpi(?:o|aron)|resultado de la limpieza)\b"
)
# Estructura del instrumento («¿tiene secciones?», «¿cuántas preguntas tiene?», «¿en qué sección está p4?»).
_ESTRUCTURA = re.compile(
    r"\b(secciones|seccion|bloques|apartados|dimensiones|subescalas|estructura|como esta organizad[oa]s?"
    r"|como estan organizad[oa]s|en que partes|que partes)\b"
    r"|\bcuant[oa]s\s+(preguntas|reactivos|items)\s+(tiene|tienen|hay|son|contiene|contienen|incluye)\b"
)
# Cuántas personas participaron en el instrumento («¿cuántas personas fueron entrevistadas?»): es estructura,
# no un filtro. Se exige el verbo de participación para no quitarle al filtro «¿cuántos estudiantes trabajan…?»
# (24 oct, banco: la pregunta se rechazaba como fuera del dominio con similitud 0.29).
_PERSONAS_CUANTAS = re.compile(
    r"\bcuant[oa]s\s+(?:personas|participantes|entrevistad\w*|respondentes|alumn\w*|estudiantes|encuestad\w*)\s+"
    r"(?:fueron\s+(?:entrevistad|encuestad|evaluad)\w*|se\s+(?:entrevist|encuest|evalu)\w*|participaron|hay\s+en\b"
    r"|tiene\s+(?:la|el)\b|(?:respondieron|contestaron)\s+(?:la|el)\s+(?:encuesta|entrevista|prueba|instrumento))"
    r"|\ba\s+cuant[oa]s\s+(?:personas|participantes|estudiantes|alumn\w*)\s+se\s+(?:entrevist|encuest|evalu)\w*"
)
# De qué trata un instrumento o qué relación hay entre varios («¿de qué habla el primer instrumento?»,
# «dime la relación entre uno y otro instrumento»): se responde con la ficha del documento.
# El sustantivo se reconoce por su raíz para tolerar erratas («el primer instrumeto»); «entrevistados» no cuenta.
_INSTRUMENTO_PALABRA = r"(?:instrum\w*|encuest\w*|entrevistas?\b|prueb\w*|cuestionari\w*|document\w*)"
_DETERMINANTE = r"(?:(?:el|la|los|las|del|al|un|unos|unas|este|esta|estos|estas|ese|esa|cada|ambos|ambas|uno|una)\s+)?(?:\w+\s+)?"
_RELACION = re.compile(
    r"\brelacion(?:es)?\b|\bse\s+relacionan?\b|\ben\s+comun\b|\bse\s+(?:parecen|diferencian|distinguen)\b"
    r"|\bdiferencias?\b|\bsemejanzas?\b|\bsimilitud(?:es)?\b|\bcompar\w*\b"
)
# Solo preguntas SOBRE el instrumento: el verbo va pegado al sustantivo. «Compara la motivación entre los dos
# instrumentos» o «¿qué opinan los entrevistados…?» siguen por la ruta semántica, porque preguntan por un tema.
_DESCRIPCION = re.compile(
    r"\bde\s+que\s+(?:trata|tratan|habla|hablan|va|van|se\s+trata|se\s+tratan)\s+" + _DETERMINANTE + _INSTRUMENTO_PALABRA +
    r"|\bque\s+(?:evalua|evaluan|mide|miden|aborda|abordan|investiga|investigan|estudia|estudian)\s+" + _DETERMINANTE + _INSTRUMENTO_PALABRA +
    r"|\b(?:objetivo|proposito|tema|temas)\s+(?:del?|de\s+la|de\s+los|de\s+las)\s+(?:\w+\s+)?" + _INSTRUMENTO_PALABRA +
    r"|\b(?:describ\w*|resum\w*|explica\w*)\s+(?:me\s+)?" + _DETERMINANTE + _INSTRUMENTO_PALABRA +
    r"|\b(?:que\s+(?:me\s+)?(?:puedes|podrias|sabes)\s+(?:decir|contar)?|que\s+sabes|dime\s+algo|cuentame(?:\s+algo)?"
    r"|hablame|informacion)\s+(?:sobre|de|del|acerca\s+de)\s+" + _DETERMINANTE + _INSTRUMENTO_PALABRA +
    r"|\b(?:relacion(?:es)?|similitud(?:es)?|semejanzas?|diferencias?|en\s+comun|compar\w*)"
    r"(?:\s+(?:hay|existe|existen|tienen|tiene))?(?:\s+(?:entre|de))?\s+(?:(?:el|la|los|las|un|una|unos|unas|estos|estas|mis)\s+)?"
    r"(?:dos\s+|tres\s+)?(?:" + _INSTRUMENTO_PALABRA + r"|uno\s+y\s+otro|una\s+y\s+otra|ambos|ambas)"
    r"|\ben\s+que\s+se\s+(?:parecen|diferencian|distinguen|relacionan)\b|\bcomo\s+se\s+relacionan\b"
)
# Patrones o hallazgos de los datos («¿qué patrón de información consideras más interesante…?»,
# «¿qué muestran los resultados?»): se calculan sobre los datos completos y el modelo solo redacta.
_PATRONES = re.compile(
    r"\bpatron(?:es)?\b|\btendencias?\b|\bhallazgos?\b|\binsights?\b|\bconclusion(?:es)?\b|\bse\s+puede\s+concluir\b"
    r"|\blo\s+mas\s+(?:interesante|relevante|destacado|llamativo|importante|notable|significativo)\b"
    r"|\b(?:mas|muy)\s+(?:interesante|relevante|destacad[oa]|llamativ[oa]|notable)s?\b"
    r"|\bque\s+(?:dicen|muestran|revelan|indican|reflejan)\s+(?:los|las)\s+(?:datos|resultados|respuestas)\b"
    r"|\b(?:principales|resumen\s+de\s+los|resume\s+los)\s+(?:resultados|datos|hallazgos)\b"
    # «¿Qué temas se repiten más…?» (24 oct, banco: no se reconocía y el modelo improvisó los temas).
    r"|\bse\s+repiten\b|\b(?:temas|ideas|palabras)\s+(?:mas|que\s+mas)\s+(?:frecuentes|comunes|repetid\w*|mencionad\w*|usad\w*)\b"
    r"|\bque\s+(?:temas|ideas)\s+(?:aparecen|surgen|predominan|destacan)\b"
    r"|\b(?:palabras|temas|ideas)\s+(?:que\s+)?(?:usan|mencionan|repiten|dicen|comentan)\s+mas\b"
)
# La pregunta habla de los instrumentos elegidos («estos instrumentos», «los datos», «la encuesta»): es del
# dominio aunque su similitud caiga en la zona gris (el clasificador de 3B llegó a rechazarla).
_REFIERE_ALCANCE = re.compile(
    r"\b(?:estos|estas|los|las|mis|ambos|ambas|el|la|del|al|un|una|unos|unas|otro|otra|este|esta|cada)\s+(?:dos\s+|tres\s+)?"
    r"(?:instrum\w*|encuest\w*|entrevistas?\b|prueb\w*|cuestionari\w*|datos|resultados|respuestas|respondentes|participantes)"
    r"|\binstrum\w*"
)


def refiere_al_alcance(pregunta: str) -> bool:
    return bool(_REFIERE_ALCANCE.search(normalizar(pregunta)))


# «el primer instrumento», «la segunda encuesta», «el último»: posición en la selección del chat.
_ORDINALES = {"primer": 0, "primero": 0, "primera": 0, "segundo": 1, "segunda": 1, "tercer": 2, "tercero": 2,
              "tercera": 2, "cuarto": 3, "cuarta": 3, "quinto": 4, "quinta": 4, "ultimo": -1, "ultima": -1}
_ORDINAL = re.compile(r"\b(" + "|".join(_ORDINALES) + r")\s+(instrum\w*|encuest\w*|entrevist\w*|prueb\w*|cuestionari\w*|document\w*)")
_NUMERAL = re.compile(r"\b(instrum\w*|encuest\w*|entrevista|prueb\w*|cuestionari\w*|document\w*)\s+(?:n(?:umero|o\.?|°)\s*)?(\d{1,2})\b")


def _posicion(texto: str) -> tuple[int, str, str] | None:
    """(posición en la selección, sustantivo, cómo lo dijo) de «el segundo instrumento» o «el instrumento 2»."""
    if m := _ORDINAL.search(texto):
        return _ORDINALES[m.group(1)], m.group(2), f"{m.group(1)} {{}}"
    if (m := _NUMERAL.search(texto)) and int(m.group(2)) >= 1:
        return int(m.group(2)) - 1, m.group(1), f"{{}} {m.group(2)}"
    return None
_TIPO_DE_PALABRA = {"encuest": "encuesta", "cuestio": "encuesta", "entrevi": "entrevista", "prueb": "prueba_estandarizada"}
_SUSTANTIVOS = ("instrumento", "encuesta", "entrevista", "prueba", "cuestionario", "documento")
_KPI = re.compile(r"\b(kpi|kpis|indicador|indicadores)\b")
_KPI_PREGUNTAS = re.compile(r"\b(que|cuales)\s+(preguntas|reactivos|items)\b|\bcomo\s+respondieron\b")
# Consultas con filtro: quién cumple una condición sobre sus respuestas.
_FILTRO = re.compile(
    r"\b(?:que|quienes)\s+(?:respondieron|contestaron|dijeron|eligieron|marcaron|seleccionaron|escogieron)\b"
    r"|\bque\s+(?:si|no)\s+\w+|\b(?:los|las|aquellos|aquellas)\s+que\b|\bquienes\b|\bfiltra(?:r)?\b"
    r"|\b(?:estudiantes|alumn[oa]s|respondentes|encuestad[oa]s|personas|participantes|jovenes)\s+que\b"
    r"|\b(?:cuantos|cuantas|porcentaje de)\s+(?:estudiantes|alumn[oa]s|respondentes|encuestad[oa]s|personas|jovenes)\b"
    r"|\b(?:cuantos|cuantas)\s+(?:respondieron|contestaron|dijeron|eligieron|marcaron)\b"
    r"|\b(?:cuantos|cuantas)\s+(?:tienen|tiene|estan|cursan|trabajan|han|cuentan|son\s+de|viven|usan)\b"
    r"|\balgun[oa]s?\s+de\s+(?:los|las|ellos|ellas|esos|esas|estos|estas)\b"
)
_ACCION_UNO = re.compile(r"\b(?:uno|una)\s+de\b|\b(?:un|una|algun|alguna)\s+(?:estudiante|alumn[oa]|respondente|persona|encuestad[oa]|joven)\b|\bejemplo\b")
_ACCION_LISTA = re.compile(r"\b(?:quienes|cuales|lista|enlista|listado|todos los|todas las)\b")
_POLARIDAD = re.compile(
    r"\b(?:que|dijeron|respondieron|contestaron|marcaron|eligieron)\s+(si|no)\b"
    r"|\b(si|no)\s+(?:han|ha|hayan|haya|\w+(?:aron|ieron|ado|ido|an|en))\b"
)
_COMPARACION = re.compile(
    r"\b(mas|menos|mayor|menor)\s+(?:de|que|a)\s+(\d+(?:[.,]\d+)?)"
    r"|\b(?:al menos|por lo menos|minimo)\s+(\d+(?:[.,]\d+)?)|\b(?:como maximo|maximo|a lo mucho)\s+(\d+(?:[.,]\d+)?)"
)
_TIPOS_NUMERICOS = {"numerica", "escala_lineal", "calificacion"}
_STOP = set("que cual cuales como donde cuando para por con sin sobre los las del una uno unos unas este esta estos estas "
            "pregunta preguntas respondio respondieron respondente dijo dice instrumento kpi kpis mide miden relacionado "
            "relacionada porque esta estan tiene tienen hay cuanto cuantos".split())
# Palabras de la petición que no dicen nada de la condición («dame todas las respuestas de uno de los estudiantes…»).
_STOP_FILTRO = _STOP | set(
    "dame todas todos todo resumen resume tantos tanto ese esa esos esas estudiante estudiantes alumno alumnos alumna "
    "alumnas respondentes persona personas encuestados encuestadas encuesta encuestas prueba entrevista ellos ellas "
    "alguno alguna algunos algunas quienes uno una han sido fueron favor quiero saber respuestas respuesta contestaron "
    "dijeron eligieron marcaron cuantas porcentaje muestrame muestra".split()
)
_VACIAS_VALOR = {"de", "la", "el", "en", "y", "a", "o", "lo", "los", "las", "del", "al", "un", "una", "h"}
# Verbos de la pregunta que no nombran ningún tema («¿cuántos TIENEN carga mínima…?» no habla del doctorado
# aunque esa pregunta diga «¿cuántos tienen doctorado?»).
_VERBOS_CONSULTA = set(
    "tienen tiene tener tenido cursan cursando cursa estan estando cuentan cuenta suelen suele pueden puede "
    "hayan tengan esten cursen".split()
)
_GENERICAS_TITULO = {"encue", "prueb", "entre", "instr", "cuest", "estud"}


@dataclass
class Intencion:
    tipo: str  # respuesta | persona | respondente_con_nivel | pct_nivel | kpi | kpi_preguntas | sin_calificar | dijo | filtro | calidad | postura | estructura | descripcion | patrones
    persona: tuple[str, int] | None = None
    preguntas: list[int] = field(default_factory=list)
    nivel: str | None = None
    tema: str = ""
    texto: str = ""  # pregunta normalizada (para grupos y KPIs por nombre)
    accion: str = ""  # filtro: uno | contar | lista | resumen


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


def pide_filtro(pregunta: str) -> bool:
    """¿La pregunta pide los respondentes que cumplen algo («los que sí reprobaron…»)?"""
    return bool(_FILTRO.search(normalizar(pregunta)))


def _accion(texto: str) -> str:
    if _ACCION_UNO.search(texto):
        return "uno"
    if _PORCENTAJE.search(texto):
        return "contar"
    return "lista" if _ACCION_LISTA.search(texto) else "resumen"


def detectar(pregunta: str, *, sin_filtro: bool = False) -> Intencion | None:
    """Intención estructurada de la pregunta, o None si es una pregunta abierta."""
    texto = normalizar(pregunta)
    persona, preguntas, nivel = _persona(texto), _preguntas(texto), _nivel(texto)
    tema = (m.group(1).strip() if (m := _TEMA.search(texto)) else "")
    base = {"persona": persona, "preguntas": preguntas, "nivel": nivel, "tema": tema, "texto": texto}
    if _CALIDAD.search(texto) and not persona and not es_definicion(pregunta):
        return Intencion("calidad", **base)
    if _CALIFICACION.search(texto) and not persona:
        return Intencion("sin_calificar", **base)
    if _KPI.search(texto):
        return Intencion("kpi_preguntas" if _KPI_PREGUNTAS.search(texto) else "kpi", **base)
    if _PATRONES.search(texto) and not persona and not preguntas:
        return Intencion("patrones", **base)
    if (_ESTRUCTURA.search(texto) or _PERSONAS_CUANTAS.search(texto)) and not persona and not nivel:
        return Intencion("estructura", **base)
    if _DESCRIPCION.search(texto) and not persona and not preguntas and not nivel:
        return Intencion("descripcion", **base)
    if persona and persona[0] == "E":
        return Intencion("dijo", **base)
    if not sin_filtro and not persona and _FILTRO.search(texto):
        return Intencion("filtro", accion=_accion(texto), **base)
    # Sin número de pregunta ni «sobre…», la pregunta se busca por sus palabras («…de acuerdo con que se siente
    # parte de la comunidad escolar»): antes iba a la ruta semántica y el modelo inventó «100 %» (24 oct, banco).
    if nivel and _PORCENTAJE.search(texto) and not persona:
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


# ── Filtros: condiciones sobre las respuestas ──────────────────────────────────


def _raices(texto: str) -> set[str]:
    """Raíces de 5 letras (y números) de las palabras con contenido: «reprobado» y «reprobaron» → «repro»."""
    return {t if t[0].isdigit() else t[:5] for t in re.findall(r"\d+(?:[.,]\d+)?|[a-z]+", normalizar(texto))
            if (t[0].isdigit() or len(t) >= 4) and t not in _STOP_FILTRO}


def _fichas_valor(texto: str) -> set[str]:
    """Palabras de una opción de respuesta («Trabajo más de 30h» → trabajo, mas, 30), con raíz de 5 letras."""
    return {t if t[0].isdigit() else t[:5] for t in re.findall(r"\d+(?:[.,]\d+)?|[a-z]+", normalizar(texto))
            if t not in _VACIAS_VALOR}


@dataclass
class _DatosPregunta:
    valores: list[str]  # opciones que alguien eligió (significados), en orden de aparición
    numerica: bool
    con_nivel: bool

    @property
    def binaria(self) -> bool:
        primeras = {normalizar(v).split(" ")[0].strip(",.") for v in self.valores}
        return bool(self.valores) and primeras <= {"si", "no"}


def _indice(doc: dict[str, Any]) -> dict[str, _DatosPregunta]:
    valores: dict[str, dict[str, None]] = {}
    numeros: dict[str, list[bool]] = {}
    nivel: dict[str, bool] = {}
    for r in doc.get("respondentes") or []:
        for x in r["respuestas"]:
            if x.get("estado") != "respondida":
                continue
            pid = x["pregunta_id"]
            valores.setdefault(pid, {})[str(x.get("significado") or x.get("valor"))] = None
            numeros.setdefault(pid, []).append(consultas._numero(x.get("valor")) is not None)
            nivel[pid] = nivel.get(pid, False) or bool(x.get("nivel"))
    tipos = {p["id"]: p.get("tipo") for p in _items(doc)}
    return {pid: _DatosPregunta(list(v)[:40], tipos.get(pid) in _TIPOS_NUMERICOS or (bool(numeros[pid]) and all(numeros[pid])),
                                nivel.get(pid, False))
            for pid, v in valores.items()}


def _comparacion(texto: str) -> list[Any] | None:
    if not (m := _COMPARACION.search(texto)):
        return None
    if m.group(1):
        return [">" if m.group(1) in ("mas", "mayor") else "<", float(m.group(2).replace(",", "."))]
    if m.group(3):
        return [">=", float(m.group(3).replace(",", "."))]
    return ["<=", float(m.group(4).replace(",", "."))]


def _primera(valor: str) -> str:
    return normalizar(valor).split(" ")[0].strip(",.")


def _condicion_en(doc: dict[str, Any], indice: dict[str, _DatosPregunta], texto: str, quitar: set[str],
                  excluir: set[str], estricta: bool) -> tuple[dict[str, Any], str, int] | None:
    """La condición mejor expresada en la consulta («que sí han reprobado por falta de tiempo»), o None.

    Elige la pregunta con más palabras en común (o la nombrada «p13») que además tenga
    una opción mencionada: completa («Sí, una vez»), por sus palabras («más de 30h»),
    por polaridad («que sí…» → todas las que empiezan con «Sí»), un nivel («de acuerdo»)
    o una comparación numérica («más de 20»). `estricta` (segunda condición en adelante)
    exige más evidencia para no inventar condiciones.
    """
    raices, fichas = _raices(texto) - quitar, _fichas_valor(texto) - quitar
    numeros = _preguntas(texto)
    nivel, comparacion = _nivel(texto), _comparacion(texto)
    m = _POLARIDAD.search(texto)
    polaridad = (m.group(1) or m.group(2)) if m else None
    mejor: tuple[dict[str, Any], str, int] | None = None
    for p in _items(doc):
        datos = indice.get(p["id"])
        if datos is None or p["id"] in excluir:
            continue
        explicita = any(re.fullmatch(rf"[a-z]+0*{n}", _corto(p["id"])) for n in numeros)
        solape = len(raices & _raices(p.get("texto", "")))
        completos: list[str] = []
        por_fichas: list[str] = []
        # En las preguntas numéricas «más de 30» es una comparación, no la opción «30 horas».
        if not (datos.numerica and comparacion):
            completos = [v for v in datos.valores if re.search(rf"(?<![a-z0-9]){re.escape(normalizar(v))}(?![a-z0-9])", texto)]
            completos = [v for v in completos if not any(v != w and normalizar(v) in normalizar(w) for w in completos)]
            por_fichas = [] if completos else [v for v in datos.valores if (f := _fichas_valor(v)) and f <= fichas and len(f) >= 2]
        condicion, fuerza, nota = None, 0, ""
        if nivel and datos.con_nivel and not any("totalmente" in normalizar(v) for v in completos):
            condicion, fuerza = {"nivel": nivel}, 2
        elif completos or por_fichas:
            elegidos = completos or por_fichas
            condicion, fuerza = {"valores": elegidos}, 3 + max(len(_fichas_valor(v)) for v in elegidos)
        elif polaridad and (con_polaridad := [v for v in datos.valores if _primera(v) == polaridad]):
            condicion, fuerza = {"valores": con_polaridad}, 1
        elif comparacion and datos.numerica:
            condicion, fuerza = {"comparacion": comparacion}, 1
        elif solape >= 2 and datos.binaria:
            condicion, nota = {"valores": [v for v in datos.valores if _primera(v) == "si"]}, "se interpretó como «sí»"
        if condicion is None:
            continue
        fuerte = fuerza >= 5  # una opción nombrada con al menos dos palabras («Trabajo más de 30h»)
        if not (explicita or solape >= (2 if estricta else 1) or fuerte):
            continue
        puntos = solape * 2 + (6 if explicita else 0) + fuerza
        if mejor is None or puntos > mejor[2]:
            mejor = ({"pregunta_id": p["id"], **condicion}, nota, puntos)
    return mejor


def _condiciones(doc: dict[str, Any], texto: str) -> list[tuple[dict[str, Any], str]]:
    """Condiciones de la consulta (hasta 3: «… que reprobaron una vez y tienen dificultades para…»).

    Se busca la mejor; sus palabras se descuentan y se busca otra con más exigencia.
    """
    indice = _indice(doc)
    titulo = _raices((doc.get("instrumento") or {}).get("titulo", "")) - _GENERICAS_TITULO
    # Si la consulta nombra el instrumento, sus palabras no cuentan para elegir la pregunta.
    quitar = set(titulo) if len(_raices(texto) & titulo) >= 2 else set()
    salida: list[tuple[dict[str, Any], str]] = []
    usadas: set[str] = set()
    for _ in range(3):
        hallada = _condicion_en(doc, indice, texto, quitar, usadas, estricta=bool(salida))
        if hallada is None:
            break
        condicion = hallada[0]
        salida.append(hallada[:2])
        usadas.add(condicion["pregunta_id"])
        p = next(x for x in _items(doc) if x["id"] == condicion["pregunta_id"])
        quitar |= _raices(p.get("texto", ""))
    # Una palabra que nombra UNA sola pregunta con opciones «Sí…» / «No…» y que no tuvo condición:
    # «tienen alguna certificación» → las opciones «Sí…» de «¿Has presentado algún examen de certificación…?»;
    # «sin certificación» o «no tienen…» → las «No…» (28 oct).
    for palabra in _sin_condicion(doc, texto, salida)[: 3 - len(salida)]:
        candidatas = [p for p in _items(doc) if p["id"] not in usadas and palabra[:5] in _raices(p.get("texto", ""))]
        if len(candidatas) != 1 or (datos := indice.get(candidatas[0]["id"])) is None:
            continue
        negativa = bool(re.search(rf"\b(?:sin|ningun\w*|no\s+\w+(?:\s+\w+)?)\s+(?:\w+\s+)?{palabra}", texto))
        polo = "no" if negativa else "si"
        valores = [v for v in datos.valores if _primera(v) == polo]
        if not valores or len(valores) == len(datos.valores):
            continue
        p = candidatas[0]
        salida.append(({"pregunta_id": p["id"], "valores": valores}, f"«{palabra}» se interpretó como «{'no' if negativa else 'sí'}»"))
        usadas.add(p["id"])
    return salida


def _sin_condicion(doc: dict[str, Any], texto: str, condiciones: list[tuple[dict[str, Any], str]]) -> list[str]:
    """Palabras de la consulta que nombran OTRA pregunta del instrumento y para las que no se armó condición.

    Caso (28 oct): «¿cuántos tienen carga mínima y alguna certificación?» → solo «carga mínima» tenía
    condición; «certificación» nombra la pregunta «¿Has presentado algún examen de certificación…?».
    Solo cuentan raíces de palabras de 6 letras o más, para no confundir «tienen» con cualquier pregunta.
    """
    usadas = {c["pregunta_id"] for c, _ in condiciones}
    cubiertas: set[str] = set()
    for c, _ in condiciones:
        p = next((x for x in _items(doc) if x["id"] == c["pregunta_id"]), {})
        cubiertas |= _raices(p.get("texto", "")) | {r for v in c.get("valores") or [] for r in _raices(v)}
    largas = {t[:5]: t for t in re.findall(r"[a-z]+", normalizar(texto))
              if len(t) >= 6 and t not in _STOP_FILTRO and t not in _VERBOS_CONSULTA}
    faltan = []
    for raiz, palabra in largas.items():
        if raiz in cubiertas:
            continue
        if any(raiz in _raices(p.get("texto", "")) for p in _items(doc) if p["id"] not in usadas):
            faltan.append(palabra)
    return faltan


def filtro_incompleto(resultado: "Resultado") -> list[str]:
    """Palabras que la consulta de filtro nombró y que quedaron sin condición en algún instrumento."""
    if resultado is None or resultado.consulta != "filtro":
        return []
    faltan: list[str] = []
    for ins, _, _ in resultado.partes:
        for palabra in _sin_condicion(ins.doc, resultado.consulta_texto, _condiciones(ins.doc, resultado.consulta_texto)):
            if palabra not in faltan:
                faltan.append(palabra)
    return faltan


def _describir(doc: dict[str, Any], condicion: dict[str, Any]) -> str:
    p = next((x for x in _items(doc) if x["id"] == condicion["pregunta_id"]), {"texto": ""})
    base = f"{_corto(condicion['pregunta_id'])} «{p['texto']}»"
    if condicion.get("nivel"):
        return f"{base}: {_FRASE_NIVEL.get(condicion['nivel'], condicion['nivel'])}"
    if condicion.get("valores"):
        return f"{base} = " + " o ".join(f"«{v}»" for v in condicion["valores"])
    op, n = condicion["comparacion"]
    return f"{base} {op} {n:g}"


def _lineas_calidad(ins: Instrumento, sesion: Session) -> tuple[list[str], bool]:
    """Medidas de la última limpieza confirmada del instrumento y las sugerencias de análisis."""
    ejecucion = (
        sesion.query(LimpiezaEjecucion)
        .filter(LimpiezaEjecucion.id_crudo == int(ins.id_crudo), LimpiezaEjecucion.estado == "confirmada")
        .order_by(LimpiezaEjecucion.version.desc())
        .first()
    )
    estadistica = (((ejecucion.reporte or {}).get("vista_final") or {}).get("estadistica")) if ejecucion else None
    correcciones = _lineas_correcciones(ejecucion.reporte or {}) if ejecucion else []
    if not estadistica:
        if correcciones:
            return correcciones, True
        return ["Este instrumento no tiene medidas de la limpieza (se cargó antes de la limpieza asistida)."], False
    lineas: list[str] = []
    fiabilidad = estadistica.get("fiabilidad")
    if isinstance(fiabilidad, list):
        for b in fiabilidad:
            if b.get("alfa") is not None:
                lineas.append(f"Fiabilidad del bloque «{b.get('bloque')}»: α de Cronbach = {b['alfa']} "
                              f"({b.get('interpretacion') or 'sin interpretación'}), {b.get('n_items')} ítems.")
    if (resp := estadistica.get("respuestas")) and resp.get("pct_sin_respuesta") is not None:
        lineas.append(f"Respuestas de la prueba: {resp.get('n_alumnos')} alumnos, {resp.get('n_reactivos')} reactivos; "
                      f"{round(100 * resp['pct_sin_respuesta'], 1)} % de las respuestas quedó nula o sin responder. "
                      "La prueba no se califica (Indagata no usa clave de respuestas).")
    if r := estadistica.get("resumen_reactivos"):
        lineas.append(f"Reactivos: {r.get('mucha_no_respuesta', 0)} con muchas respuestas nulas o vacías, "
                      f"{r.get('con_opciones_sin_elegir', 0)} con opciones que nadie eligió y {r.get('casi_unanimes', 0)} casi unánimes.")
    if e := estadistica.get("encuestados"):
        n = max((c.get("n") or 0 for c in estadistica.get("columnas") or []), default=0)
        lineas.append(f"Encuestados que respondieron en línea recta: {e.get('linea_recta', 0)}" + (f" de {n}." if n else "."))
    lineas += correcciones
    lineas += [f"Sugerencia ({s['nivel']}): {s['texto']} {s['porque']}" for s in sugerencias.sugerir(ins.tipo, estadistica)]
    return lineas, True


# Pasos de la limpieza que no corrigen datos (validar el formato, convertir a UTF-8): no se cuentan como correcciones.
_SIN_CORRECCION = {"validacion_archivo", "codificacion_utf8", "respuestas_validadas", "identificadores_seguros"}


def _lineas_correcciones(reporte: dict[str, Any]) -> list[str]:
    """Qué corrigió la limpieza confirmada y qué decidió la persona investigadora, del reporte de limpieza.

    Usa el texto de cada transformación que ya escribe cleaning-service; de las decisiones, solo el tipo de hallazgo y
    la opción elegida (los títulos de los hallazgos traen matrículas del archivo crudo, como «R0067»)."""
    lineas = []
    for t in reporte.get("transformaciones") or []:
        if t.get("regla") in _SIN_CORRECCION or not t.get("afectados") or not t.get("detalle"):
            continue
        lineas.append(f"Corrección de la limpieza ({t['afectados']}): {str(t['detalle']).rstrip('.')}.")
    tipos = {h.get("id"): str(h.get("tipo") or "").replace("_", " ") for h in reporte.get("hallazgos") or []}
    por_tipo: dict[str, list[str]] = {}
    for hid, d in (reporte.get("decisiones") or {}).items():
        valor = str((d or {}).get("valor") or "").replace("_", " ")
        if valor:
            por_tipo.setdefault(tipos.get(hid) or str(hid).split(":")[0].replace("-", " "), []).append(valor)
    if por_tipo:
        lineas.append("Decisiones de la limpieza asistida: "
                      + "; ".join(f"{t} → {', '.join(v)}" for t, v in por_tipo.items()) + ".")
    antes = ((reporte.get("metricas") or {}).get("antes") or {}).get("pct_validas")
    despues = ((reporte.get("metricas") or {}).get("despues") or {}).get("pct_validas")
    if antes is not None and despues is not None:
        lineas.append(f"Respuestas válidas: {round(100 * antes, 1)} % antes de la limpieza y {round(100 * despues, 1)} % después.")
    return lineas


_SECCION_GENERAL = "General"  # la sección única de un instrumento sin secciones (knowledge-service)


def _cuantas(n: int, unidad: str) -> str:
    """«1 pregunta», «4 preguntas», «1 reactivo»."""
    return f"{n} {unidad[:-1] if n == 1 else unidad}"


def _lineas_estructura(intencion: Intencion, ins: Instrumento) -> list[str]:
    """Secciones del instrumento con sus preguntas, o que no tiene secciones."""
    doc, items = ins.doc, _items(ins.doc)
    unidad = "reactivos" if ins.tipo == "prueba_estandarizada" else "preguntas"
    if ins.tipo == "entrevista":
        lineas = [f"Es una entrevista: su guion tiene {len(items)} preguntas y no está dividido en secciones."]
        if n := len(doc.get("entrevistas") or []):
            lineas.append(f"Se entrevistó a {n} participantes.")
        return lineas
    if _PERSONAS_CUANTAS.search(intencion.texto):  # «¿cuántos respondieron la encuesta?»: el número de personas
        personas = doc.get("respondentes") or doc.get("alumnos") or []
        quien = "alumnos presentaron la prueba" if ins.tipo == "prueba_estandarizada" else "personas respondieron la encuesta"
        return [f"{len(personas)} {quien}; tiene {_cuantas(len(items), unidad)}."]
    nombres = {s["id"]: s.get("nombre") or "" for s in doc.get("secciones") or []}
    por_seccion: dict[str, list[dict[str, Any]]] = {}
    for p in items:
        por_seccion.setdefault(p.get("seccion_id") or "", []).append(p)
    reales = [sid for sid in por_seccion if nombres.get(sid) and nombres[sid] != _SECCION_GENERAL]
    if intencion.preguntas:  # «¿en qué sección está la pregunta 4?»
        lineas = []
        for numero in intencion.preguntas:
            p = _por_numero(doc, numero)
            if p is None:
                lineas.append(f"El instrumento no tiene la pregunta {numero}.")
            elif reales and nombres.get(p.get("seccion_id") or ""):
                lineas.append(f"{_corto(p['id'])} «{p['texto']}» está en la sección «{nombres[p['seccion_id']]}».")
            else:
                lineas.append(f"{_corto(p['id'])} «{p['texto']}»: el instrumento no tiene secciones.")
        return lineas
    if not reales:
        return [f"No tiene secciones: sus {len(items)} {unidad} forman un solo bloque."]
    lineas = [f"Tiene {len(reales)} {'sección' if len(reales) == 1 else 'secciones'} y {len(items)} {unidad}:"]
    for i, sid in enumerate(reales, start=1):
        ids = ", ".join(_corto(p["id"]) for p in por_seccion[sid])
        lineas.append(f"Sección {i} «{nombres[sid]}»: {_cuantas(len(por_seccion[sid]), unidad)} ({ids}).")
    if sueltas := [p for sid, ps in por_seccion.items() if sid not in reales for p in ps]:
        lineas.append(f"Sin sección: {_cuantas(len(sueltas), unidad)} ({', '.join(_corto(p['id']) for p in sueltas)}).")
    return lineas


_SIN_DATO = {"", "no especificado", "no especificada", "ninguno", "ninguna"}
_MAX_EJEMPLOS = 4


def _dato(valor: Any) -> str:
    texto = str(valor or "").strip()
    return "" if normalizar(texto) in _SIN_DATO else texto


def _palabras_clave(doc: dict[str, Any]) -> list[str]:
    ins = doc.get("instrumento") or {}
    vistas, salida = set(), []
    for p in (ins.get("palabras_clave") or []) + (ins.get("temas") or []):
        clave = normalizar(str(p))
        if clave and clave not in vistas and not str(p).isupper():  # los temas en MAYÚSCULAS son nombres de sección
            vistas.add(clave)
            salida.append(str(p))
    return salida[:8]


def _lineas_descripcion(ins: Instrumento) -> list[str]:
    """De qué trata el instrumento, solo con datos de su documento (objetivo, población, estructura, KPIs)."""
    doc, meta = ins.doc, ins.doc.get("instrumento") or {}
    items = _items(doc)
    lineas = [f"Tipo: {ins.tipo_ui}."]
    if objetivo := _dato(meta.get("objetivo")):
        lineas.append(f"Objetivo: {objetivo.rstrip('.')}.")
    if poblacion := _dato(meta.get("poblacion")):
        lineas.append(f"Población: {poblacion.rstrip('.')}.")
    if nivel := _dato(meta.get("nivel_educativo")):
        lineas.append(f"Nivel educativo: {nivel}.")
    if ins.tipo == "entrevista":
        lineas.append(f"Guion de {_cuantas(len(items), 'preguntas')}; se entrevistó a {len(doc.get('entrevistas') or [])} participantes.")
    else:
        unidad = "reactivos" if ins.tipo == "prueba_estandarizada" else "preguntas"
        personas = doc.get("respondentes") or doc.get("alumnos") or []
        secciones = [s.get("nombre") for s in doc.get("secciones") or [] if s.get("nombre") and s.get("nombre") != _SECCION_GENERAL]
        estructura = (f"en {len(secciones)} {'sección' if len(secciones) == 1 else 'secciones'} ({'; '.join(secciones)})"
                      if secciones else "sin secciones")
        lineas.append(f"{_cuantas(len(items), unidad).capitalize()} {estructura}; {len(personas)} {'alumnos' if ins.tipo == 'prueba_estandarizada' else 'respondentes'}.")
    if items:
        ejemplos = "; ".join(f"«{p['texto']}»" for p in items[:_MAX_EJEMPLOS])
        lineas.append(f"Algunas de sus preguntas: {ejemplos}.")
    if claves := _palabras_clave(doc):
        lineas.append(f"Palabras clave: {', '.join(claves)}.")
    kpis = [k.get("nombre") for k in doc.get("kpis_asociados") or [] if k.get("nombre")]
    lineas.append(f"KPIs asociados: {'; '.join(kpis)}." if kpis else "No tiene KPIs asociados.")
    return lineas


def _lineas_relacion(instrumentos: list[Instrumento]) -> list[str]:
    """Qué comparten los instrumentos del alcance (tipo, nivel, KPIs y palabras clave), calculado."""
    if len(instrumentos) < 2:
        return ["En la consulta hay un solo instrumento; para compararlo, agrega otro a la selección del chat."]
    tipos = [i.tipo_ui for i in instrumentos]
    lineas = [f"Tipos: {', '.join(tipos)}" + (" (el mismo tipo)." if len(set(tipos)) == 1 else " (tipos distintos).")]
    # El objetivo de cada uno por separado: con solo la ficha, el modelo le atribuyó a los dos el de uno.
    objetivos = [(i.titulo, _dato((i.doc.get("instrumento") or {}).get("objetivo"))) for i in instrumentos]
    if any(o for _, o in objetivos):
        distintos = len({normalizar(o) for _, o in objetivos}) > 1
        lineas.append(f"Objetivo de cada uno ({'son distintos' if distintos else 'es el mismo'}): " + "; ".join(f"«{t}»: {o.rstrip('.') or 'sin objetivo registrado'}"
                                                                          for t, o in objetivos) + ".")
    niveles = {_dato((i.doc.get("instrumento") or {}).get("nivel_educativo")) for i in instrumentos}
    if len(niveles) == 1 and (nivel := niveles.pop()):
        lineas.append(f"Comparten el nivel educativo: {nivel}.")
    kpis = [{k.get("kpi_id"): k.get("nombre") for k in i.doc.get("kpis_asociados") or []} for i in instrumentos]
    comunes = set(kpis[0]).intersection(*kpis[1:])
    lineas.append(f"KPIs en común: {'; '.join(n for k, n in kpis[0].items() if k in comunes)}." if comunes else "No comparten KPIs asociados.")
    claves = [{normalizar(p): p for p in _palabras_clave(i.doc)} for i in instrumentos]
    en_comun = set(claves[0]).intersection(*claves[1:])
    lineas.append(f"Palabras clave en común: {', '.join(p for c, p in claves[0].items() if c in en_comun)}." if en_comun else "No comparten palabras clave.")
    return lineas


_POSITIVOS = ("acuerdo", "alta", "satisfaccion", "si")
_NEGATIVOS = ("desacuerdo", "baja", "insatisfaccion", "no")
_MAX_PATRONES = 4
# Palabras que no dicen nada del contenido de una respuesta de entrevista.
_VACIAS_TEXTO = _STOP | set(
    "pero porque cuando entonces tambien siempre nunca ahora antes despues muchas mucho mucha muchos poco poca "
    "bastante algo nada todo toda todos todas otra otro otros otras cosa cosas veces vez creo pienso siento digo "
    "bueno pues osea ser estar haber hacer tener puedo puede pueden podido sido estado hecho tenido sobre entre "
    "desde hasta hacia durante mismo misma mismos ellos ellas nosotros usted ustedes quien quienes donde algunos "
    "algunas cada cual menos algun alguna aqui alli asi solo sola mejor peor gran grande parte forma manera tipo "
    "menudo realmente verdad embargo tengo tenia tenemos tienes hago hacia hacemos estoy estaba estamos estaban "
    "quiero queria queremos puedes podia podemos fueron habia hemos tuve tuvo hubo seria sobre todavia aunque mientras".split()
)


def _nivel_pct(resumen: dict[str, Any], claves: tuple[str, ...]) -> float | None:
    por_nivel = resumen.get("por_nivel") or {}
    return next((por_nivel[k] for k in claves if k in por_nivel), None)


def _lineas_patrones_encuesta(doc: dict[str, Any]) -> list[str]:
    preguntas = [p for p in _items(doc) if p.get("resumen")]
    escala = [p for p in preguntas if p.get("tipo") in ("likert", "escala_lineal") and _nivel_pct(p["resumen"], _POSITIVOS) is not None]
    lineas = []
    if escala:
        alto = max(escala, key=lambda p: _nivel_pct(p["resumen"], _POSITIVOS))
        bajo = max(escala, key=lambda p: _nivel_pct(p["resumen"], _NEGATIVOS) or 0)
        lineas.append(f"Pregunta con más acuerdo (o nivel alto): {_corto(alto['id'])} «{alto['texto']}», "
                      f"{_nivel_pct(alto['resumen'], _POSITIVOS)} %.")
        if bajo is not alto and _nivel_pct(bajo["resumen"], _NEGATIVOS):
            lineas.append(f"Pregunta con más desacuerdo (o nivel bajo): {_corto(bajo['id'])} «{bajo['texto']}», "
                          f"{_nivel_pct(bajo['resumen'], _NEGATIVOS)} %.")
        divididas = [p for p in escala if p["resumen"].get("interpretacion", "").startswith("Respuestas divididas")]
        if len(divididas) == len(escala) and len(escala) > 2:
            lineas.append(f"Las {len(escala)} preguntas de escala tienen respuestas divididas: ninguna opinión predomina con claridad.")
    nombres = {s["id"]: s.get("nombre") for s in doc.get("secciones") or [] if s.get("nombre") and s.get("nombre") != _SECCION_GENERAL}
    medias: dict[str, list[float]] = {}
    for p in preguntas:
        if p.get("tipo") == "likert" and p["resumen"].get("media") is not None and p.get("seccion_id") in nombres:
            medias.setdefault(p["seccion_id"], []).append(float(p["resumen"]["media"]))
    if len(medias) >= 2:
        promedios = {sid: round(sum(v) / len(v), 2) for sid, v in medias.items()}
        sid_alto, sid_bajo = max(promedios, key=promedios.get), min(promedios, key=promedios.get)
        lineas.append(f"Sección con la media más alta: «{nombres[sid_alto]}» ({promedios[sid_alto]}); "
                      f"la más baja: «{nombres[sid_bajo]}» ({promedios[sid_bajo]}), en escala de 1 a 5.")
    opciones = []
    for p in preguntas:
        dist = p["resumen"].get("distribucion") or []
        if p.get("tipo") in ("categorica", "binaria", "opcion_multiple_varias") and dist:
            top = max(dist, key=lambda d: d.get("pct") or 0)
            opciones.append((top.get("pct") or 0, p, top))
    for pct, p, top in sorted(opciones, key=lambda x: -x[0])[:_MAX_PATRONES - 1]:
        lineas.append(f"Opción más elegida en {_corto(p['id'])} «{p['texto']}»: «{top['significado']}», {pct} %.")
    return lineas


def _lineas_patrones_entrevista(doc: dict[str, Any]) -> list[str]:
    entrevistas = doc.get("entrevistas") or []
    lineas = []
    con_analisis = []
    for p in _items(doc):
        res = consultas.posturas(doc, p["id"])
        if res.get("total"):
            con_analisis.append((p, res))
    for p, res in con_analisis[:_MAX_PATRONES]:
        c = res["conteo"]
        partes = [f"{c[k]} {_FRASE_POSTURA[k]}" for k in ("si", "no", "ambivalente", "sin_determinar", "no_aplica") if c.get(k)]
        lineas.append(f"Postura en {_corto(p['id'])} «{p['texto']}»: de {res['total']}, {', '.join(partes)}.")
    # Temas que se repiten: en cuántas personas aparece cada palabra (una vez por persona).
    personas_por_palabra: dict[str, set[str]] = {}
    escrita: dict[str, str] = {}  # forma normalizada → como aparece en el texto (con acentos)
    for e in entrevistas:
        for i in e.get("intercambios") or []:
            for original in re.findall(r"[a-záéíóúüñ]+", (i.get("respuesta") or "").lower()):
                t = normalizar(original)
                if len(t) >= 5 and t not in _VACIAS_TEXTO:
                    escrita.setdefault(t, original)
                    personas_por_palabra.setdefault(t, set()).add(e.get("participante") or "")
    frecuentes = sorted(personas_por_palabra.items(), key=lambda x: (-len(x[1]), x[0]))[:6]
    if frecuentes and entrevistas:
        lineas.append(f"Palabras que más participantes usan en sus respuestas (de {len(entrevistas)}): "
                      + ", ".join(f"«{escrita[t]}» ({len(ps)})" for t, ps in frecuentes) + ".")
    if not con_analisis:
        lineas.append("Esta entrevista no tiene análisis de posturas; los temas salen del conteo de palabras.")
    return lineas


def _lineas_patrones_prueba(doc: dict[str, Any]) -> list[str]:
    """Patrones de lo que respondieron los alumnos (la prueba no se califica)."""
    reactivos = [r for r in _items(doc) if (r.get("resumen") or {}).get("opcion_mas_elegida")]
    lineas = []
    if reactivos:
        def pct(r: dict[str, Any]) -> float:
            return r["resumen"]["opcion_mas_elegida"]["pct"]

        junto = max(reactivos, key=pct)
        repartido = min(reactivos, key=pct)
        m = junto["resumen"]["opcion_mas_elegida"]
        lineas.append(f"Reactivo donde más alumnos coinciden: {_corto(junto['id'])} «{junto['texto']}», el {m['pct']} % eligió «{m['significado']}».")
        m = repartido["resumen"]["opcion_mas_elegida"]
        lineas.append(f"Reactivo con las respuestas más repartidas: {_corto(repartido['id'])} «{repartido['texto']}», "
                      f"la opción más elegida («{m['significado']}») solo reúne el {m['pct']} %.")
    sin = [r for r in _items(doc) if (r.get("resumen") or {}).get("n_alumnos")]
    if sin:
        def vacias(r: dict[str, Any]) -> int:
            return r["resumen"].get("n_nulas", 0) + r["resumen"].get("n_sin_respuesta", 0)

        peor = max(sin, key=vacias)
        if vacias(peor):
            lineas.append(f"Reactivo con más respuestas nulas o vacías: {_corto(peor['id'])} «{peor['texto']}», "
                          f"{vacias(peor)} de {peor['resumen']['n_alumnos']} alumnos.")
    return lineas


def _lineas_patrones(ins: Instrumento) -> tuple[list[str], bool]:
    """Patrones calculados sobre los datos completos del instrumento (no sobre unos fragmentos)."""
    if ins.tipo == "entrevista":
        lineas = _lineas_patrones_entrevista(ins.doc)
    elif ins.tipo == "prueba_estandarizada":
        lineas = _lineas_patrones_prueba(ins.doc)
    else:
        lineas = _lineas_patrones_encuesta(ins.doc)
    return (lineas, True) if lineas else (["No hay resúmenes calculados para buscar patrones en este instrumento."], False)


def _resumen_persona(doc: dict[str, Any], persona: dict[str, Any]) -> str:
    """Resumen calculado de una persona: sus respuestas de escala agrupadas por opción.

    Sirve aunque el modelo no redacte (y le da al modelo el resumen ya hecho).
    """
    tipos = {p["id"]: p.get("tipo") for p in _items(doc)}
    grupos: dict[str, list[str]] = {}
    sin_respuesta = []
    for x in persona["respuestas"]:
        if x.get("estado") != "respondida":
            sin_respuesta.append(_corto(x["pregunta_id"]))
        elif tipos.get(x["pregunta_id"]) == "likert":
            grupos.setdefault(str(x.get("significado") or x.get("valor")), []).append(_corto(x["pregunta_id"]))
    partes = [f"«{v}» en {', '.join(ps)}" for v, ps in sorted(grupos.items(), key=lambda g: -len(g[1]))]
    if sin_respuesta:
        partes.append(f"sin respuesta en {', '.join(sin_respuesta)}")
    return "Resumen calculado de sus respuestas de escala: " + ("; ".join(partes) if partes else "no tiene preguntas de escala") + "."


def _lineas_filtro(intencion: Intencion, ins: Instrumento, condiciones: list[tuple[dict[str, Any], str]]) -> tuple[list[str], bool]:
    """Resultado de una consulta con filtro: cuántos cumplen y, según la acción, quiénes o uno completo."""
    doc = ins.doc
    grupo = _grupo(doc, intencion.texto)
    total = len(consultas.filtrar(doc, [], grupo))
    personas = consultas.filtrar(doc, [c for c, _ in condiciones], grupo)
    lineas = [f"Condición: {_describir(doc, c)}" + (f" ({nota})" if nota else "") for c, nota in condiciones]
    if grupo:
        lineas.append("Grupo: " + ", ".join(f"{k} = {v}" for k, v in grupo.items()))
    if not personas:
        return lineas + [f"Ninguno de los {total} respondentes cumple la condición."], False
    pct = round(100 * len(personas) / total, 1) if total else 0.0
    lineas.append(f"Cumplen la condición {len(personas)} de {total} respondentes ({pct} %).")
    ids = [_corto(r["id"]) for r in personas]
    if intencion.accion == "uno":
        elegido = personas[0]
        contexto = "; ".join(f"{k}: {v}" for k, v in (elegido.get("contexto") or {}).items() if v not in (None, ""))
        lineas.append(f"Respondente elegido como ejemplo: {ids[0]}" + (f" ({contexto})" if contexto else "") + ".")
        lineas.append(_resumen_persona(doc, elegido))
        lineas.append("Sus respuestas:")
        for x in elegido["respuestas"][:_MAX_LINEAS_FILTRO]:
            valor = x.get("significado") or x.get("valor") if x.get("estado") == "respondida" else f"sin respuesta ({x.get('motivo') or x.get('estado')})"
            lineas.append(f"{_corto(x['pregunta_id'])} «{x['pregunta']}»: {valor}")
        if len(ids) > 1:
            lineas.append(f"Otros que cumplen la condición: {', '.join(ids[1:11])}" + (f" y {len(ids) - 11} más." if len(ids) > 11 else "."))
    elif intencion.accion in ("lista", "resumen"):
        tope = _MAX_IDS_LISTA if intencion.accion == "lista" else 10
        lineas.append(f"Respondentes que la cumplen: {', '.join(ids[:tope])}" + (f" y {len(ids) - tope} más." if len(ids) > tope else "."))
    return lineas, True


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
    # Líneas que cruzan instrumentos («relación entre uno y otro»): van al final, sin una sola fuente.
    comun: list[str] = field(default_factory=list)
    # «el primer instrumento» → cuál es. Con el ordinal sin resolver, el modelo de 3B respondía
    # que «el primer instrumento no se menciona» aunque el resultado era justo ese (22 oct).
    aclaracion: str = ""
    consulta_texto: str = ""  # la consulta normalizada (para revisar si quedó alguna parte sin condición)

    @property
    def instrumentos(self) -> list[Instrumento]:
        return [p[0] for p in self.partes]

    def _bloque_comun(self) -> list[str]:
        if not self.comun:
            return []
        return ["Relación entre los instrumentos (calculada; no hay más relaciones que estas):\n" + "\n".join(f"- {l}" for l in self.comun)]

    def texto(self, numeros: dict[str, int]) -> str:
        """Bloque RESULTADO CALCULADO para el prompt (con el [Fuente n] de cada instrumento)."""
        bloques = [self.aclaracion] if self.aclaracion else []
        for ins, lineas, _ in self.partes:
            bloques.append(f"[Fuente {numeros.get(ins.id_crudo, '?')}] {ins.titulo} ({ins.tipo_ui}):\n" + "\n".join(f"- {l}" for l in lineas))
        return "\n\n".join(bloques + self._bloque_comun())

    def listado(self, numeros: dict[str, int]) -> str:
        """Respuesta sin LLM agrupada por instrumento (consultas que son solo un listado de hechos)."""
        return "\n\n".join(([self.aclaracion] if self.aclaracion else [])
                           + [f"{ins.titulo} ({ins.tipo_ui}) [Fuente {numeros.get(ins.id_crudo, '?')}]:\n" + "\n".join(f"- {l}" for l in lineas)
                              for ins, lineas, _ in self.partes] + self._bloque_comun())

    def respuesta_directa(self, numeros: dict[str, int]) -> str:
        """Respuesta sin LLM (cuando nada se encontró): las líneas, con su fuente."""
        if self.consulta in ("descripcion", "patrones"):  # varias líneas por instrumento: se agrupan para que se lean
            return self.listado(numeros)
        return "\n".join(f"{l} [Fuente {numeros.get(ins.id_crudo, '?')}]" for ins, lineas, _ in self.partes for l in lineas)


def _ejecutar_en(intencion: Intencion, ins: Instrumento, sesion: Session) -> tuple[list[str], bool] | None:
    """Líneas del resultado y si se encontró, o None si la consulta no aplica a este instrumento."""
    doc, t = ins.doc, intencion.tipo
    if t == "sin_calificar":
        if ins.tipo != "prueba_estandarizada":
            return None
        lineas = ["Indagata no califica las pruebas: no tiene clave de respuestas, así que no sabe qué respuesta es "
                  "correcta ni cuántos aciertos hubo. Lo que sí sabe es qué eligieron los alumnos en cada reactivo:"]
        for r in _items(doc)[:_MAX_LINEAS_PERSONA]:
            if interpretacion := (r.get("resumen") or {}).get("interpretacion"):
                lineas.append(f"{_corto(r['id'])} «{r['texto']}»: {interpretacion}")
        return lineas, True

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
            como = res.get("interpretacion") or ""
            lineas.append(f"{_corto(p['pregunta_id'])} «{p['texto']}»: {como}".rstrip(": "))
        return lineas, True

    if t == "calidad":
        return _lineas_calidad(ins, sesion)

    if t == "estructura":
        return _lineas_estructura(intencion, ins), True

    if t == "descripcion":
        return _lineas_descripcion(ins), True

    if t == "patrones":
        return _lineas_patrones(ins)

    if t == "filtro":
        if ins.tipo != "encuesta" or not (condiciones := _condiciones(doc, intencion.texto)):
            return None
        return _lineas_filtro(intencion, ins, condiciones)

    if t == "postura":
        p = _por_texto(doc, intencion.texto) if ins.tipo == "entrevista" else None
        res = consultas.posturas(doc, p["id"]) if p else {"total": 0}
        if not res["total"]:
            return None  # sin análisis de respuestas: la pregunta sigue por la ruta semántica
        c = res["conteo"]
        partes = [f"{c[k]} {_FRASE_POSTURA[k]}" for k in ("si", "no", "ambivalente", "sin_determinar", "no_aplica") if c.get(k)]
        revisados = sum(d["revisado"] for d in res["detalle"])
        lineas = [f"Pregunta {_corto(p['id'])} «{p['texto']}»: de {res['total']} entrevistados con respuesta analizada, "
                  f"{', '.join(partes)} (análisis revisado por el investigador en {revisados} de {res['total']})."]
        for d in res["detalle"][:_MAX_LINEAS_PERSONA]:
            motivo = f"; motivo: «{d['motivo']}»" if d["motivo"] else ""
            lineas.append(f"{_corto(d['participante'])} ({_FRASE_POSTURA[d['postura']].split()[0] if d['postura'] in ('si', 'no') else d['postura']}): «{d['nucleo']}»{motivo}")
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
        if p is None and not (intencion.preguntas or intencion.tema):
            return None  # ninguna pregunta se parece: sigue por la ruta semántica
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
        lineas = [f"{encabezado}: respondió {persona.get('n_respondidas', 0)} reactivos"
                  + (f", {persona['n_nulas']} nulos" if persona.get("n_nulas") else "")
                  + (f", {persona['n_sin_respuesta']} sin respuesta" if persona.get("n_sin_respuesta") else "") + "."]
        for x in persona["respuestas"][:_MAX_LINEAS_PERSONA]:
            valor = x.get("significado") or x.get("respuesta") or "sin respuesta"
            letra = f"{x['respuesta']}) " if x.get("respuesta") and x.get("significado") and x["respuesta"] != x["significado"] else ""
            lineas.append(f"{_corto(x['reactivo_id'])}: {letra}{valor}")
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


def nombrados(instrumentos: list[Instrumento], texto: str) -> list[Instrumento]:
    """Los instrumentos que la pregunta nombra por su título («la encuesta de carga académica»)."""
    raices = _raices(texto)
    puntos = {ins.id_crudo: len(raices & (_raices(ins.titulo) - _GENERICAS_TITULO)) for ins in instrumentos}
    maximo = max(puntos.values(), default=0)
    return [ins for ins in instrumentos if maximo >= 2 and puntos[ins.id_crudo] == maximo]


def por_ordinal(instrumentos: list[Instrumento], texto: str) -> list[Instrumento]:
    """El instrumento que la pregunta señala por su posición («el primer instrumento», «la segunda encuesta»)."""
    if not (p := _posicion(texto)):
        return []
    posicion, sustantivo, _ = p
    tipo = next((t for raiz, t in _TIPO_DE_PALABRA.items() if sustantivo.startswith(raiz)), None)
    candidatos = [i for i in instrumentos if tipo is None or i.tipo == tipo]
    return [candidatos[posicion]] if candidatos and posicion < len(candidatos) else []


def _alcance(sesion: Session, ids: list[str] | None, texto: str) -> list[Instrumento]:
    instrumentos = cargar_documentos(sesion, ids)
    return por_ordinal(instrumentos, texto) or nombrados(instrumentos, texto) or instrumentos


def _juntar(intencion: Intencion, partes: list[tuple[Instrumento, list[str], bool]]) -> Resultado | None:
    if not partes:
        return None
    # Si en algún instrumento sí se encontró, los «no existe» de los demás sobran.
    if any(encontro for _, _, encontro in partes):
        partes = [p for p in partes if p[2]]
    sin_coincidencia = intencion.tipo == "dijo" and any(l.startswith("(Ninguna respuesta") for _, ls, _ in partes for l in ls)
    return Resultado(intencion.tipo, any(p[2] for p in partes), partes, admite_negativa=sin_coincidencia, consulta_texto=intencion.texto)


_FRASE_POSTURA = {"si": "sí (dicen que sí)", "no": "no (dicen que no)", "ambivalente": "ambivalentes",
                  "sin_determinar": "sin postura determinada", "no_aplica": "sin postura"}


def _postura(pregunta: str, sesion: Session, ids: list[str] | None) -> Resultado | None:
    """Posturas calculadas en entrevistas con análisis de respuestas; None si no aplica."""
    texto = normalizar(pregunta)
    if not _POSTURA_ENT.search(texto):
        return None
    entrevistas = [i for i in _alcance(sesion, ids, texto) if i.tipo == "entrevista"]
    intencion = Intencion("postura", texto=texto)
    return _juntar(intencion, _ejecutar_todos(intencion, entrevistas, sesion)) if entrevistas else None


def resolver(pregunta: str, sesion: Session, ids: list[str] | None) -> Resultado | None:
    """Resultado calculado para la pregunta, o None si va por la ruta semántica."""
    if (por_postura := _postura(pregunta, sesion, ids)) is not None:
        return por_postura
    intencion = detectar(pregunta)
    if intencion is None:
        return None
    todos = cargar_documentos(sesion, ids)
    elegido = por_ordinal(todos, intencion.texto)
    instrumentos = elegido or nombrados(todos, intencion.texto) or todos
    resultado = _juntar(intencion, _ejecutar_todos(intencion, instrumentos, sesion))
    if resultado is not None and intencion.tipo == "descripcion" and _RELACION.search(intencion.texto):
        resultado.comun = _lineas_relacion(resultado.instrumentos)
    if resultado is not None and elegido:
        _, dicho, forma = _posicion(intencion.texto)
        # Forma correcta aunque la pregunta traiga una errata («primer instrumeto»): el juez de métricas no las liga.
        sustantivo = next((n for n in _SUSTANTIVOS if dicho.startswith(n[:6])), dicho)
        resultado.aclaracion = (f"«{forma.format(sustantivo)}» es «{elegido[0].titulo}», "
                                "el que ocupa ese lugar en la selección del chat.")
    if resultado is None and intencion.tipo == "filtro":
        # Las reglas no hallaron la condición: quizá es otra intención («cuántos están de acuerdo con p4»).
        otra = detectar(pregunta, sin_filtro=True)
        if otra is not None:
            resultado = _juntar(otra, _ejecutar_todos(otra, instrumentos, sesion))
    return resultado


def _ejecutar_todos(intencion: Intencion, instrumentos: list[Instrumento], sesion: Session) -> list[tuple[Instrumento, list[str], bool]]:
    partes: list[tuple[Instrumento, list[str], bool]] = []
    for ins in instrumentos:
        try:
            salida = _ejecutar_en(intencion, ins, sesion)
        except (KeyError, TypeError, ValueError) as exc:  # documento con una forma inesperada
            logger.warning("Consulta %s falló en el instrumento %s: %s", intencion.tipo, ins.id_crudo, exc)
            continue
        if salida is not None:
            partes.append((ins, *salida))
    return partes


# ── Respaldo con Ollama para los filtros que las reglas no entienden ───────────

_MAX_PREGUNTAS_CATALOGO = 40
_PROMPT_FILTRO = (
    "Traduce la PETICIÓN a una condición sobre las respuestas de una encuesta. Usa SOLO las preguntas y "
    "opciones del CATÁLOGO, copiadas tal cual. No respondas la petición.\n"
    'Responde solo JSON: {{"instrumento": "<id>", "condiciones": [{{"pregunta": "p13", "valores": ["<opción>"]}}]}}\n'
    'Para preguntas numéricas usa {{"pregunta": "p17", "comparacion": [">", 20]}} (operadores >, >=, <, <=).\n'
    'Si ninguna pregunta del catálogo corresponde, responde {{"condiciones": []}}.\n\n'
    "CATÁLOGO:\n{catalogo}\n\nPETICIÓN: {pregunta}"
)


def _catalogo(instrumentos: list[Instrumento]) -> str:
    bloques = []
    for ins in instrumentos:
        indice = _indice(ins.doc)
        lineas = [f"Instrumento {ins.id_crudo}: {ins.titulo}"]
        for p in _items(ins.doc)[:_MAX_PREGUNTAS_CATALOGO]:
            datos = indice.get(p["id"])
            if datos is None:
                continue
            opciones = "número" if datos.numerica else "; ".join(datos.valores[:8])
            lineas.append(f"{_corto(p['id'])} | {p['texto'][:90]} | opciones: {opciones}")
        bloques.append("\n".join(lineas))
    return "\n\n".join(bloques)


def _validar(ins: Instrumento, crudas: Any) -> list[tuple[dict[str, Any], str]]:
    """Condiciones del modelo que existen en el catálogo del documento (las demás se descartan)."""
    indice, salida = _indice(ins.doc), []
    for c in crudas if isinstance(crudas, list) else []:
        numero = re.search(r"\d+", str(c.get("pregunta"))) if isinstance(c, dict) else None
        p = _por_numero(ins.doc, int(numero.group())) if numero else None
        if p is None:
            continue
        datos = indice.get(p["id"])
        if datos is None:
            continue
        if isinstance(c.get("valores"), list):
            pedidos = {normalizar(str(v)) for v in c["valores"]}
            valores = [v for v in datos.valores if normalizar(v) in pedidos]
            if valores:
                salida.append(({"pregunta_id": p["id"], "valores": valores}, "condición interpretada por el modelo"))
        elif isinstance(c.get("comparacion"), list) and len(c["comparacion"]) == 2 and datos.numerica:
            op, n = c["comparacion"]
            if op in (">", ">=", "<", "<=") and consultas._numero(n) is not None:
                salida.append(({"pregunta_id": p["id"], "comparacion": [op, consultas._numero(n)]}, "condición interpretada por el modelo"))
    return salida[:3]


async def filtro_llm(pregunta: str, sesion: Session, ids: list[str] | None) -> Resultado | None:
    """Condición del filtro según Ollama (validada contra el catálogo), o None."""
    if not settings.RAG_FILTRO_LLM or not pide_filtro(pregunta):
        return None
    from services import ollama_client

    texto = normalizar(pregunta)
    instrumentos = [i for i in _alcance(sesion, ids, texto) if i.tipo == "encuesta"][:3]
    if not instrumentos:
        return None
    modelo = settings.RAG_CLASIFICADOR_MODELO or settings.OLLAMA_MODEL
    salida, degradado = await ollama_client.generar_no_stream(
        _PROMPT_FILTRO.format(catalogo=_catalogo(instrumentos), pregunta=pregunta), modelo,
        formato="json", opciones={"temperature": 0, "num_predict": 200},
    )
    if degradado:
        return None
    try:
        datos = json.loads(salida)
    except ValueError:
        logger.warning("Filtro por modelo: respuesta no válida %r", salida[:200])
        return None
    ins = next((i for i in instrumentos if str(datos.get("instrumento", "")) == i.id_crudo), instrumentos[0])
    condiciones = _validar(ins, datos.get("condiciones"))
    # Si la consulta nombra literalmente ciertas preguntas («certificación» → «¿Has presentado algún examen de
    # certificación…?»), el modelo no puede poner la condición en otra que no comparte ninguna palabra con la
    # consulta (28 oct: eligió «¿cambio de profesor…?» > 1). Sin coincidencia literal (sinónimos: «empleo» →
    # «carga laboral»), se confía en el modelo, ya validado contra el catálogo.
    raices = _raices(texto)
    largas = {t[:5] for t in re.findall(r"[a-z]+", texto) if len(t) >= 6 and t not in _STOP_FILTRO and t not in _VERBOS_CONSULTA}
    nombradas = {p["id"] for p in _items(ins.doc) if largas & _raices(p.get("texto", ""))}

    def plausible(c: dict[str, Any]) -> bool:
        p_texto = next((p.get("texto", "") for p in _items(ins.doc) if p["id"] == c["pregunta_id"]), "")
        comparte = bool(raices & _raices(p_texto)) or any(raices & _raices(v) for v in c.get("valores") or [])
        return comparte or not nombradas

    condiciones = [(c, nota) for c, nota in condiciones if plausible(c)]
    if not condiciones:
        return None
    intencion = Intencion("filtro", texto=texto, accion=_accion(texto))
    return _juntar(intencion, [(ins, *_lineas_filtro(intencion, ins, condiciones))])
