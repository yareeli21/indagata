import { useEffect, useMemo, useState } from "react";
import { Link } from "@tanstack/react-router";
import { BarChart3, FolderOpen, MousePointerClick, Search, SearchX } from "lucide-react";
import { Pagina } from "@/components/layout/Pagina";
import { EstadoVacio } from "@/components/shared/EstadoVacio";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getCatalogoKpis, getDatosGrafica, getKpis } from "@/api/kpis";
import { getInstrumentos } from "@/api/instrumentos";
import { useAuth } from "@/features/auth/AuthContext";
import { useResearch } from "@/features/research/ResearchContext";
import { fuentesDeInvestigacion } from "@/features/research/fuentes";
import { PageHeader } from "@/components/layout/PageHeader";
import type { DatosGrafica, Kpi, KpiCatalogo } from "@/types";
import { TarjetaKpi } from "./TarjetaKpi";
import { TarjetaMetrica } from "./TarjetaMetrica";
import { DetalleKpi } from "./DetalleKpi";
import { GraficasKpi } from "./GraficasKpi";

export function KpisPage() {
  const { usuario } = useAuth();
  const { activa } = useResearch();
  const miId = usuario?.investigadorId ?? "";

  // Métricas resumidas (tira superior)
  const [metricas, setMetricas] = useState<Kpi[]>([]);

  // Catálogo
  const [catalogo, setCatalogo] = useState<KpiCatalogo[]>([]);
  const [busqueda, setBusqueda] = useState("");
  const [kpiDetalle, setKpiDetalle] = useState<KpiCatalogo | null>(null);

  // Dashboard
  const [kpiDashboard, setKpiDashboard] = useState<KpiCatalogo | null>(null);
  const [fuenteIds, setFuenteIds] = useState<string[]>([]);
  const [datosDashboard, setDatosDashboard] = useState<DatosGrafica | null>(null);
  const [cargandoGraficas, setCargandoGraficas] = useState(false);

  // Cargar catálogo y métricas resumidas
  useEffect(() => {
    getCatalogoKpis().then(setCatalogo);
    getKpis().then((k) => setMetricas(k.slice(0, 4)));
  }, []);

  // Cargar las fuentes de la investigación activa (los instrumentos elegidos al armarla)
  useEffect(() => {
    if (!activa) {
      setFuenteIds([]);
      return;
    }
    getInstrumentos()
      .then((todos) =>
        setFuenteIds(fuentesDeInvestigacion(todos, activa.id, miId).map((i) => i.id)),
      )
      .catch(() => setFuenteIds([]));
  }, [activa, miId]);

  // Cargar datos del dashboard cuando cambia el KPI o las fuentes
  useEffect(() => {
    if (!kpiDashboard || fuenteIds.length === 0) {
      setDatosDashboard(null);
      return;
    }
    let vigente = true;
    setCargandoGraficas(true);
    getDatosGrafica(kpiDashboard.id, fuenteIds)
      .then((d) => {
        if (vigente) setDatosDashboard(d);
      })
      .catch(() => {
        if (vigente) setDatosDashboard(null);
      })
      .finally(() => {
        if (vigente) setCargandoGraficas(false);
      });
    return () => {
      vigente = false;
    };
  }, [kpiDashboard, fuenteIds]);

  const catalogoFiltrado = useMemo(() => {
    const q = busqueda.trim().toLowerCase();
    if (!q) return catalogo;
    return catalogo.filter(
      (k) =>
        k.nombre.toLowerCase().includes(q) ||
        k.descripcionCorta.toLowerCase().includes(q) ||
        k.etiquetas.some((e) => e.toLowerCase().includes(q)),
    );
  }, [catalogo, busqueda]);

  function abrirDashboard(kpi: KpiCatalogo) {
    setKpiDashboard((prev) => (prev?.id === kpi.id ? null : kpi));
  }

  return (
    <Pagina>
      <PageHeader
        icono={BarChart3}
        etiqueta="Indicadores educativos"
        titulo="KPIs"
        descripcion="Indicadores clave del repositorio de investigación educativa universitaria."
        acciones={
          <div className="relative w-full sm:w-80">
            <Search className="absolute left-4 top-1/2 size-5 -translate-y-1/2 text-muted-foreground" />
            <Input
              className="pl-11"
              placeholder="Buscar KPI…"
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              maxLength={80}
            />
          </div>
        }
      />

      {/* Tira de métricas resumidas */}
      {metricas.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {metricas.map((m) => (
            <TarjetaMetrica key={m.id} kpi={m} />
          ))}
        </div>
      )}

      {/* ── Sección 1: Catálogo ── */}
      <section className="space-y-5">
        {catalogoFiltrado.length === 0 ? (
          <EstadoVacio
            compacto
            icono={SearchX}
            titulo={busqueda.trim() ? "Sin coincidencias" : "Catálogo vacío"}
            descripcion={
              busqueda.trim()
                ? `No hay KPIs que coincidan con "${busqueda}".`
                : "Aún no hay KPIs en el catálogo."
            }
          />
        ) : (
          <div className="grid gap-4 [grid-template-columns:repeat(auto-fill,minmax(16rem,1fr))]">
            {catalogoFiltrado.map((kpi) => (
              <TarjetaKpi
                key={kpi.id}
                kpi={kpi}
                activo={kpiDashboard?.id === kpi.id}
                onClick={() => abrirDashboard(kpi)}
              />
            ))}
          </div>
        )}

        <p className="text-xs text-muted-foreground">
          Haz clic en una tarjeta para ver el dashboard · Haz clic en "Ver detalle" para la ficha
          completa.
        </p>
      </section>

      {/* Separador */}
      <div className="border-t" />

      {/* ── Sección 2: Dashboard ── */}
      <section className="space-y-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold">
              Dashboard de mi investigación
              {activa && (
                <span className="ml-2 text-base font-normal text-muted-foreground">
                  — {activa.nombre}
                </span>
              )}
            </h2>
            <p className="text-sm text-muted-foreground">
              Gráficas calculadas solo con las fuentes de tu investigación activa.
            </p>
          </div>
          {kpiDashboard && (
            <Button variant="ghost" size="sm" onClick={() => setKpiDetalle(kpiDashboard)}>
              Ver detalle del KPI
            </Button>
          )}
        </div>

        {/* Sin investigación activa */}
        {!activa ? (
          <EstadoVacio
            icono={FolderOpen}
            titulo="No tienes una investigación activa"
            descripcion="Los dashboards se calculan con los instrumentos de tu investigación activa. Arma una investigación para verlos."
            accion={
              <Button asChild variant="accent" size="lg">
                <Link to="/investigacion">
                  <FolderOpen />
                  Armar investigación
                </Link>
              </Button>
            }
          />
        ) : !kpiDashboard ? (
          /* Sin KPI seleccionado */
          <div>
            <EstadoVacio
              compacto
              icono={MousePointerClick}
              titulo="Elige un KPI"
              descripcion="Selecciona un KPI del catálogo para ver sus gráficas."
            />
          </div>
        ) : (
          /* Gráficas */
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold">{kpiDashboard.nombre}</span>
              <span className="text-xs text-muted-foreground">
                · {fuenteIds.length} fuente{fuenteIds.length !== 1 ? "s" : ""} en la investigación
              </span>
            </div>
            <GraficasKpi kpi={kpiDashboard} datos={datosDashboard} cargando={cargandoGraficas} />
          </div>
        )}
      </section>

      {/* Sheet de detalle */}
      <DetalleKpi kpi={kpiDetalle} onCerrar={() => setKpiDetalle(null)} />
    </Pagina>
  );
}
