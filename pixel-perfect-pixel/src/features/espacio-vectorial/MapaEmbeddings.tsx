import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { contourDensity } from "d3-contour";
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
import type { ClusterEspacio, PuntoEspacio, TipoPuntoEspacio } from "@/types";
import { ControlesMapa } from "./ControlesMapa";
import { MiniMapa } from "./MiniMapa";
import { TooltipPunto } from "./TooltipPunto";
import { usePosicionAnimada, usePuntosAnimados } from "./usePuntosAnimados";
import {
  RADIO,
  colorPunto,
  escalaBase,
  leerPaleta,
  pasoRedondo,
  rebote,
  recortar,
  trazarEstrella,
  trazarForma,
  type Paleta,
} from "./dibujo";

/** Frase buscada, ya en coordenadas del plano de la vista actual. */
export interface ConsultaMapa {
  texto: string;
  x: number;
  y: number;
}

/** Zona de densidad de un grupo temático (en coordenadas base, sin zoom). */
interface Zona {
  cluster: number;
  anillos: Array<Array<[number, number]>>;
  etiqueta: string;
  /** Ancla de la etiqueta: centro horizontal, borde superior de los puntos. */
  ancla: [number, number];
}

interface MapaEmbeddingsProps {
  puntos: PuntoEspacio[];
  visibles: ReadonlySet<TipoPuntoEspacio>;
  /** Grupos temáticos de KPIs ocultos desde la leyenda. */
  clustersOcultos: ReadonlySet<number>;
  /** Proporción de varianza explicada por PC1 y PC2 (0–1). */
  varianza: [number, number];
  /** Punto seleccionado (id del mapa) y sus vecinos con su similitud coseno. */
  seleccionId: string | null;
  vecinos: ReadonlyMap<string, number>;
  onSeleccionar: (punto: PuntoEspacio | null) => void;
  /** Ancho (px) que tapa una hoja desde el borde derecho de la ventana; al centrar
   * la selección se descuenta la parte que cae sobre el mapa. */
  reservaDerecha?: number;
  /** Frase de la búsqueda semántica (estrella con líneas a sus vecinos). */
  consulta?: ConsultaMapa | null;
  /** Grupos temáticos: con `mostrarZonas` se dibuja su zona de densidad. */
  clusters?: ClusterEspacio[];
  mostrarZonas?: boolean;
  /** Recorrido guiado: resalta un tipo y atenúa el resto. */
  resaltarTipo?: TipoPuntoEspacio | null;
  /** Controles extra en la esquina superior izquierda (vista alineada…). */
  controles?: ReactNode;
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
/** Duración de la animación de entrada (los puntos crecen desde el centro). */
const DURACION_ENTRADA_MS = 1100;
/** A partir de este zoom aparece el mini-mapa de orientación. */
const ZOOM_MINIMAPA = 1.4;

function porcentaje(v: number) {
  return `${(v * 100).toLocaleString("es-MX", { maximumFractionDigits: 1 })} %`;
}

/**
 * Dispersograma del espacio de embeddings en canvas (escala a miles de puntos):
 * zoom y desplazamiento con d3-zoom, punto más cercano al cursor con d3-delaunay,
 * misma escala en ambos ejes para no deformar el plano PCA.
 */
export function MapaEmbeddings({
  puntos: puntosDestino,
  visibles,
  clustersOcultos,
  varianza,
  seleccionId,
  vecinos,
  onSeleccionar,
  reservaDerecha = 0,
  consulta: consultaDestino = null,
  clusters = [],
  mostrarZonas = false,
  resaltarTipo = null,
  controles,
  children,
}: MapaEmbeddingsProps) {
  // Al cambiar de vista (normal ↔ alineada) los puntos viajan a su nueva posición.
  const puntos = usePuntosAnimados(puntosDestino);
  const consultaDestinoClave = useMemo(
    () => (consultaDestino ? { ...consultaDestino, clave: consultaDestino.texto } : null),
    [consultaDestino],
  );
  const consulta = usePosicionAnimada(consultaDestinoClave);
  const [entrada, setEntrada] = useState(0);
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
        .filter(
          (p) =>
            visibles.has(p.tipo) &&
            !(p.tipo === "kpi" && p.clusterId != null && clustersOcultos.has(p.clusterId)),
        )
        .sort((a, b) => ORDEN.indexOf(a.tipo) - ORDEN.indexOf(b.tipo)),
    [puntos, visibles, clustersOcultos],
  );
  const hayChunks = useMemo(() => puntos.some((p) => p.tipo === "chunk"), [puntos]);
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

