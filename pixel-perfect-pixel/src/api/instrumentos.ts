import type {
  EstadoInstrumento,
  FormatoDescarga,
  Instrumento,
  InstrumentoRelacionado,
  Investigador,
  KpiDeInstrumento,
  NivelCoincidencia,
  NivelEducativo,
  RazonCoincidencia,
  TipoInstrumento,
} from "@/types";
import { API_URL, ErrorHttp, avisarSesionExpirada, leerToken, pedir } from "./client";

/**
 * DTO de instrumento que devuelven el instrument-service y el visualization-service
 * (vía api-gateway). Espeja `Instrumento` y añade campos informativos que el
 * frontend descarta al mapear a `Instrumento`.
 */
interface InstrumentoDTO {
  id: string;
  titulo: string;
  tipo: TipoInstrumento;
  nivel: NivelEducativo;
  autorId: string;
  anio: number;
  fecha: string;
  kpis: string[];
  reactivos: number;
  estado: EstadoInstrumento;
  descripcion: string;
  etiquetas: string[];
  idProcesado?: string | null;
}

/**
 * Mapeo campo a campo DTO→`Instrumento`. NO se usa spread para no colar campos
 * informativos (interfaz cerrada); se asignan explícitamente los 12 campos.
 */
function mapear(d: InstrumentoDTO): Instrumento {
  return {
    id: d.id,
    titulo: d.titulo,
    tipo: d.tipo,
    nivel: d.nivel,
    autorId: d.autorId,
    anio: d.anio,
    fecha: d.fecha,
    kpis: d.kpis,
    reactivos: d.reactivos,
    estado: d.estado,
    descripcion: d.descripcion,
    etiquetas: d.etiquetas,
  };
}

export async function getInstrumentos(): Promise<Instrumento[]> {
  const dtos = await pedir<InstrumentoDTO[]>(`${API_URL}/instrumentos`, { auth: true });
  return dtos.map(mapear);
}

export async function getInstrumento(id: string): Promise<Instrumento | null> {
  try {
    const dto = await pedir<InstrumentoDTO>(`${API_URL}/instrumentos/${id}`, { auth: true });
    return mapear(dto);
  } catch (e) {
    if ((e as ErrorHttp).status === 404) return null;
    throw e;
  }
}

/** Autores del acervo (visualization-service). GET /visualizacion/investigadores */
export function getInvestigadores(): Promise<Investigador[]> {
  return pedir<Investigador[]>(`${API_URL}/visualizacion/investigadores`, { auth: true });
}

/** Catálogo de KPIs usados por los instrumentos. GET /instrumentos/kpis/catalogo */
export function getCatalogoKpis(): Promise<string[]> {
  return pedir<string[]>(`${API_URL}/instrumentos/kpis/catalogo`, { auth: true });
}

/** DELETE /instrumentos/{id}: `id` es str(id_crudo) (borra también archivos y vectores). */
export function eliminarInstrumento(id: string): Promise<void> {
  return pedir<void>(`${API_URL}/instrumentos/${id}`, { method: "DELETE", auth: true });
}

/** Nombre del archivo desde Content-Disposition (prefiere `filename*` UTF-8). */
function nombreDeDescarga(cabecera: string | null, defecto: string): string {
  if (!cabecera) return defecto;
  const utf8 = /filename\*=UTF-8''([^;]+)/i.exec(cabecera);
  if (utf8?.[1]) return decodeURIComponent(utf8[1]);
  const simple = /filename="?([^";]+)"?/i.exec(cabecera);
  return simple?.[1] ?? defecto;
}

/**
 * Descarga el instrumento: crudo (tal cual lo subió su autor), JSON estandarizado
 * o .sav (encuestas). GET /visualizacion/descargas/{id}?formato=...
 * El backend aplica la regla: de instrumentos ajenos solo se descarga el crudo.
 */
export async function descargarInstrumento(id: string, formato: FormatoDescarga): Promise<void> {
  const headers: Record<string, string> = {};
  const token = leerToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const respuesta = await fetch(
    `${API_URL}/visualizacion/descargas/${encodeURIComponent(id)}?formato=${formato}`,
    { headers },
  );
  if (!respuesta.ok) {
    if (respuesta.status === 401) avisarSesionExpirada();
    let detalle = "";
    try {
      const datos = (await respuesta.json()) as { detail?: unknown };
      if (typeof datos?.detail === "string") detalle = datos.detail;
    } catch {
      /* cuerpo no-JSON */
    }
    const error: ErrorHttp = new Error(
      detalle || `No se pudo descargar (HTTP ${respuesta.status}).`,
    );
    error.status = respuesta.status;
    throw error;
  }

  const extension = formato === "crudo" ? "dat" : formato;
  const nombre = nombreDeDescarga(
    respuesta.headers.get("Content-Disposition"),
    `instrumento-${id}.${extension}`,
  );
  const url = URL.createObjectURL(await respuesta.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = nombre;
  a.click();
  URL.revokeObjectURL(url);
}

interface RelacionadoDTO {
  instrumento: InstrumentoDTO;
  nivel: NivelCoincidencia;
  coincideCon: string[];
  razones: RazonCoincidencia[];
}

/**
 * Instrumentos de OTROS autores relacionados con la selección, por KPIs en común,
 * nivel educativo y similitud semántica de su ficha (vectores en ChromaDB).
 * POST /visualizacion/relacionados
 */
export async function buscarRelacionados(
  seleccionIds: string[],
  autorId: string,
): Promise<InstrumentoRelacionado[]> {
  if (seleccionIds.length === 0) return [];
  const datos = await pedir<RelacionadoDTO[]>(`${API_URL}/visualizacion/relacionados`, {
    method: "POST",
    auth: true,
    body: { ids: seleccionIds, autorId },
  });
  return datos.map((r) => ({
    instrumento: mapear(r.instrumento),
    nivel: r.nivel,
    coincideCon: r.coincideCon,
    razones: r.razones,
  }));
}

/**
 * KPIs asociados a un instrumento y, para cada uno, las preguntas del instrumento
 * que mejor lo miden. GET /visualizacion/instrumentos/{id}/kpis
 */
export function getKpisDeInstrumento(id: string): Promise<KpiDeInstrumento[]> {
  return pedir<KpiDeInstrumento[]>(
    `${API_URL}/visualizacion/instrumentos/${encodeURIComponent(id)}/kpis`,
    {
      auth: true,
    },
  );
}
