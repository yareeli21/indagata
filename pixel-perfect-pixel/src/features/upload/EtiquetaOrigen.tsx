import { Bot, FileSearch, Lock, Sparkles } from "lucide-react";
import type { OrigenMetadato } from "@/types";

const TEXTOS: Record<OrigenMetadato, { texto: string; icono: typeof Bot }> = {
  automatico: { texto: "Automático", icono: Lock },
  archivo: { texto: "Leído del archivo", icono: FileSearch },
  inferido: { texto: "Inferido del contenido", icono: Sparkles },
  llm: { texto: "Sugerido por IA", icono: Bot },
  aprobado: { texto: "Aprobado", icono: Lock },
};

interface EtiquetaOrigenProps {
  origen: OrigenMetadato | undefined;
}

/** Indica de dónde salió un valor propuesto, para que el autor sepa qué revisar. */
export function EtiquetaOrigen({ origen }: EtiquetaOrigenProps) {
  if (!origen) return null;
  const { texto, icono: Icono } = TEXTOS[origen];
  const destacado = origen === "llm" || origen === "inferido";
  return (
    <span
      className={
        destacado
          ? "inline-flex items-center gap-1 rounded-full bg-accent-soft px-2 py-0.5 text-xs font-medium text-accent-foreground"
          : "inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground"
      }
    >
      <Icono className="size-3" aria-hidden />
      {texto}
    </span>
  );
}
