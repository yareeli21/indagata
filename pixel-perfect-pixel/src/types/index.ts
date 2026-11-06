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
  /** ISO; ausente en investigaciones creadas antes de guardarla. */
  fechaCreacion?: string;
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
  /** Medio que la publicó y enlace a la nota original. */
  medio?: string;
  url?: string;
}

export interface NoticiasRespuesta {
  noticias: Noticia[];
  actualizado: string | null;
  aviso: string | null;
}

// ── Limpieza (cleaning-service) ───────────────────────────────────────────────

export type EstadoLimpieza = "esperando_decisiones" | "confirmada" | "fallida";

/** Algo que el investigador decide en la fase asistida (con una opción sugerida). */
export interface HallazgoLimpieza {
  id: string;
  /** columna_ajena | rol_columna | columna_incompleta | fuera_de_rango | duplicados | likert_orden | item_invertido… */
  tipo: string;
  /** Agrupación para la interfaz. */
  tema: string;
  objetivo: string;
  titulo: string;
  descripcion: string;
  opciones: string[];
  sugerida: string | null;
  obligatoria: boolean;
  detalle: Record<string, unknown>;
  /** Lo que eligió el investigador (null = se usará la sugerida). */
  decision: string | null;
}

export interface TransformacionLimpieza {
  regla: string;
  detalle: string;
  afectados: number | null;
  /** Dónde: cada cambio con su fila, pregunta, valor antes y después (los primeros cientos). */
  casos?: { fila: number; columna?: string; antes?: string; despues?: string }[];
  /** Cuántos cambios hubo en cada pregunta. */
  columnas?: Record<string, number>;
}

/** Una métrica antes y después de la limpieza. */
export interface ComparacionMetrica {
  metrica: string;
  antes: number | null;
  despues: number | null;
  formato: "num" | "pct" | "dec";
}

export interface DescriptivosNumericos {
  n: number;
  media: number | null;
  mediana: number | null;
  desviacion: number | null;
  min: number | null;
  max: number | null;
  q1: number | null;
  q3: number | null;
  iqr: number | null;
  asimetria: number | null;
  curtosis: number | null;
}

export interface Frecuencias {
  tabla: { valor: string; n: number; pct: number }[];
  moda: string | string[] | null;
  n_categorias: number;
  otras: number;
}

/** Medidas de una columna de encuesta. */
export interface ColumnaEstadistica {
  id: string;
  etiqueta: string;
  tipo: string;
  rol: string | null;
  n: number;
  n_nulos: number;
  pct_nulos: number;
  numerico?: DescriptivosNumericos | null;
  frecuencias?: Frecuencias;
  atipicos?: {
    metodo: string;
    sigma: number;
    iqr: number;
    factor_sigma: number;
    factor_iqr: number;
  };
  texto?: { palabras_promedio: number; respuestas_distintas: number };
  n_excluidos?: number;
  escala?: { puntos: number; invertido: boolean };
}

/** Alfa de Cronbach de un bloque de ítems Likert. */
export interface FiabilidadBloque {
  bloque: string;
  items: string[];
  invertidos: string[];
  n_items: number;
  n_casos: number;
  alfa: number | null;
  interpretacion: string | null;
  por_item: {
    item: string;
    media: number | null;
    correlacion_item_total: number | null;
    alfa_si_se_elimina: number | null;
  }[];
}

/** Descripción de un reactivo de una prueba estandarizada (no se califica: sin respuesta correcta). */
export interface ReactivoEstadistica {
  pregunta: string;
  tipo_reactivo: string;
  n: number;
  distribucion: { opcion: string; n: number; pct: number }[];
  opcion_mas_elegida: { opcion: string; n: number; pct: number; pct_validas: number } | null;
  opciones_sin_elegir: string[];
  n_nulas: number;
  n_no_respondidas: number;
  pct_sin_respuesta: number;
  mucha_no_respuesta: boolean;
  casi_unanime: boolean;
  puntos_max?: number;
  descriptivos?: Partial<DescriptivosNumericos> | null;
}

export interface HablanteEstadistica {
  nombre: string;
  rol: string | null;
  turnos: number;
  palabras: number;
  pct_palabras: number;
  pct_preguntas: number;
  palabras_por_turno: Partial<DescriptivosNumericos>;
}

