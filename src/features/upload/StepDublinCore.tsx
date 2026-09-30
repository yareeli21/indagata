import { Info } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { NIVELES_EDUCATIVOS, type DublinCore, type NivelEducativo } from "@/types";

interface StepDublinCoreProps {
  valor: DublinCore;
  onChange: (v: DublinCore) => void;
}

export function StepDublinCore({ valor, onChange }: StepDublinCoreProps) {
  const set = (k: keyof DublinCore) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    onChange({ ...valor, [k]: e.target.value });

  return (
    <div className="grid gap-5 sm:grid-cols-2">
      <Campo id="titulo" label="Título *" className="sm:col-span-2">
        <Input id="titulo" value={valor.titulo} onChange={set("titulo")} maxLength={200} />
      </Campo>
      <Campo id="creador" label="Creador *">
        <Input id="creador" value={valor.creador} onChange={set("creador")} maxLength={120} />
      </Campo>
      <Campo id="tema" label="Tema">
        <Input id="tema" value={valor.tema} onChange={set("tema")} placeholder="p. ej. comprensión lectora" maxLength={120} />
      </Campo>
      <Campo id="descripcion" label="Descripción *" className="sm:col-span-2">
        <Textarea id="descripcion" rows={5} value={valor.descripcion} onChange={set("descripcion")} maxLength={2000} />
        <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Info className="size-3.5" /> Se usa para encontrar instrumentos similares.
        </p>
      </Campo>
      <Campo id="fecha" label="Fecha">
        <Input id="fecha" type="date" value={valor.fecha} onChange={set("fecha")} />
      </Campo>
      <Campo id="idioma" label="Idioma">
        <Input id="idioma" value={valor.idioma} onChange={set("idioma")} maxLength={40} />
      </Campo>
      <Campo id="derechos" label="Derechos">
        <Input id="derechos" value={valor.derechos} onChange={set("derechos")} placeholder="p. ej. CC BY 4.0" maxLength={120} />
      </Campo>
      <Campo id="cobertura" label="Nivel educativo (cobertura) *">
        <Select value={valor.cobertura} onValueChange={(v) => onChange({ ...valor, cobertura: v as NivelEducativo })}>
          <SelectTrigger id="cobertura"><SelectValue placeholder="Selecciona un nivel" /></SelectTrigger>
          <SelectContent>
            {NIVELES_EDUCATIVOS.map((n) => <SelectItem key={n} value={n}>{n}</SelectItem>)}
          </SelectContent>
        </Select>
      </Campo>
    </div>
  );
}

interface CampoProps { id: string; label: string; className?: string; children: React.ReactNode }

function Campo({ id, label, className, children }: CampoProps) {
  return (
    <div className={`space-y-2 ${className ?? ""}`}>
      <Label htmlFor={id}>{label}</Label>
      {children}
    </div>
  );
}
