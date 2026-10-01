import { useState } from "react";
import { Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { OtherResearcherBadge } from "@/components/shared/OtherResearcherBadge";
import type { Instrumento } from "@/types";

interface Paso3Props {
  propios: Instrumento[];
  ajenos: Instrumento[];
  onQuitarPropio: (id: string) => void;
  onQuitarAjeno: (id: string) => void;
  onIniciar: (nombre: string) => Promise<void>;
  onAtras: () => void;
}

export function Paso3Revision({
  propios,
  ajenos,
  onQuitarPropio,
  onQuitarAjeno,
  onIniciar,
  onAtras,
}: Paso3Props) {
  const [nombre, setNombre] = useState("");
  const [iniciando, setIniciando] = useState(false);

  const totalInstrumentos = propios.length + ajenos.length;
  const puedeIniciar = nombre.trim().length > 0 && totalInstrumentos > 0;

  async function handleIniciar() {
    if (!puedeIniciar) return;
    setIniciando(true);
    await onIniciar(nombre.trim());
    // La navegación la maneja el padre; no reseteamos aquí
  }

  return (
    <div className="space-y-8">
      {/* Lista de instrumentos propios */}
      <section className="space-y-3">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Mis instrumentos
          <span className="ml-2 rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
            {propios.length}
          </span>
        </h3>
        {propios.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No has seleccionado instrumentos propios.
          </p>
        ) : (
          <ul className="divide-y rounded-xl border bg-card shadow-sm">
            {propios.map((ins) => (
              <ItemRevision
                key={ins.id}
                instrumento={ins}
                onQuitar={() => onQuitarPropio(ins.id)}
              />
            ))}
          </ul>
        )}
      </section>

      {/* Lista de instrumentos ajenos */}
      {ajenos.length > 0 && (
        <section className="space-y-3">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            De otros investigadores
            <span className="ml-2 rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
              {ajenos.length}
            </span>
          </h3>
          <ul className="divide-y rounded-xl border bg-card shadow-sm">
            {ajenos.map((ins) => (
              <ItemRevision
                key={ins.id}
                instrumento={ins}
                ajeno
                onQuitar={() => onQuitarAjeno(ins.id)}
              />
            ))}
          </ul>
        </section>
      )}

      {/* Nombre de la investigación */}
      <div className="space-y-2">
        <Label htmlFor="nombre-investigacion">
          Nombre de la investigación
          <span className="ml-1 text-destructive" aria-hidden>
            *
          </span>
        </Label>
        <Input
          id="nombre-investigacion"
          placeholder="Ej. Trayectorias lectoras en secundaria rural"
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          maxLength={120}
          autoComplete="off"
        />
        <p className="text-xs text-muted-foreground">
          {nombre.trim().length}/120 caracteres
        </p>
      </div>

      {/* Acciones */}
      <div className="flex flex-wrap gap-3 border-t pt-4">
        <Button
          disabled={!puedeIniciar || iniciando}
          onClick={handleIniciar}
        >
          {iniciando && <Loader2 className="animate-spin" />}
          Iniciar investigación
        </Button>
        <Button variant="outline" disabled={iniciando} onClick={onAtras}>
          Volver
        </Button>
      </div>
    </div>
  );
}

/* ---- sub-componentes ---- */

interface ItemRevisionProps {
  instrumento: Instrumento;
  ajeno?: boolean;
  onQuitar: () => void;
}

function ItemRevision({ instrumento: ins, ajeno = false, onQuitar }: ItemRevisionProps) {
  return (
    <li className="flex items-start gap-3 px-4 py-3">
      <div className="min-w-0 flex-1 space-y-1">
        <p className="font-medium leading-snug">{ins.titulo}</p>
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <span>{ins.tipo}</span>
          <span>·</span>
          <span>{ins.nivel}</span>
          {ajeno && <OtherResearcherBadge />}
        </div>
      </div>
      <button
        type="button"
        onClick={onQuitar}
        aria-label={`Quitar ${ins.titulo}`}
        className="mt-0.5 rounded-md p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
      >
        <X className="size-4" />
      </button>
    </li>
  );
}
