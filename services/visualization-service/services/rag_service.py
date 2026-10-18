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
"""
from __future__ import annotations

import json
import logging
import re
import time
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse

from shared.db.core.config import settings
from shared.models.rag_log import RagLog

from models import ChatRequest, ChatResponse, FuenteChatOut, IndexRequest, ReferenciaChatOut
from services import dominio, enrutador, evaluacion, ollama_client, prompt, storage_client, vectores

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
        res = coleccion.query(
            query_embeddings=[vector],
            n_results=peticion.top_k * _CANDIDATOS_POR_FRAGMENTO,
            where=where,
            include=["metadatas", "documents", "distances"],
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Vector store no disponible: %s", exc)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Vector store no disponible.") from exc

    fragmentos: list[dict[str, Any]] = []
    encabezados: dict[str, int] = {}
    por_instrumento: dict[str, int] = {}
    score_max = 0.0
    for meta, doc, dist in zip(
        (res.get("metadatas") or [[]])[0], (res.get("documents") or [[]])[0], (res.get("distances") or [[]])[0]
    ):
        meta = meta or {}
        score = round(1.0 - float(dist), 4)
        score_max = max(score_max, score)
        if score < settings.RAG_MIN_SCORE:
            continue  # poco relacionado: no se le da al LLM para que no improvise
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
            }
        )
    return fragmentos, score_max


def _numerar(fragmentos: list[dict[str, Any]], primero: list[enrutador.Instrumento] | None = None) -> list[FuenteChatOut]:
    """Una fuente por instrumento, numerada: [Fuente n] es la n-ésima tarjeta de la UI.

    Los instrumentos del resultado calculado (`primero`) van antes; después, los de
    los fragmentos en orden de relevancia. Asigna `numero` a cada fragmento.
    """
    fuentes: list[FuenteChatOut] = []
    numeros: dict[str, int] = {}
    for ins in primero or []:
        numeros[ins.id_crudo] = len(numeros) + 1
        kpis = [k.get("nombre", "") for k in ins.doc.get("kpis_asociados") or []]
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
                kpis=f["kpis"],
                fragmento=f["fragmento"],
            )
        )
    return fuentes


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
            )
            evaluar = False
            if plan is not None:
                fila.decision_dominio = plan.decision
                fila.motivo = plan.motivo
                fila.score_max = plan.score_max
                fila.ruta = plan.ruta
                fila.instrumentos = list(plan.instrumentos)
                fila.contexto_usado = plan.contexto_usado() if chunks else []
                # Solo se evalúan las respuestas que redactó el LLM con contexto; los
                # rechazos, «no existe» y «sin información» no tienen qué medir.
                if not settings.RAG_METRICAS:
                    fila.metricas = evaluacion.omitida("Métricas desactivadas.")
                elif plan.fija is not None or not chunks:
                    fila.metricas = evaluacion.omitida("Respuesta sin redacción del modelo (rechazo, «no existe» o sin información).")
                else:
                    evaluar = True
            sesion.add(fila)
            sesion.commit()
            if evaluar:  # después de entregar la respuesta, en segundo plano
                evaluacion.programar(fila.rag_log_id, fabrica_sesiones)
            return fila.rag_log_id
        finally:
            sesion.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo registrar la consulta RAG: %s", exc)
        return None


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
    if frase not in texto or len(sin_frase) < 20:
        return texto
    return sin_frase


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

    @property
    def usados(self) -> int:
        return len(self.fragmentos) + (1 if self.resultado else 0) + len(self.referencias)

    def contexto_usado(self) -> list[dict[str, Any]]:
        """Lo que vio el LLM (para evaluar fidelidad y precisión del contexto después)."""
        salida: list[dict[str, Any]] = []
        if self.resultado:
            salida.append({"tipo": "resultado", "texto": self.resultado})
        salida += [{"tipo": r.tipo, "titulo": r.titulo, "texto": r.texto} for r in self.referencias]
        salida += [{"tipo": "fragmento", "instrumentoId": f["instrumentoId"], "seccion": f["seccion"], "texto": f["fragmento"]}
                   for f in self.fragmentos]
        return salida

    def referencias_out(self) -> list[ReferenciaChatOut]:
        return [ReferenciaChatOut(tipo=r.tipo, titulo=r.titulo, texto=r.texto) for r in self.referencias]


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
    """Aplica el dominio acotado y el enrutador; deja listo el prompt o la respuesta fija."""
    pregunta = peticion.pregunta
    ids = [i for i in (peticion.instrumentoIds or []) if i]
    contexto = peticion.contexto.model_dump() if peticion.contexto else None

    # Capa 1a: reglas de intención (sin modelo).
    if regla := dominio.reglas(pregunta):
        decision, motivo = regla
        return Plan(decision=decision, motivo=motivo, fija=dominio.mensaje(decision, _tipos_alcance(ids)), instrumentos=ids)

    # Ayuda de la plataforma: solo la base curada (no consulta Chroma ni exige alcance).
    if dominio.es_ayuda(pregunta):
        vector = _vector(pregunta)
        refs = [a for a, s in dominio.anclas_cercanas(pregunta, vector, "ayuda", k=3) if s >= 0.35] or \
               [a for a, _ in dominio.anclas_cercanas(pregunta, vector, "ayuda", k=2)]
        return Plan(decision=dominio.AYUDA, ruta="ayuda", referencias=refs, instrumentos=ids,
                    texto_prompt=prompt.construir(pregunta, [], contexto, referencias=refs))

    vector = _vector(pregunta)
    # Ruta estructurada (cálculo exacto sobre el documento vigente).
    resultado = None
    try:
        sesion = fabrica_sesiones()
        try:
            resultado = enrutador.resolver(pregunta, sesion, ids)
        finally:
            sesion.close()
    except Exception as exc:  # noqa: BLE001 — sin BD o storage: sigue la ruta semántica
        logger.warning("Enrutador no disponible: %s", exc)

    fragmentos, score_chunks = _buscar(peticion, vector)
    if resultado is not None:
        # Ruta MIXTA solo en las consultas de KPI (la justificación y las preguntas se
        # complementan con sus fragmentos). En las demás el resultado va SOLO: con los
        # fragmentos al lado, el modelo llegó a tomar el % de toda la muestra en lugar
        # del % del grupo calculado (auditoría de la Fase 3).
        propios = {i.id_crudo for i in resultado.instrumentos}
        fragmentos = ([f for f in fragmentos if f["instrumentoId"] in propios][:3]
                      if resultado.consulta in _CONSULTAS_MIXTAS else [])
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
        plan.fuentes = _numerar(fragmentos, resultado.instrumentos)
        numeros = {f.instrumentoId: f.numero for f in plan.fuentes}
        plan.instrumentos = ids or [i.id_crudo for i in resultado.instrumentos]
        if not resultado.encontrado:  # «no existe»: se dice tal cual, sin LLM
            plan.motivo = f"estructurada:{resultado.consulta}:no_existe"
            plan.fija = resultado.respuesta_directa(numeros)
            return plan
        plan.motivo = f"estructurada:{resultado.consulta}"
        plan.resultado = resultado.texto(numeros)
        plan.respuesta_directa = resultado.respuesta_directa(numeros)
        plan.admite_negativa = resultado.admite_negativa
    else:
        plan.ruta = "semantica"
        plan.fuentes = _numerar(fragmentos)
        if not fragmentos and not glosario:
            if score < settings.RAG_FUERA_MAX:  # nada del acervo, del glosario ni de los KPIs se le parece
                plan.decision, plan.motivo = dominio.FUERA, f"similitud máxima {score:.2f} < {settings.RAG_FUERA_MAX}"
                plan.fija = dominio.mensaje(dominio.FUERA, _tipos_alcance(ids))
            else:
                plan.decision, plan.motivo, plan.fija = dominio.SIN_INFORMACION, "sin fragmentos sobre el umbral", MENSAJE_SIN_CONTEXTO
            return plan
        # Capa 1c: zona gris (similitud ambigua y ninguna regla decidió).
        if not glosario and dominio.en_zona_gris(score):
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
    plan.texto_prompt = prompt.construir(pregunta, plan.fragmentos, contexto, resultado=plan.resultado, referencias=plan.referencias)
    return plan


_CITA_CURADA = re.compile(r"\s*\[(Glosario|Ayuda):\s*([^\]]+)\]")


def quitar_citas_inventadas(texto: str, referencias: list[dominio.Ancla]) -> str:
    """Quita las citas [Glosario: …]/[Ayuda: …] que no corresponden a una referencia dada.

    El modelo imita el formato de cita de las reglas aunque no haya recibido glosario
    ni ayuda (p. ej. «[Glosario: Tamaño Promedio de Clase]»): una cita que no existe
    hace parecer verificable algo que no lo es.
    """
    validas = {(r.tipo, dominio.normalizar(r.titulo)) for r in referencias}

    def _filtrar(m: re.Match) -> str:
        tipo = "glosario" if m.group(1) == "Glosario" else "ayuda"
        return m.group(0) if (tipo, dominio.normalizar(m.group(2))) in validas else ""

    return _CITA_CURADA.sub(_filtrar, texto)


def _pulir(texto: str, plan: Plan | None = None) -> str:
    """Capa 3: frase de «sin información» sobrante, citas inventadas y datos personales."""
    texto = quitar_sin_informacion_sobrante(texto)
    if plan is not None:
        texto = quitar_citas_inventadas(texto, plan.referencias)
    return dominio.tachar_datos_personales(texto)


_CONSULTAS_MIXTAS = {"kpi", "kpi_preguntas"}
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


async def _generar_estructurada(plan: Plan, modelo: str) -> tuple[str, bool]:
    """Redacción del resultado calculado, verificada cifra por cifra."""
    respuesta, degradado = await ollama_client.generar_no_stream(plan.texto_prompt, modelo, sistema=prompt.SISTEMA)
    respuesta = _pulir(respuesta, plan)
    contexto = "\n".join(c["texto"] for c in plan.contexto_usado())
    if degradado:
        respuesta = plan.respuesta_directa or respuesta
    elif es_negativa(respuesta) and not plan.admite_negativa:
        # Con un resultado calculado SÍ hay respuesta: el modelo pequeño a veces dice
        # «no tengo información» porque no ve una sección CONTEXTO (auditoría Fase 4).
        logger.warning("La redacción negó un resultado calculado; se responde con el resultado.")
        plan.motivo = f"{plan.motivo}:negativa_corregida"
        respuesta = plan.respuesta_directa or respuesta
    elif not cifras_fieles(respuesta, contexto):
        logger.warning("La redacción cambió cifras del resultado calculado; se responde con el resultado.")
        plan.motivo = f"{plan.motivo}:cifras_corregidas"
        respuesta = plan.respuesta_directa or respuesta
    return respuesta, degradado


async def responder(peticion: ChatRequest):
    inicio = time.monotonic()
    modelo = peticion.modelo or settings.OLLAMA_MODEL
    plan = await planear(peticion)

    if peticion.stream:
        return StreamingResponse(_sse(peticion.pregunta, modelo, plan, inicio), media_type="text/event-stream")

    degradado = False
    if plan.fija is not None:
        respuesta = plan.fija
    elif plan.resultado:
        respuesta, degradado = await _generar_estructurada(plan, modelo)
    else:
        respuesta, degradado = await ollama_client.generar_no_stream(plan.texto_prompt, modelo, sistema=prompt.SISTEMA)
        respuesta = _pulir(respuesta, plan)
    fuentes, usados = _fuentes_finales(plan, respuesta)
    consulta_id = registrar_consulta(peticion.pregunta, respuesta, modelo, usados, inicio, plan)
    return ChatResponse(respuesta=respuesta, fuentes=fuentes, modelo=modelo, degradado=degradado,
                        referencias=plan.referencias_out() if usados else [], decision=plan.decision, ruta=plan.ruta,
                        consultaId=consulta_id)


def _fuentes_finales(plan: Plan, respuesta: str) -> tuple[list[FuenteChatOut], int]:
    """Fuentes que se muestran: ninguna si el modelo respondió que no tiene información."""
    if plan.fija is not None and plan.decision != dominio.DENTRO:
        return [], 0
    if plan.fija is None and es_negativa(respuesta):  # no respondió con ellas: no se muestran como fuentes
        plan.decision = dominio.SIN_INFORMACION
        plan.motivo = plan.motivo or "el modelo no encontró la respuesta en el contexto"
        return [], 0
    return plan.fuentes, plan.usados


def _evento(nombre: str, datos: dict[str, Any]) -> str:
    return f"event: {nombre}\ndata: {json.dumps(datos, ensure_ascii=False)}\n\n"


async def _sse(pregunta: str, modelo: str, plan: Plan, inicio: float):
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
    fuentes, usados = _fuentes_finales(plan, respuesta)
    consulta_id = registrar_consulta(pregunta, respuesta, modelo, usados, inicio, plan)
    yield _evento("fuentes", {
        "fuentes": [f.model_dump() for f in fuentes],
        "referencias": [r.model_dump() for r in plan.referencias_out()] if usados else [],
        "decision": plan.decision,
        "ruta": plan.ruta,
        "consultaId": consulta_id,
    })
    yield "event: fin\ndata: {}\n\n"
