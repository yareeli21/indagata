import type {
  CalificacionRespuesta,
  ContextoInvestigacion,
  DocumentoFuente,
  Mensaje,
  MetricasRespuesta,
  ModeloLLM,
  ResultadoChat,
} from "@/types";
import { API_URL, avisarSesionExpirada, leerToken, pedir } from "./client";

export const MODELOS_DISPONIBLES: { id: ModeloLLM; etiqueta: string }[] = [
  { id: "llama3.2:3b", etiqueta: "Llama 3.2 (3B) — local" },
];

// ── Selección de instrumentos por investigación (persistencia en cliente) ───────

const CLAVE_INSTRUMENTOS_POR_INVESTIGACION = "indagata.instrumentosPorInvestigacion";

function leerMapa(): Record<string, string[]> {
  try {
    const crudo = window.localStorage.getItem(CLAVE_INSTRUMENTOS_POR_INVESTIGACION);
    if (!crudo) return {};
    const datos = JSON.parse(crudo) as Record<string, string[]>;
    return datos && typeof datos === "object" ? datos : {};
  } catch {
    return {};
  }
}

function escribirMapa(mapa: Record<string, string[]>): void {
  try {
    window.localStorage.setItem(CLAVE_INSTRUMENTOS_POR_INVESTIGACION, JSON.stringify(mapa));
  } catch {
    /* almacenamiento no disponible */
  }
}

/** Persiste los instrumentos (ids = str(id_crudo)) juntados para una investigación. */
export function setInstrumentosDeInvestigacion(
  investigacionId: string,
  instrumentoIds: string[],
): void {
  const mapa = leerMapa();
  mapa[investigacionId] = instrumentoIds;
  escribirMapa(mapa);
}

/** Devuelve los instrumentos juntados de una investigación (vacío ⇒ []). */
export function getInstrumentosDeInvestigacion(investigacionId: string): string[] {
  return leerMapa()[investigacionId] ?? [];
}

// ── Chat RAG con streaming SSE ──────────────────────────────────────────────────

/** Datos del evento SSE `fuentes` emitido por el visualization-service (al final). */
type EventoFuentes = Partial<ResultadoChat> & {
  /** Respuesta final con las citas [Fuente n] que el servicio añadió donde el modelo no citó. */
  respuesta?: string;
};

/** Datos del evento SSE `token`. */
interface EventoToken {
  t: string;
}

/**
 * Envía una pregunta al RAG y recibe la respuesta por streaming (SSE sobre fetch).
 * POST ${API_URL}/rag/chat con Authorization Bearer. El servicio emite eventos
 * `token` (fragmentos), un `fuentes` al final y `fin` para cerrar (§4.9 del diseño).
 * El evento `fuentes` trae además las referencias (glosario o ayuda), la decisión
 * del dominio, la ruta y el id de la consulta en rag_log.
 *
 * @param onToken        se llama con cada fragmento de texto generado
 * @param onDone         se llama al terminar, con las fuentes y la decisión
 * @param instrumentoIds alcance explícito; [] = todo el acervo; sin indicar = la investigación
 * @param anteriores     mensajes previos de la sesión: el servicio usa los últimos 4 para entender
 *                       preguntas de seguimiento («¿y de ellos…?»)
 * @returns              función para cancelar el streaming (AbortController)
 */
export function enviarMensaje(
  pregunta: string,
  contexto: ContextoInvestigacion,
  modelo: ModeloLLM,
  onToken: (token: string) => void,
  onDone: (resultado: ResultadoChat) => void,
  investigacionId: string,
  instrumentoIds?: string[],
  anteriores: Mensaje[] = [],
): () => void {
  const controlador = new AbortController();
  const ids = instrumentoIds ?? getInstrumentosDeInvestigacion(investigacionId);

  const encabezados: Record<string, string> = { "Content-Type": "application/json" };
  const token = leerToken();
  if (token) encabezados["Authorization"] = `Bearer ${token}`;

  let resultado: ResultadoChat = { fuentes: [], referencias: [] };
  let recibioTexto = false;

  async function ejecutar(): Promise<void> {
    const respuesta = await fetch(`${API_URL}/rag/chat`, {
      method: "POST",
      headers: encabezados,
      body: JSON.stringify({
        investigacionId,
        pregunta,
        instrumentoIds: ids,
        modelo,
        stream: true,
        top_k: 6,
        // Orienta la respuesta hacia la investigación (objetivo, población, nivel).
        contexto,
        historial: historialReciente(anteriores),
      }),
      signal: controlador.signal,
    });

    if (!respuesta.ok || !respuesta.body) {
      // Sin este mensaje la burbuja quedaba vacía y parecía que el chat no respondía.
      if (respuesta.status === 401) {
        onToken("Tu sesión expiró. Vuelve a iniciar sesión para seguir consultando.");
        avisarSesionExpirada();
      } else {
        onToken(
          `No se pudo obtener la respuesta (HTTP ${respuesta.status}). Intenta de nuevo en un momento.`,
        );
      }
      onDone(resultado);
      return;
    }

    const lector = respuesta.body.getReader();
    const decodificador = new TextDecoder();
    let buffer = "";
    let eventoActual = "";

    const procesarLinea = (linea: string): void => {
      if (linea === "") {
        eventoActual = "";
        return;
      }
      if (linea.startsWith("event:")) {
        eventoActual = linea.slice("event:".length).trim();
        return;
      }
      if (linea.startsWith("data:")) {
        const datos = linea.slice("data:".length).trim();
        if (eventoActual === "token") {
          try {
            const { t } = JSON.parse(datos) as EventoToken;
            if (t) {
              recibioTexto = true;
              onToken(t);
            }
          } catch {
            /* trozo no-JSON: se ignora */
          }
        } else if (eventoActual === "fuentes") {
          try {
            const evento = JSON.parse(datos) as EventoFuentes;
            resultado = {
              fuentes: evento.fuentes ?? [],
              referencias: evento.referencias ?? [],
              decision: evento.decision,
              ruta: evento.ruta ?? null,
              consultaId: evento.consultaId ?? null,
              enCache: evento.enCache ?? false,
              latenciaMs: evento.latenciaMs ?? null,
              // Reemplaza el texto que llegó por tokens: es el mismo, con las citas que faltaban.
              ...(evento.respuesta ? { contenido: evento.respuesta } : {}),
            };
          } catch {
            /* se ignora */
          }
        }
      }
    };

    while (true) {
      const { done, value } = await lector.read();
      if (done) break;
      buffer += decodificador.decode(value, { stream: true });
      let corte = buffer.indexOf("\n");
      while (corte !== -1) {
        procesarLinea(buffer.slice(0, corte).replace(/\r$/, ""));
        buffer = buffer.slice(corte + 1);
        corte = buffer.indexOf("\n");
      }
    }

    onDone(resultado);
  }

  ejecutar().catch(() => {
    // Cancelación (AbortError) o fallo de red: no se notifica onDone en aborto.
    if (!controlador.signal.aborted) {
      if (!recibioTexto) {
        onToken(
          "No se pudo conectar con el chat. Revisa que los servicios estén encendidos e intenta de nuevo.",
        );
      }
      onDone(resultado);
    }
  });

  return () => controlador.abort();
}

