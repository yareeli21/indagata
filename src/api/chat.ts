import { instrumentos, investigadores } from "@/mocks/data";
import type {
  ContextoInvestigacion,
  FuenteChat,
  ModeloLLM,
} from "@/types";
import { simularRed } from "./client";

export const MODELOS_DISPONIBLES: { id: ModeloLLM; etiqueta: string }[] = [
  { id: "gpt-4o", etiqueta: "GPT-4o" },
  { id: "gpt-4o-mini", etiqueta: "GPT-4o mini" },
  { id: "gemini-1.5-pro", etiqueta: "Gemini 1.5 Pro" },
  { id: "claude-3-5-sonnet", etiqueta: "Claude 3.5 Sonnet" },
];

/** Frases de relleno para simular respuestas del asistente */
const FRAGMENTOS_RESPUESTA = [
  "Basándome en los instrumentos de tu investigación activa, ",
  "De acuerdo con la evidencia disponible en el acervo, ",
  "Los instrumentos seleccionados sugieren que ",
  "A partir del análisis de los reactivos registrados, ",
];

const CONTINUACIONES = [
  "existe una correlación entre la comprensión lectora y el nivel de acompañamiento familiar documentada en varios reactivos. Los instrumentos estandarizados muestran patrones consistentes en distintos niveles educativos.",
  "los factores socioemocionales inciden significativamente en los indicadores de retención escolar. Los instrumentos de tipo encuesta aportan datos cuantitativos que complementan las entrevistas semiestructuradas.",
  "la apropiación tecnológica por parte del profesorado varía considerablemente según el nivel y la zona geográfica, tal como reflejan las guías de observación y las entrevistas especializadas.",
  "los niveles de logro en comprensión lectora presentan diferencias estadísticamente significativas entre primaria urbana y rural, según los datos de los instrumentos estandarizados.",
];

function elegirAlAzar<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

/** Genera fuentes simuladas basadas en los instrumentos reales del mock */
function generarFuentes(n = 2): FuenteChat[] {
  const muestra = [...instrumentos]
    .sort(() => Math.random() - 0.5)
    .slice(0, n);

  return muestra.map((ins) => {
    const inv = investigadores.find((x) => x.id === ins.autorId);
    return {
      instrumentoId: ins.id,
      titulo: ins.titulo,
      tipo: ins.tipo,
      investigador: inv?.nombre ?? "—",
      kpis: ins.kpis.slice(0, 2),
      fragmento: ins.descripcion,
    };
  });
}

/**
 * Simula un endpoint de chat con streaming.
 * Futuro: POST /chat/mensaje con SSE / WebSocket.
 *
 * @param onToken  se llama con cada "token" generado durante el streaming
 * @param onDone   se llama cuando la generación termina, con las fuentes
 * @returns        función para cancelar el streaming
 */
export function enviarMensaje(
  _pregunta: string,
  _contexto: ContextoInvestigacion,
  _modelo: ModeloLLM,
  onToken: (token: string) => void,
  onDone: (fuentes: FuenteChat[]) => void,
): () => void {
  const respuestaCompleta =
    elegirAlAzar(FRAGMENTOS_RESPUESTA) + elegirAlAzar(CONTINUACIONES);

  const palabras = respuestaCompleta.split(" ");
  let i = 0;
  let cancelado = false;

  // Simula streaming palabra a palabra con intervalos variables
  function emitirSiguiente() {
    if (cancelado || i >= palabras.length) {
      if (!cancelado) {
        onDone(generarFuentes(2));
      }
      return;
    }
    onToken((i === 0 ? "" : " ") + palabras[i]);
    i++;
    const delay = 40 + Math.random() * 60;
    timerId = window.setTimeout(emitirSiguiente, delay);
  }

  let timerId = window.setTimeout(emitirSiguiente, 300);

  return () => {
    cancelado = true;
    window.clearTimeout(timerId);
  };
}

/** Futuro: POST /investigacion/{id}/contexto */
export function guardarContexto(
  _investigacionId: string,
  contexto: ContextoInvestigacion,
): Promise<void> {
  return simularRed(undefined, 200).then(() => {
    void contexto; // sustituir por fetch en producción
  });
}
