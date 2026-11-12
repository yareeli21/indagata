import { useState } from "react";
import { BarChart3, ChevronDown, Loader2 } from "lucide-react";
import { getMetricas } from "@/api/chat";
import { cn } from "@/lib/utils";
import type {
  EvaluacionFable as Evaluacion,
  FragmentoRecuperado,
  IndicadoresRespuesta,
  MetricaCitas,
  MetricaFundamentacion,
  MetricaRecuperacion,
} from "@/types";
import { EvaluacionFable } from "./EvaluacionFable";
import { IndicadoresSistema } from "./IndicadoresSistema";

/**
 * «Ver métricas» de una respuesta: se calculan sin modelo juez con lo que el chat registró (lo que recuperó la
 * búsqueda híbrida, la respuesta y sus fuentes), así que valen para cualquier instrumento.
 * GET /rag/consultas/{id}/metricas → indicadores.{recuperacion, fundamentacion, citas} (metricas_respuesta.py).
 * Debajo va la evaluación del juez Claude Fable 5.2 (juezFable: seis métricas RAGAS), que el servicio calcula sola
 * después de cada respuesta.
 */
export function VerMetricas({ consultaId }: { consultaId: number }) {
  const [abierto, setAbierto] = useState(false);
  const [ind, setInd] = useState<IndicadoresRespuesta | null>(null);
  const [fable, setFable] = useState<Evaluacion | null>(null);
  const [estado, setEstado] = useState<"inicial" | "cargando" | "listo" | "error">("inicial");

  function alternar() {
    const abrir = !abierto;
    setAbierto(abrir);
    if (abrir && estado !== "listo") {
      setEstado("cargando");
      getMetricas(consultaId)
        .then((m) => {
          setInd(m.indicadores);
          setFable(m.juezFable ?? null);
          setEstado("listo");
        })
        .catch(() => setEstado("error"));
    }
  }

  return (
    <div className="flex w-full max-w-[80%] flex-col gap-2">
      <button
        type="button"
        onClick={alternar}
        aria-expanded={abierto}
        className="flex items-center gap-1.5 self-start rounded-lg border border-border px-3 py-1 text-xs font-medium text-primary hover:bg-muted"
      >
        <BarChart3 className="size-3.5" aria-hidden />
        {abierto ? "Ocultar métricas" : "Ver métricas"}
        <ChevronDown className={cn("size-3.5 transition-transform", abierto && "rotate-180")} />
      </button>

      {abierto && (
        <div className="space-y-4 rounded-2xl border border-border bg-card p-4 text-xs shadow-card">
          {estado === "cargando" && (
            <p className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="size-3.5 animate-spin" aria-hidden /> Calculando métricas…
            </p>
          )}
          {estado === "error" && (
            <p className="text-destructive">No se pudieron leer las métricas de esta respuesta.</p>
          )}
          {estado === "listo" && !ind && (
            <p className="text-muted-foreground">Esta respuesta no tiene métricas registradas.</p>
          )}
          {estado === "listo" && ind && (
            <>
              {ind.recuperacion && <SeccionRecuperacion r={ind.recuperacion} />}
              {ind.respuesta === "redactada" ? (
                <SeccionRespuesta f={ind.fundamentacion ?? null} c={ind.citas ?? null} ind={ind} />
              ) : (
                <p className="rounded-lg bg-muted px-3 py-2 text-muted-foreground">
                  {ind.respuesta === "presentacion_fija"
                    ? "Esta respuesta es el resultado calculado sobre los datos, presentado tal cual: es fiel por construcción (no la redactó el modelo)."
                    : "Esta respuesta es un mensaje fijo del sistema; no se evalúa su fundamentación."}
                </p>
              )}
              <div className="border-t border-border pt-3">
                <EvaluacionFable consultaId={consultaId} inicial={fable} />
              </div>
              <div className="border-t border-border pt-3">
                <IndicadoresSistema ind={ind} />
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function pct(v: number | null | undefined): string {
  return v == null ? "—" : `${Math.round(v * 100)} %`;
}

const PASO: Record<FragmentoRecuperado["paso"], string> = {
  ambos: "significado y palabras",
  significado: "significado",
  palabras: "palabras",
  contexto: "contexto",
};

function SeccionRecuperacion({ r }: { r: MetricaRecuperacion }) {
  return (
    <section className="space-y-2">
      <Titulo
        texto="Recuperación"
        detalle={
          r.modo === "hibrida"
            ? "búsqueda híbrida: significado (embeddings) + palabras (BM25)"
            : "búsqueda por significado (embeddings)"
        }
      />
      <p className="text-muted-foreground">
        Un fragmento llega a la respuesta si su similitud alcanza el umbral de{" "}
        <b className="text-card-foreground">{pct(r.umbral)}</b>
        {r.modo === "hibrida" && (
          <>
            {" "}
            o si contiene al menos el{" "}
            <b className="text-card-foreground">{pct(r.coberturaMinima)}</b> de las palabras con
            contenido de la pregunta
          </>
        )}
        .
      </p>
      {r.fragmentos.length === 0 ? (
        <p className="text-muted-foreground">
          No se usaron fragmentos recuperados (la respuesta salió del cálculo o de un mensaje fijo).
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[28rem] text-left">
            <thead className="text-muted-foreground">
              <tr className="border-b border-border">
                <th className="py-1 pr-2 font-medium">Fragmento</th>
                <th className="py-1 pr-2 font-medium">Similitud</th>
                <th className="py-1 pr-2 font-medium">Palabras</th>
                <th className="py-1 pr-2 font-medium">Lugar (signif. / palabras)</th>
                <th className="py-1 font-medium">Pasó por</th>
              </tr>
            </thead>
            <tbody className="tabular-nums">
              {r.fragmentos.map((f, i) => (
                <tr key={`${f.etiqueta}-${i}`} className="border-b border-border/60 last:border-0">
                  <td className="py-1 pr-2 font-medium text-card-foreground">{f.etiqueta}</td>
                  <td
                    className={cn(
                      "py-1 pr-2",
                      f.similitud != null && f.similitud >= r.umbral && "text-success",
                    )}
                  >
                    {pct(f.similitud)}
                  </td>
                  <td
                    className={cn(
                      "py-1 pr-2",
                      f.coincidencia != null &&
                        f.coincidencia >= r.coberturaMinima &&
                        "text-success",
                    )}
                  >
                    {pct(f.coincidencia)}
                  </td>
                  <td className="py-1 pr-2">
                    {f.rangoSemantico ?? "—"} / {f.rangoPalabras ?? "—"}
                  </td>
                  <td className="py-1">{PASO[f.paso]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {(r.similitudMaxima != null || r.similitudPromedio != null) && (
        <p className="text-muted-foreground">
          Similitud máxima <b className="text-card-foreground">{pct(r.similitudMaxima)}</b> ·
          promedio <b className="text-card-foreground">{pct(r.similitudPromedio)}</b>
        </p>
      )}
    </section>
  );
}

function SeccionRespuesta({
  f,
  c,
  ind,
}: {
  f: MetricaFundamentacion | null;
  c: MetricaCitas | null;
  ind: IndicadoresRespuesta;
}) {
  const cifrasOk =
    ind.cifrasTotal == null || ind.cifrasTotal === 0 || ind.cifrasConRespaldo === ind.cifrasTotal;
  return (
    <section className="space-y-2">
      <Titulo texto="Respuesta" detalle="comparada con lo recuperado" />
      <div className="grid gap-2 sm:grid-cols-2">
        <Medida
          nombre="Fundamentación"
          valor={pct(f?.proporcion)}
          detalle={
            f && f.respaldadas != null
              ? `${f.respaldadas} de ${f.oraciones} oraciones respaldadas por un fragmento o por el cálculo`
              : "sin oraciones que evaluar"
          }
          bien={f?.proporcion != null ? f.proporcion >= 0.8 : null}
        />
        <Medida
          nombre="Citas"
          valor={pct(c?.proporcion)}
          detalle={
            c
              ? `${c.conCita} de ${c.oraciones} oraciones citan su fuente` +
                (c.citasInvalidas.length
                  ? ` · citas a fuentes inexistentes: ${c.citasInvalidas.join(", ")}`
                  : "")
              : "—"
          }
          bien={c ? c.citasInvalidas.length === 0 && (c.proporcion ?? 0) >= 0.5 : null}
        />
        <Medida
          nombre="Cifras con respaldo"
          valor={
            ind.cifrasTotal == null
              ? "—"
              : ind.cifrasTotal === 0
                ? "sin cifras"
                : `${ind.cifrasConRespaldo} de ${ind.cifrasTotal}`
          }
          detalle={
            ind.cifrasSinRespaldo.length
              ? `sin respaldo: ${ind.cifrasSinRespaldo.join(", ")}`
              : "todo número está en lo recuperado o en el cálculo"
          }
          bien={cifrasOk}
        />
        <Medida
          nombre="IDs inventados"
          valor={ind.idsInventados.length ? String(ind.idsInventados.length) : "0"}
          detalle={
            ind.idsInventados.length
              ? ind.idsInventados.join(", ")
              : "toda persona o pregunta nombrada está en los datos"
          }
          bien={ind.idsInventados.length === 0}
        />
      </div>
      {f && f.sinRespaldo.length > 0 && (
        <div className="space-y-1">
          <p className="text-muted-foreground">Oraciones sin respaldo directo en lo recuperado:</p>
          <ul className="list-disc space-y-0.5 pl-5 text-card-foreground">
            {f.sinRespaldo.map((o) => (
              <li key={o}>{o}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function Titulo({ texto, detalle }: { texto: string; detalle: string }) {
  return (
    <p className="font-medium text-card-foreground">
      {texto} <span className="font-normal text-muted-foreground">({detalle})</span>
    </p>
  );
}

function Medida({
  nombre,
  valor,
  detalle,
  bien,
}: {
  nombre: string;
  valor: string;
  detalle: string;
  bien: boolean | null;
}) {
  return (
    <div className="rounded-lg border border-border px-3 py-2">
      <p className="text-muted-foreground">{nombre}</p>
      <p
        className={cn(
          "text-base font-semibold tabular-nums",
          bien === true && "text-success",
          bien === false && "text-destructive",
          bien === null && "text-card-foreground",
        )}
      >
        {valor}
      </p>
      <p className="text-muted-foreground">{detalle}</p>
    </div>
  );
}
