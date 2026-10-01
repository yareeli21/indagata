import { BookOpen } from "lucide-react";
import { cn } from "@/lib/utils";
import type { FuenteChat, Mensaje } from "@/types";

interface BurbujaMensajeProps {
  mensaje: Mensaje;
}

export function BurbujaMensaje({ mensaje }: BurbujaMensajeProps) {
  const esUsuario = mensaje.rol === "usuario";

  return (
    <div
      className={cn(
        "flex w-full flex-col gap-3",
        esUsuario ? "items-end" : "items-start",
      )}
    >
      {/* Burbuja */}
      <div
        className={cn(
          "max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm",
          esUsuario
            ? "rounded-br-sm bg-primary text-primary-foreground"
            : "rounded-bl-sm border bg-card text-card-foreground",
        )}
      >
        <p className="whitespace-pre-wrap break-words">{mensaje.contenido}</p>
        {/* Cursor parpadeante mientras se genera */}
        {mensaje.generando && (
          <span
            aria-label="Generando respuesta"
            className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-current align-middle"
          />
        )}
      </div>

      {/* Tarjetas de fuentes (solo asistente, cuando terminó de generar) */}
      {!esUsuario && !mensaje.generando && mensaje.fuentes && mensaje.fuentes.length > 0 && (
        <div className="flex w-full max-w-[80%] flex-col gap-2">
          <p className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
            <BookOpen className="size-3.5" />
            Fuentes
          </p>
          <div className="grid gap-2 sm:grid-cols-2">
            {mensaje.fuentes.map((f) => (
              <TarjetaFuente key={f.instrumentoId} fuente={f} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function TarjetaFuente({ fuente: f }: { fuente: FuenteChat }) {
  return (
    <div className="rounded-xl border bg-card p-3 shadow-sm space-y-2">
      {/* Título + tipo */}
      <div className="space-y-0.5">
        <p className="text-xs font-semibold leading-snug text-foreground line-clamp-2">
          {f.titulo}
        </p>
        <p className="text-xs text-muted-foreground">
          {f.tipo} · {f.investigador}
        </p>
      </div>

      {/* KPIs */}
      {f.kpis.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {f.kpis.map((k) => (
            <span
              key={k}
              className="rounded-md border px-1.5 py-0.5 text-[10px] text-muted-foreground"
            >
              {k}
            </span>
          ))}
        </div>
      )}

      {/* Fragmento */}
      <p className="text-xs italic text-muted-foreground line-clamp-3 border-l-2 border-primary/30 pl-2">
        "{f.fragmento}"
      </p>
    </div>
  );
}
