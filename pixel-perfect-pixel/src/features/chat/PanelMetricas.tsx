import { useEffect, useState } from "react";
import { Gauge, Loader2 } from "lucide-react";
import { calcularMetricas, getMetricas } from "@/api/chat";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import type { MetricasRespuesta } from "@/types";
import { CalificacionHumana } from "./CalificacionHumana";
import { IndicadoresSistema } from "./IndicadoresSistema";

interface PanelMetricasProps {
  consultaId: number;
}

const INTERVALO_MS = 4000;
const MAX_INTENTOS = 90; // ~6 minutos: el juez comparte Ollama con el chat

/** Las tres métricas de RAGAS sin respuesta de referencia, en el orden del resumen. */
const METRICAS: {
  clave: "fidelidad" | "relevancia" | "precisionContexto";
  nombre: string;
  corto: string;
  ragas: string;
  explicacion: string;
}[] = [
  {
    clave: "fidelidad",
    nombre: "Fidelidad",
    corto: "Fidelidad",
    ragas: "faithfulness",
    explicacion:
      "Qué parte de lo que afirma la respuesta está respaldada por las fuentes. Baja = posible invención.",
  },
  {
    clave: "relevancia",
    nombre: "Relevancia de la respuesta",
    corto: "Relevancia",
    ragas: "answer relevancy",
    explicacion: "Qué tan directo contesta lo que preguntaste, sin rodeos ni datos de más.",
  },
  {
    clave: "precisionContexto",
    nombre: "Precisión del contexto",
    corto: "Precisión",
    ragas: "context precision",
    explicacion:
      "Si los fragmentos recuperados sirvieron y los útiles estaban primero. Baja = la búsqueda trajo ruido.",
  },
];

const RESUMEN_RESPUESTA = {
  redactada: "redactada por el modelo",
  presentacion_fija: "cálculo tal cual",
  plantilla: "plantilla",
} as const;

const CALIFICACION = ["Mal", "Parcial", "Bien"] as const;

/** Rango de lectura: ≥ 70 % bien, 40–69 % revisar, < 40 % bajo. */
function tono(valor: number | null): string {
  if (valor == null) return "text-muted-foreground";
  if (valor >= 0.7) return "text-success";
  if (valor >= 0.4) return "text-accent-strong";
  return "text-destructive";
}

function formato(valor: number | null): string {
  return valor == null ? "—" : `${Math.round(valor * 100)} %`;
}

/**
 * Evaluación de una respuesta en tres partes: los indicadores del sistema (sin juez, al instante), la evaluación
 * del juez (RAGAS, bajo demanda; con una tabla si varios jueces la calificaron) y la calificación humana.
 * Se consulta hasta que el cálculo del juez termina.
 */
