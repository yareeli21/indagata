/** Textos de la limpieza para el investigador (las claves vienen del cleaning-service). */

/** Etiqueta de cada opción de decisión. */
export const ETIQUETA_OPCION: Record<string, string> = {
  eliminar: "Eliminar",
  conservar: "Conservar",
  pregunta: "Pregunta",
  contexto: "Dato de contexto",
  anular: "Dejar vacíos",
  usar_orden_propuesto: "Usar este orden",
  invertir_orden: "Invertir el orden",
  no_es_likert: "No es una escala",
  invertido: "Sí, está invertido",
  no_invertido: "No",
  entrevistador: "Entrevistador",
  entrevistado: "Entrevistado",
  otro: "Otro",
  continuar_por_parrafos: "Continuar por párrafos",
  conservar_primero: "Conservar el primero",
  conservar_todos: "Conservar todos",
  eliminar_todos: "Eliminar todos",
  conservar_marcadas: "Conservarlas marcadas",
  confirmar: "Confirmar la clave",
  vaciar: "Dejarlas vacías",
};

/** Nombre corto de cada transformación automática. */
export const ETIQUETA_REGLA: Record<string, string> = {
  codificacion_utf8: "Texto en UTF-8",
  encabezados_normalizados: "Encabezados normalizados",
  espacios_en_valores: "Espacios de más",
  vacios_unificados: "Vacíos unificados",
  filas_vacias: "Filas vacías eliminadas",
  columnas_vacias: "Columnas vacías eliminadas",
  identificadores_seguros: "Identificadores por columna",
  roles_automaticos: "Preguntas detectadas",
  texto_normalizado: "Texto normalizado",
  marcas_de_tiempo: "Marcas de tiempo",
  numeros_de_pagina: "Números de página",
  identificadores: "Identificadores",
  separadores: "Líneas separadoras",
  palabras_reconstruidas: "Palabras reconstruidas",
  espacios_normalizados: "Espacios normalizados",
  ciclo_de_ruido: "Iteraciones del ciclo de ruido",
  validacion_archivo: "Archivo y estructura válidos",
  respuestas_validadas: "Respuestas validadas",
  respuestas_nulificadas: "Respuestas nulas",
  no_respondidas: "No respondidas",
  linea_recta_eliminados: "Respuestas en línea recta eliminadas",
  incompletos_eliminados: "Encuestados incompletos eliminados",
  no_respuestas_conservadas: "«No sé / No aplica» conservadas",
  clave_propuesta: "Clave de respuestas propuesta",
  no_respuestas_vaciadas: "«No sé / No aplica» vaciadas",
};

/** Mensaje mientras corre la fase automática, según el tipo de instrumento. */
export const DETALLE_PROCESANDO: Record<string, string> = {
  Encuesta:
    "Unificamos vacíos, quitamos filas y columnas vacías, detectamos tipos de pregunta, escalas y valores fuera de rango.",
  Entrevista:
    "Quitamos marcas de tiempo, números de página e identificadores, reconstruimos palabras partidas e identificamos a los hablantes.",
  "Prueba estandarizada":
    "Validamos la estructura, comparamos las respuestas con la clave y marcamos las respuestas nulas o no respondidas.",
};

/** Nombre legible de un tipo canónico provisional. */
export const ETIQUETA_TIPO: Record<string, string> = {
  cuadricula: "Cuadrícula",
  ranking: "Ranking",
  opcion_multiple_varias: "Opción múltiple",
  likert: "Escala Likert",
  binaria: "Binaria",
  escala_lineal: "Escala lineal",
  calificacion: "Calificación",
  numerica: "Numérica",
  categorica: "Categórica",
  texto_corto: "Texto corto",
  texto_largo: "Texto largo",
};

export function etiquetaOpcion(opcion: string): string {
  return ETIQUETA_OPCION[opcion] ?? opcion.replaceAll("_", " ");
}
