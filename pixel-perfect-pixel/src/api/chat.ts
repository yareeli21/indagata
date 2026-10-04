import type { ContextoInvestigacion, FuenteChat, ModeloLLM } from "@/types";
import { API_URL, leerToken } from "./client";

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

/** Datos del evento SSE `fuentes` emitido por el visualization-service. */
interface EventoFuentes {
  fuentes: FuenteChat[];
}

/** Datos del evento SSE `token`. */
interface EventoToken {
  t: string;
}

/**
 * Envía una pregunta al RAG y recibe la respuesta por streaming (SSE sobre fetch).
 * POST ${API_URL}/rag/chat con Authorization Bearer. El servicio emite eventos
 * `token` (fragmentos), un `fuentes` al final y `fin` para cerrar (§4.9 del diseño).
 *
 * @param onToken  se llama con cada fragmento de texto generado
 * @param onDone   se llama al terminar, con las fuentes recuperadas
 * @returns        función para cancelar el streaming (AbortController)
 */
export function enviarMensaje(
  pregunta: string,
  _contexto: ContextoInvestigacion,
  modelo: ModeloLLM,
  onToken: (token: string) => void,
  onDone: (fuentes: FuenteChat[]) => void,
  investigacionId: string,
  instrumentoIds?: string[],
): () => void {
  void _contexto; // el contexto se usa en el prompt del backend; aquí no viaja

  const controlador = new AbortController();
  const ids = instrumentoIds ?? getInstrumentosDeInvestigacion(investigacionId);

  const encabezados: Record<string, string> = { "Content-Type": "application/json" };
  const token = leerToken();
  if (token) encabezados.Authorization = `Bearer ${token}`;

  let fuentes: FuenteChat[] = [];

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
        top_k: 5,
      }),
      signal: controlador.signal,
    });

    if (!respuesta.ok || !respuesta.body) {
      onDone(fuentes);
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
            if (t) onToken(t);
          } catch {
            /* trozo no-JSON: se ignora */
          }
        } else if (eventoActual === "fuentes") {
          try {
            fuentes = (JSON.parse(datos) as EventoFuentes).fuentes ?? [];
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

    onDone(fuentes);
  }

  ejecutar().catch(() => {
    // Cancelación (AbortError) o fallo de red: no se notifica onDone en aborto.
    if (!controlador.signal.aborted) onDone(fuentes);
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
  if (token) encabezados.Authorization = `Bearer ${token}`;

  await fetch(`${API_URL}/rag/index`, {
    method: "POST",
    headers: encabezados,
    body: JSON.stringify({ investigacionId, instrumentoIds }),
  });
}
