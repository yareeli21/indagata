import type { PuntoEspacio } from "@/types";
import { SimboloTipo } from "./SimboloTipo";

interface TooltipPuntoProps {
  punto: PuntoEspacio;
  /** Posición del punto en el mapa (px). */
  x: number;
  y: number;
  /** Tamaño del mapa, para no salirse de él. */
  ancho: number;
  alto: number;
}

const NOMBRE_TIPO = {
  kpi: "KPI educativo",
  instrumento: "Instrumento",
  chunk: "Chunk (provisional)",
};
const ANCHO_TOOLTIP = 320;

/** Tarjeta flotante con el nombre del punto y un resumen de una línea. */
export function TooltipPunto({ punto, x, y, ancho, alto }: TooltipPuntoProps) {
  const izquierda = x + 18 + ANCHO_TOOLTIP > ancho ? Math.max(8, x - 18 - ANCHO_TOOLTIP) : x + 18;
  const arriba = Math.min(Math.max(8, y - 24), Math.max(8, alto - 170));

  return (
    <div
      role="tooltip"
      className="pointer-events-none absolute z-10 rounded-2xl border border-border bg-card/97 p-4 shadow-elevated backdrop-blur-sm"
      style={{ left: izquierda, top: arriba, width: ANCHO_TOOLTIP }}
    >
      <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-muted-foreground">
        <SimboloTipo tipo={punto.tipo} />
        {NOMBRE_TIPO[punto.tipo]}
      </p>
      <p className="mt-1.5 font-display text-base font-bold leading-snug text-foreground">
        {punto.etiqueta}
      </p>
      {punto.resumen && (
        <p className="mt-1 line-clamp-2 text-sm leading-snug text-muted-foreground">
          {punto.resumen}
        </p>
      )}
      {punto.detalle && <p className="mt-2 text-xs font-semibold text-primary">{punto.detalle}</p>}
    </div>
  );
}
