import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "@tanstack/react-router";
import {
  AlertTriangle,
  BookOpenText,
  Compass,
  Cpu,
  Network,
  RotateCw,
  Shapes,
  Upload,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Sheet, SheetContent, SheetDescription, SheetTitle } from "@/components/ui/sheet";
import { PageHeader } from "@/components/layout/PageHeader";
import { Pagina } from "@/components/layout/Pagina";
import { EstadoVacio } from "@/components/shared/EstadoVacio";
import { Panel } from "@/components/shared/Panel";
import { buscarEnEspacio, getMapaEspacio, getVecinosEspacio } from "@/api/espacio";
import { getCatalogoKpis } from "@/api/kpis";
import type {
  BusquedaEspacio,
  KpiCatalogo,
  MapaEspacio,
  PuntoEspacio,
  TipoPuntoEspacio,
  VecinosEspacio,
} from "@/types";
import { BuscadorSemantico } from "./BuscadorSemantico";
import { ComoLeerMapa } from "./ComoLeerMapa";
import { LeyendaClusters } from "./LeyendaClusters";
import { LeyendaInteractiva } from "./LeyendaInteractiva";
import { MapaEmbeddings, type ConsultaMapa } from "./MapaEmbeddings";
import { PanelBusqueda } from "./PanelBusqueda";
import { PanelDetalle } from "./PanelDetalle";
import { RecorridoGuiado } from "./RecorridoGuiado";
import { EJEMPLOS_BUSQUEDA, PASOS_RECORRIDO } from "./recorrido";
import { SelectorVista } from "./SelectorVista";

type Estado = "cargando" | "listo" | "error";

/** Altura del mapa: protagonista, pero sin exceder la ventana. */
const ALTO_MAPA = "h-[clamp(26rem,72vh,56rem)]";
/** Vecinos por grupo que se piden al seleccionar un punto. */
const K_VECINOS = 6;
/** Marca en localStorage: el recorrido guiado ya se mostró una vez. */
const CLAVE_RECORRIDO = "indagata.espacio.recorrido";

function recorridoVisto(): boolean {
  try {
    return window.localStorage.getItem(CLAVE_RECORRIDO) === "visto";
  } catch {
    return true;
  }
}

function marcarRecorridoVisto() {
  try {
    window.localStorage.setItem(CLAVE_RECORRIDO, "visto");
  } catch {
    // Sin almacenamiento: se volverá a ofrecer en la próxima visita.
  }
}

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

/** true en pantallas anchas (≥ 1536 px), donde el detalle va en la barra lateral. */
function usePantallaAncha() {
  const [ancha, setAncha] = useState(false);
  useEffect(() => {
    const mql = window.matchMedia("(min-width: 1536px)");
    const actualizar = () => setAncha(mql.matches);
    actualizar();
    mql.addEventListener("change", actualizar);
    return () => mql.removeEventListener("change", actualizar);
  }, []);
  return ancha;
}

