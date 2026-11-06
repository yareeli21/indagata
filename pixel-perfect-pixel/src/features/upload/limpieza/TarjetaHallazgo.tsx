import { useState } from "react";
import { AlertCircle, MapPin } from "lucide-react";
import { cn } from "@/lib/utils";
import type { HallazgoLimpieza } from "@/types";
import { OpcionesDecision } from "./OpcionesDecision";
import { TablaUbicacion, type CeldaUbicacion } from "./TablaUbicacion";
import { ETIQUETA_TIPO } from "./textos";

interface TarjetaHallazgoProps {
  hallazgo: HallazgoLimpieza;
  onElegir: (opcion: string) => void;
}

/** Hallazgos sobre filas completas: texto antes de la lista de filas. */
const FILAS_HALLAZGO: Record<string, string> = {
  duplicados: "Filas repetidas",
  id_duplicado: "En las filas",
  linea_recta: "Filas",
  encuestados_incompletos: "Filas",
  id_parecido: "En las filas",
};

function lista(valor: unknown): string[] {
  return Array.isArray(valor) ? valor.map(String) : [];
}

interface GrupoDimension {
  nombre: string;
  etiquetas: string[];
  alfa: number;
}

function grupos(valor: unknown): GrupoDimension[] {
  return Array.isArray(valor)
    ? valor.filter(
        (g): g is GrupoDimension =>
          typeof g === "object" && g !== null && Array.isArray((g as GrupoDimension).etiquetas),
      )
    : [];
}

