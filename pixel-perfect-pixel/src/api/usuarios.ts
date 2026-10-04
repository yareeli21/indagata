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
      return "Datos inválidos: revisa el correo (formato válido, sin dominios reservados) y que la contraseña tenga al menos 6 caracteres.";
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
