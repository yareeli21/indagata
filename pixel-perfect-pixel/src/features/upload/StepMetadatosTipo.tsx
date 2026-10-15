import { ProcesandoIA } from "@/components/shared/ProcesandoIA";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { MetadatosTipo, OrigenMetadato, TipoInstrumento } from "@/types";
import { EtiquetaOrigen } from "./EtiquetaOrigen";

interface CampoDef {
  /** Columna de la tabla metadatos_enriquecidos_* */
  clave: string;
  etiqueta: string;
  tipo?: "number" | "text" | "textarea";
  placeholder?: string;
  ayuda?: string;
}

/** Campos por tipo, 1:1 con las tablas de infrastructure/postgres/init/01_schema.sql. */
export const CAMPOS_POR_TIPO: Record<TipoInstrumento, CampoDef[]> = {
  Encuesta: [
    { clave: "n_respondentes", etiqueta: "Número de respondentes", tipo: "number" },
    { clave: "n_poblacion", etiqueta: "Tamaño de la población", tipo: "number" },
    { clave: "objetivo", etiqueta: "Objetivo", tipo: "textarea" },
    {
      clave: "poblacion_objetivo",
      etiqueta: "Población objetivo",
      placeholder: "Estudiantes de licenciatura",
    },
    { clave: "carrera", etiqueta: "Carrera(s)", placeholder: "Pedagogía, Derecho" },
    {
      clave: "constructo_principal",
      etiqueta: "Constructo principal",
      placeholder: "Compromiso escolar",
    },
    { clave: "palabras_clave", etiqueta: "Palabras clave", ayuda: "Separadas por comas." },
    {
      clave: "dimensiones",
      etiqueta: "Dimensiones",
      ayuda: "Subescalas o bloques, separados por comas.",
    },
    { clave: "notas_contextuales", etiqueta: "Notas contextuales", tipo: "textarea" },
    { clave: "notas_interpretacion", etiqueta: "Notas de interpretación", tipo: "textarea" },
  ],
  Entrevista: [
    { clave: "identificador_propio", etiqueta: "Identificador propio" },
    { clave: "objetivo", etiqueta: "Objetivo", tipo: "textarea" },
    { clave: "metodologia", etiqueta: "Metodología", placeholder: "Entrevista semiestructurada" },
    { clave: "institucion", etiqueta: "Institución" },
    {
      clave: "derechos",
      etiqueta: "Derechos",
      placeholder: "Consentimiento informado, uso académico",
    },
  ],
  "Prueba estandarizada": [
    { clave: "unidad_de_aprendizaje", etiqueta: "Unidad de aprendizaje" },
    { clave: "objetivo_de_evaluacion", etiqueta: "Objetivo de la evaluación", tipo: "textarea" },
    {
      clave: "tipo_de_prueba",
      etiqueta: "Tipo de prueba",
      placeholder: "Diagnóstica, formativa, sumativa",
    },
    { clave: "nivel_educativo", etiqueta: "Nivel educativo" },
    {
      clave: "mapeo_de_reactivos_por_seccion",
      etiqueta: "Reactivos por sección",
      tipo: "textarea",
      placeholder: "Sección A: 10\nSección B: 5",
      ayuda: "Una línea por sección con el formato «Sección: número».",
    },
    { clave: "institucion", etiqueta: "Institución" },
    { clave: "campus", etiqueta: "Campus" },
    { clave: "grado", etiqueta: "Grado" },
    { clave: "grupo", etiqueta: "Grupo" },
    { clave: "ciclo_escolar", etiqueta: "Ciclo escolar", placeholder: "2024-2025" },
    { clave: "version", etiqueta: "Versión" },
    { clave: "taxonomia_bloom", etiqueta: "Taxonomía de Bloom" },
    { clave: "subareas", etiqueta: "Subáreas" },
    { clave: "competencias", etiqueta: "Competencias", tipo: "textarea" },
  ],
};

interface StepMetadatosTipoProps {
  tipo: TipoInstrumento;
  valor: MetadatosTipo;
  onChange: (v: MetadatosTipo) => void;
  origen: Record<string, OrigenMetadato>;
  obligatorios: string[];
  cargando: boolean;
}

export function StepMetadatosTipo({
  tipo,
  valor,
  onChange,
  origen,
  obligatorios,
  cargando,
}: StepMetadatosTipoProps) {
  if (cargando) {
    return <ProcesandoIA mensaje="Completando los metadatos faltantes…" />;
  }
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Metadatos específicos para <strong className="text-foreground">{tipo}</strong>. Los valores
        propuestos se infirieron del archivo; corrige lo necesario y completa los obligatorios (*).
      </p>
      <div className="grid gap-5 sm:grid-cols-2">
        {CAMPOS_POR_TIPO[tipo].map((c) => {
          const largo = c.tipo === "textarea";
          const etiqueta = `${c.etiqueta}${obligatorios.includes(c.clave) ? " *" : ""}`;
          return (
            <div key={c.clave} className={`space-y-2 ${largo ? "sm:col-span-2" : ""}`}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <Label htmlFor={c.clave}>{etiqueta}</Label>
                <EtiquetaOrigen origen={origen[c.clave]} />
              </div>
              {largo ? (
                <Textarea
                  id={c.clave}
                  rows={3}
                  placeholder={c.placeholder}
                  maxLength={2000}
                  value={valor[c.clave] ?? ""}
                  onChange={(e) => onChange({ ...valor, [c.clave]: e.target.value })}
                />
              ) : (
                <Input
                  id={c.clave}
                  type={c.tipo ?? "text"}
                  min={c.tipo === "number" ? 0 : undefined}
                  placeholder={c.placeholder}
                  maxLength={300}
                  value={valor[c.clave] ?? ""}
                  onChange={(e) => onChange({ ...valor, [c.clave]: e.target.value })}
                />
              )}
              {c.ayuda && <p className="text-xs text-muted-foreground">{c.ayuda}</p>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
