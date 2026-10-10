import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import {
  Background,
  Controls,
  ReactFlow,
  ReactFlowProvider,
  type Edge,
  type Node,
  type NodeMouseHandler,
  type NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { AlertTriangle, Loader2, Share2 } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { guardarContexto } from "@/api/chat";
import {
  getAcervoGrafo,
  guardarGrafoInvestigacion,
  recomendarGrafo,
  type AristaGrafo,
  type NodoGrafo,
  type Recomendacion,
} from "@/api/grafo";
import { useAuth } from "@/features/auth/AuthContext";
import { useResearch } from "@/features/research/ResearchContext";
import type { ContextoInvestigacion } from "@/types";
import { NodoInstrumento, type DatosNodoInstrumento } from "./NodoInstrumento";
import { FichaInstrumento } from "./FichaInstrumento";

type Estado = "cargando" | "listo" | "error";

const TIPOS_NODO: NodeTypes = { instrumento: NodoInstrumento };
const DEBOUNCE_MS = 300;

// Contexto neutro para arrancar el chat desde el grafo (el investigador lo
// refina después en el formulario de contexto del chat).
const CONTEXTO_INICIAL: ContextoInvestigacion = {
  objetivo: "",
  poblacion: "",
  nivel: "Licenciatura",
  pregunta: "",
};

// Posición en rejilla para el grafo base del acervo.
function posicionAcervo(indice: number): { x: number; y: number } {
  const columnas = 4;
  return {
    x: 40 + (indice % columnas) * 230,
    y: 80 + Math.floor(indice / columnas) * 150,
  };
}

// Posición para los nodos recomendados (columna derecha, agrupados por razón).
function posicionRecomendado(indice: number): { x: number; y: number } {
  return { x: 1080, y: 80 + indice * 150 };
}

export function GrafoPage() {
  return (
    <ReactFlowProvider>
      <GrafoCanvas />
    </ReactFlowProvider>
  );
}

function GrafoCanvas() {
  const navigate = useNavigate();
  const { usuario } = useAuth();
  const { activa, crear, seleccionar } = useResearch();

  const [estado, setEstado] = useState<Estado>("cargando");
  const [mensajeError, setMensajeError] = useState("");
  const [acervo, setAcervo] = useState<NodoGrafo[]>([]);
  const [aristas, setAristas] = useState<AristaGrafo[]>([]);
  const [activos, setActivos] = useState<string[]>([]);
  const [recomendaciones, setRecomendaciones] = useState<Recomendacion[]>([]);
  const [degradado, setDegradado] = useState(false);
  const [seleccionado, setSeleccionado] = useState<NodoGrafo | Recomendacion | null>(null);
  const [recomendando, setRecomendando] = useState(false);
  const [iniciando, setIniciando] = useState(false);

  // ── Carga inicial del acervo ──
  useEffect(() => {
    let vivo = true;
    setEstado("cargando");
    getAcervoGrafo()
      .then((datos) => {
        if (!vivo) return;
        setAcervo(datos.nodos);
        setAristas(datos.aristas);
        setEstado("listo");
      })
      .catch((error: unknown) => {
        if (!vivo) return;
        setMensajeError(
          error instanceof Error ? error.message : "No se pudo cargar el acervo del grafo.",
        );
        setEstado("error");
      });
    return () => {
      vivo = false;
    };
  }, []);

  // ── Recomendación en tiempo real (debounce ~300 ms sobre el set activo) ──
  useEffect(() => {
    if (activos.length === 0) {
      setRecomendaciones([]);
      setDegradado(false);
      return;
    }
    setRecomendando(true);
    const temporizador = window.setTimeout(() => {
      recomendarGrafo({ instrumentoIds: activos })
        .then((datos) => {
          setRecomendaciones(datos.recomendaciones);
          setDegradado(datos.degradado_semantico);
        })
        .catch(() => {
          setRecomendaciones([]);
        })
        .finally(() => setRecomendando(false));
    }, DEBOUNCE_MS);
    return () => window.clearTimeout(temporizador);
  }, [activos]);

  const agregarActivo = useCallback((id: string) => {
    setActivos((prev) => (prev.includes(id) ? prev : [...prev, id]));
  }, []);

  const quitarActivo = useCallback((id: string) => {
    setActivos((prev) => prev.filter((x) => x !== id));
  }, []);

  const porId = useMemo(() => {
    const mapa = new Map<string, NodoGrafo>();
    for (const nodo of acervo) mapa.set(nodo.id, nodo);
    return mapa;
  }, [acervo]);

  // ── Construcción de nodos y aristas de React Flow ──
  const nodos: Node[] = useMemo(() => {
    const activosSet = new Set(activos);
    const recomendadosSet = new Set(recomendaciones.map((r) => r.id));

    const nodosAcervo: Node[] = acervo
      .filter((inst) => !recomendadosSet.has(inst.id))
      .map((inst, i) => {
        const grupo: DatosNodoInstrumento["grupo"] = activosSet.has(inst.id)
          ? "activo"
          : "acervo";
        return {
          id: inst.id,
          type: "instrumento",
          position: posicionAcervo(i),
          data: { instrumento: inst, grupo } satisfies DatosNodoInstrumento,
        };
      });

    const nodosReco: Node[] = recomendaciones.map((reco, i) => ({
      id: reco.id,
      type: "instrumento",
      position: posicionRecomendado(i),
      data: {
        instrumento: reco,
        grupo: "recomendado",
        razon: reco.razon,
      } satisfies DatosNodoInstrumento,
    }));

    return [...nodosAcervo, ...nodosReco];
  }, [acervo, activos, recomendaciones]);

  const edges: Edge[] = useMemo(() => {
    const visibles = new Set(nodos.map((n) => n.id));
    return aristas
      .filter((a) => visibles.has(a.origen) && visibles.has(a.destino))
      .map((a) => ({
        id: `${a.origen}-${a.destino}`,
        source: a.origen,
        target: a.destino,
        label: `${a.peso} KPI${a.peso !== 1 ? "s" : ""}`,
      }));
  }, [aristas, nodos]);

  const onNodeClick: NodeMouseHandler = useCallback((_evento, nodo) => {
    const datos = nodo.data as DatosNodoInstrumento;
    setSeleccionado(datos.instrumento);
  }, []);

  // ── Comenzar investigación: persistir grafo → indexar RAG → navegar al chat ──
  const comenzarRef = useRef(false);
  async function comenzarInvestigacion() {
    if (activos.length === 0 || comenzarRef.current) return;
    comenzarRef.current = true;
    setIniciando(true);
    try {
      const investigacion = activa ?? (await crear("Investigación desde el grafo"));
      seleccionar(investigacion.id);

      const snapshot = {
        nodos: nodos.map((n) => ({ id: n.id, position: n.position })),
        aristas: edges.map((e) => ({ origen: e.source, destino: e.target })),
        activos,
        recomendados: recomendaciones.map((r) => r.id),
      };

      const { instrumentoIdsCrudo } = await guardarGrafoInvestigacion({
        investigacionId: investigacion.id,
        instrumentoIds: activos,
        grafo_snapshot: snapshot,
      });

      await guardarContexto(investigacion.id, CONTEXTO_INICIAL, instrumentoIdsCrudo);
      await navigate({ to: "/chat" });
    } catch (error: unknown) {
      setMensajeError(
        error instanceof Error ? error.message : "No se pudo comenzar la investigación.",
      );
      comenzarRef.current = false;
      setIniciando(false);
    }
  }

  const seleccionadoActivo = seleccionado ? activos.includes(seleccionado.id) : false;

  return (
    <div className="flex h-full flex-col gap-4 p-6 md:p-8">
      <PageHeader
        titulo="Grafo de recomendación"
        descripcion="Explora el acervo como un grafo, arma tu investigación y descubre instrumentos complementarios en tiempo real."
        acciones={
          <button
            type="button"
            onClick={comenzarInvestigacion}
            disabled={activos.length === 0 || iniciando}
            className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {iniciando ? <Loader2 className="size-4 animate-spin" /> : <Share2 className="size-4" />}
            Comenzar investigación
          </button>
        }
      />

      {estado === "error" && (
        <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-border bg-card px-6 py-14 text-center shadow-card">
          <span className="flex size-10 items-center justify-center rounded-full bg-destructive/10 text-destructive">
            <AlertTriangle className="size-5" />
          </span>
          <p className="font-display text-sm font-semibold">No se pudo cargar el grafo</p>
          <p className="max-w-md text-xs text-muted-foreground">{mensajeError}</p>
        </div>
      )}

      {estado === "cargando" && (
        <div className="h-full min-h-96 animate-pulse rounded-2xl border border-border bg-card" />
      )}

      {estado === "listo" && (
        <div className="flex min-h-0 flex-1 gap-4">
          <div className="flex min-w-0 flex-1 flex-col gap-3">
            <PanelActivos
              activos={activos}
              recomendando={recomendando}
              degradado={degradado}
              porId={porId}
              onQuitar={quitarActivo}
            />
            <div className="min-h-0 flex-1 overflow-hidden rounded-2xl border border-border bg-card shadow-card">
              <ReactFlow
                nodes={nodos}
                edges={edges}
                nodeTypes={TIPOS_NODO}
                onNodeClick={onNodeClick}
                fitView
                proOptions={{ hideAttribution: true }}
              >
                <Background />
                <Controls showInteractive={false} />
              </ReactFlow>
            </div>
          </div>

          {seleccionado && (
            <FichaInstrumento
              instrumento={seleccionado}
              activo={seleccionadoActivo}
              onAgregar={
                seleccionadoActivo ? undefined : () => agregarActivo(seleccionado.id)
              }
              onCerrar={() => setSeleccionado(null)}
            />
          )}
        </div>
      )}
    </div>
  );
}

function PanelActivos({
  activos,
  recomendando,
  degradado,
  porId,
  onQuitar,
}: {
  activos: string[];
  recomendando: boolean;
  degradado: boolean;
  porId: Map<string, NodoGrafo>;
  onQuitar: (id: string) => void;
}) {
  return (
    <section className="rounded-2xl border border-primary/30 bg-primary-soft/30 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-display text-sm font-semibold text-foreground">
          Investigación activa
        </h2>
        {recomendando && (
          <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
            <Loader2 className="size-3.5 animate-spin" /> Recalculando recomendaciones…
          </span>
        )}
      </div>

      {activos.length === 0 ? (
        <p className="mt-2 text-xs text-muted-foreground">
          Haz clic en un instrumento del grafo y agrégalo a tu investigación para recibir
          recomendaciones.
        </p>
      ) : (
        <div className="mt-3 flex flex-wrap gap-2">
          {activos.map((id) => {
            const inst = porId.get(id);
            return (
              <button
                key={id}
                type="button"
                onClick={() => onQuitar(id)}
                className="inline-flex items-center gap-1.5 rounded-full bg-primary px-3 py-1 text-xs font-medium text-primary-foreground transition-opacity hover:opacity-90"
                title="Quitar de la investigación"
              >
                {inst?.titulo ?? id}
                <span aria-hidden>×</span>
              </button>
            );
          })}
        </div>
      )}

      {degradado && (
        <p className="mt-3 rounded-lg bg-accent-soft px-3 py-1.5 text-[11px] text-accent-foreground">
          Modo degradado: la similitud semántica no está disponible, las recomendaciones usan
          solo los KPIs compartidos.
        </p>
      )}
    </section>
  );
}
