import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import type { MetadatosTipo, TipoInstrumento } from "@/types";

interface CampoDef {
  clave: string;
  etiqueta: string;
  tipo?: "number" | "text" | "textarea";
  placeholder?: string;
  /** Si true, el campo vive en la sección colapsable "Más detalles". */
  detalle?: boolean;
}

/**
 * Campos REALES de cada tabla de metadatos enriquecidos (design.md §6.2, columnas
 * de los modelos ORM de FEAT-002). Las claves son las columnas de la tabla del tipo.
 * Los campos lista (`palabras_clave`, `dimensiones`, `subareas`, `competencias`) se
 * capturan como texto por comas; `carga.ts` los transforma antes de enviar.
 * Se OMITE `mapeo_de_reactivos_por_seccion` (JSONB complejo, fuera de alcance).
 */
export const CAMPOS_POR_TIPO: Record<TipoInstrumento, CampoDef[]> = {
  Encuesta: [
    {
      clave: "n_respondentes",
      etiqueta: "Número de respondentes",
      tipo: "number",
      placeholder: "Detectado automáticamente; editable",
    },
    { clave: "n_poblacion", etiqueta: "Tamaño de la población", tipo: "number" },
    { clave: "objetivo", etiqueta: "Objetivo", placeholder: "¿Qué busca medir el instrumento?" },
    { clave: "carrera", etiqueta: "Carrera", placeholder: "p. ej. Ingeniería" },
    {
      clave: "poblacion_objetivo",
      etiqueta: "Población objetivo",
      placeholder: "p. ej. estudiantes de primer año",
    },
    {
      clave: "constructo_principal",
      etiqueta: "Constructo principal",
      placeholder: "p. ej. motivación académica",
    },
    {
      clave: "palabras_clave",
      etiqueta: "Palabras clave",
      placeholder: "separadas por comas",
    },
    {
      clave: "dimensiones",
      etiqueta: "Dimensiones",
      placeholder: "separadas por comas",
    },
    { clave: "notas_contextuales", etiqueta: "Notas contextuales", tipo: "textarea" },
    { clave: "notas_interpretacion", etiqueta: "Notas de interpretación", tipo: "textarea" },
  ],
  Entrevista: [
    { clave: "identificador_propio", etiqueta: "Identificador propio" },
    { clave: "objetivo", etiqueta: "Objetivo", tipo: "textarea" },
    { clave: "metodologia", etiqueta: "Metodología", tipo: "textarea" },
    { clave: "institucion", etiqueta: "Institución" },
    { clave: "derechos", etiqueta: "Derechos", placeholder: "p. ej. CC BY 4.0" },
  ],
  "Prueba estandarizada": [
    { clave: "unidad_de_aprendizaje", etiqueta: "Unidad de aprendizaje" },
    { clave: "tipo_de_prueba", etiqueta: "Tipo de prueba", placeholder: "p. ej. diagnóstica" },
    { clave: "nivel_educativo", etiqueta: "Nivel educativo" },
    {
      clave: "objetivo_de_evaluacion",
      etiqueta: "Objetivo de evaluación",
      tipo: "textarea",
    },
    // ── Más detalles (colapsable) ──
    { clave: "institucion", etiqueta: "Institución", detalle: true },
    { clave: "campus", etiqueta: "Campus", detalle: true },
    { clave: "grado", etiqueta: "Grado", detalle: true },
    { clave: "grupo", etiqueta: "Grupo", detalle: true },
    { clave: "ciclo_escolar", etiqueta: "Ciclo escolar", detalle: true },
    { clave: "version", etiqueta: "Versión", detalle: true },
    { clave: "taxonomia_bloom", etiqueta: "Taxonomía de Bloom", detalle: true },
    {
      clave: "subareas",
      etiqueta: "Subáreas",
      placeholder: "separadas por comas",
      detalle: true,
    },
    {
      clave: "competencias",
      etiqueta: "Competencias",
      placeholder: "separadas por comas",
      detalle: true,
    },
  ],
};

interface StepMetadatosTipoProps {
  tipo: TipoInstrumento;
  valor: MetadatosTipo;
  onChange: (v: MetadatosTipo) => void;
}

export function StepMetadatosTipo({ tipo, valor, onChange }: StepMetadatosTipoProps) {
  const [mostrarDetalles, setMostrarDetalles] = useState(false);
  const campos = CAMPOS_POR_TIPO[tipo];
  const principales = campos.filter((c) => !c.detalle);
  const detalles = campos.filter((c) => c.detalle);

  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">
        Metadatos específicos para <strong className="text-foreground">{tipo}</strong>. Todos los
        campos son opcionales.
      </p>
      <div className="grid gap-5 sm:grid-cols-2">
        {principales.map((c) => (
          <CampoMetadato key={c.clave} campo={c} valor={valor} onChange={onChange} />
        ))}
      </div>

      {detalles.length > 0 && (
        <div className="space-y-4">
          <button
            type="button"
            onClick={() => setMostrarDetalles((v) => !v)}
            aria-expanded={mostrarDetalles}
            className="flex items-center gap-2 text-sm font-medium text-primary"
          >
            <ChevronDown
              className={cn("size-4 transition-transform", mostrarDetalles && "rotate-180")}
            />
            Más detalles
          </button>
          {mostrarDetalles && (
            <div className="grid gap-5 sm:grid-cols-2">
              {detalles.map((c) => (
                <CampoMetadato key={c.clave} campo={c} valor={valor} onChange={onChange} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

interface CampoMetadatoProps {
  campo: CampoDef;
  valor: MetadatosTipo;
  onChange: (v: MetadatosTipo) => void;
}

function CampoMetadato({ campo, valor, onChange }: CampoMetadatoProps) {
  const esTextarea = campo.tipo === "textarea";
  return (
    <div className={cn("space-y-2", esTextarea && "sm:col-span-2")}>
      <Label htmlFor={campo.clave}>{campo.etiqueta}</Label>
      {esTextarea ? (
        <Textarea
          id={campo.clave}
          rows={3}
          placeholder={campo.placeholder}
          maxLength={2000}
          value={valor[campo.clave] ?? ""}
          onChange={(e) => onChange({ ...valor, [campo.clave]: e.target.value })}
        />
      ) : (
        <Input
          id={campo.clave}
          type={campo.tipo === "number" ? "number" : "text"}
          min={campo.tipo === "number" ? 0 : undefined}
          placeholder={campo.placeholder}
          maxLength={campo.tipo === "number" ? undefined : 120}
          value={valor[campo.clave] ?? ""}
          onChange={(e) => onChange({ ...valor, [campo.clave]: e.target.value })}
        />
      )}
    </div>
  );
}
