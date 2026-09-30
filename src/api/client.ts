/**
 * Punto único de acceso a datos. Hoy resuelve con datos de ejemplo (src/mocks).
 * Para conectar la API FastAPI basta con reemplazar el cuerpo de estas funciones
 * por llamadas HTTP: la firma (promesas) no cambia.
 */
export function simularRed<T>(dato: T, ms = 300): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(dato), ms));
}
