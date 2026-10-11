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

export interface DublinCore {
  titulo: string;
  creador: string;
  tema: string;
  descripcion: string;
  fecha: string;
  idioma: string;
  derechos: string;
  cobertura: NivelEducativo | "";
  /** dc_source — opcional (Bug 1). */
  fuente?: string;
  /** dc_relation — opcional (Bug 1). */
  relacion?: string;
}

export type MetadatosTipo = Record<string, string>;

export interface KpiSugerido {
  id: string;
  nombre: string;
  coincidencia: number;
}

// ── Estandarización (tipos de pregunta) ─────────────────────────────────────────

/**
 * Etiquetas de UI (español) para el tipo de pregunta. El mapeo a vocabulario
 * backend (binaria/opcion_multiple/likert/numerica_continua/abierta) vive en
 * `src/api/carga.ts` (frontera de conversión).
 */
export const TIPOS_PREGUNTA_UI = [
  "Binaria",
  "Opción múltiple",
  "Likert",
  "Numérica continua",
  "Abierta",
] as const;
export type TipoPreguntaUI = (typeof TIPOS_PREGUNTA_UI)[number];

/** Vocabulario cerrado de `type` que exige/devuelve el backend de estandarización. */
export type TipoPreguntaBackend =
  "binaria" | "opcion_multiple" | "likert" | "numerica_continua" | "abierta";

/** Confianza informativa de la detección automática de tipo. */
export type ConfianzaDeteccion = "alta" | "media" | "baja";

/** Pregunta tal como la propone el preview de estandarización (editable por el investigador). */
export interface PreguntaPreview {
  question_id: string;
  text: string;
  type: TipoPreguntaBackend;
  options?: string[] | null;
  scale_min?: number | null;
  scale_max?: number | null;
  confianza: ConfianzaDeteccion;
  es_demografica: boolean;
}

/** Respuesta de `POST /instrumentos/{id}/estandarizar/preview`. */
export interface EstandarizarPreviewResponse {
  id_crudo: number;
  tipo_instrumento: string;
  preguntas: PreguntaPreview[];
  n_respondentes_detectados: number;
  notas: string[];
}

/** Respuesta de `POST /instrumentos/{id}/estandarizar`. */
export interface EstandarizarResponse {
  id_crudo: number;
  id_instrumento: number;
  estado: string;
  ruta_json: string;
  json_instrumento: Record<string, unknown>;
  mensaje: string;
}

/** Campos de metadatos específicos por tipo (claves = columnas reales de la tabla). */
export type MetadatosEspecificos = Record<string, string>;

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
