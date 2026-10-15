import { AlertTriangle, X } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { ClusterEspacio, KpiCatalogo, PuntoEspacio, VecinosEspacio } from "@/types";
import { claseCluster } from "./dibujo";
import { FichaInstrumento } from "./FichaInstrumento";
import { FichaKpi } from "./FichaKpi";
import { ListaVecinos } from "./ListaVecinos";
import { SimboloTipo } from "./SimboloTipo";

interface PanelDetalleProps {
  punto: PuntoEspacio;
  vecinos: VecinosEspacio | null;
  cargandoVecinos: boolean;
  errorVecinos: string | null;
  clusters: ClusterEspacio[];
  kpiCatalogo: KpiCatalogo | undefined;
  enMapa: (id: string) => boolean;
  onSeleccionar: (id: string) => void;
  onCerrar: () => void;
  className?: string | undefined;
}

const NOMBRE_TIPO = { kpi: "KPI educativo", instrumento: "Instrumento", chunk: "Chunk" };

function Provisional() {
  return (
    <span className="rounded-full bg-accent-soft px-2 py-0.5 text-[0.75rem] font-bold normal-case tracking-normal text-accent-strong">
      provisionales
    </span>
  );
}

/**
 * Detalle del punto seleccionado: su ficha y sus vecinos más parecidos (coseno en
 * el espacio original). Se muestra en la barra lateral o en una hoja en móvil.
 */
export function PanelDetalle({
  punto,
  vecinos,
  cargandoVecinos,
  errorVecinos,
  clusters,
  kpiCatalogo,
  enMapa,
  onSeleccionar,
  onCerrar,
  className,
}: PanelDetalleProps) {
  const cluster =
    punto.clusterId != null ? clusters.find((c) => c.id === punto.clusterId) : undefined;
  const listas = vecinos ? ordenListas(punto, vecinos) : [];

  return (
    <article className={cn("space-y-6", className)} aria-label={`Detalle: ${punto.etiqueta}`}>
      <header className="space-y-2">
        <div className="flex items-start justify-between gap-3">
          <p className="flex items-center gap-2 pt-1 text-xs font-bold uppercase tracking-wide text-muted-foreground">
            <SimboloTipo tipo={punto.tipo} clusterId={punto.clusterId} />
            {NOMBRE_TIPO[punto.tipo]}
            {punto.tipo === "chunk" && <Provisional />}
          </p>
          <button
            type="button"
            onClick={onCerrar}
            aria-label="Cerrar el detalle"
            title="Cerrar (Esc)"
            className="-mr-2 -mt-1 flex size-10 shrink-0 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-primary-soft hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <X className="size-5" />
          </button>
        </div>
        <h2 className="font-display text-xl font-bold leading-snug text-foreground">
          {punto.etiqueta}
        </h2>
        {cluster && (
          <p className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-xs font-semibold text-muted-foreground">
            <span aria-hidden className={cn("size-2.5 rounded-full", claseCluster(cluster.id))} />
            Grupo: {cluster.etiqueta}
          </p>
        )}
      </header>

      {punto.tipo === "kpi" && <FichaKpi kpi={kpiCatalogo} resumen={punto.resumen} />}
      {punto.tipo === "instrumento" && <FichaInstrumento id={punto.ref} resumen={punto.resumen} />}
      {punto.tipo === "chunk" && (
        <div className="space-y-2">
          <p className="whitespace-pre-line rounded-xl bg-primary-soft/60 p-3 text-sm leading-relaxed text-foreground">
            {vecinos?.origen.texto || punto.resumen}
          </p>
          {punto.detalle && (
            <p className="text-xs font-semibold text-muted-foreground">Sección: {punto.detalle}</p>
          )}
        </div>
      )}

      <div className="space-y-6 border-t border-border/70 pt-6">
        {cargandoVecinos && (
          <div className="space-y-3" role="status" aria-label="Buscando vecinos">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-12 rounded-xl" />
            ))}
          </div>
        )}
        {errorVecinos && !cargandoVecinos && (
          <p className="flex gap-2 rounded-xl bg-accent-soft p-3 text-sm text-accent-foreground">
            <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden />
            {errorVecinos}
          </p>
        )}
        {!cargandoVecinos &&
          listas.map((l) => (
            <ListaVecinos
              key={l.titulo}
              titulo={l.titulo}
              vecinos={l.vecinos}
              enMapa={enMapa}
              onSeleccionar={onSeleccionar}
              insignia={l.chunks ? <Provisional /> : undefined}
              vacio={l.vacio}
            />
          ))}
        {vecinos && !cargandoVecinos && (
          <p className="text-xs leading-relaxed text-muted-foreground">
            Similitud coseno entre los vectores completos (768 dimensiones). No depende de la
            posición en el mapa ni de la vista elegida.
          </p>
        )}
      </div>
    </article>
  );
}

function ordenListas(punto: PuntoEspacio, v: VecinosEspacio) {
  const chunksVacio = "Aún no hay chunks del RAG para comparar.";
  if (punto.tipo === "kpi") {
    return [
      { titulo: "Instrumentos más asociados", vecinos: v.instrumentos },
      { titulo: "Preguntas que lo miden", vecinos: v.chunks, chunks: true, vacio: chunksVacio },
      { titulo: "KPIs parecidos", vecinos: v.kpis },
    ];
  }
  if (punto.tipo === "instrumento") {
    return [
      { titulo: "KPIs más cercanos", vecinos: v.kpis },
      {
        titulo: "Fragmentos representativos",
        vecinos: v.chunks,
        chunks: true,
        vacio: "Este instrumento aún no está en el RAG.",
      },
      { titulo: "Instrumentos parecidos", vecinos: v.instrumentos },
    ];
  }
  return [
    { titulo: "KPIs más cercanos", vecinos: v.kpis },
    { titulo: "Instrumentos más cercanos", vecinos: v.instrumentos },
    { titulo: "Chunks parecidos", vecinos: v.chunks, chunks: true, vacio: chunksVacio },
  ];
}
