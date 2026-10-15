import { useEffect, useMemo, useState } from "react";
import {
  BadgeCheck,
  BarChart3,
  FolderOpen,
  Library,
  MessageSquare,
  Network,
  Upload,
  UserPlus,
} from "lucide-react";
import { toast } from "sonner";
import { getInstrumentos } from "@/api/instrumentos";
import { getCatalogoKpis, getKpis } from "@/api/kpis";
import { Aparecer, AparecerItem } from "@/components/efectos/Aparecer";
import { Pagina } from "@/components/layout/Pagina";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/features/auth/AuthContext";
import { useResearch } from "@/features/research/ResearchContext";
import { fuentesDeInvestigacion } from "@/features/research/fuentes";
import { TarjetaMetrica } from "@/features/kpis/TarjetaMetrica";
import { TIPOS_INSTRUMENTO, type Instrumento, type Kpi, type KpiCatalogo } from "@/types";
import { HeroInicio } from "./HeroInicio";
import { Gateway } from "./Gateway";
import { InstrumentosRecientes } from "./InstrumentosRecientes";
import { InvestigacionActiva } from "./InvestigacionActiva";
import { VisualBarrasKpi } from "./visuales/VisualBarrasKpi";
import { VisualChat } from "./visuales/VisualChat";
import { VisualConstelacion } from "./visuales/VisualConstelacion";
import { VisualMarcaAgua } from "./visuales/VisualMarcaAgua";

const ICONOS_METRICA = [Library, BadgeCheck, BarChart3, MessageSquare];

function plural(n: number, singular: string, pluralTexto: string) {
  return `${n} ${n === 1 ? singular : pluralTexto}`;
}

