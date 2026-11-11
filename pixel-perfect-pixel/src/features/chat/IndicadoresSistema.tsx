import { Cpu } from "lucide-react";
import { cn } from "@/lib/utils";
import type { IndicadoresRespuesta } from "@/types";

const INTENCIONES: Record<string, string> = {
  datos_respondente: "datos de respondentes",
  filtrar_respondentes: "filtrar respondentes",
  conteo_porcentaje: "conteo o porcentaje",
  comparar_grupos: "comparar grupos",
  hallazgo: "hallazgo",
  resumen_pregunta: "resumen de una pregunta",
  ranking_preguntas: "ranking de preguntas",
  kpi: "KPI",
  semantica_abierta: "búsqueda abierta",
  metodologia: "metodología",
  uso_plataforma: "uso de la plataforma",
  fuera_de_dominio: "fuera de dominio",
  aclaracion: "aclaración",
  reglas: "reglas (sin plan)",
};

const RESPUESTAS: Record<IndicadoresRespuesta["respuesta"], string> = {
  redactada: "la redactó el modelo",
  presentacion_fija: "presentación fija del cálculo",
  plantilla: "plantilla (mensaje fijo o de respaldo)",
};

const FALLOS: Record<string, string> = {
  negativa_corregida: "negó el resultado",
  inventada: "inventó una tabla o IDs",
  cifras_corregidas: "usó cifras que no estaban en el cálculo",
  cifras_completadas: "omitió cifras necesarias",
  calificada: "habló de respuestas correctas o calificaciones",
  vacia: "respondió vacío",
  cita_inventada: "puso entre comillas una frase que no está en los datos",
};

const ETAPAS: [string, string][] = [
  ["interpretacion", "entender"],
  ["ejecucion", "calcular"],
  ["recuperacion", "buscar en el RAG"],
  ["redaccion", "escribir"],
  ["verificacion", "verificar"],
];

function segundos(ms: number): string {
  return `${(ms / 1000).toFixed(1)} s`;
}

/**
 * Indicadores del sistema de una respuesta: se calculan sin modelo juez a partir de lo que registró el chat
 * (intención entendida, quién escribió la respuesta, regeneraciones, cifras e IDs sin respaldo, tiempos).
 */
export function IndicadoresSistema({ ind }: { ind: IndicadoresRespuesta }) {
  const redactada = ind.respuesta === "redactada";
  const cifrasCompletas =
    ind.cifrasTotal != null &&
    ind.cifrasConRespaldo != null &&
    ind.cifrasConRespaldo === ind.cifrasTotal;
  const etapas = ETAPAS.filter(([clave]) => ind.tiempos[clave] != null);
  const recuperados = ind.fragmentosRag ?? [];

  return (
    <div className="space-y-1.5">
      <p className="flex items-center gap-1.5 font-medium text-card-foreground">
        <Cpu className="size-3.5 shrink-0 text-primary" aria-hidden />
        Indicadores del sistema
      </p>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-muted-foreground">
        {ind.modelo && (
          <>
            <dt>Modelo</dt>
            <dd className="font-medium text-card-foreground">{ind.modelo}</dd>
          </>
        )}
        <dt>Entendió</dt>
        <dd>{ind.intencion ? (INTENCIONES[ind.intencion] ?? ind.intencion) : "—"}</dd>

        <dt>Respuesta</dt>
        <dd className={cn(ind.respuesta === "plantilla" && "text-accent-strong")}>
          {RESPUESTAS[ind.respuesta]}
          {ind.plantillaDetalle && <span className="block">{ind.plantillaDetalle}</span>}
        </dd>

        {ind.regeneraciones != null && (
          <>
            <dt>Regeneraciones</dt>
            <dd className={cn(ind.regeneraciones > 0 && "text-accent-strong")}>
              {ind.regeneraciones}
              {ind.primerFallo && ` (${FALLOS[ind.primerFallo] ?? ind.primerFallo})`}
            </dd>
          </>
        )}

        <dt>Recuperado del RAG</dt>
        <dd className={cn(recuperados.length > 0 && "text-card-foreground")}>
          {recuperados.length
            ? `${recuperados.length} fragmento${recuperados.length === 1 ? "" : "s"}: ${recuperados.join(", ")}`
            : "nada (solo cálculo o mensaje fijo)"}
        </dd>

        {redactada && ind.cifrasTotal != null && (
          <>
            <dt>Cifras con respaldo</dt>
            <dd
              className={cn("tabular-nums", cifrasCompletas ? "text-success" : "text-destructive")}
            >
              {ind.cifrasTotal === 0
                ? "no escribió cifras"
                : `${ind.cifrasConRespaldo} de ${ind.cifrasTotal}`}
              {ind.cifrasSinRespaldo.length > 0 &&
                ` · sin respaldo: ${ind.cifrasSinRespaldo.join(", ")}`}
            </dd>
          </>
        )}

        {redactada && (
          <>
            <dt>IDs inventados</dt>
            <dd className={cn(ind.idsInventados.length ? "text-destructive" : "text-success")}>
              {ind.idsInventados.length ? ind.idsInventados.join(", ") : "ninguno"}
            </dd>
          </>
        )}

        {(etapas.length > 0 || ind.latenciaMs != null) && (
          <>
            <dt>Tiempo</dt>
            <dd className="tabular-nums">
              {etapas
                .map(([clave, nombre]) => `${nombre} ${segundos(ind.tiempos[clave] ?? 0)}`)
                .join(" · ")}
              {ind.latenciaMs != null && (
                <span className="font-medium text-card-foreground">
                  {etapas.length > 0 && " · "}total {segundos(ind.latenciaMs)}
                </span>
              )}
            </dd>
          </>
        )}
      </dl>
    </div>
  );
}
