import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Delaunay } from "d3-delaunay";
import { select } from "d3-selection";
import {
  zoom,
  zoomIdentity,
  zoomTransform,
  type D3ZoomEvent,
  type ZoomBehavior,
  type ZoomTransform,
} from "d3-zoom";
import { MoveHorizontal } from "lucide-react";
import type { PuntoEspacio, TipoPuntoEspacio } from "@/types";
import { ControlesMapa } from "./ControlesMapa";
import { TooltipPunto } from "./TooltipPunto";
import {
  RADIO,
  escalaBase,
  leerPaleta,
  pasoRedondo,
  recortar,
  trazarForma,
  type Paleta,
} from "./dibujo";

interface MapaEmbeddingsProps {
  puntos: PuntoEspacio[];
  visibles: ReadonlySet<TipoPuntoEspacio>;
  /** Proporción de varianza explicada por PC1 y PC2 (0–1). */
  varianza: [number, number];
  /** Capa superpuesta (p. ej. aviso de "sin instrumentos"). */
  children?: ReactNode;
}

const ZOOM_MIN = 0.5;
const ZOOM_MAX = 24;
/** A partir de este zoom se rotulan los puntos. */
const ZOOM_ETIQUETAS = 2.2;
/** Distancia máxima (px) entre cursor y punto para mostrar el tooltip. */
const RADIO_HOVER = 18;
/** Orden de dibujo: lo más importante queda arriba. */
const ORDEN: TipoPuntoEspacio[] = ["chunk", "kpi", "instrumento"];

function porcentaje(v: number) {
  return `${(v * 100).toLocaleString("es-MX", { maximumFractionDigits: 1 })} %`;
}

/**
 * Dispersograma del espacio de embeddings en canvas (escala a miles de puntos):
 * zoom y desplazamiento con d3-zoom, punto más cercano al cursor con d3-delaunay,
 * misma escala en ambos ejes para no deformar el plano PCA.
 */
