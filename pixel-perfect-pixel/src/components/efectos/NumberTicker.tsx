import { useEffect, useRef } from "react";
import { animate, useInView, useReducedMotion } from "motion/react";
import { cn } from "@/lib/utils";

interface NumberTickerProps {
  /** Valor tal como llega del backend (p. ej. "128", "84%", "3.5 h"). */
  valor: string;
  className?: string;
}

const PATRON = /^(\D*?)(-?[\d.,]*\d)(.*)$/;

/**
 * Contador animado (inspirado en NumberTicker de Magic UI). Si el valor no
 * empieza con un número se muestra tal cual; respeta `prefers-reduced-motion`.
 */
export function NumberTicker({ valor, className }: NumberTickerProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const visible = useInView(ref, { once: true, margin: "-40px" });
  const reducido = useReducedMotion();

  const partes = PATRON.exec(valor.trim());
  const prefijo = partes?.[1] ?? "";
  const textoNumero = partes?.[2] ?? "";
  const sufijo = partes?.[3] ?? "";
  // "1,234.5" → 1234.5 ; decimales según el texto original.
  const numero = Number(textoNumero.replace(/,/g, ""));
  const decimales = textoNumero.includes(".") ? (textoNumero.split(".")[1]?.length ?? 0) : 0;
  const animable = partes !== null && Number.isFinite(numero);

  useEffect(() => {
    const nodo = ref.current;
    if (!nodo || !animable || !visible || reducido) return;
    const formato = new Intl.NumberFormat("es-MX", {
      minimumFractionDigits: decimales,
      maximumFractionDigits: decimales,
    });
    const control = animate(0, numero, {
      duration: 1.2,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => {
        nodo.textContent = `${prefijo}${formato.format(v)}${sufijo}`;
      },
    });
    return () => control.stop();
  }, [animable, visible, reducido, numero, decimales, prefijo, sufijo]);

  return (
    <span ref={ref} className={cn("tabular-nums", className)}>
      {valor}
    </span>
  );
}
