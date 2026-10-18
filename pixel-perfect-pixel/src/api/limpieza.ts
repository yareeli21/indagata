import type { EjecucionLimpieza, ResumenLimpieza } from "@/types";
import { API_URL, pedir } from "./client";

/**
 * Limpieza asistida (cleaning-service vía api-gateway, prefijo `/limpieza`).
 *
 * Flujo: `ejecutarLimpieza` (fase automática; retoma si ya hay una versión en
 * curso) → `guardarDecisiones` (parcial, conforme el investigador decide) →
 * `confirmarLimpieza` (CSV limpio + reporte). El reporte completo nunca llega a
 * la interfaz: el servicio devuelve una vista derivada.
 */

// Peticiones de ejecución en vuelo: dos llamadas idénticas simultáneas (doble clic,
// doble montaje de React en desarrollo) comparten la misma respuesta.
const enVuelo = new Map<string, Promise<EjecucionLimpieza>>();

/** Corre la fase automática. Con `nueva`, crea otra versión (p. ej. «volver a ajustar»). */
export function ejecutarLimpieza(idCrudo: number, nueva = false): Promise<EjecucionLimpieza> {
  const clave = `${idCrudo}:${nueva}`;
  const existente = enVuelo.get(clave);
  if (existente) return existente;
  const peticion = pedir<EjecucionLimpieza>(
    `${API_URL}/limpieza/${idCrudo}/ejecuciones${nueva ? "?nueva=true" : ""}`,
    { method: "POST", auth: true },
  ).finally(() => enVuelo.delete(clave));
  enVuelo.set(clave, peticion);
  return peticion;
}

/** Última versión de la limpieza del instrumento (para retomar). */
export function getLimpiezaActual(idCrudo: number): Promise<EjecucionLimpieza> {
  return pedir<EjecucionLimpieza>(`${API_URL}/limpieza/${idCrudo}/ejecuciones/actual`, {
    auth: true,
  });
}

/**
 * Guarda decisiones parciales `{idHallazgo: opción}` (null borra la decisión).
 * Con `alCerrar`, la petición sobrevive al cierre o recarga de la página.
 */
export function guardarDecisiones(
  idCrudo: number,
  version: number,
  decisiones: Record<string, string | null>,
  alCerrar = false,
): Promise<EjecucionLimpieza> {
  return pedir<EjecucionLimpieza>(
    `${API_URL}/limpieza/${idCrudo}/ejecuciones/${version}/decisiones`,
    { method: "PATCH", auth: true, body: { decisiones }, keepalive: alCerrar },
  );
}

/** Aplica las decisiones, genera el CSV limpio y cierra el reporte. */
export function confirmarLimpieza(idCrudo: number, version: number): Promise<EjecucionLimpieza> {
  return pedir<EjecucionLimpieza>(
    `${API_URL}/limpieza/${idCrudo}/ejecuciones/${version}/confirmar`,
    { method: "POST", auth: true },
  );
}

/**
 * Medidas de la última limpieza confirmada y sugerencias de análisis, para verlas
 * después de guardar el instrumento (catálogo). Sin filas de respondentes.
 */
export function getResumenLimpieza(idCrudo: number): Promise<ResumenLimpieza> {
  return pedir<ResumenLimpieza>(`${API_URL}/limpieza/${idCrudo}/resumen`, { auth: true });
}
