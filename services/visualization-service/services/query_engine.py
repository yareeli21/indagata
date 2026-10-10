"""Motor de consultas de solo lectura: catálogo, filtros, KPIs y relaciones.

Construye una «ficha» por instrumento combinando, en este orden de prioridad:
  1. las tablas aprobadas por el autor (metadatos_dc, metadatos_enriquecidos_*);
  2. el JSON estandarizado (`instrumento_procesado.ruta_json`, o el del seed);
  3. las columnas de raw_data / instrumento_procesado.

Sobre las fichas resuelve:
  - catálogo con filtros y facetas («filtrar su información»);
  - catálogo de KPIs (tabla `kpi`), resumen del acervo y datos de dashboard;
  - qué preguntas de cada instrumento miden un KPI (similitud en Chroma entre el
    vector del KPI y los vectores de las preguntas del instrumento);
  - instrumentos relacionados de otros autores (KPIs, nivel y similitud semántica).
"""
from __future__ import annotations

import json
import logging
import re
import threading
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from shared.db.core.config import settings
from shared.models.instrumento_procesado import InstrumentoProcesado
from shared.models.kpi import KPI
from shared.models.kpi_inferido import KPIInferido
from shared.models.kpi_inferido_chunk import KpiInferidoChunk
from shared.models.kpi_variable import KPIVariable
from shared.models.metadatos_dc import MetadatosDC
from shared.models.metadatos_encuestas import MetadatosEnriquecidosEncuestas
from shared.models.metadatos_entrevistas import MetadatosEnriquecidosEntrevistas
from shared.models.metadatos_pruebasestandarizadas import MetadatosEnriquecidosPruebas
from shared.models.rag_log import RagLog
from shared.models.raw_data import RawData
from shared.models.usuario import Usuario
from shared.models.variable import Variable

from services import vectores

logger = logging.getLogger("visualization-service")

TIPO_UI = {"encuesta": "Encuesta", "entrevista": "Entrevista", "prueba_estandarizada": "Prueba estandarizada"}
ESTADO_UI = {
    "recibido": "Borrador",
    "limpieza_en_proceso": "Borrador",
    "limpio": "Borrador",
    "metadatos_registrados": "En revisión",
    "estandarizado": "Estandarizado",
    "vectorizado": "Estandarizado",
    "error": "Borrador",
}
_NIVEL_POSGRADO = ("posgrado", "maestr", "doctor", "especialidad")
TABLAS_TIPO = {
    "encuesta": MetadatosEnriquecidosEncuestas,
    "entrevista": MetadatosEnriquecidosEntrevistas,
    "prueba_estandarizada": MetadatosEnriquecidosPruebas,
}
_ICONOS = (
    (r"satisf", "Smile"),
    (r"bienestar|emoc|salud|estr[eé]s", "Heart"),
    (r"empleab|laboral|trabaj|egres", "Briefcase"),
    (r"tecnolog|digital|virtual|en l[ií]nea", "Laptop"),
    (r"deserci|abandono|retenci|permanencia|eficiencia terminal", "Shield"),
    (r"rendimiento|desempe|calificaci|promedio|aprobaci", "Award"),
    (r"particip|convivencia|social|inclusi|equidad", "Users"),
    (r"infraestructura|instalaci|espacio", "Home"),
    (r"comunicaci|retroaliment|tutor", "MessageCircle"),
    (r"evalua|examen|prueba", "ClipboardCheck"),
    (r"docen|enseñ|aprend|lectur|acad[eé]m|curr", "BookOpen"),
    (r"tasa|[ií]ndice|porcentaje|proporci", "Calculator"),
)


