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
  /** Un color por grupo temático de KPIs (se repiten si hay más de 8). */
  clusters: string[];
  /** Estrella de la búsqueda semántica. */
  consulta: string;
}

/** Número de colores de grupo definidos en styles.css (--cluster-1…8). */
export const NUM_COLORES_CLUSTER = 8;

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
    consulta: v("--primary-glow", "#4b4bd6"),
    clusters: Array.from({ length: NUM_COLORES_CLUSTER }, (_, i) =>
      v(`--cluster-${i + 1}`, v("--primary", "#1e2a5a")),
    ),
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

/** Clase de Tailwind con el color de un grupo (para la leyenda y el panel). */
export function claseCluster(id: number | null | undefined): string {
  const clases = [
    "bg-cluster-1",
    "bg-cluster-2",
    "bg-cluster-3",
    "bg-cluster-4",
    "bg-cluster-5",
    "bg-cluster-6",
    "bg-cluster-7",
    "bg-cluster-8",
  ];
  return id == null ? "bg-primary" : (clases[id % clases.length] ?? "bg-primary");
}

/** Color de canvas de un punto: KPIs por grupo, el resto por tipo. */
export function colorPunto(paleta: Paleta, p: PuntoEspacio): string {
  if (p.tipo === "kpi" && p.clusterId != null) {
    return paleta.clusters[p.clusterId % paleta.clusters.length] ?? paleta.kpi;
  }
  return paleta[p.tipo];
}

/** Estrella de cinco puntas (la frase buscada en el mapa). */
export function trazarEstrella(ctx: CanvasRenderingContext2D, x: number, y: number, radio: number) {
  ctx.beginPath();
  for (let i = 0; i < 10; i++) {
    const r = i % 2 === 0 ? radio : radio * 0.45;
    const a = -Math.PI / 2 + (i * Math.PI) / 5;
    const px = x + r * Math.cos(a);
    const py = y + r * Math.sin(a);
    if (i === 0) ctx.moveTo(px, py);
    else ctx.lineTo(px, py);
  }
  ctx.closePath();
}

/** Curva de entrada con un pequeño rebote (0 → 1). */
export function rebote(u: number): number {
  const c1 = 1.70158;
  const c3 = c1 + 1;
  const v = Math.min(1, Math.max(0, u));
  return 1 + c3 * (v - 1) ** 3 + c1 * (v - 1) ** 2;
}
