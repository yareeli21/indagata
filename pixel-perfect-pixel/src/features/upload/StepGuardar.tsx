import { FileWarning, RotateCcw } from "lucide-react";
import { EstadoVacio } from "@/components/shared/EstadoVacio";
import { ProcesandoIA } from "@/components/shared/ProcesandoIA";
import { Button } from "@/components/ui/button";
import type { DocumentoGenerado, PerfilGenerado } from "@/types";
import { DocumentoFinalVista } from "./conocimiento/DocumentoFinalVista";
import { PerfilSemanticoVista } from "./conocimiento/PerfilSemanticoVista";

interface StepGuardarProps {
  resumen: { etiqueta: string; valor: string }[];
  /** Documento final generado al entrar al paso (null mientras se genera o si falló). */
  documento: DocumentoGenerado | null;
  errorDocumento: string | null;
  onReintentar: () => void;
  /** Perfil con los KPIs ya integrados (JSON pequeño de la asociación de KPIs). */
  perfil: PerfilGenerado | null;
}

export function StepGuardar({
  resumen,
  documento,
  errorDocumento,
  onReintentar,
  perfil,
}: StepGuardarProps) {
  return (
    <div className="space-y-5">
      <dl className="divide-y rounded-xl border bg-card">
        {resumen.map((r) => (
          <div
            key={r.etiqueta}
            className="grid grid-cols-1 gap-1 px-5 py-3 text-sm sm:grid-cols-[12rem_1fr] sm:gap-4"
          >
            <dt className="text-muted-foreground">{r.etiqueta}</dt>
            <dd className="font-medium">{r.valor || "—"}</dd>
          </div>
        ))}
      </dl>
      {perfil && <PerfilSemanticoVista datos={perfil} conKpis />}
      {documento ? (
        <DocumentoFinalVista datos={documento} />
      ) : errorDocumento ? (
        <EstadoVacio
          icono={FileWarning}
          compacto
          titulo="No se pudo generar el documento final"
          descripcion={`${errorDocumento} Puedes guardar el instrumento igualmente y reintentarlo después.`}
          accion={
            <Button variant="outline" size="sm" onClick={onReintentar}>
              <RotateCcw className="size-4" aria-hidden /> Reintentar
            </Button>
          }
        />
      ) : (
        <ProcesandoIA
          mensaje="Generando el documento final…"
          detalle="Interpretamos cada respuesta, calculamos los resúmenes y lo validamos con su esquema."
        />
      )}
    </div>
  );
}
