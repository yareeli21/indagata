import { useRef, useState } from "react";
import { ArrowUp, Square } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { MODELOS_DISPONIBLES } from "@/api/chat";
import type { ModeloLLM } from "@/types";

interface BarraEntradaProps {
  modelo: ModeloLLM;
  generando: boolean;
  onCambiarModelo: (m: ModeloLLM) => void;
  onEnviar: (texto: string) => void;
  onDetener: () => void;
}

export function BarraEntrada({
  modelo,
  generando,
  onCambiarModelo,
  onEnviar,
  onDetener,
}: BarraEntradaProps) {
  const [texto, setTexto] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const puedeEnviar = texto.trim().length > 0 && !generando;

  function handleEnviar() {
    const msg = texto.trim();
    if (!msg) return;
    onEnviar(msg);
    setTexto("");
    textareaRef.current?.focus();
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (puedeEnviar) handleEnviar();
    }
  }

  return (
    <div className="border-t bg-card px-4 py-3">
      {/* Selector de modelo */}
      <div className="mb-2 flex items-center gap-2">
        <span className="text-xs text-muted-foreground">Modelo:</span>
        <Select
          value={modelo}
          onValueChange={(v) => onCambiarModelo(v as ModeloLLM)}
          disabled={generando}
        >
          <SelectTrigger className="h-7 w-44 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {MODELOS_DISPONIBLES.map((m) => (
              <SelectItem key={m.id} value={m.id} className="text-xs">
                {m.etiqueta}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Campo de texto + acciones */}
      <div className="flex items-end gap-2">
        <Textarea
          ref={textareaRef}
          className="min-h-[44px] max-h-40 flex-1 resize-none text-sm"
          placeholder="Escribe tu pregunta… (Enter para enviar, Shift+Enter para nueva línea)"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={generando}
          rows={1}
          maxLength={2000}
          aria-label="Mensaje al asistente"
        />

        {generando ? (
          <Button
            variant="outline"
            size="icon"
            onClick={onDetener}
            aria-label="Detener generación"
            className="shrink-0 border-destructive text-destructive hover:bg-destructive hover:text-destructive-foreground"
          >
            <Square className="size-4 fill-current" />
          </Button>
        ) : (
          <Button
            size="icon"
            disabled={!puedeEnviar}
            onClick={handleEnviar}
            aria-label="Enviar mensaje"
            className="shrink-0"
          >
            <ArrowUp className="size-4" />
          </Button>
        )}
      </div>
      <p className="mt-1 text-right text-[10px] text-muted-foreground/60">
        {texto.length}/2000
      </p>
    </div>
  );
}
