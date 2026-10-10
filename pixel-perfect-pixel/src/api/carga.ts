import type {
  DublinCore,
  KpiSugerido,
  MetadatosTipo,
  NivelEducativo,
  OrigenMetadato,
  ReporteLimpieza,
  TipoInstrumento,
} from "@/types";
import { ANALYSIS_URL, API_URL, leerToken, pedir } from "./client";

// ── Mapeo tipo UI → enum backend ────────────────────────────────────────────────
// La etiqueta de UI (`TIPOS_INSTRUMENTO`) se convierte aquí al vocabulario cerrado
// del dominio que exige el backend (`app/config/constants.py`). Esta capa es la
// frontera donde ocurre la conversión.
const TIPO_UI_A_BACKEND: Record<TipoInstrumento, string> = {
  Encuesta: "encuesta",
  Entrevista: "entrevista",
  "Prueba estandarizada": "prueba_estandarizada",
};

// ── Tipos del backend (upload) ──────────────────────────────────────────────────

/** Resumen de parseo que devuelve el upload (ver instrument-service schemas/upload.py). */
interface ParseoArchivo {
  parser_family: "tabular" | "documento";
  headers?: string[] | null;
  n_columns?: number | null;
  n_rows?: number | null;
  preview_rows?: string[][] | null;
  sheet?: string | null;
  n_chars?: number | null;
  n_words?: number | null;
  n_pages?: number | null;
  text_preview?: string | null;
  encoding?: string | null;
  notes?: string[];
}

interface ArchivoRegistrado {
  nombre_original: string;
  ruta_relativa: string;
  extension: string;
  mime_type: string;
  parser_family: "tabular" | "documento";
  size_bytes: number;
  parseo?: ParseoArchivo | null;
}

interface UploadResponse {
  id_crudo: number;
  id_instrumento: number;
  id_owner: number;
  tipo_instrumento: string;
  estado: string;
  fecha_carga?: string | null;
  archivo_respondido: ArchivoRegistrado;
  archivo_original?: ArchivoRegistrado | null;
  mensaje: string;
}

/** Resultado del paso 1 (subir): ambos ids reales + el reporte de limpieza derivado. */
export interface ResultadoCarga {
  /** PK de raw_data: id canónico (instrument-, metadata-, storage- y visualization-service). */
  idCrudo: number;
  /** PK de instrumento_procesado (lo usa el analysis-service para los KPIs). */
  idInstrumento: number;
  /** Reporte de limpieza derivado del parseo del upload (no hay endpoint propio). */
  reporte: ReporteLimpieza;
}

// ── Helper puro: ParseoArchivo → ReporteLimpieza ─────────────────────────────────

/**
 * Deriva un `ReporteLimpieza` del resumen de parseo del upload.
 *
 * NOTA: la etapa de limpieza (imputación, duplicados, registros vacíos) no forma
 * parte de los servicios actuales; por eso `duplicadosEliminados` y
 * `nulosTratados` son 0 (valor honesto, no inventado). Cuando exista ese
 * endpoint se reemplaza este derivado sin cambiar la forma de `ReporteLimpieza`.
 */
export function mapearParseoALimpieza(parseo: ParseoArchivo | null | undefined): ReporteLimpieza {
  if (!parseo) {
    return { duplicadosEliminados: 0, nulosTratados: 0, columnasNormalizadas: 0, cambios: [] };
  }

  const cambios: ReporteLimpieza["cambios"] = [];

  if (parseo.headers && parseo.headers.length > 0) {
    for (const header of parseo.headers) {
      cambios.push({ campo: "Columna detectada", antes: header, despues: header });
    }
  }

  if (parseo.parser_family === "documento") {
    cambios.push({
      campo: "Texto extraído",
      antes: `${parseo.n_chars ?? 0} caracteres`,
      despues: `${parseo.n_words ?? 0} palabras`,
    });
  }

  for (const nota of parseo.notes ?? []) {
    cambios.push({ campo: "Observación del parser", antes: nota, despues: "" });
  }

  return {
    columnasNormalizadas: parseo.headers?.length ?? 0,
    duplicadosEliminados: 0,
    nulosTratados: 0,
    cambios,
  };
}

// ── Paso 1: subir el instrumento ──────────────────────────────────────────────────

/** Lee el `detail` de una respuesta de error de FastAPI (si es texto). */
async function detalleDe(respuesta: Response): Promise<string> {
  try {
    const datos = (await respuesta.json()) as { detail?: unknown };
    return typeof datos?.detail === "string" ? datos.detail : "";
  } catch {
    return "";
  }
}

/**
 * Sube el instrumento RESPONDIDO (y opcionalmente el ORIGINAL) por el gateway:
 * `POST /instrumentos/upload` (multipart). El storage-service guarda el archivo
 * tal cual se subió. Requiere Bearer (rol investigador/admin).
 *
 * `pedir()` fuerza `Content-Type: application/json`, así que para multipart se usa
 * `fetch` directo con `FormData` y header Authorization.
 */
