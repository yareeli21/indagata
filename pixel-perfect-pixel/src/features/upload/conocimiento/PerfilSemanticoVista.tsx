import { useState } from "react";
import { Braces, FileText, Info, ListChecks } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { FuentePerfil, KpiAsociado, PerfilGenerado } from "@/types";
import { JsonPreview } from "../JsonPreview";

const FUENTE: Record<FuentePerfil, string> = {
  original: "Preguntas y secciones tomadas del instrumento original.",
  encabezados: "Preguntas tomadas de los encabezados del archivo.",
  json_tecnico: "Preguntas tomadas de los metadatos anteriores a la limpieza.",
};

function Dato({ etiqueta, valor }: { etiqueta: string; valor: string }) {
  if (!valor) return null;
  return (
    <div className="min-w-0">
      <dt className="text-xs font-semibold text-muted-foreground">{etiqueta}</dt>
      <dd className="text-sm text-foreground">{valor}</dd>
    </div>
  );
}

function Etiquetas({ titulo, valores }: { titulo: string; valores: string[] }) {
  if (valores.length === 0) return null;
  return (
    <div className="space-y-1.5">
      <p className="text-xs font-semibold text-muted-foreground">{titulo}</p>
      <ul className="flex flex-wrap gap-1.5">
        {valores.map((v) => (
          <li
            key={v}
            className="rounded-full bg-primary-soft px-2.5 py-0.5 text-xs font-semibold text-primary-strong"
          >
            {v}
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Perfil semántico legible: lo que describe al instrumento y se usará para asociar
 * KPIs (sin métricas, respuestas ni datos técnicos), con la opción de ver su JSON.
 */
export function PerfilSemanticoVista({
  datos,
  conKpis = false,
}: {
  datos: PerfilGenerado;
  /** En «Guardar»: el perfil ya con los KPIs integrados (el JSON de la asociación de KPIs). */
  conKpis?: boolean;
}) {
  const [verJson, setVerJson] = useState(false);
  const { perfil } = datos;
  const kpis = perfil.kpis_asociados as unknown as KpiAsociado[];

  return (
    <section
      className="space-y-5 rounded-2xl border border-border bg-card p-4 sm:p-5"
      aria-labelledby="perfil-semantico"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <h3
            id="perfil-semantico"
            className="flex items-center gap-2 font-display text-base font-bold text-foreground"
          >
            <FileText className="size-5 text-primary" aria-hidden />{" "}
            {conKpis ? "Perfil para la asociación de KPIs" : "Perfil semántico"}
          </h3>
          <p className="text-sm text-muted-foreground">
            {conKpis
              ? "Solo los metadatos y las preguntas del instrumento original, ya con los KPIs que aceptaste."
              : "Es lo que se usará para sugerir los KPIs: describe el instrumento, sin respuestas ni métricas."}
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setVerJson((v) => !v)}
          aria-pressed={verJson}
        >
          <Braces className="size-4" aria-hidden /> {verJson ? "Ver legible" : "Ver JSON"}
        </Button>
      </div>

      {verJson ? (
        <JsonPreview datos={perfil} />
      ) : (
        <>
          <div className="space-y-3">
            <p className="font-display text-lg font-bold text-foreground">{perfil.titulo}</p>
            {perfil.objetivo && <p className="text-sm text-foreground">{perfil.objetivo}</p>}
            <dl className="grid gap-3 sm:grid-cols-2">
              <Dato etiqueta="Nivel educativo" valor={perfil.nivel_educativo} />
              <Dato etiqueta="Población" valor={perfil.poblacion} />
              <div className="sm:col-span-2">
                <Dato etiqueta="Contexto" valor={perfil.contexto} />
              </div>
            </dl>
            <Etiquetas titulo="Temas" valores={perfil.temas} />
            <Etiquetas titulo="Palabras clave" valores={perfil.palabras_clave} />
          </div>

          {conKpis && (
            <div className="space-y-1.5">
              <p className="text-xs font-semibold text-muted-foreground">KPIs asociados</p>
              {kpis.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No aceptaste KPIs para este instrumento.
                </p>
              ) : (
                <ul className="space-y-1.5">
                  {kpis.map((k) => (
                    <li
                      key={k.kpi_id}
                      className="rounded-xl border border-border/70 px-3 py-2 text-sm"
                    >
                      <p className="font-semibold text-foreground">
                        {k.kpi_id} · {k.nombre}
                      </p>
                      <p className="text-muted-foreground">{k.justificacion}</p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          <div className="space-y-2 rounded-xl bg-muted/50 p-3 text-sm">
            <p className="flex items-start gap-2 text-foreground">
              <Info className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />
              <span>
                {FUENTE[datos.fuente]} {datos.n_preguntas} pregunta
                {datos.n_preguntas === 1 ? "" : "s"} en {perfil.secciones.length}{" "}
                {perfil.secciones.length === 1 ? "sección" : "secciones"}.
              </span>
            </p>
            {datos.avisos.map((a) => (
              <p key={a.codigo} className="pl-6 text-muted-foreground">
                {a.mensaje}
              </p>
            ))}
          </div>

          <div className="space-y-4">
            {perfil.secciones.map((s) => (
              <div key={s.id} className="space-y-2">
                <h4 className="flex items-center gap-2 font-display text-sm font-bold text-foreground">
                  <ListChecks className="size-4 text-primary" aria-hidden /> {s.nombre}
                  <span className="text-xs font-semibold text-muted-foreground">
                    {s.preguntas.length}
                  </span>
                </h4>
                {s.descripcion && <p className="text-sm text-muted-foreground">{s.descripcion}</p>}
                <ol className="space-y-2">
                  {s.preguntas.map((q) => (
                    <li key={q.id} className="rounded-xl border border-border/70 px-3 py-2">
                      <p className="text-sm text-foreground">{q.texto}</p>
                      {q.opciones && q.opciones.length > 0 && (
                        <p className="mt-1 text-xs text-muted-foreground">
                          Opciones: {q.opciones.join(" · ")}
                        </p>
                      )}
                    </li>
                  ))}
                </ol>
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
