import type { Rol, Usuario } from "@/types";
import { API_URL, guardarToken, pedir } from "./client";

/** Representación de salida del backend (shared/schemas/usuario.py: UsuarioRead). */
interface UsuarioRead {
  usuario_id: number;
  nombre: string;
  email: string;
  rol: string | null;
}

interface RespuestaLogin {
  access_token: string;
  token_type: string;
  usuario: UsuarioRead;
}

function mapearRol(rol: string | null | undefined): Rol {
  return (rol ?? "").trim().toLowerCase() === "administrador" ? "Administrador" : "Investigador";
}

function mapearUsuario(datos: UsuarioRead): Usuario {
  const id = String(datos.usuario_id);
  return {
    id,
    nombre: datos.nombre,
    usuario: datos.email,
    rol: mapearRol(datos.rol),
    investigadorId: id,
  };
}

export async function iniciarSesion(usuario: string, contrasena: string): Promise<Usuario> {
  const respuesta = await pedir<RespuestaLogin>(`${API_URL}/auth/login`, {
    method: "POST",
    body: { email: usuario, password: contrasena },
  });
  guardarToken(respuesta.access_token);
  return mapearUsuario(respuesta.usuario);
}
