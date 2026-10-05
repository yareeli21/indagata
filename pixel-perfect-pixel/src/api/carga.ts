import type { KpiSugerido, ReporteLimpieza, TipoInstrumento } from "@/types";
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
  /** PK de raw_data (instrument-service: listados/detalle). */
  idCrudo: number;
  /** PK de instrumento_procesado (metadatos + KPIs). */
  idInstrumento: number;
  /** Reporte de limpieza derivado del parseo del upload (no hay endpoint propio). */
  reporte: ReporteLimpieza;
}

// ── Helper puro: ParseoArchivo → ReporteLimpieza ─────────────────────────────────

/**
 * Deriva un `ReporteLimpieza` del resumen de parseo del upload.
 *
 * NOTA: no existe etapa de limpieza con conteos de duplicados/nulos en el backend
 * (instrument-service solo expone upload/list/get/delete). Por eso
 * `duplicadosEliminados` y `nulosTratados` son 0 (valor honesto, no inventado).
 * Cuando exista `POST /instrumentos/limpieza` que devuelva esos conteos, se
 * reemplaza este derivado. La forma de `ReporteLimpieza`/`CambioLimpieza` se preserva.
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
    duplicadosEliminados: 0, // sin etapa de limpieza con este conteo (ver NOTA)
    nulosTratados: 0, // sin etapa de limpieza con este conteo (ver NOTA)
    cambios,
  };
}

// ── Paso 1: subir el instrumento ──────────────────────────────────────────────────

/**
 * Sube el instrumento RESPONDIDO (y opcionalmente el ORIGINAL) por el gateway:
 * `POST /instrumentos/upload` (multipart). Requiere Bearer (rol investigador/admin).
 * Devuelve ambos ids (`id_crudo`, `id_instrumento`) y el reporte derivado del parseo.
 *
 * `pedir()` fuerza `Content-Type: application/json`, así que para multipart se usa
 * `fetch` directo con `FormData` y header Authorization (patrón de `chat.ts`).
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
    // Mapeo de errores a mensajes en español según el status (§2.5 del diseño).
    let detalle = "";
    try {
      const datos = (await respuesta.json()) as { detail?: unknown };
      if (typeof datos?.detail === "string") detalle = datos.detail;
    } catch {
      /* cuerpo no-JSON: se ignora */
    }
    const mensaje =
      respuesta.status === 401
        ? "Usuario o contraseña incorrectos"
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

/**
 * Firma estable por compatibilidad. El reporte de limpieza REAL lo produce
 * `subirInstrumento` (derivado del parseo del upload) y el wizard ya no invoca
 * esta función: no hay endpoint de limpieza y no se inventa uno. Devuelve un
 * reporte derivado solo del `File` (ceros, sin cambios).
 */
export function limpiarArchivo(_archivo: File): Promise<ReporteLimpieza> {
  return Promise.resolve({
    duplicadosEliminados: 0,
    nulosTratados: 0,
    columnasNormalizadas: 0,
    cambios: [],
  });
}

// ── Paso 3: metadatos Dublin Core ──────────────────────────────────────────────────

/** Datos pre-poblados que devuelve el init de metadatos (7 campos auto-rellenados). */
export interface MetadatosInit {
  dc_creator: string;
  dc_publisher: string;
  dc_type: string;
  dc_format: string;
  dc_date: string;
  dc_language: string;
  dc_title_sugerido: string;
}

/**
 * GET pre-poblado de metadatos por el gateway.
 * NOTA: la ruta real tiene DOBLE segmento `metadata` (el router usa prefix
 * `/metadata` con decoradores `/metadata/{id}/init`, montado con prefix `/api`).
 * No "corregir" a un solo `metadata`: el proxy reenvía el path tal cual.
 */
export function getMetadatosInit(idInstrumento: number): Promise<MetadatosInit> {
  return pedir<MetadatosInit>(`${API_URL}/api/metadata/metadata/${idInstrumento}/init`, {
    auth: true,
  });
}

/** Payload de registro de los 13 campos Dublin Core (solo título/tema exige el wizard). */
export interface RegistroMetadatos {
  dc_title: string;
  dc_subject: string[];
  dc_creator?: string;
  dc_description?: string;
  dc_coverage?: string;
  dc_rights?: string;
  dc_source?: string;
  dc_relation?: string;
}

/**
 * POST de registro de metadatos (inmutable: una 2ª llamada → 409). El `dc_creator`
 * lo envía el frontend (si se omite, el backend persiste "Sistema"). Doble `metadata`
 * en la ruta (ver `getMetadatosInit`). Mapeo de 409/404 a mensaje por el status lo
 * hace el caller leyendo `ErrorHttp.status`.
 */
export function registrarMetadatos(
  idInstrumento: number,
  datos: RegistroMetadatos,
): Promise<Record<string, unknown>> {
  return pedir<Record<string, unknown>>(`${API_URL}/api/metadata/metadata/${idInstrumento}`, {
    method: "POST",
    body: datos,
    auth: true,
  });
}

// ── Paso 4: asociación de KPIs (analysis-service directo) ───────────────────────────

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
 * Firma estable por compatibilidad. La propuesta REAL la produce `proponerKpis`
 * (necesita el JSON del instrumento + .md original + tipo + id_instrumento, no solo
 * una descripción). El wizard ya no invoca esta función; devuelve `[]`.
 */
export function getKpisSugeridos(_descripcion: string): Promise<KpiSugerido[]> {
  // TODO: la propuesta real la hace `proponerKpis` (POST /vectorizacion/propuestas).
  return Promise.resolve([]);
}

/**
 * Paso 1 de KPIs: propone KPIs por similitud semántica.
 * `POST /vectorizacion/propuestas` (multipart) contra ANALYSIS_URL directo (el gateway
 * no proxea /vectorizacion/*). Sin Authorization (auth dev mode resuelve sin token,
 * patrón de `espacio.ts`). Se envían Blob/File con `type` explícito.
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
    let detalle = "";
    try {
      const datos = (await respuesta.json()) as { detail?: unknown };
      if (typeof datos?.detail === "string") detalle = datos.detail;
    } catch {
      /* cuerpo no-JSON: se ignora */
    }
    const error = new Error(
      detalle || `No se pudieron proponer KPIs (HTTP ${respuesta.status}).`,
    ) as Error & { status?: number };
    error.status = respuesta.status;
    throw error;
  }

  const datos = (await respuesta.json()) as PropuestasResponse;
  // Mapeo PropuestaKPI → KpiSugerido (preserva la forma de 3 campos).
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
 * Paso 2 de KPIs: confirma las decisiones y enriquece el JSON.
 * `POST /vectorizacion/confirmar` (JSON) contra ANALYSIS_URL directo, sin auth.
 * El /confirmar persiste los KPIs aceptados: ES el "guardar" del dominio de KPIs.
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

/**
 * Firma estable. El "guardado" de dominio del paso 4 es el `json_enriquecido` que
 * devuelve `confirmarKpis` (el /confirmar ya persiste los KPIs aceptados en BD).
 * Devuelve el id real del instrumento (en vez del `ins-${Date.now()}` del mock).
 *
 * TODO: si se requiere persistir `json_enriquecido` como artefacto en storage-service,
 * cablear `POST /almacenamiento/...` tras verificar su contrato real (router no leído).
 */
export function guardarInstrumento(documento: unknown): Promise<{ id: string }> {
  const doc = documento as { id_instrumento?: number } | null | undefined;
  const id = doc?.id_instrumento != null ? String(doc.id_instrumento) : `ins-${Date.now()}`;
  return Promise.resolve({ id });
}
