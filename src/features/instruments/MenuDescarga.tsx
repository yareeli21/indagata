import { ChevronDown, Download, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import type { FormatoDescarga, Instrumento } from "@/types";

interface MenuDescargaProps {
  instrumento: Instrumento;
  ajeno: boolean;
  onDescargar: (f: FormatoDescarga) => void;
}

export function MenuDescarga({ instrumento, ajeno, onDescargar }: MenuDescargaProps) {
  const opciones: { formato: FormatoDescarga; etiqueta: string }[] = [
    { formato: "crudo", etiqueta: "Instrumento crudo" },
    { formato: "json", etiqueta: "JSON" },
    ...(instrumento.tipo === "Encuesta" ? [{ formato: "sav" as const, etiqueta: ".sav (SPSS)" }] : []),
  ];
  return (
    <TooltipProvider delayDuration={100}>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button><Download /> Descargar <ChevronDown /></Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-56">
          {opciones.map((o) => {
            const bloqueado = ajeno && o.formato !== "crudo";
            if (!bloqueado) {
              return <DropdownMenuItem key={o.formato} onSelect={() => onDescargar(o.formato)}>{o.etiqueta}</DropdownMenuItem>;
            }
            return (
              <Tooltip key={o.formato}>
                <TooltipTrigger asChild>
                  <div>
                    <DropdownMenuItem disabled className="justify-between">
                      {o.etiqueta} <Lock className="size-3.5" />
                    </DropdownMenuItem>
                  </div>
                </TooltipTrigger>
                <TooltipContent side="left">Solo puedes descargar el instrumento en crudo</TooltipContent>
              </Tooltip>
            );
          })}
        </DropdownMenuContent>
      </DropdownMenu>
    </TooltipProvider>
  );
}
