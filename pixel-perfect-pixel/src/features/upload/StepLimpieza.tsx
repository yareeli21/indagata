import { useCallback, useEffect, useRef, useState } from "react";
import { AlertTriangle, FileWarning, RotateCcw, Upload } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { EstadoVacio } from "@/components/shared/EstadoVacio";
import { ProcesandoIA } from "@/components/shared/ProcesandoIA";
import { confirmarLimpieza, ejecutarLimpieza, guardarDecisiones } from "@/api/limpieza";
import type { ErrorHttp } from "@/api/client";
import type { EjecucionLimpieza } from "@/types";
import { FaseAsistida } from "./limpieza/FaseAsistida";
import { VistaFinalLimpieza } from "./limpieza/VistaFinalLimpieza";
import { DETALLE_PROCESANDO } from "./limpieza/textos";

interface StepLimpiezaProps {
  idCrudo: number;
  /** Tipo de instrumento (para el mensaje mientras se limpia). */
  tipo: string | null;
  /** Versión vigente de la limpieza (vive en el wizard para no perderla al navegar). */
  ejecucion: EjecucionLimpieza | null;
  onEjecucion: (e: EjecucionLimpieza) => void;
  onContinuar: () => void;
  onCambiarArchivo: () => void;
}

/** Espera tras la última decisión antes de guardarla (agrupa clics seguidos). */
const ESPERA_GUARDADO_MS = 400;

function mensajeDe(e: unknown, defecto: string): string {
  return e instanceof Error && e.message ? e.message : defecto;
}

/** Aplica decisiones locales a una ejecución (vista optimista mientras se guardan). */
function conDecisiones(
  e: EjecucionLimpieza,
  decisiones: Record<string, string>,
): EjecucionLimpieza {
  const hallazgos = e.hallazgos.map((h) =>
    h.id in decisiones ? { ...h, decision: decisiones[h.id] ?? null } : h,
  );
  return {
    ...e,
    hallazgos,
    pendientesObligatorias: hallazgos.filter((h) => h.obligatoria && h.decision === null).length,
  };
}

/**
 * Paso «Limpieza»: corre la fase automática (o retoma la versión en curso), guarda
 * cada decisión conforme se toma y, al confirmar, muestra la vista final.
 */