def normalizar(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode("ascii").lower().strip()


def slug(texto: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", normalizar(texto)).strip("-")


def _texto(valor: Any) -> str:
    if valor is None:
        return ""
    if isinstance(valor, (list, tuple)):
        return ", ".join(t for t in (_texto(v) for v in valor) if t)
    return str(valor).strip()


# ── JSON estandarizado (con caché por ruta + mtime) ────────────────────────────

_json_cache: dict[str, tuple[float, dict[str, Any] | None]] = {}
_json_lock = threading.Lock()


def leer_json(ruta_json: str | None) -> dict[str, Any] | None:
    if not ruta_json:
        return None
    ruta = Path(ruta_json)
    if not ruta.is_absolute():
        ruta = settings.PROJECT_ROOT / ruta_json
    try:
        mtime = ruta.stat().st_mtime
    except OSError:
        return None
    clave = str(ruta)
    with _json_lock:
        guardado = _json_cache.get(clave)
        if guardado and guardado[0] == mtime:
            return guardado[1]
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("JSON ilegible %s: %s", ruta, exc)
        datos = None
    datos = datos if isinstance(datos, dict) else None
    with _json_lock:
        _json_cache[clave] = (mtime, datos)
    return datos


def preguntas_de(data: dict[str, Any] | None) -> list[dict[str, str]]:
    salida: list[dict[str, str]] = []
    for seccion in ((data or {}).get("instrument") or {}).get("sections") or []:
        if not isinstance(seccion, dict):
            continue
        for q in seccion.get("questions") or []:
            if isinstance(q, dict) and q.get("text"):
                salida.append(
                    {
                        "id": str(q.get("question_id") or ""),
                        "texto": str(q["text"]),
                        "tipo": str(q.get("type") or ""),
                        "seccion": str(seccion.get("name") or ""),
                    }
                )
    return salida


# ── Fichas ─────────────────────────────────────────────────────────────────────


@dataclass
class Ficha:
    id: str
    id_crudo: int
    id_instrumento: int | None
    titulo: str
    tipo: str
    tipo_backend: str
    nivel: str
    autorId: str
    autorNombre: str
    anio: int
    fecha: str
    kpis: list[str]
    reactivos: int
    estado: str
    estado_backend: str
    descripcion: str
    etiquetas: list[str]
    aprobado: bool
    indexado: bool
    institucion: str
    fecha_carga: datetime | None = None
    kpi_ids: set[int] = field(default_factory=set)
    kpi_scores: dict[int, float] = field(default_factory=dict)
    data: dict[str, Any] | None = None

    def dto(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "titulo": self.titulo,
            "tipo": self.tipo,
            "nivel": self.nivel,
            "autorId": self.autorId,
            "anio": self.anio,
            "fecha": self.fecha,
            "kpis": self.kpis,
            "reactivos": self.reactivos,
            "estado": self.estado,
            "descripcion": self.descripcion,
            "etiquetas": self.etiquetas,
            "autorNombre": self.autorNombre,
            "aprobado": self.aprobado,
            "indexado": self.indexado,
            "institucion": self.institucion,
        }


def _nivel(*textos: str) -> str:
    t = normalizar(" ".join(textos))
    return "Posgrado" if any(c in t for c in _NIVEL_POSGRADO) else "Licenciatura"


def _anio(dc_date: str, fecha_carga: datetime | None) -> int:
    if len(dc_date) >= 4 and dc_date[:4].isdigit():
        return int(dc_date[:4])
    return fecha_carga.year if isinstance(fecha_carga, datetime) else datetime.now().year


def cargar_fichas(db: Session) -> list[Ficha]:
    """Una ficha por instrumento de raw_data (con su último procesado)."""
    raws = db.query(RawData).order_by(RawData.id_crudo).all()
    if not raws:
        return []
    procesados: dict[int, InstrumentoProcesado] = {}
    for p in db.query(InstrumentoProcesado).order_by(InstrumentoProcesado.id_instrumento).all():
        procesados[p.id_crudo] = p  # el último gana
    usuarios = {u.usuario_id: u.nombre for u in db.query(Usuario.usuario_id, Usuario.nombre)}
    dcs = {m.id_crudo: m for m in db.query(MetadatosDC).all()}
    especificos: dict[int, Any] = {}
    for modelo in TABLAS_TIPO.values():
        for fila in db.query(modelo).all():
            especificos[fila.id_crudo] = fila

    kpis_por_procesado: dict[int, list[tuple[int, str, float | None]]] = {}
    filas_kpi = (
        db.query(KPIInferido.id_procesado, KPI.kpi_id, KPI.nombre_kpi, func.max(KpiInferidoChunk.score))
        .join(KPI, KPI.kpi_id == KPIInferido.kpi_id)
        .outerjoin(
            KpiInferidoChunk,
            (KpiInferidoChunk.id_procesado == KPIInferido.id_procesado)
            & (KpiInferidoChunk.kpi_id == KPIInferido.kpi_id),
        )
        .group_by(KPIInferido.id_procesado, KPI.kpi_id, KPI.nombre_kpi)
        .all()
    )
    for id_procesado, kpi_id, nombre, score in filas_kpi:
        kpis_por_procesado.setdefault(id_procesado, []).append((kpi_id, nombre, score))

    fichas: list[Ficha] = []
    for raw in raws:
        procesado = procesados.get(raw.id_crudo)
        data = leer_json(procesado.ruta_json if procesado else None)
        instrumento = (data or {}).get("instrument") or {}
        metadata = (data or {}).get("metadata") or {}
        dc_json = metadata.get("dublin_core") or {}
        esp_json = metadata.get("survey_specific") or {}
        dc = dcs.get(raw.id_crudo)
        esp = especificos.get(raw.id_crudo)

        def dc_campo(clave: str) -> str:
            return _texto(getattr(dc, f"dc_{clave}", None)) or _texto(dc_json.get(f"dc:{clave}"))

        def esp_campo(clave: str) -> Any:
            valor = getattr(esp, clave, None) if esp is not None else None
            return valor if valor not in (None, "", []) else esp_json.get(clave)

        kpis: list[str] = []
        kpi_ids: set[int] = set()
        kpi_scores: dict[int, float] = {}
        for k in (data or {}).get("inferred_kpis") or []:
            if isinstance(k, dict) and k.get("nombre_kpi"):
                kpis.append(str(k["nombre_kpi"]))
                if isinstance(k.get("kpi_id"), int):
                    kpi_ids.add(k["kpi_id"])
                    if isinstance(k.get("score"), (int, float)):
                        kpi_scores[k["kpi_id"]] = float(k["score"])
        if procesado is not None:
            for kpi_id, nombre, score in kpis_por_procesado.get(procesado.id_instrumento, []):
                kpi_ids.add(kpi_id)
                kpis.append(nombre)
                if score is not None:
                    kpi_scores[kpi_id] = float(score)
        kpis += [str(k) for k in ((data or {}).get("design_reference") or {}).get("kpi_hints") or []]
        kpis = list(dict.fromkeys(k for k in kpis if k))

        palabras = esp_campo("palabras_clave")
        etiquetas = [str(p) for p in palabras] if isinstance(palabras, list) and palabras else [
            t.strip() for t in dc_campo("subject").split(",") if t.strip()
        ]
        estado_backend = procesado.estado if procesado else "recibido"
        institucion = _texto(esp_campo("institucion"))
        if not institucion and dc_campo("publisher") and dc_campo("publisher") != settings.APP_NAME:
            institucion = dc_campo("publisher")
        fecha_carga = raw.fecha_carga if isinstance(raw.fecha_carga, datetime) else None

        fichas.append(
            Ficha(
                id=str(raw.id_crudo),
                id_crudo=raw.id_crudo,
                id_instrumento=procesado.id_instrumento if procesado else None,
                titulo=dc_campo("title") or _texto(instrumento.get("title")) or raw.nombre_archivo,
                tipo=TIPO_UI.get((raw.tipo_instrumento or "").lower(), "Encuesta"),
                tipo_backend=(raw.tipo_instrumento or "").lower(),
                nivel=_nivel(
                    dc_campo("coverage"),
                    _texto(esp_campo("poblacion_objetivo")),
                    _texto(esp_campo("nivel_educativo")),
                ),
                autorId=str(raw.id_owner),
                autorNombre=usuarios.get(raw.id_owner, ""),
                anio=_anio(dc_campo("date"), fecha_carga),
                fecha=(fecha_carga or datetime.now()).date().isoformat(),
                kpis=kpis,
                reactivos=len(preguntas_de(data)),
                estado=ESTADO_UI.get(estado_backend, "Borrador"),
                estado_backend=estado_backend,
                descripcion=dc_campo("description") or _texto(instrumento.get("objective")),
                etiquetas=etiquetas,
                aprobado=bool(procesado and (procesado.fecha_aprobado or estado_backend in ("estandarizado", "vectorizado"))),
                indexado=estado_backend == "vectorizado",
                institucion=institucion,
                fecha_carga=fecha_carga,
                kpi_ids=kpi_ids,
                kpi_scores=kpi_scores,
                data=data,
            )
        )
    return fichas


# ── Catálogo y filtros ─────────────────────────────────────────────────────────


@dataclass
class Filtros:
    q: str = ""
    tipo: str | None = None
    nivel: str | None = None
    kpi: str | None = None
    autor: str | None = None
    anio: int | None = None
    estado: str | None = None
    solo_propios: bool = False
    solo_aprobados: bool = False


def filtrar(fichas: list[Ficha], f: Filtros, usuario_id: int, kpi: "KpiRef | None" = None) -> list[Ficha]:
    """Aplica los filtros. `kpi` es el KPI ya resuelto de `f.kpi` (id o nombre)."""
    q = normalizar(f.q)
    salida = []
    for ficha in fichas:
        if q and not any(q in normalizar(t) for t in (ficha.titulo, ficha.descripcion, *ficha.etiquetas, *ficha.kpis)):
            continue
        if f.tipo and ficha.tipo != f.tipo and ficha.tipo_backend != f.tipo:
            continue
        if f.nivel and ficha.nivel != f.nivel:
            continue
        if f.kpi and (kpi is None or not asociado(ficha, kpi)):
            continue
        if f.autor and ficha.autorId != f.autor:
            continue
        if f.anio and ficha.anio != f.anio:
            continue
        if f.estado and ficha.estado != f.estado:
            continue
        if f.solo_propios and ficha.autorId != str(usuario_id):
            continue
        if f.solo_aprobados and not ficha.aprobado:
            continue
        salida.append(ficha)
    return salida


def facetas(fichas: list[Ficha]) -> dict[str, dict[str, int]]:
    kpis: Counter[str] = Counter()
    for f in fichas:
        kpis.update(f.kpis)
    return {
        "tipo": dict(Counter(f.tipo for f in fichas)),
        "nivel": dict(Counter(f.nivel for f in fichas)),
        "estado": dict(Counter(f.estado for f in fichas)),
        "anio": {str(a): n for a, n in sorted(Counter(f.anio for f in fichas).items(), reverse=True)},
        "autor": dict(Counter(f.autorNombre or f.autorId for f in fichas)),
        "kpi": dict(kpis.most_common()),
    }


def investigadores(db: Session, fichas: list[Ficha]) -> list[dict[str, str]]:
    instituciones: dict[str, Counter[str]] = {}
    for f in fichas:
        if f.institucion:
            instituciones.setdefault(f.autorId, Counter())[f.institucion] += 1
    salida = []
    for u in db.query(Usuario).order_by(Usuario.nombre).all():
        conteo = instituciones.get(str(u.usuario_id))
        salida.append(
            {
                "id": str(u.usuario_id),
                "nombre": u.nombre,
                "institucion": conteo.most_common(1)[0][0] if conteo else "",
            }
        )
    return salida


# ── KPIs ───────────────────────────────────────────────────────────────────────


@dataclass
class KpiRef:
    id: str
    kpi_id: int | None
    nombre: str
    descripcion: str = ""
    categoria: str = ""
    ambito: str = ""


def _icono(*textos: str) -> str:
    t = normalizar(" ".join(textos))
    for patron, icono in _ICONOS:
        if re.search(normalizar(patron), t):
            return icono
    return "BarChart2"


def asociado(ficha: Ficha, kpi: KpiRef) -> bool:
    if kpi.kpi_id is not None and kpi.kpi_id in ficha.kpi_ids:
        return True
    objetivo = normalizar(kpi.nombre)
    return any(normalizar(k) == objetivo for k in ficha.kpis)


def resolver_kpi(db: Session, kpi_id: str, fichas: list[Ficha]) -> KpiRef | None:
    """KPI por id numérico, por nombre o por su slug."""
    if kpi_id.isdigit():
        fila = db.get(KPI, int(kpi_id))
        if fila is not None:
            return KpiRef(str(fila.kpi_id), fila.kpi_id, fila.nombre_kpi, fila.descripcion or "", fila.categoria or "", fila.ambito or "")
    clave = slug(kpi_id)
    for fila in db.query(KPI).all():
        if slug(fila.nombre_kpi) == clave:
            return KpiRef(str(fila.kpi_id), fila.kpi_id, fila.nombre_kpi, fila.descripcion or "", fila.categoria or "", fila.ambito or "")
    for ficha in fichas:
        for nombre in ficha.kpis:
            if slug(nombre) == clave:
                return KpiRef(clave, None, nombre)
    return None


def catalogo_kpis(db: Session, fichas: list[Ficha]) -> list[dict[str, Any]]:
    variables: dict[int, list[Variable]] = {}
    for kpi_id, variable in db.query(KPIVariable.kpi_id, Variable).join(Variable, Variable.variable_id == KPIVariable.variable_id):
        variables.setdefault(kpi_id, []).append(variable)

    salida: list[dict[str, Any]] = []
    filas = db.query(KPI).order_by(KPI.nombre_kpi).all()
    refs = [
        (KpiRef(str(k.kpi_id), k.kpi_id, k.nombre_kpi, k.descripcion or "", k.categoria or "", k.ambito or ""), k)
        for k in filas
    ]
    if not refs:
        # Sin catálogo en BD: se usan los nombres de KPI declarados en los instrumentos.
        nombres = sorted({n for f in fichas for n in f.kpis}, key=normalizar)
        refs = [(KpiRef(slug(n), None, n), None) for n in nombres]

    for ref, fila in refs:
        n = sum(1 for f in fichas if asociado(f, ref))
        vars_kpi = variables.get(ref.kpi_id or -1, [])
        como = (
            "Variables: " + "; ".join(
                f"{v.nombre_variable}" + (f" ({v.unidad})" if v.unidad else "") + (f": {v.descripcion}" if v.descripcion else "")
                for v in vars_kpi
            )
            if vars_kpi
            else "Se estima con los reactivos de los instrumentos asociados, identificados por similitud semántica."
        )
        info = f"{n} instrumento{'s' if n != 1 else ''} del acervo asociado{'s' if n != 1 else ''} a este KPI."
        if fila is not None and fila.url_documentacion:
            info += f" Documentación: {fila.url_documentacion}"
        salida.append(
            {
                "id": ref.id,
                "nombre": ref.nombre,
                "descripcionCorta": (ref.descripcion[:137] + "…") if len(ref.descripcion) > 140 else ref.descripcion,
                "queEs": ref.descripcion,
                "queMide": " · ".join(p for p in (
                    f"Categoría: {ref.categoria}" if ref.categoria else "",
                    f"Ámbito: {ref.ambito}" if ref.ambito else "",
                ) if p),
                "comoSeMide": como,
                "formula": (fila.formula if fila is not None and fila.formula else ""),
                "infoGeneral": info,
                "icono": _icono(ref.nombre, ref.categoria, ref.ambito),
                "etiquetas": [e for e in (ref.categoria, ref.ambito) if e],
                "instrumentos": n,
                "categoria": ref.categoria,
                "ambito": ref.ambito,
            }
        )
    return salida


def _variacion(actual: int, previo: int) -> float:
    return round((actual - previo) * 100 / previo, 1) if previo else 0.0


def resumen(db: Session, fichas: list[Ficha]) -> list[dict[str, Any]]:
    ahora = datetime.now()
    hace_30, hace_60 = ahora - timedelta(days=30), ahora - timedelta(days=60)
    recientes = sum(1 for f in fichas if f.fecha_carga and f.fecha_carga >= hace_30)
    previos = sum(1 for f in fichas if f.fecha_carga and hace_60 <= f.fecha_carga < hace_30)
    aprobados = sum(1 for f in fichas if f.aprobado)
    total_kpis = db.query(func.count(KPI.kpi_id)).scalar() or 0
    con_evidencia = len({normalizar(n) for f in fichas for n in f.kpis})
    consultas = db.query(func.count(RagLog.rag_log_id)).filter(RagLog.timestamp >= hace_30).scalar() or 0
    consultas_previas = (
        db.query(func.count(RagLog.rag_log_id))
        .filter(RagLog.timestamp >= hace_60, RagLog.timestamp < hace_30)
        .scalar()
        or 0
    )
    pct = round(aprobados * 100 / len(fichas)) if fichas else 0
    return [
        {
            "id": "acervo",
            "etiqueta": "Instrumentos en el acervo",
            "valor": str(len(fichas)),
            "variacion": _variacion(recientes, previos),
            "detalle": f"{recientes} subido{'s' if recientes != 1 else ''} en los últimos 30 días",
        },
        {
            "id": "aprobados",
            "etiqueta": "Listos para el RAG",
            "valor": str(aprobados),
            "variacion": 0.0,
            "detalle": f"{pct}% con metadatos aprobados",
        },
        {
            "id": "kpis",
            "etiqueta": "KPIs con evidencia",
            "valor": str(con_evidencia),
            "variacion": 0.0,
            "detalle": f"de {total_kpis} en el catálogo" if total_kpis else "declarados en los instrumentos",
        },
        {
            "id": "consultas",
            "etiqueta": "Consultas al RAG (30 días)",
            "valor": str(consultas),
            "variacion": _variacion(consultas, consultas_previas),
            "detalle": "preguntas respondidas con tus instrumentos",
        },
        {
            "id": "reactivos",
            "etiqueta": "Reactivos analizados",
            "valor": str(sum(f.reactivos for f in fichas)),
            "variacion": 0.0,
            "detalle": "en instrumentos estandarizados",
        },
    ]


# ── Evidencia: qué preguntas miden un KPI ──────────────────────────────────────

_kpi_vectores: dict[str, list[float]] = {}


def vector_kpi(kpi: KpiRef) -> list[float] | None:
    """Vector del KPI: el de la colección `kpis` (analysis-service) o se calcula."""
    if kpi.id in _kpi_vectores:
        return _kpi_vectores[kpi.id]
    vector = None
    try:
        if kpi.kpi_id is not None:
            col = vectores.coleccion_existente(settings.CHROMA_COLLECTION_KPIS)
            if col is not None:
                res = col.get(ids=[str(kpi.kpi_id)], include=["embeddings"])
                embs = res.get("embeddings")
                if embs is not None and len(embs) > 0:
                    vector = vectores.a_lista(embs[0])
        if vector is None:
            texto = ". ".join(p for p in (kpi.nombre, kpi.descripcion, kpi.categoria, kpi.ambito) if p)
            vector = vectores.embed_text(texto)
    except Exception as exc:  # noqa: BLE001 - Chroma o modelo no disponibles
        logger.warning("Sin vector para el KPI %s: %s", kpi.nombre, exc)
        return None
    _kpi_vectores[kpi.id] = vector
    return vector


def preguntas_que_miden(kpi: KpiRef, instrumento_id: str, n: int = 3) -> list[dict[str, Any]]:
    """Preguntas del instrumento más cercanas al KPI en el espacio vectorial."""
    vector = vector_kpi(kpi)
    if vector is None:
        return []
    try:
        col = vectores.coleccion_existente(settings.CHROMA_COLLECTION_INSTRUMENTOS)
        if col is None:
            return []
        res = col.query(
            query_embeddings=[vector],
            n_results=n,
            where={"$and": [{"instrumentoId": instrumento_id}, {"seccion": "pregunta"}]},
            include=["metadatas", "documents", "distances"],
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo consultar la evidencia del KPI %s: %s", kpi.nombre, exc)
        return []
    metas = (res.get("metadatas") or [[]])[0]
    docs = (res.get("documents") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    salida = []
    for meta, doc, dist in zip(metas, docs, dists):
        meta = meta or {}
        salida.append(
            {
                "preguntaId": str(meta.get("preguntaId") or ""),
                "texto": str(meta.get("pregunta") or doc or ""),
                "score": round(max(0.0, min(1.0, 1.0 - float(dist))), 4),
            }
        )
    return salida


def datos_grafica(db: Session, fichas: list[Ficha], kpi_id: str, ids: list[str]) -> dict[str, Any] | None:
    kpi = resolver_kpi(db, kpi_id, fichas)
    if kpi is None:
        return None
    fuentes = [f for f in fichas if not ids or f.id in ids]
    asociadas = [f for f in fuentes if asociado(f, kpi)]

    por_nivel: Counter[str] = Counter()
    por_anio: Counter[int] = Counter()
    por_tipo: Counter[str] = Counter()
    for f in asociadas:
        por_nivel[f.nivel] += f.reactivos
        por_anio[f.anio] += f.reactivos
        por_tipo[f.tipo] += 1

    instrumentos = []
    for f in asociadas:
        aceptado = kpi.kpi_id is not None and kpi.kpi_id in f.kpi_ids
        instrumentos.append(
            {
                "instrumentoId": f.id,
                "titulo": f.titulo,
                "tipo": f.tipo,
                "score": f.kpi_scores.get(kpi.kpi_id) if kpi.kpi_id is not None else None,
                "origen": "aceptado" if aceptado else "referencia",
                "preguntas": preguntas_que_miden(kpi, f.id) if f.indexado else [],
            }
        )
    return {
        "kpiId": kpi.id,
        "porNivel": [{"etiqueta": k, "valor": v} for k, v in por_nivel.items()],
        "porAnio": [{"etiqueta": str(k), "valor": v} for k, v in sorted(por_anio.items())],
        "porTipo": [{"etiqueta": k, "valor": v} for k, v in por_tipo.items()],
        "fuentesConteo": len(asociadas),
        "instrumentos": instrumentos,
    }


def kpis_de_instrumento(db: Session, ficha: Ficha) -> list[dict[str, Any]]:
    """KPIs asociados a un instrumento y las preguntas que mejor los miden."""
    refs: dict[str, tuple[KpiRef, str]] = {}
    filas = {k.kpi_id: k for k in db.query(KPI).all()}
    for kpi_id in ficha.kpi_ids:
        if kpi_id in filas:
            k = filas[kpi_id]
            refs[normalizar(k.nombre_kpi)] = (
                KpiRef(str(k.kpi_id), k.kpi_id, k.nombre_kpi, k.descripcion or "", k.categoria or "", k.ambito or ""),
                "aceptado",
            )
    por_nombre = {normalizar(k.nombre_kpi): k for k in filas.values()}
    for nombre in ficha.kpis:
        clave = normalizar(nombre)
        if clave in refs:
            continue
        k = por_nombre.get(clave)
        ref = (
            KpiRef(str(k.kpi_id), k.kpi_id, k.nombre_kpi, k.descripcion or "", k.categoria or "", k.ambito or "")
            if k is not None
            else KpiRef(slug(nombre), None, nombre)
        )
        refs[clave] = (ref, "referencia")
    return [
        {
            "kpiId": ref.id,
            "nombre": ref.nombre,
            "score": ficha.kpi_scores.get(ref.kpi_id) if ref.kpi_id is not None else None,
            "origen": origen,
            "preguntas": preguntas_que_miden(ref, ficha.id) if ficha.indexado else [],
        }
        for ref, origen in refs.values()
    ]


# ── Instrumentos relacionados ──────────────────────────────────────────────────


def _vectores_encabezado(ids: list[str]) -> dict[str, list[float]]:
    """Vector del chunk 0 (encabezado) de cada instrumento en Chroma."""
    try:
        col = vectores.coleccion_existente(settings.CHROMA_COLLECTION_INSTRUMENTOS)
        if col is None or not ids:
            return {}
        res = col.get(ids=[f"inst-{i}-0" for i in ids], include=["embeddings"])
    except Exception as exc:  # noqa: BLE001
        logger.warning("Sin vectores de encabezado: %s", exc)
        return {}
    salida: dict[str, list[float]] = {}
    embs = res.get("embeddings")
    for pid, emb in zip(res.get("ids") or [], embs if embs is not None else []):
        vector = vectores.a_lista(emb)
        if vector:
            salida[pid.split("-")[1]] = vector
    return salida


def _coseno(a: list[float], b: list[float]) -> float:
    import math

    num = sum(x * y for x, y in zip(a, b))
    den = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return num / den if den else 0.0


def _similitud_lexica(a: str, b: str) -> float:
    pa = {w for w in re.findall(r"[a-z]{5,}", normalizar(a))}
    pb = {w for w in re.findall(r"[a-z]{5,}", normalizar(b))}
    return len(pa & pb) / max(len(pa | pb), 1)


UMBRAL_SEMANTICO = 0.55
UMBRAL_LEXICO = 0.2


def relacionados(fichas: list[Ficha], ids: list[str], autor_id: str) -> list[dict[str, Any]]:
    seleccion = [f for f in fichas if f.id in ids]
    candidatos = [f for f in fichas if f.autorId != autor_id and f.id not in ids]
    if not seleccion or not candidatos:
        return []
    vecs = _vectores_encabezado([f.id for f in seleccion + candidatos])

    resultados = []
    for cand in candidatos:
        razones: list[dict[str, str]] = []
        coincide: list[str] = []
        mejor_sim: float | None = None
        for propia in seleccion:
            hubo = False
            kpis_cand = {normalizar(k): k for k in cand.kpis}
            compartidos = kpis_cand.keys() & {normalizar(k) for k in propia.kpis}
            for clave in sorted(compartidos):
                etiqueta = f"Mismo KPI: {kpis_cand[clave]}"
                if not any(r["etiqueta"] == etiqueta for r in razones):
                    razones.append({"tipo": "kpi", "etiqueta": etiqueta})
                hubo = True
            if propia.nivel == cand.nivel:
                if not any(r["tipo"] == "nivel" for r in razones):
                    razones.append({"tipo": "nivel", "etiqueta": f"Mismo nivel: {cand.nivel}"})
                hubo = True
            if propia.id in vecs and cand.id in vecs:
                sim, umbral = _coseno(vecs[propia.id], vecs[cand.id]), UMBRAL_SEMANTICO
            else:
                sim = _similitud_lexica(
                    f"{propia.titulo} {propia.descripcion}", f"{cand.titulo} {cand.descripcion}"
                )
                umbral = UMBRAL_LEXICO
            if sim >= umbral:
                mejor_sim = max(mejor_sim or 0.0, sim)
                hubo = True
            if hubo and propia.id not in coincide:
                coincide.append(propia.id)
        if mejor_sim is not None:
            razones.append({"tipo": "descripcion", "etiqueta": f"Descripción similar: {round(mejor_sim * 100)}%"})
        if not razones:
            continue
        criterios = len({r["tipo"] for r in razones})
        nivel = "alta" if criterios >= 3 else "media" if criterios == 2 else "baja"
        resultados.append(
            {
                "instrumento": cand.dto(),
                "nivel": nivel,
                "coincideCon": coincide,
                "razones": razones,
                "similitud": round(mejor_sim, 4) if mejor_sim is not None else None,
            }
        )
    orden = {"alta": 0, "media": 1, "baja": 2}
    resultados.sort(key=lambda r: (orden[r["nivel"]], -(r["similitud"] or 0), r["instrumento"]["titulo"]))
    return resultados
