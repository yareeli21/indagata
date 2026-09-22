/**
 * Constantes de dominio del sistema
 */

import type { EstadoPipeline, TipoInstrumento } from './index';

/**
 * Labels legibles para tipos de instrumento
 */
export const TIPO_INSTRUMENTO_LABELS: Record<TipoInstrumento, string> = {
  encuesta: "Encuesta",
  entrevista: "Entrevista",
  prueba_estandarizada: "Prueba Estandarizada"
};

/**
 * Labels legibles para estados del pipeline
 */
export const ESTADO_PIPELINE_LABELS: Record<EstadoPipeline, string> = {
  pendiente: "Pendiente",
  metadata_registrado: "Metadatos Registrados",
  etl_pendiente: "Análisis ETL Completado",
  etl_aprobado: "ETL Aprobado",
  en_ingesta: "En Proceso de Ingesta",
  vectorizado: "Completado",
  error: "Error"
};

/**
 * Colores para badges de estado
 */
export const ESTADO_COLORS: Record<EstadoPipeline, string> = {
  pendiente: "bg-gray-200 text-gray-800",
  metadata_registrado: "bg-blue-200 text-blue-800",
  etl_pendiente: "bg-yellow-200 text-yellow-800",
  etl_aprobado: "bg-green-200 text-green-800",
  en_ingesta: "bg-purple-200 text-purple-800",
  vectorizado: "bg-green-500 text-white",
  error: "bg-red-500 text-white"
};

/**
 * Pasos del wizard controlados por estado
 */
export interface EstadoWizardMapping {
  estado: EstadoPipeline;
  currentStep: number;
  enabledSteps: number[];
}

export const ESTADO_TO_WIZARD: Record<EstadoPipeline, EstadoWizardMapping> = {
  pendiente: {
    estado: "pendiente",
    currentStep: 1,
    enabledSteps: [1, 2]
  },
  metadata_registrado: {
    estado: "metadata_registrado",
    currentStep: 3,
    enabledSteps: [3]
  },
  etl_pendiente: {
    estado: "etl_pendiente",
    currentStep: 4,
    enabledSteps: [4]
  },
  etl_aprobado: {
    estado: "etl_aprobado",
    currentStep: 5,
    enabledSteps: [5]
  },
  en_ingesta: {
    estado: "en_ingesta",
    currentStep: 5,
    enabledSteps: []
  },
  vectorizado: {
    estado: "vectorizado",
    currentStep: 5,
    enabledSteps: []
  },
  error: {
    estado: "error",
    currentStep: 0,
    enabledSteps: []
  }
};

/**
 * Títulos de los pasos del wizard
 */
export const WIZARD_STEP_TITLES = [
  "Subir Archivo",
  "Registrar Metadatos",
  "Analizar Instrumento",
  "Revisar Propuestas ETL",
  "Ejecutar Ingesta"
];

/**
 * Campos Dublin Core obligatorios
 */
export const DUBLIN_CORE_REQUIRED_FIELDS = [
  "dc_title",
  "dc_creator",
  "dc_subject",
  "dc_description",
  "dc_publisher",
  "dc_contributor",
  "dc_date",
  "dc_type",
  "dc_format",
  "dc_identifier",
  "dc_language",
  "dc_coverage",
  "dc_rights"
] as const;

/**
 * Campos Dublin Core opcionales
 */
export const DUBLIN_CORE_OPTIONAL_FIELDS = [
  "dc_source",
  "dc_relation"
] as const;

/**
 * Labels para campos Dublin Core
 */
export const DUBLIN_CORE_LABELS: Record<string, string> = {
  dc_title: "Título",
  dc_creator: "Creador/Autor",
  dc_subject: "Temas (separados por coma)",
  dc_description: "Descripción",
  dc_publisher: "Editor/Institución",
  dc_contributor: "Colaborador",
  dc_date: "Fecha (YYYY-MM-DD)",
  dc_type: "Tipo",
  dc_format: "Formato",
  dc_identifier: "Identificador",
  dc_language: "Idioma (ej: es, en)",
  dc_coverage: "Cobertura temporal/geográfica",
  dc_rights: "Derechos de autor",
  dc_source: "Fuente (opcional)",
  dc_relation: "Relación con otros recursos (opcional)"
};

/**
 * Tipos de archivo aceptados por tipo de instrumento
 */
export const ACCEPTED_FILE_TYPES: Record<TipoInstrumento, string> = {
  encuesta: ".pdf,.docx,.xlsx,.csv,.sav",
  entrevista: ".pdf,.docx,.txt",
  prueba_estandarizada: ".pdf,.docx,.xlsx"
};
