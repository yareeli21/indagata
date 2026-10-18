import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  crearInvestigacion,
  eliminarInvestigacion,
  getInvestigaciones,
} from "@/api/investigaciones";
import type { Investigacion } from "@/types";

const CLAVE = "indagata.investigacionActiva";

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
  const [investigaciones, setInvestigaciones] = useState<Investigacion[]>([]);
  const [activaId, setActivaId] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    let vivo = true;
    getInvestigaciones().then((datos) => {
      if (!vivo) return;
      setInvestigaciones(datos);
      setActivaId(window.localStorage.getItem(CLAVE));
      setCargando(false);
    });
    return () => {
      vivo = false;
    };
  }, []);

  const seleccionar = useCallback((id: string) => {
    window.localStorage.setItem(CLAVE, id);
    setActivaId(id);
  }, []);

  const crear = useCallback(async (nombre: string) => {
    const nueva = await crearInvestigacion(nombre, "inv-ana");
    setInvestigaciones((prev) => [...prev, nueva]);
    window.localStorage.setItem(CLAVE, nueva.id);
    setActivaId(nueva.id);
    return nueva;
  }, []);

  const eliminar = useCallback(
    async (id: string) => {
      await eliminarInvestigacion(id);
      setInvestigaciones((prev) => prev.filter((i) => i.id !== id));
      if (activaId === id) {
        try {
          window.localStorage.removeItem(CLAVE);
        } catch {
          /* almacenamiento no disponible */
        }
        setActivaId(null);
      }
    },
    [activaId],
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
