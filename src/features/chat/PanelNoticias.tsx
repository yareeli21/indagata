import { useEffect, useState } from "react";
import { ChevronLeft, Newspaper } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getNoticias } from "@/api/kpis";
import { cn } from "@/lib/utils";
import type { Noticia } from "@/types";

function formatearFechaCorta(iso: string): string {
  return new Date(`${iso}T12:00:00`).toLocaleDateString("es-MX", {
    day: "numeric",
    month: "short",
  });
}

export function PanelNoticias() {
  const [abierto, setAbierto] = useState(true);
  const [noticias, setNoticias] = useState<Noticia[]>([]);

  useEffect(() => {
    getNoticias().then((data) => setNoticias(data.slice(0, 4)));
  }, []);

  return (
    <aside
      className={cn(
        "relative flex flex-col border-l bg-card transition-all duration-300",
        abierto ? "w-72 min-w-[18rem]" : "w-10 min-w-[2.5rem]",
      )}
    >
      {/* Botón toggle */}
      <Button
        variant="ghost"
        size="icon"
        onClick={() => setAbierto((v) => !v)}
        aria-label={abierto ? "Colapsar noticias" : "Expandir noticias"}
        className="absolute -left-3.5 top-4 z-10 size-7 rounded-full border bg-card shadow-sm"
      >
        <ChevronLeft
          className={cn("size-3.5 transition-transform", !abierto && "rotate-180")}
        />
      </Button>

      {abierto && (
        <div className="flex flex-1 flex-col overflow-hidden">
          {/* Cabecera */}
          <div className="flex items-center gap-2 border-b px-4 py-3">
            <Newspaper className="size-4 text-muted-foreground" />
            <h2 className="text-sm font-semibold">Noticias de educación en México</h2>
          </div>

          {/* Tarjetas */}
          <ul className="flex-1 overflow-auto divide-y">
            {noticias.map((n) => (
              <li key={n.id} className="px-4 py-3 space-y-1 hover:bg-muted/30 transition-colors">
                <p className="text-xs font-semibold leading-snug text-foreground line-clamp-2">
                  {n.titulo}
                </p>
                <p className="text-xs text-muted-foreground line-clamp-2">
                  {n.resumen}
                </p>
                <p className="text-[10px] text-muted-foreground/70">
                  INDAGATA · {formatearFechaCorta(n.fecha)}
                </p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Estado colapsado: icono vertical */}
      {!abierto && (
        <div className="flex flex-1 flex-col items-center justify-center">
          <span className="rotate-90 whitespace-nowrap text-[10px] font-medium tracking-widest text-muted-foreground/50 uppercase select-none">
            Noticias
          </span>
        </div>
      )}
    </aside>
  );
}
