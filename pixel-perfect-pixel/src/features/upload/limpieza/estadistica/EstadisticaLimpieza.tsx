import { useState } from "react";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import type { EstadisticaLimpieza as Estadistica, FraseResumen } from "@/types";
import { EstadisticaEncuesta } from "./EstadisticaEncuesta";
import { EstadisticaEntrevista } from "./EstadisticaEntrevista";
import { EstadisticaPrueba } from "./EstadisticaPrueba";
import { GlosarioEstadistico, ResumenEstadistica } from "./ResumenEstadistica";

interface EstadisticaLimpiezaProps {
  despues: Estadistica | null | undefined;
  antes: Estadistica | null | undefined;
  /** Frases clave del instrumento limpio (ausentes en limpiezas antiguas). */
  resumen?: FraseResumen[] | undefined;
}

function vacia(e: Estadistica | null | undefined): boolean {
  return !e || (!e.columnas?.length && !e.reactivos?.length && !e.hablantes?.length);
}

/** Medidas estadísticas del instrumento limpio, con la opción de ver las del archivo original. */
export function EstadisticaLimpieza({ despues, antes, resumen }: EstadisticaLimpiezaProps) {
  const [momento, setMomento] = useState<"despues" | "antes">("despues");
  const estadistica = momento === "antes" && !vacia(antes) ? antes : despues;

  if (vacia(estadistica)) {
    return (
      <p className="rounded-2xl border border-border bg-card p-4 text-sm text-muted-foreground">
        Este instrumento no tiene medidas estadísticas (es un documento de texto).
      </p>
    );
  }

  return (
    <div className="space-y-5">
      {!vacia(antes) && (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-muted-foreground">
            {momento === "despues"
              ? "Medidas del instrumento limpio, con tus decisiones aplicadas."
              : "Medidas del archivo antes de aplicar tus decisiones."}
          </p>
          <ToggleGroup
            type="single"
            variant="outline"
            size="sm"
            value={momento}
            onValueChange={(v) => v && setMomento(v as "despues" | "antes")}
            aria-label="Momento de la limpieza"
          >
            <ToggleGroupItem value="despues">Después de limpiar</ToggleGroupItem>
            <ToggleGroupItem value="antes">Antes</ToggleGroupItem>
          </ToggleGroup>
        </div>
      )}
      {momento === "despues" && resumen?.length ? (
        <ResumenEstadistica frases={resumen} />
      ) : (
        <GlosarioEstadistico />
      )}
      {estadistica?.reactivos?.length ? (
        <EstadisticaPrueba estadistica={estadistica} />
      ) : estadistica?.hablantes ? (
        <EstadisticaEntrevista estadistica={estadistica} />
      ) : (
        <EstadisticaEncuesta estadistica={estadistica!} />
      )}
    </div>
  );
}
