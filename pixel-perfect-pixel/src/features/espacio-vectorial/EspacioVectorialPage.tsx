import { useEffect, useState } from "react";
import { AlertTriangle, Network } from "lucide-react";
import {
  CartesianGrid,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import { ChartContainer, type ChartConfig } from "@/components/ui/chart";
import { PageHeader } from "@/components/layout/PageHeader";
import { getEspacioVectorial } from "@/api/espacio";
import type { EspacioVectorial, PuntoVector } from "@/types";

type Estado = "cargando" | "listo" | "error";

// Nombre legible y color (token semántico) por colección conocida.
const COLECCIONES: Record<string, { etiqueta: string; color: string }> = {
  kpis: { etiqueta: "KPIs", color: "var(--chart-1)" },
  summary_instrument: { etiqueta: "Instrumentos", color: "var(--chart-2)" },
};

const configGrafica: ChartConfig = {
  kpis: { label: "KPIs", color: "var(--chart-1)" },
  summary_instrument: { label: "Instrumentos", color: "var(--chart-2)" },
};

function etiquetaColeccion(coleccion: string): string {
  return COLECCIONES[coleccion]?.etiqueta ?? coleccion;
}

function colorColeccion(coleccion: string): string {
  return COLECCIONES[coleccion]?.color ?? "var(--chart-3)";
}

export function EspacioVectorialPage() {
  const [estado, setEstado] = useState<Estado>("cargando");
  const [espacio, setEspacio] = useState<EspacioVectorial | null>(null);
  const [mensajeError, setMensajeError] = useState("");

  useEffect(() => {
    let activo = true;
    setEstado("cargando");
    getEspacioVectorial()
      .then((datos) => {
        if (!activo) return;
        setEspacio(datos);
        setEstado("listo");
      })
      .catch((error: unknown) => {
        if (!activo) return;
        setMensajeError(
          error instanceof Error ? error.message : "No se pudo cargar el espacio vectorial.",
        );
        setEstado("error");
      });
    return () => {
      activo = false;
    };
  }, []);

  // Agrupa los puntos por colección para dibujar un <Scatter> por serie.
  const porColeccion = agruparPorColeccion(espacio?.puntos ?? []);
  const totalPuntos = espacio?.puntos.length ?? 0;

  return (
    <div className="space-y-8 p-6 md:p-8">
      <PageHeader
        titulo="Espacio vectorial"
        descripcion="Proyección 2D (PCA) de los embeddings almacenados en ChromaDB, coloreada por colección."
      />

      {estado === "cargando" && (
        <div className="h-96 animate-pulse rounded-2xl border border-border bg-card" />
      )}

      {estado === "error" && (
        <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-border bg-card px-6 py-14 text-center shadow-card">
          <span className="flex size-10 items-center justify-center rounded-full bg-destructive/10 text-destructive">
            <AlertTriangle className="size-5" />
          </span>
          <p className="font-display text-sm font-semibold">
            No se pudo cargar el espacio vectorial
          </p>
          <p className="max-w-md text-xs text-muted-foreground">{mensajeError}</p>
        </div>
      )}

      {estado === "listo" && totalPuntos === 0 && (
        <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-border bg-card px-6 py-14 text-center shadow-card">
          <span className="flex size-10 items-center justify-center rounded-full bg-muted text-muted-foreground">
            <Network className="size-5" />
          </span>
          <p className="font-display text-sm font-semibold">Aún no hay vectores que mostrar</p>
          <p className="max-w-md text-xs text-muted-foreground">
            Cuando se complete una ingesta, los embeddings aparecerán aquí como un dispersograma.
          </p>
        </div>
      )}

      {estado === "listo" && totalPuntos > 0 && (
        <section className="space-y-4 rounded-2xl border border-border bg-card p-4 shadow-card md:p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="font-display text-sm font-semibold">
              {totalPuntos} vector{totalPuntos !== 1 ? "es" : ""} proyectado
              {totalPuntos !== 1 ? "s" : ""}
            </p>
            {/* Leyenda por colección */}
            <div className="flex flex-wrap items-center gap-4">
              {Object.entries(espacio?.colecciones ?? {}).map(([coleccion, conteo]) => (
                <div
                  key={coleccion}
                  className="flex items-center gap-1.5 text-xs text-muted-foreground"
                >
                  <span
                    aria-hidden
                    className="size-2.5 rounded-full"
                    style={{ background: colorColeccion(coleccion) }}
                  />
                  {etiquetaColeccion(coleccion)} · {conteo}
                </div>
              ))}
            </div>
          </div>

          <ChartContainer config={configGrafica} className="aspect-auto h-[28rem] w-full">
            <ScatterChart margin={{ top: 12, right: 12, bottom: 12, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                type="number"
                dataKey="x"
                name="Componente 1"
                tick={{ fontSize: 10 }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                type="number"
                dataKey="y"
                name="Componente 2"
                tick={{ fontSize: 10 }}
                tickLine={false}
                axisLine={false}
              />
              <ZAxis range={[60, 60]} />
              <Tooltip cursor={{ strokeDasharray: "3 3" }} content={<TooltipPunto />} />
              {Object.entries(porColeccion).map(([coleccion, puntos]) => (
                <Scatter
                  key={coleccion}
                  name={etiquetaColeccion(coleccion)}
                  data={puntos}
                  fill={colorColeccion(coleccion)}
                />
              ))}
            </ScatterChart>
          </ChartContainer>
        </section>
      )}
    </div>
  );
}

function agruparPorColeccion(puntos: PuntoVector[]): Record<string, PuntoVector[]> {
  const grupos: Record<string, PuntoVector[]> = {};
  for (const punto of puntos) {
    (grupos[punto.coleccion] ??= []).push(punto);
  }
  return grupos;
}

function TooltipPunto({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload?: PuntoVector }>;
}) {
  const punto = payload?.[0]?.payload;
  if (!active || !punto) return null;
  return (
    <div className="max-w-xs rounded-lg border bg-background px-3 py-2 text-xs shadow-md">
      <p className="font-medium text-foreground">{punto.label}</p>
      <p className="text-muted-foreground">{etiquetaColeccion(punto.coleccion)}</p>
      <p className="text-muted-foreground">ID: {punto.id}</p>
    </div>
  );
}
