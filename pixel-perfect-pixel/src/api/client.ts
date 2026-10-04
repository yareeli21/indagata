/**
 * Punto único de acceso a datos. Hoy resuelve con datos de ejemplo (src/mocks).
 * Para conectar la API FastAPI basta con reemplazar el cuerpo de estas funciones
 * por llamadas HTTP: la firma (promesas) no cambia.
 */
export function simularRed<T>(dato: T, ms = 300): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(dato), ms));
}

/** URL base del api-gateway (login y servicios proxeados). */
export const API_URL: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

/** URL base del analysis-service (el api-gateway NO proxea /vectorizacion/*). */
export const ANALYSIS_URL: string = import.meta.env.VITE_ANALYSIS_URL ?? "http://localhost:8002";

// ── Store de token (memoria + localStorage) ────────────────────────────────────

const CLAVE_TOKEN = "indagata.token";

let tokenEnMemoria: string | null = null;

export function guardarToken(token: string): void {
  tokenEnMemoria = token;
  try {
    window.localStorage.setItem(CLAVE_TOKEN, token);
  } catch {
    /* almacenamiento no disponible: se mantiene solo en memoria */
  }
}

export function leerToken(): string | null {
  if (tokenEnMemoria) return tokenEnMemoria;
  try {
    tokenEnMemoria = window.localStorage.getItem(CLAVE_TOKEN);
  } catch {
    tokenEnMemoria = null;
  }
  return tokenEnMemoria;
}

export function borrarToken(): void {
  tokenEnMemoria = null;
  try {
    window.localStorage.removeItem(CLAVE_TOKEN);
  } catch {
    /* almacenamiento no disponible */
  }
}

// ── Helper HTTP ─────────────────────────────────────────────────────────────────

interface OpcionesPedir {
  method?: string;
  body?: unknown;
  /** Si es true y hay token, adjunta Authorization: Bearer <token>. */
  auth?: boolean;
}

/**
 * Realiza una petición HTTP contra la API y devuelve el JSON parseado.
 * Lanza un Error con mensaje en español en respuestas no-2xx; un HTTP 401
 * se mapea al mensaje exacto 'Usuario o contraseña incorrectos'.
 */
export async function pedir<T>(url: string, opciones: OpcionesPedir = {}): Promise<T> {
  const { method = "GET", body, auth = false } = opciones;

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (auth) {
    const token = leerToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const respuesta = await fetch(url, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (!respuesta.ok) {
    if (respuesta.status === 401) {
      throw new Error("Usuario o contraseña incorrectos");
    }
    let detalle = "";
    try {
      const datos = (await respuesta.json()) as { detail?: unknown };
      if (typeof datos?.detail === "string") detalle = datos.detail;
    } catch {
      /* cuerpo no-JSON: se ignora */
    }
    throw new Error(detalle || `Error en la petición (HTTP ${respuesta.status}).`);
  }

  return (await respuesta.json()) as T;
}
