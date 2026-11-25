import type { ContextoInvestigacion, Investigacion, Mensaje, SesionChat } from "@/types";
import { API_URL, pedir } from "./client";

/**
 * Investigaciones del usuario y su conversación (contexto y mensajes), para retomarlas sin volver a preguntar.
 *
 * 25 nov: se guardan en el servidor (GET/PUT/DELETE /visualizacion/investigaciones) para verlas desde cualquier
 * dispositivo. El navegador (localStorage) queda como copia rápida: cada escritura va a los dos lados y, al iniciar
 * sesión, `sincronizarInvestigaciones` baja las del servidor y sube las que solo estaban en este navegador.
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

/**
 * Investigaciones del usuario (16 nov): cada quien ve solo las suyas, aunque los instrumentos sean compartidos.
 * Antes todas se creaban con el dueño fijo «inv-ana» y cualquiera que entrara en el navegador las veía.
 */
export function getInvestigaciones(propietarioId: string): Promise<Investigacion[]> {
  return Promise.resolve(leerInvestigaciones().filter((i) => i.propietarioId === propietarioId));
}

/** Dueño fijo con que se crearon las investigaciones antes del 16 nov. */
const PROPIETARIO_ANTERIOR = "inv-ana";
/** Cuenta con la que se crearon esas investigaciones (la de demostración del investigador). */
export const CUENTA_INVESTIGACIONES_ANTERIORES = "investigador@indagata.com";

/** Pasa a `propietarioId` las investigaciones creadas con el dueño fijo anterior. */
export function reclamarInvestigacionesAnteriores(propietarioId: string): void {
  const lista = leerInvestigaciones();
  if (!lista.some((i) => i.propietarioId === PROPIETARIO_ANTERIOR)) return;
  escribirInvestigaciones(
    lista.map((i) => (i.propietarioId === PROPIETARIO_ANTERIOR ? { ...i, propietarioId } : i)),
  );
}

// ── Servidor ─────────────────────────────────────────────────────────────────────

interface InvestigacionServidor {
  id: string;
  nombre: string;
  fechaCreacion: string | null;
  instrumentos: string[];
  sesion: SesionChat | null;
  actualizada: string | null;
}

/** Datos que se mandan al servidor; solo se actualizan los campos presentes. */
export interface CambiosInvestigacion {
  nombre?: string;
  fechaCreacion?: string;
  instrumentos?: string[];
  sesion?: SesionChat;
}

const url = (id = "") =>
  `${API_URL}/visualizacion/investigaciones${id ? `/${encodeURIComponent(id)}` : ""}`;

/** Guarda en el servidor sin hacer esperar a la página (si falla, queda la copia del navegador). */
export function enviarInvestigacion(id: string, cambios: CambiosInvestigacion): void {
  void pedir(url(id), { method: "PUT", auth: true, body: cambios }).catch((e: unknown) =>
    console.warn("No se pudo guardar la investigación en el servidor:", e),
  );
}

/** Ids que ya estuvieron en el servidor: si dejan de estar, se eliminaron en otro dispositivo. */
const claveEnServidor = (usuario: string) => `indagata.investigaciones.enServidor.${usuario}`;

function leerJson<T>(clave: string, defecto: T): T {
  try {
    const crudo = window.localStorage.getItem(clave);
    return crudo ? (JSON.parse(crudo) as T) : defecto;
  } catch {
    return defecto;
  }
}

function escribirJson(clave: string, valor: unknown): void {
  try {
    window.localStorage.setItem(clave, JSON.stringify(valor));
  } catch {
    /* almacenamiento lleno o no disponible */
  }
}

/**
 * Junta lo del servidor con lo de este navegador: baja las investigaciones del servidor (la conversación más
 * reciente gana), sube las que solo están aquí y quita las que se eliminaron en otro dispositivo. Sin servidor no
 * cambia nada: se sigue con la copia local.
 */
export async function sincronizarInvestigaciones(propietarioId: string): Promise<void> {
  let remotas: InvestigacionServidor[];
  try {
    remotas = await pedir<InvestigacionServidor[]>(url(), { auth: true });
  } catch {
    return;
  }
  const idsRemotos = new Set(remotas.map((r) => r.id));
  const yaEnServidor = new Set(leerJson<string[]>(claveEnServidor(propietarioId), []));
  const mapa = leerJson<Record<string, string[]>>(CLAVE_INSTRUMENTOS, {});
  let lista = leerInvestigaciones();

  // Eliminadas en otro dispositivo: estuvieron en el servidor y ya no están.
  const borradas = lista.filter(
    (i) => i.propietarioId === propietarioId && yaEnServidor.has(i.id) && !idsRemotos.has(i.id),
  );
  for (const i of borradas) {
    delete mapa[i.id];
    try {
      window.localStorage.removeItem(PREFIJO_SESION + i.id);
    } catch {
      /* almacenamiento no disponible */
    }
  }
  lista = lista.filter((i) => !borradas.includes(i));

  for (const r of remotas) {
    const local: Investigacion = {
      id: r.id,
      nombre: r.nombre,
      propietarioId,
      ...(r.fechaCreacion ? { fechaCreacion: r.fechaCreacion } : {}),
    };
    const idx = lista.findIndex((i) => i.id === r.id);
    if (idx >= 0) lista[idx] = { ...lista[idx], ...local };
    else lista.push(local);
    if (r.instrumentos.length > 0 || !(r.id in mapa)) mapa[r.id] = r.instrumentos;
    const sesionLocal = leerSesionChat(r.id);
    const fechaLocal = sesionLocal?.actualizada ?? "";
    const fechaRemota = r.sesion?.actualizada ?? "";
    if (r.sesion && fechaRemota >= fechaLocal) escribirJson(PREFIJO_SESION + r.id, r.sesion);
    else if (sesionLocal) enviarInvestigacion(r.id, { sesion: sesionLocal });
  }

  // Solo en este navegador (creadas antes de guardarse en el servidor, o sin conexión): se suben.
  for (const i of lista.filter((x) => x.propietarioId === propietarioId && !idsRemotos.has(x.id))) {
    const sesion = leerSesionChat(i.id);
    enviarInvestigacion(i.id, {
      nombre: i.nombre,
      ...(i.fechaCreacion ? { fechaCreacion: i.fechaCreacion } : {}),
      instrumentos: mapa[i.id] ?? [],
      ...(sesion ? { sesion } : {}),
    });
    idsRemotos.add(i.id);
  }

  escribirInvestigaciones(lista);
  escribirJson(CLAVE_INSTRUMENTOS, mapa);
  escribirJson(claveEnServidor(propietarioId), [...idsRemotos]);
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
  enviarInvestigacion(nueva.id, {
    nombre,
    fechaCreacion: nueva.fechaCreacion ?? new Date().toISOString(),
  });
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
  void pedir<void>(url(id), { method: "DELETE", auth: true }).catch((e: unknown) =>
    console.warn("No se pudo eliminar la investigación en el servidor:", e),
  );
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
  // Al servidor, agrupando los guardados seguidos (cada respuesta termina con varios cambios de estado).
  const previo = pendientesSesion.get(id);
  if (previo) window.clearTimeout(previo);
  pendientesSesion.set(
    id,
    window.setTimeout(() => {
      pendientesSesion.delete(id);
      enviarInvestigacion(id, { sesion });
    }, ESPERA_ENVIO_SESION_MS),
  );
}

const ESPERA_ENVIO_SESION_MS = 1500;
const pendientesSesion = new Map<string, number>();
