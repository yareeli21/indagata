import type {
  BusquedaEspacio,
  DetalleInstrumento,
  Instrumento,
  MapaEspacio,
  PreguntaInstrumento,
  TipoPuntoEspacio,
  VecinosEspacio,
} from "@/types";
import { API_URL, pedir } from "./client";

interface OpcionesMapa {
  /** Incluir los chunks del RAG (fuente provisional por ahora). */
  chunks?: boolean;
  /** Vista alineada: quita la brecha entre grupos (solo cambia el dibujo). */
  alinear?: boolean;
}

/**
 * Mapa 2D del espacio de embeddings (KPIs, instrumentos y, opcionalmente,
 * chunks) proyectado con PCA. GET /visualizacion/espacio/mapa (visualization-service).
 */
export function getMapaEspacio({
  chunks = false,
  alinear = false,
}: OpcionesMapa = {}): Promise<MapaEspacio> {
  return pedir<MapaEspacio>(
    `${API_URL}/visualizacion/espacio/mapa?chunks=${chunks}&alinear=${alinear}`,
    { auth: true },
  );
}

/**
 * KPIs, instrumentos y chunks más parecidos a un punto, por similitud coseno en
 * el espacio original. GET /visualizacion/espacio/vecinos/{tipo}/{ref}
 */
export function getVecinosEspacio(
  tipo: TipoPuntoEspacio,
  ref: string,
  k = 6,
): Promise<VecinosEspacio> {
  return pedir<VecinosEspacio>(
    `${API_URL}/visualizacion/espacio/vecinos/${tipo}/${encodeURIComponent(ref)}?k=${k}`,
    { auth: true },
  );
}

interface DetalleInstrumentoDTO {
  instrumento: Instrumento;
  dublin_core: Record<string, unknown>;
  enriquecidos: Record<string, unknown>;
  preguntas: PreguntaInstrumento[];
}

/** Ficha completa de un instrumento. GET /visualizacion/catalogo/{id} */
export async function getDetalleInstrumento(id: string): Promise<DetalleInstrumento> {
  const d = await pedir<DetalleInstrumentoDTO>(`${API_URL}/visualizacion/catalogo/${id}`, {
    auth: true,
  });
  return {
    instrumento: d.instrumento,
    dublinCore: d.dublin_core,
    enriquecidos: d.enriquecidos,
    preguntas: d.preguntas,
  };
}

/**
 * Proyecta una frase en el espacio (mismo modelo y PCA) y devuelve sus vecinos.
 * POST /visualizacion/espacio/buscar
 */
export function buscarEnEspacio(texto: string, k = 6): Promise<BusquedaEspacio> {
  return pedir<BusquedaEspacio>(`${API_URL}/visualizacion/espacio/buscar`, {
    method: "POST",
    auth: true,
    body: { texto, k },
  });
}
