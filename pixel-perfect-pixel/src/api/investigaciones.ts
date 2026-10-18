import type { ContextoInvestigacion, Investigacion, Mensaje, SesionChat } from "@/types";

/**
 * No hay servicio de investigaciones en el backend de esta tanda. La lista se
 * persiste en el cliente (localStorage) para que el flujo "crear investigación →
 * juntar instrumentos → chatear" sea real de punta a punta. Las firmas no cambian.
 *
 * Cada investigación guarda también su conversación (contexto y mensajes) para
 * retomarla sin volver a preguntar: lo ya respondido no se vuelve a generar.
 */
const CLAVE_INVESTIGACIONES = "indagata.investigaciones";
const CLAVE_INSTRUMENTOS = "indagata.instrumentosPorInvestigacion";
const PREFIJO_SESION = "indagata.chat.";
/** Mensajes que se guardan por investigación (los más recientes). */
const MAX_MENSAJES = 200;

function leerInvestigaciones(): Investigacion[] {
  try {
    const crudo = window.localStorage.getItem(CLAVE_INVESTIGACIONES);
    if (!crudo) return [];
    const datos = JSON.parse(crudo) as Investigacion[];
    return Array.isArray(datos) ? datos : [];
  } catch {
    return [];
  }
}

function escribirInvestigaciones(lista: Investigacion[]): void {
  try {
    window.localStorage.setItem(CLAVE_INVESTIGACIONES, JSON.stringify(lista));
  } catch {
    /* almacenamiento no disponible: se mantiene solo en memoria del proceso */
  }
}

export function getInvestigaciones(): Promise<Investigacion[]> {
  return Promise.resolve(leerInvestigaciones());
}

export function crearInvestigacion(nombre: string, propietarioId: string): Promise<Investigacion> {
  const nueva: Investigacion = {
    id: `res-${Date.now()}`,
    nombre,
    propietarioId,
    fechaCreacion: new Date().toISOString(),
  };
  const lista = leerInvestigaciones();
  lista.push(nueva);
  escribirInvestigaciones(lista);
  return Promise.resolve(nueva);
}

/**
 * Elimina la investigación con su selección de instrumentos y su conversación.
 * No borra instrumentos ni la bitácora de consultas del servidor.
 */
export function eliminarInvestigacion(id: string): Promise<void> {
  escribirInvestigaciones(leerInvestigaciones().filter((i) => i.id !== id));
  try {
    window.localStorage.removeItem(PREFIJO_SESION + id);
    const crudo = window.localStorage.getItem(CLAVE_INSTRUMENTOS);
    if (crudo) {
      const mapa = JSON.parse(crudo) as Record<string, string[]>;
      delete mapa[id];
      window.localStorage.setItem(CLAVE_INSTRUMENTOS, JSON.stringify(mapa));
    }
  } catch {
    /* almacenamiento no disponible */
  }
  return Promise.resolve();
}

// ── Conversación guardada por investigación ─────────────────────────────────────

export function leerSesionChat(id: string): SesionChat | null {
  try {
    const crudo = window.localStorage.getItem(PREFIJO_SESION + id);
    if (!crudo) return null;
    const datos = JSON.parse(crudo) as SesionChat;
    return datos && datos.contexto && Array.isArray(datos.mensajes) ? datos : null;
  } catch {
    return null;
  }
}

/** Guarda el contexto y los mensajes terminados (los que se están generando no). */
export function guardarSesionChat(
  id: string,
  contexto: ContextoInvestigacion,
  mensajes: Mensaje[],
): void {
  const terminados = mensajes.filter((m) => !m.generando && m.contenido).slice(-MAX_MENSAJES);
  const sesion: SesionChat = {
    contexto,
    mensajes: terminados,
    actualizada: new Date().toISOString(),
  };
  try {
    window.localStorage.setItem(PREFIJO_SESION + id, JSON.stringify(sesion));
  } catch {
    /* almacenamiento lleno o no disponible: la conversación sigue en pantalla */
  }
}
