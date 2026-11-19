import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import type { Instrumento } from "@/types";

type Alcance = "todos" | "mios";

interface Paso1Props {
  /** Todo el acervo: los instrumentos son compartidos entre investigadores. */
  instrumentos: Instrumento[];
  miId: string;
  nombreAutor: (autorId: string) => string;
  seleccionados: string[];
  onCambiarSeleccion: (ids: string[]) => void;
  onBuscar: () => void;
  onOmitir: () => void;
}

/** Minúsculas y sin acentos, para que «satisfaccion» encuentre «Satisfacción». */
const normalizar = (texto: string) => texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

export function Paso1Seleccion({
  instrumentos,
  miId,
  nombreAutor,
  seleccionados,
  onCambiarSeleccion,
  onBuscar,
  onOmitir,
}: Paso1Props) {
  const [busqueda, setBusqueda] = useState("");
  const [alcance, setAlcance] = useState<Alcance>("todos");

  const propios = useMemo(
    () => instrumentos.filter((i) => i.autorId === miId).length,
    [instrumentos, miId],
  );

  const filtrados = useMemo(() => {
    const terminos = normalizar(busqueda).split(/\s+/).filter(Boolean);
    return instrumentos
      .filter((i) => alcance === "todos" || i.autorId === miId)
      .filter((i) => {
        if (terminos.length === 0) return true;
        const texto = normalizar(
          [i.titulo, i.tipo, nombreAutor(i.autorId), ...i.kpis, ...i.etiquetas].join(" "),
        );
        return terminos.every((t) => texto.includes(t));
      })
      .sort((a, b) => Number(b.autorId === miId) - Number(a.autorId === miId));
  }, [instrumentos, busqueda, alcance, miId, nombreAutor]);

  const visiblesSeleccionados = filtrados.filter((i) => seleccionados.includes(i.id)).length;
  const todosSeleccionados = filtrados.length > 0 && visiblesSeleccionados === filtrados.length;
  const algunoSeleccionado = visiblesSeleccionados > 0 && !todosSeleccionados;

  // «Seleccionar todos» actúa sobre lo que se ve con la búsqueda actual.
  function toggleTodos() {
    const visibles = new Set(filtrados.map((i) => i.id));
    if (todosSeleccionados) {
      onCambiarSeleccion(seleccionados.filter((id) => !visibles.has(id)));
    } else {
      onCambiarSeleccion([...new Set([...seleccionados, ...visibles])]);
    }
  }

  function toggle(id: string) {
    if (seleccionados.includes(id)) {
      onCambiarSeleccion(seleccionados.filter((x) => x !== id));
    } else {
      onCambiarSeleccion([...seleccionados, id]);
    }
  }

  return (
    <div className="space-y-6">
      {/* Buscador + alcance */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-9"
            placeholder="Buscar por título, tipo, KPI o autor…"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            maxLength={100}
          />
        </div>
        <div className="flex gap-2" role="group" aria-label="Instrumentos a mostrar">
          <Button
            size="sm"
            variant={alcance === "todos" ? "default" : "outline"}
            onClick={() => setAlcance("todos")}
          >
            Todo el acervo ({instrumentos.length})
          </Button>
          <Button
            size="sm"
            variant={alcance === "mios" ? "default" : "outline"}
            onClick={() => setAlcance("mios")}
          >
            Solo míos ({propios})
          </Button>
        </div>
      </div>

      {/* Contador + seleccionar todos */}
      <div className="flex items-center justify-between text-sm">
        <label className="flex cursor-pointer items-center gap-2 text-muted-foreground">
          <Checkbox
            checked={todosSeleccionados}
            data-state={algunoSeleccionado ? "indeterminate" : undefined}
            onCheckedChange={toggleTodos}
            aria-label="Seleccionar todos los mostrados"
          />
          Seleccionar todos los mostrados
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
          {busqueda.trim()
            ? `No hay instrumentos que coincidan con "${busqueda}".`
            : "Aún no has subido instrumentos; elige «Todo el acervo» para ver los de otros investigadores."}
        </p>
      ) : (
        <ul className="divide-y divide-border rounded-2xl border border-border bg-card shadow-card">
          {filtrados.map((ins) => {
            const marcado = seleccionados.includes(ins.id);
            const mio = ins.autorId === miId;
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
                      {mio ? (
                        <span className="rounded-md bg-primary/10 px-1.5 py-0.5 font-medium text-primary">
                          Tuyo
                        </span>
                      ) : (
                        <span>{nombreAutor(ins.autorId)}</span>
                      )}
                      {ins.kpis.slice(0, 2).map((k) => (
                        <span key={k} className="rounded-md border px-1.5 py-0.5">
                          {k}
                        </span>
                      ))}
                      {ins.kpis.length > 2 && (
                        <span className="text-muted-foreground/70">+{ins.kpis.length - 2}</span>
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
        <Button disabled={seleccionados.length === 0} onClick={onBuscar} className="sm:flex-none">
          Buscar instrumentos relacionados
        </Button>
        <Button variant="ghost" size="sm" onClick={onOmitir}>
          Omitir búsqueda
        </Button>
      </div>
    </div>
  );
}
