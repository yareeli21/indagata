import type { ReactNode } from "react";
import { BookOpen, CircleHelp, GraduationCap } from "lucide-react";
import { cn } from "@/lib/utils";
import type { FuenteChat, Mensaje, ReferenciaChat } from "@/types";

interface BurbujaMensajeProps {
  mensaje: Mensaje;
}

// Citas tal como las escribe el modelo: [Fuente 2], (Fuentes 3 y 5), [Fuente 1, 3 y 6],
// [Fuente 5 y Fuente 6]. Cada número es el de una tarjeta de fuente.
const RE_CITA = /[[(]\s*Fuentes?\s+(\d+(?:\s*(?:,|y|e)\s*(?:Fuente\s+)?\d+)*)\s*[\])]/gi;

function idTarjeta(mensajeId: string, numero: number): string {
  return `fuente-${mensajeId}-${numero}`;
}

export function BurbujaMensaje({ mensaje }: BurbujaMensajeProps) {
  const esUsuario = mensaje.rol === "usuario";

  return (
    <div className={cn("flex w-full flex-col gap-3", esUsuario ? "items-end" : "items-start")}>
      {/* Burbuja */}
      <div
        aria-live={!esUsuario && mensaje.generando ? "polite" : undefined}
        className={cn(
          "max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-card",
          esUsuario
            ? "rounded-br-md bg-primary text-primary-foreground"
            : "rounded-bl-md border border-border bg-card text-card-foreground",
        )}
      >
        <p className="whitespace-pre-wrap break-words">
          {esUsuario ? mensaje.contenido : conCitas(mensaje.contenido, mensaje.id, mensaje.fuentes)}
        </p>
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
            {mensaje.fuentes.map((f, i) => (
              <TarjetaFuente
                key={f.instrumentoId}
                fuente={f}
                numero={f.numero ?? i + 1}
                id={idTarjeta(mensaje.id, f.numero ?? i + 1)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Glosario metodológico o ayuda de la plataforma que respaldan la respuesta */}
      {!esUsuario &&
        !mensaje.generando &&
        mensaje.referencias &&
        mensaje.referencias.length > 0 && (
          <div className="flex w-full max-w-[80%] flex-col gap-2">
            {mensaje.referencias.map((r) => (
              <TarjetaReferencia key={`${r.tipo}-${r.titulo}`} referencia={r} />
            ))}
          </div>
        )}
    </div>
  );
}

function TarjetaReferencia({ referencia }: { referencia: ReferenciaChat }) {
  const esAyuda = referencia.tipo === "ayuda";
  const Icono = esAyuda ? CircleHelp : GraduationCap;
  return (
    <details className="rounded-xl border border-border bg-card px-3 py-2 text-xs">
      <summary className="flex cursor-pointer items-center gap-1.5 font-medium text-card-foreground">
        <Icono className="size-3.5 shrink-0 text-primary" aria-hidden />
        {esAyuda ? "Ayuda" : "Glosario"}: {referencia.titulo}
      </summary>
      <p className="mt-1.5 leading-relaxed text-muted-foreground">{referencia.texto}</p>
    </details>
  );
}

/** Texto de la respuesta con cada cita convertida en una marca numerada que
 *  coincide con su tarjeta de fuente. */
function conCitas(texto: string, mensajeId: string, fuentes?: FuenteChat[]): ReactNode[] {
  const partes: ReactNode[] = [];
  let desde = 0;
  for (const m of texto.matchAll(RE_CITA)) {
    const inicio = m.index ?? 0;
    if (inicio > desde) partes.push(texto.slice(desde, inicio));
    const numeros = [...new Set((m[1] ?? "").match(/\d+/g)?.map(Number) ?? [])];
    partes.push(
      <span key={`cita-${inicio}`} className="whitespace-nowrap">
        {numeros.map((n) => (
          <MarcaCita
            key={n}
            numero={n}
            fuente={fuentes?.find((f) => f.numero === n)}
            idDestino={idTarjeta(mensajeId, n)}
          />
        ))}
      </span>,
    );
    desde = inicio + m[0].length;
  }
  if (desde < texto.length) partes.push(texto.slice(desde));
  return partes;
}

function MarcaCita({
  numero,
  fuente,
  idDestino,
}: {
  numero: number;
  fuente: FuenteChat | undefined;
  idDestino: string;
}) {
  return (
    <button
      type="button"
      title={fuente ? fuente.titulo : `Fuente ${numero}`}
      aria-label={fuente ? `Fuente ${numero}: ${fuente.titulo}` : `Fuente ${numero}`}
      onClick={() =>
        document.getElementById(idDestino)?.scrollIntoView({ behavior: "smooth", block: "nearest" })
      }
      className="mx-0.5 inline-flex h-4 min-w-4 items-center justify-center rounded bg-primary/10 px-1 align-super text-[10px] font-semibold text-primary hover:bg-primary/20"
    >
      {numero}
    </button>
  );
}

function TarjetaFuente({
  fuente: f,
  numero,
  id,
}: {
  fuente: FuenteChat;
  numero: number;
  id: string;
}) {
  return (
    <div id={id} className="space-y-2 rounded-2xl border border-border bg-card p-3 shadow-card">
      {/* Número + título + tipo */}
      <div className="flex items-start gap-2">
        <span className="mt-0.5 inline-flex size-5 shrink-0 items-center justify-center rounded bg-primary/10 text-xs font-semibold text-primary">
          {numero}
        </span>
        <div className="min-w-0 space-y-0.5">
          <p className="text-xs font-semibold leading-snug text-foreground line-clamp-2">
            {f.titulo}
          </p>
          <p className="text-xs text-muted-foreground">
            {f.tipo} · {f.investigador}
          </p>
        </div>
      </div>

      {/* KPIs */}
      {f.kpis.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {f.kpis.map((k) => (
            <span key={k} className="rounded-md border px-1.5 py-0.5 text-xs text-muted-foreground">
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