export function PanelMetricas({ consultaId }: PanelMetricasProps) {
  const [metricas, setMetricas] = useState<MetricasRespuesta | null>(null);
  // Cada vez que cambia, se vuelve a consultar hasta que el cálculo termine (al pedir la evaluación).
  const [ronda, setRonda] = useState(0);
  const [pidiendo, setPidiendo] = useState(false);
  // Abierto mientras la respuesta no tenga calificación, para calificar sin un clic extra.
  const [abierto, setAbierto] = useState<boolean | null>(null);

  async function pedirEvaluacion() {
    setPidiendo(true);
    try {
      setMetricas(await calcularMetricas(consultaId));
      setRonda((r) => r + 1);
    } catch {
      /* el botón queda disponible para reintentar */
    } finally {
      setPidiendo(false);
    }
  }

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
        setAbierto((a) => (a === null ? !m.calificacion : a));
        if (m.estado !== "calculando" && !m.jueces.some((j) => j.estado === "calculando")) return;
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
  }, [consultaId, ronda]);

  if (!metricas) return null;
  const ind = metricas.indicadores;
  const otrosJueces = metricas.jueces.filter((j) => j.modeloJuez !== metricas.modeloJuez);

  return (
    <details
      open={abierto ?? false}
      onToggle={(e) => setAbierto(e.currentTarget.open)}
      className="w-full max-w-[80%] rounded-xl border border-border bg-card px-3 py-2 text-xs"
    >
      <summary className="flex cursor-pointer flex-wrap items-center gap-x-1.5 gap-y-0.5 font-medium text-card-foreground">
        <Gauge className="size-3.5 shrink-0 text-primary" aria-hidden />
        Evaluación de la respuesta
        <span className="font-normal text-muted-foreground">
          {ind && <>· {RESUMEN_RESPUESTA[ind.respuesta]} </>}
          {(metricas.estado === "listo" || metricas.estado === "calculada") && (
            <>
              · juez{" "}
              {METRICAS.map((m, i) => (
                <span key={m.clave}>
                  {i > 0 && " / "}
                  <span className={cn("font-semibold tabular-nums", tono(metricas[m.clave]))}>
                    {formato(metricas[m.clave])}
                  </span>
                </span>
              ))}{" "}
            </>
          )}
          {metricas.estado === "calculando" && (
            <span className="inline-flex items-center gap-1">
              · <Loader2 className="size-3 animate-spin" aria-hidden /> juez calculando…{" "}
            </span>
          )}
          {metricas.calificacion && (
            <>
              · tu calificación:{" "}
              <span className="font-semibold text-card-foreground">
                {CALIFICACION[metricas.calificacion.calificacion]}
              </span>
            </>
          )}
        </span>
      </summary>

      <div className="mt-2 space-y-3">
        {ind && <IndicadoresSistema ind={ind} />}

        <div className="space-y-2 border-t border-border pt-2">
          <SeccionJuez
            metricas={metricas}
            pidiendo={pidiendo}
            onPedir={() => void pedirEvaluacion()}
          />
          {otrosJueces.length > 0 && <TablaJueces metricas={metricas} />}
        </div>

        <div className="border-t border-border pt-2">
          <CalificacionHumana consultaId={consultaId} inicial={metricas.calificacion} />
        </div>
      </div>
    </details>
  );
}

