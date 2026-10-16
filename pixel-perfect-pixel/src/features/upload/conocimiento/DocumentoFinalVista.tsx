import { useState } from "react";
import {
  AlertTriangle,
  Braces,
  Download,
  FileCheck2,
  ListChecks,
  Loader2,
  Target,
} from "lucide-react";
import { getDocumentoJson } from "@/api/conocimiento";
import { Button } from "@/components/ui/button";
import type { DocumentoGenerado, KpiAsociado, PreguntaDoc } from "@/types";
import { JsonPreview } from "../JsonPreview";
import { Barra } from "../limpieza/estadistica/piezas";

// Documentos grandes: en pantalla se muestran todas las preguntas y solo los primeros
// respondentes/alumnos/entrevistas (con todas sus respuestas); el resto se descarga.
const MAX_JSON_VISIBLE = 250_000;
const PERSONAS_EN_PANTALLA = 5;
const LISTAS_PERSONAS = ["respondentes", "alumnos", "entrevistas"] as const;

function recortar(doc: Record<string, unknown>): { visible: unknown; recortado: boolean } {
  const visible: Record<string, unknown> = { ...doc };
  let recortado = false;
  for (const clave of LISTAS_PERSONAS) {
    const lista = doc[clave];
    if (Array.isArray(lista) && lista.length > PERSONAS_EN_PANTALLA) {
      visible[clave] = lista.slice(0, PERSONAS_EN_PANTALLA);
      recortado = true;
    }
  }
  return { visible, recortado };
}

type RespuestaMuestra = {
  pregunta?: string;
  significado?: string;
  texto?: string;
  estado: string;
  correcta?: boolean;
};

function MuestraPersonas({
  titulo,
  personas,
}: {
  titulo: string;
  personas: { id: string; respuestas: RespuestaMuestra[] }[];
}) {
  if (personas.length === 0) return null;
  return (
    <div className="space-y-2">
      <h4 className="font-display text-sm font-bold text-foreground">{titulo} (muestra)</h4>
      {personas.map((persona) => (
        <details key={persona.id} className="rounded-xl border border-border/70 px-3 py-2">
          <summary className="cursor-pointer text-sm font-semibold text-foreground">
            {persona.id} · {persona.respuestas.length} respuestas
          </summary>
          <ul className="mt-2 space-y-1.5">
            {persona.respuestas.map((r, i) => (
              <li key={i} className="text-sm">
                <p className="text-muted-foreground">{r.pregunta}</p>
                <p className="text-foreground">
                  {r.estado === "sin_respuesta" && !r.significado
                    ? "Sin respuesta"
                    : (r.significado ?? r.texto ?? "—")}
                  {r.correcta !== undefined && (r.correcta ? " ✓ correcta" : " ✗ incorrecta")}
                </p>
              </li>
            ))}
          </ul>
        </details>
      ))}
    </div>
  );
}

const ESTADO: Record<string, string> = {
  borrador: "Borrador (se publica al guardar)",
  vigente: "Vigente",
  reemplazado: "Reemplazado",
};

function Cifra({ etiqueta, valor }: { etiqueta: string; valor: number | string }) {
  return (
    <div className="rounded-xl border border-border bg-card px-3 py-2">
      <p className="text-xs font-semibold text-muted-foreground">{etiqueta}</p>
      <p className="font-display text-xl font-bold tabular-nums text-foreground">{valor}</p>
    </div>
  );
}

function ChipsKpi({ ids }: { ids: string[] }) {
  if (ids.length === 0) return null;
  return (
    <span className="flex flex-wrap gap-1">
      {ids.map((k) => (
        <span
          key={k}
          className="rounded-full bg-accent-soft px-2 py-0.5 text-xs font-semibold text-accent-strong"
        >
          {k}
        </span>
      ))}
    </span>
  );
}

function Pregunta({ p }: { p: PreguntaDoc }) {
  const dist = p.resumen?.distribucion ?? [];
  const total = p.resumen?.n_validas ?? 0;
  return (
    <li className="space-y-2 rounded-xl border border-border/70 px-3 py-2">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <p className="min-w-0 text-sm text-foreground">{p.texto}</p>
        <ChipsKpi ids={p.kpis_relacionados} />
      </div>
      {p.resumen && <p className="text-xs text-muted-foreground">{p.resumen.interpretacion}</p>}
      {dist.length > 0 && dist.length <= 8 && (
        <ul className="space-y-1">
          {dist.map((d) => (
            <Barra
              key={d.significado}
              etiqueta={d.significado}
              n={d.n}
              proporcion={total ? d.n / total : 0}
            />
          ))}
        </ul>
      )}
    </li>
  );
}