export async function subirInstrumento(
  archivo: File,
  tipo: TipoInstrumento,
  archivoOriginal?: File | null,
): Promise<ResultadoCarga> {
  const form = new FormData();
  form.append("archivo", archivo);
  form.append("tipo_instrumento", TIPO_UI_A_BACKEND[tipo]);
  if (archivoOriginal) form.append("archivo_original", archivoOriginal);

  const headers: Record<string, string> = {};
  const token = leerToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const respuesta = await fetch(`${API_URL}/instrumentos/upload`, {
    method: "POST",
    headers,
    body: form,
  });

  if (!respuesta.ok) {
    const detalle = await detalleDe(respuesta);
    const mensaje =
      respuesta.status === 401
        ? "Tu sesión expiró, vuelve a iniciar sesión."
        : respuesta.status === 403
          ? detalle || "No tienes permiso para subir instrumentos."
          : detalle || `No se pudo subir el instrumento (HTTP ${respuesta.status}).`;
    const error = new Error(mensaje) as Error & { status?: number };
    error.status = respuesta.status;
    throw error;
  }

  const datos = (await respuesta.json()) as UploadResponse;
  return {
    idCrudo: datos.id_crudo,
    idInstrumento: datos.id_instrumento,
    reporte: mapearParseoALimpieza(datos.archivo_respondido?.parseo),
  };
}

// ── Pasos 3 y 4: propuesta de metadatos (metadata-service) ────────────────────────

interface PropuestaResponse {
  id_crudo: number;
  id_instrumento: number;
  tipo_instrumento: string;
  tabla: string;
  aprobado: boolean;
  valores: Record<string, unknown>;
  origen: Record<string, OrigenMetadato>;
  obligatorios: string[];
  notas: string[];
}

/** Propuesta del metadata-service para un grupo de metadatos (o lo ya aprobado). */
export interface PropuestaMetadatos {
  aprobado: boolean;
  valores: Record<string, unknown>;
  origen: Record<string, OrigenMetadato>;
  obligatorios: string[];
  notas: string[];
}

function aPropuesta(r: PropuestaResponse): PropuestaMetadatos {
  return {
    aprobado: r.aprobado,
    valores: r.valores ?? {},
    origen: r.origen ?? {},
    obligatorios: r.obligatorios ?? [],
    notas: r.notas ?? [],
  };
}

/** Dublin Core propuesto: automáticos + inferidos del archivo (+ LLM si está activo). */
export async function getPropuestaDublinCore(idCrudo: number): Promise<PropuestaMetadatos> {
  return aPropuesta(
    await pedir<PropuestaResponse>(`${API_URL}/api/metadata/${idCrudo}/propuesta`, { auth: true }),
  );
}

/** Metadatos específicos del tipo propuestos (encuesta, entrevista o prueba). */
export async function getPropuestaEnriquecida(idCrudo: number): Promise<PropuestaMetadatos> {
  return aPropuesta(
    await pedir<PropuestaResponse>(`${API_URL}/api/enrichment/${idCrudo}/propuesta`, {
      auth: true,
    }),
  );
}

// Correspondencia campo del formulario ↔ columna de metadatos_dc.
const CAMPOS_DC: Record<Exclude<keyof DublinCore, "cobertura" | "coberturaDetalle">, string> = {
  titulo: "dc_title",
  creador: "dc_creator",
  tema: "dc_subject",
  descripcion: "dc_description",
  tipo: "dc_type",
  fecha: "dc_date",
  idioma: "dc_language",
  editor: "dc_publisher",
  derechos: "dc_rights",
  formato: "dc_format",
  fuente: "dc_source",
  relacion: "dc_relation",
};

/** Campo del formulario Dublin Core que corresponde a una columna `dc_*`. */
export const CAMPO_DC_POR_COLUMNA: Record<string, keyof DublinCore> = {
  ...Object.fromEntries(Object.entries(CAMPOS_DC).map(([campo, col]) => [col, campo])),
  dc_coverage: "cobertura",
} as Record<string, keyof DublinCore>;

function texto(valor: unknown): string {
  if (valor === null || valor === undefined) return "";
  if (Array.isArray(valor)) return valor.map(texto).filter(Boolean).join(", ");
  if (typeof valor === "object") {
    return Object.entries(valor as Record<string, unknown>)
      .map(([k, v]) => `${k}: ${texto(v)}`)
      .join("\n");
  }
  return String(valor);
}

