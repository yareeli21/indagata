"""Chat RAG sobre los instrumentos del usuario y del sistema.

Ingesta: la colección `instrumentos` la escribe el storage-service (solo con
metadatos aprobados). `indexar()` le pide asegurar la ingesta de los
instrumentos de una investigación; los no aprobados se reportan como omitidos.

Consulta: se vectoriza la pregunta y se recuperan los fragmentos más cercanos
(ficha del instrumento, reactivos con sus resultados, texto de entrevistas).
Solo pasan los que alcanzan `RAG_MIN_SCORE`; si ninguno lo hace, se responde
`MENSAJE_SIN_CONTEXTO` sin llamar al LLM.
  - Con `instrumentoIds`: solo la investigación activa.
  - Sin ellos: todo el acervo aprobado del sistema.
La respuesta la genera Ollama (SSE o JSON) y cada consulta queda en `rag_log`.

Antes de generar (`planear`):
  1. Dominio acotado (`dominio.py`): reglas de intención (privacidad, manipulación,
     fuera del dominio) → mensaje fijo sin LLM.
  2. Ayuda de la plataforma → solo la base curada `config/ayuda.yaml`.
  3. Enrutador (`enrutador.py`): si la pregunta pide un dato puntual o una cuenta,
     el resultado se CALCULA sobre el documento final vigente y el LLM solo lo
     redacta; si no existe, se dice sin LLM.
  4. Si no, recuperación semántica de PA (umbral, diversidad, citas [Fuente n]),
     con el glosario metodológico cuando la pregunta es de definición, y el
     clasificador de la zona gris cuando la similitud es ambigua.
Después de generar: se quita la frase de «sin información» sobrante y se tachan
datos personales. La decisión, la ruta y el contexto usado quedan en rag_log.

Caché: antes de todo se calcula la huella de la consulta (pregunta normalizada,
alcance, versión vigente de cada instrumento, contexto y modelo). Si ya se respondió
igual hace menos de `RAG_CACHE_HORAS`, se repite esa respuesta sin llamar a Ollama
(publicar una versión nueva cambia la huella, así que nunca se sirve algo viejo).
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse

from shared.db.core.config import settings
from shared.models.kpi import KPI
from shared.models.kpi_fuente import KPIFuente
from shared.models.rag_log import RagLog
from shared.models.version_conocimiento import VersionConocimiento

from models import ChatRequest, ChatResponse, FuenteChatOut, IndexRequest, ReferenciaChatOut
from services import (consulta_planificada, dominio, ejecutor, enrutador, evaluacion, interpretacion, ollama_client, prompt,
                      hibrida, juez_fable, seguimiento, storage_client, trazabilidad, vectores)
from services.plan_consulta import ESTRUCTURADAS, PlanConsulta

logger = logging.getLogger("visualization-service")

_TIPOS = {"Encuesta", "Entrevista", "Prueba estandarizada"}
# Se piden más candidatos de los que caben y se eligen con tope por instrumento.
_CANDIDATOS_POR_FRAGMENTO = 4
_MAX_FICHAS_POR_INSTRUMENTO = 1
_MAX_FRAGMENTOS_POR_INSTRUMENTO = 3
MENSAJE_SIN_CONTEXTO = (
    f"{prompt.SIN_INFORMACION} Recuerda que solo entran al RAG los instrumentos con "
    "metadatos aprobados por su autor; puedes ampliar la selección de tu investigación."
)


def fabrica_sesiones():
    """Sesión de BD para registrar consultas (reemplazable en pruebas)."""
    from shared.db.session import SessionLocal

    return SessionLocal()


# ── Ingesta ────────────────────────────────────────────────────────────────────


def indexar(peticion: IndexRequest) -> dict[str, Any]:
    resultados: list[dict[str, Any]] = []
    for instrumento_id in peticion.instrumentoIds:
        if not instrumento_id.isdigit():
            resultados.append(
                {"instrumentoId": instrumento_id, "chunks": 0, "estado": "omitido", "motivo": "Identificador inválido."}
            )
            continue
        id_crudo = int(instrumento_id)
        try:
            if not peticion.reindexar:
                estado = storage_client.estado_indice(id_crudo)
                if estado.get("indexado"):
                    resultados.append(
                        {"instrumentoId": instrumento_id, "chunks": estado.get("chunks", 0), "estado": "indexado", "motivo": None}
                    )
                    continue
            r = storage_client.indexar(id_crudo, reindexar=True)
            resultados.append(
                {"instrumentoId": instrumento_id, "chunks": r.get("chunks", 0), "estado": r.get("estado", "indexado"), "motivo": r.get("motivo")}
            )
        except storage_client.StorageError as exc:
            if exc.status_code is None:
                raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
            resultados.append({"instrumentoId": instrumento_id, "chunks": 0, "estado": "omitido", "motivo": str(exc)})

    indexados = [r for r in resultados if r["estado"] == "indexado"]
    total = sum(int(r["chunks"] or 0) for r in indexados)
    return {
        "coleccion": settings.CHROMA_COLLECTION_INSTRUMENTOS,
        "total_chunks": total,
        "instrumentos": resultados,
        "mensaje": f"{len(indexados)} de {len(resultados)} instrumento(s) disponibles en el RAG ({total} fragmentos).",
    }


# ── Recuperación ───────────────────────────────────────────────────────────────


def _kpis(valor: Any) -> list[str]:
    if isinstance(valor, list):
        return [str(k) for k in valor]
    if isinstance(valor, str) and valor:
        try:
            datos = json.loads(valor)
        except json.JSONDecodeError:
            return []
        return [str(k) for k in datos] if isinstance(datos, list) else []
    return []


def _ficha_completa(coleccion: Any, instrumento_id: str) -> str:
    """Todos los chunks de la ficha de un instrumento, en orden y sin repeticiones.

    Solo entra una ficha por instrumento y era la pieza más parecida a la pregunta: a
    veces la cola («KPIs asociados: …») sin el objetivo ni lo que pregunta, y el modelo
    describía el instrumento por sus KPIs. Cada pieza repite el título y arranca con el
    solape de la anterior; ambos se quitan al unirlas. Si falla, se usa la pieza sola.
    """
    try:
        res = coleccion.get(where={"$and": [{"instrumentoId": instrumento_id}, {"seccion": "encabezado"}]},
                            include=["metadatas", "documents"])
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo leer la ficha completa de %s: %s", instrumento_id, exc)
        return ""
    piezas = sorted(zip(res.get("metadatas") or [], res.get("documents") or []),
                    key=lambda par: int((par[0] or {}).get("chunk_index") or 0))
    titulo, cuerpo = "", ""
    for _, texto in piezas:
        primera, _, resto = str(texto or "").partition("\n")
        titulo = titulo or primera
        resto = resto if primera == titulo else str(texto or "")
        # Solape: el mayor final del cuerpo que es principio de la pieza nueva. Se compara
        # sin distinguir espacios: el solape se guarda con espacios donde había saltos.
        plano = " ".join(cuerpo.split())
        solape = next((n for n in range(min(len(cuerpo), len(resto)), 9, -1)
                       if not resto[n:n + 1].strip() and plano.endswith(" ".join(resto[:n].split()))), 0)
        nuevo = resto[solape:]
        cuerpo = f"{cuerpo}{'' if not cuerpo or solape else chr(10)}{nuevo}" if nuevo.strip() else cuerpo
    return f"{titulo}\n{cuerpo.strip()}" if titulo and cuerpo else ""


def _buscar(peticion: ChatRequest, vector: list[float]) -> tuple[list[dict[str, Any]], float]:
    """Fragmentos del alcance que pasan el umbral (con diversidad) y la similitud máxima vista."""
    try:
        coleccion = vectores.coleccion_existente(settings.CHROMA_COLLECTION_INSTRUMENTOS)
    except Exception as exc:  # noqa: BLE001
        logger.error("Vector store no disponible: %s", exc)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Vector store no disponible.") from exc
    if coleccion is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Aún no hay instrumentos en el RAG: aprueba los metadatos de tus instrumentos.",
        )

    ids = [i for i in (peticion.instrumentoIds or []) if i]
    where = {"instrumentoId": {"$in": ids}} if ids else None
    try:
        res = hibrida.consultar(coleccion, vector, peticion.pregunta, peticion.top_k * _CANDIDATOS_POR_FRAGMENTO,
                                where, ids, fabrica_sesiones)
    except Exception as exc:  # noqa: BLE001
        logger.error("Vector store no disponible: %s", exc)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Vector store no disponible.") from exc

    fragmentos: list[dict[str, Any]] = []
    encabezados: dict[str, int] = {}
    por_instrumento: dict[str, int] = {}
    score_max = 0.0
    for n, (meta, doc, dist) in enumerate(zip(
        (res.get("metadatas") or [[]])[0], (res.get("documents") or [[]])[0], (res.get("distances") or [[]])[0]
    )):
        meta = meta or {}
        score = round(1.0 - float(dist), 4)
        score_max = max(score_max, score)
        lexico = _lexico(res, n)
        if not hibrida.relevante({"score": score, "seccion": str(meta.get("seccion", "")), **lexico}):
            continue  # poco relacionado (ni por significado ni por palabras): no se le da al LLM para que no improvise
        if len(fragmentos) >= peticion.top_k:
            break
        # Diversidad: las fichas (encabezado) se parecen a casi cualquier pregunta y,
        # sin tope, desplazan a los reactivos con resultados y al texto de entrevistas.
        inst, seccion = str(meta.get("instrumentoId", "")), str(meta.get("seccion", ""))
        if seccion == "encabezado" and encabezados.get(inst, 0) >= _MAX_FICHAS_POR_INSTRUMENTO:
            continue
        if por_instrumento.get(inst, 0) >= _MAX_FRAGMENTOS_POR_INSTRUMENTO:
            continue
        if seccion == "encabezado":
            encabezados[inst] = encabezados.get(inst, 0) + 1
            doc = _ficha_completa(coleccion, inst) or doc
        por_instrumento[inst] = por_instrumento.get(inst, 0) + 1
        fragmentos.append(
            {
                "instrumentoId": inst,
                "titulo": str(meta.get("titulo", "")),
                "tipo": meta.get("tipo") if meta.get("tipo") in _TIPOS else "Encuesta",
                "investigador": str(meta.get("investigador", "")),
                "kpis": _kpis(meta.get("kpis")),
                "seccion": seccion,
                "fragmento": str(doc or ""),
                "score": score,
                "preguntaId": str(meta.get("preguntaId", "")),
                "respondenteId": str(meta.get("respondenteId", "")),
                # Trazabilidad: posición en el documento indexado y texto sin recortes (services/trazabilidad.py).
                "chunkIndex": 0 if seccion == "encabezado" else meta.get("chunk_index"),
                "fragmentoOriginal": str(doc or ""),
                **lexico,
            }
        )
    return fragmentos, score_max


def _lexico(res: dict[str, Any], n: int) -> dict[str, Any]:
    """Cobertura de la pregunta y posiciones en las dos búsquedas del n-ésimo resultado (búsqueda híbrida)."""
    def dato(clave: str) -> Any:
        lista = (res.get(clave) or [[]])[0]
        return lista[n] if n < len(lista) else None
    return {"coincidencia": dato("coincidencias"), "palabras": dato("palabras"), "rangos": dato("rangos")}


def _kpis_usados(fragmentos: list[dict[str, Any]], instrumento_id: str, consulta_kpi: bool) -> list[str]:
    """KPIs que se muestran en la tarjeta: solo si la consulta trata de KPIs o se recuperó un fragmento de KPI.

    Antes cada tarjeta traía todos los KPIs del instrumento aunque no tuvieran que ver con la pregunta (Fase 0).
    """
    propios = [f for f in fragmentos if f["instrumentoId"] == instrumento_id]
    if consulta_kpi or any(f.get("seccion") == "kpi" for f in propios):
        return next((f["kpis"] for f in propios if f.get("kpis")), [])
    return []


def _numerar(fragmentos: list[dict[str, Any]], primero: list[enrutador.Instrumento] | None = None,
             consulta_kpi: bool = True) -> list[FuenteChatOut]:
    """Una fuente por instrumento, numerada: [Fuente n] es la n-ésima tarjeta de la UI.

    Los instrumentos del resultado calculado (`primero`) van antes; después, los de
    los fragmentos en orden de relevancia. Asigna `numero` a cada fragmento.
    """
    fuentes: list[FuenteChatOut] = []
    numeros: dict[str, int] = {}
    for ins in primero or []:
        numeros[ins.id_crudo] = len(numeros) + 1
        kpis = [k.get("nombre", "") for k in ins.doc.get("kpis_asociados") or []] if consulta_kpi else []
        fuentes.append(FuenteChatOut(numero=numeros[ins.id_crudo], instrumentoId=ins.id_crudo, titulo=ins.titulo,
                                     tipo=ins.tipo_ui, investigador="", kpis=kpis, fragmento="Resultado calculado sobre el documento final."))
    for f in fragmentos:
        if f["instrumentoId"] in numeros:
            f["numero"] = numeros[f["instrumentoId"]]
            continue
        numeros[f["instrumentoId"]] = f["numero"] = len(numeros) + 1
        fuentes.append(
            FuenteChatOut(
                numero=f["numero"],
                instrumentoId=f["instrumentoId"],
                titulo=f["titulo"],
                tipo=f["tipo"],
                investigador=f["investigador"],
                kpis=_kpis_usados(fragmentos, f["instrumentoId"], consulta_kpi),
                fragmento=f["fragmento"],
            )
        )
    return fuentes


# ── RAG + cálculo (4 nov) ─────────────────────────────────────────────────────
# Antes, en la ruta del plan la redacción recibía solo el resultado calculado y Chroma no se consultaba: el sistema
# era «LLM + cálculo». Ahora cada respuesta calculada lleva también el TEXTO RECUPERADO más parecido a la pregunta,
# del mismo instrumento: el cálculo pone las cifras y el RAG el texto con que el modelo contextualiza e interpreta.

# Secciones de Chroma que complementan cada intención. Las de personas se filtran por los respondentes del resultado.
_SECCIONES_APOYO = {
    "datos_respondente": ["intercambio", "respondente", "alumno"],
    "kpi": ["kpi", "pregunta", "reactivo"],
}
_SECCIONES_APOYO_DEFECTO = ["encabezado", "pregunta", "reactivo", "intercambio"]
_MAX_APOYO = 4
# Si con el filtro nada pasa el umbral, entran los más cercanos igual: el RAG no se descarta (5 nov, corrida 1709–1771:
# «¿por qué consideras que es preocupante?» o «¿de qué trata el instrumento?» se respondían solo con el cálculo).
_MAX_FICHA_APOYO = 1200
# En los patrones de una entrevista el texto ES la evidencia: entran más intercambios y sin umbral de similitud
# («¿qué patrones encuentras?» se parece poco a cualquier respuesta concreta).
_MAX_APOYO_ENTREVISTA = 8
_CAMPOS_RECUPERADOS = 2  # intercambios recuperados que se suman a la tabla de una persona en una entrevista


def _consulta_apoyo(pregunta: str, historial: list[Any]) -> str:
    """Texto que se vectoriza: la pregunta y, en un seguimiento corto («¿Le parecieron suficientes?»), también la
    pregunta anterior del usuario, que es la que dice de qué se habla."""
    anteriores = [m.texto for m in historial if m.rol == "usuario"]
    if anteriores and len(pregunta.split()) <= 8:
        return f"{anteriores[-1]} {pregunta}"
    return pregunta


def _apoyo_rag(peticion: ChatRequest, preparada: "consulta_planificada.Preparada") -> list[dict[str, Any]]:
    """Fragmentos de Chroma que acompañan al resultado calculado del plan (sin tope por instrumento de la ruta
    semántica: todos son de los instrumentos que el resultado usó)."""
    p = preparada.plan
    if p is None or p.intencion not in ESTRUCTURADAS or not preparada.ejecuciones:
        return []
    ejecuciones = preparada.ejecuciones
    entrevista = all(e.instrumento.tipo == "entrevista" for e in ejecuciones)
    patrones_texto = p.intencion == "hallazgo" and entrevista
    secciones = ["intercambio"] if patrones_texto else _SECCIONES_APOYO.get(p.intencion, _SECCIONES_APOYO_DEFECTO)
    condiciones: list[dict[str, Any]] = [{"instrumentoId": {"$in": [e.instrumento.id_crudo for e in ejecuciones]}},
                                         {"seccion": {"$in": secciones}}]
    if p.intencion == "datos_respondente":
        personas = [r for e in ejecuciones for r in e.respondentes][:20]
        if not personas:
            return []
        condiciones.append({"respondenteId": {"$in": personas}})
    elif p.intencion == "hallazgo" and not entrevista:
        # El texto de las preguntas de los patrones calculados: con la búsqueda abierta llegaban otras preguntas y el
        # modelo explicaba esas en lugar de los patrones (4 nov, consulta 1696).
        preguntas = [q for e in ejecuciones for q in e.preguntas][:20]
        if not preguntas:
            return []
        condiciones.append({"preguntaId": {"$in": preguntas}})
    limite = _MAX_APOYO_ENTREVISTA if patrones_texto else _MAX_APOYO
    try:
        coleccion = vectores.coleccion_existente(settings.CHROMA_COLLECTION_INSTRUMENTOS)
        if coleccion is None:
            return []
        res = coleccion.query(query_embeddings=[_vector(_consulta_apoyo(peticion.pregunta, peticion.historial))],
                              n_results=limite * 2, where={"$and": condiciones},
                              include=["metadatas", "documents", "distances"])
    except Exception as exc:  # noqa: BLE001 — sin Chroma se responde solo con el cálculo
        logger.warning("Texto de apoyo del RAG no disponible: %s", exc)
        return []
    numeros = {e.instrumento.id_crudo: n for n, e in enumerate(ejecuciones, start=1)}
    candidatos = _fragmentos_de(res, coleccion)
    for f in candidatos:
        f["numero"] = numeros.get(f["instrumentoId"], 1)
    salida = [f for f in candidatos if f["score"] >= settings.RAG_MIN_SCORE or patrones_texto][:limite]
    return salida  # sin relleno bajo el umbral (10 nov)


def _fragmentos_de(res: dict[str, Any], coleccion: Any) -> list[dict[str, Any]]:
    """Fragmentos de una consulta a Chroma, sin repetidos, en orden de similitud. La ficha (`encabezado`) se completa:
    su primer fragmento solo trae el título."""
    salida: list[dict[str, Any]] = []
    vistos: set[str] = set()
    for n, (meta, doc, dist) in enumerate(zip((res.get("metadatas") or [[]])[0], (res.get("documents") or [[]])[0],
                                              (res.get("distances") or [[]])[0])):
        meta, score = meta or {}, round(1.0 - float(dist), 4)
        inst, seccion = str(meta.get("instrumentoId", "")), str(meta.get("seccion", ""))
        if seccion == "encabezado":
            if f"ficha {inst}" in vistos:
                continue
            vistos.add(f"ficha {inst}")
            doc = (_ficha_completa(coleccion, inst) or doc)[:_MAX_FICHA_APOYO]
        if str(doc) in vistos:
            continue
        vistos.add(str(doc))
        salida.append({"instrumentoId": inst, "numero": 1, "titulo": str(meta.get("titulo", "")),
                       "tipo": meta.get("tipo") if meta.get("tipo") in _TIPOS else "Encuesta",
                       "investigador": str(meta.get("investigador", "")), "kpis": _kpis(meta.get("kpis")),
                       "seccion": seccion, "fragmento": str(doc or ""), "score": score,
                       "preguntaId": str(meta.get("preguntaId", "")), "respondenteId": str(meta.get("respondenteId", "")),
                       "chunkIndex": 0 if seccion == "encabezado" else meta.get("chunk_index"),
                       "fragmentoOriginal": str(doc or ""), **_lexico(res, n)})
    return salida


# ── RAG primero (5 nov) ───────────────────────────────────────────────────────
# Toda pregunta (salvo las que bloquean las reglas de dominio y la ayuda) empieza buscando en Chroma. Lo recuperado:
#   1. orienta a la interpretación (qué pregunta o parte del instrumento se parece más a lo que se pide);
#   2. responde por sí mismo cuando no hace falta calcular (o cuando el plan solo sabría pedir aclaración);
#   3. complementa el cálculo cuando la pregunta implica contar o filtrar: si difieren, manda el cálculo.
_MAX_RECUPERADOS = 5
_MAX_PISTAS = 3


def _recuperar_primero(peticion: ChatRequest, estado: dict[str, Any] | None = None
                       ) -> tuple[list[dict[str, Any]], float, dict[str, float]]:
    """Los fragmentos del alcance más parecidos a la pregunta (o al seguimiento con su pregunta anterior) y la
    similitud máxima. Sin Chroma devuelve vacío: las demás etapas siguen."""
    ids = [i for i in (peticion.instrumentoIds or []) if i]
    try:
        coleccion = vectores.coleccion_existente(settings.CHROMA_COLLECTION_INSTRUMENTOS)
        if coleccion is None:
            return [], 0.0, {}
        consulta = _consulta_apoyo(peticion.pregunta, peticion.historial)
        res = hibrida.consultar(coleccion, _vector(consulta), consulta, _MAX_RECUPERADOS * 3,
                                {"instrumentoId": {"$in": ids}} if ids else None, ids, fabrica_sesiones)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning("Recuperación del RAG no disponible: %s", exc)
        return [], 0.0, {}
    candidatos = _fragmentos_de(res, coleccion)
    score_max = max((f["score"] for f in candidatos), default=0.0)
    if any(hibrida.relevante(f) for f in candidatos):
        # Lo encontró la búsqueda por palabras aunque el coseno no llegue: para las decisiones del chat («¿hay algo
        # del tema?») cuenta como relevante; la similitud mostrada sigue siendo el coseno.
        score_max = max(score_max, settings.RAG_MIN_SCORE)
    # La mayor similitud de cada instrumento, pase o no el umbral: la tarjeta de fuente la muestra.
    similitudes: dict[str, float] = {}
    for f in candidatos:
        clave = str(f["instrumentoId"])
        similitudes[clave] = max(similitudes.get(clave, 0.0), f["score"])
    # A la respuesta solo llega lo que alcanza el umbral (10 nov: antes se completaba con los más cercanos sobre
    # RAG_FUERA_MAX y una pregunta sin relación se respondía con ellos). Las pistas de la interpretación sí usan los
    # cercanos: solo orientan el plan y no se muestran; sin ellas «¿qué porcentaje organiza su material…?» (0.62) se
    # quedaba en aclaración.
    if estado is not None:
        estado["pistas"] = [f for f in candidatos
                            if f["score"] >= settings.RAG_FUERA_MAX or hibrida.relevante(f)][:_MAX_RECUPERADOS]
    return [f for f in candidatos if hibrida.relevante(f)][:_MAX_RECUPERADOS], score_max, similitudes


_SOBRE_EL_INSTRUMENTO = {"descripcion", "estructura"}


def _fichas(instrumentos: list[enrutador.Instrumento]) -> list[dict[str, Any]]:
    """La ficha de cada instrumento, leída de Chroma por sus metadatos. «¿De qué trata el instrumento?» se parece poco
    a cualquier fragmento (similitud 0.29 con el 127, 5 nov) y no recuperaba nada, aunque la ficha es la respuesta."""
    try:
        coleccion = vectores.coleccion_existente(settings.CHROMA_COLLECTION_INSTRUMENTOS)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Fichas del RAG no disponibles: %s", exc)
        return []
    if coleccion is None:
        return []
    salida = []
    for ins in instrumentos:
        if ficha := _ficha_completa(coleccion, ins.id_crudo):
            salida.append({"instrumentoId": ins.id_crudo, "numero": 1, "titulo": ins.titulo, "tipo": ins.tipo_ui,
                           "investigador": "", "kpis": [], "seccion": "encabezado",
                           "fragmento": ficha[:_MAX_FICHA_APOYO], "score": None, "preguntaId": "", "respondenteId": "",
                           "chunkIndex": 0, "fragmentoOriginal": ficha})
    return salida


def _pistas(recuperados: list[dict[str, Any]]) -> str:
    """Para la interpretación: qué partes del instrumento recuperó el RAG («r03 (0.62): ¿Cuál es la principal función
    de una VPN?»). Solo la primera línea de cada fragmento: las cifras no le sirven para elegir el plan."""
    return "\n".join(f"- {_etiqueta_fragmento(f)} (similitud {f['score']:.2f}): "
                     f"{(f['fragmento'].splitlines() or [''])[0][:160]}" for f in recuperados[:_MAX_PISTAS])


def _apoyo_de_recuperados(recuperados: list[dict[str, Any]],
                          preparada: "consulta_planificada.Preparada") -> list[dict[str, Any]]:
    """Si la búsqueda filtrada del cálculo no trajo nada, lo que recuperó la búsqueda general de sus instrumentos."""
    numeros = {e.instrumento.id_crudo: n for n, e in enumerate(preparada.ejecuciones, start=1)}
    return [{**f, "numero": numeros[f["instrumentoId"]]} for f in recuperados if f["instrumentoId"] in numeros][:_MAX_APOYO]


_ID_EXPLICITO = re.compile(r"\b[RAE]\d{2,5}\b")  # sin IGNORECASE: «r03» es un reactivo, no una persona


def _rag_responde_aclaracion(preparada: "consulta_planificada.Preparada", pregunta: str, seguimiento: bool,
                             score_max: float) -> bool:
    """¿La aclaración del plan se cambia por una respuesta con lo recuperado? Sí, si la pregunta es del alcance (o un
    seguimiento) y el RAG encontró algo sobre el umbral. No si nombra una persona por su ID: el fragmento más parecido
    sería de otra persona («¿Y R0067?» se contestaría con lo que dijo R0023). Tampoco «¿qué opinan de eso?» sin
    conversación previa: no hay a qué se refiera «eso»."""
    p = preparada.plan
    if p is None or p.intencion != "aclaracion" or score_max < settings.RAG_MIN_SCORE or _ID_EXPLICITO.search(pregunta):
        return False
    # Con similitud alta la pregunta es del alcance aunque no use sus palabras («¿cuántos estudian ingeniería?»).
    return seguimiento or score_max >= settings.RAG_ZONA_GRIS_MAX \
        or consulta_planificada.del_alcance(pregunta, preparada.catalogos)


def _completar_con_recuperados(preparada: "consulta_planificada.Preparada", apoyo: list[dict[str, Any]]) -> None:
    """En una entrevista, lo que dijo una persona puede estar en una pregunta que no nombra el tema: «¿cuántas sesiones
    le dieron?» está en p04 «¿Has utilizado alguno de esos servicios?» y el plan eligió p05 (4 nov, consulta 1676).
    Las preguntas de los intercambios más parecidos se suman a la tabla y se vuelve a calcular."""
    p = preparada.plan
    if p is None or p.intencion != "datos_respondente" or not isinstance(p.campos, list) \
            or not all(e.instrumento.tipo == "entrevista" for e in preparada.ejecuciones):
        return
    recuperadas = list(dict.fromkeys(f["preguntaId"].rsplit("-", 1)[-1] for f in apoyo
                                     if f["seccion"] == "intercambio" and f["preguntaId"]))[:_CAMPOS_RECUPERADOS]
    nuevas = [c for c in recuperadas if c not in p.campos]
    if not nuevas:
        return
    plan = p.model_copy(update={"campos": [*p.campos, *nuevas]})
    preparada.interp.plan = plan
    preparada.interp.correcciones.append(f"RAG: se agregó {', '.join(nuevas)} (intercambio más parecido a la pregunta)")
    preparada.ejecuciones = ejecutor.ejecutar(plan, preparada.instrumentos)


def _anterior(historial: list[Any]) -> tuple[str, dict[str, Any] | None]:
    """De qué trató la última respuesta (su pregunta, intención, respondentes, preguntas y criterio) y su plan, leídos
    de rag_log.

    Solo se usa si su pregunta es el último mensaje del usuario en el historial: así un ID ajeno no lee otra consulta.
    """
    previa = next((m for m in reversed(historial) if m.rol == "asistente" and m.consultaId), None)
    usuario = next((m.texto for m in reversed(historial) if m.rol == "usuario"), "")
    if previa is None:
        return "", None
    try:
        sesion = fabrica_sesiones()
        try:
            fila = sesion.get(RagLog, previa.consultaId)
            if fila is None or fila.pregunta.strip() != usuario.strip():
                return "", None
            plan = (fila.plan or {}).get("plan") or {}
            lineas = [f"Pregunta anterior: «{fila.pregunta[:200]}»"]
            if plan.get("intencion"):
                lineas.append(f"Intención: {plan['intencion']}")
            lineas += [f"{f.get('titulo') or 'Instrumento'}: {str(f.get('fragmento') or '')[:300]}"
                       for f in ((fila.salida or {}).get("fuentes") or [])[:2] if f.get("fragmento")]
            return "\n".join(lineas), plan or None
        finally:
            sesion.close()
    except Exception as exc:  # noqa: BLE001 — sin BD se sigue con el historial de texto
        logger.warning("No se pudo leer la consulta anterior: %s", exc)
        return "", None


# «¿Qué significa eso?», «¿por qué?», «¿en qué te basas?»: se pregunta por la respuesta anterior, no por algo nuevo.
_SOBRE_LO_ANTERIOR = re.compile(r"\b(?:eso|esto|ello|lo anterior|por que|signific\w*|en que te basas|a que se debe|"
                                r"expli\w*|interpret\w*)\b")


def _retomar_anterior(preparada: "consulta_planificada.Preparada", pregunta: str,
                      plan_anterior: dict[str, Any] | None) -> None:
    """Si la interpretación pidió aclaración pero la pregunta se refiere a la respuesta anterior («y eso, ¿qué puede
    significar?»), se vuelve a calcular el plan anterior y la redacción, con la conversación, explica (4 nov, consultas
    1697 y 1702: el modelo pedía aclaración aunque recibía el tema anterior)."""
    p = preparada.plan
    if p is None or p.intencion != "aclaracion" or not plan_anterior \
            or plan_anterior.get("intencion") not in ESTRUCTURADAS \
            or not _SOBRE_LO_ANTERIOR.search(dominio.normalizar(pregunta)):
        return
    try:
        plan = PlanConsulta.model_validate(plan_anterior)
    except ValueError:
        return
    preparada.interp.plan = plan
    preparada.interp.correcciones.append("aclaración → plan de la respuesta anterior (la pregunta se refiere a ella)")
    sesion = fabrica_sesiones()
    try:
        preparada.ejecuciones = ejecutor.ejecutar(plan, preparada.instrumentos,
                                                  ejecutor.fiabilidad_de(sesion, preparada.instrumentos))
    finally:
        sesion.close()


_MAX_CONVERSACION = 2
_MAX_TEXTO_CONVERSACION = 300


def _conversacion(historial: list[Any]) -> str:
    """Los últimos mensajes sin tablas, para que la redacción entienda «¿por qué?» o «¿en qué te basas?»."""
    return "\n".join(f"{'Usuario' if m.rol == 'usuario' else 'Asistente'}: "
                     f"{interpretacion.sin_tablas(m.texto)[:_MAX_TEXTO_CONVERSACION]}"
                     for m in historial[-_MAX_CONVERSACION:])


def recuperar(peticion: ChatRequest) -> tuple[list[dict[str, Any]], list[FuenteChatOut]]:
    """Recuperación semántica de PA: fragmentos del alcance y sus fuentes numeradas."""
    fragmentos, _ = _buscar(peticion, _vector(peticion.pregunta))
    return fragmentos, _numerar(fragmentos)


def _vector(pregunta: str) -> list[float]:
    try:
        return vectores.embed_text(pregunta)
    except Exception as exc:  # noqa: BLE001
        logger.error("No se pudo cargar el modelo de embeddings: %s", exc)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "No se pudo cargar el modelo de embeddings.") from exc


def registrar_consulta(
    pregunta: str,
    respuesta: str,
    modelo: str,
    chunks: int,
    inicio: float,
    plan: "Plan | None" = None,
    *,
    clave: str | None = None,
    salida: dict[str, Any] | None = None,
) -> int | None:
    """Guarda la consulta en rag_log y devuelve su id (mejor esfuerzo: nunca rompe el chat)."""
    try:
        sesion = fabrica_sesiones()
        try:
            fila = RagLog(
                pregunta=pregunta,
                respuesta=respuesta,
                modelo_usado=modelo,
                chunks_usados=chunks,
                latencia_ms=int((time.monotonic() - inicio) * 1000),
                clave_cache=clave,
                salida=salida,
            )
            evaluar = False
            if plan is not None:
                fila.decision_dominio = plan.decision
                fila.motivo = plan.motivo
                fila.score_max = plan.score_max
                fila.ruta = plan.ruta
                fila.instrumentos = list(plan.instrumentos)
                fila.contexto_usado = plan.contexto_usado() if chunks else []
                fila.plan = plan.plan_consulta
                fila.tiempos = plan.tiempos or None
                # Solo se evalúan las respuestas que redactó el LLM con contexto; los
                # rechazos, «no existe» y «sin información» no tienen qué medir.
                if not settings.RAG_METRICAS:
                    fila.metricas = evaluacion.omitida("Métricas desactivadas.")
                elif plan.literal and plan.decision == dominio.DENTRO:
                    # El juez de 3B le dio 0.25 a una copia literal del resultado (22 oct): la fidelidad no se le
                    # pregunta; la relevancia y la precisión sí se miden contra el resultado usado (28 oct, Fase 4).
                    fila.metricas = evaluacion.por_construccion()
                    evaluar = plan.calcular_metricas
                    if evaluar and settings.RAG_METRICAS_BAJO_DEMANDA:
                        fila.metricas, evaluar = evaluacion.pendiente(calculada=True), False
                elif not plan.calcular_metricas:
                    fila.metricas = evaluacion.omitida("Métricas no solicitadas en esta consulta (evaluación).")
                elif plan.fija is not None or not chunks:
                    fila.metricas = evaluacion.omitida("Respuesta sin redacción del modelo (rechazo, «no existe» o sin información).")
                elif settings.RAG_METRICAS_BAJO_DEMANDA:
                    # Se calculan cuando la persona abre la evaluación (POST /rag/consultas/{id}/metricas).
                    fila.metricas = evaluacion.pendiente(calculada=False)
                else:
                    evaluar = True
            sesion.add(fila)
            sesion.commit()
            if evaluar:  # después de entregar la respuesta, en segundo plano
                evaluacion.programar(fila.rag_log_id, fabrica_sesiones)
            # Juez Claude Fable 5.2 (11 nov): cada respuesta evaluable, en segundo plano y en la API de Anthropic
            # (no compite con Ollama por la GPU, así que no espera a que la persona lo pida).
            try:
                if plan is not None and juez_fable.aplica(fila):
                    juez_fable.solicitar(fila, sesion, fabrica_sesiones)
            except Exception as exc:  # noqa: BLE001 — el juez nunca rompe el chat
                logger.warning("No se pudo agendar el juez Fable de la consulta %s: %s", fila.rag_log_id, exc)
            return fila.rag_log_id
        finally:
            sesion.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo registrar la consulta RAG: %s", exc)
        return None


# ── Caché de respuestas ────────────────────────────────────────────────────────

_DECISIONES_REUTILIZABLES = {dominio.DENTRO, dominio.AYUDA}
# Súbelo cuando cambie cómo se calculan o redactan las respuestas (enrutador, consultas):
# las guardadas con la versión anterior dejan de reutilizarse. Las reglas del prompt
# (`prompt.SISTEMA`) ya entran en la huella.
_VERSION_RESPUESTAS = 42  # 42: búsqueda híbrida (significado + palabras, RRF); 41: «¿qué significa eso?» usa el seguimiento si la interpretación no retoma el plan; 40: búsqueda semántica con la pregunta original si la reescrita se parece menos; «¿qué significa eso?» interpreta el resultado; 39: pistas de la interpretación con los fragmentos cercanos y personas de la evidencia en los seguimientos; 38: seguimientos tras una aclaración y sin muletillas del prompt; 37: seguimientos de inferencia con la evidencia de la respuesta anterior; 36: umbral 0.65, similitud en cada tarjeta y hallazgos sin relación también dentro de una conversación; 35: umbral 0.70 sin relleno bajo el umbral y hallazgos de un tema sin relación → sin información; 34: regla 16 también pide variar «esto sugiere»; 33: regla 16 del prompt (interpretar con sus palabras, sin abrir siempre con «según el contexto»); 32: catálogo de la interpretación dentro del contexto; 31: citas [Fuente n] añadidas a las líneas que salen claramente de una fuente cuando el modelo no citó; 30: solo las fuentes que la respuesta usó (citadas o del resultado calculado); 29: cada fuente trae sus pasajes (trazabilidad: parte del documento, similitud y posición); 28: RAG primero (recuperación antes de interpretar, aclaraciones respondidas con lo recuperado, texto recuperado en toda respuesta calculada y en las reglas, filtros redactados); 27: RAG + cálculo (texto recuperado en las respuestas del plan), respuestas de una persona interpretadas por el modelo, varios patrones, patrones de entrevistas desde el texto y tema anterior en los seguimientos; 26: filtros inventados se quitan antes de validar, variables de sí/no nombradas, calificación de pruebas por la regla y redacción sin lenguaje de calificación (Fase 6, tercera corrida); 25: alcance con datos de contexto, aclaración en seguimientos, anclaje de verdadero/falso, comparaciones sobre el contexto numérico y ranking de preguntas con exclusiones , conteo de menciones en respuestas abiertas y calidad con las correcciones de la limpieza (Fase 6); 24: interpretación con plan JSON, ejecutor y redacción por intención; 4: ficha completa; 5: posturas de entrevistas; 6: conteo obligatorio en posturas y filtros; 8: estructura (listado sin LLM); 9: singular en el listado; 10: descripción y relación de instrumentos; 11: descripción sin LLM; 12: descripción y patrones redactados y verificados; 13: objetivos por separado en la relación; 14: afirmaciones verificadas antes de mostrar; 15: descripción con listado y métrica por construcción; 16: juez qwen2.5:3b; 17: sin verificación no se muestra la redacción; 18: patrones con el cálculo directo; 19: reactivos de pruebas en el orden de la hoja; 20: correcciones del banco (selección múltiple, conteo de filtros, rutas); 21: pruebas sin calificar; 22: más formas de pedir la descripción y el instrumento por número; 23: filtros con condición «sí» implícita y aviso de condición faltante


def clave_cache(peticion: ChatRequest, modelo: str) -> str | None:
    """Huella de la consulta, o None si la caché está apagada (o la petición no la quiere) o no hay BD."""
    if settings.RAG_CACHE_HORAS <= 0 or not peticion.usarCache:
        return None
    ids = sorted({i for i in (peticion.instrumentoIds or []) if i})
    try:
        sesion = fabrica_sesiones()
        try:
            consulta = sesion.query(VersionConocimiento.id_crudo, VersionConocimiento.version).filter(
                VersionConocimiento.estado == "vigente")
            if ids:
                consulta = consulta.filter(VersionConocimiento.id_crudo.in_([int(i) for i in ids if i.isdigit()]))
            versiones = sorted(f"{a}:{b}" for a, b in consulta.all())
        finally:
            sesion.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Caché no disponible: %s", exc)
        return None
    huella = {
        "pregunta": dominio.normalizar(peticion.pregunta).strip(" ?.!"),
        "ids": ids,
        "versiones": versiones,
        "contexto": peticion.contexto.model_dump() if peticion.contexto else None,
        # Con historial, «¿y de ellos…?» depende de lo anterior: la misma pregunta no es la misma consulta.
        "historial": [[m.rol, dominio.normalizar(m.texto)[:300]] for m in peticion.historial[-4:]],
        "modelo": modelo,
        "version": _VERSION_RESPUESTAS,
        "reglas": hashlib.sha256(prompt.SISTEMA.encode("utf-8")).hexdigest()[:16],
    }
    return hashlib.sha256(json.dumps(huella, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


@dataclass
class Guardada:
    """Respuesta reutilizada de la caché (ya registrada como consulta nueva)."""

    respuesta: str
    salida: dict[str, Any]
    decision: str | None
    ruta: str | None
    consulta_id: int | None


def buscar_en_cache(clave: str | None, pregunta: str, modelo: str, inicio: float) -> Guardada | None:
    """La respuesta guardada para esta huella (reciente y no degradada), registrada como consulta nueva."""
    if clave is None:
        return None
    try:
        sesion = fabrica_sesiones()
        try:
            limite = datetime.now() - timedelta(hours=settings.RAG_CACHE_HORAS)
            previa = (
                sesion.query(RagLog)
                .filter(RagLog.clave_cache == clave, RagLog.timestamp >= limite)
                .order_by(RagLog.rag_log_id.desc())
                .first()
            )
            salida = (previa.salida or {}) if previa is not None else {}
            if (previa is None or not previa.respuesta or salida.get("degradado")
                    or previa.decision_dominio not in _DECISIONES_REUTILIZABLES):
                return None
            origen = (previa.metricas or {}).get("origen") or previa.rag_log_id
            fila = RagLog(
                pregunta=pregunta, respuesta=previa.respuesta, modelo_usado=modelo, chunks_usados=previa.chunks_usados,
                latencia_ms=int((time.monotonic() - inicio) * 1000), decision_dominio=previa.decision_dominio,
                motivo=f"cache:{origen}", score_max=previa.score_max, ruta=previa.ruta, instrumentos=previa.instrumentos,
                contexto_usado=previa.contexto_usado, clave_cache=clave, salida=salida,
                # Las métricas son las de la respuesta original: se leen de ahí, sin volver a juzgar.
                metricas={"estado": "calculando", "origen": origen},
            )
            sesion.add(fila)
            sesion.commit()
            return Guardada(previa.respuesta, salida, previa.decision_dominio, previa.ruta, fila.rag_log_id)
        finally:
            sesion.close()
    except Exception as exc:  # noqa: BLE001 — la caché nunca rompe el chat
        logger.warning("Caché no disponible: %s", exc)
        return None


def _salida(fuentes: list[FuenteChatOut], referencias: list[ReferenciaChatOut], degradado: bool) -> dict[str, Any]:
    return {"fuentes": [f.model_dump() for f in fuentes], "referencias": [r.model_dump() for r in referencias],
            "degradado": degradado}


# ── Respuesta ──────────────────────────────────────────────────────────────────

# Caracteres que el streaming retiene al final para poder quitar la frase de
# «sin información» si el modelo la pega tras una respuesta que sí dio.
_RETENCION = len(prompt.SIN_INFORMACION) + 8


def quitar_sin_informacion_sobrante(texto: str) -> str:
    """Quita la frase de «sin información» cuando acompaña a una respuesta real.

    El modelo de 3B a veces la añade al final aunque sí respondió; si es lo único
    que dijo, se conserva (es la negativa correcta).
    """
    frase = prompt.SIN_INFORMACION
    sin_frase = texto.replace(frase, "").strip()
    if frase in texto and len(sin_frase) >= 20:
        return sin_frase
    # Variantes («No tengo información relacionada con los instrumentos consultados.») como
    # último párrafo de una respuesta que sí respondió.
    parrafos = [p for p in re.split(r"\n\s*\n", texto.strip()) if p.strip()]
    if len(parrafos) > 1 and es_negativa(parrafos[-1]) and len("\n\n".join(parrafos[:-1])) >= 20:
        return "\n\n".join(parrafos[:-1])
    return texto


# Inicios con los que el modelo dice que no puede responder (la frase exacta del
# prompt o sus variantes: «No tengo información relacionada con la pregunta…»).
_NEGATIVAS = (
    "no tengo informacion relacionada", "no tiene informacion relacionada", "no hay informacion",
    "lo siento, pero no tengo informacion", "no encontre informacion",
)


def es_negativa(texto: str) -> bool:
    """La respuesta es «no tengo información» (y no una respuesta real)."""
    normalizado = unicodedata.normalize("NFKD", texto.strip().lower()).encode("ascii", "ignore").decode()
    return len(normalizado) < 400 and normalizado.startswith(_NEGATIVAS)


@dataclass
class Plan:
    """Qué se va a responder y cómo (lo decide `planear`; se guarda en rag_log).

    - `fija`: respuesta sin LLM (rechazo, sin información o «no existe»).
    - si no, `texto_prompt` va a Ollama con las reglas de `prompt.SISTEMA`.
    """

    decision: str = dominio.DENTRO
    motivo: str | None = None
    ruta: str | None = None
    score_max: float | None = None
    fija: str | None = None
    texto_prompt: str = ""
    fragmentos: list[dict[str, Any]] = field(default_factory=list)
    fuentes: list[FuenteChatOut] = field(default_factory=list)
    referencias: list[dominio.Ancla] = field(default_factory=list)
    resultado: str | None = None
    respuesta_directa: str | None = None  # el resultado sin redactar (respaldo de la ruta estructurada)
    admite_negativa: bool = False  # en la ruta estructurada, «no hay información» puede ser correcto
    instrumentos: list[str] = field(default_factory=list)
    # Lo que se mostró es el resultado calculado tal cual (listado sin LLM o respaldo de una redacción
    # descartada): su fidelidad es 1 por construcción y no se le pide al juez que la califique.
    literal: bool = False
    calcular_metricas: bool = True  # la evaluación las apaga en las paráfrasis (ChatRequest.calcularMetricas)
    # Rediseño en cuatro etapas (28 oct): plan de la interpretación, ms por etapa, tablas que se anexan tal cual
    # debajo de la redacción y cifras que la redacción debe conservar (None = verificación anterior).
    plan_consulta: dict[str, Any] | None = None
    tiempos: dict[str, int] = field(default_factory=dict)
    anexo: str = ""
    cifras_obligatorias: set[float] | None = None
    # 4 nov: en conteos, comparaciones, resúmenes y rankings la redacción solo puede usar cifras del resultado; en
    # las demás también las del texto recuperado del RAG (lo que dijo una persona, «tres sesiones», «15 horas»).
    cifras_solo_resultado: bool = False
    # Mayor similitud de cada instrumento con la pregunta en la recuperación (para mostrarla en su tarjeta).
    similitudes: dict[str, float] = field(default_factory=dict)

    @property
    def usados(self) -> int:
        return len(self.fragmentos) + (1 if self.resultado else 0) + len(self.referencias)

    def contexto_usado(self) -> list[dict[str, Any]]:
        """Lo que vio el LLM (para evaluar fidelidad y precisión del contexto después)."""
        salida: list[dict[str, Any]] = []
        if self.resultado and self.plan_consulta is not None:
            # Un bloque por instrumento («[Fuente n] …»): lo que de verdad usó la respuesta.
            salida += [{"tipo": "resultado", "texto": b.strip()} for b in re.split(r"\n\n(?=\[Fuente \d+\])", self.resultado)
                       if b.strip()]
        elif self.resultado:
            salida.append({"tipo": "resultado", "texto": self.resultado})
        salida += [{"tipo": r.tipo, "titulo": r.titulo, "texto": r.texto} for r in self.referencias]
        salida += [{"tipo": "fragmento", "instrumentoId": f["instrumentoId"], "seccion": f["seccion"],
                    "etiqueta": _etiqueta_fragmento(f), "score": f.get("score"), "texto": f["fragmento"],
                    # Búsqueda híbrida (11 nov): para «Ver métricas» (services/metricas_respuesta.py).
                    "coincidencia": f.get("coincidencia"), "palabras": f.get("palabras"), "rangos": f.get("rangos")}
                   for f in self.fragmentos]
        return salida

    def referencias_out(self) -> list[ReferenciaChatOut]:
        return [ReferenciaChatOut(tipo=r.tipo, titulo=r.titulo, texto=r.texto, url=r.url) for r in self.referencias]


_UMBRAL_ANCLA = 0.6  # similitud con una entrada del glosario o de la ayuda para usarla


def _tipos_alcance(ids: list[str]) -> set[str]:
    """Tipos de instrumento del alcance (para elegir los ejemplos del mensaje de rechazo)."""
    try:
        sesion = fabrica_sesiones()
        try:
            return {i.tipo for i in enrutador.cargar_documentos(sesion, ids)}
        finally:
            sesion.close()
    except Exception:  # noqa: BLE001
        return set()


async def planear(peticion: ChatRequest) -> Plan:
    """Aplica el dominio acotado y el enrutador; deja listo el prompt o la respuesta fija.

    El plan de la interpretación y sus tiempos se guardan aunque responda otra ruta (reglas, ayuda, semántica):
    sin esto, «¿de qué trata el instrumento…?» quedaba en rag_log sin plan ni tiempos (28 oct, Fase 4).
    """
    estado: dict[str, Any] = {}
    plan = await _planear(peticion, estado)
    if plan.plan_consulta is None and estado.get("registro") is not None:
        plan.plan_consulta = estado["registro"]
    if not plan.tiempos and estado.get("tiempos"):
        plan.tiempos = dict(estado["tiempos"])
    if "similitudes" in estado:  # un seguimiento no busca: conserva las de la respuesta anterior
        plan.similitudes = estado["similitudes"]
    return plan


async def _planear(peticion: ChatRequest, estado: dict[str, Any]) -> Plan:
    pregunta = peticion.pregunta
    ids = [i for i in (peticion.instrumentoIds or []) if i]
    contexto = peticion.contexto.model_dump() if peticion.contexto else None

    # Capa 1a: reglas de intención (sin modelo).
    if regla := dominio.reglas(pregunta):
        decision, motivo = regla
        return Plan(decision=decision, motivo=motivo, fija=dominio.mensaje(decision, _tipos_alcance(ids)), instrumentos=ids)

    # Ayuda de la plataforma: solo la base curada (no consulta Chroma ni exige alcance).
    if dominio.es_ayuda(pregunta):
        return _plan_ayuda(pregunta, ids, contexto)

    # Hilo de la conversación: «¿por qué crees que pasa eso?» razona sobre la respuesta anterior con su misma
    # evidencia, sin pasar por la interpretación (que la calculaba como pregunta nueva sobre toda la colección).
    # «¿Qué significa eso?» tras un cálculo se difiere: primero se intenta retomar el plan anterior con cifras
    # verificadas (_retomar_anterior); si la interpretación no lo retoma, se usa este seguimiento.
    diferido: Plan | None = None
    if peticion.historial and (plan := _plan_cuentas(pregunta, peticion, ids)) is not None:
        return plan
    if peticion.historial and (plan := _plan_seguimiento(pregunta, peticion, ids, contexto)) is not None:
        if not plan.motivo.endswith(_DIFERIDO):
            return plan
        diferido, plan.motivo = plan, plan.motivo.removesuffix(_DIFERIDO)

    # Etapas 1 y 2: interpretación (plan JSON) y ejecución determinista. Sin plan (Ollama caído o plan inválido
    # dos veces) se sigue con las reglas anteriores.
    registro: dict[str, Any] | None = None
    tiempos: dict[str, int] = {}
    consulta_semantica: str | None = None  # la interpretación decidió buscar en el RAG
    conversacion = _conversacion(peticion.historial)
    # RAG primero: la búsqueda en Chroma va antes que la interpretación y que cualquier cálculo.
    inicio_rag = time.perf_counter()
    recuperados, score_rag, estado["similitudes"] = _recuperar_primero(peticion, estado)
    cercanos = estado.get("pistas") or recuperados
    ms_rag = round((time.perf_counter() - inicio_rag) * 1000)
    tiempos["recuperacion"] = ms_rag
    estado["tiempos"] = tiempos
    if settings.RAG_INTERPRETACION_LLM and peticion.usarInterpretacion:
        try:
            sesion = fabrica_sesiones()
            tema, plan_anterior = _anterior(peticion.historial)
            try:
                preparada = await consulta_planificada.preparar(
                    pregunta, [(m.rol, m.texto) for m in peticion.historial], ids, sesion, tema=tema,
                    pistas=_pistas(cercanos),
                    prioridad=list(dict.fromkeys(str(f["instrumentoId"]) for f in cercanos)))
            finally:
                sesion.close()
        except Exception as exc:  # noqa: BLE001 — sin BD o storage: siguen las reglas
            logger.warning("Interpretación no disponible: %s", exc)
            preparada = None
        if preparada is None and diferido is not None:
            return diferido
        if preparada is not None:
            _retomar_anterior(preparada, pregunta, plan_anterior)
            if diferido is not None and not any(c.startswith("aclaración → plan de la respuesta anterior")
                                                for c in preparada.interp.correcciones):
                diferido.plan_consulta = preparada.registro()
                diferido.tiempos = {"recuperacion": ms_rag, "interpretacion": preparada.interp.ms}
                return diferido
            inicio_apoyo = time.perf_counter()
            apoyo = _apoyo_rag(peticion, preparada)
            p = preparada.plan
            if not apoyo and p is not None and p.intencion in ESTRUCTURADAS and preparada.ejecuciones:
                apoyo = _apoyo_de_recuperados(recuperados, preparada)
            _completar_con_recuperados(preparada, apoyo)
            tiempos = {"recuperacion": ms_rag + round((time.perf_counter() - inicio_apoyo) * 1000),
                       "interpretacion": preparada.interp.ms, "ejecucion": preparada.ms_ejecucion}
            if _rag_responde_aclaracion(preparada, pregunta, bool(peticion.historial), score_rag):
                # Antes de preguntarle al usuario se intenta responder con lo recuperado (5 nov: «¿cuántos estudian
                # ingeniería?» o «¿a qué carrera está aplicada?» recibían una aclaración sin buscar en el RAG).
                preparada.interp.correcciones.append("aclaración → respuesta con lo recuperado del RAG")
                consulta_semantica = _consulta_apoyo(pregunta, peticion.historial)
            registro = preparada.registro()
            estado.update(registro=registro, tiempos=tiempos)
            if consulta_semantica is None:
                decidido = _plan_desde_preparada(preparada, pregunta, ids, contexto,
                                                 seguimiento=bool(peticion.historial), apoyo=apoyo,
                                                 conversacion=conversacion, score_rag=score_rag)
                if decidido is not None:
                    decidido.plan_consulta, decidido.tiempos = registro, tiempos
                    return decidido
                if p is not None and p.intencion in ("semantica_abierta", "metodologia", "fuera_de_dominio"):
                    consulta_semantica = p.consulta_semantica or pregunta

    vector = _vector(consulta_semantica or pregunta)
    # Ruta estructurada (cálculo exacto sobre el documento vigente).
    resultado = None
    try:
        sesion = fabrica_sesiones()
        try:
            resultado = enrutador.resolver(pregunta, sesion, ids)
            if consulta_semantica is not None:
                # La interpretación pidió la ruta semántica, pero las reglas deterministas (descripción, estructura,
                # patrones…) responden mejor lo que saben calcular: «¿de qué trata el instrumento y qué secciones
                # tiene?» se iba a la búsqueda y perdía la estructura (28 oct, Fase 4). Las que piden condición al
                # modelo (filtros) no se repiten: la interpretación ya las habría resuelto.
                if resultado is not None and resultado.consulta == "filtro":
                    resultado = None
                raise _SinReglas
            if resultado is None:  # filtro que las reglas no entendieron: Ollama propone la condición
                resultado = await enrutador.filtro_llm(pregunta, sesion, ids)
            elif faltan := enrutador.filtro_incompleto(resultado):
                # Las reglas armaron solo una parte de la condición (28 oct: «carga mínima y alguna
                # certificación» se respondía con la carga mínima). Ollama propone la condición completa,
                # validada contra el catálogo; si no puede, se responde con lo que hay y se dice qué faltó.
                completo = await enrutador.filtro_llm(pregunta, sesion, ids)
                if completo is not None:  # condición propuesta por Ollama y validada contra el catálogo
                    resultado = completo
                else:
                    resultado.aclaracion = (
                        f"No se pudo convertir en condición lo que la pregunta dice sobre «{', '.join(faltan)}»: "
                        "el conteo de abajo aplica solo las condiciones que se muestran."
                    )
        finally:
            sesion.close()
    except _SinReglas:
        pass
    except Exception as exc:  # noqa: BLE001 — sin BD o storage: sigue la ruta semántica
        logger.warning("Enrutador no disponible: %s", exc)

    fragmentos, score_chunks = _buscar(peticion, vector)
    if consulta_semantica and consulta_semantica != pregunta:
        # La interpretación reescribe la búsqueda («comentarios sobre el apoyo de sus compañeros», 0.55) y puede
        # quedar bajo el umbral aunque la pregunta original sí lo pase (0.74): se usa la que más se parezca (10 nov).
        otros, score_otros = _buscar(peticion, _vector(pregunta))
        if score_otros > score_chunks:
            fragmentos, score_chunks = otros, score_otros
    if resultado is not None:
        # RAG primero (5 nov): todo resultado de las reglas lleva el texto recuperado de sus instrumentos. Antes solo
        # los KPIs lo llevaban porque, con los fragmentos al lado, el modelo llegó a tomar el % de toda la muestra en
        # lugar del % del grupo calculado (auditoría de la Fase 3): fuera de los KPIs los fragmentos llegan sin cifras
        # y las cifras salen solo del cálculo.
        propios = {i.id_crudo for i in resultado.instrumentos}
        fragmentos = ([f for f in fragmentos if f["instrumentoId"] in propios][:3]
                      or [f for f in recuperados if f["instrumentoId"] in propios][:3]
                      or (_fichas(resultado.instrumentos) if resultado.consulta in _SOBRE_EL_INSTRUMENTO else []))
        if resultado.consulta not in _CONSULTAS_MIXTAS:
            fragmentos = [{**f, "fragmento": _sin_cifras(f["fragmento"])} for f in fragmentos]
    # El glosario solo entra en preguntas de definición («qué es», «qué significa»…) que
    # no tienen ya un resultado calculado: en las demás no es evidencia sobre los datos.
    glosario = (
        [a for a, s in dominio.anclas_cercanas(pregunta, vector, "glosario") if s >= _UMBRAL_ANCLA]
        if resultado is None and dominio.es_definicion(pregunta) else []
    )
    score_anclas = max((s for _, s in dominio.anclas_cercanas(pregunta, vector, k=1)), default=0.0)
    score = max(score_chunks, score_anclas, dominio.score_kpis(vector), 1.0 if resultado else 0.0)

    plan = Plan(score_max=round(score, 4), fragmentos=fragmentos, referencias=glosario,
                instrumentos=ids or sorted({f["instrumentoId"] for f in fragmentos}))
    if resultado is not None:
        plan.ruta = "mixta" if fragmentos else "estructurada"
        plan.fuentes = _numerar(fragmentos, resultado.instrumentos, resultado.consulta in _CONSULTAS_MIXTAS)
        numeros = {f.instrumentoId: f.numero for f in plan.fuentes}
        plan.instrumentos = ids or [i.id_crudo for i in resultado.instrumentos]
        if not resultado.encontrado:  # «no existe»: se dice tal cual, sin LLM
            plan.motivo = f"estructurada:{resultado.consulta}:no_existe"
            plan.fija = resultado.respuesta_directa(numeros)
            plan.literal = True
            return plan
        plan.motivo = f"estructurada:{resultado.consulta}"
        if resultado.consulta in _CONSULTAS_SIN_LLM:
            listado = resultado.listado(numeros)
            if not fragmentos:  # sin texto recuperado: el listado de hechos tal cual
                plan.fija, plan.literal = listado, True
                return plan
            # Con texto recuperado el modelo lo explica con el listado como RESULTADO CALCULADO; la verificación del
            # plan (cifras, IDs, citas, reintento) cae al listado si cambia algo.
            plan.resultado = plan.respuesta_directa = listado
            plan.cifras_obligatorias, plan.cifras_solo_resultado = set(), True
            pregunta_regla = f"{pregunta}\n({resultado.aclaracion})" if resultado.aclaracion else pregunta
            plan.texto_prompt = prompt.construir(pregunta_regla, plan.fragmentos, contexto, resultado=listado,
                                                 formato=_FORMATO_REGLA.get(resultado.consulta, ""),
                                                 conversacion=conversacion)
            plan.plan_consulta, plan.tiempos = registro, tiempos
            return plan
        if resultado.consulta in _CONSULTAS_MIXTAS:  # la definición del KPI, respaldada por fuentes verificadas
            plan.referencias = plan.referencias + _fuentes_kpi(pregunta, resultado)
        plan.resultado = resultado.texto(numeros)
        plan.respuesta_directa = resultado.respuesta_directa(numeros)
        plan.admite_negativa = resultado.admite_negativa
    else:
        plan.ruta = "semantica"
        plan.fuentes = _numerar(fragmentos, consulta_kpi=bool(re.search(r"\bkpis?\b|indicador", dominio.normalizar(pregunta))))
        if not fragmentos and not glosario:
            if score < settings.RAG_FUERA_MAX:  # nada del acervo, del glosario ni de los KPIs se le parece
                plan.decision, plan.motivo = dominio.FUERA, f"similitud máxima {score:.2f} < {settings.RAG_FUERA_MAX}"
                plan.fija = dominio.mensaje(dominio.FUERA, _tipos_alcance(ids))
            else:
                plan.decision, plan.motivo, plan.fija = dominio.SIN_INFORMACION, "sin fragmentos sobre el umbral", MENSAJE_SIN_CONTEXTO
            return plan
        # Capa 1c: zona gris (similitud ambigua y ninguna regla decidió).
        # Una pregunta sobre los instrumentos elegidos no pasa por el clasificador: rechazó «¿qué patrón…
        # de los datos de estos instrumentos?» con el motivo «análisis de tendencias…», que es del dominio.
        if (not glosario and consulta_semantica is None and dominio.en_zona_gris(score)
                and not enrutador.refiere_al_alcance(pregunta)):
            try:
                veredicto = await dominio.clasificar_llm(pregunta)
            except Exception as exc:  # noqa: BLE001 — el clasificador nunca bloquea el chat
                logger.warning("Clasificador de dominio no disponible: %s", exc)
                veredicto = None
            if veredicto is not None and not veredicto[0]:
                plan.decision, plan.motivo = dominio.FUERA, f"clasificador: {veredicto[1]}"
                plan.fija = dominio.mensaje(dominio.FUERA, _tipos_alcance(ids))
                plan.fuentes, plan.fragmentos = [], []
                return plan
            if veredicto is not None:
                plan.motivo = f"clasificador: {veredicto[1]}"
    pregunta_llm = f"{pregunta}\n({resultado.aclaracion})" if resultado is not None and resultado.aclaracion else pregunta
    plan.texto_prompt = prompt.construir(pregunta_llm, plan.fragmentos, contexto, resultado=plan.resultado,
                                         referencias=plan.referencias, conversacion=conversacion)
    plan.plan_consulta, plan.tiempos = registro, tiempos
    return plan


class _SinReglas(Exception):
    """La interpretación pidió la ruta semántica: no se consultan las reglas del enrutador."""


def _plan_ayuda(pregunta: str, ids: list[str], contexto: dict[str, Any] | None) -> Plan:
    vector = _vector(pregunta)
    refs = [a for a, s in dominio.anclas_cercanas(pregunta, vector, "ayuda", k=3) if s >= 0.35] or \
           [a for a, _ in dominio.anclas_cercanas(pregunta, vector, "ayuda", k=2)]
    return Plan(decision=dominio.AYUDA, ruta="ayuda", referencias=refs, instrumentos=ids,
                texto_prompt=prompt.construir(pregunta, [], contexto, referencias=refs))


def _plan_desde_preparada(preparada: "consulta_planificada.Preparada", pregunta: str, ids: list[str],
                          contexto: dict[str, Any] | None, seguimiento: bool = False,
                          apoyo: list[dict[str, Any]] | None = None, conversacion: str = "",
                          score_rag: float | None = None) -> Plan | None:
    """Plan del chat a partir del plan de la interpretación; None = sigue la ruta semántica o las reglas.

    `seguimiento`: la conversación ya tiene turnos anteriores. `apoyo`: fragmentos del RAG que acompañan al
    resultado (`_apoyo_rag`). `conversacion`: los últimos mensajes sin tablas, para la redacción."""
    p = preparada.plan
    if p is None:
        return None
    if preparada.instrumentos and all(i.tipo == "prueba_estandarizada" for i in preparada.instrumentos) \
            and (regla := enrutador.detectar(pregunta)) is not None and regla.tipo == "sin_calificar":
        # «¿Cuántos aprobaron la prueba?», «¿quién sacó la calificación más alta?» o «¿qué pregunta es más difícil?»:
        # sin clave no se sabe, y el plan inventaba un filtro («A» en r01), la descartaba como ajena o la respondía
        # con un ranking de no respuesta (Fase 6, consultas 1577, 1578, 1595, 1600, 1618). La regla lo aclara.
        return None
    if p.intencion == "aclaracion" and not seguimiento \
            and not consulta_planificada.del_alcance(pregunta, preparada.catalogos) \
            and not consulta_planificada.REFERENCIA.search(dominio.normalizar(pregunta)):
        # Ni habla de los instrumentos ni se refiere a algo anterior («eso»): es ajena, no ambigua («¿quién ganó el
        # mundial de 2010?» se respondía con una pregunta de aclaración, regresión C16). En un seguimiento la
        # aclaración se muestra: «¿Por qué nadie la contestó?» o «¿Le parecieron suficientes?» se refieren a lo
        # anterior sin repetir sus palabras y recibían el mensaje de fuera de dominio (Fase 6, consultas 1519, 1537).
        return Plan(decision=dominio.FUERA, motivo="plan:aclaracion_ajena",
                    fija=dominio.mensaje(dominio.FUERA, {i.tipo for i in preparada.instrumentos}), instrumentos=ids)
    if p.intencion == "aclaracion":
        return Plan(motivo="plan:aclaracion", ruta="aclaracion", fija=p.aclaracion, instrumentos=ids, score_max=1.0)
    if p.intencion == "fuera_de_dominio" and not consulta_planificada.del_alcance(pregunta, preparada.catalogos):
        return Plan(decision=dominio.FUERA, motivo="plan:fuera_de_dominio",
                    fija=dominio.mensaje(dominio.FUERA, {i.tipo for i in preparada.instrumentos}), instrumentos=ids)
    if p.intencion == "uso_plataforma" and (regla := enrutador.detectar(pregunta)) is not None and regla.tipo == "calidad":
        # «¿Qué se corrigió en la limpieza?» pregunta por ESTE instrumento, no por cómo usar la plataforma: la regla
        # de calidad responde con el reporte de limpieza (Fase 6, consulta 1495).
        return None
    if p.intencion == "uso_plataforma":
        plan = _plan_ayuda(pregunta, ids, contexto)
        plan.motivo = "plan:uso_plataforma"
        return plan
    if p.intencion not in ESTRUCTURADAS or not preparada.ejecuciones:
        return None
    if _hallazgo_sin_relacion(p.intencion, pregunta, seguimiento, score_rag):
        return Plan(decision=dominio.SIN_INFORMACION, motivo=f"plan:hallazgo con similitud {score_rag:.2f} < "
                    f"{settings.RAG_MIN_SCORE}", fija=MENSAJE_SIN_CONTEXTO, instrumentos=ids, score_max=score_rag or 0.0)
    ejecuciones = preparada.ejecuciones
    apoyo = apoyo or []
    plan = Plan(ruta="estructurada", motivo=f"plan:{p.intencion}", score_max=1.0,
                instrumentos=ids or [e.instrumento.id_crudo for e in ejecuciones])
    plan.fuentes = consulta_planificada.fuentes(ejecuciones)
    plan.resultado = consulta_planificada.resultado_completo(ejecuciones)
    plan.respuesta_directa = consulta_planificada.directa(ejecuciones)
    plan.anexo = consulta_planificada.anexo(ejecuciones)
    plan.cifras_obligatorias = consulta_planificada.cifras_clave(ejecuciones)
    plan.admite_negativa = all(e.vacio for e in ejecuciones)
    formato = consulta_planificada.FORMATO.get(p.intencion, "")
    if any(c.startswith("aclaración → plan de la respuesta anterior") for c in preparada.interp.correcciones):
        # «¿Qué significa eso?» tras un resultado: con el formato del cálculo el modelo lo repetía tal cual (10 nov).
        formato = (f"{formato} La pregunta pide interpretar el resultado anterior: no lo repitas; explica con tus "
                   "palabras qué significa y qué podría implicar, usando sus cifras tal cual.").strip()
    texto_entrevista = p.intencion == "hallazgo" and all(e.instrumento.tipo == "entrevista" for e in ejecuciones)
    if texto_entrevista and apoyo and plan.admite_negativa:
        # Entrevistas: con uno o pocos participantes no hay conteos de posturas («No hay resúmenes calculados», 4 nov,
        # consulta 1681); los patrones salen del texto recuperado y el modelo los agrupa en temas con citas.
        formato = consulta_planificada.FORMATO["hallazgo_texto"]
        plan.resultado = "\n\n".join(f"[Fuente {n}] {e.instrumento.titulo} ({e.instrumento.tipo_ui})\n- Patrones a partir "
                                     f"de {len([f for f in apoyo if f['numero'] == n])} intercambios recuperados."
                                     for n, e in enumerate(ejecuciones, start=1))
        plan.respuesta_directa = "\n".join(f"- {f['fragmento']} [Fuente {f['numero']}]" for f in apoyo[:3])
        plan.admite_negativa = False
    if plan.admite_negativa:  # sin resultados: se dice tal cual, sin redacción («nunca rellena»)
        plan.motivo = f"plan:{p.intencion}:vacio"
        plan.fija, plan.literal = plan.respuesta_directa, True
        return plan
    if p.intencion in consulta_planificada.SIN_REDACCION:  # tabla de respondentes: presentación fija + tabla
        plan.motivo = f"plan:{p.intencion}:tabla"
        plan.fija = f"{plan.respuesta_directa}\n\n{plan.anexo}" if plan.anexo else plan.respuesta_directa
        plan.literal = True
        return plan
    # Las cifras salen solo del cálculo salvo en lo que dijo una persona o en los patrones de una entrevista, donde el
    # texto es la evidencia. Si no, los fragmentos llegan sin sus cifras: con ellas el modelo citó los porcentajes de
    # otras preguntas en vez de los calculados (4 nov, consultas 1696, 1698 y 1699).
    plan.cifras_solo_resultado = p.intencion not in _INTENCIONES_TEXTO or (p.intencion == "hallazgo" and not texto_entrevista)
    if plan.cifras_solo_resultado:
        apoyo = [{**f, "fragmento": _sin_cifras(f["fragmento"])} for f in apoyo]
    if apoyo:  # el RAG complementa el cálculo: se ve en la ruta, en la tarjeta de fuente y en el contexto usado
        plan.ruta, plan.fragmentos = "mixta", apoyo
        for fuente in plan.fuentes:
            propios = [f for f in apoyo if f["numero"] == fuente.numero]
            if propios:
                recuperado = ", ".join(dict.fromkeys(_etiqueta_fragmento(f) for f in propios))
                fuente.fragmento = f"{fuente.fragmento} · Texto recuperado del RAG: {recuperado}"[:600]
    plan.texto_prompt = prompt.construir(
        pregunta, apoyo, contexto, resultado=consulta_planificada.resultado_para_prompt(ejecuciones, p.intencion),
        formato=formato, conversacion=conversacion)
    return plan


# Intenciones donde el texto recuperado es evidencia (lo que dijo una persona, patrones de una entrevista): la
# redacción puede usar sus cifras («tres sesiones», «15 horas»). En las demás solo las del resultado (Fase 3: tomó el
# % de toda la muestra de un fragmento en lugar del % del grupo calculado).
_INTENCIONES_TEXTO = {"datos_respondente", "hallazgo"}

# «Dame un dato interesante», «¿qué patrones hay?», «¿qué destaca de esta encuesta?»: piden los hallazgos del
# instrumento en sí, no un tema; se responden con el cálculo aunque ningún fragmento se parezca a la pregunta.
_PIDE_HALLAZGOS = re.compile(r"\b(dato|datos) (interesante|curioso|relevante)|patron|hallazg|tendencia|destac|"
                             r"llama la atencion|sobresal|resum")


_DIFERIDO = " (diferido)"


def _plan_cuentas(pregunta: str, peticion: ChatRequest, ids: list[str]) -> Plan | None:
    """«¿Cómo inferiste que no hay…?» tras un «sin información»: la traza de esa respuesta, sin LLM (qué se buscó, la
    parte más parecida y su similitud frente al umbral), con esa parte como fuente para abrirla."""
    if not seguimiento.pide_cuentas(pregunta):
        return None
    anterior = seguimiento.leer_sin_respuesta(peticion.historial, fabrica_sesiones)
    if anterior is None:
        return None
    busqueda: dict[str, Any] = {}
    _recuperar_primero(ChatRequest(pregunta=anterior.pregunta, instrumentoIds=anterior.instrumentos or ids), busqueda)
    cercano = next(iter(busqueda.get("pistas") or []), None)
    plan = Plan(motivo=f"explicación de la consulta {anterior.consulta_id}", ruta="semantica",
                instrumentos=anterior.instrumentos or ids, score_max=cercano["score"] if cercano else None)
    if cercano is not None:
        plan.fragmentos = [cercano]
        plan.fuentes = _numerar(plan.fragmentos)
        cercano = {**cercano, "etiqueta": trazabilidad.etiqueta(cercano.get("seccion") or "", cercano.get("preguntaId"),
                                                                cercano.get("respondenteId")).lower()}
    plan.fija = seguimiento.explicar_sin_respuesta(anterior, cercano, settings.RAG_MIN_SCORE)
    return plan


def _plan_seguimiento(pregunta: str, peticion: ChatRequest, ids: list[str],
                      contexto: dict[str, Any] | None) -> Plan | None:
    """Seguimiento de inferencia sobre la respuesta anterior (`services/seguimiento.py`); None = no lo es."""
    if not seguimiento.es_inferencia(pregunta):
        return None
    anterior = seguimiento.leer_anterior(peticion.historial, fabrica_sesiones)
    if anterior is None:
        return None
    try:
        fuentes = [FuenteChatOut(**f) for f in anterior.fuentes]
    except ValueError:
        return None
    fragmentos = anterior.fragmentos()
    if not fragmentos:
        return None
    scores = [f["score"] for f in fragmentos if f.get("score") is not None]
    diferir = settings.RAG_INTERPRETACION_LLM and seguimiento.lo_retoma_el_plan(pregunta, anterior, ESTRUCTURADAS)
    plan = Plan(ruta="semantica",
                motivo=f"seguimiento de la consulta {anterior.consulta_id}" + (_DIFERIDO if diferir else ""),
                score_max=max(scores) if scores else None,
                instrumentos=ids or sorted({f.instrumentoId for f in fuentes}), fragmentos=fragmentos, fuentes=fuentes)
    plan.similitudes = {str(f.instrumentoId): f.similitud for f in fuentes if f.similitud is not None}
    plan.texto_prompt = prompt.construir(pregunta, fragmentos, contexto, formato=seguimiento.formato(fragmentos),
                                         conversacion=seguimiento.conversacion(anterior, interpretacion.sin_tablas))
    return plan


def _hallazgo_sin_relacion(intencion: str, pregunta: str, seguimiento: bool, score_rag: float | None) -> bool:
    """¿Un «hallazgo» que responde a un TEMA que nada del alcance trata? El plan elegía hallazgos del instrumento
    aunque no hablara del tema (10 nov: «¿qué estrategias usan los estudiantes para mejorar su rendimiento?» con un
    instrumento sobre modalidad de estudio, similitud 0.65); sin un fragmento sobre RAG_MIN_SCORE, no hay información."""
    if intencion != "hallazgo" or score_rag is None or score_rag >= settings.RAG_MIN_SCORE:
        return False
    texto = dominio.normalizar(pregunta)
    # En una conversación solo cuenta como seguimiento lo que se refiere a lo anterior («¿y eso?», «¿por qué?»): una
    # pregunta nueva sobre otro tema no hereda nada (10 nov, consulta 130).
    if seguimiento and (consulta_planificada.REFERENCIA.search(texto) or len(texto.split()) <= 4):
        return False
    return not (_PIDE_HALLAZGOS.search(texto) or enrutador.refiere_al_alcance(pregunta))
_CON_CIFRA = re.compile(r"\d")


def _sin_cifras(fragmento: str) -> str:
    """El fragmento sin las líneas con cifras (distribución, respuestas válidas…); la primera, que dice qué pregunta
    o parte es, se conserva."""
    primera, *resto = fragmento.splitlines() or [""]
    return "\n".join([primera, *(l for l in resto if not _CON_CIFRA.search(l))])


def _etiqueta_fragmento(f: dict[str, Any]) -> str:
    """«E01 en p04», «p03», «KPI»: qué parte del instrumento se recuperó."""
    pregunta = f["preguntaId"].rsplit("-", 1)[-1] if f.get("preguntaId") else ""
    persona = f["respondenteId"].rsplit("-", 1)[-1] if f.get("respondenteId") else ""
    if persona and pregunta:
        return f"{persona} en {pregunta}"
    return persona or pregunta or str(f.get("seccion") or "fragmento")


def _fuentes_kpi(pregunta: str, resultado: enrutador.Resultado) -> list[dominio.Ancla]:
    """Fuentes de referencia (tabla kpi_fuente) de los KPIs que menciona la consulta."""
    texto = dominio.normalizar(pregunta)
    nombres = {k["nombre"] for ins in resultado.instrumentos if (k := enrutador._kpi_mencionado(ins.doc, texto))}
    if not nombres:
        return []
    try:
        sesion = fabrica_sesiones()
        try:
            filas = (sesion.query(KPIFuente).join(KPI, KPI.kpi_id == KPIFuente.kpi_id)
                     .filter(KPI.nombre.in_(nombres)).order_by(KPIFuente.kpi_fuente_id).limit(4).all())
        finally:
            sesion.close()
    except Exception as exc:  # noqa: BLE001 — sin la tabla (BD sin migrar) se responde sin fuentes
        logger.warning("Fuentes de KPI no disponibles: %s", exc)
        return []
    return [dominio.Ancla("fuente_kpi", f.organismo, f"{f.titulo}. {f.nota or ''}".strip(), url=f.url) for f in filas]


_CITA_CURADA = re.compile(r"\s*\[(Glosario|Ayuda|Fuente KPI):\s*([^\]]+)\]")


def quitar_citas_inventadas(texto: str, referencias: list[dominio.Ancla]) -> str:
    """Quita las citas [Glosario: …]/[Ayuda: …] que no corresponden a una referencia dada.

    El modelo imita el formato de cita de las reglas aunque no haya recibido glosario
    ni ayuda (p. ej. «[Glosario: Tamaño Promedio de Clase]»): una cita que no existe
    hace parecer verificable algo que no lo es.
    """
    validas = {(r.tipo, dominio.normalizar(r.titulo)) for r in referencias}

    def _filtrar(m: re.Match) -> str:
        tipo = {"Glosario": "glosario", "Ayuda": "ayuda", "Fuente KPI": "fuente_kpi"}[m.group(1)]
        return m.group(0) if (tipo, dominio.normalizar(m.group(2))) in validas else ""

    return _CITA_CURADA.sub(_filtrar, texto)


# Corchetes que no son una cita válida ([Fuente n], [Glosario: …], [Ayuda: …], [Fuente KPI: …]):
# el modelo copia el ejemplo de la regla 12 como si fuera cita («[R017 en p04]»).
_CORCHETE_NO_CITA = re.compile(r"\s*\[(?!\s*(?:Fuente|Glosario|Ayuda)\b)[^\]\n]{1,40}\]")


def _pulir(texto: str, plan: Plan | None = None) -> str:
    """Capa 3: frase de «sin información» sobrante, citas inventadas y datos personales."""
    texto = quitar_sin_informacion_sobrante(texto)
    if plan is not None:
        texto = quitar_citas_inventadas(texto, plan.referencias)
        texto = _CORCHETE_NO_CITA.sub("", texto)
    return dominio.tachar_datos_personales(texto)


_CONSULTAS_MIXTAS = {"kpi", "kpi_preguntas"}
# Estructura del instrumento: el modelo de 3B llegó a decir «sí, ambos tienen secciones» con un
# resultado que decía lo contrario para la entrevista; se responde con el listado calculado.
# Descripción y relación de instrumentos: también van con el listado calculado. Redactadas por el
# modelo tardaban de 15 a 42 s (redacción + verificación de afirmaciones) y en 3 de 4 casos la
# verificación las descartó (prueba en vivo del 22 oct); la métrica queda «fiel por construcción».
# Patrones: igual. Redactados por el modelo y verificados con el juez antes de mostrarse tardaban de
# 35 a 57 s; en 3 de 4 pruebas (22–23 oct, con llama3.2:3b y con qwen2.5:3b como juez) la redacción se
# descartó, y la cuarta pasó solo porque el juez falló (rag_log 737, «55 % de acuerdo» por «55 % eligió Sí»).
_CONSULTAS_SIN_LLM = {"estructura", "descripcion", "patrones", "sin_calificar"}
# Desde el 5 nov esas consultas se redactan cuando hay texto recuperado (RAG primero), con la verificación del plan y
# el listado como respaldo.
_FORMATO_REGLA = {
    "descripcion": "Describe el instrumento en un párrafo breve: de qué trata, a quién se aplicó y qué temas cubre, "
                   "con lo que dicen el RESULTADO CALCULADO y el TEXTO RECUPERADO. No inventes temas.",
    "estructura": "Di qué secciones o partes tiene el instrumento y qué trata cada una, en una lista breve, con lo que "
                  "dice el RESULTADO CALCULADO; usa el TEXTO RECUPERADO para explicar de qué trata cada parte.",
    "patrones": "Presenta los patrones del RESULTADO CALCULADO como una lista con viñetas, con su cifra exacta, y "
                "explica cada uno con una frase prudente apoyada en el TEXTO RECUPERADO.",
    "sin_calificar": "Empieza diciendo que Indagata no califica las pruebas porque no tiene clave de respuestas. Después "
                     "describe con el RESULTADO CALCULADO qué opción eligieron más los alumnos en los reactivos que "
                     "tienen que ver con la pregunta. Nunca digas qué opción es correcta, quién aprobó ni quién sacó "
                     "más puntos.",
}
_DICE_SIN_CALIFICAR = re.compile(r"\bno\s+califica|\bclave\s+de\s+respuestas?\b|\bsin\s+clave\b")
# Formas en que el modelo niega un resultado calculado sin empezar por «no tengo información»
# («El primer instrumento no se menciona explícitamente en el contexto…», prueba del 22 oct).
_NIEGA = re.compile(
    r"\bno\s+se\s+(?:menciona|especifica|proporciona|indica|encuentra|incluye|describe)\w*\b"
    r"|\bno\s+(?:hay|tengo|cuento\s+con)\s+(?:suficiente\s+)?(?:informacion|datos)\b|\bno\s+es\s+posible\s+determinar\b"
)
# IDs y citas que contienen dígitos pero no son cifras: R017, p04, r06, E02, A001,
# [Fuente 2], INS-0012, KPI-07.
_NO_CIFRA = re.compile(r"\[fuente\s*\d+[^\]]*\]|\b(?:ins|kpi)-?\d+\b|\b[rpqaei]-?\d{1,4}\b", re.IGNORECASE)
_CIFRA = re.compile(r"\d+(?:[.,]\d+)?")


def _cifras(texto: str) -> set[float]:
    return {round(float(c.replace(",", ".")), 1) for c in _CIFRA.findall(_NO_CIFRA.sub(" ", texto))}


def cifras_fieles(respuesta: str, contexto: str) -> bool:
    """¿Toda cifra de la respuesta está en el contexto que vio el modelo?

    Es la garantía de la ruta estructurada: el LLM redacta, pero NO calcula. Si
    escribe una cifra que no está en el RESULTADO CALCULADO (o en sus fragmentos),
    se descarta su redacción y se responde con el resultado tal cual.
    """
    return _cifras(respuesta) <= _cifras(contexto)


_AVISOS_REINTENTO = {
    "negativa_corregida": "dice que no hay información, y el RESULTADO CALCULADO sí la tiene",
    "inventada": "escribe una tabla o menciona IDs que no están en el RESULTADO CALCULADO",
    "cifras_corregidas": "usa cifras que no están en el RESULTADO CALCULADO",
    "cifras_completadas": "omite cuántos cumplen, de cuántos y el porcentaje",
    "calificada": "habla de respuestas correctas, aciertos o calificaciones, y la prueba no se califica",
    "vacia": "está vacía",
    "cita_inventada": "pone entre comillas frases que no aparecen así en el RESULTADO CALCULADO ni en el TEXTO RECUPERADO",
}
# Citas textuales de la redacción: «…», “…” o "…" de cuatro palabras o más.
_CITA = re.compile(r"«([^»]{8,})»|“([^”]{8,})”|\"([^\"]{8,})\"")
_MIN_PALABRAS_CITA = 4
_COBERTURA_CITA = 0.85  # palabras de la cita que deben estar en el texto (tolera «respiración» por «res piración»)


# Fila de una tabla de respuestas: «| p07 «¿Cómo valoras…?» | La psicóloga fue muy amable… |».
_FILA_PREGUNTA = re.compile(r"^\|\s*(p\d{2,3})\b[^|]*\|(.*)\|\s*$", re.MULTILINE)
_ID_PREGUNTA = re.compile(r"\bp\d{2,3}\b")
_VENTANA_CITA = 120  # caracteres antes de la cita donde se busca a qué pregunta la atribuye


def _palabras(texto: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", dominio.normalizar(texto)))


def citas_fieles(respuesta: str, contexto: str) -> bool:
    """¿Cada cita textual está en lo que vio el modelo, y en la pregunta a la que se atribuye? Al interpretar una
    entrevista (4 nov) el modelo puede poner entre comillas una frase que la persona no dijo, o una que dijo en otra
    pregunta («se rio durante la pregunta p04: “La psicóloga fue muy amable…”», que está en p07; consulta 1695)."""
    palabras_contexto = _palabras(contexto)
    por_pregunta: dict[str, set[str]] = {}
    for pid, texto in _FILA_PREGUNTA.findall(contexto):
        por_pregunta.setdefault(pid, set()).update(_palabras(texto))
    for m in _CITA.finditer(respuesta):
        palabras = re.findall(r"[a-z0-9]+", dominio.normalizar(next(g for g in m.groups() if g)))
        if len(palabras) < _MIN_PALABRAS_CITA:
            continue
        antes = respuesta[max(0, m.start() - _VENTANA_CITA):m.start()].rsplit("\n", 1)[-1]
        atribuidas = [p for p in _ID_PREGUNTA.findall(antes) if p in por_pregunta]
        donde = set().union(*(por_pregunta[p] for p in atribuidas)) if atribuidas else palabras_contexto
        if sum(p in donde for p in palabras) / len(palabras) < _COBERTURA_CITA:
            return False
    return True
# Lenguaje de calificación: Indagata no tiene clave de respuestas. Si el resultado no lo trae, la redacción no
# puede decir «0 de 97 eligieron la opción correcta» (Fase 6, consulta 1575).
_CALIFICA = re.compile(
    r"\b(?:respuestas?|opcion(?:es)?)\s+(?:correctas?|incorrectas?)\b|\b(?:aciert\w*|acert\w*|calificacion\w*|puntajes?)\b"
)
_TABLA_MD = re.compile(r"^\s*\|.*\|\s*$", re.MULTILINE)  # la redacción no escribe tablas: se anexan del cálculo
_ID_DATO = re.compile(r"\b(?:[RAE]\d{2,5}|p\d{2,3}|r\d{2,3}|KPI-\d+)\b")


def ids_fieles(respuesta: str, contexto: str) -> bool:
    """¿Cada ID de respondente, pregunta o KPI de la redacción está en el resultado? (28 oct: inventó «R017»)."""
    return set(_ID_DATO.findall(respuesta)) <= set(_ID_DATO.findall(contexto))


_CONTEO_EN_PRIMERA = {"postura", "filtro"}  # la primera línea es el conteo («de 4, 3 sí y 1 no»)


def cifras_completas(respuesta: str, directa: str | None, consulta: str = "") -> bool:
    """¿La redacción conserva las cifras que dan sentido al resultado?

    El modelo pequeño a veces resume «el 13.3 %» y omite el «4 de 30», o dice «3 creen que
    sí» y calla que 1 dijo que no (matrices de formatos, 21–22 oct 2026). En resultados de
    una o dos líneas se exigen todas sus cifras; en las posturas y los filtros, las de la
    primera línea (el conteo); en las demás listas sí se vale resumir.
    """
    lineas = [l for l in (directa or "").splitlines() if l.strip()]
    if not lineas:
        return True
    if len(lineas) <= 2:
        return _cifras("\n".join(lineas)) <= _cifras(respuesta)
    if consulta not in _CONTEO_EN_PRIMERA:
        return True
    # En los filtros, la primera línea es la condición y el conteo viene después («Cumplen la condición 88
    # de 160…»): antes se revisaba la condición y una redacción sin «88 de 160» pasaba (24 oct, banco).
    conteo = next((l for l in lineas if "Cumplen la condición" in l or "Ninguno de los" in l), lineas[0])
    return _cifras(conteo) <= _cifras(respuesta)


async def _generar_estructurada(plan: Plan, modelo: str) -> tuple[str, bool]:
    """Redacción del resultado calculado, verificada cifra por cifra; las tablas calculadas se anexan al final."""
    inicio = time.perf_counter()
    respuesta, degradado = await ollama_client.generar_no_stream(plan.texto_prompt, modelo, sistema=prompt.SISTEMA)
    plan.tiempos["redaccion"] = round((time.perf_counter() - inicio) * 1000)
    inicio = time.perf_counter()
    motivo_antes = plan.motivo
    verificada, degradado = _verificar_redaccion(plan, respuesta, degradado)
    verificacion = {"intentos": 1, "resultado": "aceptada"}
    if plan.cifras_obligatorias is not None and plan.motivo != motivo_antes and not degradado:
        # Fase 4: un reintento con el motivo antes de caer al resultado calculado.
        fallo = plan.motivo.rsplit(":", 1)[-1]
        plan.motivo, plan.literal = motivo_antes, False
        aviso = _AVISOS_REINTENTO.get(fallo, "no respetó el RESULTADO CALCULADO")
        reintento, degradado = await ollama_client.generar_no_stream(
            f"{plan.texto_prompt}\n\nTu respuesta anterior fue: «{_pulir(respuesta, plan)[:600]}»\nNo es válida porque {aviso}. "
            "Escríbela de nuevo usando solo el RESULTADO CALCULADO y el TEXTO RECUPERADO.", modelo, sistema=prompt.SISTEMA)
        plan.tiempos["redaccion"] += round((time.perf_counter() - inicio) * 1000)
        verificada, degradado = _verificar_redaccion(plan, reintento, degradado)
        verificacion = {"intentos": 2, "primer_fallo": fallo,
                        "resultado": "respaldo" if plan.motivo != motivo_antes else "regenerada"}
        if plan.motivo == motivo_antes:
            plan.motivo = f"{plan.motivo}:regenerada"
    elif plan.motivo != motivo_antes:
        verificacion["resultado"] = "respaldo"
    respuesta = verificada
    if plan.plan_consulta is not None:
        plan.plan_consulta = {**plan.plan_consulta, "verificacion": verificacion}
    if plan.anexo:
        respuesta = f"{respuesta.rstrip()}\n\n{plan.anexo}"
    plan.tiempos["verificacion"] = round((time.perf_counter() - inicio) * 1000)
    return respuesta, degradado


def _verificar_redaccion(plan: Plan, respuesta: str, degradado: bool) -> tuple[str, bool]:
    respuesta = _pulir(respuesta, plan)
    contexto = "\n".join(c["texto"] for c in plan.contexto_usado())
    if plan.cifras_obligatorias is not None and not degradado:
        # Ruta del plan (28 oct): toda cifra de la redacción debe estar en el resultado y deben estar las del conteo.
        if not respuesta.strip():
            plan.motivo = f"{plan.motivo}:vacia"
        elif es_negativa(respuesta) or _NIEGA.search(dominio.normalizar(respuesta)):
            plan.motivo = f"{plan.motivo}:negativa_corregida"
        elif _TABLA_MD.search(respuesta) or not ids_fieles(respuesta, contexto):
            plan.motivo = f"{plan.motivo}:inventada"
        elif not cifras_fieles(respuesta, (plan.resultado or "") if plan.cifras_solo_resultado else contexto):
            plan.motivo = f"{plan.motivo}:cifras_corregidas"
        elif not citas_fieles(respuesta, contexto):
            plan.motivo = f"{plan.motivo}:cita_inventada"
        elif not plan.cifras_obligatorias <= _cifras(respuesta):
            plan.motivo = f"{plan.motivo}:cifras_completadas"
        elif (_CALIFICA.search(dominio.normalizar(respuesta)) and not _CALIFICA.search(dominio.normalizar(contexto))) \
                or (plan.motivo.startswith("estructurada:sin_calificar")
                    and not _DICE_SIN_CALIFICAR.search(dominio.normalizar(respuesta))):
            plan.motivo = f"{plan.motivo}:calificada"
        else:
            return respuesta, degradado
        logger.warning("Redacción descartada (%s); se responde con el resultado calculado.", plan.motivo)
        plan.literal = bool(plan.respuesta_directa)
        return plan.respuesta_directa or respuesta, degradado
    if degradado:
        respuesta, plan.literal = plan.respuesta_directa or respuesta, bool(plan.respuesta_directa)
    elif (es_negativa(respuesta) or _NIEGA.search(dominio.normalizar(respuesta))) and not plan.admite_negativa:
        # Con un resultado calculado SÍ hay respuesta: el modelo pequeño a veces dice
        # «no tengo información» porque no ve una sección CONTEXTO (auditoría Fase 4).
        logger.warning("La redacción negó un resultado calculado; se responde con el resultado.")
        plan.motivo = f"{plan.motivo}:negativa_corregida"
        respuesta, plan.literal = plan.respuesta_directa or respuesta, bool(plan.respuesta_directa)
    elif not cifras_fieles(respuesta, contexto):
        logger.warning("La redacción cambió cifras del resultado calculado; se responde con el resultado.")
        plan.motivo = f"{plan.motivo}:cifras_corregidas"
        respuesta, plan.literal = plan.respuesta_directa or respuesta, bool(plan.respuesta_directa)
    elif not cifras_completas(respuesta, plan.respuesta_directa, (plan.motivo or "estructurada:").split(":")[1]):
        logger.warning("La redacción omitió cifras del resultado calculado; se responde con el resultado.")
        plan.motivo = f"{plan.motivo}:cifras_completadas"
        respuesta, plan.literal = plan.respuesta_directa or respuesta, bool(plan.respuesta_directa)
    return respuesta, degradado


async def responder(peticion: ChatRequest):
    inicio = time.monotonic()
    modelo = peticion.modelo or settings.OLLAMA_MODEL
    clave = clave_cache(peticion, modelo)
    if (guardada := buscar_en_cache(clave, peticion.pregunta, modelo, inicio)) is not None:
        if peticion.stream:
            return StreamingResponse(_sse_guardada(guardada), media_type="text/event-stream")
        return ChatResponse(respuesta=guardada.respuesta, fuentes=guardada.salida.get("fuentes") or [], modelo=modelo,
                            referencias=guardada.salida.get("referencias") or [], decision=guardada.decision,
                            ruta=guardada.ruta, consultaId=guardada.consulta_id, enCache=True)

    # Mientras se responde, las métricas en segundo plano esperan (comparten el único Ollama).
    evaluacion.chat_empieza()
    try:
        plan = await planear(peticion)
    finally:
        evaluacion.chat_termina()
    plan.calcular_metricas = peticion.calcularMetricas

    if peticion.stream:
        return StreamingResponse(_sse(peticion.pregunta, modelo, plan, inicio, clave), media_type="text/event-stream")

    degradado = False
    evaluacion.chat_empieza()
    try:
        if plan.fija is not None:
            respuesta = plan.fija
        elif plan.resultado:
            respuesta, degradado = await _generar_estructurada(plan, modelo)
        else:
            respuesta, degradado = await ollama_client.generar_no_stream(plan.texto_prompt, modelo, sistema=prompt.SISTEMA)
            respuesta = _pulir(respuesta, plan)
            _anotar_cifras_semanticas(plan, respuesta)
    finally:
        evaluacion.chat_termina()
    fuentes, usados, respuesta = _fuentes_finales(plan, respuesta)
    referencias = plan.referencias_out() if usados else []
    consulta_id = registrar_consulta(peticion.pregunta, respuesta, modelo, usados, inicio, plan, clave=clave,
                                     salida=_salida(fuentes, referencias, degradado))
    return ChatResponse(respuesta=respuesta, fuentes=fuentes, modelo=modelo, degradado=degradado,
                        referencias=referencias, decision=plan.decision, ruta=plan.ruta,
                        consultaId=consulta_id)


def _anotar_cifras_semanticas(plan: Plan, respuesta: str) -> None:
    """En la ruta semántica la respuesta ya se transmitió: las cifras sin respaldo en los fragmentos se anotan en
    rag_log.plan (y salen en las métricas como «cifra sin respaldo») en lugar de retirarse."""
    contextos = [c["texto"] for c in plan.contexto_usado()]
    sin = evaluacion.cifras_sin_sustento(respuesta, contextos) if contextos else []
    plan.plan_consulta = {**(plan.plan_consulta or {}), "verificacion": {
        "resultado": "cifras_sin_respaldo" if sin else "aceptada", "cifras_sin_sustento": sin}}


def _fuentes_finales(plan: Plan, respuesta: str) -> tuple[list[FuenteChatOut], int, str]:
    """Fuentes que se muestran (ninguna si el modelo respondió que no tiene información), cuántas piezas de contexto
    se usaron y la respuesta final (con las citas que faltaban, en la redacción libre)."""
    if plan.fija is not None and plan.decision != dominio.DENTRO:
        return [], 0, respuesta
    if plan.fija is None and es_negativa(respuesta):  # no respondió con ellas: no se muestran como fuentes
        plan.decision = dominio.SIN_INFORMACION
        plan.motivo = plan.motivo or "el modelo no encontró la respuesta en el contexto"
        return [], 0, respuesta
    # Cada tarjeta lleva los pasajes que se le dieron al modelo (de qué parte del documento salió la información) y
    # solo se muestran las fuentes que la respuesta usó: citadas o parte del resultado calculado. En la redacción
    # libre (sin resultado calculado), si el modelo no citó, se citan las líneas que salen claramente de una fuente.
    fuentes = trazabilidad.adjuntar(plan.fuentes, plan.fragmentos)
    for f in fuentes:
        scores = [p.score for p in f.pasajes if p.score is not None]
        f.similitud = max(scores) if scores else plan.similitudes.get(str(f.instrumentoId))
    if plan.fija is None and not plan.resultado:
        respuesta = trazabilidad.citar(respuesta, fuentes)
    return trazabilidad.citadas(fuentes, respuesta, plan.resultado), plan.usados, respuesta


def _evento(nombre: str, datos: dict[str, Any]) -> str:
    return f"event: {nombre}\ndata: {json.dumps(datos, ensure_ascii=False)}\n\n"


async def _sse_guardada(guardada: Guardada):
    yield _evento("token", {"t": guardada.respuesta})
    yield _evento("fuentes", {
        "fuentes": guardada.salida.get("fuentes") or [],
        "referencias": guardada.salida.get("referencias") or [],
        "decision": guardada.decision,
        "ruta": guardada.ruta,
        "consultaId": guardada.consulta_id,
        "enCache": True,
    })
    yield "event: fin\ndata: {}\n\n"


async def _sse(pregunta: str, modelo: str, plan: Plan, inicio: float, clave: str | None = None):
    evaluacion.chat_empieza()
    try:
        async for evento in _sse_generar(pregunta, modelo, plan, inicio, clave):
            yield evento
    finally:
        evaluacion.chat_termina()


async def _sse_generar(pregunta: str, modelo: str, plan: Plan, inicio: float, clave: str | None = None):
    if plan.fija is not None:
        respuesta = plan.fija
        yield _evento("token", {"t": respuesta})
    elif plan.resultado:
        # La ruta estructurada no se transmite token por token: primero se verifica
        # que la redacción conserve las cifras (respuestas cortas: la espera es mínima).
        respuesta, _ = await _generar_estructurada(plan, modelo)
        yield _evento("token", {"t": respuesta})
    else:
        # Se emite con un retraso de `_RETENCION` caracteres: al terminar, el
        # remanente se limpia de la frase de «sin información» sobrante.
        generado, enviados = "", 0
        async for trozo in ollama_client.generar_stream(plan.texto_prompt, modelo, sistema=prompt.SISTEMA):
            generado += trozo
            hasta = len(generado) - _RETENCION
            if hasta > enviados:
                yield _evento("token", {"t": dominio.tachar_datos_personales(generado[enviados:hasta])})
                enviados = hasta
        final = quitar_sin_informacion_sobrante(generado)
        if final.startswith(generado[:enviados]):
            resto = final[enviados:]
        else:  # la frase quedó antes de lo ya enviado: no se puede retirar
            resto = generado[enviados:]
            final = generado
        if resto:
            yield _evento("token", {"t": _pulir(resto, plan)})
        respuesta = _pulir(final, plan)
        _anotar_cifras_semanticas(plan, respuesta)
    transmitida = respuesta
    fuentes, usados, respuesta = _fuentes_finales(plan, respuesta)
    referencias = plan.referencias_out() if usados else []
    # El mensaje de Ollama no disponible no se guarda como respuesta reutilizable.
    degradado = ollama_client.MENSAJE_DEGRADADO in respuesta
    latencia_ms = int((time.monotonic() - inicio) * 1000)  # lo que esperó la persona (se muestra bajo la respuesta)
    consulta_id = registrar_consulta(pregunta, respuesta, modelo, usados, inicio, plan, clave=clave,
                                     salida=_salida(fuentes, referencias, degradado))
    yield _evento("fuentes", {
        "fuentes": [f.model_dump() for f in fuentes],
        "referencias": [r.model_dump() for r in referencias],
        "decision": plan.decision,
        "ruta": plan.ruta,
        "consultaId": consulta_id,
        "latenciaMs": latencia_ms,
        # Si se añadieron citas, la UI reemplaza el texto que llegó por tokens por este (es el mismo, con las marcas).
        **({"respuesta": respuesta} if respuesta != transmitida else {}),
    })
    yield "event: fin\ndata: {}\n\n"
