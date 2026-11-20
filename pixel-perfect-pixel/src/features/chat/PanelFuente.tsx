import { useEffect, useRef, useState, type ReactNode } from "react";
import { ChevronDown, ChevronUp, FileText, LoaderCircle, Quote, X } from "lucide-react";
import { getDocumentoFuente } from "@/api/chat";
import { cn } from "@/lib/utils";
import type { FragmentoDocumento, FuenteChat, PasajeFuente } from "@/types";

/** Fuente abierta en el panel y la posición del pasaje elegido (null = el más parecido). */
export interface FuenteSeleccionada {
  fuente: FuenteChat;
  chunk: number | null;
}

/** Fragmentos del documento que se muestran antes y después del pasaje elegido. */
const RADIO = 2;

const ORIGEN: Record<string, string> = {
  documento: "Documento final vigente",
  json_tecnico: "Registro técnico del instrumento",
};

interface Tramo {
  titulo: string;
  tipo: string;
  origen: string;
  total: number;
  desde: number;
  hasta: number;
  fragmentos: FragmentoDocumento[];
}

/**
 * Trazabilidad de una fuente citada: barra lateral derecha que se abre junto al chat y lo angosta
 * (no lo tapa) con qué documento es, la parte exacta que se recuperó para responder y esa parte
 * dentro del documento, con lo que tiene antes y después. Va dentro de la fila del chat
 * (ChatPage); sin fuente seleccionada no ocupa espacio.
 */
export function PanelFuente({
  seleccion,
  onCerrar,
}: {
  seleccion: FuenteSeleccionada | null;
  onCerrar: () => void;
}) {
  // Escape cierra la barra (como hacía la hoja flotante).
  useEffect(() => {
    if (!seleccion) return;
    const alTeclear = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCerrar();
    };
    window.addEventListener("keydown", alTeclear);
    return () => window.removeEventListener("keydown", alTeclear);
  }, [seleccion, onCerrar]);

  if (!seleccion) return null;
  // Dos piezas con el mismo ancho: el espaciador ocupa su lugar en la fila del chat (lo angosta en vez de taparlo) y
  // la barra va fija a la derecha bajo el encabezado de la app (h-18 = 4.5rem). Fija y no `sticky`: la página entera
  // hace scroll con la conversación y el contenedor del chat tiene overflow-hidden, que anula `sticky`.
  const ancho = "w-full sm:w-[24rem] xl:w-[28rem]";
  return (
    <>
      <div aria-hidden className={cn("shrink-0", ancho)} />
      <aside
        aria-label="Fuente citada"
        className={cn(
          "fixed bottom-0 right-0 top-18 z-20 flex flex-col gap-4 overflow-hidden border-l border-border bg-background p-5 shadow-elevated animate-in slide-in-from-right-8 duration-300",
          ancho,
        )}
      >
        <button
          type="button"
          onClick={onCerrar}
          aria-label="Cerrar la fuente"
          className="absolute right-3 top-3 rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <X className="size-4" aria-hidden />
        </button>
        {/* La key reinicia el panel al abrir otra fuente u otro pasaje. */}
        <ContenidoFuente
          key={`${seleccion.fuente.instrumentoId}-${seleccion.fuente.numero}-${seleccion.chunk ?? "x"}`}
          seleccion={seleccion}
        />
      </aside>
    </>
  );
}

