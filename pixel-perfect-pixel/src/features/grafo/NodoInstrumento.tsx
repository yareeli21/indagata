import { Handle, Position, type NodeProps } from "@xyflow/react";
import { cn } from "@/lib/utils";
import type { NodoGrafo, Recomendacion } from "@/api/grafo";

/** Datos que cada nodo del grafo transporta en React Flow. */
export interface DatosNodoInstrumento extends Record<string, unknown> {
  instrumento: NodoGrafo | Recomendacion;
  /** Clasificación visual del nodo dentro del grafo. */
  grupo: "acervo" | "activo" | "recomendado";
  /** Razón de recomendación (solo nodos recomendados). */
  razon?: string;
}

// Token semántico de color por tipo de instrumento.
const COLOR_POR_TIPO: Record<NodoGrafo["tipo"], string> = {
  Encuesta: "bg-chart-1",
  Entrevista: "bg-chart-2",
  "Prueba estandarizada": "bg-chart-4",
};

// Tamaño del nodo proporcional al número de KPIs (acotado).
function tamanoPorKpis(numKpis: number): number {
  const base = 120;
  return base + Math.min(numKpis, 8) * 10;
}

function etiquetaGrupo(grupo: DatosNodoInstrumento["grupo"]): string {
  if (grupo === "activo") return "En tu investigación";
  if (grupo === "recomendado") return "Recomendado";
  return "Acervo";
}

/**
 * Nodo custom del grafo: color por tipo, tamaño por nº de KPIs, e indicador de
 * si es propio / activo / recomendado. Solo tokens semánticos.
 */
export function NodoInstrumento({ data, selected }: NodeProps) {
  const { instrumento, grupo, razon } = data as DatosNodoInstrumento;
  const numKpis = instrumento.kpis.length;
  const ancho = tamanoPorKpis(numKpis);

  return (
    <div
      className={cn(
        "flex flex-col gap-1.5 rounded-xl border bg-card px-3 py-2.5 text-left shadow-card transition-colors",
        grupo === "activo" && "border-primary ring-2 ring-primary/40",
        grupo === "recomendado" && "border-dashed border-accent",
        grupo === "acervo" && "border-border",
        selected && "ring-2 ring-ring",
      )}
      style={{ width: ancho }}
    >
      <Handle type="target" position={Position.Top} className="!bg-muted-foreground" />
      <div className="flex items-center gap-2">
        <span
          aria-hidden
          className={cn("size-2.5 shrink-0 rounded-full", COLOR_POR_TIPO[instrumento.tipo])}
        />
        <span className="truncate font-display text-xs font-semibold text-foreground">
          {instrumento.titulo}
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-1.5">
        <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
          {instrumento.tipo}
        </span>
        <span className="rounded-full bg-secondary px-2 py-0.5 text-[10px] font-medium text-secondary-foreground">
          {numKpis} KPI{numKpis !== 1 ? "s" : ""}
        </span>
        {instrumento.esPropio && (
          <span className="rounded-full bg-primary-soft px-2 py-0.5 text-[10px] font-medium text-primary">
            Propio
          </span>
        )}
      </div>

      {grupo === "recomendado" && razon && (
        <p className="truncate text-[10px] text-accent-foreground">{razon}</p>
      )}
      {grupo !== "recomendado" && (
        <p className="text-[10px] text-muted-foreground">{etiquetaGrupo(grupo)}</p>
      )}

      <Handle type="source" position={Position.Bottom} className="!bg-muted-foreground" />
    </div>
  );
}
