import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { MessageSquare, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { getInstrumentosDeInvestigacion } from "@/api/chat";
import { leerSesionChat } from "@/api/investigaciones";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import type { Investigacion } from "@/types";
import { useResearch } from "./ResearchContext";

function fecha(iso: string | undefined): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("es-MX", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/** Investigaciones guardadas: continuar su conversación en el chat o eliminarlas. */
export function MisInvestigaciones() {
  const { investigaciones, activa, seleccionar, eliminar } = useResearch();
  const navigate = useNavigate();
  const [porEliminar, setPorEliminar] = useState<Investigacion | null>(null);

  if (investigaciones.length === 0) return null;

  function continuar(id: string) {
    seleccionar(id);
    void navigate({ to: "/chat" });
  }

  async function confirmarEliminar() {
    if (!porEliminar) return;
    await eliminar(porEliminar.id);
    toast.success(`Investigación «${porEliminar.nombre}» eliminada.`);
    setPorEliminar(null);
  }

  return (
    <section
      aria-labelledby="titulo-mis-investigaciones"
      className="superficie rounded-3xl p-6 md:p-8"
    >
      <h2
        id="titulo-mis-investigaciones"
        className="mb-1 font-display text-2xl font-bold tracking-tight"
      >
        Mis investigaciones
      </h2>
      <p className="mb-5 text-sm text-muted-foreground">
        Retoma una investigación donde la dejaste: su conversación queda guardada en este navegador.
      </p>
      <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {[...investigaciones].reverse().map((inv) => {
          const instrumentos = getInstrumentosDeInvestigacion(inv.id).length;
          const sesion = leerSesionChat(inv.id);
          const preguntas = sesion?.mensajes.filter((m) => m.rol === "usuario").length ?? 0;
          return (
            <li
              key={inv.id}
              className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-4 shadow-card"
            >
              <div className="min-w-0">
                <p className="truncate font-semibold text-foreground">
                  {inv.nombre}
                  {activa?.id === inv.id && (
                    <span className="ml-2 rounded-full bg-accent-soft px-2 py-0.5 text-xs font-semibold text-accent-strong">
                      activa
                    </span>
                  )}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {instrumentos} {instrumentos === 1 ? "instrumento" : "instrumentos"} · {preguntas}{" "}
                  {preguntas === 1 ? "pregunta" : "preguntas"}
                  {inv.fechaCreacion ? ` · ${fecha(inv.fechaCreacion)}` : ""}
                </p>
              </div>
              <div className="mt-auto flex flex-wrap gap-2">
                <Button size="sm" onClick={() => continuar(inv.id)}>
                  <MessageSquare /> Continuar en el chat
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  className="text-destructive hover:text-destructive"
                  onClick={() => setPorEliminar(inv)}
                >
                  <Trash2 /> Eliminar
                </Button>
              </div>
            </li>
          );
        })}
      </ul>

      <AlertDialog open={!!porEliminar} onOpenChange={(o) => !o && setPorEliminar(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Eliminar «{porEliminar?.nombre}»?</AlertDialogTitle>
            <AlertDialogDescription>
              Se borran la selección de instrumentos y la conversación guardada de esta
              investigación. No se borran los instrumentos ni la bitácora de consultas del servidor.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={() => void confirmarEliminar()}>Eliminar</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </section>
  );
}