/** Medidas estadísticas de la limpieza (dependen del tipo de instrumento). */
export interface EstadisticaLimpieza {
  // Encuestas
  columnas?: ColumnaEstadistica[];
  encuestados?: { linea_recta: number; incompletos: number };
  // Encuestas: alfa de Cronbach por bloque.
  fiabilidad?: FiabilidadBloque[];
  // Pruebas (no se califican: se describe lo que respondieron los alumnos)
  reactivos?: ReactivoEstadistica[];
  respuestas?: { n_alumnos: number; n_reactivos: number; pct_sin_respuesta: number };
  resumen_reactivos?: {
    con_opciones_sin_elegir: number;
    mucha_no_respuesta: number;
    casi_unanimes: number;
  };
  umbrales?: { sin_respuesta: number; casi_unanime: number };
  // Entrevistas
  hablantes?: HablanteEstadistica[];
  palabras_por_turno?: Partial<DescriptivosNumericos>;
  n_participantes?: number;
  n_preguntas?: number;
  n_respuestas?: number;
  palabras_por_respuesta?: Partial<DescriptivosNumericos>;
  preguntas?: PreguntaEntrevistaEstadistica[];
  participantes?: {
    id: string;
    respuestas: number;
    palabras: number;
    palabras_por_respuesta: number | null;
  }[];
  palabras_por_rol?: { rol: string; turnos: number; palabras: number; pct_palabras: number }[];
}

/** Respuestas que recibió una pregunta del entrevistador. */
export interface PreguntaEntrevistaEstadistica {
  pregunta: string;
  texto: string;
  n_respuestas: number;
  sin_respuesta: number;
  palabras: Partial<DescriptivosNumericos>;
}

/** Una frase del resumen «En pocas palabras» (reglas fijas del cleaning-service). */
export interface FraseResumen {
  nivel: "bien" | "info" | "atencion" | "alerta";
  texto: string;
}

/** Sugerencia de análisis derivada de las medidas de la limpieza. */
export interface SugerenciaAnalisis {
  nivel: "bien" | "info" | "atencion" | "alerta";
  texto: string;
  porque: string;
}

/** Medidas de la última limpieza confirmada y sugerencias (GET /limpieza/{id}/resumen). */
export interface ResumenLimpieza {
  idCrudo: number;
  version: number;
  tipoInstrumento: string;
  fechaConfirmacion: string | null;
  cifras: { etiqueta: string; valor: number | string }[];
  estadistica: EstadisticaLimpieza | null;
  estadistica_antes: EstadisticaLimpieza | null;
  resumen: FraseResumen[];
  sugerencias: SugerenciaAnalisis[];
}

export interface VistaFinalLimpieza {
  cifras: { etiqueta: string; valor: number | string }[];
  forma: "tabla" | "turnos";
  columnas: string[];
  filas: string[][];
  total_filas: number;
  /** Ausentes en limpiezas confirmadas antes de las medidas estadísticas. */
  comparacion?: ComparacionMetrica[];
  estadistica?: EstadisticaLimpieza | null;
  estadistica_antes?: EstadisticaLimpieza | null;
  resumen?: FraseResumen[];
}

