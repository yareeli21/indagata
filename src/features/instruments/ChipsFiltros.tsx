import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { FILTROS_VACIOS, formatearFecha, hayFiltros, type Filtros } from "./filtros";

interface ChipsFiltrosProps {
  filtros: Filtros;
  onChange: (f: Filtros) => void;
}

export function ChipsFiltros({ filtros: f, onChange }: ChipsFiltrosProps) {
  if (!hayFiltros(f)) return null;
  const chips: { etiqueta: string; quitar: () => void }[] = [];
  if (f.palabra.trim()) chips.push({ etiqueta: `“${f.palabra.trim()}”`, quitar: () => onChange({ ...f, palabra: "" }) });
  f.kpis.forEach((k) => chips.push({ etiqueta: `KPI: ${k}`, quitar: () => onChange({ ...f, kpis: f.kpis.filter((x) => x !== k) }) }));
  if (f.nivel) chips.push({ etiqueta: f.nivel, quitar: () => onChange({ ...f, nivel: null }) });
  if (f.tipo) chips.push({ etiqueta: f.tipo, quitar: () => onChange({ ...f, tipo: null }) });
  if (f.desde) chips.push({ etiqueta: `Desde ${formatearFecha(f.desde)}`, quitar: () => onChange({ ...f, desde: "" }) });
  if (f.hasta) chips.push({ etiqueta: `Hasta ${formatearFecha(f.hasta)}`, quitar: () => onChange({ ...f, hasta: "" }) });

  return (
    <div className="flex flex-wrap items-center gap-2">
      {chips.map((c) => (
        <span key={c.etiqueta} className="inline-flex items-center gap-1 rounded-full bg-primary/10 py-1 pl-3 pr-1 text-sm text-primary">
          {c.etiqueta}
          <button type="button" onClick={c.quitar} aria-label={`Quitar ${c.etiqueta}`} className="rounded-full p-0.5 hover:bg-primary/20">
            <X className="size-3.5" />
          </button>
        </span>
      ))}
      <Button variant="link" size="sm" onClick={() => onChange(FILTROS_VACIOS)}>Limpiar filtros</Button>
    </div>
  );
}
