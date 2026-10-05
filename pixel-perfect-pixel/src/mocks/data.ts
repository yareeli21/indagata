import type { Instrumento, Investigador, Kpi, KpiCatalogo, Noticia, Investigacion } from "@/types";

export const investigadores: Investigador[] = [
  { id: "inv-ana", nombre: "Ana Beltrán", institucion: "UNAM" },
  { id: "inv-luis", nombre: "Luis Ordóñez", institucion: "UPN" },
  { id: "inv-mar", nombre: "Marisol Cadena", institucion: "IPN" },
  { id: "inv-jor", nombre: "Jorge Rentería", institucion: "UdeG" },
];

export const investigaciones: Investigacion[] = [
  { id: "res-1", nombre: "Lectura académica en licenciatura", propietarioId: "inv-ana" },
  { id: "res-2", nombre: "Deserción en programas de posgrado", propietarioId: "inv-ana" },
  { id: "res-3", nombre: "Formación de profesorado universitario", propietarioId: "inv-luis" },
];

export const instrumentos: Instrumento[] = [
  {
    id: "ins-01",
    titulo: "Encuesta de hábitos de lectura en licenciatura",
    tipo: "Encuesta",
    nivel: "Licenciatura",
    autorId: "inv-ana",
    anio: 2024,
    fecha: "2024-01-01",
    kpis: ["Comprensión lectora", "Tasa de respuesta"],
    reactivos: 28,
    estado: "Estandarizado",
    descripcion:
      "Mide frecuencia, medios y motivación lectora en estudiantes de los primeros semestres de licenciatura.",
    etiquetas: ["lectura", "hábitos", "estudiantes"],
  },
  {
    id: "ins-02",
    titulo: "Entrevista a docentes sobre uso de TIC",
    tipo: "Entrevista",
    nivel: "Posgrado",
    autorId: "inv-ana",
    anio: 2023,
    fecha: "2023-06-08",
    kpis: ["Uso de TIC"],
    reactivos: 14,
    estado: "Estandarizado",
    descripcion: "Guion semiestructurado sobre apropiación tecnológica en el aula de posgrado.",
    etiquetas: ["TIC", "docentes"],
  },
  {
    id: "ins-03",
    titulo: "Prueba de comprensión lectora de nivel universitario",
    tipo: "Prueba estandarizada",
    nivel: "Licenciatura",
    autorId: "inv-ana",
    anio: 2025,
    fecha: "2025-11-15",
    kpis: ["Comprensión lectora", "Nivel de logro"],
    reactivos: 40,
    estado: "En revisión",
    descripcion: "Instrumento con textos académicos y de divulgación y 4 niveles de logro.",
    etiquetas: ["comprensión", "evaluación"],
  },
  {
    id: "ins-04",
    titulo: "Cuestionario de clima institucional en el campus",
    tipo: "Encuesta",
    nivel: "Posgrado",
    autorId: "inv-ana",
    anio: 2022,
    fecha: "2022-04-22",
    kpis: ["Clima escolar", "Tasa de respuesta"],
    reactivos: 35,
    estado: "Estandarizado",
    descripcion: "Convivencia, seguridad percibida y relación con autoridades académicas.",
    etiquetas: ["clima", "convivencia"],
  },
  {
    id: "ins-05",
    titulo: "Guía de observación de trabajo colaborativo",
    tipo: "Entrevista",
    nivel: "Licenciatura",
    autorId: "inv-ana",
    anio: 2024,
    fecha: "2024-09-02",
    kpis: ["Desarrollo socioemocional"],
    reactivos: 18,
    estado: "Borrador",
    descripcion:
      "Registro de interacciones durante actividades de trabajo en equipo en el aula universitaria.",
    etiquetas: ["colaboración", "observación"],
  },
  {
    id: "ins-06",
    titulo: "Escala de motivación académica",
    tipo: "Encuesta",
    nivel: "Posgrado",
    autorId: "inv-luis",
    anio: 2023,
    fecha: "2023-02-09",
    kpis: ["Motivación académica", "Tasa de respuesta"],
    reactivos: 24,
    estado: "Estandarizado",
    descripcion: "Adaptación mexicana de la escala de motivación intrínseca y extrínseca.",
    etiquetas: ["motivación", "posgrado"],
  },
  {
    id: "ins-07",
    titulo: "Entrevista a tutores de primer semestre",
    tipo: "Entrevista",
    nivel: "Licenciatura",
    autorId: "inv-luis",
    anio: 2025,
    fecha: "2025-07-16",
    kpis: ["Retención escolar"],
    reactivos: 12,
    estado: "En revisión",
    descripcion: "Acompañamiento tutorial y detección temprana de riesgo académico.",
    etiquetas: ["tutoría", "permanencia"],
  },
  {
    id: "ins-08",
    titulo: "Prueba diagnóstica de razonamiento cuantitativo",
    tipo: "Prueba estandarizada",
    nivel: "Posgrado",
    autorId: "inv-luis",
    anio: 2024,
    fecha: "2024-12-23",
    kpis: ["Nivel de logro", "Razonamiento matemático"],
    reactivos: 45,
    estado: "Estandarizado",
    descripcion:
      "Bloques de estadística, modelación matemática y resolución de problemas aplicados a la investigación.",
    etiquetas: ["matemáticas", "diagnóstico"],
  },
  {
    id: "ins-09",
    titulo: "Cuestionario de acompañamiento académico",
    tipo: "Encuesta",
    nivel: "Licenciatura",
    autorId: "inv-luis",
    anio: 2021,
    fecha: "2021-05-03",
    kpis: ["Acompañamiento académico"],
    reactivos: 20,
    estado: "Estandarizado",
    descripcion: "Acompañamiento de tutores y asesores en el avance académico del estudiantado.",
    etiquetas: ["tutoría", "acompañamiento"],
  },
  {
    id: "ins-10",
    titulo: "Escala de bienestar docente",
    tipo: "Encuesta",
    nivel: "Posgrado",
    autorId: "inv-mar",
    anio: 2025,
    fecha: "2025-10-10",
    kpis: ["Bienestar docente", "Tasa de respuesta"],
    reactivos: 30,
    estado: "En revisión",
    descripcion: "Agotamiento, satisfacción laboral y apoyo institucional percibido.",
    etiquetas: ["docentes", "bienestar"],
  },
  {
    id: "ins-11",
    titulo: "Entrevista a egresadas de licenciatura",
    tipo: "Entrevista",
    nivel: "Licenciatura",
    autorId: "inv-mar",
    anio: 2023,
    fecha: "2023-03-17",
    kpis: ["Inserción laboral"],
    reactivos: 16,
    estado: "Estandarizado",
    descripcion: "Trayectorias laborales y valoración de la formación recibida.",
    etiquetas: ["egreso", "empleabilidad"],
  },
  {
    id: "ins-12",
    titulo: "Prueba de alfabetización académica",
    tipo: "Prueba estandarizada",
    nivel: "Posgrado",
    autorId: "inv-mar",
    anio: 2022,
    fecha: "2022-08-24",
    kpis: ["Alfabetización académica", "Nivel de logro"],
    reactivos: 32,
    estado: "Estandarizado",
    descripcion:
      "Lectura crítica, redacción académica y uso de fuentes en estudiantes de posgrado.",
    etiquetas: ["lenguaje", "escritura"],
  },
  {
    id: "ins-13",
    titulo: "Encuesta de deserción escolar",
    tipo: "Encuesta",
    nivel: "Licenciatura",
    autorId: "inv-jor",
    anio: 2024,
    fecha: "2024-01-04",
    kpis: ["Retención escolar", "Tasa de respuesta"],
    reactivos: 26,
    estado: "Estandarizado",
    descripcion: "Factores económicos, escolares y personales asociados al abandono.",
    etiquetas: ["deserción", "abandono"],
  },
  {
    id: "ins-14",
    titulo: "Guía de entrevista a coordinadores de programa",
    tipo: "Entrevista",
    nivel: "Posgrado",
    autorId: "inv-jor",
    anio: 2021,
    fecha: "2021-06-11",
    kpis: ["Liderazgo directivo"],
    reactivos: 15,
    estado: "Borrador",
    descripcion: "Gestión académica, liderazgo y toma de decisiones en programas universitarios.",
    etiquetas: ["gestión", "liderazgo"],
  },
  {
    id: "ins-15",
    titulo: "Prueba de competencias digitales universitarias",
    tipo: "Prueba estandarizada",
    nivel: "Licenciatura",
    autorId: "inv-jor",
    anio: 2025,
    fecha: "2025-11-18",
    kpis: ["Competencias digitales", "Nivel de logro"],
    reactivos: 50,
    estado: "En revisión",
    descripcion: "Búsqueda de información, seguridad digital y creación de contenidos.",
    etiquetas: ["competencias", "digital"],
  },
];