function Kpi({ k, texto }: { k: KpiAsociado; texto: (id: string) => string }) {
  return (
    <li className="space-y-1.5 rounded-xl border border-border/70 px-3 py-2">
      <p className="flex flex-wrap items-center gap-2 text-sm font-bold text-foreground">
        <span className="rounded-full bg-accent-soft px-2 py-0.5 text-xs text-accent-strong">
          {k.kpi_id}
        </span>
        {k.nombre}
        <span className="text-xs font-semibold tabular-nums text-muted-foreground">
          {Math.round(k.similitud * 100)} %
        </span>
      </p>
      <p className="text-sm text-foreground">{k.justificacion}</p>
      {k.evidencia.length > 0 && (
        <p className="text-xs text-muted-foreground">
          Lo sustentan: {k.evidencia.map((e) => `«${texto(e.pregunta_id)}»`).join(" · ")}
        </p>
      )}
    </li>
  );
}

/**
 * Documento final legible (paso «Guardar»): resúmenes con etiquetas, KPIs con su
 * justificación, avisos de lo que no se pudo interpretar y «Ver JSON».
 */
export function DocumentoFinalVista({ datos }: { datos: DocumentoGenerado }) {
  const [completo, setCompleto] = useState<Record<string, unknown> | null>(null);
  const [cargandoJson, setCargandoJson] = useState(false);
  const [verJson, setVerJson] = useState(false);
  const doc = datos.documento;
  const preguntas = doc.preguntas ?? [];
  const esEntrevista = doc.instrumento.tipo === "entrevista";
  const textoDe = (id: string) =>
    [...preguntas, ...(doc.reactivos ?? [])].find((p) => p.id === id)?.texto ?? id;
  const personas = doc.n_respondentes ?? doc.n_alumnos ?? doc.n_entrevistas ?? 0;
  const etiquetaPersonas =
    doc.n_alumnos != null ? "Alumnos" : esEntrevista ? "Entrevistas" : "Respondentes";

  async function alternarJson() {
    if (verJson) {
      setVerJson(false);
      return;
    }
    if (completo === null) {
      setCargandoJson(true);
      try {
        setCompleto(await getDocumentoJson(datos.id_crudo));
      } finally {
        setCargandoJson(false);
      }
    }
    setVerJson(true);
  }

  function descargar() {
    if (completo === null) return;
    const texto = JSON.stringify(completo, null, 2);
    const url = URL.createObjectURL(new Blob([texto], { type: "application/json" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `${doc.instrumento.id}_documento_final_v${datos.version}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section
      className="space-y-5 rounded-2xl border border-border bg-card p-4 sm:p-5"
      aria-labelledby="documento-final"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <h3
            id="documento-final"
            className="flex items-center gap-2 font-display text-base font-bold text-foreground"
          >
            <FileCheck2 className="size-5 text-primary" aria-hidden /> Documento final
          </h3>
          <p className="text-sm text-muted-foreground">
            Versión {datos.version} · {ESTADO[datos.estado] ?? datos.estado} · esquema{" "}
            {datos.esquema_version}. Es lo que consultará el asistente: cada respuesta interpretada,
            con resúmenes y KPIs.
          </p>
        </div>
        <div className="flex gap-2">
          {verJson && completo !== null && (
            <Button variant="outline" size="sm" onClick={descargar}>
              <Download className="size-4" aria-hidden /> Descargar
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={alternarJson}
            aria-pressed={verJson}
            disabled={cargandoJson}
          >
            {cargandoJson ? (
              <Loader2 className="size-4 animate-spin" aria-hidden />
            ) : (
              <Braces className="size-4" aria-hidden />
            )}
            {verJson ? "Ver legible" : "Ver JSON"}
          </Button>
        </div>
      </div>

      {verJson && completo !== null ? (
        (() => {
          const tamano = JSON.stringify(completo).length;
          if (tamano <= MAX_JSON_VISIBLE) return <JsonPreview datos={completo} />;
          const { visible, recortado } = recortar(completo);
          return (
            <div className="space-y-2">
              {recortado && (
                <p className="text-sm text-muted-foreground">
                  El documento completo pesa {Math.round(tamano / 1024)} KB: aquí ves todas las
                  preguntas y los primeros {PERSONAS_EN_PANTALLA} {etiquetaPersonas.toLowerCase()}{" "}
                  con todas sus respuestas. Descárgalo para verlo entero.
                </p>
              )}
              <JsonPreview datos={visible} />
            </div>
          );
        })()
      ) : (
        <>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <Cifra etiqueta={etiquetaPersonas} valor={personas} />
            <Cifra
              etiqueta={doc.reactivos ? "Reactivos" : "Preguntas"}
              valor={(doc.reactivos ?? preguntas).length}
            />
            {doc.secciones && <Cifra etiqueta="Secciones" valor={doc.secciones.length} />}
            <Cifra etiqueta="KPIs asociados" valor={doc.kpis_asociados.length} />
          </div>

          {datos.avisos.length > 0 && (
            <div className="space-y-1.5 rounded-xl border border-accent/30 bg-accent-soft/60 p-3 text-sm">
              <p className="flex items-center gap-2 font-semibold text-foreground">
                <AlertTriangle className="size-4 text-accent-strong" aria-hidden /> Avisos
              </p>
              <ul className="space-y-1 pl-6 text-foreground">
                {datos.avisos.map((a, i) => (
                  <li key={`${a.codigo}-${i}`} className="list-disc">
                    {a.mensaje}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {doc.kpis_asociados.length > 0 && (
            <div className="space-y-2">
              <h4 className="flex items-center gap-2 font-display text-sm font-bold text-foreground">
                <Target className="size-4 text-primary" aria-hidden /> KPIs asociados
              </h4>
              <ul className="space-y-2">
                {doc.kpis_asociados.map((k) => (
                  <Kpi key={k.kpi_id} k={k} texto={textoDe} />
                ))}
              </ul>
            </div>
          )}

          {esEntrevista && preguntas.length > 0 && (
            <div className="space-y-2">
              <h4 className="flex items-center gap-2 font-display text-sm font-bold text-foreground">
                <ListChecks className="size-4 text-primary" aria-hidden /> Preguntas del
                entrevistador
              </h4>
              <ol className="space-y-2">
                {preguntas.map((p, k) => (
                  <li
                    key={p.id}
                    className="flex flex-wrap items-start justify-between gap-2 rounded-xl border border-border/70 px-3 py-2"
                  >
                    <p className="min-w-0 text-sm text-foreground">
                      <span className="font-semibold">{k + 1}.</span> {p.texto}
                    </p>
                    <ChipsKpi ids={p.kpis_relacionados} />
                  </li>
                ))}
              </ol>
            </div>
          )}

          {(doc.secciones ?? []).map((s) => {
            const deSeccion = preguntas.filter((p) => p.seccion_id === s.id);
            const reactivos = (doc.reactivos ?? []).filter((r) => r.seccion_id === s.id);
            if (deSeccion.length === 0 && reactivos.length === 0) return null;
            return (
              <div key={s.id} className="space-y-2">
                <h4 className="flex items-center gap-2 font-display text-sm font-bold text-foreground">
                  <ListChecks className="size-4 text-primary" aria-hidden /> {s.nombre}
                </h4>
                <ol className="space-y-2">
                  {deSeccion.map((p) => (
                    <Pregunta key={p.id} p={p} />
                  ))}
                  {reactivos.map((r) => (
                    <li
                      key={r.id}
                      className="space-y-1 rounded-xl border border-border/70 px-3 py-2"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <p className="min-w-0 text-sm text-foreground">
                          <span className="font-semibold">{r.clave}.</span> {r.texto}
                        </p>
                        <ChipsKpi ids={r.kpis_relacionados} />
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {r.calificable === false
                          ? r.resumen.interpretacion
                          : `Respuesta correcta: ${r.respuesta_correcta}. ${r.resumen.interpretacion}`}
                      </p>
                    </li>
                  ))}
                </ol>
              </div>
            );
          })}

          <MuestraPersonas
            titulo={etiquetaPersonas}
            personas={doc.muestra_respondentes ?? doc.muestra_alumnos ?? []}
          />

          {(doc.muestra_entrevistas ?? []).length > 0 && (
            <div className="space-y-2">
              <h4 className="font-display text-sm font-bold text-foreground">
                Entrevistas (muestra)
              </h4>
              {(doc.muestra_entrevistas ?? []).map((e) => (
                <details
                  key={e.participante}
                  className="rounded-xl border border-border/70 px-3 py-2"
                >
                  <summary className="cursor-pointer text-sm font-semibold text-foreground">
                    {e.participante} · {e.intercambios.length} respuestas
                  </summary>
                  <ul className="mt-2 space-y-2">
                    {e.intercambios.map((i, k) => (
                      <li key={k} className="space-y-0.5 text-sm">
                        <p className="text-muted-foreground">{i.pregunta}</p>
                        <p className="text-foreground">{i.respuesta}</p>
                      </li>
                    ))}
                  </ul>
                </details>
              ))}
            </div>
          )}
        </>
      )}
    </section>
  );
}
