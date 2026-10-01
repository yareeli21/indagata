import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import type { Instrumento } from "@/types";

interface Paso1Props {
  instrumentos: Instrumento[];
  seleccionados: string[];
  onCambiarSeleccion: (ids: string[]) => void;
  onBuscar: () => void;
  onOmitir: () => void;
}

export function Paso1Seleccion({
  instrumentos,
  seleccionados,
  onCambiarSeleccion,
  onBuscar,
  onOmitir,
}: Paso1Props) {
  const [busqueda, setBusqueda] = useState("");

  const filtrados = useMemo(() => {
    const q = busqueda.trim().toLowerCase();
    if (!q) return instrumentos;
    return instrumentos.filter(
      (i) =>
        i.titulo.toLowerCase().includes(q) ||
        i.tipo.toLowerCase().includes(q) ||
        i.kpis.some((k) => k.toLowerCase().includes(q)),
    );
  }, [instrumentos, busqueda]);

  function toggleTodos() {
    if (seleccionados.length === instrumentos.length) {
      onCambiarSeleccion([]);
    } else {
      onCambiarSeleccion(instrumentos.map((i) => i.id));
    }
  }

  function toggle(id: string) {
    if (seleccionados.includes(id)) {
      onCambiarSeleccion(seleccionados.filter((x) => x !== id));
    } else {
      onCambiarSeleccion([...seleccionados, id]);
    }
  }

  const todosSeleccionados =
    instrumentos.length > 0 && seleccionados.length === instrumentos.length;
  const algunoSeleccionado =
    seleccionados.length > 0 && seleccionados.length < instrumentos.length;

  return (
    <div className="space-y-6">
      {/* Buscador */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          className="pl-9"
          placeholder="Buscar por título, tipo o KPI…"
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          maxLength={100}
        />
      </div>

      {/* Contador + seleccionar todos */}
      <div className="flex items-center justify-between text-sm">
        <label className="flex cursor-pointer items-center gap-2 text-muted-foreground">
          <Checkbox
            checked={todosSeleccionados}
            data-state={algunoSeleccionado ? "indeterminate" : undefined}
            onCheckedChange={toggleTodos}
            aria-label="Seleccionar todos"
          />
          Seleccionar todos
        </label>
        <span className="font-medium text-primary">
          {seleccionados.length > 0
            ? `${seleccionados.length} seleccionado${seleccionados.length > 1 ? "s" : ""}`
            : "Ninguno seleccionado"}
        </span>
      </div>

      {/* Lista */}
      {filtrados.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">
          No hay instrumentos que coincidan con "{busqueda}".
        </p>
      ) : (
        <ul className="divide-y rounded-xl border bg-card shadow-sm">
          {filtrados.map((ins) => {
            const marcado = seleccionados.includes(ins.id);
            return (
              <li key={ins.id}>
                <label
                  className={cn(
                    "flex cursor-pointer items-start gap-3 px-4 py-3 transition-colors hover:bg-muted/30",
                    marcado && "bg-primary/5",
                  )}
                >
                  <Checkbox
                    checked={marcado}
                    onCheckedChange={() => toggle(ins.id)}
                    className="mt-0.5"
                    aria-label={`Seleccionar ${ins.titulo}`}
                  />
                  <div className="min-w-0 flex-1 space-y-1">
                    <p
                      className={cn(
                        "font-medium leading-snug",
                        marcado ? "text-foreground" : "text-foreground/80",
                      )}
                    >
                      {ins.titulo}
                    </p>
                    <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      <span>{ins.tipo}</span>
                      <span>·</span>
                      <span>{ins.nivel}</span>
                      {ins.kpis.slice(0, 2).map((k) => (
                        <span
                          key={k}
                          className="rounded-md border px-1.5 py-0.5"
                        >
                          {k}
                        </span>
                      ))}
                      {ins.kpis.length > 2 && (
                        <span className="text-muted-foreground/70">
                          +{ins.kpis.length - 2}
                        </span>
                      )}
                    </div>
                  </div>
                </label>
              </li>
            );
          })}
        </ul>
      )}

      {/* Acciones */}
      <div className="flex flex-wrap items-center gap-3 border-t pt-4">
        <Button
          disabled={seleccionados.length === 0}
          onClick={onBuscar}
          className="sm:flex-none"
        >
          Buscar instrumentos relacionados
        </Button>
        <Button variant="ghost" size="sm" onClick={onOmitir}>
          Omitir búsqueda
        </Button>
      </div>
    </div>
  );
}
