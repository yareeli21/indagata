import { useCallback, useEffect, useRef, useState } from "react";
import { enviarMensaje, guardarContexto } from "@/api/chat";
import { getInstrumentos } from "@/api/instrumentos";
import { guardarSesionChat, leerSesionChat } from "@/api/investigaciones";
import { useAuth } from "@/features/auth/AuthContext";
import { useResearch } from "@/features/research/ResearchContext";
import { fuentesDeInvestigacion } from "@/features/research/fuentes";
import type { AlcanceChat, ContextoInvestigacion, Instrumento, Mensaje, ModeloLLM } from "@/types";
import { MessageSquare, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/layout/PageHeader";
import { Pagina } from "@/components/layout/Pagina";
import { BarraEntrada } from "./BarraEntrada";
import { BurbujaMensaje } from "./BurbujaMensaje";
import { ChipsFuentes } from "./ChipsFuentes";
import { EstadoVacioChat } from "./EstadoVacioChat";
import { FormularioContexto } from "./FormularioContexto";
import { PanelFuente, type FuenteSeleccionada } from "./PanelFuente";
import { PanelNoticias } from "./PanelNoticias";
import { SelectorAlcance } from "./SelectorAlcance";

type Fase = "vacio" | "contexto" | "chat";

export function ChatPage() {
  const { usuario } = useAuth();
  const { activa, cargando: cargandoResearch } = useResearch();
  const miId = usuario?.investigadorId ?? "";

  // Instrumentos de la investigación activa (los elegidos al armarla) y todo el catálogo
  // (para elegir instrumentos sueltos en el alcance del chat).
  const [instrumentosFuentes, setInstrumentosFuentes] = useState<Instrumento[]>([]);
  const [catalogo, setCatalogo] = useState<Instrumento[]>([]);

  useEffect(() => {
    if (!activa) return;
    getInstrumentos()
      .then((todos) => {
        setCatalogo(todos);
        setInstrumentosFuentes(fuentesDeInvestigacion(todos, activa.id, miId));
      })
      .catch(() => setInstrumentosFuentes([]));
  }, [activa, miId]);

  // Alcance del chat: la investigación (por defecto), instrumentos elegidos o todo el acervo.
  const [alcance, setAlcance] = useState<AlcanceChat>("investigacion");
  const [elegidos, setElegidos] = useState<string[]>([]);

  // Fase del asistente
  const [fase, setFase] = useState<Fase>("vacio");
  const [contexto, setContexto] = useState<ContextoInvestigacion | null>(null);

  // Al cambiar de investigación se retoma su conversación guardada (si la hay):
  // las respuestas ya generadas no se vuelven a pedir al modelo.
  useEffect(() => {
    if (cargandoResearch) return;
    const sesion = activa ? leerSesionChat(activa.id) : null;
    setFase(!activa ? "vacio" : sesion ? "chat" : "contexto");
    setMensajes(sesion?.mensajes ?? []);
    setContexto(sesion?.contexto ?? null);
  }, [activa, cargandoResearch]);

  // Chat
  const [mensajes, setMensajes] = useState<Mensaje[]>([]);
  // Fuente citada abierta en el panel lateral (trazabilidad: documento y parte exacta usada).
  const [fuenteAbierta, setFuenteAbierta] = useState<FuenteSeleccionada | null>(null);
  const [modelo, setModelo] = useState<ModeloLLM>("llama3.2:3b");
  const [generando, setGenerando] = useState(false);
  const cancelarRef = useRef<(() => void) | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const listaRef = useRef<HTMLDivElement>(null);
  const mensajesPrevios = useRef(0);

  // Auto-scroll al último mensaje. Al abrir una conversación guardada se salta directo al final (antes
  // el desplazamiento suave se quedaba a medio camino en conversaciones largas); con cada mensaje nuevo,
  // desplazamiento suave.
  useEffect(() => {
    const lista = listaRef.current;
    const alAbrir = mensajesPrevios.current === 0 && mensajes.length > 0;
    mensajesPrevios.current = mensajes.length;
    if (!lista) return;
    requestAnimationFrame(() => {
      lista.scrollTo({ top: lista.scrollHeight, behavior: alAbrir ? "auto" : "smooth" });
    });
  }, [mensajes]);

  // Guarda la conversación cada vez que termina una respuesta.
  useEffect(() => {
    if (!activa || !contexto || generando) return;
    guardarSesionChat(activa.id, contexto, mensajes);
  }, [activa, contexto, mensajes, generando]);

  function nuevaConversacion() {
    setMensajes([]);
    if (activa && contexto) guardarSesionChat(activa.id, contexto, []);
  }

  async function handleComenzar(ctx: ContextoInvestigacion) {
    if (!activa) return;
    await guardarContexto(
      activa.id,
      ctx,
      instrumentosFuentes.map((i) => i.id),
    );
    setContexto(ctx);
    setFase("chat");
  }

  const handleEnviar = useCallback(
    (texto: string) => {
      if (!contexto) return;

      // Añadir mensaje del usuario
      const idUsuario = `msg-${Date.now()}-u`;
      const idAsistente = `msg-${Date.now()}-a`;

      const anteriores = mensajes;
      setMensajes((prev) => [
        ...prev,
        { id: idUsuario, rol: "usuario", contenido: texto },
        { id: idAsistente, rol: "asistente", contenido: "", generando: true },
      ]);
      setGenerando(true);

      const cancelar = enviarMensaje(
        texto,
        contexto,
        modelo,
        (token) => {
          setMensajes((prev) =>
            prev.map((m) => (m.id === idAsistente ? { ...m, contenido: m.contenido + token } : m)),
          );
        },
        (resultado) => {
          setMensajes((prev) =>
            prev.map((m) => (m.id === idAsistente ? { ...m, generando: false, ...resultado } : m)),
          );
          setGenerando(false);
          cancelarRef.current = null;
        },
        activa?.id ?? "",
        // [] = todo el acervo; sin indicar = los instrumentos de la investigación.
        alcance === "acervo"
          ? []
          : alcance === "elegidos" && elegidos.length > 0
            ? elegidos
            : undefined,
        anteriores,
      );

      cancelarRef.current = cancelar;
    },
    [contexto, modelo, activa, alcance, elegidos, mensajes],
  );

  function handleDetener() {
    cancelarRef.current?.();
    cancelarRef.current = null;
    // Marcar el mensaje en curso como completo (sin fuentes)
    setMensajes((prev) => prev.map((m) => (m.generando ? { ...m, generando: false } : m)));
    setGenerando(false);
  }

  // ── Estado de carga inicial ──
  if (cargandoResearch) {
    return <div className="flex-1 bg-background" />;
  }

  // ── Sin investigación activa ──
  if (fase === "vacio") {
    return (
      <Pagina>
        <PageHeader
          icono={MessageSquare}
          etiqueta="Asistente RAG"
          titulo="Chat con el acervo"
          descripcion="Pregunta en lenguaje natural y recibe respuestas fundamentadas en tus instrumentos."
        />
        <EstadoVacioChat />
      </Pagina>
    );
  }

  // ── Formulario de contexto ──
  if (fase === "contexto") {
    return (
      <Pagina>
        <PageHeader
          icono={MessageSquare}
          etiqueta="Asistente RAG"
          titulo="Chat con el acervo"
          descripcion="Antes de empezar, cuéntale al asistente el contexto de tu investigación."
        />
        <FormularioContexto
          nombreInvestigacion={activa?.nombre ?? ""}
          onComenzar={handleComenzar}
        />
      </Pagina>
    );
  }

  // ── Chat activo ──
  return (
    // Alto de la ventana menos el encabezado de la app (h-18 = 4.5rem): solo la lista de mensajes hace
    // scroll, así la barra de entrada y el panel de noticias quedan siempre a la vista. Antes la página
    // entera crecía con la conversación y ambos se perdían al desplazarse.
    <div className="flex h-[calc(100dvh-4.5rem)] max-h-[calc(100dvh-4.5rem)] min-h-0 flex-none overflow-hidden">
      {/* Área principal del chat */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Alcance y chips de fuentes */}
        <div className="border-b bg-card">
          <SelectorAlcance
            alcance={alcance}
            elegidos={elegidos}
            instrumentos={catalogo}
            deshabilitado={generando}
            onCambiarAlcance={setAlcance}
            onCambiarElegidos={setElegidos}
          />
          {alcance === "investigacion" && (
            <ChipsFuentes instrumentos={instrumentosFuentes} miId={miId} />
          )}
          {alcance !== "investigacion" && <div className="pb-3" />}
          {mensajes.length > 0 && (
            <div className="flex justify-end px-4 pb-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={nuevaConversacion}
                disabled={generando}
                className="text-muted-foreground"
              >
                <RotateCcw /> Nueva conversación
              </Button>
            </div>
          )}
        </div>

        {/* Mensajes (lo único que hace scroll) */}
        <div ref={listaRef} className="min-h-0 flex-1 overflow-y-auto px-4 py-6 space-y-6">
          {mensajes.length === 0 && (
            <div className="flex flex-col items-center gap-2 py-12 text-center">
              <p className="text-sm font-medium text-muted-foreground">
                El chat está listo. Haz tu primera pregunta sobre los instrumentos de tu
                investigación.
              </p>
            </div>
          )}
          {mensajes.map((m) => (
            <BurbujaMensaje key={m.id} mensaje={m} onAbrirFuente={setFuenteAbierta} />
          ))}
          <div ref={bottomRef} />
        </div>

        {/* Barra de entrada */}
        <BarraEntrada
          modelo={modelo}
          generando={generando}
          onCambiarModelo={setModelo}
          onEnviar={handleEnviar}
          onDetener={handleDetener}
        />
      </div>

      {/* Fuente citada (trazabilidad): angosta el chat en lugar de taparlo. Mientras está abierta,
          las noticias se ocultan para dejarle espacio; al cerrarla vuelven. */}
      <PanelFuente seleccion={fuenteAbierta} onCerrar={() => setFuenteAbierta(null)} />

      {/* Panel lateral de noticias */}
      {!fuenteAbierta && <PanelNoticias />}
    </div>
  );
}
