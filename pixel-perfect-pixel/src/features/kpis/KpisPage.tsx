import { useEffect, useMemo, useState } from "react";
import { Link } from "@tanstack/react-router";
import { FolderOpen, Minus, Search, TrendingDown, TrendingUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getCatalogoKpis, getDatosGrafica, getKpis } from "@/api/kpis";
import { getInstrumentos } from "@/api/instrumentos";
import { useAuth } from "@/features/auth/AuthContext";
import { useResearch } from "@/features/research/ResearchContext";
import { cn } from "@/lib/utils";
import { PageHeader } from "@/components/layout/PageHeader";
import type { DatosGrafica, Kpi, KpiCatalogo } from "@/types";
import { TarjetaKpi } from "./TarjetaKpi";
import { DetalleKpi } from "./DetalleKpi";
import { GraficasKpi } from "./GraficasKpi";

function TarjetaMetrica({ kpi }: { kpi: Kpi }) {
  const sube = kpi.variacion > 0;
  const baja = kpi.variacion < 0;
  const Icono = sube ? TrendingUp : baja ? TrendingDown : Minus;
  return (
    <div className="rounded-2xl border border-border bg-card p-4 shadow-soft">
      <p className="text-xs font-medium text-muted-foreground">{kpi.etiqueta}</p>
      <div className="mt-1 flex items-end justify-between gap-2">
        <p className="font-display text-2xl font-semibold text-foreground">{kpi.valor}</p>
        <span
          className={cn(
            "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
            sube && "bg-primary/10 text-primary",
            baja && "bg-destructive/10 text-destructive",
            !sube && !baja && "bg-muted text-muted-foreground",
          )}
        >
          <Icono className="size-3.5" aria-hidden />
          <span aria-hidden>
            {sube ? "+" : ""}
            {kpi.variacion}%
          </span>
          <span className="sr-only">
            {sube
              ? `aumentó ${kpi.variacion}%`
              : baja
                ? `disminuyó ${Math.abs(kpi.variacion)}%`
                : "sin cambio"}
          </span>
        </span>
      </div>
      <p className="mt-1 text-xs text-muted-foreground">{kpi.detalle}</p>
    </div>
  );
}

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

  // Cargar fuentes de la investigación activa (propios + ajenos simulados)
  useEffect(() => {
    if (!activa) {
      setFuenteIds([]);
      return;
    }
    getInstrumentos().then((todos) => {
      const propios = todos.filter((i) => i.autorId === miId).slice(0, 3);
      const ajenos = todos.filter((i) => i.autorId !== miId).slice(0, 2);
      setFuenteIds([...propios, ...ajenos].map((i) => i.id));
    });
  }, [activa, miId]);

  // Cargar datos del dashboard cuando cambia el KPI o las fuentes
  useEffect(() => {
    if (!kpiDashboard || fuenteIds.length === 0) {
      setDatosDashboard(null);
      return;
    }
    setCargandoGraficas(true);
    getDatosGrafica(kpiDashboard.id, fuenteIds).then((d) => {
      setDatosDashboard(d);
      setCargandoGraficas(false);
    });
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
    <div className="space-y-10 p-6 md:p-8">
      <PageHeader
        titulo="KPIs"
        descripcion="Indicadores clave del repositorio de investigación educativa universitaria."
        acciones={
          <div className="relative w-full max-w-xs">
            <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              className="pl-9"
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
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {metricas.map((m) => (
            <TarjetaMetrica key={m.id} kpi={m} />
          ))}
        </div>
      )}

      {/* ── Sección 1: Catálogo ── */}
      <section className="space-y-5">
        {catalogoFiltrado.length === 0 ? (
          <p className="py-10 text-center text-sm text-muted-foreground">
            No hay KPIs que coincidan con "{busqueda}".
          </p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
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
          <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-border bg-card px-6 py-14 text-center shadow-card">
            <span className="flex size-12 items-center justify-center rounded-2xl bg-primary-soft text-primary">
              <FolderOpen className="size-6" />
            </span>
            <p className="font-display font-semibold">No tienes una investigación activa</p>
            <p className="max-w-sm text-sm text-muted-foreground">
              Los dashboards se calculan con los instrumentos de tu investigación activa. Arma una
              investigación para verlos.
            </p>
            <Button asChild>
              <Link to="/investigacion">
                <FolderOpen />
                Armar investigación
              </Link>
            </Button>
          </div>
        ) : !kpiDashboard ? (
          /* Sin KPI seleccionado */
          <div className="flex flex-col items-center gap-2 rounded-2xl border border-dashed border-border bg-card px-6 py-14 text-center shadow-card">
            <p className="text-sm text-muted-foreground">
              Selecciona un KPI del catálogo para ver sus gráficas.
            </p>
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
    </div>
  );
}
