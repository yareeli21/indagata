import { useCallback, useEffect, useState } from "react";
import { ChevronLeft, ExternalLink, Newspaper, RefreshCw, WifiOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getNoticias } from "@/api/kpis";
import { cn } from "@/lib/utils";
import type { Noticia } from "@/types";

function formatearFechaCorta(iso: string): string {
  if (!iso) return "";
  return new Date(`${iso}T12:00:00`).toLocaleDateString("es-MX", {
    day: "numeric",
    month: "short",
  });
}

/** Noticias actuales de educación e investigación, con enlace a la nota original. */
export function PanelNoticias() {
  const [abierto, setAbierto] = useState(true);
  const [noticias, setNoticias] = useState<Noticia[]>([]);
  const [aviso, setAviso] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);

  const cargar = useCallback(async (actualizar = false) => {
    setCargando(true);
    const datos = await getNoticias(actualizar);
    setNoticias(datos.noticias.slice(0, 8));
    setAviso(datos.aviso);
    setCargando(false);
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

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
        <ChevronLeft className={cn("size-3.5 transition-transform", !abierto && "rotate-180")} />
      </Button>

      {abierto && (
        <div className="flex flex-1 flex-col overflow-hidden">
          {/* Cabecera */}
          <div className="flex items-center gap-2 border-b px-4 py-3">
            <Newspaper className="size-4 text-muted-foreground" />
            <h2 className="flex-1 text-sm font-semibold">Educación e investigación</h2>
            <Button
              variant="ghost"
              size="icon"
              className="size-7"
              onClick={() => void cargar(true)}
              disabled={cargando}
              aria-label="Actualizar noticias"
            >
              <RefreshCw className={cn("size-3.5", cargando && "animate-spin")} />
            </Button>
          </div>

          {aviso && (
            <p className="flex items-start gap-2 border-b px-4 py-2 text-xs text-muted-foreground">
              <WifiOff className="mt-0.5 size-3.5 shrink-0" aria-hidden />
              {aviso}
            </p>
          )}

          {/* Tarjetas */}
          <ul className="flex-1 overflow-auto divide-y">
            {cargando && noticias.length === 0 && (
              <li className="px-4 py-3 text-xs text-muted-foreground">Cargando noticias…</li>
            )}
            {noticias.map((n) => (
              <li key={n.id} className="transition-colors hover:bg-muted/30">
                <a
                  href={n.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block space-y-1 px-4 py-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <p className="line-clamp-2 text-xs font-semibold leading-snug text-foreground">
                    {n.titulo}
                    <ExternalLink
                      className="ml-1 inline size-3 text-muted-foreground"
                      aria-hidden
                    />
                  </p>
                  {n.resumen && (
                    <p className="line-clamp-2 text-xs text-muted-foreground">{n.resumen}</p>
                  )}
                  <p className="text-xs text-muted-foreground/70">
                    {n.medio}
                    {n.fecha ? ` · ${formatearFechaCorta(n.fecha)}` : ""}
                  </p>
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Estado colapsado: icono vertical */}
      {!abierto && (
        <div className="flex flex-1 flex-col items-center justify-center">
          <span className="rotate-90 whitespace-nowrap text-xs font-medium tracking-widest text-muted-foreground/50 uppercase select-none">
            Noticias
          </span>
        </div>
      )}
    </aside>
  );
}