/** Una decisión de la fase asistida: qué encontramos, por qué y qué hacer. */
export function TarjetaHallazgo({ hallazgo: h, onElegir }: TarjetaHallazgoProps) {
  const [verDonde, setVerDonde] = useState(false);
  const ubicacion = Array.isArray(h.detalle["ubicacion"])
    ? (h.detalle["ubicacion"] as CeldaUbicacion[])
    : [];
  const totalUbicacion =
    typeof h.detalle["total"] === "number" ? h.detalle["total"] : ubicacion.length;
  const valor = h.decision ?? h.sugerida;
  const pendiente = h.obligatoria && h.decision === null;
  const ejemplos = lista(h.detalle["ejemplos"]);
  const fuera = lista(h.detalle["valores"]);
  const filas = lista(h.detalle["filas"]);
  const orden = lista(h.detalle["orden_propuesto"]);
  const tipo = typeof h.detalle["tipo"] === "string" ? ETIQUETA_TIPO[h.detalle["tipo"]] : undefined;
  const pctNulos = typeof h.detalle["pct_nulos"] === "number" ? h.detalle["pct_nulos"] : null;
  // En entrevistas los ejemplos son frases: se muestran como citas, no como valores.
  const comoCitas = [
    "rol_hablante",
    "sin_hablantes",
    "ruido_residual",
    "segmentacion_inferida",
    "anotaciones_transcriptor",
    "muletillas",
  ].includes(h.tipo);
  const pctPreguntas =
    typeof h.detalle["pct_preguntas"] === "number" ? h.detalle["pct_preguntas"] : null;

  return (
    <article
      className={cn(
        "space-y-3 rounded-2xl border bg-card p-4 shadow-card sm:p-5",
        pendiente ? "border-accent ring-2 ring-accent/30" : "border-border",
      )}
    >
      <header className="space-y-1">
        {pendiente && (
          <p className="inline-flex items-center gap-1.5 rounded-full bg-accent-soft px-2.5 py-0.5 text-xs font-bold text-accent-strong">
            <AlertCircle className="size-3.5" aria-hidden /> Requiere tu decisión
          </p>
        )}
        <h4 className="font-display text-base font-bold leading-snug text-foreground">
          {h.titulo}
        </h4>
        <p className="text-sm leading-relaxed text-muted-foreground">{h.descripcion}</p>
      </header>

      {comoCitas && ejemplos.length > 0 && (
        <ul className="space-y-1.5">
          {ejemplos.map((e) => (
            <li
              key={e}
              className="border-l-2 border-primary/30 pl-3 text-sm italic text-foreground"
            >
              «{e}»
            </li>
          ))}
        </ul>
      )}
      {pctPreguntas !== null && (
        <p className="text-xs text-muted-foreground">
          Hace preguntas en el{" "}
          <strong className="text-foreground">{Math.round(pctPreguntas * 100)} %</strong> de sus
          turnos.
        </p>
      )}
      {!comoCitas &&
        (ejemplos.length > 0 || tipo || pctNulos !== null) &&
        h.tipo !== "duplicados" && (
          <dl className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-foreground">
            {tipo && (
              <div className="flex gap-1">
                <dt>Tipo detectado:</dt>
                <dd className="font-semibold text-foreground">{tipo}</dd>
              </div>
            )}
            {pctNulos !== null && pctNulos > 0 && (
              <div className="flex gap-1">
                <dt>Vacíos:</dt>
                <dd className="font-semibold text-foreground">{Math.round(pctNulos * 100)} %</dd>
              </div>
            )}
            {ejemplos.length > 0 && (
              <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                <dt>Ejemplos:</dt>
                {ejemplos.map((e) => (
                  <dd
                    key={e}
                    className="max-w-[16rem] truncate rounded-md bg-muted px-1.5 py-0.5 font-mono text-foreground"
                  >
                    {e}
                  </dd>
                ))}
              </div>
            )}
          </dl>
        )}

      {fuera.length > 0 && (
        <p className="text-sm text-foreground">
          Valores:{" "}
          <span className="font-mono font-semibold text-destructive">{fuera.join(", ")}</span>
          {filas.length > 0 && (
            <span className="text-muted-foreground"> · filas {filas.join(", ")}</span>
          )}
        </p>
      )}
      {FILAS_HALLAZGO[h.tipo] && filas.length > 0 && (
        <p className="text-sm text-muted-foreground">
          {FILAS_HALLAZGO[h.tipo]}: {filas.join(", ")}
          {typeof h.detalle["total"] === "number" && h.detalle["total"] > filas.length && "…"}
        </p>
      )}
      {orden.length > 0 && (
        <ol className="flex flex-wrap gap-2 text-sm" aria-label="Orden propuesto, de menor a mayor">
          {orden.map((o, i) => (
            <li
              key={o}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-primary-soft/50 px-2 py-1"
            >
              <span className="font-bold tabular-nums text-primary">{i + 1}</span> {o}
            </li>
          ))}
        </ol>
      )}

      {h.tipo === "dimensiones_sugeridas" && (
        <ul className="grid gap-2 sm:grid-cols-2" aria-label="Dimensiones sugeridas">
          {grupos(h.detalle["grupos"]).map((g) => (
            <li key={g.nombre} className="rounded-xl border border-border bg-muted/40 p-3 text-sm">
              <p className="font-semibold text-foreground">
                {g.nombre}{" "}
                <span className="font-normal text-muted-foreground">
                  · {g.etiquetas.length} ítems · α = {g.alfa.toFixed(2)}
                </span>
              </p>
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                {g.etiquetas.join(" · ")}
              </p>
            </li>
          ))}
        </ul>
      )}

      {ubicacion.length > 0 && (
        <div className="space-y-2">
          <button
            type="button"
            aria-expanded={verDonde}
            onClick={() => setVerDonde((v) => !v)}
            className="inline-flex items-center gap-1.5 text-sm font-semibold text-primary underline-offset-2 hover:underline"
          >
            <MapPin className="size-4" aria-hidden />
            {verDonde ? "Ocultar dónde" : `Ver dónde (${totalUbicacion})`}
          </button>
          {verDonde && <TablaUbicacion celdas={ubicacion} total={totalUbicacion} />}
        </div>
      )}

      <OpcionesDecision
        etiqueta={h.titulo}
        opciones={h.opciones}
        sugerida={h.sugerida}
        valor={valor}
        onElegir={onElegir}
      />
    </article>
  );
}