/** «Licenciatura — Estudiantes de la UNAM» → nivel + detalle. */
function partirCobertura(cobertura: string): { nivel: NivelEducativo | ""; detalle: string } {
  const limpio = cobertura.trim();
  const m = /^(Licenciatura|Posgrado)(?:\s*\([^)]*\))?\s*(?:[—–-]\s*)?(.*)$/i.exec(limpio);
  if (m) {
    const nivel: NivelEducativo = m[1]?.toLowerCase() === "posgrado" ? "Posgrado" : "Licenciatura";
    return { nivel, detalle: (m[2] ?? "").trim() };
  }
  const minusculas = limpio.toLowerCase();
  if (/posgrado|maestr|doctor|especialidad/.test(minusculas))
    return { nivel: "Posgrado", detalle: limpio };
  if (/licenciatura|universitari|pregrado/.test(minusculas))
    return { nivel: "Licenciatura", detalle: limpio };
  return { nivel: "", detalle: limpio };
}

/** Aplica una propuesta (valores `dc_*`) sobre el formulario Dublin Core. */
export function dublinCoreDesdePropuesta(
  valores: Record<string, unknown>,
  base: DublinCore,
): DublinCore {
  const dc: DublinCore = { ...base };
  for (const [campo, columna] of Object.entries(CAMPOS_DC) as [keyof typeof CAMPOS_DC, string][]) {
    const valor = texto(valores[columna]);
    if (valor) dc[campo] = valor;
  }
  const cobertura = texto(valores["dc_coverage"]);
  if (cobertura) {
    const { nivel, detalle } = partirCobertura(cobertura);
    dc.cobertura = nivel;
    dc.coberturaDetalle = detalle;
  }
  return dc;
}

/** Formulario Dublin Core → columnas `dc_*` que espera el metadata-service. */
export function dublinCoreAPayload(dc: DublinCore): Record<string, string> {
  const payload: Record<string, string> = {};
  for (const [campo, columna] of Object.entries(CAMPOS_DC) as [keyof typeof CAMPOS_DC, string][]) {
    payload[columna] = dc[campo].trim();
  }
  payload["dc_coverage"] = [dc.cobertura, dc.coberturaDetalle.trim()].filter(Boolean).join(" — ");
  return payload;
}

/** Valores propuestos del tipo → texto de formulario (listas con comas, mapas por línea). */
export function metadatosTipoDesdePropuesta(valores: Record<string, unknown>): MetadatosTipo {
  return Object.fromEntries(Object.entries(valores).map(([clave, valor]) => [clave, texto(valor)]));
}

// ── Paso 5: vista previa y aprobación ─────────────────────────────────────────────

export interface ErroresMetadatos {
  dublin_core: Record<string, string>;
  enriquecidos: Record<string, string>;
}

export interface VistaPrevia {
  json: Record<string, unknown>;
  valido: boolean;
  errores: ErroresMetadatos;
}

/** JSON estandarizado que se generaría con estos metadatos (no guarda nada). */
export async function previsualizarMetadatos(
  idCrudo: number,
  dc: DublinCore,
  meta: MetadatosTipo,
): Promise<VistaPrevia> {
  const r = await pedir<{
    json_estandarizado: Record<string, unknown>;
    valido: boolean;
    errores: ErroresMetadatos;
  }>(`${API_URL}/api/metadata/${idCrudo}/vista-previa`, {
    method: "POST",
    auth: true,
    body: { dublin_core: dublinCoreAPayload(dc), enriquecidos: meta },
  });
  return { json: r.json_estandarizado, valido: r.valido, errores: r.errores };
}

export interface ResultadoAprobacion {
  idInstrumento: number;
  json: Record<string, unknown>;
  /** Instrumento en Markdown (solo preguntas): entrada para proponer KPIs. */
  textoInstrumento: string;
  ingesta: { indexado: boolean; chunks: number; motivo: string | null };
  mensaje: string;
}

/**
 * El autor aprueba sus metadatos: el metadata-service los persiste
 * (metadatos_dc + metadatos_enriquecidos_*), guarda el JSON estandarizado en el
 * storage-service y lo ingiere al RAG. Se puede volver a aprobar para corregir.
 */
export async function aprobarMetadatos(
  idCrudo: number,
  dc: DublinCore,
  meta: MetadatosTipo,
): Promise<ResultadoAprobacion> {
  const r = await pedir<{
    id_instrumento: number;
    json_estandarizado: Record<string, unknown>;
    texto_instrumento: string;
    ingesta: { indexado: boolean; chunks: number; motivo: string | null };
    mensaje: string;
  }>(`${API_URL}/api/metadata/${idCrudo}/aprobar`, {
    method: "POST",
    auth: true,
    body: { dublin_core: dublinCoreAPayload(dc), enriquecidos: meta },
  });
  return {
    idInstrumento: r.id_instrumento,
    json: r.json_estandarizado,
    textoInstrumento: r.texto_instrumento,
    ingesta: r.ingesta,
    mensaje: r.mensaje,
  };
}

