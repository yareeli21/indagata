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


class TiempoPasoOut(BaseModel):
    paso: str
    etiqueta: str
    servicio: str
    inicio: datetime
    fin: datetime
    duracion_ms: int
    segundo_plano: bool = False  # corre después de responder (no lo espera la persona)
    detalle: dict[str, Any] = Field(default_factory=dict)


class LatenciaChatOut(BaseModel):
    consultas: int
    p50_ms: int | None = None
    p95_ms: int | None = None


class TiemposOut(BaseModel):
    """Tiempo de cómputo de cada paso del procesamiento de un instrumento (tabla tiempo_proceso)."""

    id_crudo: int
    pasos: list[TiempoPasoOut]
    computo_ms: int  # suma de los pasos: lo que tardaría la máquina sin esperas
    punta_a_punta_ms: int | None  # de la carga a la última operación: incluye el tiempo de decisión de la persona
    chat: LatenciaChatOut


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


class MensajeHistorial(BaseModel):
    """Un mensaje previo del chat: la interpretación lo usa para resolver «¿y de ellos…?»."""

    rol: Literal["usuario", "asistente"]
    texto: str = Field(max_length=4000)
    # 4 nov: la consulta (rag_log) de una respuesta del asistente; de ahí se lee de qué trató (tema anterior).
    consultaId: int | None = None


class ChatRequest(BaseModel):
    investigacionId: str = ""
    pregunta: str = Field(min_length=1, max_length=4000)
    instrumentoIds: list[str] | None = None
    modelo: str | None = None
    stream: bool = True
    top_k: int = 6
    contexto: ContextoInvestigacion | None = None
    # Para la evaluación (tools/rag/evaluar_banco.py): sin caché, las repeticiones y paráfrasis miden de
    # verdad la estabilidad y la latencia; sin métricas, las paráfrasis no llenan la cola del juez.
    usarCache: bool = True
    calcularMetricas: bool = True
    # Para el conjunto de regresión (tools/rag/regresion): False responde con el flujo anterior (solo reglas), para
    # comparar antes y después del rediseño sin reiniciar el servicio.
    usarInterpretacion: bool = True
    # Mensajes recientes de la sesión (los más nuevos al final); solo se usan los últimos 4.
    historial: list[MensajeHistorial] = Field(default_factory=list, max_length=20)

    @field_validator("top_k")
    @classmethod
    def _limitar_top_k(cls, v: int) -> int:
        """Se normaliza al rango [1, 8] en lugar de rechazarse (cabe en num_ctx)."""
        return max(1, min(8, v))


class InterpretarOut(BaseModel):
    """Plan de la etapa de interpretación (POST /rag/interpretar, para revisar y depurar)."""

    plan: dict | None
    correcciones: list[str]
    intentos: int
    ms: int
    error: str
    # Etapa 2: resultado calculado del plan por instrumento (texto con criterio, cifras y tablas) y su tiempo.
    ejecucion: list[str] = []
    ms_ejecucion: int = 0


class PasajeOut(BaseModel):
    """Un fragmento del instrumento que se le dio al modelo para responder (trazabilidad de la fuente).

    `chunkIndex` es su posición en el documento indexado: con él la UI abre
    `GET /visualizacion/instrumentos/{id}/documento` justo en ese punto.
    """

    seccion: str  # encabezado | pregunta | respondente | reactivo | alumno | intercambio | kpi | contenido
    etiqueta: str  # «Ficha», «Pregunta p04», «Respondente R017 · p04»…
    texto: str  # el fragmento tal como está en el documento indexado
    score: float | None = None  # similitud con la pregunta (None: se agregó sin búsqueda, p. ej. la ficha)
    chunkIndex: int | None = None
    preguntaId: str = ""
    respondenteId: str = ""


class FuenteChatOut(BaseModel):
    numero: int  # el n de las citas [Fuente n] de la respuesta
    instrumentoId: str
    titulo: str
    tipo: TipoInstrumento
    investigador: str
    kpis: list[str]
    fragmento: str
    pasajes: list[PasajeOut] = []  # de dónde se recuperó la información, en orden de similitud
    # La mayor similitud de este instrumento con la pregunta (0–1), aunque la respuesta sea un cálculo sin pasajes.
    similitud: float | None = None


class FragmentoDocumentoOut(BaseModel):
    chunkIndex: int
    seccion: str
    etiqueta: str
    texto: str
    preguntaId: str = ""
    respondenteId: str = ""


class DocumentoFuenteOut(BaseModel):
    """Un tramo del documento indexado de un instrumento (lo que el RAG puede recuperar), en orden."""

    instrumentoId: str
    titulo: str
    tipo: str
    origen: str  # documento (documento final vigente) | json_tecnico
    total: int  # fragmentos del documento completo
    desde: int
    hasta: int  # exclusivo
    fragmentos: list[FragmentoDocumentoOut]


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


class FragmentoRecuperadoOut(BaseModel):
    """Un fragmento que llegó a la respuesta y cómo lo encontró la búsqueda (services/metricas_respuesta.py)."""

    etiqueta: str
    instrumentoId: str = ""
    similitud: float | None = None  # coseno del embedding con la pregunta
    coincidencia: float | None = None  # proporción de las palabras de la pregunta que contiene
    rangoSemantico: int | None = None  # lugar en la búsqueda por significado (None: no apareció)
    rangoPalabras: int | None = None  # lugar en la búsqueda por palabras
    paso: Literal["significado", "palabras", "ambos", "contexto"]


