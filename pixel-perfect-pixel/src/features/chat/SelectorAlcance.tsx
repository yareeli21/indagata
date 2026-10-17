import { ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { AlcanceChat, Instrumento } from "@/types";

interface SelectorAlcanceProps {
  alcance: AlcanceChat;
  elegidos: string[];
  /** Instrumentos que se pueden elegir uno por uno. */
  instrumentos: Instrumento[];
  deshabilitado?: boolean;
  onCambiarAlcance: (a: AlcanceChat) => void;
  onCambiarElegidos: (ids: string[]) => void;
}

const OPCIONES: { id: AlcanceChat; etiqueta: string }[] = [
  { id: "investigacion", etiqueta: "Mi investigación" },
  { id: "elegidos", etiqueta: "Elegir instrumentos" },
  { id: "acervo", etiqueta: "Todo el acervo" },
];

/** Qué instrumentos consulta el chat: los de la investigación, unos elegidos o todo el acervo. */
export function SelectorAlcance({
  alcance,
  elegidos,
  instrumentos,
  deshabilitado,
  onCambiarAlcance,
  onCambiarElegidos,
}: SelectorAlcanceProps) {
  function alternar(id: string, marcado: boolean) {
    onCambiarElegidos(marcado ? [...elegidos, id] : elegidos.filter((e) => e !== id));
  }

  return (
    <div className="flex flex-wrap items-center gap-2 px-4 pt-3">
      <span className="text-xs font-medium text-muted-foreground">Consultar:</span>
      <Select
        value={alcance}
        onValueChange={(v) => onCambiarAlcance(v as AlcanceChat)}
        disabled={deshabilitado ?? false}
      >
        <SelectTrigger className="h-7 w-48 text-xs" aria-label="Alcance del chat">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {OPCIONES.map((o) => (
            <SelectItem key={o.id} value={o.id} className="text-xs">
              {o.etiqueta}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {alcance === "elegidos" && (
        <Popover>
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className="h-7 gap-1 text-xs"
              disabled={deshabilitado ?? false}
            >
              {elegidos.length === 0
                ? "Ninguno (se usa tu investigación)"
                : `${elegidos.length} instrumento${elegidos.length === 1 ? "" : "s"}`}
              <ChevronDown className="size-3" aria-hidden />
            </Button>
          </PopoverTrigger>
          <PopoverContent align="start" className="max-h-72 w-80 overflow-y-auto p-2">
            {instrumentos.length === 0 ? (
              <p className="p-2 text-xs text-muted-foreground">No hay instrumentos disponibles.</p>
            ) : (
              <ul className="space-y-1">
                {instrumentos.map((ins) => {
                  const id = `alcance-${ins.id}`;
                  return (
                    <li
                      key={ins.id}
                      className="flex items-start gap-2 rounded-md p-1.5 hover:bg-muted"
                    >
                      <Checkbox
                        id={id}
                        checked={elegidos.includes(ins.id)}
                        onCheckedChange={(v) => alternar(ins.id, v === true)}
                      />
                      <label
                        htmlFor={id}
                        className="min-w-0 flex-1 cursor-pointer text-xs leading-snug"
                      >
                        <span className="block truncate font-medium">{ins.titulo}</span>
                        <span className="text-muted-foreground">{ins.tipo}</span>
                      </label>
                    </li>
                  );
                })}
              </ul>
            )}
          </PopoverContent>
        </Popover>
      )}

      {alcance === "acervo" && (
        <span className="text-xs text-muted-foreground">
          Todos los instrumentos aprobados del sistema.
        </span>
      )}
    </div>
  );
}
