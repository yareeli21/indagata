import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { iniciarSesion } from "@/api/auth";
import { borrarToken } from "@/api/client";
import type { Usuario } from "@/types";

const CLAVE = "indagata.sesion";

interface AuthContextValue {
  usuario: Usuario | null;
  cargando: boolean;
  entrar: (usuario: string, contrasena: string) => Promise<Usuario>;
  salir: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    try {
      const guardado = window.localStorage.getItem(CLAVE);
      if (guardado) setUsuario(JSON.parse(guardado) as Usuario);
    } catch {
      /* sesión ilegible: se ignora */
    }
    setCargando(false);
  }, []);

  const entrar = useCallback(async (nombreUsuario: string, contrasena: string) => {
    const cuenta = await iniciarSesion(nombreUsuario, contrasena);
    window.localStorage.setItem(CLAVE, JSON.stringify(cuenta));
    setUsuario(cuenta);
    return cuenta;
  }, []);

  const salir = useCallback(() => {
    window.localStorage.removeItem(CLAVE);
    borrarToken();
    setUsuario(null);
  }, []);

  const value = useMemo(
    () => ({ usuario, cargando, entrar, salir }),
    [usuario, cargando, entrar, salir],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de AuthProvider");
  return ctx;
}