export function InicioPage() {
  const { usuario } = useAuth();
  const { activa } = useResearch();
  const miId = usuario?.investigadorId ?? "";
  const esAdmin = usuario?.rol === "Administrador";

  const [instrumentos, setInstrumentos] = useState<Instrumento[] | null>(null);
  /** `null` mientras carga. */
  const [metricas, setMetricas] = useState<Kpi[] | null>(null);
  const [catalogo, setCatalogo] = useState<KpiCatalogo[]>([]);

  useEffect(() => {
    let activo = true;
    getInstrumentos()
      .then((i) => activo && setInstrumentos(i))
      .catch((error: unknown) => {
        if (!activo) return;
        setInstrumentos([]);
        toast.error(
          error instanceof Error ? error.message : "No se pudieron cargar los instrumentos.",
        );
      });
    getKpis().then((k) => activo && setMetricas(k.slice(0, 4)));
    getCatalogoKpis().then((c) => activo && setCatalogo(c));
    return () => {
      activo = false;
    };
  }, []);

  const lista = useMemo(() => instrumentos ?? [], [instrumentos]);
  const mios = useMemo(() => lista.filter((i) => i.autorId === miId), [lista, miId]);
  const conteoTipos = useMemo(
    () =>
      TIPOS_INSTRUMENTO.map((tipo) => ({
        tipo,
        total: lista.filter((i) => i.tipo === tipo).length,
      })),
    [lista],
  );
  const recientes = useMemo(
    () => [...lista].sort((a, b) => b.fecha.localeCompare(a.fecha)).slice(0, 4),
    [lista],
  );
  // KPIs más medidos por los instrumentos del acervo (para la mini-gráfica).
  const barrasKpi = useMemo(() => {
    const cuenta = new Map<string, number>();
    for (const i of lista) for (const k of i.kpis) cuenta.set(k, (cuenta.get(k) ?? 0) + 1);
    return [...cuenta.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 7)
      .map(([nombre, total]) => ({ nombre, total }));
  }, [lista]);
  const fuentes = useMemo(
    () => (activa ? fuentesDeInvestigacion(lista, activa.id, miId).length : 0),
    [activa, lista, miId],
  );

  // Si el backend no devuelve métricas, se muestran cifras calculadas del acervo.
  const metricasRespaldo: Kpi[] = useMemo(
    () => [
      {
        id: "total",
        etiqueta: "Instrumentos en el acervo",
        valor: String(lista.length),
        variacion: 0,
        detalle: "Encuestas, entrevistas y pruebas.",
      },
      {
        id: "estandarizados",
        etiqueta: "Estandarizados",
        valor: String(lista.filter((i) => i.estado === "Estandarizado").length),
        variacion: 0,
        detalle: "Listos para el chat y los dashboards.",
      },
      {
        id: "mios",
        etiqueta: "Mis instrumentos",
        valor: String(mios.length),
        variacion: 0,
        detalle: "Los que tú has aportado.",
      },
      {
        id: "kpis",
        etiqueta: "KPIs en el catálogo",
        valor: String(catalogo.length),
        variacion: 0,
        detalle: "Indicadores educativos disponibles.",
      },
    ],
    [lista, mios, catalogo],
  );
  const usarRespaldo = metricas !== null && metricas.length === 0;
  const tarjetas = usarRespaldo ? metricasRespaldo : (metricas ?? []);
  // La tira se monta una sola vez con sus datos finales: si las tarjetas cambian
  // después de la animación de entrada, las nuevas quedarían ocultas.
  const metricasListas = metricas !== null && (!usarRespaldo || instrumentos !== null);

  const primerNombre = usuario?.nombre.trim().split(/\s+/)[0] ?? "";

  return (
    <Pagina>
      <HeroInicio
        nombre={primerNombre}
        totalInstrumentos={instrumentos === null ? null : lista.length}
        conteoTipos={conteoTipos}
        totalKpis={catalogo.length}
      />

      {/* Métricas del acervo */}
      <section aria-labelledby="titulo-metricas" className="space-y-4">
        <h2 id="titulo-metricas" className="sr-only">
          Métricas del acervo
        </h2>
        {metricasListas ? (
          <Aparecer className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {tarjetas.map((m, i) => (
              <AparecerItem key={m.id}>
                <TarjetaMetrica
                  kpi={m}
                  icono={ICONOS_METRICA[i % ICONOS_METRICA.length]}
                  mostrarVariacion={!usarRespaldo}
                />
              </AparecerItem>
            ))}
          </Aparecer>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-busy="true">
            {ICONOS_METRICA.map((_, i) => (
              <Skeleton key={i} className="h-40 rounded-2xl" />
            ))}
          </div>
        )}
      </section>

      {/* Gateways a los módulos */}
      <section aria-labelledby="titulo-modulos" className="space-y-5">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2
              id="titulo-modulos"
              className="font-display text-2xl font-bold tracking-tight md:text-3xl"
            >
              ¿Qué quieres hacer hoy?
            </h2>
            <p className="mt-1 text-base text-muted-foreground">
              Del instrumento a la evidencia: elige por dónde empezar.
            </p>
          </div>
        </div>

        <Aparecer className="grid auto-rows-[minmax(14rem,auto)] grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:gap-5 2xl:grid-cols-4">
          <AparecerItem className="sm:col-span-2 lg:row-span-2">
            <Gateway
              destacado
              to="/kpis"
              titulo="KPIs educativos"
              descripcion="Descubre qué indicadores mide cada instrumento y explora dashboards por nivel, año y tipo con la evidencia de cada pregunta."
              cta="Explorar indicadores"
              icono={BarChart3}
              dato={plural(catalogo.length, "KPI", "KPIs")}
              visual={<VisualBarrasKpi barras={barrasKpi} />}
              className="[&>a]:min-h-[26rem]"
            />
          </AparecerItem>
          <AparecerItem className="sm:col-span-2 lg:col-span-1 2xl:col-span-2">
            <Gateway
              to="/chat"
              titulo="Chat con el acervo"
              descripcion="Pregunta en lenguaje natural y recibe respuestas fundamentadas en instrumentos reales, con sus fuentes."
              cta="Iniciar una conversación"
              icono={MessageSquare}
              visual={<VisualChat />}
            />
          </AparecerItem>
          <AparecerItem>
            <Gateway
              to="/instrumentos"
              titulo="Mis instrumentos"
              descripcion="Consulta, filtra y descarga encuestas, entrevistas y pruebas."
              cta="Ver instrumentos"
              icono={Library}
              dato={instrumentos === null ? undefined : String(mios.length)}
              visual={<VisualMarcaAgua icono={Library} />}
            />
          </AparecerItem>
          <AparecerItem>
            <Gateway
              to="/instrumentos/nuevo"
              titulo="Subir instrumento"
              descripcion="Estandarízalo con Dublin Core y vincúlalo a KPIs en minutos."
              cta="Comenzar carga"
              icono={Upload}
              visual={<VisualMarcaAgua icono={Upload} />}
            />
          </AparecerItem>
          <AparecerItem className="sm:col-span-2 lg:col-span-1 2xl:col-span-2">
            <Gateway
              to="/investigacion"
              titulo="Armar investigación"
              descripcion="Reúne tus instrumentos y los de otros autores relacionados en un proyecto con fuentes claras."
              cta="Armar mi investigación"
              icono={FolderOpen}
              visual={<VisualMarcaAgua icono={FolderOpen} />}
            />
          </AparecerItem>
          <AparecerItem
            className={esAdmin ? undefined : "sm:col-span-2 lg:col-span-1 2xl:col-span-2"}
          >
            <Gateway
              to="/espacio"
              titulo="Espacio vectorial"
              descripcion="Visualiza cómo se agrupan instrumentos y KPIs por significado."
              cta="Explorar el mapa"
              icono={Network}
              visual={<VisualConstelacion />}
            />
          </AparecerItem>
          {esAdmin && (
            <AparecerItem className="lg:col-span-3 2xl:col-span-1">
              <Gateway
                to="/usuarios"
                titulo="Gestión de usuarios"
                descripcion="Da de alta investigadores y administradores."
                cta="Administrar"
                icono={UserPlus}
                visual={<VisualMarcaAgua icono={UserPlus} />}
              />
            </AparecerItem>
          )}
        </Aparecer>
      </section>

      {/* Actividad */}
      <div className="grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)] xl:gap-5">
        <InstrumentosRecientes instrumentos={instrumentos === null ? null : recientes} />
        <InvestigacionActiva activa={activa} fuentes={fuentes} />
      </div>
    </Pagina>
  );
}
