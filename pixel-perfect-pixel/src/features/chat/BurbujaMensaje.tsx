import type { ReactNode } from "react";
import {
  BookOpen,
  CircleHelp,
  ExternalLink,
  GraduationCap,
  History,
  Landmark,
  Timer,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { FuenteChat, Mensaje, ReferenciaChat } from "@/types";
import { PanelMetricas } from "./PanelMetricas";

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
        {esUsuario ? (
          <p className="whitespace-pre-wrap break-words">{mensaje.contenido}</p>
        ) : (
          <ContenidoAsistente
            texto={mensaje.contenido}
            mensajeId={mensaje.id}
            fuentes={mensaje.fuentes}
          />
        )}
        {/* Cursor parpadeante mientras se genera */}
        {mensaje.generando && (
          <span
            aria-label="Generando respuesta"
            className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-current align-middle"
          />
        )}
      </div>

      {!esUsuario && !mensaje.generando && !mensaje.enCache && mensaje.latenciaMs != null && (
        <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Timer className="size-3.5" aria-hidden />
          Respondió en {(mensaje.latenciaMs / 1000).toFixed(1)} s
        </p>
      )}

      {!esUsuario && !mensaje.generando && mensaje.enCache && (
        <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <History className="size-3.5" aria-hidden />
          Respuesta guardada: ya se había respondido esta misma pregunta con los mismos datos.
        </p>
      )}

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

      {/* Métricas automáticas (fidelidad, relevancia, precisión del contexto) */}
      {!esUsuario && !mensaje.generando && mensaje.consultaId != null && (
        <PanelMetricas consultaId={mensaje.consultaId} />
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

const REFERENCIA = {
  ayuda: { icono: CircleHelp, etiqueta: "Ayuda" },
  glosario: { icono: GraduationCap, etiqueta: "Glosario" },
  fuente_kpi: { icono: Landmark, etiqueta: "Fuente del KPI" },
} as const;

function TarjetaReferencia({ referencia }: { referencia: ReferenciaChat }) {
  const { icono: Icono, etiqueta } = REFERENCIA[referencia.tipo] ?? REFERENCIA.glosario;
  return (
    <details className="rounded-xl border border-border bg-card px-3 py-2 text-xs">
      <summary className="flex cursor-pointer items-center gap-1.5 font-medium text-card-foreground">
        <Icono className="size-3.5 shrink-0 text-primary" aria-hidden />
        {etiqueta}: {referencia.titulo}
      </summary>
      <p className="mt-1.5 leading-relaxed text-muted-foreground">{referencia.texto}</p>
      {referencia.url && (
        <a
          href={referencia.url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-1 inline-flex items-center gap-1 font-medium text-primary underline-offset-2 hover:underline"
        >
          Abrir la fuente <ExternalLink className="size-3" aria-hidden />
        </a>
      )}
    </details>
  );
}

/** Texto de la respuesta con cada cita convertida en una marca numerada que
 *  coincide con su tarjeta de fuente. */
type Bloque =
  | { tipo: "texto"; texto: string }
  | { tipo: "titulo"; texto: string }
  | { tipo: "tabla"; columnas: string[]; filas: string[][] };

function celdas(linea: string): string[] {
  return linea
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((c) => c.trim());
}

/**
 * Divide la respuesta en texto, títulos («**Respuestas interpretadas [Fuente 1]**») y tablas en Markdown: las
 * respuestas con respondentes traen la tabla calculada tal cual, debajo de la redacción del modelo.
 */
function bloques(texto: string): Bloque[] {
  const salida: Bloque[] = [];
  const lineas = texto.split("\n");
  let i = 0;
  while (i < lineas.length) {
    const linea = lineas[i] ?? "";
    if (linea.trim().startsWith("|") && (lineas[i + 1] ?? "").trim().startsWith("|---")) {
      const columnas = celdas(linea);
      const filas: string[][] = [];
      i += 2;
      while (i < lineas.length && (lineas[i] ?? "").trim().startsWith("|")) {
        filas.push(celdas(lineas[i] ?? ""));
        i += 1;
      }
      salida.push({ tipo: "tabla", columnas, filas });
      continue;
    }
    const titulo = /^\*\*(.+)\*\*$/.exec(linea.trim());
    if (titulo?.[1]) {
      salida.push({ tipo: "titulo", texto: titulo[1] });
    } else {
      const ultimo = salida[salida.length - 1];
      if (ultimo?.tipo === "texto") ultimo.texto += `\n${linea}`;
      else salida.push({ tipo: "texto", texto: linea });
    }
    i += 1;
  }
  return salida.filter((b) => b.tipo !== "texto" || b.texto.trim());
}

function ContenidoAsistente({
  texto,
  mensajeId,
  fuentes,
}: {
  texto: string;
  mensajeId: string;
  fuentes?: FuenteChat[] | undefined;
}) {
  return (
    <div className="space-y-3">
      {bloques(texto).map((b, n) => {
        if (b.tipo === "titulo") {
          return (
            <p key={n} className="font-semibold text-foreground">
              {conCitas(b.texto, mensajeId, fuentes)}
            </p>
          );
        }
        if (b.tipo === "tabla") {
          return (
            <div key={n} className="max-h-96 overflow-auto rounded-xl border border-border">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-muted text-left text-muted-foreground">
                  <tr>
                    {b.columnas.map((c, j) => (
                      <th key={j} className="px-2 py-1.5 font-semibold">
                        {c}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {b.filas.map((fila, j) => (
                    <tr key={j} className="border-t border-border/60 align-top">
                      {fila.map((c, k) => (
                        <td key={k} className={cn("px-2 py-1", k === 0 && "font-medium")}>
                          {c}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }
        return (
          <p key={n} className="whitespace-pre-wrap break-words">
            {conCitas(b.texto, mensajeId, fuentes)}
          </p>
        );
      })}
    </div>
  );
}

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
