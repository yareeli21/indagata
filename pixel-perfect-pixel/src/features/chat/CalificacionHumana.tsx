import { useState } from "react";
import { Check, Loader2, UserCheck } from "lucide-react";
import { calificarRespuesta } from "@/api/chat";
import { cn } from "@/lib/utils";
import type { CalificacionRespuesta } from "@/types";

interface Opcion<T> {
  valor: T;
  etiqueta: string;
}

const CALIFICACIONES: Opcion<0 | 1 | 2>[] = [
  { valor: 0, etiqueta: "Mal" },
  { valor: 1, etiqueta: "Parcial" },
  { valor: 2, etiqueta: "Bien" },
];
const SI_NO: Opcion<boolean>[] = [
  { valor: true, etiqueta: "Sí" },
  { valor: false, etiqueta: "No" },
];
const SI_NO_NA: Opcion<boolean | null>[] = [...SI_NO, { valor: null, etiqueta: "No aplica" }];

function Botones<T>({
  opciones,
  valor,
  onCambiar,
  etiqueta,
}: {
  opciones: Opcion<T>[];
  valor: T | undefined;
  onCambiar: (v: T) => void;
  etiqueta: string;
}) {
  return (
    <div role="radiogroup" aria-label={etiqueta} className="inline-flex flex-wrap gap-1">
      {opciones.map((o) => (
        <button
          key={o.etiqueta}
          type="button"
          role="radio"
          aria-checked={valor === o.valor}
          onClick={() => onCambiar(o.valor)}
          className={cn(
            "rounded-lg border border-border px-2.5 py-0.5 font-medium",
            valor === o.valor
              ? "bg-primary text-primary-foreground"
              : "text-card-foreground hover:bg-primary-soft",
          )}
        >
          {o.etiqueta}
        </button>
      ))}
    </div>
  );
}

/** Calificación humana de una respuesta: la referencia contra la que se compara a los jueces. */
export function CalificacionHumana({
  consultaId,
  inicial,
}: {
  consultaId: number;
  inicial: CalificacionRespuesta | null;
}) {
  const [calificacion, setCalificacion] = useState<0 | 1 | 2 | undefined>(inicial?.calificacion);
  const [entendio, setEntendio] = useState<boolean | undefined>(inicial?.entendio ?? undefined);
  // «No aplica» se guarda como null; undefined = todavía sin elegir.
  const [fundamenta, setFundamenta] = useState<boolean | null | undefined>(
    inicial ? inicial.fundamenta : undefined,
  );
  const [comentario, setComentario] = useState(inicial?.comentario ?? "");
  const [estado, setEstado] = useState<"guardada" | "cambios" | "guardando" | "error">(
    inicial ? "guardada" : "cambios",
  );

  function cambiar<T>(setter: (v: T) => void) {
    return (v: T) => {
      setter(v);
      setEstado("cambios");
    };
  }

  async function guardar() {
    if (calificacion === undefined) return;
    setEstado("guardando");
    try {
      await calificarRespuesta(consultaId, {
        calificacion,
        entendio: entendio ?? null,
        fundamenta: fundamenta ?? null,
        comentario: comentario.trim() || null,
      });
      setEstado("guardada");
    } catch {
      setEstado("error");
    }
  }

  return (
    <div className="space-y-1.5">
      <p className="flex items-center gap-1.5 font-medium text-card-foreground">
        <UserCheck className="size-3.5 shrink-0 text-primary" aria-hidden />
        Tu calificación
      </p>
      <div className="grid grid-cols-[auto_1fr] items-center gap-x-3 gap-y-1.5 text-muted-foreground">
        <span>Respuesta</span>
        <Botones
          etiqueta="Calificación"
          opciones={CALIFICACIONES}
          valor={calificacion}
          onCambiar={cambiar(setCalificacion)}
        />
        <span>¿Entendió lo que pediste?</span>
        <Botones
          etiqueta="¿Entendió?"
          opciones={SI_NO}
          valor={entendio}
          onCambiar={cambiar(setEntendio)}
        />
        <span>¿Fundamentó?</span>
        <Botones
          etiqueta="¿Fundamentó?"
          opciones={SI_NO_NA}
          valor={fundamenta}
          onCambiar={cambiar(setFundamenta)}
        />
      </div>
      <textarea
        value={comentario}
        onChange={(e) => cambiar(setComentario)(e.target.value)}
        maxLength={2000}
        rows={2}
        placeholder="Comentario (opcional): qué faltó o qué estuvo mal"
        aria-label="Comentario"
        className="w-full resize-y rounded-lg border border-border bg-background px-2 py-1 text-xs text-foreground"
      />
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => void guardar()}
          disabled={calificacion === undefined || estado === "guardando" || estado === "guardada"}
          className="inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1 font-semibold text-primary hover:bg-primary-soft disabled:opacity-60"
        >
          {estado === "guardando" && <Loader2 className="size-3 animate-spin" aria-hidden />}
          {estado === "guardada" ? (
            <>
              <Check className="size-3" aria-hidden /> Guardada
            </>
          ) : (
            "Guardar calificación"
          )}
        </button>
        {calificacion === undefined && (
          <span className="text-muted-foreground">Elige Mal, Parcial o Bien para guardar.</span>
        )}
        {estado === "error" && (
          <span className="text-destructive">No se pudo guardar; reintenta.</span>
        )}
      </div>
    </div>
  );
}
