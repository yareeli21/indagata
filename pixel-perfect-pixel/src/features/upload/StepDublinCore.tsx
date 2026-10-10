import { Info, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  NIVELES_EDUCATIVOS,
  type DublinCore,
  type NivelEducativo,
  type OrigenMetadato,
} from "@/types";
import { EtiquetaOrigen } from "./EtiquetaOrigen";

interface StepDublinCoreProps {
  valor: DublinCore;
  onChange: (v: DublinCore) => void;
  /** Origen de cada valor propuesto, por campo del formulario. */
  origen: Partial<Record<keyof DublinCore, OrigenMetadato>>;
  cargando: boolean;
  notas: string[];
}

export function StepDublinCore({ valor, onChange, origen, cargando, notas }: StepDublinCoreProps) {
  if (cargando) {
    return (
      <div className="flex items-center justify-center gap-2 py-16 text-muted-foreground">
        <Loader2 className="size-5 animate-spin" /> Analizando el instrumento para proponer sus
        metadatos…
      </div>
    );
  }

  const set =
    (k: keyof DublinCore) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      onChange({ ...valor, [k]: e.target.value });

  return (
    <div className="space-y-6">
      <p className="flex items-start gap-2 rounded-xl bg-primary-soft p-3 text-sm text-foreground">
        <Info className="mt-0.5 size-4 shrink-0 text-primary" />
        Dublin Core es obligatorio para todo instrumento. Revisa los valores propuestos: los
        aprobarás en el paso «Aprobar metadatos».
      </p>

      <div className="grid gap-5 sm:grid-cols-2">
        <Campo id="titulo" label="Título *" origen={origen.titulo} className="sm:col-span-2">
          <Input id="titulo" value={valor.titulo} onChange={set("titulo")} maxLength={200} />
        </Campo>
        <Campo id="creador" label="Creador *" origen={origen.creador}>
          <Input id="creador" value={valor.creador} onChange={set("creador")} maxLength={120} />
        </Campo>
        <Campo id="editor" label="Editor (institución) *" origen={origen.editor}>
          <Input id="editor" value={valor.editor} onChange={set("editor")} maxLength={160} />
        </Campo>
        <Campo id="tema" label="Tema *" origen={origen.tema} className="sm:col-span-2">
          <Input
            id="tema"
            value={valor.tema}
            onChange={set("tema")}
            placeholder="Palabras clave separadas por comas"
            maxLength={300}
          />
        </Campo>
        <Campo
          id="descripcion"
          label="Descripción *"
          origen={origen.descripcion}
          className="sm:col-span-2"
        >
          <Textarea
            id="descripcion"
            rows={4}
            value={valor.descripcion}
            onChange={set("descripcion")}
            maxLength={2000}
          />
          <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Info className="size-3.5" /> Se usa para encontrar instrumentos similares y en el chat.
          </p>
        </Campo>
        <Campo id="cobertura" label="Nivel educativo (cobertura) *" origen={origen.cobertura}>
          <Select
            value={valor.cobertura}
            onValueChange={(v) => onChange({ ...valor, cobertura: v as NivelEducativo })}
          >
            <SelectTrigger id="cobertura">
              <SelectValue placeholder="Selecciona un nivel" />
            </SelectTrigger>
            <SelectContent>
              {NIVELES_EDUCATIVOS.map((n) => (
                <SelectItem key={n} value={n}>
                  {n}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Campo>
        <Campo id="coberturaDetalle" label="Alcance (población, lugar, periodo)">
          <Input
            id="coberturaDetalle"
            value={valor.coberturaDetalle}
            onChange={set("coberturaDetalle")}
            placeholder="p. ej. Estudiantes de la UNAM, 2024"
            maxLength={200}
          />
        </Campo>
        <Campo id="fecha" label="Fecha *" origen={origen.fecha}>
          <Input id="fecha" type="date" value={valor.fecha} onChange={set("fecha")} />
        </Campo>
        <Campo id="idioma" label="Idioma (código) *" origen={origen.idioma}>
          <Input
            id="idioma"
            value={valor.idioma}
            onChange={set("idioma")}
            placeholder="es"
            maxLength={10}
          />
        </Campo>
        <Campo id="derechos" label="Derechos *" origen={origen.derechos} className="sm:col-span-2">
          <Input
            id="derechos"
            value={valor.derechos}
            onChange={set("derechos")}
            placeholder="p. ej. CC BY 4.0"
            maxLength={255}
          />
        </Campo>
        <Campo
          id="relacion"
          label="Relación (opcional)"
          origen={origen.relacion}
          className="sm:col-span-2"
        >
          <Input
            id="relacion"
            value={valor.relacion}
            onChange={set("relacion")}
            placeholder="Proyecto o instrumentos relacionados"
            maxLength={300}
          />
        </Campo>
      </div>

      <div className="grid gap-5 rounded-xl border border-dashed border-border p-4 sm:grid-cols-3">
        <Campo id="tipo" label="Tipo" origen={origen.tipo}>
          <Input id="tipo" value={valor.tipo} readOnly className="bg-muted" />
        </Campo>
        <Campo id="formato" label="Formato" origen={origen.formato}>
          <Input id="formato" value={valor.formato} readOnly className="bg-muted" />
        </Campo>
        <Campo id="fuente" label="Fuente" origen={origen.fuente}>
          <Input id="fuente" value={valor.fuente} readOnly className="bg-muted" />
        </Campo>
      </div>

      {notas.length > 0 && (
        <ul className="space-y-1 text-xs text-muted-foreground">
          {notas.map((n) => (
            <li key={n}>• {n}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

interface CampoProps {
  id: string;
  label: string;
  origen?: OrigenMetadato | undefined;
  className?: string;
  children: React.ReactNode;
}

function Campo({ id, label, origen, className, children }: CampoProps) {
  return (
    <div className={`space-y-2 ${className ?? ""}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Label htmlFor={id}>{label}</Label>
        <EtiquetaOrigen origen={origen} />
      </div>
      {children}
    </div>
  );
}
