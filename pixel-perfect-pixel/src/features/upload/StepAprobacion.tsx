import { AlertTriangle, CheckCircle2, ShieldCheck } from "lucide-react";
import { ProcesandoIA } from "@/components/shared/ProcesandoIA";
import type { VistaPrevia } from "@/api/carga";
import type { PerfilGenerado } from "@/types";
import { PerfilSemanticoVista } from "./conocimiento/PerfilSemanticoVista";

interface StepAprobacionProps {
  vistaPrevia: VistaPrevia | null;
  /** Perfil semántico (lo que se usará para asociar KPIs). */
  perfil: PerfilGenerado | null;
  /** Mensaje si no se pudo generar el perfil (no impide aprobar los metadatos). */
  errorPerfil: string | null;
  /** Etiqueta legible de cada campo, para listar los errores. */
  etiquetas: Record<string, string>;
}

export function StepAprobacion({
  vistaPrevia,
  perfil,
  errorPerfil,
  etiquetas,
}: StepAprobacionProps) {
  if (!vistaPrevia) {
    return <ProcesandoIA mensaje="Generando el perfil del instrumento…" />;
  }
  const errores = [
    ...Object.entries(vistaPrevia.errores.dublin_core),
    ...Object.entries(vistaPrevia.errores.enriquecidos),
  ];
  return (
    <div className="space-y-5">
      {errores.length > 0 ? (
        <div className="space-y-2 rounded-xl border border-destructive/30 bg-destructive/5 p-4 text-sm">
          <p className="flex items-center gap-2 font-semibold text-destructive">
            <AlertTriangle className="size-4" /> Faltan datos para poder aprobar
          </p>
          <ul className="space-y-1 text-foreground">
            {errores.map(([campo, mensaje]) => (
              <li key={campo}>
                <span className="font-medium">{etiquetas[campo] ?? campo}:</span> {mensaje}
              </li>
            ))}
          </ul>
          <p className="text-muted-foreground">Vuelve a los pasos anteriores para completarlos.</p>
        </div>
      ) : (
        <div className="flex gap-3 rounded-xl bg-primary-soft p-4 text-sm">
          <ShieldCheck className="size-5 shrink-0 text-primary" />
          <div className="space-y-1">
            <p className="flex items-center gap-1.5 font-semibold">
              <CheckCircle2 className="size-4 text-primary" /> Metadatos completos
            </p>
            <p className="text-muted-foreground">
              Al aprobar, los metadatos quedan registrados a tu nombre y el instrumento se integra
              al RAG para consultas y búsqueda de KPIs. Podrás corregirlos volviendo a este paso.
            </p>
          </div>
        </div>
      )}
      {perfil ? (
        <PerfilSemanticoVista datos={perfil} />
      ) : (
        <p className="flex items-start gap-2 rounded-xl border border-accent/30 bg-accent-soft p-4 text-sm text-foreground">
          <AlertTriangle className="mt-0.5 size-4 shrink-0 text-accent-strong" aria-hidden />
          {errorPerfil ?? "No se pudo generar el perfil semántico."} Puedes aprobar los metadatos
          igualmente.
        </p>
      )}
    </div>
  );
}
