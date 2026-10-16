import { useEffect, useRef, useState } from "react";
import type { PuntoEspacio } from "@/types";

const DURACION_MS = 700;

/**
 * Interpola la posición de cada punto (por id) cuando cambian las coordenadas,
 * p. ej. al pasar de la vista normal a la alineada. Los puntos nuevos aparecen
 * directamente en su lugar. Respeta `prefers-reduced-motion`.
 */
export function usePuntosAnimados(destino: PuntoEspacio[]): PuntoEspacio[] {
  const [actuales, setActuales] = useState(destino);
  const actualesRef = useRef(destino);

  useEffect(() => {
    const previos = new Map(actualesRef.current.map((p) => [p.id, p]));
    const seMueve = destino.some((p) => {
      const antes = previos.get(p.id);
      return antes && (antes.x !== p.x || antes.y !== p.y);
    });
    const reducido = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!seMueve || reducido) {
      actualesRef.current = destino;
      setActuales(destino);
      return;
    }

    const desde = destino.map((p) => previos.get(p.id) ?? p);
    const t0 = performance.now();
    let cuadro = 0;
    const paso = (ahora: number) => {
      const u = Math.min(1, (ahora - t0) / DURACION_MS);
      const e = u < 0.5 ? 4 * u ** 3 : 1 - (-2 * u + 2) ** 3 / 2;
      const intermedios =
        u >= 1
          ? destino
          : destino.map((p, i) => {
              const a = desde[i] ?? p;
              return { ...p, x: a.x + (p.x - a.x) * e, y: a.y + (p.y - a.y) * e };
            });
      actualesRef.current = intermedios;
      setActuales(intermedios);
      if (u < 1) cuadro = requestAnimationFrame(paso);
    };
    cuadro = requestAnimationFrame(paso);
    return () => cancelAnimationFrame(cuadro);
  }, [destino]);

  return actuales;
}

/**
 * Igual que `usePuntosAnimados`, para una sola posición (la estrella de la
 * búsqueda). Solo se anima si `clave` no cambia (misma frase, otra vista).
 */
export function usePosicionAnimada<T extends { x: number; y: number; clave: string }>(
  destino: T | null,
): T | null {
  const [actual, setActual] = useState(destino);
  const actualRef = useRef(destino);

  useEffect(() => {
    const antes = actualRef.current;
    const reducido = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!destino || !antes || reducido || antes.clave !== destino.clave) {
      actualRef.current = destino;
      setActual(destino);
      return;
    }
    const t0 = performance.now();
    let cuadro = 0;
    const paso = (ahora: number) => {
      const u = Math.min(1, (ahora - t0) / DURACION_MS);
      const e = u < 0.5 ? 4 * u ** 3 : 1 - (-2 * u + 2) ** 3 / 2;
      const siguiente =
        u >= 1
          ? destino
          : {
              ...destino,
              x: antes.x + (destino.x - antes.x) * e,
              y: antes.y + (destino.y - antes.y) * e,
            };
      actualRef.current = siguiente;
      setActual(siguiente);
      if (u < 1) cuadro = requestAnimationFrame(paso);
    };
    cuadro = requestAnimationFrame(paso);
    return () => cancelAnimationFrame(cuadro);
  }, [destino]);

  return actual;
}
