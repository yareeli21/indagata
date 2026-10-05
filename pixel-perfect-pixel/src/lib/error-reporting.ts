/**
 * Reporte de errores de la aplicación.
 *
 * Hoy registra el error en consola (y extrae datos útiles de un `Response`
 * lanzado por loaders o server functions). Es el punto único donde enganchar,
 * en el futuro, un servicio de telemetría propio (Sentry, GlitchTip, etc.)
 * sin tocar los límites de error de la UI.
 */
export function reportError(error: unknown, context: Record<string, unknown> = {}) {
  // Loaders y server functions suelen lanzar un `Response` crudo; String(it)
  // da el opaco "[object Response]", así que extraemos estado y URL.
  const message =
    error instanceof Response
      ? `Response ${error.status}${error.url ? ` at ${error.url}` : ""}`
      : error instanceof Error
        ? error.message
        : String(error);

  const ruta = typeof window !== "undefined" ? window.location.pathname : undefined;

  console.error("[app-error]", message, { ruta, ...context }, error);
}
