import { useEffect, useState } from "react";
import { Gauge, Loader2 } from "lucide-react";
import { getMetricas } from "@/api/chat";
import { Progress } from "@/components/ui/progress";
import type { MetricasRespuesta } from "@/types";

interface PanelMetricasProps {
  consultaId: number;
}

const INTERVALO_MS = 4000;
const MAX_INTENTOS = 90; // ~6 minutos: el juez comparte Ollama con el chat

const METRICAS: {
  clave: "fidelidad" | "relevancia" | "precisionContexto";
  nombre: string;
  explicacion: string;
}[] = [
  {
    clave: "fidelidad",
    nombre: "Fidelidad",
    explicacion: "Qué parte de lo que dice la respuesta está respaldada por las fuentes.",
  },
  {
    clave: "relevancia",
    nombre: "Relevancia",
    explicacion: "Qué tan directo contesta lo que preguntaste, sin rodeos ni datos de más.",
  },
  {
    clave: "precisionContexto",
    nombre: "Precisión del contexto",
    explicacion: "Si los fragmentos que sí sirvieron para responder estaban entre los primeros.",
  },
];

/** Métricas automáticas de una respuesta: se consultan hasta que el cálculo termina. */
export function PanelMetricas({ consultaId }: PanelMetricasProps) {
  const [metricas, setMetricas] = useState<MetricasRespuesta | null>(null);

  useEffect(() => {
    let vigente = true;
    let intentos = 0;
    let temporizador: ReturnType<typeof setTimeout> | undefined;

    async function consultar() {
      intentos += 1;
      try {
        const m = await getMetricas(consultaId);
        if (!vigente) return;
        setMetricas(m);
        if (m.estado !== "calculando") return;
      } catch {
        /* se reintenta: el servicio puede estar ocupado con otra respuesta */
      }
      if (vigente && intentos < MAX_INTENTOS) temporizador = setTimeout(consultar, INTERVALO_MS);
    }

    void consultar();
    return () => {
      vigente = false;
      if (temporizador) clearTimeout(temporizador);
    };
  }, [consultaId]);

  // Los rechazos y las respuestas sin redacción del modelo no tienen qué medir.
  if (!metricas || metricas.estado === "omitida") return null;

  return (
    <details className="w-full max-w-[80%] rounded-xl border border-border bg-card px-3 py-2 text-xs">
      <summary className="flex cursor-pointer items-center gap-1.5 font-medium text-card-foreground">
        <Gauge className="size-3.5 shrink-0 text-primary" aria-hidden />
        Evaluación automática
        {metricas.estado === "calculando" && (
          <span className="ml-1 inline-flex items-center gap-1 font-normal text-muted-foreground">
            <Loader2 className="size-3 animate-spin" aria-hidden /> calculando…
          </span>
        )}
        {metricas.estado === "listo" && (
          <span className="ml-1 font-normal text-muted-foreground">
            {METRICAS.map((m) => formato(metricas[m.clave])).join(" · ")}
          </span>
        )}
        {metricas.estado === "error" && (
          <span className="ml-1 font-normal text-muted-foreground">no se pudo calcular</span>
        )}
      </summary>

      <div className="mt-2 space-y-2.5">
        {METRICAS.map((m) => {
          const valor = metricas[m.clave];
          return (
            <div key={m.clave}>
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium text-card-foreground">{m.nombre}</span>
                <span className="tabular-nums text-muted-foreground">{formato(valor)}</span>
              </div>
              <Progress
                value={valor == null ? 0 : Math.round(valor * 100)}
                className="mt-1 h-1.5"
                aria-label={m.nombre}
              />
              <p className="mt-1 leading-snug text-muted-foreground">{m.explicacion}</p>
            </div>
          );
        })}

        {metricas.noSustentadas.length > 0 && (
          <div>
            <p className="font-medium text-card-foreground">
              Afirmaciones sin respaldo en las fuentes:
            </p>
            <ul className="ml-4 list-disc text-muted-foreground">
              {metricas.noSustentadas.map((a) => (
                <li key={a}>{a}</li>
              ))}
            </ul>
          </div>
        )}

        <p className="border-t border-border pt-2 leading-snug text-muted-foreground">
          Evaluación automática aproximada: la hace un modelo pequeño
          {metricas.modeloJuez ? ` (${metricas.modeloJuez})` : ""}, no una persona. Úsala como
          orientación y revisa las fuentes.
        </p>
      </div>
    </details>
  );
}

function formato(valor: number | null): string {
  return valor == null ? "—" : `${Math.round(valor * 100)} %`;
}
