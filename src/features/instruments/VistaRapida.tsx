import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { OtherResearcherBadge } from "@/components/shared/OtherResearcherBadge";
import type { FormatoDescarga, Instrumento } from "@/types";
import { MenuDescarga } from "./MenuDescarga";
import { TipoBadge } from "./TipoBadge";
import { formatearFecha } from "./filtros";

interface VistaRapidaProps {
  instrumento: Instrumento | null;
  autor: string;
  ajeno: boolean;
  onCerrar: () => void;
  onDescargar: (f: FormatoDescarga) => void;
  onEliminar: () => void;
}

export function VistaRapida({ instrumento: i, autor, ajeno, onCerrar, onDescargar, onEliminar }: VistaRapidaProps) {
  return (
    <Sheet open={!!i} onOpenChange={(o) => !o && onCerrar()}>
      <SheetContent className="w-full overflow-hidden sm:max-w-lg">
        {i && (
          <>
            {ajeno && (
              <div
                aria-hidden
                className="pointer-events-none absolute inset-0 overflow-hidden"
                style={{ zIndex: 0 }}
              >
                {/* Patrón diagonal de marca de agua */}
                <div
                  className="absolute inset-[-100%] flex flex-col gap-16"
                  style={{ transform: "rotate(-35deg)", transformOrigin: "center" }}
                >
                  {Array.from({ length: 12 }).map((_, row) => (
                    <div key={row} className="flex gap-20 whitespace-nowrap">
                      {Array.from({ length: 6 }).map((_, col) => (
                        <span
                          key={col}
                          className="text-sm font-semibold uppercase tracking-widest text-muted-foreground/10 select-none"
                        >
                          Instrumento de otro investigador
                        </span>
                      ))}
                    </div>
                  ))}
                </div>
              </div>
            )}
            <div className="relative z-10 space-y-6">
              <SheetHeader className="space-y-3 text-left">
                <div className="flex flex-wrap gap-2"><TipoBadge tipo={i.tipo} />{ajeno && <OtherResearcherBadge />}</div>
                <SheetTitle className="text-xl">{i.titulo}</SheetTitle>
                <SheetDescription>{i.descripcion}</SheetDescription>
              </SheetHeader>
              <dl className="grid grid-cols-2 gap-4 text-sm">
                <Dato etiqueta="Investigador" valor={autor} />
                <Dato etiqueta="Nivel educativo" valor={i.nivel} />
                <Dato etiqueta="Fecha" valor={formatearFecha(i.fecha)} />
                <Dato etiqueta="Reactivos" valor={String(i.reactivos)} />
                <Dato etiqueta="Estado" valor={i.estado} />
              </dl>
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">KPIs</p>
                <div className="flex flex-wrap gap-1.5">
                  {i.kpis.map((k) => <span key={k} className="rounded-md border px-2 py-0.5 text-xs">{k}</span>)}
                </div>
              </div>
              <div className="flex flex-wrap gap-2 border-t pt-4">
                <MenuDescarga instrumento={i} ajeno={ajeno} onDescargar={onDescargar} />
                {!ajeno && (
                  <Button variant="outline" className="text-destructive hover:text-destructive" onClick={onEliminar}>
                    <Trash2 /> Eliminar
                  </Button>
                )}
              </div>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}

function Dato({ etiqueta, valor }: { etiqueta: string; valor: string }) {
  return (
    <div>
      <dt className="text-muted-foreground">{etiqueta}</dt>
      <dd className="font-medium">{valor}</dd>
    </div>
  );
}
