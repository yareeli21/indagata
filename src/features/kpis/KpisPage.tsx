import { useEffect, useMemo, useState } from "react";
import { Link } from "@tanstack/react-router";
import { FolderOpen, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getCatalogoKpis, getDatosGrafica } from "@/api/kpis";
import { getInstrumentos } from "@/api/instrumentos";
import { useAuth } from "@/features/auth/AuthContext";
import { useResearch } from "@/features/research/ResearchContext";
import type { DatosGrafica, KpiCatalogo } from "@/types";
import { TarjetaKpi } from "./TarjetaKpi";
import { DetalleKpi } from "./DetalleKpi";
import { GraficasKpi } from "./GraficasKpi";

export function KpisPage() {
  const { usuario } = useAuth();
  const { activa } = useResearch();
  const miId = usuario?.investigadorId ?? "";

  // Catálogo
  const [catalogo, setCatalogo] = useState<KpiCatalogo[]>([]);
  const [busqueda, setBusqueda] = useState("");
  const [kpiDetalle, setKpiDetalle] = useState<KpiCatalogo | null>(null);

  // Dashboard
  const [kpiDashboard, setKpiDashboard] = useState<KpiCatalogo | null>(null);
  const [fuenteIds, setFuenteIds] = useState<string[]>([]);
  const [datosDashboard, setDatosDashboard] = useState<DatosGrafica | null>(null);
  const [cargandoGraficas, setCargandoGraficas] = useState(false);

  // Cargar catálogo
  useEffect(() => {
    getCatalogoKpis().then(setCatalogo);
  }, []);

  // Cargar fuentes de la investigación activa (propios + ajenos simulados)
  useEffect(() => {
    if (!activa) { setFuenteIds([]); return; }
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
      {/* ── Sección 1: Catálogo ── */}
      <section className="space-y-5">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold">KPIs</h1>
            <p className="text-muted-foreground">
              Indicadores clave del repositorio de investigación educativa.
            </p>
          </div>
          {/* Buscador */}
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
        </div>

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
          Haz clic en una tarjeta para ver el dashboard · Haz clic en "Ver detalle" para la ficha completa.
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
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setKpiDetalle(kpiDashboard)}
            >
              Ver detalle del KPI
            </Button>
          )}
        </div>

        {/* Sin investigación activa */}
        {!activa ? (
          <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed bg-card px-6 py-14 text-center">
            <span className="flex size-12 items-center justify-center rounded-full bg-primary/10 text-primary">
              <FolderOpen className="size-6" />
            </span>
            <p className="font-semibold">No tienes una investigación activa</p>
            <p className="max-w-sm text-sm text-muted-foreground">
              Los dashboards se calculan con los instrumentos de tu investigación activa.
              Arma una investigación para verlos.
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
          <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed bg-card px-6 py-14 text-center">
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
            <GraficasKpi
              kpi={kpiDashboard}
              datos={datosDashboard}
              cargando={cargandoGraficas}
            />
          </div>
        )}
      </section>

      {/* Sheet de detalle */}
      <DetalleKpi kpi={kpiDetalle} onCerrar={() => setKpiDetalle(null)} />
    </div>
  );
}