class RecuperacionOut(BaseModel):
    modo: Literal["hibrida", "semantica"]
    umbral: float
    coberturaMinima: float
    similitudMaxima: float | None = None
    similitudPromedio: float | None = None
    fragmentos: list[FragmentoRecuperadoOut] = []


class FundamentacionOut(BaseModel):
    """Oraciones de la respuesta respaldadas por lo recuperado (fidelidad sin juez)."""

    oraciones: int
    respaldadas: int | None = None
    proporcion: float | None = None
    sinRespaldo: list[str] = []


class CitasOut(BaseModel):
    oraciones: int
    conCita: int
    proporcion: float | None = None
    fuentesCitadas: list[int] = []
    citasInvalidas: list[int] = []


class IndicadoresOut(BaseModel):
    """Indicadores del sistema de una respuesta: deterministas, sin juez (services/indicadores.py)."""

    modelo: str | None = None
    intencion: str | None = None
    ruta: str | None = None
    decision: str | None = None
    respuesta: Literal["redactada", "presentacion_fija", "plantilla"]
    plantilla: str | None = None
    plantillaDetalle: str | None = None
    regeneraciones: int | None = None  # None: no hubo verificación de una redacción
    primerFallo: str | None = None
    verificacion: str | None = None
    cifrasTotal: int | None = None  # solo en respuestas redactadas por el modelo
    cifrasConRespaldo: int | None = None
    cifrasSinRespaldo: list[str] = []
    idsInventados: list[str] = []
    fragmentosRag: list[str] = []  # partes del instrumento que recuperó Chroma y vio el modelo
    tiempos: dict[str, int] = {}
    latenciaMs: int | None = None
    # «Ver métricas» (11 nov): recuperación, fundamentación y citas de la respuesta, sin juez.
    recuperacion: RecuperacionOut | None = None
    fundamentacion: FundamentacionOut | None = None
    citas: CitasOut | None = None


class JuezOut(BaseModel):
    """La evaluación de una respuesta por un juez (experimento redactor × juez)."""

    modeloJuez: str
    estado: str
    fidelidad: float | None = None
    relevancia: float | None = None
    precisionContexto: float | None = None
    fecha: datetime | None = None


class JuezFableOut(BaseModel):
    """Evaluación de una respuesta por el juez Claude Fable 5.2: seis métricas tipo RAGAS (services/juez_fable.py).

    `sensibilidadRuido` es la única donde MENOR es mejor. Recuerdo, ruido y corrección factual se comparan contra una
    respuesta de referencia que escribe el mismo juez sin ver la del sistema (`respuestaReferencia`).
    """

    modelo: str
    modeloReal: str | None = None  # el que juzgó de verdad (distinto si Fable declinó y respondió el respaldo)
    fallback: bool = False
    estado: Literal["calculando", "listo", "omitida", "error"]
    motivo: str | None = None
    fecha: datetime | None = None
    precisionContexto: float | None = None
    recuerdoContexto: float | None = None
    fidelidad: float | None = None
    relevancia: float | None = None
    sensibilidadRuido: float | None = None
    correccionFactual: float | None = None
    correccionPrecision: float | None = None
    correccionRecuerdo: float | None = None
    noSustentadas: list[str] = []  # afirmaciones de la respuesta sin respaldo en lo recuperado
    incorrectas: list[str] = []  # afirmaciones de la respuesta que la referencia no respalda
    respuestaReferencia: str | None = None
    afirmacionesReferencia: list[str] = []
    referenciaNoCubierta: list[int] = []  # números (1..n) de afirmaciones de referencia que la respuesta omitió
    origenReferencia: str | None = None  # contexto_ampliado | solo_contexto_usado
    preguntasGeneradas: list[str] = []


class CalificacionIn(BaseModel):
    """Calificación humana de una respuesta."""

    calificacion: int = Field(ge=0, le=2)  # 0 mal, 1 parcial, 2 bien
    entendio: bool | None = None  # ¿entendió lo que se pidió?
    fundamenta: bool | None = None  # None = no aplica
    comentario: str | None = Field(default=None, max_length=2000)


class CalificacionOut(CalificacionIn):
    fecha: datetime | None = None


class MetricasConsultaOut(BaseModel):
    """Métricas de una respuesta del chat: las del juez (aproximadas), los indicadores sin juez y la calificación
    humana."""

    consultaId: int
    estado: Literal["pendiente", "calculando", "listo", "omitida", "error", "calculada"]
    motivo: str | None = None
    fidelidad: float | None = None  # afirmaciones sustentadas por el contexto
    relevancia: float | None = None  # qué tan directo contesta la pregunta
    precisionContexto: float | None = None  # si los fragmentos útiles estaban primero
    noSustentadas: list[str] = []
    modeloJuez: str | None = None
    fecha: datetime | None = None
    indicadores: IndicadoresOut | None = None
    jueces: list[JuezOut] = []
    juezFable: JuezFableOut | None = None
    calificacion: CalificacionOut | None = None


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