function ContenidoFuente({ seleccion }: { seleccion: FuenteSeleccionada }) {
  const { fuente } = seleccion;
  const pasajes = fuente.pasajes ?? [];
  const [elegido, setElegido] = useState<PasajeFuente | undefined>(
    pasajes.find((p) => p.chunkIndex === seleccion.chunk) ?? pasajes[0],
  );
  const centro = elegido?.chunkIndex ?? seleccion.chunk ?? 0;
  const usados = new Set(pasajes.map((p) => p.chunkIndex).filter((c): c is number => c != null));

  const [tramo, setTramo] = useState<Tramo | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const refElegido = useRef<HTMLElement | null>(null);
  const refDocumento = useRef<HTMLDivElement | null>(null);
  const desplazar = useRef(true);

  // El tramo del documento alrededor del pasaje elegido.
  useEffect(() => {
    let vigente = true;
    setCargando(true);
    setError(null);
    getDocumentoFuente(fuente.instrumentoId, Math.max(0, centro - RADIO), centro + RADIO + 1)
      .then((d) => {
        if (!vigente) return;
        desplazar.current = true;
        setTramo(d);
      })
      .catch((e: unknown) => {
        if (vigente) setError(e instanceof Error ? e.message : "No se pudo abrir el documento.");
      })
      .finally(() => {
        if (vigente) setCargando(false);
      });
    return () => {
      vigente = false;
    };
  }, [fuente.instrumentoId, centro]);

  useEffect(() => {
    if (!tramo || !desplazar.current) return;
    desplazar.current = false;
    // Centra el fragmento dentro de la caja del documento, sin mover el panel: la «parte usada» sigue a la vista.
    const caja = refDocumento.current;
    const fragmento = refElegido.current;
    if (caja && fragmento) {
      caja.scrollTop = fragmento.offsetTop - caja.clientHeight / 2 + fragmento.clientHeight / 2;
    }
  }, [tramo]);

  async function ampliar(direccion: "antes" | "despues") {
    if (!tramo) return;
    const paso = RADIO * 3;
    const desde = direccion === "antes" ? Math.max(0, tramo.desde - paso) : tramo.hasta;
    const hasta = direccion === "antes" ? tramo.desde : Math.min(tramo.total, tramo.hasta + paso);
    if (hasta <= desde) return;
    setCargando(true);
    try {
      const d = await getDocumentoFuente(fuente.instrumentoId, desde, hasta);
      setTramo((t) =>
        t
          ? {
              ...t,
              desde: Math.min(t.desde, d.desde),
              hasta: Math.max(t.hasta, d.hasta),
              fragmentos:
                direccion === "antes"
                  ? [...d.fragmentos, ...t.fragmentos]
                  : [...t.fragmentos, ...d.fragmentos],
            }
          : t,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo cargar el documento.");
    } finally {
      setCargando(false);
    }
  }

  return (
    <>
      {/* Qué documento es */}
      <header className="space-y-1 pr-6 text-left">
        <p className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
          <span className="inline-flex size-5 items-center justify-center rounded bg-primary/10 text-xs font-semibold text-primary">
            {fuente.numero}
          </span>
          Fuente citada
        </p>
        <h2 className="text-base font-semibold leading-snug text-foreground">{fuente.titulo}</h2>
        <p className="text-xs text-muted-foreground">
          {fuente.tipo}
          {fuente.investigador && ` · ${fuente.investigador}`}
          {fuente.similitud != null &&
            ` · similitud con tu pregunta ${Math.round(fuente.similitud * 100)}%`}
          {tramo && ` · ${ORIGEN[tramo.origen] ?? tramo.origen} (${tramo.total} fragmentos)`}
        </p>
      </header>

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto pr-1">
        {/* La parte exacta que se recuperó */}
        <section className="space-y-2">
          <h3 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            <Quote className="size-3.5" aria-hidden /> Parte usada para responder
          </h3>
          {elegido ? (
            <div className="rounded-xl border border-primary/40 bg-primary/5 p-3 text-xs">
              <p className="mb-1.5 font-semibold text-primary">
                {elegido.etiqueta}
                {elegido.chunkIndex != null && (
                  <span className="font-normal text-muted-foreground">
                    {" "}
                    · fragmento {elegido.chunkIndex + 1}
                  </span>
                )}
                {elegido.score != null && (
                  <span className="font-normal text-muted-foreground">
                    {" "}
                    · similitud con tu pregunta {Math.round(elegido.score * 100)}%
                  </span>
                )}
              </p>
              <p className="whitespace-pre-wrap break-words leading-relaxed text-card-foreground">
                {elegido.texto}
              </p>
            </div>
          ) : (
            <p className="rounded-xl border border-border bg-muted/40 p-3 text-xs text-muted-foreground">
              {fuente.fragmento}
            </p>
          )}

          {pasajes.length > 1 && (
            <div className="space-y-1">
              <p className="text-[11px] text-muted-foreground">
                Otras partes de este documento que se usaron:
              </p>
              <div className="flex flex-wrap gap-1.5">
                {pasajes.map((p, i) => (
                  <button
                    key={p.chunkIndex ?? `p-${i}`}
                    type="button"
                    onClick={() => setElegido(p)}
                    className={cn(
                      "rounded-full border px-2 py-0.5 text-[11px] font-medium",
                      p === elegido
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-primary/30 bg-primary/10 text-primary hover:bg-primary/20",
                    )}
                  >
                    {p.etiqueta}
                    {p.chunkIndex != null && ` · frag. ${p.chunkIndex + 1}`}
                    {p.score != null && ` · ${Math.round(p.score * 100)}%`}
                  </button>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* Esa parte dentro del documento */}
        <section className="space-y-2">
          <h3 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            <FileText className="size-3.5" aria-hidden /> En el documento
          </h3>
          {error && <p className="text-xs text-destructive">{error}</p>}
          {!tramo && cargando && (
            <p className="flex items-center gap-2 text-xs text-muted-foreground">
              <LoaderCircle className="size-3.5 animate-spin" aria-hidden /> Abriendo el documento…
            </p>
          )}
          {tramo && (
            <div
              ref={refDocumento}
              className="relative max-h-[45vh] space-y-1.5 overflow-y-auto rounded-xl border border-border bg-muted/30 p-1.5"
            >
              {tramo.desde > 0 && (
                <BotonAmpliar onClick={() => void ampliar("antes")} disabled={cargando}>
                  <ChevronUp className="size-3.5" aria-hidden /> Ver lo anterior ({tramo.desde})
                </BotonAmpliar>
              )}
              {tramo.fragmentos.map((f) => {
                const esElegido = f.chunkIndex === centro;
                const usado = usados.has(f.chunkIndex);
                return (
                  <article
                    key={f.chunkIndex}
                    ref={esElegido ? refElegido : undefined}
                    className={cn(
                      "rounded-lg border p-2.5 text-xs",
                      esElegido
                        ? "border-primary bg-primary/5 ring-2 ring-primary/30"
                        : usado
                          ? "border-primary/40 bg-card"
                          : "border-border bg-card text-muted-foreground",
                    )}
                  >
                    <p className="mb-1 flex flex-wrap items-center gap-1.5 font-medium text-muted-foreground">
                      {f.etiqueta}
                      <span className="font-normal">· fragmento {f.chunkIndex + 1}</span>
                      {usado && (
                        <span className="ml-auto rounded bg-primary/10 px-1.5 py-0.5 font-semibold text-primary">
                          Usado
                        </span>
                      )}
                    </p>
                    <p className="whitespace-pre-wrap break-words leading-relaxed">{f.texto}</p>
                  </article>
                );
              })}
              {tramo.hasta < tramo.total && (
                <BotonAmpliar onClick={() => void ampliar("despues")} disabled={cargando}>
                  <ChevronDown className="size-3.5" aria-hidden /> Ver lo siguiente (
                  {tramo.total - tramo.hasta})
                </BotonAmpliar>
              )}
            </div>
          )}
        </section>
      </div>
    </>
  );
}

function BotonAmpliar({
  children,
  onClick,
  disabled,
}: {
  children: ReactNode;
  onClick: () => void;
  disabled: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="flex w-full items-center justify-center gap-1 rounded-lg border border-dashed border-border py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted disabled:opacity-50"
    >
      {children}
    </button>
  );
}
