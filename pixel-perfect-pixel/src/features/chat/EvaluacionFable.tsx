import { useEffect, useState } from "react";
import { Loader2, RefreshCw, Scale } from "lucide-react";
import { calcularMetricas, getMetricas } from "@/api/chat";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import type { EvaluacionFable as Evaluacion } from "@/types";

interface EvaluacionFableProps {
  consultaId: number;
  inicial: Evaluacion | null;
}

const INTERVALO_MS = 4000;
const MAX_INTENTOS = 90; // ~6 minutos: Fable puede tardar en respuestas largas

type Clave =
  | "precisionContexto"
  | "recuerdoContexto"
  | "fidelidad"
  | "relevancia"
  | "sensibilidadRuido"
  | "correccionFactual";

/** Las seis métricas en el orden de RAGAS: primero la recuperación, luego la respuesta. */
const METRICAS: {
  clave: Clave;
  nombre: string;
  ragas: string;
  explicacion: string;
  /** true: un valor bajo es bueno (solo la sensibilidad al ruido). */
  invertida?: boolean;
}[] = [
  {
    clave: "precisionContexto",
    nombre: "Precisión del contexto",
    ragas: "Context Precision",
    explicacion:
      "Si los fragmentos recuperados servían para la respuesta ideal y los útiles iban primero.",
  },
  {
    clave: "recuerdoContexto",
    nombre: "Recuerdo del contexto",
    ragas: "Context Recall",
    explicacion:
      "Qué parte de la respuesta ideal estaba en lo recuperado. Bajo = la búsqueda dejó fuera evidencia.",
  },
  {
    clave: "fidelidad",
    nombre: "Fidelidad",
    ragas: "Faithfulness",
    explicacion:
      "Qué parte de lo que afirma la respuesta se deduce de las fuentes. Bajo = posible invención.",
  },
  {
    clave: "relevancia",
    nombre: "Relevancia de la respuesta",
    ragas: "Response Relevancy",
    explicacion: "Qué tan directo contesta lo que preguntaste (0 si evade).",
  },
  {
    clave: "sensibilidadRuido",
    nombre: "Sensibilidad al ruido",
    ragas: "Noise Sensitivity",
    explicacion:
      "Afirmaciones incorrectas que la respuesta tomó de las fuentes. Aquí menos es mejor.",
    invertida: true,
  },
  {
    clave: "correccionFactual",
    nombre: "Corrección factual",
    ragas: "Factual Correctness (F1)",
    explicacion:
      "Coincidencia de afirmaciones con la respuesta ideal: precisión y cobertura combinadas.",
  },
];

/** Verde ≥ 70 %, ámbar 40–69 %, rojo < 40 % (al revés en las métricas donde menos es mejor). */
function tono(valor: number | null, invertida = false): string {
  if (valor == null) return "text-muted-foreground";
  const v = invertida ? 1 - valor : valor;
  if (v >= 0.7) return "text-success";
  if (v >= 0.4) return "text-accent-strong";
  return "text-destructive";
}

function pct(valor: number | null): string {
  return valor == null ? "—" : `${Math.round(valor * 100)} %`;
}

/**
 * Evaluación de la respuesta con el juez Claude Fable 5.2. El servicio la calcula sola después de cada respuesta;
 * aquí se consulta hasta que termina.
 */