/** Una versión de la limpieza de un instrumento. */
export interface EjecucionLimpieza {
  idCrudo: number;
  version: number;
  estado: EstadoLimpieza;
  tipoInstrumento: string;
  error: string | null;
  avisos: string[];
  metricasAntes: Record<string, unknown>;
  transformaciones: TransformacionLimpieza[];
  hallazgos: HallazgoLimpieza[];
  pendientesObligatorias: number;
  vistaFinal: VistaFinalLimpieza | null;
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

// ── Conocimiento (knowledge-service): perfil semántico y documento final ──────

export interface PreguntaPerfil {
  id: string;
  texto: string;
  /** Solo en preguntas categóricas y de opción múltiple (nunca anclas Likert). */
  opciones?: string[] | undefined;
}

export interface SeccionPerfil {
  id: string;
  nombre: string;
  descripcion?: string | undefined;
  preguntas: PreguntaPerfil[];
}

/** Lo que describe al instrumento; es lo único que se usa para asociar KPIs. */
export interface PerfilSemantico {
  esquema_version: string;
  instrumento_id: string;
  tipo: "encuesta" | "entrevista" | "prueba_estandarizada";
  titulo: string;
  objetivo: string;
  temas: string[];
  palabras_clave: string[];
  nivel_educativo: string;
  poblacion: string;
  contexto: string;
  secciones: SeccionPerfil[];
  kpis_asociados: Record<string, unknown>[];
}

export interface AvisoConocimiento {
  codigo: string;
  mensaje: string;
  n?: number | null | undefined;
}

/** De dónde salieron las preguntas del perfil. */
export type FuentePerfil = "original" | "encabezados" | "json_tecnico";

export interface PerfilGenerado {
  perfil: PerfilSemantico;
  fuente: FuentePerfil;
  n_preguntas: number;
  avisos: AvisoConocimiento[];
  /** Solo en perfiles guardados (versión del conocimiento). */
  version?: number | undefined;
  estado?: string | undefined;
}

/** KPI aceptado, con el mismo formato en el perfil y en el documento final. */
export interface KpiAsociado {
  kpi_id: string;
  nombre: string;
  definicion: string;
  dimension: string;
  que_mide: string;
  similitud: number;
  evidencia: { pregunta_id: string; similitud: number }[];
  justificacion: string;
  justificacion_origen: string;
  aceptado_por: string;
  fecha: string;
}

export interface ResumenPreguntaDoc {
  n_validas: number;
  n_sin_respuesta: number;
  sin_respuesta_por_motivo?: Record<string, number> | undefined;
  n_no_interpretadas?: number | undefined;
  distribucion?: { significado: string; n: number; pct: number }[] | undefined;
  por_nivel?: Record<string, number> | undefined;
  media?: number | null | undefined;
  interpretacion: string;
}

export interface PreguntaDoc {
  id: string;
  seccion_id: string;
  texto: string;
  tipo?: string | undefined;
  kpis_relacionados: string[];
  resumen?: ResumenPreguntaDoc | undefined;
}

export interface ReactivoDoc {
  id: string;
  seccion_id: string;
  clave: string;
  texto: string;
  /** opcion_multiple | verdadero_falso | puntos | escala | si_no | numerica */
  tipo_reactivo?: string | undefined;
  kpis_relacionados: string[];
  /** Lo que respondieron los alumnos (las pruebas no se califican). */
  resumen: {
    n_alumnos: number;
    opcion_mas_elegida: { opcion: string; significado: string; n: number; pct: number } | null;
    opciones_sin_elegir?: string[];
    n_nulas: number;
    n_sin_respuesta: number;
    media?: number | null;
    interpretacion: string;
  };
}

export interface RespuestaDoc {
  pregunta?: string;
  estado: string;
  significado?: string;
  texto?: string;
  nivel?: string;
}

/** Un intercambio de una entrevista: solo la pregunta del entrevistador y la respuesta. */
export interface IntercambioDoc {
  pregunta_id?: string | undefined;
  pregunta: string;
  respuesta: string;
}

/** La entrevista de una persona (ID anónimo) en el documento final. */
export interface EntrevistaDoc {
  participante: string;
  intercambios: IntercambioDoc[];
}

/** Vista ligera del documento final (sin respuestas individuales, con una muestra). */
export interface DocumentoVista {
  esquema_version: string;
  instrumento: { id: string; tipo: string; titulo: string } & Record<string, unknown>;
  kpis_asociados: KpiAsociado[];
  /** Encuestas y pruebas (las entrevistas no llevan secciones). */
  secciones?: { id: string; nombre: string }[] | undefined;
  preguntas?: PreguntaDoc[] | undefined;
  reactivos?: ReactivoDoc[] | undefined;
  n_respondentes?: number | undefined;
  n_alumnos?: number | undefined;
  /** Entrevistas: una por persona, con pregunta y respuesta (sin estadísticas). */
  n_entrevistas?: number | undefined;
  muestra_entrevistas?: EntrevistaDoc[] | undefined;
  /** Primeros respondentes/alumnos con todas sus respuestas (cada una con el texto de su pregunta). */
  muestra_respondentes?: { id: string; respuestas: RespuestaDoc[] }[] | undefined;
  muestra_alumnos?: { id: string; respuestas: RespuestaDoc[] }[] | undefined;
}

export interface DocumentoGenerado {
  id_crudo: number;
  version: number;
  estado: string;
  esquema_version: string;
  sha256: string | null;
  avisos: AvisoConocimiento[];
  documento: DocumentoVista;
}

/** Análisis de una respuesta de entrevista (knowledge-service, documento final 2.1). */
export type MarcoTemporal = "actual" | "pasado" | "hipotetico" | "general";
export type FuncionUnidad = "responde" | "contexto" | "digresion";
export type PosturaUnidad = "si" | "no" | "ambivalente" | "no_aplica";

export interface UnidadRespuesta {
  texto: string;
  marco_temporal: MarcoTemporal;
  funcion: FuncionUnidad;
  postura: PosturaUnidad;
}

export interface AnalisisRespuesta {
  unidades: UnidadRespuesta[];
  nucleo: string;
  postura: PosturaUnidad | "sin_determinar";
  motivo?: string;
  marco_pregunta?: MarcoTemporal;
  metodo: "llm" | "reglas";
  estado: "propuesto" | "revisado";
  descartadas?: number;
}

export interface IntercambioAnalizado {
  participante: string;
  n: number;
  pregunta_id: string | null;
  pregunta: string;
  respuesta: string;
  analisis: AnalisisRespuesta | null;
}

export interface AnalisisEntrevista {
  estado: "sin_analisis" | "en_curso" | "listo" | "error";
  hechos: number;
  total: number;
  revisados: number;
  mensaje?: string;
  intercambios: IntercambioAnalizado[];
}

export interface EvidenciaKpi {
  pregunta_id: string;
  texto: string;
  similitud: number;
}

/** KPI sugerido desde el perfil semántico (analysis-service). */
export interface KpiPropuesto {
  kpi_id: number;
  /** ID global en los documentos (KPI-07). */
  kpi_ref: string;
  nombre: string;
  definicion: string;
  que_mide: string;
  dimension: string;
  polaridad: string;
  /** Puntaje 0–1 de la fórmula (perfil general + preguntas + cobertura). */
  score: number;
  componentes: { g: number; p: number; c: number };
  /** Preguntas que lo sustentan. */
  evidencia: EvidenciaKpi[];
  justificacion: string;
  justificacion_origen: "llm" | "plantilla";
}

export interface PropuestaKpis {
  id_crudo: number;
  version: number;
  n_preguntas: number;
  kpis: KpiPropuesto[];
}

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

/** «servidor»: no se envía modelo y el chat usa el de `OLLAMA_MODEL` (.env) en todas sus etapas. */
export type ModeloLLM = "servidor" | "llama3.2:3b";

export interface ContextoInvestigacion {
  objetivo: string;
  poblacion: string;
  nivel: NivelEducativo;
  pregunta: string;
}

export interface FuenteChat {
  /** Número con el que la respuesta la cita: [Fuente n]. */
  numero: number;
  instrumentoId: string;
  titulo: string;
  tipo: TipoInstrumento;
  investigador: string;
  kpis: string[];
  fragmento: string;
}

/** Entrada curada que respalda una respuesta: glosario metodológico o ayuda de la plataforma. */
export interface ReferenciaChat {
  tipo: "glosario" | "ayuda" | "fuente_kpi";
  titulo: string;
  texto: string;
  /** fuente_kpi: enlace a la fuente de referencia verificada. */
  url?: string;
}

/** Decisión del dominio acotado del chat (también se guarda en rag_log). */
export type DecisionChat =
  "dentro" | "fuera" | "privacidad" | "manipulacion" | "sin_informacion" | "ayuda";

/** Cómo se respondió: búsqueda semántica, cálculo exacto, ambos o la ayuda de la plataforma. */
export type RutaChat = "semantica" | "estructurada" | "mixta" | "ayuda";

/** Lo que llega al terminar una respuesta (evento SSE `fuentes`). */
export interface ResultadoChat {
  fuentes: FuenteChat[];
  referencias: ReferenciaChat[];
  decision?: DecisionChat | undefined;
  ruta?: RutaChat | null;
  consultaId?: number | null;
  /** true si se reutilizó una respuesta guardada (misma pregunta, alcance y versiones). */
  enCache?: boolean;
  /** Milisegundos que tardó la respuesta (Pruebas: duración). */
  latenciaMs?: number | null;
}

/** Métricas automáticas de una respuesta (juez local: evaluación aproximada). */
export interface MetricasRespuesta {
  consultaId: number;
  /**
   * «pendiente»: bajo demanda, se calcula cuando la persona la pide (el juez y el redactor no caben juntos en la
   * GPU). «calculada»: la respuesta es el resultado calculado tal cual (fiel por construcción).
   */
  estado: "pendiente" | "calculando" | "listo" | "omitida" | "error" | "calculada";
  motivo: string | null;
  fidelidad: number | null;
  relevancia: number | null;
  precisionContexto: number | null;
  noSustentadas: string[];
  modeloJuez: string | null;
  fecha: string | null;
  /** Indicadores del sistema: deterministas, sin juez. */
  indicadores: IndicadoresRespuesta | null;
  /** Evaluaciones de la misma respuesta por cada juez (experimento redactor × juez). */
  jueces: EvaluacionJuez[];
  calificacion: CalificacionRespuesta | null;
}

/** Indicadores del sistema de una respuesta (sin juez): quién la escribió, si inventó cifras o IDs, tiempos. */
export interface IndicadoresRespuesta {
  modelo: string | null;
  intencion: string | null;
  ruta: string | null;
  decision: string | null;
  /** «redactada»: la escribió el modelo; «presentacion_fija»: el cálculo tal cual; «plantilla»: mensaje fijo. */
  respuesta: "redactada" | "presentacion_fija" | "plantilla";
  plantilla: string | null;
  plantillaDetalle: string | null;
  regeneraciones: number | null;
  primerFallo: string | null;
  verificacion: string | null;
  cifrasTotal: number | null;
  cifrasConRespaldo: number | null;
  cifrasSinRespaldo: string[];
  idsInventados: string[];
  /** Partes del instrumento que recuperó la búsqueda vectorial (Chroma) y vio el modelo: «E01 en p04», «p03». */
  fragmentosRag: string[];
  tiempos: Record<string, number>;
  latenciaMs: number | null;
}

export interface EvaluacionJuez {
  modeloJuez: string;
  estado: string;
  fidelidad: number | null;
  relevancia: number | null;
  precisionContexto: number | null;
  fecha: string | null;
}

/** Calificación humana: 0 mal, 1 parcial, 2 bien; `fundamenta` null = no aplica. */
export interface CalificacionRespuesta {
  calificacion: 0 | 1 | 2;
  entendio: boolean | null;
  fundamenta: boolean | null;
  comentario: string | null;
  fecha?: string | null;
}

/** Instrumentos que consulta el chat: los de la investigación, unos elegidos o todo el acervo. */
export type AlcanceChat = "investigacion" | "elegidos" | "acervo";

export type RolMensaje = "usuario" | "asistente";

export interface Mensaje {
  id: string;
  rol: RolMensaje;
  contenido: string;
  /** Solo en mensajes del asistente */
  fuentes?: FuenteChat[];
  referencias?: ReferenciaChat[];
  decision?: DecisionChat | undefined;
  ruta?: RutaChat | null;
  consultaId?: number | null;
  enCache?: boolean;
  latenciaMs?: number | null;
  /** true mientras se está generando (streaming) */
  generando?: boolean;
}

/** Conversación guardada de una investigación (para retomarla). */
export interface SesionChat {
  contexto: ContextoInvestigacion;
  mensajes: Mensaje[];
  actualizada: string;
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
  /** Fuentes de referencia verificadas (organismos oficiales); puede venir vacío. */
  fuentes?: FuenteKpi[];
}

export interface FuenteKpi {
  organismo: string;
  titulo: string;
  url: string;
  anio?: number | null;
  nota?: string | null;
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

// ── Espacio vectorial ─────────────────────────────────────────────────────────

export type TipoPuntoEspacio = "kpi" | "instrumento" | "chunk";

export interface PuntoEspacio {
  /** Único en el mapa: "kpi:5", "inst:12", "chunk:inst-12-3". */
  id: string;
  tipo: TipoPuntoEspacio;
  /** Id de dominio: kpi_id, id del instrumento o id del chunk. */
  ref: string;
  etiqueta: string;
  /** Resumen de una línea para el tooltip. */
  resumen: string;
  /** Dato secundario: polaridad (KPI), "tipo · nivel · año" (instrumento), sección (chunk). */
  detalle: string;
  /** Coordenadas en el plano PC1/PC2. */
  x: number;
  y: number;
  clusterId: number | null;
  instrumentoId: string | null;
  /** De dónde sale el vector del instrumento. */
  origenVector: "summary" | "calculado" | null;
}

export interface ClusterEspacio {
  id: number;
  /** KPI más representativo del grupo. */
  etiqueta: string;
  representativos: string[];
  tamano: number;
}

export interface MapaEspacio {
  modelo: string;
  dimension: number;
  pca: {
    /** Proporción de varianza explicada por PC1 y PC2 (0–1). */
    varianza: [number, number];
    varianzaTotal: number;
    varianzaBaja: boolean;
  };
  clusters: ClusterEspacio[];
  /** Fuente de los chunks; mientras `provisional` sea true se marca en la UI. */
  fuenteChunks: { nombre: string; provisional: boolean };
  conteos: { kpis: number; instrumentos: number; chunks: number };
  puntos: PuntoEspacio[];
  generadoEn: string;
  /** Vista alineada: cada grupo centrado en su centroide antes del PCA. */
  alineado: boolean;
}

/** Punto cercano a otro; `similitud` = coseno en el espacio original (0–1). */
export interface VecinoEspacio {
  /** Mismo id que en el mapa ("kpi:5", "inst:12", "chunk:…"). */
  id: string;
  tipo: TipoPuntoEspacio;
  ref: string;
  etiqueta: string;
  similitud: number;
  clusterId: number | null;
  instrumentoId: string | null;
  /** Solo chunks. */
  texto?: string | null;
  seccion?: string | null;
}

export interface VecinosEspacio {
  origen: {
    id: string;
    tipo: TipoPuntoEspacio;
    ref: string;
    etiqueta: string;
    clusterId: number | null;
    /** Solo chunks. */
    texto?: string | null;
    seccion?: string | null;
  };
  kpis: VecinoEspacio[];
  instrumentos: VecinoEspacio[];
  chunks: VecinoEspacio[];
  fuenteChunks: { nombre: string; provisional: boolean };
}

/** Frase libre proyectada en el mapa y sus vecinos (coseno en el espacio original). */
export interface BusquedaEspacio {
  texto: string;
  posicion: { x: number; y: number };
  posicionAlineada: { x: number; y: number };
  /** Grupo con cuyo centroide se centró la frase en la vista alineada. */
  grupoReferencia: TipoPuntoEspacio | null;
  kpis: VecinoEspacio[];
  instrumentos: VecinoEspacio[];
  chunks: VecinoEspacio[];
  fuenteChunks: { nombre: string; provisional: boolean };
}

export interface PreguntaInstrumento {
  id: string;
  texto: string;
  tipo: string;
  seccion: string;
}

/** Ficha completa de un instrumento (GET /visualizacion/catalogo/{id}). */
export interface DetalleInstrumento {
  instrumento: Instrumento;
  /** Columnas de `metadatos_dc` (dc_title, dc_creator, …). */
  dublinCore: Record<string, unknown>;
  /** Columnas de `metadatos_enriquecidos_*` según el tipo. */
  enriquecidos: Record<string, unknown>;
  preguntas: PreguntaInstrumento[];
}

/** Un paso del procesamiento de un instrumento con su tiempo de cómputo (GET /visualizacion/catalogo/{id}/tiempos). */
export interface TiempoPaso {
  paso: string;
  etiqueta: string;
  servicio: string;
  inicio: string;
  fin: string;
  duracion_ms: number;
  /** Corre después de responder (indexación, análisis de entrevista): la persona no lo espera. */
  segundo_plano: boolean;
  detalle: Record<string, unknown>;
}

/** Tiempos del procesamiento: cómputo por paso, total sin esperas y latencia del chat. */
export interface TiemposProceso {
  id_crudo: number;
  pasos: TiempoPaso[];
  /** Suma de los pasos: lo que tardaría la máquina sin esperas. */
  computo_ms: number;
  /** De la carga a la última operación: incluye el tiempo de decisión de la persona. */
  punta_a_punta_ms: number | null;
  chat: { consultas: number; p50_ms: number | null; p95_ms: number | null };
}
