import { useEffect, useRef } from "react";
import type { ZoomTransform } from "d3-zoom";
import { cn } from "@/lib/utils";
import type { PuntoEspacio } from "@/types";
import { colorPunto, leerPaleta } from "./dibujo";

interface MiniMapaProps {
  /** Coordenadas base (sin zoom) de los puntos visibles. */
  coords: Array<[number, number]>;
  puntos: PuntoEspacio[];
  /** Tamaño del mapa principal. */
  ancho: number;
  alto: number;
  transform: ZoomTransform;
  /** Centra el mapa principal en un punto (coordenadas base). */
  onIrA: (x: number, y: number) => void;
  className?: string | undefined;
}

const ANCHO_MINI = 176;

/** Vista general al acercar: todos los puntos y el recuadro de lo que se ve. */
export function MiniMapa({
  coords,
  puntos,
  ancho,
  alto,
  transform,
  onIrA,
  className,
}: MiniMapaProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const escala = ancho > 0 ? ANCHO_MINI / ancho : 0;
  const altoMini = Math.round(alto * escala);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || escala === 0) return;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = ANCHO_MINI * dpr;
    canvas.height = altoMini * dpr;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const paleta = leerPaleta(canvas);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, ANCHO_MINI, altoMini);
    puntos.forEach((p, i) => {
      const c = coords[i];
      if (!c) return;
      ctx.fillStyle = colorPunto(paleta, p);
      ctx.globalAlpha = p.tipo === "chunk" ? 0.4 : 0.9;
      ctx.fillRect(
        c[0] * escala - 1,
        c[1] * escala - 1,
        p.tipo === "chunk" ? 1.5 : 2.5,
        p.tipo === "chunk" ? 1.5 : 2.5,
      );
    });
    ctx.globalAlpha = 1;
    // Recuadro visible: la ventana del mapa principal en coordenadas base.
    const [x0, y0] = transform.invert([0, 0]);
    const [x1, y1] = transform.invert([ancho, alto]);
    ctx.strokeStyle = paleta.texto;
    ctx.lineWidth = 1.5;
    ctx.strokeRect(x0 * escala, y0 * escala, (x1 - x0) * escala, (y1 - y0) * escala);
  }, [coords, puntos, ancho, alto, transform, escala, altoMini]);

  function alClic(e: React.MouseEvent<HTMLCanvasElement>) {
    const rect = e.currentTarget.getBoundingClientRect();
    onIrA((e.clientX - rect.left) / escala, (e.clientY - rect.top) / escala);
  }

  return (
    <div
      className={cn(
        "overflow-hidden rounded-xl border border-border bg-card/95 shadow-lift backdrop-blur-sm",
        className,
      )}
    >
      <canvas
        ref={canvasRef}
        onClick={alClic}
        aria-label="Mini-mapa: haz clic para moverte a esa zona"
        role="img"
        className="block cursor-pointer"
        style={{ width: ANCHO_MINI, height: altoMini }}
      />
    </div>
  );
}
