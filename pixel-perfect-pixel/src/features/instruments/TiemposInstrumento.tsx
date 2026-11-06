import { useEffect, useState } from "react";
import { ChevronDown, Timer } from "lucide-react";
import { getTiemposProceso } from "@/api/instrumentos";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";
import type { TiemposProceso } from "@/types";

interface TiemposInstrumentoProps {
  instrumentoId: string;
}

/** «1.8 s», «2 min 05 s». */
function duracion(ms: number | null | undefined): string {
  if (ms == null) return "—";
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)} s`;
  const min = Math.floor(ms / 60_000);
  const seg = Math.round((ms % 60_000) / 1000);
  return `${min} min ${String(seg).padStart(2, "0")} s`;
}

/**
 * Tiempo de cómputo de cada paso del procesamiento (carga, limpieza, metadatos, KPIs, documento,
 * indexación) y latencia del chat. Sirve para estimar cuánto tardaría el procesamiento en un servidor:
 * el «cómputo» no incluye el tiempo que la persona tarda en decidir.
 */
export function TiemposInstrumento({ instrumentoId }: TiemposInstrumentoProps) {
  const [abierto, setAbierto] = useState(false);
  const [datos, setDatos] = useState<TiemposProceso | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  useEffect(() => {
    setDatos(null);
    setAviso(null);
    setAbierto(false);
  }, [instrumentoId]);

  useEffect(() => {
    if (!abierto || datos || aviso || !/^\d+$/.test(instrumentoId)) return;
    let vigente = true;
    getTiemposProceso(instrumentoId)
      .then((r) => vigente && setDatos(r))
      .catch(() => vigente && setAviso("No se pudieron cargar los tiempos."));
    return () => {
      vigente = false;
    };
  }, [abierto, datos, aviso, instrumentoId]);

  return (
    <Collapsible
      open={abierto}
      onOpenChange={setAbierto}
      className="rounded-2xl border border-border"
    >
      <CollapsibleTrigger className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left text-sm font-semibold text-foreground">
        <span className="flex items-center gap-2">
          <Timer className="size-4 text-primary" aria-hidden />
          Tiempos del procesamiento
        </span>
        <ChevronDown
          className={cn("size-4 transition-transform", abierto && "rotate-180")}
          aria-hidden
        />
      </CollapsibleTrigger>
      <CollapsibleContent className="space-y-4 border-t border-border px-4 py-4">
        {aviso && <p className="text-sm text-muted-foreground">{aviso}</p>}
        {abierto && !datos && !aviso && (
          <p className="text-sm text-muted-foreground">Cargando tiempos…</p>
        )}
        {datos && datos.pasos.length === 0 && (
          <p className="text-sm text-muted-foreground">
            Este instrumento se procesó antes de que se registraran los tiempos (25 oct). Los
            instrumentos que subas desde ahora los mostrarán aquí.
          </p>
        )}
        {datos && datos.pasos.length > 0 && (
          <>
            <dl className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              <div className="rounded-xl bg-muted/40 px-3 py-2">
                <dt className="text-xs text-muted-foreground">Cómputo total</dt>
                <dd className="font-display text-lg font-bold tabular-nums text-primary">
                  {duracion(datos.computo_ms)}
                </dd>
              </div>
              <div className="rounded-xl bg-muted/40 px-3 py-2">
                <dt className="text-xs text-muted-foreground">
                  De la carga a lo último (con tus decisiones)
                </dt>
                <dd className="font-display text-lg font-bold tabular-nums text-foreground">
                  {duracion(datos.punta_a_punta_ms)}
                </dd>
              </div>
              <div className="rounded-xl bg-muted/40 px-3 py-2">
                <dt className="text-xs text-muted-foreground">
                  Respuestas del chat (mediana · p95)
                </dt>
                <dd className="font-display text-lg font-bold tabular-nums text-foreground">
                  {datos.chat.consultas
                    ? `${duracion(datos.chat.p50_ms)} · ${duracion(datos.chat.p95_ms)}`
                    : "sin consultas"}
                </dd>
              </div>
            </dl>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-muted-foreground">
                    <th className="py-1 pr-3 font-medium">Paso</th>
                    <th className="py-1 pr-3 text-right font-medium">Cómputo</th>
                    <th className="py-1 font-medium">Cuándo</th>
                  </tr>
                </thead>
                <tbody>
                  {datos.pasos.map((p) => (
                    <tr key={`${p.paso}-${p.inicio}`} className="border-t border-border">
                      <td className="py-1.5 pr-3 text-foreground">
                        {p.etiqueta}
                        {p.segundo_plano && (
                          <span className="ml-1 text-xs text-muted-foreground">
                            (en segundo plano)
                          </span>
                        )}
                      </td>
                      <td className="py-1.5 pr-3 text-right tabular-nums">
                        {duracion(p.duracion_ms)}
                      </td>
                      <td className="py-1.5 text-xs text-muted-foreground">
                        {new Date(`${p.inicio}Z`).toLocaleString("es-MX")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-xs leading-snug text-muted-foreground">
              El cómputo es lo que tarda la máquina en cada paso, sin contar el tiempo que tardas en
              decidir las tarjetas o revisar los metadatos: es la base para estimar la duración en
              un servidor. Los pasos «en segundo plano» corren después de responder y no hacen
              esperar a la persona. Las cifras dependen del equipo donde corre el sistema.
            </p>
          </>
        )}
      </CollapsibleContent>
    </Collapsible>
  );
}