/**
 * Materializa "juntar los instrumentos" de una investigación: persiste la
 * selección en el cliente e indexa en el vector store (POST ${API_URL}/rag/index).
 */
export async function guardarContexto(
  investigacionId: string,
  contexto: ContextoInvestigacion,
  instrumentoIds: string[],
): Promise<void> {
  void contexto; // el contexto no se indexa; alimenta el prompt en el chat
  setInstrumentosDeInvestigacion(investigacionId, instrumentoIds);

  const encabezados: Record<string, string> = { "Content-Type": "application/json" };
  const token = leerToken();
  if (token) encabezados["Authorization"] = `Bearer ${token}`;

  const respuesta = await fetch(`${API_URL}/rag/index`, {
    method: "POST",
    headers: encabezados,
    body: JSON.stringify({ investigacionId, instrumentoIds }),
  });
  if (respuesta.status === 401) avisarSesionExpirada();
}

/** Pide calcular las métricas de una respuesta pendiente (bajo demanda); devuelve su estado. */
export function calcularMetricas(consultaId: number): Promise<MetricasRespuesta> {
  return pedir<MetricasRespuesta>(`${API_URL}/rag/consultas/${consultaId}/metricas`, {
    method: "POST",
    auth: true,
  });
}

/** Guarda (o reemplaza) la calificación humana de una respuesta. */
export function calificarRespuesta(
  consultaId: number,
  calificacion: CalificacionRespuesta,
): Promise<CalificacionRespuesta> {
  return pedir<CalificacionRespuesta>(`${API_URL}/rag/consultas/${consultaId}/calificacion`, {
    method: "PUT",
    body: calificacion,
    auth: true,
  });
}

/** Métricas automáticas de una respuesta: «pendiente» hasta que se piden, luego «calculando» y el resultado. */
export function getMetricas(consultaId: number): Promise<MetricasRespuesta> {
  return pedir<MetricasRespuesta>(`${API_URL}/rag/consultas/${consultaId}/metricas`, {
    auth: true,
  });
}

/** Últimos mensajes terminados de la sesión, recortados, para que el servicio entienda los seguimientos. */
function historialReciente(
  mensajes: Mensaje[],
): { rol: "usuario" | "asistente"; texto: string; consultaId?: number }[] {
  return mensajes
    .filter((m) => !m.generando && m.contenido.trim())
    .slice(-4)
    .map((m) => ({
      rol: m.rol === "usuario" ? "usuario" : "asistente",
      texto: m.contenido.slice(0, 1500),
      // El servicio lee de esa consulta de qué trató la respuesta (respondentes, preguntas, criterio).
      ...(m.rol !== "usuario" && m.consultaId ? { consultaId: m.consultaId } : {}),
    }));
}

// ── Trazabilidad de las fuentes ─────────────────────────────────────────────────

/**
 * Tramo [desde, hasta) del documento indexado de un instrumento: las piezas que el chat puede
 * recuperar, en orden. Abre una fuente en la posición de su pasaje (`pasajes[].chunkIndex`).
 * GET ${API_URL}/visualizacion/instrumentos/{id}/documento (máximo 200 por petición).
 */
export async function getDocumentoFuente(
  instrumentoId: string,
  desde: number,
  hasta: number,
): Promise<DocumentoFuente> {
  const params = new URLSearchParams({ desde: String(desde), hasta: String(hasta) });
  return pedir<DocumentoFuente>(
    `${API_URL}/visualizacion/instrumentos/${encodeURIComponent(instrumentoId)}/documento?${params}`,
    { auth: true },
  );
}
