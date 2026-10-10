"""Ingesta de instrumentos al índice vectorial (colección `instrumentos`).

El storage-service es el ÚNICO escritor de la colección `instrumentos` de Chroma.
Un instrumento solo se ingiere cuando su autor ya aprobó los metadatos (requisito
para el RAG). Por cada instrumento:

  1. Se resuelve su JSON estandarizado: último artefacto `analysis` (con KPIs) o
     `metadata` (recién aprobado); si no hay, `instrumento_procesado.ruta_json`
     (instrumentos sembrados de la demo).
  2. Se trocea en chunks:
       - chunk 0..k  `encabezado`: título, objetivo, Dublin Core, metadatos del
                     tipo y KPIs asociados (el chunk 0 SIEMPRE es encabezado: lo
                     usa visualization-service para comparar instrumentos);
       - un chunk    `pregunta` por reactivo (texto, opciones y resultados);
       - chunks      `contenido` con el texto íntegro (entrevistas/pruebas).
  3. Se vectorizan y se escriben en Chroma (reemplazando los anteriores) y se
     registran en `documento_vectorizado` + `coleccion_vectorial`.
  4. `instrumento_procesado.estado` pasa a `vectorizado`.

Las filas `documento_vectorizado` de OTRAS colecciones (p. ej. el summary que
escribe analysis-service como evidencia de KPIs) nunca se tocan.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from shared.db.core.config import settings
from shared.models.coleccion_vectorial import ColeccionVectorial
from shared.models.documento_vectorizado import DocumentoVectorizado
from shared.models.instrumento_procesado import InstrumentoProcesado
from shared.models.raw_data import RawData
from shared.models.usuario import Usuario

from services import file_manager, vectores

logger = logging.getLogger("storage-service")

VENTANA = 800
SOLAPE = 150
MIN_LONGITUD = 40

_ESTADOS_APROBADOS = {"estandarizado", "vectorizado"}
_TIPO_UI = {
    "encuesta": "Encuesta",
    "entrevista": "Entrevista",
    "prueba_estandarizada": "Prueba estandarizada",
}
_NIVEL_POSGRADO = ("posgrado", "maestr", "doctor", "especialidad")


class IndiceError(Exception):
    """Error de negocio de la ingesta (con código HTTP sugerido)."""

    def __init__(self, mensaje: str, status_code: int) -> None:
        super().__init__(mensaje)
        self.status_code = status_code


@dataclass
class Chunk:
    texto: str
    seccion: str
    pregunta_id: str = ""
    pregunta: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


# ── Utilidades ─────────────────────────────────────────────────────────────────


def _dict(valor: Any) -> dict[str, Any]:
    return valor if isinstance(valor, dict) else {}


def _lista(valor: Any) -> list[Any]:
    return valor if isinstance(valor, list) else []


def _texto(valor: Any) -> str:
    if valor is None:
        return ""
    if isinstance(valor, (list, tuple)):
        return ", ".join(t for t in (_texto(v) for v in valor) if t)
    if isinstance(valor, dict):
        return ", ".join(f"{k}: {_texto(v)}" for k, v in valor.items() if _texto(v))
    return str(valor).strip()


def trocear(texto: str) -> list[str]:
    """Ventanas de ~800 caracteres con solape de 150, cortando por párrafo/oración."""
    if not texto or not texto.strip():
        return []
    unidades: list[str] = []
    for parrafo in texto.split("\n\n"):
        parrafo = parrafo.strip()
        if not parrafo:
            continue
        if len(parrafo) <= VENTANA:
            unidades.append(parrafo)
            continue
        buffer = ""
        for oracion in parrafo.replace("\n", " ").split(". "):
            oracion = oracion.strip()
            if not oracion:
                continue
            candidato = f"{buffer}. {oracion}" if buffer else oracion
            if len(candidato) <= VENTANA:
                buffer = candidato
            else:
                if buffer:
                    unidades.append(buffer)
                buffer = oracion
        if buffer:
            unidades.append(buffer)

    chunks: list[str] = []
    actual = ""
    for unidad in unidades:
        candidato = f"{actual}\n\n{unidad}" if actual else unidad
        if len(candidato) <= VENTANA:
            actual = candidato
            continue
        if actual:
            chunks.append(actual)
            cola = actual[-SOLAPE:].strip()
            actual = f"{cola}\n\n{unidad}" if cola else unidad
        else:
            inicio = 0
            while inicio < len(unidad):
                chunks.append(unidad[inicio : inicio + VENTANA])
                inicio += VENTANA - SOLAPE
            actual = ""
    if actual:
        chunks.append(actual)
    return [c.strip() for c in chunks if len(c.strip()) >= MIN_LONGITUD]


def esta_aprobado(procesado: InstrumentoProcesado | None) -> bool:
    """Metadatos aprobados por el autor (o instrumento ya estandarizado)."""
    if procesado is None:
        return False
    return procesado.fecha_aprobado is not None or procesado.estado in _ESTADOS_APROBADOS


def ultimo_procesado(db: Session, id_crudo: int) -> InstrumentoProcesado | None:
    return (
        db.query(InstrumentoProcesado)
        .filter(InstrumentoProcesado.id_crudo == id_crudo)
        .order_by(InstrumentoProcesado.id_instrumento.desc())
        .first()
    )


def resolver_json(id_crudo: int, procesado: InstrumentoProcesado | None) -> dict[str, Any] | None:
    """JSON estandarizado: artefacto analysis → metadata → ruta_json."""
    for tipo in ("analysis", "metadata"):
        entrada = file_manager.obtener(tipo, str(id_crudo))
        if entrada is not None:
            try:
                return file_manager.leer_json(entrada)
            except (file_manager.NoEncontradoError, file_manager.AlmacenamientoError) as exc:
                logger.warning("Artefacto %s ilegible: %s", entrada.get("key"), exc)
    ruta_json = getattr(procesado, "ruta_json", None)
    if ruta_json:
        try:
            archivo = file_manager.leer(ruta_json)
            datos = json.loads(archivo.contenido.decode("utf-8"))
            return datos if isinstance(datos, dict) else None
        except (
            file_manager.NoEncontradoError,
            file_manager.RutaInseguraError,
            file_manager.AlmacenamientoError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            logger.warning("ruta_json ilegible (%s): %s", ruta_json, exc)
    return None


# ── Construcción de chunks ─────────────────────────────────────────────────────


def _nombres_kpis(data: dict[str, Any]) -> list[str]:
    nombres: list[str] = []
    for k in _lista(data.get("inferred_kpis")):
        nombre = _texto(_dict(k).get("nombre_kpi"))
        if nombre and nombre not in nombres:
            nombres.append(nombre)
    for nombre in _lista(_dict(data.get("design_reference")).get("kpi_hints")):
        nombre = _texto(nombre)
        if nombre and nombre not in nombres:
            nombres.append(nombre)
    return nombres


def _resumen_estadistico(stats: dict[str, Any]) -> str:
    if not stats:
        return ""
    partes: list[str] = []
    if stats.get("mean") is not None:
        partes.append(f"media {float(stats['mean']):.2f}")
        if stats.get("std") is not None:
            partes.append(f"desv. est. {float(stats['std']):.2f}")
    distribucion = _dict(stats.get("distribution"))
    total = sum(v for v in distribucion.values() if isinstance(v, (int, float))) or 0
    if distribucion and total:
        ordenados = sorted(distribucion.items(), key=lambda kv: -float(kv[1] or 0))[:6]
        partes.append(
            "; ".join(f"{valor}: {conteo} ({100 * float(conteo) / total:.0f}%)" for valor, conteo in ordenados)
        )
    n = stats.get("n") or stats.get("n_respuestas")
    prefijo = f"Resultados (n={n})" if n else "Resultados"
    return f"{prefijo}: " + ", ".join(partes) if partes else ""


def construir_chunks(data: dict[str, Any], tipo_ui: str) -> list[Chunk]:
    """Trocea el JSON estandarizado en chunks de encabezado, preguntas y contenido."""
    instrumento = _dict(data.get("instrument"))
    metadata = _dict(data.get("metadata"))
    dc = _dict(metadata.get("dublin_core"))
    especificos = _dict(metadata.get("survey_specific"))
    titulo = _texto(instrumento.get("title")) or _texto(dc.get("dc:title")) or "Instrumento"

    lineas = [f"Instrumento: {titulo}", f"Tipo: {tipo_ui}"]
    for etiqueta, valor in (
        ("Objetivo", instrumento.get("objective")),
        ("Descripción", dc.get("dc:description")),
        ("Temas", dc.get("dc:subject")),
        ("Cobertura", dc.get("dc:coverage")),
        ("Autor", dc.get("dc:creator")),
        ("Fecha", dc.get("dc:date")),
        ("Dimensiones", instrumento.get("dimensions_explored")),
    ):
        if _texto(valor):
            lineas.append(f"{etiqueta}: {_texto(valor)}")
    for clave, valor in especificos.items():
        if _texto(valor):
            etiqueta = clave.replace("_", " ").capitalize()
            lineas.append(f"{etiqueta}: {_texto(valor)}")
    kpis = _nombres_kpis(data)
    if kpis:
        lineas.append(f"KPIs asociados: {', '.join(kpis)}")

    chunks = [Chunk(texto=t, seccion="encabezado") for t in trocear("\n\n".join(lineas))]
    if not chunks:
        chunks = [Chunk(texto="\n".join(lineas), seccion="encabezado")]

    # Los chunks de pregunta y de contenido NO repiten el título del instrumento:
    # viaja en la metadata (y el prompt del RAG lo muestra en cada fuente). Así el
    # vector de cada pregunta refleja lo que pregunta, que es lo que se compara
    # con los KPIs para saber qué preguntas los miden.
    estadisticas = _dict(_dict(data.get("statistics")).get("per_question"))
    for seccion in _lista(instrumento.get("sections")):
        seccion = _dict(seccion)
        nombre_seccion = _texto(seccion.get("name"))
        for pregunta in _lista(seccion.get("questions")):
            pregunta = _dict(pregunta)
            texto_pregunta = _texto(pregunta.get("text"))
            if not texto_pregunta:
                continue
            pid = _texto(pregunta.get("question_id"))
            partes = [nombre_seccion] if nombre_seccion and nombre_seccion != "Reactivos" else []
            partes.append(f"Pregunta {pid}: {texto_pregunta}" if pid else f"Pregunta: {texto_pregunta}")
            opciones = [_texto(o) for o in _lista(pregunta.get("options")) if _texto(o)]
            if opciones:
                partes.append("Opciones: " + "; ".join(opciones[:15]))
            resumen = _resumen_estadistico(_dict(estadisticas.get(pid)))
            if resumen:
                partes.append(resumen)
            chunks.append(
                Chunk(
                    texto="\n".join(partes),
                    seccion="pregunta",
                    pregunta_id=pid,
                    pregunta=texto_pregunta[:300],
                )
            )

    contenido = _texto(instrumento.get("contenido"))
    for fragmento in trocear(contenido):
        chunks.append(Chunk(texto=fragmento, seccion="contenido"))
    return chunks


def _nivel(data: dict[str, Any]) -> str:
    metadata = _dict(data.get("metadata"))
    textos = " ".join(
        (
            _texto(_dict(metadata.get("dublin_core")).get("dc:coverage")),
            _texto(_dict(metadata.get("survey_specific")).get("poblacion_objetivo")),
            _texto(_dict(metadata.get("survey_specific")).get("nivel_educativo")),
        )
    ).lower()
    return "Posgrado" if any(c in textos for c in _NIVEL_POSGRADO) else "Licenciatura"


def _anio(data: dict[str, Any], raw: RawData) -> int:
    fecha = _texto(_dict(_dict(data.get("metadata")).get("dublin_core")).get("dc:date"))
    if len(fecha) >= 4 and fecha[:4].isdigit():
        return int(fecha[:4])
    if isinstance(raw.fecha_carga, datetime):
        return raw.fecha_carga.year
    return datetime.now().year


# ── Operaciones ────────────────────────────────────────────────────────────────


def _get_or_create_coleccion(db: Session) -> ColeccionVectorial:
    nombre = settings.CHROMA_COLLECTION_INSTRUMENTOS
    col = db.query(ColeccionVectorial).filter(ColeccionVectorial.nombre == nombre).first()
    if col is None:
        col = ColeccionVectorial(
            nombre=nombre,
            embedding_model=settings.EMBEDDING_MODEL,
            chunk_size=VENTANA,
            chunk_overlap=SOLAPE,
        )
        db.add(col)
        db.flush()
    return col


def _contar_vectores(coleccion, id_crudo: int) -> int:
    res = coleccion.get(where={"instrumentoId": str(id_crudo)}, include=[])
    return len(res.get("ids") or [])


def indexar_instrumento(db: Session, id_crudo: int, *, reindexar: bool = True) -> dict[str, Any]:
    """Ingiere (o reingiere) un instrumento aprobado en la colección `instrumentos`."""
    nombre_col = settings.CHROMA_COLLECTION_INSTRUMENTOS
    raw = db.get(RawData, id_crudo)
    if raw is None:
        raise IndiceError(f"Instrumento (id_crudo={id_crudo}) no encontrado.", 404)
    procesado = ultimo_procesado(db, id_crudo)
    if not esta_aprobado(procesado):
        raise IndiceError(
            "Los metadatos del instrumento no han sido aprobados por su autor; "
            "no puede ingerirse al RAG todavía.",
            409,
        )
    assert procesado is not None  # esta_aprobado lo garantiza

    col_db = _get_or_create_coleccion(db)
    existentes = (
        db.query(DocumentoVectorizado)
        .filter(
            DocumentoVectorizado.instrumento_id == procesado.id_instrumento,
            DocumentoVectorizado.coleccion_id == col_db.coleccion_id,
        )
        .count()
    )
    if existentes and not reindexar:
        return {
            "instrumentoId": str(id_crudo),
            "idInstrumento": procesado.id_instrumento,
            "coleccion": nombre_col,
            "chunks": existentes,
            "estado": "indexado",
            "motivo": "Ya estaba indexado.",
        }

    data = resolver_json(id_crudo, procesado)
    if not data:
        raise IndiceError("El instrumento no tiene JSON estandarizado para indexar.", 422)

    tipo_ui = _TIPO_UI.get((raw.tipo_instrumento or "").lower(), "Encuesta")
    chunks = construir_chunks(data, tipo_ui)
    dc = _dict(_dict(data.get("metadata")).get("dublin_core"))
    autor = db.get(Usuario, raw.id_owner)
    titulo = _texto(_dict(data.get("instrument")).get("title")) or _texto(dc.get("dc:title")) or raw.nombre_archivo
    base_meta = {
        "instrumentoId": str(id_crudo),
        "idInstrumento": int(procesado.id_instrumento),
        "titulo": titulo[:300],
        "tipo": tipo_ui,
        "investigador": _texto(dc.get("dc:creator")) or (autor.nombre if autor else ""),
        "autorId": str(raw.id_owner),
        "nivel": _nivel(data),
        "anio": _anio(data, raw),
        "kpis": json.dumps(_nombres_kpis(data), ensure_ascii=False),
    }
    ids = [f"inst-{id_crudo}-{n}" for n in range(len(chunks))]
    metadatas = [
        {
            **base_meta,
            "seccion": c.seccion,
            "preguntaId": c.pregunta_id,
            "pregunta": c.pregunta,
            "chunk_index": n,
        }
        for n, c in enumerate(chunks)
    ]

    try:
        embeddings = vectores.embed_texts([c.texto for c in chunks])
    except Exception as exc:  # noqa: BLE001 - modelo no disponible
        logger.exception("No se pudo cargar el modelo de embeddings.")
        raise IndiceError(f"No se pudo vectorizar el instrumento: {exc}", 503) from exc

    try:
        coleccion = vectores.coleccion(nombre_col)
        coleccion.delete(where={"instrumentoId": str(id_crudo)})
        coleccion.upsert(ids=ids, embeddings=embeddings, documents=[c.texto for c in chunks], metadatas=metadatas)
    except Exception as exc:  # noqa: BLE001 - Chroma caído
        logger.exception("Vector store no disponible.")
        raise IndiceError(f"Vector store no disponible: {exc}", 502) from exc

    db.query(DocumentoVectorizado).filter(
        DocumentoVectorizado.instrumento_id == procesado.id_instrumento,
        DocumentoVectorizado.coleccion_id == col_db.coleccion_id,
    ).delete(synchronize_session=False)
    for n, (chunk, meta) in enumerate(zip(chunks, metadatas)):
        db.add(
            DocumentoVectorizado(
                instrumento_id=procesado.id_instrumento,
                coleccion_id=col_db.coleccion_id,
                chroma_vector_id=ids[n],
                chunk_index=n,
                seccion=chunk.seccion,
                chunk_texto=chunk.texto,
                chunk_metadata=meta,
                n_tokens=len(chunk.texto.split()),
            )
        )
    procesado.estado = "vectorizado"
    db.commit()
    logger.info("Instrumento %s indexado con %d chunks.", id_crudo, len(chunks))
    return {
        "instrumentoId": str(id_crudo),
        "idInstrumento": procesado.id_instrumento,
        "coleccion": nombre_col,
        "chunks": len(chunks),
        "estado": "indexado",
        "motivo": None,
    }


def desindexar_instrumento(db: Session | None, id_crudo: int) -> int:
    """Quita los vectores del instrumento de Chroma y de documento_vectorizado."""
    eliminados = 0
    try:
        coleccion = vectores.coleccion(settings.CHROMA_COLLECTION_INSTRUMENTOS)
        eliminados = _contar_vectores(coleccion, id_crudo)
        if eliminados:
            coleccion.delete(where={"instrumentoId": str(id_crudo)})
    except Exception as exc:  # noqa: BLE001
        raise IndiceError(f"Vector store no disponible: {exc}", 502) from exc

    if db is not None:
        col_db = (
            db.query(ColeccionVectorial)
            .filter(ColeccionVectorial.nombre == settings.CHROMA_COLLECTION_INSTRUMENTOS)
            .first()
        )
        procesados = db.query(InstrumentoProcesado).filter(InstrumentoProcesado.id_crudo == id_crudo).all()
        for procesado in procesados:
            if col_db is not None:
                db.query(DocumentoVectorizado).filter(
                    DocumentoVectorizado.instrumento_id == procesado.id_instrumento,
                    DocumentoVectorizado.coleccion_id == col_db.coleccion_id,
                ).delete(synchronize_session=False)
            if procesado.estado == "vectorizado":
                procesado.estado = "estandarizado"
        db.commit()
    return eliminados


def estado_indice(db: Session, id_crudo: int) -> dict[str, Any]:
    raw = db.get(RawData, id_crudo)
    if raw is None:
        raise IndiceError(f"Instrumento (id_crudo={id_crudo}) no encontrado.", 404)
    procesado = ultimo_procesado(db, id_crudo)
    chunks = 0
    col_db = (
        db.query(ColeccionVectorial)
        .filter(ColeccionVectorial.nombre == settings.CHROMA_COLLECTION_INSTRUMENTOS)
        .first()
    )
    if procesado is not None and col_db is not None:
        chunks = (
            db.query(DocumentoVectorizado)
            .filter(
                DocumentoVectorizado.instrumento_id == procesado.id_instrumento,
                DocumentoVectorizado.coleccion_id == col_db.coleccion_id,
            )
            .count()
        )
    return {
        "instrumentoId": str(id_crudo),
        "coleccion": settings.CHROMA_COLLECTION_INSTRUMENTOS,
        "indexado": chunks > 0,
        "chunks": chunks,
        "aprobado": esta_aprobado(procesado),
    }


def listar_colecciones(db: Session) -> list[dict[str, Any]]:
    """Colecciones de Chroma con su nº de vectores y su configuración registrada."""
    configuracion = {c.nombre: c for c in db.query(ColeccionVectorial).all()}
    try:
        cliente = vectores.get_client()
        colecciones = cliente.list_collections()
    except Exception as exc:  # noqa: BLE001
        raise IndiceError(f"Vector store no disponible: {exc}", 502) from exc
    salida: list[dict[str, Any]] = []
    for col in colecciones:
        nombre = col if isinstance(col, str) else col.name
        try:
            n = cliente.get_collection(nombre).count()
        except Exception:  # noqa: BLE001
            n = 0
        conf = configuracion.get(nombre)
        salida.append(
            {
                "nombre": nombre,
                "n_vectores": n,
                "embedding_model": conf.embedding_model if conf else None,
                "chunk_size": conf.chunk_size if conf else None,
                "chunk_overlap": conf.chunk_overlap if conf else None,
            }
        )
    return sorted(salida, key=lambda c: c["nombre"])