  // Animación de entrada: una sola vez, cuando ya hay puntos y tamaño.
  const hayDatos = puntos.length > 0 && tamano.ancho > 0;
  useEffect(() => {
    if (!hayDatos) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setEntrada(1);
      return;
    }
    const t0 = performance.now();
    let cuadro = 0;
    const paso = (ahora: number) => {
      const u = Math.min(1, (ahora - t0) / DURACION_ENTRADA_MS);
      setEntrada(u);
      if (u < 1) cuadro = requestAnimationFrame(paso);
    };
    cuadro = requestAnimationFrame(paso);
    return () => cancelAnimationFrame(cuadro);
  }, [hayDatos]);

  // Zonas de densidad por grupo temático (d3-contour sobre los KPIs visibles).
  const zonas = useMemo<Zona[]>(() => {
    if (!mostrarZonas || !visibles.has("kpi") || tamano.ancho === 0) return [];
    const porCluster = new Map<number, Array<[number, number]>>();
    visiblesLista.forEach((p, i) => {
      const c = coordsBase[i];
      if (p.tipo !== "kpi" || p.clusterId == null || !c) return;
      const lista = porCluster.get(p.clusterId) ?? [];
      lista.push(c);
      porCluster.set(p.clusterId, lista);
    });
    const ancho = Math.round(tamano.ancho);
    const alto = Math.round(tamano.alto);
    const banda = Math.max(14, Math.min(ancho, alto) * 0.045);
    const salida: Zona[] = [];
    for (const [cluster, pts] of porCluster) {
      const niveles = contourDensity<[number, number]>()
        .x((d) => d[0])
        .y((d) => d[1])
        .size([ancho, alto])
        .cellSize(4)
        .bandwidth(banda)
        .thresholds(10)(pts);
      const maximo = niveles[niveles.length - 1]?.value ?? 0;
      // Nivel cercano al 22 % del máximo: envuelve el grupo sin inflarse.
      const elegido = niveles
        .filter((n) => n.coordinates.length > 0)
        .reduce<(typeof niveles)[number] | null>(
          (mejor, n) =>
            !mejor || Math.abs(n.value - maximo * 0.22) < Math.abs(mejor.value - maximo * 0.22)
              ? n
              : mejor,
          null,
        );
      if (!elegido) continue;
      const anillos = elegido.coordinates.flatMap((poligono) =>
        poligono.map((anillo) => anillo.map(([x, y]) => [x, y] as [number, number])),
      );
      const xs = pts.map((p) => p[0]);
      const ys = pts.map((p) => p[1]);
      salida.push({
        cluster,
        anillos,
        etiqueta: clusters.find((c) => c.id === cluster)?.etiqueta ?? `Grupo ${cluster + 1}`,
        ancla: [(Math.min(...xs) + Math.max(...xs)) / 2, Math.min(...ys)],
      });
    }
    return salida;
  }, [mostrarZonas, visibles, visiblesLista, coordsBase, tamano.ancho, tamano.alto, clusters]);

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

    // Zonas de los grupos temáticos (debajo de todo; se escalan con el zoom).
    if (zonas.length) {
      ctx.save();
      ctx.setTransform(
        dpr * transform.k,
        0,
        0,
        dpr * transform.k,
        dpr * transform.x,
        dpr * transform.y,
      );
      for (const z of zonas) {
        const color = paleta.clusters[z.cluster % paleta.clusters.length] ?? paleta.kpi;
        ctx.beginPath();
        for (const anillo of z.anillos) {
          anillo.forEach(([x, y], i) => (i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)));
          ctx.closePath();
        }
        ctx.globalAlpha = (seleccionId || consulta ? 0.05 : 0.11) * entrada;
        ctx.fillStyle = color;
        ctx.fill("evenodd");
        ctx.globalAlpha = (seleccionId || consulta ? 0.15 : 0.4) * entrada;
        ctx.lineWidth = 1.5 / transform.k;
        ctx.strokeStyle = color;
        ctx.stroke();
      }
      ctx.restore();
      ctx.globalAlpha = 1;
    }

    // Puntos.
    const crecimiento = Math.min(1.8, 0.85 + 0.15 * transform.k);
    // Entrada escalonada: primero los puntos cercanos al centro.
    const radioEntrada = (pos: [number, number]) => {
      if (entrada >= 1) return 1;
      const d = Math.hypot(pos[0] - ancho / 2, pos[1] - alto / 2) / Math.hypot(ancho / 2, alto / 2);
      return Math.max(0, rebote((entrada - Math.min(1, d) * 0.45) / 0.55));
    };
    const posTodos: Array<[number, number]> = coordsBase.map((c) => transform.apply(c));
    const enPantalla: Array<[number, number] | null> = posTodos.map(([sx, sy]) =>
      sx < -20 || sy < -20 || sx > ancho + 20 || sy > alto + 20 ? null : [sx, sy],
    );
    const iSeleccion = seleccionId ? visiblesLista.findIndex((p) => p.id === seleccionId) : -1;
    // Hay foco si hay un punto seleccionado o una frase buscada.
    const haySeleccion = seleccionId !== null || consulta !== null;
    const destacado = (p: PuntoEspacio) => p.id === seleccionId || vecinos.has(p.id);
    const posConsulta: [number, number] | null = consulta
      ? transform.apply(base.aPantalla(consulta.x, consulta.y))
      : null;

    // Líneas a los vecinos (grosor y opacidad según la similitud coseno).
    const origen = posConsulta ?? (iSeleccion >= 0 ? posTodos[iSeleccion] : undefined);
    if (origen) {
      visiblesLista.forEach((p, i) => {
        const sim = vecinos.get(p.id);
        const destino = posTodos[i];
        if (sim === undefined || !destino || p.id === seleccionId) return;
        ctx.beginPath();
        ctx.moveTo(origen[0], origen[1]);
        ctx.lineTo(destino[0], destino[1]);
        ctx.lineWidth = 1 + 4 * Math.max(0, sim) ** 2;
        ctx.globalAlpha = 0.3 + 0.55 * Math.max(0, sim);
        ctx.strokeStyle = colorPunto(paleta, p);
        ctx.stroke();
      });
      ctx.globalAlpha = 1;
    }

    visiblesLista.forEach((p, i) => {
      const pos = enPantalla[i];
      if (!pos) return;
      const resaltado = haySeleccion && destacado(p);
      const escalaEntrada = radioEntrada(pos);
      if (escalaEntrada <= 0) return;
      trazarForma(
        ctx,
        p.tipo,
        pos[0],
        pos[1],
        RADIO[p.tipo] * crecimiento * (resaltado ? 1.25 : 1) * escalaEntrada,
      );
      ctx.fillStyle = colorPunto(paleta, p);
      const alfa = p.tipo === "chunk" && !resaltado ? 0.55 : 1;
      const atenuado =
        (haySeleccion && !resaltado) || (resaltarTipo !== null && p.tipo !== resaltarTipo);
      ctx.globalAlpha = atenuado ? alfa * 0.16 : alfa;
      ctx.fill();
      if (p.tipo !== "chunk" || resaltado) {
        ctx.lineWidth = 1.75;
        ctx.strokeStyle = paleta.borde;
        ctx.stroke();
      }
    });
    ctx.globalAlpha = 1;

    // Anillo del punto seleccionado.
    const posSel = iSeleccion >= 0 ? enPantalla[iSeleccion] : null;
    const puntoSel = iSeleccion >= 0 ? visiblesLista[iSeleccion] : undefined;
    if (posSel && puntoSel) {
      ctx.lineWidth = 3;
      ctx.strokeStyle = paleta.texto;
      trazarForma(ctx, puntoSel.tipo, posSel[0], posSel[1], RADIO[puntoSel.tipo] * crecimiento + 8);
      ctx.stroke();
    }

    // Estrella de la frase buscada, con halo.
    if (posConsulta && consulta) {
      ctx.beginPath();
      ctx.arc(posConsulta[0], posConsulta[1], 26, 0, Math.PI * 2);
      ctx.fillStyle = paleta.consulta;
      ctx.globalAlpha = 0.16;
      ctx.fill();
      ctx.globalAlpha = 1;
      trazarEstrella(ctx, posConsulta[0], posConsulta[1], 14);
      ctx.fillStyle = paleta.consulta;
      ctx.fill();
      ctx.lineWidth = 2.5;
      ctx.strokeStyle = paleta.borde;
      ctx.stroke();
    }

    // Etiquetas: siempre la selección y sus vecinos (con su similitud); el resto al acercar.
    ctx.textBaseline = "middle";
    const ocupado: Array<[number, number, number, number]> = [];
    if (posConsulta && consulta) {
      ctx.font = "800 14px Nunito, ui-sans-serif, system-ui, sans-serif";
      const texto = `«${recortar(ctx, consulta.texto, 260)}»`;
      const x = posConsulta[0] + 22;
      const anchoTexto = ctx.measureText(texto).width;
      ocupado.push([x - 2, posConsulta[1] - 10, x + anchoTexto + 2, posConsulta[1] + 10]);
      ctx.lineWidth = 5;
      ctx.strokeStyle = paleta.fondoEtiqueta;
      ctx.strokeText(texto, x, posConsulta[1]);
      ctx.fillStyle = paleta.consulta;
      ctx.fillText(texto, x, posConsulta[1]);
    }
    const rotular = (p: PuntoEspacio, pos: [number, number], fuerte: boolean) => {
      ctx.font = `${fuerte ? 800 : 600} 13px Nunito, ui-sans-serif, system-ui, sans-serif`;
      const sim = vecinos.get(p.id);
      const sufijo =
        sim !== undefined && p.id !== seleccionId ? ` · ${Math.round(sim * 100)} %` : "";
      const texto = recortar(ctx, p.etiqueta, fuerte ? 240 : 200) + sufijo;
      const x = pos[0] + RADIO[p.tipo] * crecimiento + (fuerte ? 10 : 6);
      const anchoTexto = ctx.measureText(texto).width;
      const caja: [number, number, number, number] = [
        x - 2,
        pos[1] - 9,
        x + anchoTexto + 2,
        pos[1] + 9,
      ];
      if (ocupado.some((o) => caja[0] < o[2] && caja[2] > o[0] && caja[1] < o[3] && caja[3] > o[1]))
        return;
      ocupado.push(caja);
      ctx.lineWidth = 4;
      ctx.strokeStyle = paleta.fondoEtiqueta;
      ctx.strokeText(texto, x, pos[1]);
      ctx.fillStyle = paleta.texto;
      ctx.fillText(texto, x, pos[1]);
    };
    if (posSel && puntoSel) rotular(puntoSel, posSel, true);
    if (haySeleccion) {
      visiblesLista.forEach((p, i) => {
        const pos = enPantalla[i];
        if (pos && p.tipo !== "chunk" && p.id !== seleccionId && vecinos.has(p.id)) {
          rotular(p, pos, true);
        }
      });
    } else if (transform.k >= ZOOM_ETIQUETAS) {
      visiblesLista.forEach((p, i) => {
        const pos = enPantalla[i];
        if (pos && p.tipo !== "chunk") rotular(p, pos, false);
      });
    } else if (zonas.length && entrada >= 1) {
      // Sin foco y sin acercar: el nombre de cada zona sobre su grupo.
      ctx.font = "800 12px Nunito, ui-sans-serif, system-ui, sans-serif";
      ctx.textAlign = "center";
      for (const z of zonas) {
        const [ax, sy] = transform.apply(z.ancla);
        const texto = recortar(ctx, z.etiqueta.toUpperCase(), 190);
        const w = ctx.measureText(texto).width;
        // Dentro del mapa aunque el grupo esté pegado a un borde.
        const sx = Math.min(Math.max(ax, w / 2 + 56), ancho - w / 2 - 72);
        const y = Math.max(14, sy - 18);
        const caja: [number, number, number, number] = [
          sx - w / 2 - 2,
          y - 8,
          sx + w / 2 + 2,
          y + 8,
        ];
        if (
          ocupado.some((o) => caja[0] < o[2] && caja[2] > o[0] && caja[1] < o[3] && caja[3] > o[1])
        )
          continue;
        ocupado.push(caja);
        ctx.lineWidth = 4;
        ctx.strokeStyle = paleta.fondoEtiqueta;
        ctx.strokeText(texto, sx, y);
        ctx.fillStyle = paleta.clusters[z.cluster % paleta.clusters.length] ?? paleta.texto;
        ctx.fillText(texto, sx, y);
      }
      ctx.textAlign = "start";
    }

    // Punto bajo el cursor.
    if (hover) {
      const i = visiblesLista.indexOf(hover.punto);
      const pos = i >= 0 ? enPantalla[i] : null;
      if (pos) {
        ctx.lineWidth = 2.5;
        ctx.strokeStyle = colorPunto(paleta, hover.punto);
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
  }, [
    tamano,
    transform,
    base,
    coordsBase,
    visiblesLista,
    hover,
    seleccionId,
    vecinos,
    consulta,
    zonas,
    entrada,
    resaltarTipo,
  ]);

  // La frase buscada se centra si cae fuera de la vista.
  useEffect(() => {
    if (!consultaDestino) return;
    const c = escalaBase(puntosDestino, tamano.ancho, tamano.alto).aPantalla(
      consultaDestino.x,
      consultaDestino.y,
    );
    const actual = canvasRef.current ? zoomTransform(canvasRef.current) : transform;
    const [sx, sy] = actual.apply(c);
    const derecha = contenedorRef.current?.getBoundingClientRect().right ?? window.innerWidth;
    const tapado = Math.max(0, derecha - (window.innerWidth - reservaDerecha));
    const anchoLibre = Math.max(120, tamano.ancho - tapado);
    if (sx > 80 && sy > 80 && sx < anchoLibre - 80 && sy < tamano.alto - 80) return;
    animarA((t) =>
      zoomIdentity.translate(anchoLibre / 2 - c[0] * t.k, tamano.alto / 2 - c[1] * t.k).scale(t.k),
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [consultaDestino, puntosDestino, reservaDerecha]);

  /** Mini-mapa: centra la vista en un punto (coordenadas base). */
  const irA = useCallback(
    (bx: number, by: number) =>
      animarA((t) =>
        zoomIdentity.translate(tamano.ancho / 2 - bx * t.k, tamano.alto / 2 - by * t.k).scale(t.k),
      ),
    [animarA, tamano.ancho, tamano.alto],
  );

  // Si el punto seleccionado queda fuera de la vista (al elegirlo desde el panel o
  // al cambiar de vista), se centra. Se usa su posición FINAL, no la animada.
  useEffect(() => {
    if (!seleccionId) return;
    const destino = puntosDestino.find((p) => p.id === seleccionId);
    if (!destino) return;
    const c = escalaBase(puntosDestino, tamano.ancho, tamano.alto).aPantalla(destino.x, destino.y);
    const actual = canvasRef.current ? zoomTransform(canvasRef.current) : transform;
    const [sx, sy] = actual.apply(c);
    const margen = 60;
    const derecha = contenedorRef.current?.getBoundingClientRect().right ?? window.innerWidth;
    const tapado = Math.max(0, derecha - (window.innerWidth - reservaDerecha));
    const anchoLibre = Math.max(120, tamano.ancho - tapado);
    const dentro =
      sx > margen && sy > margen && sx < anchoLibre - margen && sy < tamano.alto - margen;
    if (dentro) return;
    animarA((t) =>
      zoomIdentity.translate(anchoLibre / 2 - c[0] * t.k, tamano.alto / 2 - c[1] * t.k).scale(t.k),
    );
    // Solo al cambiar la selección, la vista o el espacio libre; no en cada zoom.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seleccionId, puntosDestino, reservaDerecha]);

  /** Punto visible más cercano al cursor (si está a menos de RADIO_HOVER px). */
  function puntoEn(e: React.MouseEvent<HTMLCanvasElement>) {
    if (!delaunay) return null;
    const rect = e.currentTarget.getBoundingClientRect();
    const sx = e.clientX - rect.left;
    const sy = e.clientY - rect.top;
    const [bx, by] = transform.invert([sx, sy]);
    const i = delaunay.find(bx, by);
    const coords = coordsBase[i];
    const punto = visiblesLista[i];
    if (!coords || !punto) return null;
    const [px, py] = transform.apply(coords);
    return Math.hypot(px - sx, py - sy) > RADIO_HOVER ? null : { punto, x: px, y: py };
  }

  function alMover(e: React.MouseEvent<HTMLCanvasElement>) {
    if (arrastrando) return;
    const encontrado = puntoEn(e);
    if (!encontrado) return setHover(null);
    if (hover?.punto !== encontrado.punto) setHover(encontrado);
  }

  function alClic(e: React.MouseEvent<HTMLCanvasElement>) {
    const encontrado = puntoEn(e);
    onSeleccionar(encontrado && encontrado.punto.id !== seleccionId ? encontrado.punto : null);
  }

  function alTeclear(e: React.KeyboardEvent<HTMLCanvasElement>) {
    if (e.key === "+" || e.key === "=") acercar();
    else if (e.key === "-" || e.key === "_") alejar();
    else if (e.key === "0") restablecer();
    else if (e.key === "Escape" && (seleccionId || consultaDestino)) onSeleccionar(null);
    else return;
    e.preventDefault();
  }

  const resumenAccesible = `Mapa con ${visiblesLista.filter((p) => p.tipo === "kpi").length} KPIs y ${
    visiblesLista.filter((p) => p.tipo === "instrumento").length
  } instrumentos${hayChunks && visibles.has("chunk") ? " y chunks" : ""}. Usa + y − para acercar o alejar, 0 para restablecer y Escape para quitar la selección.`;

  return (
    <div ref={contenedorRef} className="relative h-full w-full overflow-hidden">
      <canvas
        ref={canvasRef}
        role="img"
        tabIndex={0}
        aria-label={resumenAccesible}
        onMouseMove={alMover}
        onClick={alClic}
        onMouseLeave={() => setHover(null)}
        onKeyDown={alTeclear}
        className="absolute inset-0 h-full w-full touch-none rounded-[inherit] focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-ring/30"
        style={{ cursor: arrastrando ? "grabbing" : hover ? "pointer" : "grab" }}
      />

      {/* Títulos de los ejes: componentes principales con su varianza */}
      <p className="pointer-events-none absolute bottom-3 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full bg-card/85 px-3 py-1 text-xs font-bold text-muted-foreground shadow-card backdrop-blur-sm">
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

      {controles && <div className="absolute left-4 right-20 top-4">{controles}</div>}

      {transform.k >= ZOOM_MINIMAPA && (
        <MiniMapa
          coords={coordsBase}
          puntos={visiblesLista}
          ancho={tamano.ancho}
          alto={tamano.alto}
          transform={transform}
          onIrA={irA}
          className="absolute bottom-12 left-4 hidden sm:block"
        />
      )}

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