export function StepLimpieza({
  idCrudo,
  tipo,
  ejecucion,
  onEjecucion,
  onContinuar,
  onCambiarArchivo,
}: StepLimpiezaProps) {
  const [cargando, setCargando] = useState(false);
  const [noDisponible, setNoDisponible] = useState<string | null>(null);
  const [errorCarga, setErrorCarga] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);
  // Hay decisiones elegidas que aún no confirma el servidor.
  const [sinGuardar, setSinGuardar] = useState(false);
  const [confirmando, setConfirmando] = useState(false);
  const [reajustando, setReajustando] = useState(false);

  // Decisiones aún no enviadas y temporizador del guardado diferido.
  const pendientesRef = useRef<Record<string, string>>({});
  const temporizadorRef = useRef<number | null>(null);
  const ejecucionRef = useRef(ejecucion);
  ejecucionRef.current = ejecucion;

  const ejecutar = useCallback(
    async (nueva: boolean) => {
      setErrorCarga(null);
      setNoDisponible(null);
      try {
        onEjecucion(await ejecutarLimpieza(idCrudo, nueva));
      } catch (e) {
        if ((e as ErrorHttp).status === 501)
          setNoDisponible(mensajeDe(e, "La limpieza de este tipo aún no está disponible."));
        else setErrorCarga(mensajeDe(e, "No se pudo limpiar el archivo."));
      }
    },
    [idCrudo, onEjecucion],
  );

  // Al entrar al paso: fase automática, o se retoma la versión en curso.
  useEffect(() => {
    if (ejecucion && ejecucion.idCrudo === idCrudo) return;
    let activo = true;
    setCargando(true);
    void ejecutar(false).finally(() => activo && setCargando(false));
    return () => {
      activo = false;
    };
    // Solo al cambiar de instrumento.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idCrudo]);

  /** Envía las decisiones acumuladas. Devuelve la ejecución actualizada (o null si falló). */
  const guardarPendientes = useCallback(async (): Promise<EjecucionLimpieza | null> => {
    if (temporizadorRef.current !== null) {
      window.clearTimeout(temporizadorRef.current);
      temporizadorRef.current = null;
    }
    const actual = ejecucionRef.current;
    const lote = pendientesRef.current;
    if (!actual || Object.keys(lote).length === 0) return actual;
    pendientesRef.current = {};
    setGuardando(true);
    try {
      const resultado = await guardarDecisiones(idCrudo, actual.version, lote);
      // Lo que el investigador eligió mientras se guardaba sigue pendiente.
      const vista = conDecisiones(resultado, pendientesRef.current);
      onEjecucion(vista);
      setSinGuardar(Object.keys(pendientesRef.current).length > 0);
      return vista;
    } catch (e) {
      pendientesRef.current = { ...lote, ...pendientesRef.current };
      toast.error(mensajeDe(e, "No se pudieron guardar tus decisiones."));
      return null;
    } finally {
      setGuardando(false);
    }
  }, [idCrudo, onEjecucion]);

  function elegir(idHallazgo: string, opcion: string) {
    const actual = ejecucionRef.current;
    if (!actual) return;
    pendientesRef.current = { ...pendientesRef.current, [idHallazgo]: opcion };
    setSinGuardar(true);
    onEjecucion(conDecisiones(actual, { [idHallazgo]: opcion }));
    if (temporizadorRef.current !== null) window.clearTimeout(temporizadorRef.current);
    temporizadorRef.current = window.setTimeout(() => void guardarPendientes(), ESPERA_GUARDADO_MS);
  }

  // Al salir del paso se envía lo que quede pendiente.
  useEffect(
    () => () => {
      if (Object.keys(pendientesRef.current).length > 0) void guardarPendientes();
    },
    [guardarPendientes],
  );

  // Si se cierra o recarga la página con decisiones sin enviar, se mandan con
  // `keepalive` (la petición termina aunque la página ya no exista).
  useEffect(() => {
    function alOcultar() {
      const actual = ejecucionRef.current;
      const lote = pendientesRef.current;
      if (!actual || Object.keys(lote).length === 0) return;
      pendientesRef.current = {};
      void guardarDecisiones(idCrudo, actual.version, lote, true).catch(() => undefined);
    }
    window.addEventListener("pagehide", alOcultar);
    return () => window.removeEventListener("pagehide", alOcultar);
  }, [idCrudo]);

  async function confirmar() {
    setConfirmando(true);
    try {
      const guardada = await guardarPendientes();
      if (!guardada) return;
      const resultado = await confirmarLimpieza(idCrudo, guardada.version);
      onEjecucion(resultado);
      if (resultado.estado === "confirmada") toast.success("Limpieza confirmada");
    } catch (e) {
      toast.error(mensajeDe(e, "No se pudo confirmar la limpieza."));
    } finally {
      setConfirmando(false);
    }
  }

  async function reajustar() {
    setReajustando(true);
    await ejecutar(true);
    setReajustando(false);
  }

  if (cargando || (!ejecucion && !errorCarga && !noDisponible)) {
    return (
      <ProcesandoIA
        mensaje="Limpiando el archivo…"
        detalle={DETALLE_PROCESANDO[tipo ?? ""] ?? DETALLE_PROCESANDO["Encuesta"]}
      />
    );
  }

  if (noDisponible) {
    // Sin limpieza confirmada, metadata-service no acepta el instrumento: se pide otro archivo.
    return (
      <EstadoVacio
        icono={FileWarning}
        titulo="Este archivo no se puede limpiar"
        descripcion={`${noDisponible} Sube el instrumento en un formato compatible con su tipo.`}
        accion={
          <Button size="lg" onClick={onCambiarArchivo}>
            <Upload /> Subir otro archivo
          </Button>
        }
      />
    );
  }

  if (errorCarga || !ejecucion) {
    return (
      <EstadoVacio
        icono={AlertTriangle}
        titulo="No se pudo limpiar el archivo"
        descripcion={errorCarga ?? "Inténtalo de nuevo."}
        accion={
          <Button variant="outline" size="lg" onClick={() => void ejecutar(false)}>
            <RotateCcw /> Reintentar
          </Button>
        }
      />
    );
  }

  if (ejecucion.estado === "fallida") {
    return (
      <EstadoVacio
        icono={AlertTriangle}
        titulo="La limpieza no pudo completarse"
        descripcion={`${ejecucion.error ?? "Ocurrió un error al limpiar el archivo."} No se enviará nada a metadatos hasta resolverlo.`}
        accion={
          <div className="flex flex-wrap justify-center gap-3">
            <Button variant="outline" size="lg" onClick={onCambiarArchivo}>
              <Upload /> Subir otro archivo
            </Button>
            <Button size="lg" onClick={() => void reajustar()} disabled={reajustando}>
              <RotateCcw /> Reintentar
            </Button>
          </div>
        }
      />
    );
  }

  if (ejecucion.estado === "confirmada" && ejecucion.vistaFinal) {
    return (
      <VistaFinalLimpieza
        vista={ejecucion.vistaFinal}
        reajustando={reajustando}
        onReajustar={() => void reajustar()}
        onContinuar={onContinuar}
      />
    );
  }

  return (
    <FaseAsistida
      ejecucion={ejecucion}
      guardado={guardando ? "guardando" : sinGuardar ? "pendiente" : "guardado"}
      confirmando={confirmando}
      onElegir={elegir}
      onConfirmar={() => void confirmar()}
    />
  );
}
