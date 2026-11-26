import { useEffect, useRef, useState } from "react";
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
import { cargarModelo, getModelos } from "@/api/chat";
import type { ModeloChat, ModeloLLM } from "@/types";

// El modelo de embeddings (paraphrase-multilingual-mpnet) lee como máximo 128 tokens, ~500 caracteres en español
// (medido el 26 nov: ~4 caracteres por token). Lo que pasa de ahí se corta y no cuenta para buscar las fuentes.
const LARGO_AVISO = 400;
const LARGO_MAXIMO_BUSQUEDA = 500;

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
  // Catálogo del servidor (26 nov): los cuatro modelos con su descripción; el predeterminado va como «servidor».
  const [modelos, setModelos] = useState<ModeloChat[]>([]);
  useEffect(() => {
    getModelos()
      .then(setModelos)
      .catch(() => setModelos([]));
  }, []);
  const valorDe = (m: ModeloChat): ModeloLLM => (m.predeterminado ? "servidor" : m.id);
  const elegido = modelos.find((m) => valorDe(m) === modelo);
  // Un modelo guardado que ya no está en el catálogo (o no está instalado) vuelve al del servidor.
  useEffect(() => {
    if (modelos.length && (!elegido || !elegido.instalado) && modelo !== "servidor")
      onCambiarModelo("servidor");
  }, [modelos, elegido, modelo, onCambiarModelo]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Carga del modelo elegido (26 nov): sin ella, la primera pregunta esperaba la carga y gemma4 llegaba al tiempo
  // límite. Mientras carga no se envía.
  const [cargando, setCargando] = useState<"" | "cargando" | "error">("");
  async function cambiarModelo(v: ModeloLLM) {
    onCambiarModelo(v);
    setCargando("cargando");
    const ok = await cargarModelo(v).catch(() => false);
    setCargando(ok ? "" : "error");
  }

  const puedeEnviar = texto.trim().length > 0 && !generando && cargando !== "cargando";

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
          onValueChange={(v) => void cambiarModelo(v as ModeloLLM)}
          disabled={generando || cargando === "cargando"}
        >
          <SelectTrigger className="h-7 w-60 text-xs" title={elegido?.descripcion}>
            <SelectValue placeholder="Modelo del servidor">
              {elegido ? elegido.etiqueta : "Modelo del servidor"}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            {modelos.length === 0 && (
              <SelectItem value="servidor" className="text-xs">
                Modelo del servidor
              </SelectItem>
            )}
            {modelos.map((m) => (
              <SelectItem key={m.id} value={valorDe(m)} disabled={!m.instalado} className="text-xs">
                <span className="flex flex-col">
                  <span>
                    {m.etiqueta}
                    {m.predeterminado ? " (predeterminado)" : ""}
                    {!m.instalado ? " · no instalado" : ""}
                  </span>
                  {m.descripcion && (
                    <span className="text-[11px] text-muted-foreground">{m.descripcion}</span>
                  )}
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {cargando === "cargando" && (
          <span className="text-xs text-muted-foreground" role="status">
            Cargando modelo…
          </span>
        )}
        {cargando === "error" && (
          <span className="text-xs text-destructive" role="status">
            No se pudo cargar el modelo; la primera respuesta puede tardar.
          </span>
        )}
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
      <div className="mt-1 flex items-start justify-between gap-3 text-xs">
        <p
          role="status"
          className={
            texto.length > LARGO_MAXIMO_BUSQUEDA ? "text-destructive" : "text-muted-foreground"
          }
        >
          {texto.length > LARGO_MAXIMO_BUSQUEDA
            ? "Pregunta demasiado larga: el buscador solo lee unos 500 caracteres y el final no se usará para encontrar las fuentes. Divídela en preguntas más cortas."
            : texto.length > LARGO_AVISO
              ? "Pregunta larga: el buscador lee unos 500 caracteres. Las preguntas cortas y concretas encuentran mejor las fuentes."
              : ""}
        </p>
        <p
          className={
            texto.length > LARGO_MAXIMO_BUSQUEDA
              ? "shrink-0 text-destructive"
              : "shrink-0 text-muted-foreground/60"
          }
        >
          {texto.length}/{LARGO_MAXIMO_BUSQUEDA}
        </p>
      </div>
    </div>
  );
}
