import type { Rol } from "@/types";
import { API_URL, pedir, type ErrorHttp } from "./client";

/** Datos del formulario de alta (rol capitalizado del dominio del front). */
export interface DatosNuevoUsuario {
  nombre: string;
  email: string;
  password: string;
  rol: Rol; // "Investigador" | "Administrador"
}

/** Representación de salida del backend (UsuarioRead). El `rol` llega en minúsculas. */
export interface UsuarioCreado {
  usuario_id: number;
  nombre: string;
  email: string;
  rol: string;
}

/** Convierte el rol del dominio del front a la forma en minúsculas que exige el backend. */
function rolAMinusculas(rol: Rol): "investigador" | "administrador" {
  return rol === "Administrador" ? "administrador" : "investigador";
}

/** Traduce un error de `pedir` al mensaje en español según el código HTTP. */
function mensajeError(error: unknown): string {
  const status = (error as ErrorHttp | undefined)?.status;
  switch (status) {
    case 409:
      return "Ya existe un usuario con ese correo electrónico.";
    case 403:
      return "No tienes permisos para crear usuarios (se requiere rol administrador).";
    case 422:
      return "Datos inválidos: revisa el correo (formato válido, sin dominios reservados) y que la contraseña tenga al menos 8 caracteres.";
    case 401:
      return "Tu sesión expiró, vuelve a iniciar sesión.";
    default:
      return "No fue posible crear el usuario. Intenta de nuevo.";
  }
}

/**
 * Da de alta un usuario llamando al endpoint existente POST /auth/register
 * del api-gateway con el JWT de administrador ya guardado (auth: true).
 */
export async function registrarUsuario(datos: DatosNuevoUsuario): Promise<UsuarioCreado> {
  try {
    return await pedir<UsuarioCreado>(`${API_URL}/auth/register`, {
      method: "POST",
      auth: true,
      body: {
        nombre: datos.nombre,
        email: datos.email,
        password: datos.password,
        rol: rolAMinusculas(datos.rol),
      },
    });
  } catch (error) {
    throw new Error(mensajeError(error));
  }
}

// ── Gestión de usuarios (24 nov) ──────────────────────────────────────────────────────────────────────

/** Usuario en la lista del administrador (GET /auth/usuarios). */
export interface UsuarioAdmin {
  usuario_id: number;
  nombre: string;
  email: string;
  rol: "investigador" | "administrador" | string;
  activo: boolean;
  instrumentos: number;
  bloqueado: boolean;
  fecha_registro: string | null;
}

/** El backend explica en `detail` por qué no se pudo (último administrador, cuenta con instrumentos…). */
function detalle(error: unknown, defecto: string): Error {
  return new Error(error instanceof Error && error.message ? error.message : defecto);
}

export async function listarUsuarios(): Promise<UsuarioAdmin[]> {
  try {
    return await pedir<UsuarioAdmin[]>(`${API_URL}/auth/usuarios`, { auth: true });
  } catch (error) {
    throw detalle(error, "No fue posible cargar los usuarios.");
  }
}

export async function actualizarUsuario(
  id: number,
  cambios: { nombre?: string; rol?: Rol; activo?: boolean },
): Promise<UsuarioAdmin> {
  try {
    return await pedir<UsuarioAdmin>(`${API_URL}/auth/usuarios/${id}`, {
      method: "PATCH",
      auth: true,
      body: { ...cambios, rol: cambios.rol ? rolAMinusculas(cambios.rol) : undefined },
    });
  } catch (error) {
    throw detalle(error, "No fue posible actualizar el usuario.");
  }
}

export async function restablecerPassword(id: number, password: string): Promise<UsuarioAdmin> {
  try {
    return await pedir<UsuarioAdmin>(`${API_URL}/auth/usuarios/${id}/password`, {
      method: "POST",
      auth: true,
      body: { password },
    });
  } catch (error) {
    throw detalle(error, "No fue posible restablecer la contraseña.");
  }
}

export async function eliminarUsuario(id: number): Promise<void> {
  try {
    await pedir<void>(`${API_URL}/auth/usuarios/${id}`, { method: "DELETE", auth: true });
  } catch (error) {
    throw detalle(error, "No fue posible eliminar el usuario.");
  }
}

export async function cambiarMiPassword(actual: string, nueva: string): Promise<void> {
  try {
    await pedir<void>(`${API_URL}/auth/me/password`, {
      method: "POST",
      auth: true,
      body: { actual, nueva },
    });
  } catch (error) {
    throw detalle(error, "No fue posible cambiar la contraseña.");
  }
}
