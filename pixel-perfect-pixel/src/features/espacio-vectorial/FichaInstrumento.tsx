import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { ArrowUpRight } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { getDetalleInstrumento } from "@/api/espacio";
import { CAMPOS_POR_TIPO } from "@/features/upload/StepMetadatosTipo";
import type { DetalleInstrumento } from "@/types";

interface FichaInstrumentoProps {
  id: string;
  /** Resumen del mapa, por si la ficha no se puede cargar. */
  resumen: string;
}

/** Columnas de metadatos_dc que se muestran (el título y la descripción van arriba). */
const ETIQUETAS_DC: Array<[string, string]> = [
  ["dc_creator", "Creador"],
  ["dc_subject", "Tema"],
  ["dc_coverage", "Cobertura"],
  ["dc_date", "Fecha"],
  ["dc_language", "Idioma"],
  ["dc_publisher", "Editor"],
  ["dc_rights", "Derechos"],
  ["dc_format", "Formato"],
  ["dc_source", "Fuente"],
  ["dc_relation", "Relación"],
];
const PREGUNTAS_INICIALES = 6;

function texto(valor: unknown): string {
  if (valor == null) return "";
  if (Array.isArray(valor)) return valor.map(String).join(", ");
  if (typeof valor === "object") return JSON.stringify(valor);
  return String(valor).trim();
}

function ListaDatos({ filas }: { filas: Array<[string, string]> }) {
  if (filas.length === 0) return null;
  return (
    <dl className="grid gap-x-4 gap-y-2.5 text-sm sm:grid-cols-[minmax(7rem,auto)_1fr]">
      {filas.map(([etiqueta, valor]) => (
        <div key={etiqueta} className="contents">
          <dt className="font-semibold text-muted-foreground">{etiqueta}</dt>
          <dd className="min-w-0 break-words text-foreground">{valor}</dd>
        </div>
      ))}
    </dl>
  );
}

/** Ficha del instrumento: Dublin Core, metadatos de su tipo y preguntas. */
export function FichaInstrumento({ id, resumen }: FichaInstrumentoProps) {
  const [detalle, setDetalle] = useState<DetalleInstrumento | null>(null);
  const [estado, setEstado] = useState<"cargando" | "listo" | "error">("cargando");
  const [todas, setTodas] = useState(false);

  useEffect(() => {
    let activo = true;
    setEstado("cargando");
    setTodas(false);
    getDetalleInstrumento(id)
      .then((d) => {
        if (!activo) return;
        setDetalle(d);
        setEstado("listo");
      })
      .catch(() => activo && setEstado("error"));
    return () => {
      activo = false;
    };
  }, [id]);

  if (estado === "cargando") {
    return (
      <div className="space-y-3" role="status" aria-label="Cargando la ficha del instrumento">
        <Skeleton className="h-16 rounded-xl" />
        <Skeleton className="h-28 rounded-xl" />
      </div>
    );
  }
  if (estado === "error" || !detalle) {
    return <p className="text-sm text-muted-foreground">{resumen}</p>;
  }

  const { instrumento, dublinCore, enriquecidos, preguntas } = detalle;
  const filasDc = ETIQUETAS_DC.map(
    ([col, etq]) => [etq, texto(dublinCore[col])] as [string, string],
  ).filter(([, v]) => v);
  const filasTipo = (CAMPOS_POR_TIPO[instrumento.tipo] ?? [])
    .map((c) => [c.etiqueta, texto(enriquecidos[c.clave])] as [string, string])
    .filter(([, v]) => v);
  const visibles = todas ? preguntas : preguntas.slice(0, PREGUNTAS_INICIALES);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {[
          ["Tipo", instrumento.tipo],
          ["Nivel", instrumento.nivel],
          ["Año", String(instrumento.anio)],
          ["Reactivos", String(instrumento.reactivos)],
        ].map(([e, v]) => (
          <div key={e} className="rounded-xl bg-primary-soft/60 px-3 py-2">
            <p className="text-xs font-semibold text-muted-foreground">{e}</p>
            <p className="truncate text-sm font-bold text-foreground">{v}</p>
          </div>
        ))}
      </div>

      {instrumento.descripcion && (
        <p className="line-clamp-6 text-sm leading-relaxed text-foreground">
          {instrumento.descripcion}
        </p>
      )}

      {filasDc.length > 0 && (
        <section className="space-y-2.5">
          <h3 className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
            Dublin Core
          </h3>
          <ListaDatos filas={filasDc} />
        </section>
      )}

      {filasTipo.length > 0 && (
        <section className="space-y-2.5">
          <h3 className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
            Metadatos de {instrumento.tipo.toLowerCase()}
          </h3>
          <ListaDatos filas={filasTipo} />
        </section>
      )}

      {preguntas.length > 0 && (
        <section className="space-y-2.5">
          <h3 className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
            Preguntas ({preguntas.length})
          </h3>
          <ol className="space-y-1.5 text-sm text-foreground">
            {visibles.map((p, i) => (
              <li key={p.id} className="flex gap-2.5">
                <span className="w-6 shrink-0 text-right text-xs font-bold tabular-nums leading-5 text-muted-foreground">
                  {i + 1}
                </span>
                <span className="min-w-0 leading-snug">{p.texto}</span>
              </li>
            ))}
          </ol>
          {preguntas.length > PREGUNTAS_INICIALES && (
            <button
              type="button"
              onClick={() => setTodas((v) => !v)}
              className="rounded-lg px-2 py-1 text-sm font-bold text-primary hover:bg-primary-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {todas ? "Ver menos" : `Ver las ${preguntas.length} preguntas`}
            </button>
          )}
        </section>
      )}

      <Link
        to="/instrumentos"
        className="inline-flex items-center gap-1.5 text-sm font-bold text-primary hover:underline"
      >
        Ir a Mis instrumentos <ArrowUpRight className="size-4" aria-hidden />
      </Link>
    </div>
  );
}
