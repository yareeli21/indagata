import { Loader2, SearchX } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { OtherResearcherBadge } from "@/components/shared/OtherResearcherBadge";
import { cn } from "@/lib/utils";
import type { Instrumento, InstrumentoRelacionado, NivelCoincidencia } from "@/types";
import { ChevronDown } from "lucide-react";

interface Paso2Props {
  cargando: boolean;
  relacionados: InstrumentoRelacionado[];
  /** Mapa id → título de los instrumentos propios seleccionados en paso 1 */
  propiosSeleccionados: Instrumento[];
  seleccionadosAjenos: string[];
  onCambiarSeleccion: (ids: string[]) => void;
  onSiguiente: () => void;
  onAtras: () => void;
}

const ETIQUETAS: Record<NivelCoincidencia, string> = {
  alta: "Coincidencia alta",
  media: "Media",
  baja: "Baja",
};

const CRITERIOS: Record<NivelCoincidencia, string> = {
  alta: "3 criterios",
  media: "2 criterios",
  baja: "1 criterio",
};

const COLORES_RAZON: Record<string, string> = {
  kpi: "bg-accent/15 text-accent-foreground border-accent/30",
  nivel: "bg-primary/10 text-primary border-primary/20",
  descripcion: "bg-secondary text-secondary-foreground border-border",
};

export function Paso2Relacionados({
  cargando,
  relacionados,
  propiosSeleccionados,
  seleccionadosAjenos,
  onCambiarSeleccion,
  onSiguiente,
  onAtras,
}: Paso2Props) {
  function toggle(id: string) {
    if (seleccionadosAjenos.includes(id)) {
      onCambiarSeleccion(seleccionadosAjenos.filter((x) => x !== id));
    } else {
      onCambiarSeleccion([...seleccionadosAjenos, id]);
    }
  }

  if (cargando) {
    return (
      <div className="flex flex-col items-center gap-4 py-20 text-muted-foreground">
        <Loader2 className="size-8 animate-spin text-primary" />
        <p className="text-sm">Buscando instrumentos relacionados…</p>
      </div>
    );
  }

  const porNivel = (nivel: NivelCoincidencia) =>
    relacionados.filter((r) => r.nivel === nivel);

  const alta = porNivel("alta");
  const media = porNivel("media");
  const baja = porNivel("baja");

  if (relacionados.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed bg-card px-6 py-16 text-center">
          <span className="flex size-12 items-center justify-center rounded-full bg-muted text-muted-foreground">
            <SearchX className="size-6" />
          </span>
          <p className="font-semibold">
            No encontramos instrumentos de otros investigadores relacionados con
            tu selección
          </p>
          <p className="max-w-sm text-sm text-muted-foreground">
            Puedes continuar solo con tus instrumentos o volver a cambiar la
            selección.
          </p>
        </div>
        <div className="flex flex-wrap gap-3 border-t pt-4">
          <Button onClick={onSiguiente}>Continuar sin agregar</Button>
          <Button variant="outline" onClick={onAtras}>
            Volver
          </Button>
        </div>
      </div>
    );
  }

  const totalTab = (nivel: NivelCoincidencia) => {
    const n = porNivel(nivel).length;
    return n > 0 ? ` (${n})` : "";
  };

  return (
    <div className="space-y-6">
      <Tabs defaultValue="alta">
        <TabsList className="mb-4">
          <TabsTrigger value="alta">
            Coincidencia alta{totalTab("alta")}
          </TabsTrigger>
          <TabsTrigger value="media">
            Media{totalTab("media")}
          </TabsTrigger>
          <TabsTrigger value="baja">
            Baja{totalTab("baja")}
          </TabsTrigger>
        </TabsList>

        {(["alta", "media", "baja"] as NivelCoincidencia[]).map((nivel) => {
          const lista = porNivel(nivel);
          return (
            <TabsContent key={nivel} value={nivel}>
              {nivel === "baja" ? (
                <Collapsible defaultOpen={false}>
                  <CollapsibleTrigger asChild>
                    <button className="flex w-full items-center justify-between rounded-lg border bg-card px-4 py-2 text-sm text-muted-foreground hover:bg-muted/30">
                      <span>
                        {ETIQUETAS[nivel]} ({CRITERIOS[nivel]}) — {lista.length} instrumento{lista.length !== 1 ? "s" : ""}
                      </span>
                      <ChevronDown className="size-4 transition-transform [[data-state=open]_&]:rotate-180" />
                    </button>
                  </CollapsibleTrigger>
                  <CollapsibleContent>
                    <GrupoTarjetas
                      lista={lista}
                      propiosSeleccionados={propiosSeleccionados}
                      seleccionadosAjenos={seleccionadosAjenos}
                      onToggle={toggle}
                    />
                  </CollapsibleContent>
                </Collapsible>
              ) : lista.length === 0 ? (
                <p className="py-6 text-center text-sm text-muted-foreground">
                  No hay resultados con {ETIQUETAS[nivel].toLowerCase()} ({CRITERIOS[nivel]}).
                </p>
              ) : (
                <GrupoTarjetas
                  lista={lista}
                  propiosSeleccionados={propiosSeleccionados}
                  seleccionadosAjenos={seleccionadosAjenos}
                  onToggle={toggle}
                />
              )}
            </TabsContent>
          );
        })}
      </Tabs>

      {seleccionadosAjenos.length > 0 && (
        <p className="text-sm font-medium text-primary">
          {seleccionadosAjenos.length} instrumento{seleccionadosAjenos.length > 1 ? "s" : ""} de otros investigadores seleccionado{seleccionadosAjenos.length > 1 ? "s" : ""}
        </p>
      )}

      <div className="flex flex-wrap gap-3 border-t pt-4">
        <Button onClick={onSiguiente}>Siguiente</Button>
        <Button variant="outline" onClick={onAtras}>
          Volver
        </Button>
      </div>
    </div>
  );
}