export function MapaEmbeddings({ puntos, visibles, varianza, children }: MapaEmbeddingsProps) {
  const contenedorRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const zoomRef = useRef<ZoomBehavior<HTMLCanvasElement, unknown> | null>(null);
  const paletaRef = useRef<Paleta | null>(null);
  const [tamano, setTamano] = useState({ ancho: 0, alto: 0 });
  const [transform, setTransform] = useState<ZoomTransform>(zoomIdentity);
  const [arrastrando, setArrastrando] = useState(false);
  const [hover, setHover] = useState<{ punto: PuntoEspacio; x: number; y: number } | null>(null);

  const visiblesLista = useMemo(
    () =>
      puntos
        .filter((p) => visibles.has(p.tipo))
        .sort((a, b) => ORDEN.indexOf(a.tipo) - ORDEN.indexOf(b.tipo)),
    [puntos, visibles],
  );
  // La escala usa TODOS los puntos: ocultar un tipo no mueve el mapa.
  const base = useMemo(
    () => escalaBase(puntos, tamano.ancho, tamano.alto),
    [puntos, tamano.ancho, tamano.alto],
  );
  const coordsBase = useMemo(
    () => visiblesLista.map((p) => base.aPantalla(p.x, p.y)),
    [visiblesLista, base],
  );
  const delaunay = useMemo(
    () => (coordsBase.length ? Delaunay.from(coordsBase) : null),
    [coordsBase],
  );

  // Tamaño del contenedor.
  useEffect(() => {
    const el = contenedorRef.current;
    if (!el) return;
    paletaRef.current = leerPaleta(el);
    const ro = new ResizeObserver(([entrada]) => {
      if (!entrada) return;
      const { width, height } = entrada.contentRect;
      setTamano({ ancho: Math.round(width), alto: Math.round(height) });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Zoom y desplazamiento.
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const comportamiento = zoom<HTMLCanvasElement, unknown>()
      .scaleExtent([ZOOM_MIN, ZOOM_MAX])
      .on("start", (e: D3ZoomEvent<HTMLCanvasElement, unknown>) => {
        if (e.sourceEvent?.type === "mousedown") setArrastrando(true);
      })
      .on("zoom", (e: D3ZoomEvent<HTMLCanvasElement, unknown>) => {
        setTransform(e.transform);
        setHover(null);
      })
      .on("end", () => setArrastrando(false));
    const seleccion = select(canvas);
    seleccion.call(comportamiento).on("dblclick.zoom", null);
    zoomRef.current = comportamiento;
    return () => {
      seleccion.on(".zoom", null);
    };
  }, []);

  // Animación suave entre dos transformaciones (respeta movimiento reducido).
  const animarA = useCallback((destino: (actual: ZoomTransform) => ZoomTransform) => {
    const canvas = canvasRef.current;
    const comportamiento = zoomRef.current;
    if (!canvas || !comportamiento) return;
    const seleccion = select(canvas);
    const inicio = zoomTransform(canvas);
    const fin = destino(inicio);
    const reducido = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const duracion = reducido ? 0 : 320;
    const t0 = performance.now();
    const paso = (ahora: number) => {
      const u = duracion ? Math.min(1, (ahora - t0) / duracion) : 1;
      const e = 1 - (1 - u) ** 3;
      const k = inicio.k + (fin.k - inicio.k) * e;
      const x = inicio.x + (fin.x - inicio.x) * e;
      const y = inicio.y + (fin.y - inicio.y) * e;
      seleccion.call(comportamiento.transform, zoomIdentity.translate(x, y).scale(k));
      if (u < 1) requestAnimationFrame(paso);
    };
    requestAnimationFrame(paso);
  }, []);

  const escalarEnCentro = useCallback(
    (factor: number) =>
      animarA((t) => {
        const k = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, t.k * factor));
        const cx = tamano.ancho / 2;
        const cy = tamano.alto / 2;
        return zoomIdentity
          .translate(cx - ((cx - t.x) * k) / t.k, cy - ((cy - t.y) * k) / t.k)
          .scale(k);
      }),
    [animarA, tamano.ancho, tamano.alto],
  );
  const acercar = useCallback(() => escalarEnCentro(1.6), [escalarEnCentro]);
  const alejar = useCallback(() => escalarEnCentro(1 / 1.6), [escalarEnCentro]);
  const restablecer = useCallback(() => animarA(() => zoomIdentity), [animarA]);

  // Dibujo.
  useEffect(() => {
    const canvas = canvasRef.current;
    const paleta = paletaRef.current;
    const { ancho, alto } = tamano;
    if (!canvas || !paleta || ancho === 0 || alto === 0) return;
    const dpr = window.devicePixelRatio || 1;
    if (canvas.width !== ancho * dpr || canvas.height !== alto * dpr) {
      canvas.width = ancho * dpr;
      canvas.height = alto * dpr;
    }
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, ancho, alto);

    // Cuadrícula en coordenadas del plano (se mueve con el zoom).
    const escala = base.k * transform.k;
    const paso = pasoRedondo(90 / escala);
    const [x0, y1] = base.aDatos(...transform.invert([0, 0]));
    const [x1, y0] = base.aDatos(...transform.invert([ancho, alto]));
    const aPantalla = (x: number, y: number) => transform.apply(base.aPantalla(x, y));
    ctx.lineWidth = 1;
    ctx.strokeStyle = paleta.cuadricula;
    ctx.globalAlpha = 0.7;
    ctx.beginPath();
    for (let x = Math.ceil(x0 / paso) * paso; x <= x1; x += paso) {
      const [sx] = aPantalla(x, 0);
      ctx.moveTo(Math.round(sx) + 0.5, 0);
      ctx.lineTo(Math.round(sx) + 0.5, alto);
    }
    for (let y = Math.ceil(y0 / paso) * paso; y <= y1; y += paso) {
      const [, sy] = aPantalla(0, y);
      ctx.moveTo(0, Math.round(sy) + 0.5);
      ctx.lineTo(ancho, Math.round(sy) + 0.5);
    }
    ctx.stroke();
    // Ejes por el centroide del conjunto (origen del PCA).
    const [ox, oy] = aPantalla(0, 0);
    ctx.globalAlpha = 0.55;
    ctx.strokeStyle = paleta.ejes;
    ctx.setLineDash([5, 5]);
    ctx.beginPath();
    ctx.moveTo(ox, 0);
    ctx.lineTo(ox, alto);
    ctx.moveTo(0, oy);
    ctx.lineTo(ancho, oy);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.globalAlpha = 1;

    // Puntos.
    const crecimiento = Math.min(1.8, 0.85 + 0.15 * transform.k);
    const color: Record<TipoPuntoEspacio, string> = {
      kpi: paleta.kpi,
      instrumento: paleta.instrumento,
      chunk: paleta.chunk,
    };
    const enPantalla: Array<[number, number] | null> = coordsBase.map(([bx, by]) => {
      const [sx, sy] = transform.apply([bx, by]);
      return sx < -20 || sy < -20 || sx > ancho + 20 || sy > alto + 20 ? null : [sx, sy];
    });
    visiblesLista.forEach((p, i) => {
      const pos = enPantalla[i];
      if (!pos) return;
      trazarForma(ctx, p.tipo, pos[0], pos[1], RADIO[p.tipo] * crecimiento);
      ctx.fillStyle = color[p.tipo];
      ctx.globalAlpha = p.tipo === "chunk" ? 0.55 : 1;
      ctx.fill();
      if (p.tipo !== "chunk") {
        ctx.lineWidth = 1.75;
        ctx.strokeStyle = paleta.borde;
        ctx.stroke();
      }
    });
    ctx.globalAlpha = 1;

    // Etiquetas al acercar (evitando encimarse).
    if (transform.k >= ZOOM_ETIQUETAS) {
      ctx.font = "600 13px Nunito, ui-sans-serif, system-ui, sans-serif";
      ctx.textBaseline = "middle";
      const ocupado: Array<[number, number, number, number]> = [];
      visiblesLista.forEach((p, i) => {
        const pos = enPantalla[i];
        if (!pos || p.tipo === "chunk") return;
        const texto = recortar(ctx, p.etiqueta, 200);
        const x = pos[0] + RADIO[p.tipo] * crecimiento + 6;
        const ancho = ctx.measureText(texto).width;
        const caja: [number, number, number, number] = [
          x - 2,
          pos[1] - 9,
          x + ancho + 2,
          pos[1] + 9,
        ];
        if (
          ocupado.some((o) => caja[0] < o[2] && caja[2] > o[0] && caja[1] < o[3] && caja[3] > o[1])
        )
          return;
        ocupado.push(caja);
        ctx.lineWidth = 4;
        ctx.strokeStyle = paleta.fondoEtiqueta;
        ctx.strokeText(texto, x, pos[1]);
        ctx.fillStyle = paleta.texto;
        ctx.fillText(texto, x, pos[1]);
      });
    }

    // Punto bajo el cursor.
    if (hover) {
      const i = visiblesLista.indexOf(hover.punto);
      const pos = i >= 0 ? enPantalla[i] : null;
      if (pos) {
        ctx.lineWidth = 2.5;
        ctx.strokeStyle = color[hover.punto.tipo];
        trazarForma(
          ctx,
          hover.punto.tipo,
          pos[0],
          pos[1],
          RADIO[hover.punto.tipo] * crecimiento + 6,
        );
        ctx.stroke();
      }
    }
  }, [tamano, transform, base, coordsBase, visiblesLista, hover]);

  function alMover(e: React.MouseEvent<HTMLCanvasElement>) {
    if (arrastrando || !delaunay) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const sx = e.clientX - rect.left;
    const sy = e.clientY - rect.top;
    const [bx, by] = transform.invert([sx, sy]);
    const i = delaunay.find(bx, by);
    const coords = coordsBase[i];
    const punto = visiblesLista[i];
    if (!coords || !punto) return setHover(null);
    const [px, py] = transform.apply(coords);
    if (Math.hypot(px - sx, py - sy) > RADIO_HOVER) return setHover(null);
    if (hover?.punto !== punto) setHover({ punto, x: px, y: py });
  }

  function alTeclear(e: React.KeyboardEvent<HTMLCanvasElement>) {
    if (e.key === "+" || e.key === "=") acercar();
    else if (e.key === "-" || e.key === "_") alejar();
    else if (e.key === "0") restablecer();
    else return;
    e.preventDefault();
  }

  const resumenAccesible = `Mapa con ${visiblesLista.filter((p) => p.tipo === "kpi").length} KPIs y ${
    visiblesLista.filter((p) => p.tipo === "instrumento").length
  } instrumentos. Usa + y − para acercar o alejar y 0 para restablecer.`;

  return (
    <div ref={contenedorRef} className="relative h-full w-full overflow-hidden">
      <canvas
        ref={canvasRef}
        role="img"
        tabIndex={0}
        aria-label={resumenAccesible}
        onMouseMove={alMover}
        onMouseLeave={() => setHover(null)}
        onKeyDown={alTeclear}
        className="absolute inset-0 h-full w-full touch-none rounded-[inherit] focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-ring/30"
        style={{ cursor: arrastrando ? "grabbing" : hover ? "pointer" : "grab" }}
      />

      {/* Títulos de los ejes: componentes principales con su varianza */}
      <p className="pointer-events-none absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full bg-card/85 px-3 py-1 text-xs font-bold text-muted-foreground shadow-card backdrop-blur-sm">
        PC1 · {porcentaje(varianza[0])} de la varianza →
      </p>
      <p className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 rotate-180 whitespace-nowrap rounded-full bg-card/85 px-1 py-3 text-xs font-bold text-muted-foreground shadow-card backdrop-blur-sm [writing-mode:vertical-rl]">
        PC2 · {porcentaje(varianza[1])} →
      </p>

      <ControlesMapa
        zoom={transform.k}
        onAcercar={acercar}
        onAlejar={alejar}
        onRestablecer={restablecer}
        className="absolute right-4 top-4"
      />

      <p className="pointer-events-none absolute bottom-3 right-4 hidden items-center gap-1.5 text-xs text-muted-foreground lg:flex">
        <MoveHorizontal className="size-4" aria-hidden /> Rueda para acercar · arrastra para mover
      </p>

      {hover && !arrastrando && (
        <TooltipPunto
          punto={hover.punto}
          x={hover.x}
          y={hover.y}
          ancho={tamano.ancho}
          alto={tamano.alto}
        />
      )}

      {children}

      {/* Lista equivalente para lectores de pantalla */}
      <ul className="sr-only">
        {visiblesLista
          .filter((p) => p.tipo !== "chunk")
          .map((p) => (
            <li key={p.id}>
              {p.tipo === "kpi" ? "KPI" : "Instrumento"}: {p.etiqueta}. {p.resumen}
            </li>
          ))}
      </ul>
    </div>
  );
}