/** La evaluación del juez por defecto: botón (bajo demanda), progreso o resultado. */
function SeccionJuez({
  metricas,
  pidiendo,
  onPedir,
}: {
  metricas: MetricasRespuesta;
  pidiendo: boolean;
  onPedir: () => void;
}) {
  const titulo = (
    <p className="flex items-center gap-1.5 font-medium text-card-foreground">
      <Gauge className="size-3.5 shrink-0 text-primary" aria-hidden />
      Evaluación del juez <span className="font-normal text-muted-foreground">(RAGAS)</span>
    </p>
  );

  if (metricas.estado === "omitida") {
    return (
      <div className="space-y-1">
        {titulo}
        <p className="leading-snug text-muted-foreground">
          No aplica: es un rechazo o un mensaje fijo, no hay redacción que evaluar.
        </p>
      </div>
    );
  }

  // Bajo demanda: el juez solo trabaja si la persona lo pide (no recarga el modelo después de cada pregunta).
  if (metricas.estado === "pendiente") {
    return (
      <div className="space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          {titulo}
          {metricas.fidelidad != null && (
            <span className="text-muted-foreground">
              Fidelidad <span className="font-semibold tabular-nums text-success">100 %</span> por
              construcción
            </span>
          )}
          <button
            type="button"
            onClick={onPedir}
            disabled={pidiendo}
            className="ml-auto inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1 font-semibold text-primary hover:bg-primary-soft disabled:opacity-60"
          >
            {pidiendo && <Loader2 className="size-3 animate-spin" aria-hidden />}
            Calcular evaluación (RAGAS)
          </button>
        </div>
        <p className="leading-snug text-muted-foreground">
          Se calcula solo si la pides: tarda alrededor de un minuto y la siguiente pregunta puede
          tardar un poco más mientras el modelo juez trabaja.
        </p>
      </div>
    );
  }

  if (metricas.estado === "calculando") {
    return (
      <div className="space-y-1">
        {titulo}
        <p className="inline-flex items-center gap-1 text-muted-foreground">
          <Loader2 className="size-3 animate-spin" aria-hidden /> calculando…
        </p>
      </div>
    );
  }

  if (metricas.estado === "error") {
    return (
      <div className="space-y-1">
        {titulo}
        <p className="text-muted-foreground">
          No se pudo calcular{metricas.motivo ? `: ${metricas.motivo}` : "."}
        </p>
      </div>
    );
  }

  // El resultado calculado mostrado tal cual: la fidelidad no se le pregunta al juez (lo hacía mal); la
  // relevancia y la precisión del contexto sí se miden contra el resultado usado.
  if (metricas.estado === "calculada") {
    return (
      <div className="space-y-1">
        {titulo}
        <p className="text-muted-foreground">
          Fidelidad <span className="font-semibold tabular-nums text-success">100 %</span> por
          construcción
          {METRICAS.filter((m) => m.clave !== "fidelidad").map((m) => (
            <span key={m.clave}>
              {" · "}
              {m.corto}{" "}
              <span className={cn("font-semibold tabular-nums", tono(metricas[m.clave]))}>
                {formato(metricas[m.clave])}
              </span>
            </span>
          ))}
        </p>
        <p className="leading-snug text-muted-foreground">
          Esta respuesta es el resultado calculado sobre los datos del instrumento, mostrado tal
          cual: no la redactó el modelo, así que todo lo que dice está en las fuentes. La relevancia
          (¿responde lo que preguntaste?) y la precisión del contexto (¿el resultado usado servía?)
          las estima un modelo pequeño{metricas.modeloJuez ? ` (${metricas.modeloJuez})` : ""}.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2.5">
      {titulo}
      {METRICAS.map((m) => {
        const valor = metricas[m.clave];
        return (
          <div key={m.clave}>
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium text-card-foreground">
                {m.nombre}{" "}
                <span className="font-normal italic text-muted-foreground">({m.ragas})</span>
              </span>
              <span className={cn("font-semibold tabular-nums", tono(valor))}>
                {formato(valor)}
              </span>
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

      <p className="leading-snug text-muted-foreground">
        Evaluación automática aproximada al estilo RAGAS, sin respuesta de referencia: la hace un
        modelo pequeño{metricas.modeloJuez ? ` (${metricas.modeloJuez})` : ""}, no una persona.
        Verde ≥ 70 %, ámbar 40–69 %, rojo &lt; 40 %. Úsala como orientación y revisa las fuentes.
      </p>
    </div>
  );
}

/** La misma respuesta calificada por varios jueces (experimento redactor × juez). */
function TablaJueces({ metricas }: { metricas: MetricasRespuesta }) {
  return (
    <div>
      <p className="font-medium text-card-foreground">Evaluación por juez</p>
      <table className="mt-1 w-full text-left tabular-nums">
        <thead className="text-muted-foreground">
          <tr>
            <th className="py-0.5 pr-2 font-normal">Juez</th>
            {METRICAS.map((m) => (
              <th key={m.clave} className="py-0.5 pr-2 font-normal">
                {m.corto}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {metricas.jueces.map((j) => (
            <tr key={j.modeloJuez} className="border-t border-border">
              <td className="py-0.5 pr-2 font-medium text-card-foreground">
                {j.modeloJuez}
                {j.modeloJuez === metricas.modeloJuez && (
                  <span className="font-normal text-muted-foreground"> (por defecto)</span>
                )}
              </td>
              {j.estado === "calculando" ? (
                <td colSpan={3} className="py-0.5 text-muted-foreground">
                  calculando…
                </td>
              ) : (
                METRICAS.map((m) => (
                  <td key={m.clave} className={cn("py-0.5 pr-2 font-semibold", tono(j[m.clave]))}>
                    {formato(j[m.clave])}
                  </td>
                ))
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
