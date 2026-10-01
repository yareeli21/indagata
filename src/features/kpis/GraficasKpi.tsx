import { Database } from "lucide-react";
import {
  Bar, BarChart, CartesianGrid, Cell, Line, LineChart,
  Pie, PieChart, Tooltip, XAxis, YAxis,
} from "recharts";
import { ChartContainer, type ChartConfig } from "@/components/ui/chart";
import type { DatosGrafica, KpiCatalogo } from "@/types";

interface GraficasKpiProps {
  kpi: KpiCatalogo;
  datos: DatosGrafica | null;
  cargando: boolean;
}

// Colores CSS vars definidos en styles.css como oklch tokens
const COLORES_DONA = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
];

const configBarras: ChartConfig = {
  valor: { label: "Reactivos", color: "var(--chart-1)" },
};
const configLineas: ChartConfig = {
  valor: { label: "Reactivos", color: "var(--chart-2)" },
};
const configDona: ChartConfig = {
  valor: { label: "Instrumentos", color: "var(--chart-3)" },
};

export function GraficasKpi({ kpi, datos, cargando }: GraficasKpiProps) {
  if (cargando) {
    return (
      <div className="grid gap-6 md:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-52 rounded-xl border bg-card animate-pulse" />
        ))}
      </div>
    );
  }

  if (!datos || datos.fuentesConteo === 0) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed bg-card px-6 py-12 text-center">
        <span className="flex size-10 items-center justify-center rounded-full bg-muted text-muted-foreground">
          <Database className="size-5" />
        </span>
        <p className="font-semibold text-sm">
          Sin datos en las fuentes de tu investigación
        </p>
        <p className="max-w-xs text-xs text-muted-foreground">
          Ningún instrumento de tu investigación activa está vinculado al KPI
          «{kpi.nombre}». Agrega instrumentos que cubran este indicador.
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-6 md:grid-cols-3">
      {/* Gráfica de barras — por nivel educativo */}
      <TarjetaGrafica
        titulo="Por nivel educativo"
        subtitulo="Reactivos totales"
        fuentesConteo={datos.fuentesConteo}
      >
        <ChartContainer config={configBarras} className="h-40 w-full">
          <BarChart data={datos.porNivel} margin={{ top: 4, right: 4, bottom: 4, left: -20 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="etiqueta" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
            <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
            <Tooltip
              content={({ active, payload, label }) =>
                active && payload?.length ? (
                  <div className="rounded-lg border bg-background px-3 py-2 shadow-md text-xs">
                    <p className="font-medium">{label}</p>
                    <p className="text-muted-foreground">{payload[0].value} reactivos</p>
                  </div>
                ) : null
              }
            />
            <Bar dataKey="valor" fill="var(--color-valor)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ChartContainer>
      </TarjetaGrafica>

      {/* Gráfica de líneas — evolución por año */}
      <TarjetaGrafica
        titulo="Evolución por año"
        subtitulo="Reactivos acumulados"
        fuentesConteo={datos.fuentesConteo}
      >
        <ChartContainer config={configLineas} className="h-40 w-full">
          <LineChart data={datos.porAnio} margin={{ top: 4, right: 4, bottom: 4, left: -20 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="etiqueta" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
            <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
            <Tooltip
              content={({ active, payload, label }) =>
                active && payload?.length ? (
                  <div className="rounded-lg border bg-background px-3 py-2 shadow-md text-xs">
                    <p className="font-medium">{label}</p>
                    <p className="text-muted-foreground">{payload[0].value} reactivos</p>
                  </div>
                ) : null
              }
            />
            <Line
              type="monotone"
              dataKey="valor"
              stroke="var(--color-valor)"
              strokeWidth={2}
              dot={{ r: 3, fill: "var(--color-valor)" }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ChartContainer>
      </TarjetaGrafica>

      {/* Gráfica de dona — por tipo de instrumento */}
      <TarjetaGrafica
        titulo="Por tipo de instrumento"
        subtitulo="Distribución de fuentes"
        fuentesConteo={datos.fuentesConteo}
      >
        <ChartContainer config={configDona} className="h-40 w-full">
          <PieChart>
            <Pie
              data={datos.porTipo}
              dataKey="valor"
              nameKey="etiqueta"
              cx="50%"
              cy="50%"
              innerRadius={38}
              outerRadius={60}
              paddingAngle={3}
            >
              {datos.porTipo.map((_, idx) => (
                <Cell key={idx} fill={COLORES_DONA[idx % COLORES_DONA.length]} />
              ))}
            </Pie>
            <Tooltip
              content={({ active, payload }) =>
                active && payload?.length ? (
                  <div className="rounded-lg border bg-background px-3 py-2 shadow-md text-xs">
                    <p className="font-medium">{payload[0].name}</p>
                    <p className="text-muted-foreground">{payload[0].value} instrumento{Number(payload[0].value) !== 1 ? "s" : ""}</p>
                  </div>
                ) : null
              }
            />
          </PieChart>
        </ChartContainer>
        {/* Leyenda manual */}
        <div className="mt-2 flex flex-wrap justify-center gap-2">
          {datos.porTipo.map((p, idx) => (
            <div key={p.etiqueta} className="flex items-center gap-1 text-[10px] text-muted-foreground">
              <span
                className="size-2 rounded-full"
                style={{ background: COLORES_DONA[idx % COLORES_DONA.length] }}
              />
              {p.etiqueta}
            </div>
          ))}
        </div>
      </TarjetaGrafica>
    </div>
  );
}

function TarjetaGrafica({
  titulo,
  subtitulo,
  fuentesConteo,
  children,
}: {
  titulo: string;
  subtitulo: string;
  fuentesConteo: number;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-2 rounded-xl border bg-card p-4 shadow-sm">
      <div>
        <p className="text-sm font-semibold">{titulo}</p>
        <p className="text-xs text-muted-foreground">
          {subtitulo} · {fuentesConteo} fuente{fuentesConteo !== 1 ? "s" : ""}
        </p>
      </div>
      {children}
    </div>
  );
}