export function EspacioVectorialPage() {
  const [estado, setEstado] = useState<Estado>("cargando");
  const [mapa, setMapa] = useState<MapaEspacio | null>(null);
  const [mensajeError, setMensajeError] = useState("");
  const [cargandoVista, setCargandoVista] = useState(false);
  const [cargandoChunks, setCargandoChunks] = useState(false);
  const [visibles, setVisibles] = useState<ReadonlySet<TipoPuntoEspacio>>(
    () => new Set<TipoPuntoEspacio>(["kpi", "instrumento"]),
  );
  const [clustersOcultos, setClustersOcultos] = useState<ReadonlySet<number>>(() => new Set());
  const [seleccionId, setSeleccionId] = useState<string | null>(null);
  const [vecinos, setVecinos] = useState<VecinosEspacio | null>(null);
  const [cargandoVecinos, setCargandoVecinos] = useState(false);
  const [errorVecinos, setErrorVecinos] = useState<string | null>(null);
  const [kpisCatalogo, setKpisCatalogo] = useState<KpiCatalogo[]>([]);
  const [busqueda, setBusqueda] = useState<BusquedaEspacio | null>(null);
  const [buscando, setBuscando] = useState(false);
  const [mostrarZonas, setMostrarZonas] = useState(true);
  const [pasoRecorrido, setPasoRecorrido] = useState<number | null>(null);
  const pantallaAncha = usePantallaAncha();

  // Mapas ya descargados por variante (vista × chunks) y vecinos por punto.
  const mapasRef = useRef(new Map<string, MapaEspacio>());
  const vecinosRef = useRef(new Map<string, VecinosEspacio>());

  const traerMapa = useCallback(async (alinear: boolean, chunks: boolean) => {
    const clave = `${alinear}|${chunks}`;
    const guardado = mapasRef.current.get(clave);
    if (guardado) return guardado;
    const datos = await getMapaEspacio({ alinear, chunks });
    mapasRef.current.set(clave, datos);
    return datos;
  }, []);

  const cargar = useCallback(() => {
    let activo = true;
    setEstado("cargando");
    mapasRef.current.clear();
    traerMapa(false, false)
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
  }, [traerMapa]);

  useEffect(() => cargar(), [cargar]);

  // Primera visita: se ofrece el recorrido guiado en cuanto hay mapa.
  useEffect(() => {
    if (estado === "listo" && !recorridoVisto()) setPasoRecorrido(0);
  }, [estado]);

  const cerrarRecorrido = useCallback(() => {
    setPasoRecorrido(null);
    marcarRecorridoVisto();
  }, []);

  // Lleva el mapa a la vista (búsqueda o recorrido lanzados desde arriba).
  const mapaRef = useRef<HTMLDivElement>(null);
  const mostrarMapa = useCallback(() => {
    const el = mapaRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    if (r.top >= 0 && r.bottom <= window.innerHeight) return;
    const reducido = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    el.scrollIntoView({ behavior: reducido ? "auto" : "smooth", block: "start" });
  }, []);

  const buscar = useCallback(
    (texto: string) => {
      setBuscando(true);
      buscarEnEspacio(texto)
        .then((resultado) => {
          setSeleccionId(null);
          setBusqueda(resultado);
          mostrarMapa();
        })
        .catch((error: unknown) =>
          toast.error(error instanceof Error ? error.message : "No se pudo hacer la búsqueda."),
        )
        .finally(() => setBuscando(false));
    },
    [mostrarMapa],
  );

  // El catálogo de KPIs (definición, fórmula…) solo se pide al abrir un KPI.
  const catalogoPedido = useRef(false);
  useEffect(() => {
    if (catalogoPedido.current || !seleccionId?.startsWith("kpi:")) return;
    catalogoPedido.current = true;
    void getCatalogoKpis().then(setKpisCatalogo);
  }, [seleccionId]);

  const conChunks = Boolean(mapa?.puntos.some((p) => p.tipo === "chunk"));

  const cambiarVista = useCallback(
    (alinear: boolean) => {
      setCargandoVista(true);
      traerMapa(alinear, conChunks)
        .then(setMapa)
        .catch(() => toast.error("No se pudo cambiar la vista del mapa."))
        .finally(() => setCargandoVista(false));
    },
    [traerMapa, conChunks],
  );

  const alternar = useCallback(
    (tipo: TipoPuntoEspacio) => {
      // Los chunks se descargan la primera vez que se activan.
      if (tipo === "chunk" && !conChunks && mapa) {
        setCargandoChunks(true);
        traerMapa(mapa.alineado, true)
          .then((datos) => {
            setMapa(datos);
            setVisibles((prev) => new Set(prev).add("chunk"));
          })
          .catch(() => toast.error("No se pudieron cargar los chunks."))
          .finally(() => setCargandoChunks(false));
        return;
      }
      setVisibles((prev) => {
        const siguiente = new Set(prev);
        if (siguiente.has(tipo)) siguiente.delete(tipo);
        else siguiente.add(tipo);
        return siguiente;
      });
    },
    [conChunks, mapa, traerMapa],
  );

  const alternarCluster = useCallback((id: number) => {
    setClustersOcultos((prev) => {
      const siguiente = new Set(prev);
      if (siguiente.has(id)) siguiente.delete(id);
      else siguiente.add(id);
      return siguiente;
    });
  }, []);

  const puntosPorId = useMemo(() => new Map((mapa?.puntos ?? []).map((p) => [p.id, p])), [mapa]);
  const seleccion = seleccionId ? (puntosPorId.get(seleccionId) ?? null) : null;

  // Vecinos del punto seleccionado (coseno en el espacio original).
  useEffect(() => {
    if (!seleccion) {
      setVecinos(null);
      setErrorVecinos(null);
      return;
    }
    const guardados = vecinosRef.current.get(seleccion.id);
    if (guardados) {
      setVecinos(guardados);
      setErrorVecinos(null);
      return;
    }
    let activo = true;
    setCargandoVecinos(true);
    setErrorVecinos(null);
    setVecinos(null);
    getVecinosEspacio(seleccion.tipo, seleccion.ref, K_VECINOS)
      .then((datos) => {
        vecinosRef.current.set(seleccion.id, datos);
        if (activo) setVecinos(datos);
      })
      .catch((error: unknown) => {
        if (activo) {
          setErrorVecinos(
            error instanceof Error ? error.message : "No se pudieron calcular los vecinos.",
          );
        }
      })
      .finally(() => activo && setCargandoVecinos(false));
    return () => {
      activo = false;
    };
  }, [seleccion]);

  // Vecinos que se unen con líneas: los de la búsqueda o los del punto seleccionado.
  const similitudes = useMemo(() => {
    const m = new Map<string, number>();
    const fuente = busqueda ?? vecinos;
    if (fuente) {
      for (const v of [...fuente.kpis, ...fuente.instrumentos, ...fuente.chunks]) {
        m.set(v.id, v.similitud);
      }
    }
    return m;
  }, [busqueda, vecinos]);

  // La frase buscada, en las coordenadas de la vista actual.
  const consulta = useMemo<ConsultaMapa | null>(() => {
    if (!busqueda || !mapa) return null;
    const pos = mapa.alineado ? busqueda.posicionAlineada : busqueda.posicion;
    return { texto: busqueda.texto, x: pos.x, y: pos.y };
  }, [busqueda, mapa]);

  // Elegir un punto (en el mapa o en una lista) sustituye a la búsqueda.
  const seleccionar = useCallback((punto: PuntoEspacio | null) => {
    setSeleccionId(punto?.id ?? null);
    setBusqueda(null);
  }, []);
  const seleccionarId = useCallback((id: string) => {
    setSeleccionId(id);
    setBusqueda(null);
  }, []);
  const cerrar = useCallback(() => {
    setSeleccionId(null);
    setBusqueda(null);
  }, []);
  const enMapa = useCallback((id: string) => puntosPorId.has(id), [puntosPorId]);

  // La hoja de detalle (pantallas medianas) tapa 28rem por la derecha desde sm.
  const reservaHoja =
    !pantallaAncha &&
    (seleccion || busqueda) &&
    typeof window !== "undefined" &&
    window.innerWidth >= 640
      ? 448
      : 0;
  const brecha = useMemo(() => hayBrecha(mapa?.puntos ?? []), [mapa]);
  const total = mapa ? mapa.conteos.kpis + mapa.conteos.instrumentos : 0;
  const kpiSeleccionado =
    seleccion?.tipo === "kpi" ? kpisCatalogo.find((k) => k.id === seleccion.ref) : undefined;

  const detalle = seleccion && mapa && (
    <PanelDetalle
      punto={seleccion}
      vecinos={vecinos}
      cargandoVecinos={cargandoVecinos}
      errorVecinos={errorVecinos}
      clusters={mapa.clusters}
      kpiCatalogo={kpiSeleccionado}
      enMapa={enMapa}
      onSeleccionar={seleccionarId}
      onCerrar={cerrar}
    />
  );
  const lateral =
    detalle ||
    (busqueda && (
      <PanelBusqueda
        busqueda={busqueda}
        enMapa={enMapa}
        onSeleccionar={seleccionarId}
        onCerrar={cerrar}
      />
    ));
  const paso = pasoRecorrido !== null ? PASOS_RECORRIDO[pasoRecorrido] : undefined;

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
            <button
              type="button"
              onClick={() => {
                setPasoRecorrido(0);
                mostrarMapa();
              }}
              className="inline-flex items-center gap-2 rounded-full border border-primary/25 bg-primary-soft px-3 py-1.5 text-xs font-bold text-primary shadow-card transition-colors hover:bg-primary hover:text-primary-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <Compass className="size-4" aria-hidden /> Recorrido guiado
            </button>
          </div>
        )}
      </PageHeader>

      {estado === "cargando" && (
        <div
          className="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_26rem]"
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
        <div className="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_26rem]">
          <div className="min-w-0 space-y-4">
            <BuscadorSemantico
              buscando={buscando}
              activa={busqueda?.texto ?? null}
              onBuscar={buscar}
              onQuitar={cerrar}
            />
            <div ref={mapaRef} className="scroll-mt-24">
              <Panel sinRelleno className={ALTO_MAPA} claseCuerpo="h-full">
                <MapaEmbeddings
                  puntos={mapa.puntos}
                  visibles={visibles}
                  clustersOcultos={clustersOcultos}
                  varianza={mapa.pca.varianza}
                  seleccionId={seleccionId}
                  vecinos={similitudes}
                  onSeleccionar={seleccionar}
                  reservaDerecha={reservaHoja}
                  consulta={consulta}
                  clusters={mapa.clusters}
                  mostrarZonas={mostrarZonas}
                  resaltarTipo={paso?.resaltar ?? null}
                  controles={
                    <SelectorVista
                      alineado={mapa.alineado}
                      cargando={cargandoVista}
                      onCambiar={cambiarVista}
                    />
                  }
                >
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
                  {pasoRecorrido !== null && (
                    <RecorridoGuiado
                      paso={pasoRecorrido}
                      onCambiar={setPasoRecorrido}
                      onCerrar={cerrarRecorrido}
                      onProbar={() => {
                        cerrarRecorrido();
                        buscar(EJEMPLOS_BUSQUEDA[0] ?? "Abandono escolar");
                      }}
                      className="absolute bottom-4 left-4 sm:bottom-auto sm:top-20"
                    />
                  )}
                </MapaEmbeddings>
              </Panel>
            </div>
          </div>

          <aside className="grid content-start gap-6 md:grid-cols-2 2xl:grid-cols-1">
            {pantallaAncha && lateral && (
              <Panel
                className="max-h-[clamp(26rem,72vh,56rem)] md:col-span-2 2xl:col-span-1"
                claseCuerpo="overflow-y-auto"
              >
                {lateral}
              </Panel>
            )}
            <Panel titulo="Qué se muestra" descripcion="Toca para mostrar u ocultar.">
              <LeyendaInteractiva
                visibles={visibles}
                onAlternar={alternar}
                elementos={[
                  {
                    tipo: "kpi",
                    nombre: "KPIs educativos",
                    descripcion: "Definición de cada indicador; su color es su grupo temático.",
                    conteo: mapa.conteos.kpis,
                  },
                  {
                    tipo: "instrumento",
                    nombre: "Instrumentos",
                    descripcion: "Metadatos y preguntas de cada instrumento.",
                    conteo: mapa.conteos.instrumentos,
                  },
                  {
                    tipo: "chunk",
                    nombre: "Chunks del RAG",
                    descripcion: "Fragmentos que el chat recupera como fuentes.",
                    conteo: conChunks ? mapa.conteos.chunks : null,
                    insignia: mapa.fuenteChunks.provisional ? "provisionales" : undefined,
                    cargando: cargandoChunks,
                  },
                ]}
              />
            </Panel>
            {mapa.clusters.length > 0 && (
              <Panel
                titulo="Grupos temáticos"
                icono={Shapes}
                descripcion="KPIs agrupados por significado. Toca para ocultar un grupo."
                acciones={
                  <label className="flex items-center gap-2 text-xs font-bold text-muted-foreground">
                    Zonas
                    <Switch
                      checked={mostrarZonas}
                      onCheckedChange={setMostrarZonas}
                      aria-label="Mostrar las zonas de cada grupo en el mapa"
                    />
                  </label>
                }
              >
                <LeyendaClusters
                  clusters={mapa.clusters}
                  ocultos={clustersOcultos}
                  onAlternar={alternarCluster}
                />
              </Panel>
            )}
            <Panel titulo="Cómo leer este mapa" icono={BookOpenText}>
              <ComoLeerMapa
                varianzaTotal={mapa.pca.varianzaTotal}
                varianzaBaja={mapa.pca.varianzaBaja}
                brecha={brecha}
                alineado={mapa.alineado}
              />
            </Panel>
          </aside>
        </div>
      )}

      {/* En pantallas angostas el detalle se abre en una hoja lateral. No es modal:
          el mapa sigue visible (con sus líneas) y se puede elegir otro punto. */}
      <Sheet
        modal={false}
        open={!pantallaAncha && Boolean(lateral)}
        onOpenChange={(abierta) => !abierta && cerrar()}
      >
        <SheetContent
          side="right"
          onInteractOutside={(e) => e.preventDefault()}
          onOpenAutoFocus={(e) => e.preventDefault()}
          className="w-full overflow-y-auto border-l border-border p-6 shadow-elevated sm:max-w-md [&>button:first-of-type]:hidden"
        >
          <SheetTitle className="sr-only">
            {seleccion?.etiqueta ?? (busqueda ? `Búsqueda: ${busqueda.texto}` : "Detalle")}
          </SheetTitle>
          <SheetDescription className="sr-only">
            Ficha del punto seleccionado y sus vecinos más parecidos.
          </SheetDescription>
          {lateral}
        </SheetContent>
      </Sheet>
    </Pagina>
  );
}
