export const NIVELES_EDUCATIVOS = ["Licenciatura", "Posgrado"] as const;

export type NivelEducativo = (typeof NIVELES_EDUCATIVOS)[number];

export const TIPOS_INSTRUMENTO = ["Encuesta", "Entrevista", "Prueba estandarizada"] as const;
export type TipoInstrumento = (typeof TIPOS_INSTRUMENTO)[number];

export const ESTADOS_INSTRUMENTO = ["Borrador", "En revisión", "Estandarizado"] as const;
export type EstadoInstrumento = (typeof ESTADOS_INSTRUMENTO)[number];

export type Rol = "Investigador" | "Administrador";

export interface Usuario {
  id: string;
  usuario: string;
  nombre: string;
  rol: Rol;
  investigadorId: string;
}

export interface Investigador {
  id: string;
  nombre: string;
  institucion: string;
}

export interface Investigacion {
  id: string;
  nombre: string;
  propietarioId: string;
}

export interface Instrumento {
  id: string;
  titulo: string;
  tipo: TipoInstrumento;
  nivel: NivelEducativo;
  autorId: string;
  anio: number;
  /** ISO AAAA-MM-DD */
  fecha: string;
  kpis: string[];
  reactivos: number;
  estado: EstadoInstrumento;
  descripcion: string;
  etiquetas: string[];
}

export interface Kpi {
  id: string;
  etiqueta: string;
  valor: string;
  variacion: number;
  detalle: string;
}

export interface Noticia {
  id: string;
  titulo: string;
  fecha: string;
  resumen: string;
}

export interface CambioLimpieza {
  campo: string;
  antes: string;
  despues: string;
}

export interface ReporteLimpieza {
  duplicadosEliminados: number;
  nulosTratados: number;
  columnasNormalizadas: number;
  cambios: CambioLimpieza[];
}

/** Los 13 campos Dublin Core de `metadatos_dc` (la cobertura se captura como
 * nivel educativo + detalle y se guarda como «Nivel — detalle»). */
export interface DublinCore {
  titulo: string;
  creador: string;
  tema: string;
  descripcion: string;
  tipo: string;
  fecha: string;
  /** Código ISO 639-1, p. ej. «es». */
  idioma: string;
  cobertura: NivelEducativo | "";
  coberturaDetalle: string;
  editor: string;
  derechos: string;
  formato: string;
  fuente: string;
  relacion: string;
}

/** Metadatos específicos del tipo, como texto de formulario (listas separadas
 * por comas; reactivos por sección como «Sección: número» por línea). */
export type MetadatosTipo = Record<string, string>;

/** De dónde salió un metadato propuesto por el metadata-service. */
export type OrigenMetadato = "automatico" | "archivo" | "inferido" | "llm" | "aprobado";

export interface KpiSugerido {
  id: string;
  nombre: string;
  coincidencia: number;
}

export type FormatoDescarga = "crudo" | "json" | "sav";

export type NivelCoincidencia = "alta" | "media" | "baja";

export interface RazonCoincidencia {
  tipo: "kpi" | "nivel" | "descripcion";
  etiqueta: string;
}

export interface InstrumentoRelacionado {
  instrumento: Instrumento;
  nivel: NivelCoincidencia;
  coincideCon: string[];
  razones: RazonCoincidencia[];
}

export type ModeloLLM = "llama3.2:3b";

export interface ContextoInvestigacion {
  objetivo: string;
  poblacion: string;
  nivel: NivelEducativo;
  pregunta: string;
}

export interface FuenteChat {
  instrumentoId: string;
  titulo: string;
  tipo: TipoInstrumento;
  investigador: string;
  kpis: string[];
  fragmento: string;
}

export type RolMensaje = "usuario" | "asistente";

export interface Mensaje {
  id: string;
  rol: RolMensaje;
  contenido: string;
  /** Solo en mensajes del asistente */
  fuentes?: FuenteChat[];
  /** true mientras se está generando (streaming) */
  generando?: boolean;
}

// ── KPIs ──────────────────────────────────────────────────────────────────────

export interface KpiCatalogo {
  id: string;
  nombre: string;
  descripcionCorta: string;
  queEs: string;
  queMide: string;
  comoSeMide: string;
  formula: string;
  infoGeneral: string;
  /** Nombre del ícono de Lucide que representa este KPI */
  icono: string;
  /** Etiquetas de búsqueda */
  etiquetas: string[];
}

export interface PuntoDato {
  etiqueta: string;
  valor: number;
}

export interface DatosGrafica {
  kpiId: string;
  /** Datos para gráfica de barras: por nivel educativo */
  porNivel: PuntoDato[];
  /** Datos para gráfica de líneas: por año */
  porAnio: PuntoDato[];
  /** Datos para gráfica de dona: por tipo de instrumento */
  porTipo: PuntoDato[];
  /** Número de instrumentos en las fuentes que cubren este KPI */
  fuentesConteo: number;
  /** Instrumentos que miden el KPI y sus preguntas más relacionadas */
  instrumentos: EvidenciaKpiInstrumento[];
}

/** Pregunta de un instrumento cercana a un KPI en el espacio vectorial. */
export interface PreguntaEvidencia {
  preguntaId: string;
  texto: string;
  /** Similitud 0–1 entre la pregunta y el KPI */
  score: number;
}

/** «aceptado»: el autor lo confirmó; «referencia»: declarado en el diseño del instrumento. */
export type OrigenKpi = "aceptado" | "referencia";

export interface EvidenciaKpiInstrumento {
  instrumentoId: string;
  titulo: string;
  tipo: TipoInstrumento;
  score: number | null;
  origen: OrigenKpi;
  preguntas: PreguntaEvidencia[];
}

export interface KpiDeInstrumento {
  kpiId: string;
  nombre: string;
  score: number | null;
  origen: OrigenKpi;
  preguntas: PreguntaEvidencia[];
}

// ── Espacio vectorial ───────────────────────────────────────────────────────────

export interface PuntoVector {
  x: number;
  y: number;
  /** Colección de ChromaDB a la que pertenece el punto (p.ej. "kpis"). */
  coleccion: string;
  /** Etiqueta legible del punto para mostrar al pasar el cursor. */
  label: string;
  id: string;
}

export interface EspacioVectorial {
  puntos: PuntoVector[];
  /** Conteo de puntos por colección. */
  colecciones: Record<string, number>;
}