// ── Paso 6: asociación de KPIs (analysis-service directo) ───────────────────────────

/** KPI candidato que devuelve el backend en /vectorizacion/propuestas. */
interface PropuestaKPI {
  kpi_id: number;
  nombre_kpi: string;
  categoria?: string | null;
  ambito?: string | null;
  score: number;
}

interface PropuestasResponse {
  id_instrumento: number;
  tipo_instrumento: string;
  metadatos_clave: Record<string, string>;
  propuestas: PropuestaKPI[];
  mensaje: string;
}

/**
 * Propone KPIs por similitud semántica con los KPIs almacenados en Chroma.
 * `POST /vectorizacion/propuestas` (multipart) contra ANALYSIS_URL directo (el gateway
 * no proxea /vectorizacion/*). Recibe el JSON aprobado y el instrumento en texto.
 */
export async function proponerKpis(args: {
  idInstrumento: number;
  archivoJson: File | Blob;
  instrumentoOriginal: File | Blob;
  tipo: TipoInstrumento;
}): Promise<KpiSugerido[]> {
  const { idInstrumento, archivoJson, instrumentoOriginal, tipo } = args;

  const form = new FormData();
  form.append(
    "archivo_json",
    new Blob([archivoJson], { type: "application/json" }),
    "instrumento.json",
  );
  form.append(
    "instrumento_original",
    new Blob([instrumentoOriginal], { type: "text/markdown" }),
    "instrumento.md",
  );
  form.append("tipo_instrumento", TIPO_UI_A_BACKEND[tipo]);
  form.append("id_instrumento", String(idInstrumento));

  const respuesta = await fetch(`${ANALYSIS_URL}/vectorizacion/propuestas`, {
    method: "POST",
    body: form,
  });

  if (!respuesta.ok) {
    const detalle = await detalleDe(respuesta);
    const error = new Error(
      detalle || `No se pudieron proponer KPIs (HTTP ${respuesta.status}).`,
    ) as Error & { status?: number };
    error.status = respuesta.status;
    throw error;
  }

  const datos = (await respuesta.json()) as PropuestasResponse;
  return (datos.propuestas ?? []).map((p) => ({
    id: String(p.kpi_id),
    nombre: p.nombre_kpi,
    coincidencia: Math.round(p.score * 100),
  }));
}

export interface DecisionKpiApi {
  kpiId: number;
  aceptado: boolean;
  score?: number;
}

interface KpiAgregado {
  kpi_id: number;
  nombre_kpi: string;
  score?: number | null;
}

interface ConfirmarResponse {
  id_instrumento: number;
  kpis_agregados: KpiAgregado[];
  json_enriquecido: Record<string, unknown>;
  mensaje: string;
}

/**
 * Confirma las decisiones del autor: el analysis-service persiste los KPIs
 * aceptados (`kpi_inferido` + evidencia). `POST /vectorizacion/confirmar`.
 */
export async function confirmarKpis(args: {
  idInstrumento: number;
  decisiones: DecisionKpiApi[];
  jsonInstrumento: Record<string, unknown>;
}): Promise<{
  kpisAgregados: { kpiId: number; nombreKpi: string; score?: number }[];
  jsonEnriquecido: Record<string, unknown>;
}> {
  const datos = await pedir<ConfirmarResponse>(`${ANALYSIS_URL}/vectorizacion/confirmar`, {
    method: "POST",
    body: {
      id_instrumento: args.idInstrumento,
      decisiones: args.decisiones.map((d) => ({
        kpi_id: d.kpiId,
        aceptado: d.aceptado,
        score: d.score,
      })),
      json_instrumento: args.jsonInstrumento,
    },
    auth: false,
  });

  return {
    kpisAgregados: (datos.kpis_agregados ?? []).map((k) =>
      k.score == null
        ? { kpiId: k.kpi_id, nombreKpi: k.nombre_kpi }
        : { kpiId: k.kpi_id, nombreKpi: k.nombre_kpi, score: k.score },
    ),
    jsonEnriquecido: datos.json_enriquecido,
  };
}

// ── Paso 7: guardar ──────────────────────────────────────────────────────────────────

/**
 * Cierra la carga: el metadata-service añade al JSON estandarizado los KPIs que el
 * autor aceptó, lo guarda como versión final en el storage-service y actualiza el
 * índice del RAG. `POST /api/metadata/{id_crudo}/finalizar`.
 */
export async function guardarInstrumento(idCrudo: number): Promise<{ id: string; kpis: string[] }> {
  const r = await pedir<{ id_crudo: number; kpis: { nombre_kpi: string }[] }>(
    `${API_URL}/api/metadata/${idCrudo}/finalizar`,
    { method: "POST", auth: true },
  );
  return { id: String(r.id_crudo), kpis: (r.kpis ?? []).map((k) => k.nombre_kpi) };
}