export const kpis: Kpi[] = [
  {
    id: "kpi-1",
    etiqueta: "Instrumentos registrados",
    valor: "15",
    variacion: 12,
    detalle: "vs. trimestre anterior",
  },
  { id: "kpi-2", etiqueta: "Estandarizados", valor: "9", variacion: 8, detalle: "60% del acervo" },
  {
    id: "kpi-3",
    etiqueta: "En revisión",
    valor: "4",
    variacion: -3,
    detalle: "tiempo medio: 9 días",
  },
  {
    id: "kpi-4",
    etiqueta: "Investigadores activos",
    valor: "4",
    variacion: 0,
    detalle: "en los últimos 30 días",
  },
  {
    id: "kpi-5",
    etiqueta: "Reactivos totales",
    valor: "405",
    variacion: 21,
    detalle: "en todo el repositorio",
  },
  {
    id: "kpi-6",
    etiqueta: "Consultas al chat",
    valor: "238",
    variacion: 34,
    detalle: "últimos 30 días",
  },
  {
    id: "kpi-7",
    etiqueta: "Investigaciones abiertas",
    valor: "3",
    variacion: 5,
    detalle: "con al menos 1 instrumento",
  },
  {
    id: "kpi-8",
    etiqueta: "Nivel más cubierto",
    valor: "Licenciatura",
    variacion: 4,
    detalle: "8 instrumentos",
  },
];

