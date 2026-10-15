import type { PuntoEspacio, TipoPuntoEspacio } from "@/types";

/** Colores del mapa, leídos de los tokens CSS (el canvas no entiende clases). */
export interface Paleta {
  kpi: string;
  instrumento: string;
  chunk: string;
  borde: string;
  cuadricula: string;
  ejes: string;
  texto: string;
  fondoEtiqueta: string;
}

export function leerPaleta(elemento: Element): Paleta {
  const css = getComputedStyle(elemento);
  const v = (nombre: string, respaldo: string) => css.getPropertyValue(nombre).trim() || respaldo;
  return {
    kpi: v("--primary", "#1e2a5a"),
    instrumento: v("--accent", "#e8a33d"),
    chunk: v("--chart-4", "#6b8db5"),
    borde: v("--card", "#ffffff"),
    cuadricula: v("--border", "#e2e6f0"),
    ejes: v("--muted-foreground", "#6b7280"),
    texto: v("--foreground", "#1f2937"),
    fondoEtiqueta: v("--card", "#ffffff"),
  };
}

/**
 * Transformación base datos → pantalla con la MISMA escala en ambos ejes, para
 * no deformar las distancias del plano PCA. El zoom se aplica encima.
 */
export interface EscalaBase {
  k: number;
  aPantalla: (x: number, y: number) => [number, number];
  aDatos: (sx: number, sy: number) => [number, number];
}

export function escalaBase(
  puntos: PuntoEspacio[],
  ancho: number,
  alto: number,
  margen = 48,
): EscalaBase {
  if (puntos.length === 0 || ancho <= 0 || alto <= 0) {
    return { k: 1, aPantalla: () => [ancho / 2, alto / 2], aDatos: () => [0, 0] };
  }
  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;
  for (const p of puntos) {
    minX = Math.min(minX, p.x);
    maxX = Math.max(maxX, p.x);
    minY = Math.min(minY, p.y);
    maxY = Math.max(maxY, p.y);
  }
  const dx = maxX - minX || 1;
  const dy = maxY - minY || 1;
  const k = Math.min((ancho - 2 * margen) / dx, (alto - 2 * margen) / dy);
  const cx = (minX + maxX) / 2;
  const cy = (minY + maxY) / 2;
  return {
    k,
    aPantalla: (x, y) => [ancho / 2 + (x - cx) * k, alto / 2 - (y - cy) * k],
    aDatos: (sx, sy) => [cx + (sx - ancho / 2) / k, cy - (sy - alto / 2) / k],
  };
}

/** Paso "redondo" (1, 2, 5 × 10ⁿ) cercano a `aproximado`, para la cuadrícula. */
export function pasoRedondo(aproximado: number): number {
  if (!(aproximado > 0) || !Number.isFinite(aproximado)) return 1;
  const potencia = 10 ** Math.floor(Math.log10(aproximado));
  const relativo = aproximado / potencia;
  return (relativo < 1.5 ? 1 : relativo < 3.5 ? 2 : relativo < 7.5 ? 5 : 10) * potencia;
}

/** Tamaño de cada tipo de punto (radio en px, a zoom 1). */
export const RADIO: Record<TipoPuntoEspacio, number> = { kpi: 6.5, instrumento: 8, chunk: 2.6 };

/**
 * Forma por tipo (no depender solo del color): KPI = círculo,
 * instrumento = rombo, chunk = punto pequeño.
 */
export function trazarForma(
  ctx: CanvasRenderingContext2D,
  tipo: TipoPuntoEspacio,
  x: number,
  y: number,
  radio: number,
) {
  ctx.beginPath();
  if (tipo === "instrumento") {
    ctx.moveTo(x, y - radio);
    ctx.lineTo(x + radio, y);
    ctx.lineTo(x, y + radio);
    ctx.lineTo(x - radio, y);
    ctx.closePath();
  } else {
    ctx.arc(x, y, radio, 0, Math.PI * 2);
  }
}

/** Recorta un texto para que quepa en `maximo` px. */
export function recortar(ctx: CanvasRenderingContext2D, texto: string, maximo: number): string {
  if (ctx.measureText(texto).width <= maximo) return texto;
  let fin = texto.length;
  while (fin > 1 && ctx.measureText(`${texto.slice(0, fin)}…`).width > maximo) fin -= 1;
  return `${texto.slice(0, fin)}…`;
}
