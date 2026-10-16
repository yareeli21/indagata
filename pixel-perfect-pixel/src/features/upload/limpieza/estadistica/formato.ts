/** Formato de las medidas estadísticas de la limpieza (es-MX). */

const NUMERO = new Intl.NumberFormat("es-MX", { maximumFractionDigits: 2 });

export function num(valor: number | null | undefined, decimales = 2): string {
  if (valor === null || valor === undefined || Number.isNaN(valor)) return "—";
  if (decimales === 2) return NUMERO.format(valor);
  return new Intl.NumberFormat("es-MX", { maximumFractionDigits: decimales }).format(valor);
}

export function pct(valor: number | null | undefined): string {
  if (valor === null || valor === undefined) return "—";
  return `${new Intl.NumberFormat("es-MX", { maximumFractionDigits: 1 }).format(valor * 100)} %`;
}

export function segunFormato(valor: number | null, formato: "num" | "pct" | "dec"): string {
  if (formato === "pct") return pct(valor);
  if (formato === "dec") return num(valor, 3);
  return num(valor, 0);
}

/** Interpretaciones que calcula el cleaning-service, agrupadas por tono. */
const TONO: Record<string, "bien" | "medio" | "alerta" | "mal"> = {
  excelente: "bien",
  buena: "bien",
  aceptable: "medio",
  media: "bien",
  fácil: "medio",
  cuestionable: "alerta",
  regular: "alerta",
  difícil: "alerta",
  pobre: "mal",
  inaceptable: "mal",
};

export const CLASE_TONO: Record<"bien" | "medio" | "alerta" | "mal", string> = {
  bien: "bg-success-soft text-success",
  medio: "bg-primary-soft text-primary-strong",
  alerta: "bg-accent-soft text-accent-strong",
  mal: "bg-destructive/10 text-destructive",
};

export function claseNivel(nivel: string | null | undefined): string {
  return CLASE_TONO[TONO[nivel ?? ""] ?? "medio"];
}

/** Explicación breve de cada medida, para el atributo title y las ayudas. */
export const AYUDA = {
  alfa: "Alfa de Cronbach: qué tan consistentes son las respuestas a los ítems de un mismo bloque. ≥ 0.7 se considera aceptable.",
  kr20: "KR-20: consistencia interna de una prueba con respuestas correctas/incorrectas. ≥ 0.7 se considera aceptable.",
  itemTotal:
    "Correlación ítem-total corregida: qué tanto se relaciona el ítem con el resto del bloque. Menor a 0.3 sugiere revisarlo.",
  alfaSiSeElimina:
    "Alfa si se elimina el ítem: si es mayor que el alfa del bloque, el ítem le resta consistencia.",
  asimetria:
    "Asimetría: 0 es simétrica; positiva, cola hacia valores altos; negativa, hacia valores bajos.",
  curtosis:
    "Curtosis (en exceso): 0 es como la normal; positiva, más concentrada; negativa, más plana.",
  atipicos:
    "Atípicos según ±kσ (desviaciones estándar) y según el rango intercuartílico (Q1 − k·IQR, Q3 + k·IQR).",
  dificultad:
    "Índice de dificultad p: proporción de alumnos que acertaron. > 0.7 fácil, < 0.3 difícil.",
  discriminacion:
    "Índice de discriminación D: aciertos del 27 % con mejor puntaje menos los del 27 % con peor puntaje. ≥ 0.3 es bueno.",
  puntoBiserial:
    "Correlación punto-biserial corregida: relación entre acertar el reactivo y el puntaje en el resto de la prueba.",
} as const;
