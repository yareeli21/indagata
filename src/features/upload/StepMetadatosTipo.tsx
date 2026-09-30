import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { MetadatosTipo, TipoInstrumento } from "@/types";

interface CampoDef { clave: string; etiqueta: string; tipo?: "number" | "text"; placeholder?: string }

export const CAMPOS_POR_TIPO: Record<TipoInstrumento, CampoDef[]> = {
  Encuesta: [
    { clave: "numero_reactivos", etiqueta: "Número de reactivos", tipo: "number" },
    { clave: "escala", etiqueta: "Tipo de escala", placeholder: "Likert de 5 puntos" },
    { clave: "modalidad", etiqueta: "Modalidad de aplicación", placeholder: "En línea / presencial" },
    { clave: "tamano_muestra", etiqueta: "Tamaño de muestra", tipo: "number" },
  ],
  Entrevista: [
    { clave: "tipo_entrevista", etiqueta: "Tipo de entrevista", placeholder: "Semiestructurada" },
    { clave: "numero_preguntas", etiqueta: "Número de preguntas guía", tipo: "number" },
    { clave: "duracion_minutos", etiqueta: "Duración estimada (min)", tipo: "number" },
    { clave: "perfil_informante", etiqueta: "Perfil del informante", placeholder: "Docentes de primaria" },
  ],
  "Prueba estandarizada": [
    { clave: "numero_reactivos", etiqueta: "Número de reactivos", tipo: "number" },
    { clave: "puntaje_maximo", etiqueta: "Puntaje máximo", tipo: "number" },
    { clave: "confiabilidad", etiqueta: "Confiabilidad (alfa de Cronbach)", placeholder: "0.87" },
    { clave: "tiempo_limite", etiqueta: "Tiempo límite (min)", tipo: "number" },
  ],
};

interface StepMetadatosTipoProps {
  tipo: TipoInstrumento;
  valor: MetadatosTipo;
  onChange: (v: MetadatosTipo) => void;
}

export function StepMetadatosTipo({ tipo, valor, onChange }: StepMetadatosTipoProps) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">Metadatos específicos para <strong className="text-foreground">{tipo}</strong>.</p>
      <div className="grid gap-5 sm:grid-cols-2">
        {CAMPOS_POR_TIPO[tipo].map((c) => (
          <div key={c.clave} className="space-y-2">
            <Label htmlFor={c.clave}>{c.etiqueta}</Label>
            <Input
              id={c.clave}
              type={c.tipo ?? "text"}
              min={c.tipo === "number" ? 0 : undefined}
              placeholder={c.placeholder}
              maxLength={120}
              value={valor[c.clave] ?? ""}
              onChange={(e) => onChange({ ...valor, [c.clave]: e.target.value })}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
