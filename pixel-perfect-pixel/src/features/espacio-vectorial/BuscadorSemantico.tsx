import { useState, type FormEvent } from "react";
import { Loader2, Sparkles, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { EJEMPLOS_BUSQUEDA } from "./recorrido";

interface BuscadorSemanticoProps {
  buscando: boolean;
  /** Frase de la búsqueda activa (para mostrar «Quitar»). */
  activa: string | null;
  onBuscar: (texto: string) => void;
  onQuitar: () => void;
  className?: string | undefined;
}

/**
 * Buscador en vivo: la frase se convierte en vector con el mismo modelo, aparece
 * como estrella en el mapa y se une con sus vecinos. Es lo que hace el RAG.
 */
export function BuscadorSemantico({
  buscando,
  activa,
  onBuscar,
  onQuitar,
  className,
}: BuscadorSemanticoProps) {
  const [texto, setTexto] = useState("");
  const valido = texto.trim().length >= 3;

  function enviar(e: FormEvent) {
    e.preventDefault();
    if (valido && !buscando) onBuscar(texto.trim());
  }

  return (
    <div className={cn("superficie flex flex-col gap-3 rounded-3xl p-3 lg:p-4", className)}>
      <form onSubmit={enviar} className="flex min-w-0 flex-col gap-3 sm:flex-row" role="search">
        <label className="relative min-w-0 flex-1">
          <span className="sr-only">Escribe una frase para ubicarla en el mapa</span>
          <Sparkles
            className="pointer-events-none absolute left-4 top-1/2 size-5 -translate-y-1/2 text-primary"
            aria-hidden
          />
          <input
            id="buscador-espacio"
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            maxLength={300}
            placeholder="Escribe una pregunta y mira dónde cae en el mapa…"
            className="h-12 w-full rounded-2xl border border-input bg-card pl-12 pr-4 text-sm text-foreground shadow-card outline-none transition-shadow placeholder:text-muted-foreground focus-visible:border-primary focus-visible:ring-4 focus-visible:ring-ring/15"
          />
        </label>
        <div className="flex gap-2">
          <Button
            type="submit"
            size="lg"
            disabled={!valido || buscando}
            className="flex-1 sm:flex-none"
          >
            {buscando ? <Loader2 className="animate-spin" /> : <Sparkles />}
            Ubicar en el mapa
          </Button>
          {activa && (
            <Button
              type="button"
              variant="outline"
              size="lg"
              onClick={() => {
                setTexto("");
                onQuitar();
              }}
              aria-label="Quitar la búsqueda"
            >
              <X />
              <span className="hidden md:inline">Quitar</span>
            </Button>
          )}
        </div>
      </form>
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-semibold text-muted-foreground">Prueba con:</span>
        {EJEMPLOS_BUSQUEDA.map((ejemplo) => (
          <button
            key={ejemplo}
            type="button"
            disabled={buscando}
            onClick={() => {
              setTexto(ejemplo);
              onBuscar(ejemplo);
            }}
            className="rounded-full border border-border bg-card px-3 py-1.5 text-xs font-semibold text-foreground transition-colors hover:border-primary/40 hover:bg-primary-soft hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60"
          >
            {ejemplo}
          </button>
        ))}
      </div>
    </div>
  );
}
