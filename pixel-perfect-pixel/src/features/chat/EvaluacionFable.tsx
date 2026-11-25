import { useEffect, useState } from "react";
import { Loader2, RefreshCw, Scale } from "lucide-react";
import { calcularMetricas, getMetricas } from "@/api/chat";
import { Progress } from "@/components/ui/progress";
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

/**
 * Las seis métricas de RAGAS. Fidelidad y relevancia no necesitan respuesta de referencia: son las principales.
 * Las otras cuatro se comparan con una referencia que escribe el mismo juez (no una anotación humana), así que se
 * muestran aparte y marcadas (16 nov).
 */
const METRICAS: {
  clave: Clave;
  nombre: string;
  ragas: string;
  explicacion: string;
  /** true: se calcula contra la respuesta de referencia escrita por el juez. */
  conReferencia: boolean;
}[] = [
  {
    clave: "precisionContexto",
    conReferencia: true,
    nombre: "Precisión del contexto",
    ragas: "Context Precision",
    explicacion:
      "Si los fragmentos recuperados servían para la respuesta ideal y los útiles iban primero.",
  },
  {
    clave: "recuerdoContexto",
    conReferencia: true,
    nombre: "Recuerdo del contexto",
    ragas: "Context Recall",
    explicacion:
      "Qué parte de la respuesta ideal estaba en lo recuperado. Bajo = la búsqueda dejó fuera evidencia.",
  },
  {
    clave: "fidelidad",
    conReferencia: false,
    nombre: "Fidelidad",
    ragas: "Faithfulness",
    explicacion:
      "Qué parte de lo que afirma la respuesta se deduce de las fuentes. Bajo = posible invención.",
  },
  {
    clave: "relevancia",
    conReferencia: false,
    nombre: "Relevancia de la respuesta",
    ragas: "Response Relevancy",
    explicacion: "Qué tan directo contesta lo que preguntaste (0 si evade).",
  },
  {
    clave: "sensibilidadRuido",
    conReferencia: true,
    nombre: "Sensibilidad al ruido",
    ragas: "Noise Sensitivity",
    explicacion:
      "Afirmaciones incorrectas que la respuesta tomó de las fuentes. Aquí menos es mejor.",
  },
  {
    clave: "correccionFactual",
    conReferencia: true,
    nombre: "Corrección factual",
    ragas: "Factual Correctness (F1)",
    explicacion:
      "Coincidencia de afirmaciones con la respuesta ideal: precisión y cobertura combinadas.",
  },
];

/** Puntaje RAGAS de 0 a 1, sin colores: no hay un corte validado entre «bueno» y «malo». */
function puntaje(valor: number | null): string {
  return valor == null ? "—" : valor.toFixed(2);
}

/**
 * Evaluación de la respuesta con el juez Claude Fable 5.2. Es bajo demanda: la respuesta llega «pendiente» y se
 * evalúa al pulsar «Evaluar» (cada evaluación usa la API de Anthropic); después se consulta hasta que termina.
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

  if (evaluacion.estado === "pendiente") {
    return (
      <section className="space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          {titulo}
          <BotonReevaluar pidiendo={pidiendo} onClick={() => void reevaluar()} texto="Evaluar" />
        </div>
        <p className="text-muted-foreground">
          Sin evaluar. Se evalúa solo si lo pides: cada evaluación usa la API de Anthropic y tarda
          alrededor de un minuto.
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

      <GrupoMetricas metricas={METRICAS.filter((m) => !m.conReferencia)} evaluacion={evaluacion} />

      <div className="space-y-2 rounded-lg border border-border px-3 py-2">
        <p className="font-medium text-card-foreground">Métricas con respuesta de referencia</p>
        <GrupoMetricas metricas={METRICAS.filter((m) => m.conReferencia)} evaluacion={evaluacion} />
      </div>

      {evaluacion.motivo && <p className="text-muted-foreground">{evaluacion.motivo}</p>}

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
        {evaluacion.fallback && " (Fable declinó y juzgó su modelo de respaldo)"}. Puntajes de 0 a 1
        calculados con las fórmulas de RAGAS 0.4.3 a partir de los veredictos del juez.
      </p>
    </section>
  );
}

function GrupoMetricas({
  metricas,
  evaluacion,
}: {
  metricas: typeof METRICAS;
  evaluacion: Evaluacion;
}) {
  return (
    <div className="grid gap-x-4 gap-y-2.5 sm:grid-cols-2">
      {metricas.map((m) => {
        const valor = evaluacion[m.clave];
        return (
          <div key={m.clave}>
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium text-card-foreground">
                {m.nombre}{" "}
                <span className="font-normal italic text-muted-foreground">({m.ragas})</span>
              </span>
              <span className="font-semibold tabular-nums text-card-foreground">
                {puntaje(valor)}
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
                ` Precisión ${puntaje(evaluacion.correccionPrecision)} · cobertura ${puntaje(evaluacion.correccionRecuerdo)}.`}
            </p>
          </div>
        );
      })}
    </div>
  );
}

function BotonReevaluar({
  pidiendo,
  onClick,
  texto = "Volver a evaluar",
}: {
  pidiendo: boolean;
  onClick: () => void;
  texto?: string;
}) {
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
      {texto}
    </button>
  );
}
