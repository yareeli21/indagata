/**
 * Tipos TypeScript generados a partir de los schemas Pydantic del backend.
 * Mapeo de: backend/app/schemas/schemas_cargar_instru.py
 * 
 * IMPORTANTE: Mantener sincronizado con el backend.
 */

// ---------------------------------------------------------------------------
// Tipos base
// ---------------------------------------------------------------------------

export type TipoInstrumento = "encuesta" | "entrevista" | "prueba_estandarizada";

export type EstadoPipeline = 
  | "pendiente"
  | "metadata_registrado"
  | "etl_pendiente"
  | "etl_aprobado"
  | "en_ingesta"
  | "vectorizado"
  | "error";

export type Visibilidad = "public" | "private";

export type TipoDescarga = "original" | "json" | "sav";

export type TipoPropuesta = "transformacion" | "metadato_enriquecido" | "kpi_sugerido";

export type DecisionPropuesta = "aceptada" | "rechazada";

// ---------------------------------------------------------------------------
// Schemas de ENTRADA
// ---------------------------------------------------------------------------

export interface UploadRequest {
  tipo_instrumento: TipoInstrumento;
  visibilidad?: Visibilidad;
}

export interface KpiInferidoInput {
  kpi_id: number;
  evidencia_textual?: string | null;
  score_inferencia: number; // 0.0 a 1.0
}

export interface MetadataRequest {
  instrumento_id: number;
  
  // 13 campos Dublin Core obligatorios
  dc_title: string;
  dc_creator: string;
  dc_subject: string[];
  dc_description: string;
  dc_publisher: string;
  dc_contributor: string;
  dc_date: string;
  dc_type: string;
  dc_format: string;
  dc_identifier: string;
  dc_language: string;
  dc_coverage: string;
  dc_rights: string;
  
  // 2 campos Dublin Core opcionales
  dc_source?: string | null;
  dc_relation?: string | null;
  
  // KPIs base conocidos
  kpis_inferidos?: KpiInferidoInput[];
}

export interface DecisionInput {
  propuesta_id: number;
  decision: DecisionPropuesta;
}

export interface AprobacionRequest {
  instrumento_id: number;
  decisiones: DecisionInput[];
}

export interface IngestaRequest {
  instrumento_id: number;
}

export interface FiltrosInstrumento {
  tipo_instrumento?: TipoInstrumento | null;
  idioma?: string | null;
  kpi_id?: number | null;
  skip?: number;
  limit?: number;
}

// ---------------------------------------------------------------------------
// Schemas de SALIDA — pasos de registro
// ---------------------------------------------------------------------------

export interface UploadResponse {
  instrumento_id: number;
  estado: EstadoPipeline;
  mensaje: string;
}

export interface MetadataResponse {
  instrumento_id: number;
  estado: EstadoPipeline;
  mensaje: string;
}

export interface EtlExtractResponse {
  instrumento_id: number;
  estado: EstadoPipeline;
  n_propuestas: number;
  n_transformaciones: number;
  n_metadatos: number;
  n_kpis: number;
  mensaje: string;
}

export interface IngestaResponse {
  instrumento_id: number;
  mensaje: string;
}

// ---------------------------------------------------------------------------
// Schemas de SALIDA — ETL (propuestas y aprobación)
// ---------------------------------------------------------------------------

export interface EtlPropuestaOutput {
  propuesta_id: number;
  tipo: TipoPropuesta;
  descripcion: string;
  accion_sugerida: string;
  justificacion: string;
  impacto_esperado: string | null;
  valor_original: string | null;
  valor_propuesto: string | null;
  estado_decision: string; // 'pendiente' | 'aceptada' | 'rechazada'
  fecha_propuesta: string; // ISO datetime
  fecha_decision: string | null; // ISO datetime
}

export interface EtlProposalsResponse {
  instrumento_id: number;
  estado: EstadoPipeline;
  propuestas: EtlPropuestaOutput[];
  n_pendientes: number;
  n_aceptadas: number;
  n_rechazadas: number;
}

export interface AprobacionResponse {
  instrumento_id: number;
  estado: EstadoPipeline;
  n_aceptadas: number;
  n_rechazadas: number;
  mensaje: string;
}

// ---------------------------------------------------------------------------
// Schemas de SALIDA — detalle del instrumento
// ---------------------------------------------------------------------------

export interface KpiInferidoOutput {
  kpi_id: number;
  nombre_kpi: string;
  tipo_relacion?: string | null; // 'directa' | 'indirecta' | 'complementaria'
  evidencia_textual?: string | null;
  score_inferencia?: number | null;
  origen: string; // 'registro_manual' | 'propuesta_etl'
}

export interface MetadatosEnriquecidosOutput {
  poblacion_objetivo?: string | null;
  unidad_analisis?: string | null;
  sector_economico?: string | null;
  ambito_geografico?: string | null;
  dominio_tematico?: string | null;
  metodologia_levantamiento?: string | null;
  nivel_educativo?: string | null;
  periodicidad?: string | null;
  tamano_muestra?: number | null;
  otros?: Record<string, any> | null;
}

export interface InstrumentoResumen {
  instrumento_id: number;
  nombre: string;
  tipo_instrumento: TipoInstrumento;
  idioma?: string | null;
  visibilidad: Visibilidad;
  propietario?: string | null;
  creado_en: string; // ISO datetime
}

export interface InstrumentoDetalle extends InstrumentoResumen {
  dublin_core?: Record<string, any> | null;
  metadatos_enriquecidos?: MetadatosEnriquecidosOutput | null;
  kpis_inferidos_detalle?: KpiInferidoOutput[];
  fecha_procesamiento?: string | null; // ISO datetime
  error_detalle?: string | null;
}

export interface EliminacionResponse {
  mensaje: string;
}

// ---------------------------------------------------------------------------
// Tipos auxiliares para la UI
// ---------------------------------------------------------------------------

/**
 * Representa el estado de un paso del wizard de carga
 */
export interface WizardStep {
  number: number;
  title: string;
  enabled: boolean;
  completed: boolean;
}

/**
 * Payload para el upload con archivo
 */
export interface UploadWithFileRequest {
  file: File;
  tipo_instrumento: TipoInstrumento;
  visibilidad?: Visibilidad;
}

/**
 * Estado local del wizard de carga
 */
export interface CargaWizardState {
  currentStep: number;
  instrumentoId: number | null;
  estado: EstadoPipeline | null;
  loading: boolean;
  error: string | null;
}

/**
 * Filtros activos en la tabla de instrumentos
 */
export interface FiltrosActivos {
  tipo_instrumento: TipoInstrumento | null;
  idioma: string;
  kpi_id: number | null;
}