/* ---- sub-componentes ---- */

interface GrupoTarjetasProps {
  lista: InstrumentoRelacionado[];
  propiosSeleccionados: Instrumento[];
  seleccionadosAjenos: string[];
  onToggle: (id: string) => void;
}

function GrupoTarjetas({ lista, propiosSeleccionados, seleccionadosAjenos, onToggle }: GrupoTarjetasProps) {
  return (
    <ul className="mt-3 space-y-3">
      {lista.map((rel) => (
        <TarjetaRelacionado
          key={rel.instrumento.id}
          rel={rel}
          propiosSeleccionados={propiosSeleccionados}
          marcado={seleccionadosAjenos.includes(rel.instrumento.id)}
          onToggle={() => onToggle(rel.instrumento.id)}
        />
      ))}
    </ul>
  );
}

interface TarjetaRelacionadoProps {
  rel: InstrumentoRelacionado;
  propiosSeleccionados: Instrumento[];
  marcado: boolean;
  onToggle: () => void;
}

function TarjetaRelacionado({ rel, propiosSeleccionados, marcado, onToggle }: TarjetaRelacionadoProps) {
  const coincideConNombres = propiosSeleccionados
    .filter((p) => rel.coincideCon.includes(p.id))
    .map((p) => p.titulo);

  return (
    <li
      className={cn(
        "rounded-xl border bg-card p-4 transition-colors",
        marcado && "border-primary/40 bg-primary/5",
      )}
    >
      <label className="flex cursor-pointer items-start gap-3">
        <Checkbox
          checked={marcado}
          onCheckedChange={onToggle}
          className="mt-0.5"
          aria-label={`Seleccionar ${rel.instrumento.titulo}`}
        />
        <div className="min-w-0 flex-1 space-y-3">
          {/* Cabecera */}
          <div className="flex flex-wrap items-start gap-2">
            <p className="font-medium leading-snug">{rel.instrumento.titulo}</p>
            <OtherResearcherBadge />
          </div>

          {/* Tipo e investigador */}
          <p className="text-xs text-muted-foreground">
            {rel.instrumento.tipo} · {rel.instrumento.nivel}
          </p>

          {/* Razones de coincidencia */}
          <div className="flex flex-wrap gap-1.5">
            {rel.razones.map((r) => (
              <span
                key={r.etiqueta}
                className={cn(
                  "rounded-full border px-2.5 py-0.5 text-xs font-medium",
                  COLORES_RAZON[r.tipo] ?? "bg-muted text-muted-foreground",
                )}
              >
                {r.etiqueta}
              </span>
            ))}
          </div>

          {/* Coincide con */}
          {coincideConNombres.length > 0 && (
            <p className="text-xs text-muted-foreground">
              <span className="font-medium text-foreground/70">Coincide con:</span>{" "}
              {coincideConNombres.join(", ")}
            </p>
          )}
        </div>
      </label>
    </li>
  );
}