export function EvaluacionFable({ consultaId, inicial }: EvaluacionFableProps) {
  const [evaluacion, setEvaluacion] = useState<Evaluacion | null>(inicial);
  const [ronda, setRonda] = useState(0);
  const [pidiendo, setPidiendo] = useState(false);
  const calculando = evaluacion?.estado === "calculando";

  useEffect(() => {
    if (!calculando) return;
    let vigente = true;
    let intentos = 0;
    let temporizador: ReturnType<typeof setTimeout> | undefined;

    async function consultar() {
      intentos += 1;
      try {
        const m = await getMetricas(consultaId);
        if (!vigente) return;
        setEvaluacion(m.juezFable);
        if (m.juezFable?.estado !== "calculando") return;
      } catch {
        /* se reintenta */
      }
      if (vigente && intentos < MAX_INTENTOS) temporizador = setTimeout(consultar, INTERVALO_MS);
    }

    temporizador = setTimeout(consultar, INTERVALO_MS);
    return () => {
      vigente = false;
      if (temporizador) clearTimeout(temporizador);
    };
  }, [consultaId, calculando, ronda]);

  async function reevaluar() {
    if (!evaluacion) return;
    setPidiendo(true);
    try {
      const m = await calcularMetricas(consultaId, evaluacion.modelo);
      setEvaluacion(m.juezFable);
      setRonda((r) => r + 1);
    } catch {
      /* el botón queda disponible para reintentar */
    } finally {
      setPidiendo(false);
    }
  }

  const titulo = (
    <p className="flex flex-wrap items-center gap-1.5 font-medium text-card-foreground">
      <Scale className="size-3.5 shrink-0 text-primary" aria-hidden />
      Juez Claude Fable 5.2{" "}
      <span className="font-normal text-muted-foreground">(métricas RAGAS)</span>
    </p>
  );

  if (!evaluacion) {
    return (
      <section className="space-y-1">
        {titulo}
        <p className="text-muted-foreground">
          No aplica a esta respuesta (rechazo, mensaje fijo o respuesta reutilizada sin evaluación).
        </p>
      </section>
    );
  }

  if (evaluacion.estado === "calculando") {
    return (
      <section className="space-y-1">
        {titulo}
        <p className="inline-flex items-center gap-1.5 text-muted-foreground">
          <Loader2 className="size-3.5 animate-spin" aria-hidden /> El juez está evaluando esta
          respuesta…
        </p>
      </section>
    );
  }

  if (evaluacion.estado === "omitida" || evaluacion.estado === "error") {
    return (
      <section className="space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          {titulo}
          <BotonReevaluar pidiendo={pidiendo} onClick={() => void reevaluar()} />
        </div>
        <p className="text-muted-foreground">
          {evaluacion.estado === "omitida" ? "Sin evaluar" : "No se pudo evaluar"}
          {evaluacion.motivo ? `: ${evaluacion.motivo}` : "."}
        </p>
      </section>
    );
  }

  const noCubiertas = new Set(evaluacion.referenciaNoCubierta);
  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        {titulo}
        <BotonReevaluar pidiendo={pidiendo} onClick={() => void reevaluar()} />
      </div>

      <div className="grid gap-x-4 gap-y-2.5 sm:grid-cols-2">
        {METRICAS.map((m) => {
          const valor = evaluacion[m.clave];
          return (
            <div key={m.clave}>
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium text-card-foreground">
                  {m.nombre}{" "}
                  <span className="font-normal italic text-muted-foreground">({m.ragas})</span>
                </span>
                <span className={cn("font-semibold tabular-nums", tono(valor, m.invertida))}>
                  {pct(valor)}
                </span>
              </div>
              <Progress
                value={valor == null ? 0 : Math.round(valor * 100)}
                className="mt-1 h-1.5"
                aria-label={m.nombre}
              />
              <p className="mt-1 leading-snug text-muted-foreground">
                {m.explicacion}
                {m.clave === "correccionFactual" &&
                  evaluacion.correccionPrecision != null &&
                  ` Precisión ${pct(evaluacion.correccionPrecision)} · cobertura ${pct(evaluacion.correccionRecuerdo)}.`}
              </p>
            </div>
          );
        })}
      </div>

      {evaluacion.motivo && <p className="text-muted-foreground">{evaluacion.motivo}</p>}

      <Lista titulo="Afirmaciones sin respaldo en lo recuperado" items={evaluacion.noSustentadas} />
      <Lista
        titulo="Afirmaciones que no coinciden con la respuesta ideal"
        items={evaluacion.incorrectas}
      />

      {evaluacion.respuestaReferencia && (
        <details className="rounded-lg border border-border px-3 py-2">
          <summary className="cursor-pointer font-medium text-card-foreground">
            Respuesta ideal con la que se comparó
          </summary>
          <p className="mt-1.5 whitespace-pre-line text-card-foreground">
            {evaluacion.respuestaReferencia}
          </p>
          {evaluacion.afirmacionesReferencia.length > 0 && (
            <ol className="mt-1.5 list-decimal space-y-0.5 pl-5">
              {evaluacion.afirmacionesReferencia.map((a, i) => (
                <li
                  key={`${i}-${a}`}
                  className={noCubiertas.has(i + 1) ? "text-destructive" : "text-muted-foreground"}
                >
                  {a}
                  {noCubiertas.has(i + 1) && " (la respuesta no lo dice)"}
                </li>
              ))}
            </ol>
          )}
          {evaluacion.preguntasGeneradas.length > 0 && (
            <p className="mt-1.5 text-muted-foreground">
              Preguntas que el juez dedujo de la respuesta (relevancia):{" "}
              {evaluacion.preguntasGeneradas.join(" · ")}
            </p>
          )}
        </details>
      )}

      <p className="leading-snug text-muted-foreground">
        Evaluación automática de {evaluacion.modeloReal ?? evaluacion.modelo}
        {evaluacion.fallback && " (Fable declinó y juzgó su modelo de respaldo)"}. La respuesta
        ideal la escribe el mismo juez con{" "}
        {evaluacion.origenReferencia === "contexto_ampliado"
          ? "lo recuperado más otros fragmentos cercanos del acervo"
          : "solo lo recuperado"}
        , sin ver la respuesta del sistema; no es una anotación humana. Verde ≥ 70 %, ámbar 40–69 %,
        rojo &lt; 40 % (al revés en la sensibilidad al ruido).
      </p>
    </section>
  );
}

function BotonReevaluar({ pidiendo, onClick }: { pidiendo: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={pidiendo}
      className="ml-auto inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1 font-medium text-primary hover:bg-muted disabled:opacity-60"
    >
      {pidiendo ? (
        <Loader2 className="size-3 animate-spin" aria-hidden />
      ) : (
        <RefreshCw className="size-3" aria-hidden />
      )}
      Volver a evaluar
    </button>
  );
}

function Lista({ titulo, items }: { titulo: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div className="space-y-1">
      <p className="text-muted-foreground">{titulo}:</p>
      <ul className="list-disc space-y-0.5 pl-5 text-card-foreground">
        {items.map((a) => (
          <li key={a}>{a}</li>
        ))}
      </ul>
    </div>
  );
}
