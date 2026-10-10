import { useEffect, useState } from "react";
import { Ban, Calculator, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import {
  prepararCalculo,
  type KpiCalculoResult,
  type PrepararCalculoResponse,
} from "@/api/carga";

/** KPI aceptado en el paso 4 que entra al paso de cálculo. */
export interface KpiAceptado {
  id: number;
  nombre: string;
}

/** Estado del cálculo de un KPI dentro del paso 5. */
export interface EstadoCalculoKpi {
  /** Metadatos de preparación (variables, expresión…). null mientras carga. */
  preparado: PrepararCalculoResponse | null;
  /** Valores capturados por el investigador, por clave de variable. */
  valores: Record<string, string>;
  /** Resultado calculado en cliente (si la expresión es evaluable). */
  resultado: number | null;
  /** Unidad del resultado (de la 1ª variable, si existe). */
  unidad: string;
  /** Valor de referencia capturado. */
  referencia: string;
  /** Semáforo tras registrar (si ya se registró en vivo). */
  resultadoRegistrado: KpiCalculoResult | null;
  /** El investigador omitió este KPI explícitamente. */
  omitido: boolean;
}

export function estadoInicialCalculo(): EstadoCalculoKpi {
  return {
    preparado: null,
    valores: {},
    resultado: null,
    unidad: "",
    referencia: "",
    resultadoRegistrado: null,
    omitido: false,
  };
}

/** Evalúa la expresión Python-like devuelta por Ollama con los valores capturados.
 * Solo soporta aritmética simple (+ - * / paréntesis), suficiente para ratios. */
function evaluarExpresion(expresion: string, valores: Record<string, number>): number | null {
  let expr = expresion;
  for (const [clave, valor] of Object.entries(valores)) {
    expr = expr.replace(new RegExp(`\\b${clave}\\b`, "g"), String(valor));
  }
  if (!/^[\d\s+\-*/().]+$/.test(expr)) return null;
  try {
    // eslint-disable-next-line no-new-func
    const resultado = Function(`"use strict";return (${expr});`)() as unknown;
    return typeof resultado === "number" && Number.isFinite(resultado) ? resultado : null;
  } catch {
    return null;
  }
}

/** Clase del badge de semáforo según el nivel. */
function claseSemaforo(nivel: KpiCalculoResult["nivel_semaforo"]): string {
  switch (nivel) {
    case "bueno":
      return "bg-emerald-100 text-emerald-800";
    case "neutro":
      return "bg-amber-100 text-amber-800";
    case "riesgo":
      return "bg-destructive/15 text-destructive";
    default:
      return "bg-muted text-muted-foreground";
  }
}

const ETIQUETA_SEMAFORO: Record<KpiCalculoResult["nivel_semaforo"], string> = {
  bueno: "Favorable",
  neutro: "Aceptable",
  riesgo: "En riesgo",
  informativo: "Informativo",
  sin_calculo: "Sin cálculo",
};

interface StepCalculoKpisProps {
  idInstrumento: number | null;
  kpis: KpiAceptado[];
  estados: Record<number, EstadoCalculoKpi>;
  onCambio: (kpiId: number, estado: EstadoCalculoKpi) => void;
}

export function StepCalculoKpis({ idInstrumento, kpis, estados, onCambio }: StepCalculoKpisProps) {
  const [cargandoIds, setCargandoIds] = useState<Set<number>>(new Set());

  // Prepara cada KPI (extrae variables vía Ollama) al entrar al paso.
  useEffect(() => {
    if (idInstrumento == null) return;
    let cancelado = false;
    for (const kpi of kpis) {
      const estado = estados[kpi.id];
      if (estado?.preparado || estado?.omitido) continue;
      setCargandoIds((prev) => new Set(prev).add(kpi.id));
      prepararCalculo(idInstrumento, kpi.id)
        .then((preparado) => {
          if (cancelado) return;
          onCambio(kpi.id, { ...estadoInicialCalculo(), ...estados[kpi.id], preparado });
        })
        .catch(() => {
          if (cancelado) return;
          // Fallback: se trata como no calculable (sin bloquear el flujo).
          onCambio(kpi.id, {
            ...estadoInicialCalculo(),
            ...estados[kpi.id],
            preparado: {
              kpi_id: kpi.id,
              nombre: kpi.nombre,
              tipo: "descriptivo",
              variables: [],
              expresion: null,
              formula_texto: "",
              descripcion_direccional: "",
            },
          });
        })
        .finally(() => {
          if (cancelado) return;
          setCargandoIds((prev) => {
            const siguiente = new Set(prev);
            siguiente.delete(kpi.id);
            return siguiente;
          });
        });
    }
    return () => {
      cancelado = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idInstrumento, kpis]);

  if (kpis.length === 0) {
    return (
      <p className="py-16 text-center text-muted-foreground">
        No hay KPIs aceptados para calcular. Puedes finalizar.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {kpis.map((kpi) => {
        const estado = estados[kpi.id] ?? estadoInicialCalculo();
        const prep = estado.preparado;
        const cargando = cargandoIds.has(kpi.id);
        const noCalculable =
          !cargando && prep != null && (prep.tipo === "descriptivo" || prep.variables.length === 0);

        return (
          <div
            key={kpi.id}
            className={cn(
              "space-y-4 rounded-2xl border border-border bg-card p-5 shadow-card",
              estado.omitido && "opacity-50",
            )}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-medium">{kpi.nombre}</p>
                {prep?.formula_texto && (
                  <p className="mt-1 text-xs text-muted-foreground">{prep.formula_texto}</p>
                )}
              </div>
              {estado.resultadoRegistrado && (
                <span
                  className={cn(
                    "shrink-0 rounded-full px-2.5 py-0.5 text-sm font-semibold",
                    claseSemaforo(estado.resultadoRegistrado.nivel_semaforo),
                  )}
                >
                  {ETIQUETA_SEMAFORO[estado.resultadoRegistrado.nivel_semaforo]}
                </span>
              )}
            </div>

            {cargando && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="size-4 animate-spin" /> Analizando la fórmula…
              </div>
            )}

            {estado.omitido ? (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-muted px-2.5 py-0.5 text-sm text-muted-foreground">
                <Ban className="size-3.5" /> KPI omitido
              </span>
            ) : noCalculable ? (
              <div className="flex flex-wrap items-center gap-3">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-muted px-2.5 py-0.5 text-sm text-muted-foreground">
                  No disponible para cálculo automático
                </span>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => onCambio(kpi.id, { ...estado, omitido: true })}
                >
                  <Ban /> Omitir este KPI
                </Button>
              </div>
            ) : (
              prep && (
                <div className="space-y-4">
                  <div className="grid gap-3 sm:grid-cols-2">
                    {prep.variables.map((v) => (
                      <label key={v.clave} className="space-y-1 text-sm">
                        <span className="font-medium">
                          {v.etiqueta}
                          {v.unidad && (
                            <span className="ml-1 text-muted-foreground">({v.unidad})</span>
                          )}
                        </span>
                        <Input
                          type="number"
                          inputMode="decimal"
                          value={estado.valores[v.clave] ?? ""}
                          onChange={(e) => {
                            const valores = { ...estado.valores, [v.clave]: e.target.value };
                            const numericos: Record<string, number> = {};
                            let completo = true;
                            for (const varb of prep.variables) {
                              const n = Number(valores[varb.clave]);
                              if (valores[varb.clave] === undefined || valores[varb.clave] === "" || Number.isNaN(n)) {
                                completo = false;
                                break;
                              }
                              numericos[varb.clave] = n;
                            }
                            const resultado =
                              completo && prep.expresion
                                ? evaluarExpresion(prep.expresion, numericos)
                                : null;
                            onCambio(kpi.id, {
                              ...estado,
                              valores,
                              resultado,
                              unidad: prep.variables[0]?.unidad ?? "",
                            });
                          }}
                        />
                      </label>
                    ))}
                  </div>

                  {estado.resultado != null && (
                    <div className="flex items-center gap-2 rounded-xl bg-primary-soft px-4 py-2 text-sm">
                      <Calculator className="size-4" />
                      <span className="font-medium">Resultado calculado:</span>
                      <span>{estado.resultado.toLocaleString("es-MX", { maximumFractionDigits: 4 })}</span>
                    </div>
                  )}

                  <label className="space-y-1 text-sm">
                    <span className="font-medium">Valor de referencia</span>
                    {prep.descripcion_direccional && (
                      <span className="block text-xs text-muted-foreground">
                        {prep.descripcion_direccional}
                      </span>
                    )}
                    <Input
                      type="number"
                      inputMode="decimal"
                      value={estado.referencia}
                      onChange={(e) => onCambio(kpi.id, { ...estado, referencia: e.target.value })}
                    />
                  </label>

                  {estado.resultadoRegistrado && (
                    <p className="text-sm text-muted-foreground">
                      {estado.resultadoRegistrado.interpretacion_texto}
                    </p>
                  )}

                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => onCambio(kpi.id, { ...estado, omitido: true })}
                  >
                    <Ban /> Omitir este KPI
                  </Button>
                </div>
              )
            )}
          </div>
        );
      })}
    </div>
  );
}
