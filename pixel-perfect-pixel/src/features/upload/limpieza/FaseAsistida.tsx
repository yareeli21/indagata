import { useMemo } from "react";
import { AlertTriangle, CheckCircle2, CloudCheck, Loader2, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { EjecucionLimpieza, HallazgoLimpieza } from "@/types";
import { ResumenAutomatico } from "./ResumenAutomatico";
import { TarjetaHallazgo } from "./TarjetaHallazgo";

interface FaseAsistidaProps {
  ejecucion: EjecucionLimpieza;
  /** Estado del guardado de decisiones: «guardado» solo cuando el servidor confirmó. */
  guardado: "pendiente" | "guardando" | "guardado";
  confirmando: boolean;
  onElegir: (idHallazgo: string, opcion: string) => void;
  onConfirmar: () => void;
}

/** Fase asistida: hallazgos agrupados por tema con su opción sugerida preseleccionada. */
export function FaseAsistida({
  ejecucion,
  guardado,
  confirmando,
  onElegir,
  onConfirmar,
}: FaseAsistidaProps) {
  const { hallazgos } = ejecucion;
  const grupos = useMemo(() => {
    const mapa = new Map<string, HallazgoLimpieza[]>();
    for (const h of hallazgos) mapa.set(h.tema, [...(mapa.get(h.tema) ?? []), h]);
    return [...mapa.entries()];
  }, [hallazgos]);
  const pendientes = ejecucion.pendientesObligatorias;

  return (
    <div className="space-y-6">
      <ResumenAutomatico
        transformaciones={ejecucion.transformaciones}
        metricas={ejecucion.metricasAntes}
      />

      {ejecucion.avisos.map((aviso) => (
        <p
          key={aviso}
          className="flex gap-2 rounded-xl bg-accent-soft p-3 text-sm text-accent-foreground"
        >
          <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden /> {aviso}
        </p>
      ))}

      {grupos.length === 0 ? (
        <div className="flex items-center gap-3 rounded-2xl border border-border bg-card p-5">
          <CheckCircle2 className="size-6 shrink-0 text-success" aria-hidden />
          <p className="text-sm text-foreground">
            No encontramos nada que requiera tu decisión. Revisa el resumen y confirma la limpieza.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          <p className="text-sm text-muted-foreground">
            Revisa lo que encontramos. Ya preseleccionamos la opción sugerida; tú decides. Cada
            cambio se guarda solo.
          </p>
          {grupos.map(([tema, delTema]) => (
            <section key={tema} className="space-y-3">
              <h3 className="flex items-baseline gap-2 font-display text-lg font-bold text-foreground">
                {tema}
                <span className="text-sm font-semibold text-muted-foreground">
                  {delTema.length}
                </span>
              </h3>
              <div className="grid gap-3 xl:grid-cols-2">
                {delTema.map((h) => (
                  <TarjetaHallazgo key={h.id} hallazgo={h} onElegir={(o) => onElegir(h.id, o)} />
                ))}
              </div>
            </section>
          ))}
        </div>
      )}

      <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="flex items-center gap-2 text-sm" aria-live="polite">
          {guardado === "pendiente" ? (
            <>
              <Loader2 className="size-4 text-muted-foreground" aria-hidden /> Cambios sin guardar…
            </>
          ) : guardado === "guardando" ? (
            <>
              <Loader2 className="size-4 animate-spin text-muted-foreground" aria-hidden />{" "}
              Guardando tus decisiones…
            </>
          ) : pendientes > 0 ? (
            <>
              <AlertTriangle className="size-4 text-accent-strong" aria-hidden />
              <span>
                <strong>{pendientes}</strong> decisión{pendientes === 1 ? "" : "es"} pendiente
                {pendientes === 1 ? "" : "s"}
              </span>
            </>
          ) : (
            <>
              <CloudCheck className="size-4 text-success" aria-hidden /> Decisiones guardadas
            </>
          )}
        </p>
        <Button
          size="lg"
          onClick={onConfirmar}
          disabled={pendientes > 0 || confirmando || guardado === "guardando"}
        >
          {confirmando ? <Loader2 className="animate-spin" /> : <ShieldCheck />}
          Confirmar limpieza
        </Button>
      </div>
    </div>
  );
}
