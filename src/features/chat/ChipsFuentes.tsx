import { Lock } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Instrumento } from "@/types";

interface ChipsFuentesProps {
  instrumentos: Instrumento[];
  miId: string;
}

export function ChipsFuentes({ instrumentos, miId }: ChipsFuentesProps) {
  if (instrumentos.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1.5 px-4 pb-2 pt-3">
      <span className="self-center text-xs font-medium text-muted-foreground">
        Fuentes:
      </span>
      {instrumentos.map((ins) => {
        const ajeno = ins.autorId !== miId;
        return (
          <span
            key={ins.id}
            title={ins.titulo}
            className={cn(
              "inline-flex max-w-[180px] items-center gap-1 truncate rounded-full border px-2.5 py-0.5 text-xs font-medium",
              ajeno
                ? "border-border bg-muted text-muted-foreground"
                : "border-primary/20 bg-primary/10 text-primary",
            )}
          >
            {ajeno && <Lock className="size-2.5 shrink-0" />}
            <span className="truncate">{ins.titulo}</span>
          </span>
        );
      })}
    </div>
  );
}
