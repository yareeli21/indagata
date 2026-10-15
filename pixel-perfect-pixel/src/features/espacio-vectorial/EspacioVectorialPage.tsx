import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "@tanstack/react-router";
import { AlertTriangle, BookOpenText, Cpu, Network, RotateCw, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/layout/PageHeader";
import { Pagina } from "@/components/layout/Pagina";
import { EstadoVacio } from "@/components/shared/EstadoVacio";
import { Panel } from "@/components/shared/Panel";
import { getMapaEspacio } from "@/api/espacio";
import type { MapaEspacio, PuntoEspacio, TipoPuntoEspacio } from "@/types";
import { ComoLeerMapa } from "./ComoLeerMapa";
import { LeyendaInteractiva } from "./LeyendaInteractiva";
import { MapaEmbeddings } from "./MapaEmbeddings";

type Estado = "cargando" | "listo" | "error";

/** Altura del mapa: protagonista, pero sin exceder la ventana. */
const ALTO_MAPA = "h-[clamp(26rem,72vh,56rem)]";

/** ¿Los rangos de PC1 de KPIs e instrumentos no se traslapan? */
function hayBrecha(puntos: PuntoEspacio[]): boolean {
  const rango = (tipo: TipoPuntoEspacio): [number, number] | null => {
    const xs = puntos.filter((p) => p.tipo === tipo).map((p) => p.x);
    return xs.length ? [Math.min(...xs), Math.max(...xs)] : null;
  };
  const k = rango("kpi");
  const i = rango("instrumento");
  return Boolean(k && i && (k[1] < i[0] || i[1] < k[0]));
}

export function EspacioVectorialPage() {
  const [estado, setEstado] = useState<Estado>("cargando");
  const [mapa, setMapa] = useState<MapaEspacio | null>(null);
  const [mensajeError, setMensajeError] = useState("");
  const [visibles, setVisibles] = useState<ReadonlySet<TipoPuntoEspacio>>(
    () => new Set<TipoPuntoEspacio>(["kpi", "instrumento"]),
  );

  const cargar = useCallback(() => {
    let activo = true;
    setEstado("cargando");
    getMapaEspacio()
      .then((datos) => {
        if (!activo) return;
        setMapa(datos);
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

  useEffect(() => cargar(), [cargar]);

  const alternar = useCallback((tipo: TipoPuntoEspacio) => {
    setVisibles((prev) => {
      const siguiente = new Set(prev);
      if (siguiente.has(tipo)) siguiente.delete(tipo);
      else siguiente.add(tipo);
      return siguiente;
    });
  }, []);

  const brecha = useMemo(() => hayBrecha(mapa?.puntos ?? []), [mapa]);
  const total = mapa ? mapa.conteos.kpis + mapa.conteos.instrumentos : 0;

  return (
    <Pagina>
      <PageHeader
        icono={Network}
        etiqueta="Embeddings · base del RAG"
        titulo="Espacio vectorial"
        descripcion="Cómo se relacionan los instrumentos con los KPIs educativos según su significado: cada punto es un texto convertido en vector y proyectado en dos dimensiones."
      >
        {mapa && (
          <div className="flex flex-wrap gap-2">
            <span className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1.5 text-xs font-semibold text-muted-foreground shadow-card">
              <Cpu className="size-4 text-primary" aria-hidden />
              {mapa.modelo.split("/").pop()} · {mapa.dimension} dimensiones
            </span>
            <span className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1.5 text-xs font-semibold text-muted-foreground shadow-card">
              {mapa.conteos.kpis} KPIs · {mapa.conteos.instrumentos} instrumentos
            </span>
          </div>
        )}
      </PageHeader>

      {estado === "cargando" && (
        <div
          className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_24rem]"
          role="status"
          aria-live="polite"
        >
          <span className="sr-only">Cargando el espacio vectorial…</span>
          <Skeleton className={`${ALTO_MAPA} w-full rounded-3xl`} />
          <div className="space-y-4">
            <Skeleton className="h-40 rounded-3xl" />
            <Skeleton className="h-72 rounded-3xl" />
          </div>
        </div>
      )}

      {estado === "error" && (
        <EstadoVacio
          icono={AlertTriangle}
          titulo="No se pudo cargar el espacio vectorial"
          descripcion={mensajeError}
          accion={
            <Button variant="outline" size="lg" onClick={cargar}>
              <RotateCw /> Reintentar
            </Button>
          }
        />
      )}

      {estado === "listo" && mapa && total === 0 && (
        <EstadoVacio
          icono={Network}
          titulo="Aún no hay vectores que mostrar"
          descripcion="Cuando el catálogo de KPIs esté indexado y subas instrumentos, aparecerán aquí agrupados por su significado."
          accion={
            <Button asChild variant="accent" size="lg">
              <Link to="/instrumentos/nuevo">
                <Upload /> Subir instrumento
              </Link>
            </Button>
          }
        />
      )}

      {estado === "listo" && mapa && total > 0 && (
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_24rem]">
          <Panel sinRelleno className={ALTO_MAPA} claseCuerpo="h-full">
            <MapaEmbeddings puntos={mapa.puntos} visibles={visibles} varianza={mapa.pca.varianza}>
              {mapa.conteos.instrumentos === 0 && (
                <div className="absolute inset-x-4 bottom-14 mx-auto max-w-xl rounded-3xl border border-border bg-card/95 p-6 text-center shadow-elevated backdrop-blur-sm sm:inset-x-0">
                  <p className="font-display text-xl font-bold">
                    Todavía no hay instrumentos en el mapa
                  </p>
                  <p className="mt-2 text-sm text-muted-foreground">
                    Sube uno para ver junto a qué KPIs queda según su significado.
                  </p>
                  <Button asChild variant="accent" size="lg" className="mt-4">
                    <Link to="/instrumentos/nuevo">
                      <Upload /> Subir instrumento
                    </Link>
                  </Button>
                </div>
              )}
            </MapaEmbeddings>
          </Panel>

          <aside className="grid content-start gap-6 md:grid-cols-2 xl:grid-cols-1">
            <Panel titulo="Qué se muestra" descripcion="Toca para mostrar u ocultar.">
              <LeyendaInteractiva
                visibles={visibles}
                onAlternar={alternar}
                elementos={[
                  {
                    tipo: "kpi",
                    nombre: "KPIs educativos",
                    descripcion: "Definición de cada indicador del catálogo.",
                    conteo: mapa.conteos.kpis,
                  },
                  {
                    tipo: "instrumento",
                    nombre: "Instrumentos",
                    descripcion: "Metadatos y preguntas de cada instrumento.",
                    conteo: mapa.conteos.instrumentos,
                  },
                ]}
              />
            </Panel>
            <Panel titulo="Cómo leer este mapa" icono={BookOpenText}>
              <ComoLeerMapa
                varianzaTotal={mapa.pca.varianzaTotal}
                varianzaBaja={mapa.pca.varianzaBaja}
                brecha={brecha}
              />
            </Panel>
          </aside>
        </div>
      )}
    </Pagina>
  );
}
