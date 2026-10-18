"""DTOs (Pydantic v2) del visualization-service.

Las formas espejan los tipos del frontend (`pixel-perfect-pixel/src/types`):
`Instrumento`, `Investigador`, `InstrumentoRelacionado`, `KpiCatalogo`, `Kpi`,
`DatosGrafica` y `FuenteChat`, más campos informativos que la UI puede ignorar.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

TipoInstrumento = Literal["Encuesta", "Entrevista", "Prueba estandarizada"]


# ── Catálogo ───────────────────────────────────────────────────────────────────


class InstrumentoCatalogo(BaseModel):
    id: str
    titulo: str
    tipo: TipoInstrumento
    nivel: Literal["Licenciatura", "Posgrado"]
    autorId: str
    anio: int
    fecha: str
    kpis: list[str]
    reactivos: int
    estado: Literal["Borrador", "En revisión", "Estandarizado"]
    descripcion: str
    etiquetas: list[str]
    autorNombre: str = ""
    aprobado: bool = False
    indexado: bool = False
    institucion: str = ""


class CatalogoResponse(BaseModel):
    total: int
    items: list[InstrumentoCatalogo]
    facetas: dict[str, dict[str, int]]


class PreguntaOut(BaseModel):
    id: str
    texto: str
    tipo: str = ""
    seccion: str = ""


class InstrumentoDetalle(BaseModel):
    instrumento: InstrumentoCatalogo
    dublin_core: dict[str, Any]
    enriquecidos: dict[str, Any]
    preguntas: list[PreguntaOut]
    estadisticas: dict[str, Any] = Field(default_factory=dict)


class InvestigadorOut(BaseModel):
    id: str
    nombre: str
    institucion: str = ""


class RelacionadosRequest(BaseModel):
    ids: list[str] = Field(min_length=1)
    autorId: str | None = None


class RazonOut(BaseModel):
    tipo: Literal["kpi", "nivel", "descripcion"]
    etiqueta: str


class RelacionadoOut(BaseModel):
    instrumento: InstrumentoCatalogo
    nivel: Literal["alta", "media", "baja"]
    coincideCon: list[str]
    razones: list[RazonOut]
    similitud: float | None = None


# ── KPIs ───────────────────────────────────────────────────────────────────────


class FuenteKpiOut(BaseModel):
    """Fuente de referencia verificada de un KPI (tabla kpi_fuente)."""

    organismo: str
    titulo: str
    url: str
    anio: int | None = None
    nota: str | None = None


class KpiCatalogoOut(BaseModel):
    id: str
    nombre: str
    descripcionCorta: str
    queEs: str
    queMide: str
    comoSeMide: str
    formula: str
    infoGeneral: str
    icono: str
    etiquetas: list[str]
    instrumentos: int = 0
    categoria: str = ""
    ambito: str = ""
    fuentes: list[FuenteKpiOut] = []


class KpiResumenOut(BaseModel):
    id: str
    etiqueta: str
    valor: str
    variacion: float
    detalle: str


class DatosGraficaRequest(BaseModel):
    instrumentoIds: list[str] = Field(default_factory=list)


class PuntoDato(BaseModel):
    etiqueta: str
    valor: float


class PreguntaEvidencia(BaseModel):
    preguntaId: str
    texto: str
    score: float


class InstrumentoEvidencia(BaseModel):
    instrumentoId: str
    titulo: str
    tipo: TipoInstrumento
    score: float | None = None
    origen: Literal["aceptado", "referencia"]
    preguntas: list[PreguntaEvidencia]


class DatosGraficaOut(BaseModel):
    kpiId: str
    porNivel: list[PuntoDato]
    porAnio: list[PuntoDato]
    porTipo: list[PuntoDato]
    fuentesConteo: int
    instrumentos: list[InstrumentoEvidencia]


class KpiDeInstrumentoOut(BaseModel):
    kpiId: str
    nombre: str
    score: float | None = None
    origen: Literal["aceptado", "referencia"]
    preguntas: list[PreguntaEvidencia]


# ── RAG ────────────────────────────────────────────────────────────────────────


class IndexRequest(BaseModel):
    investigacionId: str = Field(min_length=1)
    instrumentoIds: list[str] = Field(min_length=1)
    reindexar: bool = False


class IndexInstrumentoResultado(BaseModel):
    instrumentoId: str
    chunks: int
    estado: Literal["indexado", "omitido"]
    motivo: str | None = None


class IndexResponse(BaseModel):
    coleccion: str
    total_chunks: int
    instrumentos: list[IndexInstrumentoResultado]
    mensaje: str


class ContextoInvestigacion(BaseModel):
    objetivo: str = ""
    poblacion: str = ""
    nivel: str = ""
    pregunta: str = ""


class ChatRequest(BaseModel):
    investigacionId: str = ""
    pregunta: str = Field(min_length=1, max_length=4000)
    instrumentoIds: list[str] | None = None
    modelo: str | None = None
    stream: bool = True
    top_k: int = 6
    contexto: ContextoInvestigacion | None = None

    @field_validator("top_k")
    @classmethod
    def _limitar_top_k(cls, v: int) -> int:
        """Se normaliza al rango [1, 8] en lugar de rechazarse (cabe en num_ctx)."""
        return max(1, min(8, v))


class FuenteChatOut(BaseModel):
    numero: int  # el n de las citas [Fuente n] de la respuesta
    instrumentoId: str
    titulo: str
    tipo: TipoInstrumento
    investigador: str
    kpis: list[str]
    fragmento: str


class ReferenciaChatOut(BaseModel):
    """Entrada curada que respalda la respuesta: glosario metodológico o ayuda de la plataforma."""

    tipo: Literal["glosario", "ayuda", "fuente_kpi"]
    titulo: str
    texto: str
    url: str = ""  # fuente_kpi: enlace a la fuente de referencia verificada


class ChatResponse(BaseModel):
    respuesta: str
    fuentes: list[FuenteChatOut]
    modelo: str
    degradado: bool = False
    referencias: list[ReferenciaChatOut] = []
    # Dominio acotado y enrutador (también en rag_log).
    decision: str = "dentro"  # dentro | fuera | privacidad | manipulacion | sin_informacion | ayuda
    ruta: str | None = None  # semantica | estructurada | mixta | ayuda
    consultaId: int | None = None  # rag_log_id (para pedir las métricas de esta respuesta)
    enCache: bool = False  # se reutilizó la respuesta guardada de una consulta idéntica


class MetricasConsultaOut(BaseModel):
    """Métricas automáticas de una respuesta del chat (juez local: evaluación aproximada)."""

    consultaId: int
    estado: Literal["calculando", "listo", "omitida", "error"]
    motivo: str | None = None
    fidelidad: float | None = None  # afirmaciones sustentadas por el contexto
    relevancia: float | None = None  # qué tan directo contesta la pregunta
    precisionContexto: float | None = None  # si los fragmentos útiles estaban primero
    noSustentadas: list[str] = []
    modeloJuez: str | None = None
    fecha: datetime | None = None


# ── Espacio vectorial ──────────────────────────────────────────────────────────

TipoPunto = Literal["kpi", "instrumento", "chunk"]


class PcaOut(BaseModel):
    varianza: list[float]
    varianzaTotal: float
    varianzaBaja: bool


class ClusterOut(BaseModel):
    id: int
    etiqueta: str
    representativos: list[str]
    tamano: int


class FuenteChunksOut(BaseModel):
    nombre: str
    provisional: bool


class ConteosEspacioOut(BaseModel):
    kpis: int
    instrumentos: int
    chunks: int


class PuntoEspacioOut(BaseModel):
    id: str
    tipo: TipoPunto
    ref: str
    etiqueta: str
    resumen: str
    detalle: str
    x: float
    y: float
    clusterId: int | None = None
    instrumentoId: str | None = None
    origenVector: Literal["summary", "calculado"] | None = None


class MapaEspacioOut(BaseModel):
    modelo: str
    dimension: int
    pca: PcaOut
    clusters: list[ClusterOut]
    fuenteChunks: FuenteChunksOut
    conteos: ConteosEspacioOut
    puntos: list[PuntoEspacioOut]
    generadoEn: str
    # True si cada grupo se centró en su propio centroide antes del PCA.
    alineado: bool = False


class VecinoOut(BaseModel):
    """Punto cercano al origen; `similitud` = coseno en el espacio original."""

    id: str
    tipo: TipoPunto
    ref: str
    etiqueta: str
    similitud: float
    clusterId: int | None = None
    instrumentoId: str | None = None
    # Solo chunks: texto completo y sección.
    texto: str | None = None
    seccion: str | None = None


class OrigenVecinosOut(BaseModel):
    id: str
    tipo: TipoPunto
    ref: str
    etiqueta: str
    clusterId: int | None = None
    # Solo chunks: texto completo y sección.
    texto: str | None = None
    seccion: str | None = None


class VecinosEspacioOut(BaseModel):
    origen: OrigenVecinosOut
    kpis: list[VecinoOut]
    instrumentos: list[VecinoOut]
    chunks: list[VecinoOut]
    fuenteChunks: FuenteChunksOut


class BusquedaEspacioIn(BaseModel):
    texto: str = Field(min_length=3, max_length=300)
    k: int = Field(6, ge=1, le=30)


class PosicionOut(BaseModel):
    x: float
    y: float


class BusquedaEspacioOut(BaseModel):
    texto: str
    # Posición de la consulta en la vista original y en la alineada.
    posicion: PosicionOut
    posicionAlineada: PosicionOut
    # Grupo con cuyo centroide se centró la consulta en la vista alineada.
    grupoReferencia: Literal["kpi", "instrumento", "chunk"] | None = None
    kpis: list[VecinoOut]
    instrumentos: list[VecinoOut]
    chunks: list[VecinoOut]
    fuenteChunks: FuenteChunksOut
