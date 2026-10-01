import { useCallback, useEffect, useRef, useState } from "react";
import { enviarMensaje, guardarContexto } from "@/api/chat";
import { getInstrumentos } from "@/api/instrumentos";
import { useAuth } from "@/features/auth/AuthContext";
import { useResearch } from "@/features/research/ResearchContext";
import type {
  ContextoInvestigacion,
  Instrumento,
  Mensaje,
  ModeloLLM,
} from "@/types";
import { BarraEntrada } from "./BarraEntrada";
import { BurbujaMensaje } from "./BurbujaMensaje";
import { ChipsFuentes } from "./ChipsFuentes";
import { EstadoVacioChat } from "./EstadoVacioChat";
import { FormularioContexto } from "./FormularioContexto";
import { PanelNoticias } from "./PanelNoticias";

type Fase = "vacio" | "contexto" | "chat";

export function ChatPage() {
  const { usuario } = useAuth();
  const { activa, cargando: cargandoResearch } = useResearch();
  const miId = usuario?.investigadorId ?? "";

  // Instrumentos de la investigación activa (simulado: todos los propios + algunos ajenos)
  const [instrumentosFuentes, setInstrumentosFuentes] = useState<Instrumento[]>([]);

  useEffect(() => {
    if (!activa) return;
    getInstrumentos().then((todos) => {
      // Simulación: tomar instrumentos propios + 2 ajenos como fuentes de la investigación
      const propios = todos.filter((i) => i.autorId === miId).slice(0, 3);
      const ajenos = todos.filter((i) => i.autorId !== miId).slice(0, 2);
      setInstrumentosFuentes([...propios, ...ajenos]);
    });
  }, [activa, miId]);

  // Fase del asistente
  const [fase, setFase] = useState<Fase>("vacio");
  const [contexto, setContexto] = useState<ContextoInvestigacion | null>(null);

  // Actualizar fase cuando cambia la investigación activa
  useEffect(() => {
    if (cargandoResearch) return;
    setFase(activa ? "contexto" : "vacio");
    setMensajes([]);
    setContexto(null);
  }, [activa, cargandoResearch]);

  // Chat
  const [mensajes, setMensajes] = useState<Mensaje[]>([]);
  const [modelo, setModelo] = useState<ModeloLLM>("gpt-4o");
  const [generando, setGenerando] = useState(false);
  const cancelarRef = useRef<(() => void) | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll al último mensaje
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensajes]);

  async function handleComenzar(ctx: ContextoInvestigacion) {
    if (!activa) return;
    await guardarContexto(activa.id, ctx);
    setContexto(ctx);
    setFase("chat");
  }

  const handleEnviar = useCallback(
    (texto: string) => {
      if (!contexto) return;

      // Añadir mensaje del usuario
      const idUsuario = `msg-${Date.now()}-u`;
      const idAsistente = `msg-${Date.now()}-a`;

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
            prev.map((m) =>
              m.id === idAsistente
                ? { ...m, contenido: m.contenido + token }
                : m,
            ),
          );
        },
        (fuentes) => {
          setMensajes((prev) =>
            prev.map((m) =>
              m.id === idAsistente
                ? { ...m, generando: false, fuentes }
                : m,
            ),
          );
          setGenerando(false);
          cancelarRef.current = null;
        },
      );

      cancelarRef.current = cancelar;
    },
    [contexto, modelo],
  );

  function handleDetener() {
    cancelarRef.current?.();
    cancelarRef.current = null;
    // Marcar el mensaje en curso como completo (sin fuentes)
    setMensajes((prev) =>
      prev.map((m) =>
        m.generando ? { ...m, generando: false } : m,
      ),
    );
    setGenerando(false);
  }

  // ── Estado de carga inicial ──
  if (cargandoResearch) {
    return <div className="flex-1 bg-background" />;
  }

  // ── Sin investigación activa ──
  if (fase === "vacio") {
    return (
      <div className="flex h-full flex-1 flex-col">
        <EstadoVacioChat />
      </div>
    );
  }

  // ── Formulario de contexto ──
  if (fase === "contexto") {
    return (
      <div className="flex h-full flex-1 flex-col">
        <FormularioContexto
          nombreInvestigacion={activa?.nombre ?? ""}
          onComenzar={handleComenzar}
        />
      </div>
    );
  }

  // ── Chat activo ──
  return (
    <div className="flex h-full flex-1 overflow-hidden">
      {/* Área principal del chat */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Chips de fuentes */}
        <div className="border-b bg-card">
          <ChipsFuentes instrumentos={instrumentosFuentes} miId={miId} />
        </div>

        {/* Mensajes */}
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
          {mensajes.length === 0 && (
            <div className="flex flex-col items-center gap-2 py-12 text-center">
              <p className="text-sm font-medium text-muted-foreground">
                El chat está listo. Haz tu primera pregunta sobre los instrumentos
                de tu investigación.
              </p>
            </div>
          )}
          {mensajes.map((m) => (
            <BurbujaMensaje key={m.id} mensaje={m} />
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

      {/* Panel lateral de noticias */}
      <PanelNoticias />
    </div>
  );
}