export const noticias: Noticia[] = [
  {
    id: "not-1",
    titulo: "Nueva guía de estandarización de reactivos",
    fecha: "2026-09-18",
    resumen:
      "Publicamos los criterios mínimos para dar por estandarizado un instrumento en INDAGATA.",
  },
  {
    id: "not-2",
    titulo: "Convocatoria: investigación en educación superior",
    fecha: "2026-09-10",
    resumen:
      "Se abre registro para proyectos colaborativos sobre permanencia en programas universitarios.",
  },
  {
    id: "not-3",
    titulo: "El chat de IA ya cita la fuente del reactivo",
    fecha: "2026-08-29",
    resumen: "Cada respuesta incluye el instrumento y el número de reactivo de origen.",
  },
  {
    id: "not-4",
    titulo: "Tres nuevas pruebas de alfabetización académica universitaria",
    fecha: "2026-08-14",
    resumen: "Incorporadas al acervo tras revisión metodológica del comité.",
  },
  {
    id: "not-5",
    titulo: "Taller en línea: diseño de entrevistas semiestructuradas",
    fecha: "2026-07-30",
    resumen: "Sesión de dos horas con ejemplos del repositorio y ejercicios prácticos.",
  },
];

export const catalogoKpis: KpiCatalogo[] = [
  {
    id: "cat-01",
    nombre: "Comprensión lectora",
    descripcionCorta: "Capacidad de los estudiantes para entender e interpretar textos.",
    queEs:
      "Indicador que refleja el nivel con que los estudiantes comprenden, interpretan y usan información contenida en textos escritos.",
    queMide:
      "Mide el porcentaje de estudiantes que alcanzan el nivel de logro esperado en pruebas de comprensión lectora aplicadas en los instrumentos de la investigación.",
    comoSeMide:
      "Se aplica una prueba estandarizada con reactivos de opción múltiple y respuesta construida sobre textos narrativos e informativos. Se califica por rúbrica de 4 niveles.",
    formula: "% Logro = (Alumnos en nivel esperado / Total evaluados) × 100",
    infoGeneral:
      "Indicador alineado con marcos de evaluación de la lectura en educación superior y rúbricas institucionales de comprensión de textos académicos.",
    icono: "BookOpen",
    etiquetas: ["lectura", "comprensión", "universitaria", "evaluación"],
  },
  {
    id: "cat-02",
    nombre: "Tasa de respuesta",
    descripcionCorta: "Porcentaje de participantes que completan el instrumento.",
    queEs:
      "Proporción de cuestionarios o entrevistas completados respecto al total de participantes convocados.",
    queMide:
      "Mide la cobertura efectiva del instrumento y permite estimar posibles sesgos por no respuesta.",
    comoSeMide:
      "Se contabilizan los instrumentos aplicados con al menos el 80% de los reactivos respondidos dividido entre el total de participantes en muestra.",
    formula: "TR = (Instrumentos completos / Participantes convocados) × 100",
    infoGeneral:
      "Una tasa de respuesta mayor al 70% se considera aceptable en investigación educativa cuantitativa (Groves et al., 2009).",
    icono: "ClipboardCheck",
    etiquetas: ["respuesta", "cobertura", "encuesta"],
  },
  {
    id: "cat-03",
    nombre: "Nivel de logro",
    descripcionCorta: "Distribución de estudiantes por nivel de desempeño en pruebas.",
    queEs:
      "Clasificación del desempeño estudiantil en cuatro niveles: Insuficiente, Básico, Satisfactorio y Destacado.",
    queMide:
      "Mide la distribución porcentual de los estudiantes evaluados en cada nivel de desempeño para un área de conocimiento.",
    comoSeMide:
      "Los puntajes brutos se convierten a escala estándar (0-100) y se asigna nivel según puntos de corte establecidos.",
    formula: "% Nivel_k = (Alumnos en nivel k / Total evaluados) × 100",
    infoGeneral:
      "Metodología basada en los estándares de exámenes de egreso de educación superior (EGEL del CENEVAL) y en rúbricas institucionales de evaluación de aprendizajes.",
    icono: "BarChart2",
    etiquetas: ["logro", "desempeño", "prueba", "estándares"],
  },
  {
    id: "cat-04",
    nombre: "Retención escolar",
    descripcionCorta: "Porcentaje de alumnos que permanecen inscritos al finalizar el ciclo.",
    queEs:
      "Indicador que mide la capacidad del sistema educativo para mantener a los estudiantes matriculados desde el inicio hasta el final del ciclo escolar.",
    queMide:
      "Mide el porcentaje de alumnos que continúan inscritos al término del grado o nivel, sin abandono ni deserción.",
    comoSeMide:
      "Se compara la matrícula inicial con la matrícula al cierre del ciclo usando registros de control escolar y los instrumentos de seguimiento.",
    formula: "RE = (Matrícula final / Matrícula inicial) × 100",
    infoGeneral:
      "La retención es uno de los indicadores prioritarios del Sistema Nacional de Indicadores Educativos (SNIE) de la SEP.",
    icono: "Users",
    etiquetas: ["retención", "deserción", "permanencia", "matrícula"],
  },
  {
    id: "cat-05",
    nombre: "Uso de TIC",
    descripcionCorta: "Grado de integración tecnológica en las prácticas docentes.",
    queEs:
      "Indicador que refleja con qué frecuencia e intensidad los docentes incorporan tecnologías de la información y comunicación en sus actividades de enseñanza.",
    queMide:
      "Mide el porcentaje de sesiones observadas o reportadas donde el docente usa al menos una herramienta TIC con propósito pedagógico.",
    comoSeMide:
      "Se aplica guía de observación o cuestionario de autoinforme con escala Likert de 5 puntos sobre frecuencia de uso semanal.",
    formula: "% Uso TIC = (Sesiones con TIC / Total sesiones observadas) × 100",
    infoGeneral:
      "Indicador alineado con el Marco de Competencias Docentes en Materia Digital (UNESCO, 2019).",
    icono: "Monitor",
    etiquetas: ["TIC", "tecnología", "docentes", "digital"],
  },
  {
    id: "cat-06",
    nombre: "Desarrollo socioemocional",
    descripcionCorta: "Nivel de competencias emocionales y sociales en estudiantes.",
    queEs:
      "Indicador que evalúa el desarrollo de habilidades para regular emociones, establecer relaciones positivas y tomar decisiones responsables.",
    queMide:
      "Mide el porcentaje de estudiantes que demuestran competencias socioemocionales esperadas para su nivel de desarrollo.",
    comoSeMide:
      "Se usa observación estructurada y escalas de autoinforme con rúbricas validadas para estudiantes universitarios.",
    formula: "% Desarrollo = (Estudiantes con nivel esperado / Total evaluados) × 100",
    infoGeneral:
      "Basado en marcos de aprendizaje socioemocional aplicados a la formación universitaria y al desarrollo de competencias transversales.",
    icono: "Heart",
    etiquetas: ["socioemocional", "emociones", "universitarios", "habilidades"],
  },
  {
    id: "cat-07",
    nombre: "Motivación académica",
    descripcionCorta: "Nivel de motivación intrínseca y extrínseca hacia el aprendizaje.",
    queEs:
      "Indicador que evalúa el grado de motivación que presentan los estudiantes hacia sus actividades escolares, distinguiendo entre motivación intrínseca (por el placer de aprender) y extrínseca (por recompensas externas).",
    queMide:
      "Mide puntuaciones promedio en escalas validadas de motivación intrínseca, extrínseca y desmotivación.",
    comoSeMide:
      "Se aplica la Escala de Motivación Académica (EMA) adaptada al contexto mexicano con 28 ítems en escala Likert 1-7.",
    formula: "Puntuación media = Σ(puntajes ítems) / n_ítems",
    infoGeneral:
      "Basado en la Teoría de la Autodeterminación (Deci & Ryan, 1985). La adaptación mexicana fue validada con estudiantes universitarios.",
    icono: "Zap",
    etiquetas: ["motivación", "universitarios", "actitudes", "aprendizaje"],
  },
  {
    id: "cat-08",
    nombre: "Acompañamiento académico",
    descripcionCorta:
      "Grado de acompañamiento tutorial recibido por el estudiantado universitario.",
    queEs:
      "Indicador que mide el nivel de acompañamiento de tutores, asesores y mentores en el avance académico de los estudiantes.",
    queMide:
      "Mide la frecuencia e intensidad del acompañamiento en asesorías, seguimiento de trayectoria y comunicación con el profesorado.",
    comoSeMide:
      "Se aplica cuestionario de autoinforme al estudiantado con 20 ítems agrupados en 3 dimensiones: asesoría académica, comunicación con el profesorado y participación en programas de tutoría.",
    formula: "Índice AA = (Σ puntuaciones dimensiones) / 3",
    infoGeneral:
      "El acompañamiento académico es uno de los predictores más consistentes de la permanencia y el logro en educación superior (Tinto, 2012). Rango: 1-5.",
    icono: "Home",
    etiquetas: ["acompañamiento", "tutoría", "participación", "universitarios"],
  },
  {
    id: "cat-09",
    nombre: "Bienestar docente",
    descripcionCorta: "Estado de salud emocional y satisfacción laboral del profesorado.",
    queEs:
      "Indicador multidimensional que evalúa el bienestar subjetivo de los docentes en su entorno laboral, considerando aspectos emocionales, relacionales e institucionales.",
    queMide:
      "Mide niveles de agotamiento emocional, satisfacción laboral y percepción de apoyo institucional en el profesorado.",
    comoSeMide:
      "Se aplica escala adaptada del Maslach Burnout Inventory (MBI) y la Escala de Satisfacción Laboral Docente, 30 ítems en total.",
    formula: "IBD = (Satisfacción − Agotamiento + Apoyo) / 3",
    infoGeneral:
      "El bienestar docente impacta directamente en la calidad del proceso de enseñanza-aprendizaje (OCDE, 2019). Rango: −1 a 1.",
    icono: "Smile",
    etiquetas: ["bienestar", "docentes", "salud mental", "satisfacción"],
  },
  {
    id: "cat-10",
    nombre: "Inserción laboral",
    descripcionCorta: "Porcentaje de egresados que se incorporan al mercado laboral.",
    queEs:
      "Indicador de seguimiento de egresados que mide la tasa de inserción en el mercado laboral en el primer año tras la titulación.",
    queMide:
      "Mide el porcentaje de egresados empleados en su área de formación al año de haber concluido sus estudios.",
    comoSeMide:
      "Se aplica entrevista semiestructurada o cuestionario a egresados entre 6 y 18 meses después de concluir sus estudios.",
    formula: "% IL = (Egresados empleados en área / Total egresados encuestados) × 100",
    infoGeneral:
      "Indicador solicitado por la SEP para el seguimiento de la pertinencia de los programas de nivel superior (ANUIES, 2020).",
    icono: "Briefcase",
    etiquetas: ["egresados", "empleo", "superior", "trayectorias"],
  },
  {
    id: "cat-11",
    nombre: "Alfabetización académica",
    descripcionCorta:
      "Dominio de la lectura crítica y la escritura académica en el estudiantado universitario.",
    queEs:
      "Indicador que evalúa las competencias de lectura crítica, redacción académica y uso ético de fuentes propias de la comunicación científica.",
    queMide:
      "Mide el porcentaje de estudiantes que alcanzan el nivel esperado en cada dimensión de la alfabetización académica.",
    comoSeMide:
      "Se aplica una prueba con tareas de síntesis de textos académicos, argumentación escrita y citación de fuentes, calificada por rúbrica.",
    formula: "% Nivel esperado_dim = (Estudiantes en nivel / Total evaluados) × 100",
    infoGeneral:
      "La alfabetización académica es predictor del desempeño en los estudios universitarios y de la producción escrita de posgrado (Carlino, 2013).",
    icono: "MessageCircle",
    etiquetas: ["lenguaje", "universitarios", "escritura", "lectura"],
  },
  {
    id: "cat-12",
    nombre: "Liderazgo directivo",
    descripcionCorta: "Calidad del liderazgo académico de coordinadores de programa.",
    queEs:
      "Indicador que evalúa la capacidad de coordinadores y directores de programa para ejercer un liderazgo académico que mejore los procesos de enseñanza-aprendizaje.",
    queMide:
      "Mide la percepción del liderazgo directivo en dimensiones de gestión curricular, gestión de recursos y clima institucional.",
    comoSeMide:
      "Se aplica guía de entrevista semiestructurada con 15 ítems a coordinadores de programa, con rúbrica de análisis cualitativo posterior.",
    formula: "Índice LD = Media de puntuaciones en 3 dimensiones (escala 1-4)",
    infoGeneral:
      "El liderazgo directivo es uno de los factores institucionales con mayor impacto en el logro (Leithwood, 2010), después de la calidad docente.",
    icono: "Award",
    etiquetas: ["directivos", "liderazgo", "gestión", "universitarios"],
  },
  {
    id: "cat-13",
    nombre: "Razonamiento matemático",
    descripcionCorta: "Capacidad para resolver problemas y aplicar conceptos matemáticos.",
    queEs:
      "Indicador que evalúa la capacidad de los estudiantes para razonar cuantitativamente, resolver problemas y aplicar conceptos matemáticos en situaciones reales.",
    queMide:
      "Mide el porcentaje de estudiantes que alcanzan el nivel esperado en los bloques de estadística, modelación matemática y resolución de problemas aplicados.",
    comoSeMide:
      "Se aplica prueba diagnóstica con 45 reactivos organizados en 3 bloques, con tiempo límite de 90 minutos.",
    formula: "% Logro matemático = (Reactivos correctos / Total reactivos) × 100 por bloque",
    infoGeneral:
      "Indicador alineado con marcos de referencia de razonamiento cuantitativo para la educación superior. Aplicable en programas de licenciatura y posgrado.",
    icono: "Calculator",
    etiquetas: ["matemáticas", "razonamiento", "universitarios", "cuantitativo"],
  },
  {
    id: "cat-14",
    nombre: "Competencias digitales",
    descripcionCorta: "Nivel de habilidades digitales en estudiantes universitarios.",
    queEs:
      "Indicador que evalúa las competencias de los estudiantes para buscar información, comunicarse, crear contenido y actuar con seguridad en entornos digitales.",
    queMide:
      "Mide el nivel de competencia digital en cinco áreas: información, comunicación, creación de contenidos, seguridad y resolución de problemas.",
    comoSeMide:
      "Se aplica prueba de competencias digitales con 50 ítems basada en el marco DigComp 2.1 (JRC, 2017), tiempo 60 minutos.",
    formula: "Nivel CD = Puntuación total / 5 áreas (escala 1-3: básico/intermedio/avanzado)",
    infoGeneral:
      "Marco de referencia: DigComp 2.1 (Vuorikari et al., 2016). La SEP incorporó competencias digitales como eje transversal desde el Plan 2022.",
    icono: "Laptop",
    etiquetas: ["digital", "universitarios", "TIC", "DigComp"],
  },
  {
    id: "cat-15",
    nombre: "Clima escolar",
    descripcionCorta: "Percepción del ambiente de convivencia y seguridad en la escuela.",
    queEs:
      "Indicador que mide la percepción de estudiantes, docentes y directivos sobre el ambiente de convivencia, seguridad y relaciones interpersonales en la escuela.",
    queMide:
      "Mide puntuaciones en dimensiones de convivencia, seguridad percibida, relación alumno-docente y normas institucionales.",
    comoSeMide:
      "Se aplica cuestionario de 35 ítems en escala Likert 1-5 a estudiantes universitarios, con versiones paralelas para docentes y autoridades académicas.",
    formula: "ICE = Media ponderada de las 4 dimensiones (escala 1-5)",
    infoGeneral:
      "El clima institucional positivo se asocia con menores tasas de abandono y mayor logro académico (UNESCO, 2018). Aplicable en educación superior.",
    icono: "Shield",
    etiquetas: ["clima", "convivencia", "seguridad", "universitarios"],
  },
];
