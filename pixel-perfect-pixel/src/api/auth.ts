import type { Usuario } from "@/types";
import { simularRed } from "./client";

const CUENTAS: Record<string, Usuario> = {
  ana: {
    id: "usr-ana",
    usuario: "ana",
    nombre: "Ana Beltrán",
    rol: "Investigador",
    investigadorId: "inv-ana",
  },
  admin: {
    id: "usr-admin",
    usuario: "admin",
    nombre: "Administración INDAGATA",
    rol: "Administrador",
    investigadorId: "inv-ana",
  },
};

export function iniciarSesion(usuario: string, _contrasena: string): Promise<Usuario> {
  const cuenta = CUENTAS[usuario.trim().toLowerCase()];
  if (!cuenta) {
    return Promise.reject(new Error("Usuario o contraseña incorrectos"));
  }
  return simularRed(cuenta, 400);
}
