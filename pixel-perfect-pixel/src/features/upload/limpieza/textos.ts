/** Textos de la limpieza para el investigador (las claves vienen del cleaning-service). */

/** Etiqueta de cada opción de decisión. */
export const ETIQUETA_OPCION: Record<string, string> = {
  eliminar: "Eliminar",
  conservar: "Conservar",
  pregunta: "Pregunta",
  contexto: "Dato de contexto",
  anular: "Eliminar (dejar vacío)",
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
  vaciar: "Dejarlas vacías",
  quitar_ninguno: "Quitar «Ninguno» y dejar las otras",
  usar: "Usar estas dimensiones",
  ignorar: "No agrupar",
  usar_segmentacion: "Usar estas preguntas y respuestas",
  reparar: "Reparar la fila",
  recortar: "Recortar al ancho del encabezado",
  usar_como_texto: "Quitarla y guardar el texto de las preguntas",
  es_respondente: "Es un encuestado",
  uno_es_si: "1 = Sí, 0 = No",
  uno_es_no: "1 = No, 0 = Sí",
  quitar: "Quitarlas",
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
  no_respuestas_vaciadas: "«No sé / No aplica» vaciadas",
  escritura_homologada: "Escritura homologada",
  fuera_de_rango_anulados: "Fuera de la escala, vaciados",
  fuera_de_rango_cambiados: "Fuera de la escala, cambiados",
  acentos_reparados: "Acentos reparados",
  encabezado_repetido: "Encabezado repetido descartado",
  filas_completadas: "Filas completadas",
  filas_resumen_eliminadas: "Filas de totales eliminadas",
  texto_de_preguntas: "Texto de las preguntas guardado",
  filas_corridas_reparadas: "Filas corridas reparadas",
  filas_irregulares_eliminadas: "Filas irregulares eliminadas",
  coma_decimal: "Coma decimal",
  numero_con_etiqueta: "Número con etiqueta",
  numero_en_palabras: "Números con palabras",
  unidad_quitada: "Unidades quitadas",
  si_no_unificado: "Sí / No unificados",
  si_no_codigos: "«1» y «0» en Sí / No",
  opciones_parecidas_cambiadas: "Opciones parecidas cambiadas",
  respuestas_normalizadas: "Respuestas normalizadas",
  reactivos_vacios_conservados: "Reactivos sin respuestas",
  duplicados_nulificados: "Repetidos marcados como nulos",
  duplicados_eliminados: "Repetidos eliminados",
  encabezados_repetidos: "Encabezados y pies de página",
  transcripcion_minutos_en_etiqueta: "Minuto en la etiqueta",
  anotaciones_quitadas: "Anotaciones quitadas",
  muletillas_quitadas: "Muletillas quitadas",
};

/** Mensaje mientras corre la fase automática, según el tipo de instrumento. */
export const DETALLE_PROCESANDO: Record<string, string> = {
  Encuesta:
    "Unificamos vacíos, quitamos filas y columnas vacías, detectamos tipos de pregunta, escalas y valores fuera de rango.",
  Entrevista:
    "Quitamos marcas de tiempo, números de página e identificadores, reconstruimos palabras partidas e identificamos a los hablantes.",
  "Prueba estandarizada":
    "Validamos la estructura, detectamos el tipo de cada reactivo y marcamos las respuestas nulas o no respondidas (las pruebas no se califican).",
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
  // «cambiar:5» → cambiar un valor fuera de la escala por uno de la escala.
  if (opcion.startsWith("cambiar:")) return `Cambiar a «${opcion.slice("cambiar:".length)}»`;
  return ETIQUETA_OPCION[opcion] ?? opcion.replaceAll("_", " ");
}
