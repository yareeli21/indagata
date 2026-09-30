import { Search } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { NIVELES_EDUCATIVOS, TIPOS_INSTRUMENTO, type NivelEducativo, type TipoInstrumento } from "@/types";
import type { Filtros } from "./filtros";

interface FiltrosPanelProps {
  filtros: Filtros;
  catalogoKpis: string[];
  onChange: (f: Filtros) => void;
}

const TODOS = "__todos";

export function FiltrosPanel({ filtros, catalogoKpis, onChange }: FiltrosPanelProps) {
  const toggleKpi = (k: string) =>
    onChange({ ...filtros, kpis: filtros.kpis.includes(k) ? filtros.kpis.filter((x) => x !== k) : [...filtros.kpis, k] });

  return (
    <aside className="space-y-6 rounded-xl border bg-card p-5 shadow-sm">
      <h2 className="font-semibold">Filtros</h2>
      <div className="space-y-2">
        <Label htmlFor="f-palabra">Palabra clave</Label>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input id="f-palabra" className="pl-9" maxLength={100} placeholder="Buscar…" value={filtros.palabra}
            onChange={(e) => onChange({ ...filtros, palabra: e.target.value })} />
        </div>
      </div>
      <div className="space-y-2">
        <Label>KPI</Label>
        <div className="max-h-48 space-y-2 overflow-auto pr-1">
          {catalogoKpis.map((k) => (
            <label key={k} className="flex cursor-pointer items-center gap-2 text-sm">
              <Checkbox checked={filtros.kpis.includes(k)} onCheckedChange={() => toggleKpi(k)} />
              {k}
            </label>
          ))}
        </div>
      </div>
      <div className="space-y-2">
        <Label htmlFor="f-nivel">Nivel educativo</Label>
        <Select value={filtros.nivel ?? TODOS} onValueChange={(v) => onChange({ ...filtros, nivel: v === TODOS ? null : (v as NivelEducativo) })}>
          <SelectTrigger id="f-nivel"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value={TODOS}>Todos los niveles</SelectItem>
            {NIVELES_EDUCATIVOS.map((n) => <SelectItem key={n} value={n}>{n}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-2">
        <Label htmlFor="f-tipo">Tipo de instrumento</Label>
        <Select value={filtros.tipo ?? TODOS} onValueChange={(v) => onChange({ ...filtros, tipo: v === TODOS ? null : (v as TipoInstrumento) })}>
          <SelectTrigger id="f-tipo"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value={TODOS}>Todos los tipos</SelectItem>
            {TIPOS_INSTRUMENTO.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-2">
        <Label>Rango de fechas</Label>
        <Input type="date" aria-label="Desde" value={filtros.desde} onChange={(e) => onChange({ ...filtros, desde: e.target.value })} />
        <Input type="date" aria-label="Hasta" value={filtros.hasta} onChange={(e) => onChange({ ...filtros, hasta: e.target.value })} />
      </div>
    </aside>
  );
}
