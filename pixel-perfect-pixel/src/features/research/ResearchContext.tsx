import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  CUENTA_INVESTIGACIONES_ANTERIORES,
  crearInvestigacion,
  eliminarInvestigacion,
  getInvestigaciones,
  reclamarInvestigacionesAnteriores,
  sincronizarInvestigaciones,
} from "@/api/investigaciones";
import { useAuth } from "@/features/auth/AuthContext";
import type { Investigacion } from "@/types";

/** La investigación activa se recuerda por usuario: cada quien tiene las suyas. */
const claveActiva = (usuarioId: string) => `indagata.investigacionActiva.${usuarioId}`;

function leerActiva(usuarioId: string): string | null {
  try {
    return window.localStorage.getItem(claveActiva(usuarioId));
  } catch {
    return null;
  }
}

/** Clave única que se usaba antes del 16 nov (sin usuario). */
function leerActivaAnterior(): string | null {
  try {
    return window.localStorage.getItem("indagata.investigacionActiva");
  } catch {
    return null;
  }
}

function guardarActiva(usuarioId: string, id: string | null): void {
  try {
    if (id) window.localStorage.setItem(claveActiva(usuarioId), id);
    else window.localStorage.removeItem(claveActiva(usuarioId));
  } catch {
    /* almacenamiento no disponible */
  }
}

interface ResearchContextValue {
  investigaciones: Investigacion[];
  activa: Investigacion | null;
  cargando: boolean;
  seleccionar: (id: string) => void;
  crear: (nombre: string) => Promise<Investigacion>;
  /** Borra la investigación y su conversación; si era la activa, no queda ninguna activa. */
  eliminar: (id: string) => Promise<void>;
}

const ResearchContext = createContext<ResearchContextValue | null>(null);

export function ResearchProvider({ children }: { children: ReactNode }) {
  const { usuario, cargando: cargandoSesion } = useAuth();
  const usuarioId = usuario?.id ?? null;
  const [investigaciones, setInvestigaciones] = useState<Investigacion[]>([]);
  const [activaId, setActivaId] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);

  // Se recargan al cambiar de usuario (cerrar sesión y entrar con otra cuenta en el mismo navegador).
  useEffect(() => {
    if (cargandoSesion) return;
    if (!usuario) {
      setInvestigaciones([]);
      setActivaId(null);
      setCargando(false);
      return;
    }
    let vivo = true;
    setCargando(true);
    const cuentaAnterior = usuario.usuario === CUENTA_INVESTIGACIONES_ANTERIORES;
    if (cuentaAnterior) reclamarInvestigacionesAnteriores(usuario.id);
    // 25 nov: primero se junta con lo guardado en el servidor (investigaciones de otros dispositivos).
    sincronizarInvestigaciones(usuario.id)
      .then(() => getInvestigaciones(usuario.id))
      .then((datos) => {
        if (!vivo) return;
        setInvestigaciones(datos);
        const guardada = leerActiva(usuario.id) ?? (cuentaAnterior ? leerActivaAnterior() : null);
        setActivaId(datos.some((i) => i.id === guardada) ? guardada : null);
        setCargando(false);
      });
    return () => {
      vivo = false;
    };
  }, [usuario, cargandoSesion]);

  const seleccionar = useCallback(
    (id: string) => {
      if (usuarioId) guardarActiva(usuarioId, id);
      setActivaId(id);
    },
    [usuarioId],
  );

  const crear = useCallback(
    async (nombre: string) => {
      if (!usuarioId) throw new Error("Inicia sesión para crear una investigación.");
      const nueva = await crearInvestigacion(nombre, usuarioId);
      setInvestigaciones((prev) => [...prev, nueva]);
      guardarActiva(usuarioId, nueva.id);
      setActivaId(nueva.id);
      return nueva;
    },
    [usuarioId],
  );

  const eliminar = useCallback(
    async (id: string) => {
      await eliminarInvestigacion(id);
      setInvestigaciones((prev) => prev.filter((i) => i.id !== id));
      if (activaId === id) {
        if (usuarioId) guardarActiva(usuarioId, null);
        setActivaId(null);
      }
    },
    [activaId, usuarioId],
  );

  const activa = useMemo(
    () => investigaciones.find((i) => i.id === activaId) ?? null,
    [investigaciones, activaId],
  );

  const value = useMemo(
    () => ({ investigaciones, activa, cargando, seleccionar, crear, eliminar }),
    [investigaciones, activa, cargando, seleccionar, crear, eliminar],
  );

  return <ResearchContext.Provider value={value}>{children}</ResearchContext.Provider>;
}

export function useResearch(): ResearchContextValue {
  const ctx = useContext(ResearchContext);
  if (!ctx) throw new Error("useResearch debe usarse dentro de ResearchProvider");
  return ctx;
}
