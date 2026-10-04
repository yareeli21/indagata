import { Search } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  ESTADOS_INSTRUMENTO,
  NIVELES_EDUCATIVOS,
  TIPOS_INSTRUMENTO,
  type EstadoInstrumento,
  type NivelEducativo,
  type TipoInstrumento,
} from "@/types";
import type { Filtros } from "./filtros";

interface FiltrosPanelProps {
  filtros: Filtros;
  catalogoKpis: string[];
  anios: number[];
  onChange: (f: Filtros) => void;
}

const TODOS = "__todos";

export function FiltrosPanel({ filtros, catalogoKpis, anios, onChange }: FiltrosPanelProps) {
  const toggleKpi = (k: string) =>
    onChange({
      ...filtros,
      kpis: filtros.kpis.includes(k) ? filtros.kpis.filter((x) => x !== k) : [...filtros.kpis, k],
    });

  return (
    <aside className="space-y-6 rounded-2xl border border-border bg-card p-5 shadow-soft">
      <h2 className="font-display text-base font-semibold text-foreground">Filtros</h2>
      <div className="space-y-2">
        <Label htmlFor="f-palabra">Palabra clave</Label>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            id="f-palabra"
            className="pl-9"
            maxLength={100}
            placeholder="Buscar…"
            value={filtros.palabra}
            onChange={(e) => onChange({ ...filtros, palabra: e.target.value })}
          />
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
        <Select
          value={filtros.nivel ?? TODOS}
          onValueChange={(v) =>
            onChange({ ...filtros, nivel: v === TODOS ? null : (v as NivelEducativo) })
          }
        >
          <SelectTrigger id="f-nivel">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={TODOS}>Todos los niveles</SelectItem>
            {NIVELES_EDUCATIVOS.map((n) => (
              <SelectItem key={n} value={n}>
                {n}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-2">
        <Label htmlFor="f-tipo">Tipo de instrumento</Label>
        <Select
          value={filtros.tipo ?? TODOS}
          onValueChange={(v) =>
            onChange({ ...filtros, tipo: v === TODOS ? null : (v as TipoInstrumento) })
          }
        >
          <SelectTrigger id="f-tipo">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={TODOS}>Todos los tipos</SelectItem>
            {TIPOS_INSTRUMENTO.map((t) => (
              <SelectItem key={t} value={t}>
                {t}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-2">
        <Label htmlFor="f-estado">Estado</Label>
        <Select
          value={filtros.estado ?? TODOS}
          onValueChange={(v) =>
            onChange({ ...filtros, estado: v === TODOS ? null : (v as EstadoInstrumento) })
          }
        >
          <SelectTrigger id="f-estado">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={TODOS}>Todos los estados</SelectItem>
            {ESTADOS_INSTRUMENTO.map((e) => (
              <SelectItem key={e} value={e}>
                {e}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-2">
        <Label htmlFor="f-anio">Año</Label>
        <Select
          value={filtros.anio !== null ? String(filtros.anio) : TODOS}
          onValueChange={(v) => onChange({ ...filtros, anio: v === TODOS ? null : Number(v) })}
        >
          <SelectTrigger id="f-anio">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={TODOS}>Todos los años</SelectItem>
            {anios.map((a) => (
              <SelectItem key={a} value={String(a)}>
                {a}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-2">
        <Label>Rango de fechas</Label>
        <div className="space-y-1.5">
          <Label htmlFor="f-desde" className="text-xs text-muted-foreground">
            Desde
          </Label>
          <Input
            id="f-desde"
            type="date"
            aria-label="Desde"
            value={filtros.desde}
            onChange={(e) => onChange({ ...filtros, desde: e.target.value })}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="f-hasta" className="text-xs text-muted-foreground">
            Hasta
          </Label>
          <Input
            id="f-hasta"
            type="date"
            aria-label="Hasta"
            value={filtros.hasta}
            onChange={(e) => onChange({ ...filtros, hasta: e.target.value })}
          />
        </div>
      </div>
    </aside>
  );
}
