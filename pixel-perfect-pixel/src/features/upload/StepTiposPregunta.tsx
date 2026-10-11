import { FileText, Info, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { tipoPreguntaABackend, tipoPreguntaAUI } from "@/api/carga";
import {
  TIPOS_PREGUNTA_UI,
  type ConfianzaDeteccion,
  type PreguntaPreview,
  type TipoPreguntaUI,
} from "@/types";

/** Límite de caracteres del texto mostrado en la UI (el estado conserva el completo). */
const MAX_TEXTO_VISIBLE = 160;

const VARIANTE_CONFIANZA: Record<ConfianzaDeteccion, "default" | "secondary" | "outline"> = {
  alta: "default",
  media: "secondary",
  baja: "outline",
};

const ETIQUETA_CONFIANZA: Record<ConfianzaDeteccion, string> = {
  alta: "Confianza alta",
  media: "Confianza media",
  baja: "Confianza baja",
};

interface StepTiposPreguntaProps {
  /** Preguntas en edición (controladas por el wizard). `null` mientras carga el preview. */
  preguntas: PreguntaPreview[] | null;
  /** Notas informativas del preview (columnas ignoradas, etc.). */
  notas: string[];
  /** Emite la lista actualizada tras cada edición. */
  onChange: (preguntas: PreguntaPreview[]) => void;
}

function truncar(texto: string): string {
  return texto.length > MAX_TEXTO_VISIBLE ? `${texto.slice(0, MAX_TEXTO_VISIBLE)}…` : texto;
}

export function StepTiposPregunta({ preguntas, notas, onChange }: StepTiposPreguntaProps) {
  if (!preguntas) {
    return (
      <div className="flex items-center justify-center gap-2 py-16 text-muted-foreground">
        <Loader2 className="size-5 animate-spin" /> Analizando las preguntas del instrumento…
      </div>
    );
  }

  // Caso documento: una sola pregunta abierta con el texto completo (NIT #2).
  const esDocumento = preguntas.length === 1 && preguntas[0].type === "abierta";

  function actualizar(index: number, cambios: Partial<PreguntaPreview>) {
    const copia = preguntas!.map((p, i) => (i === index ? { ...p, ...cambios } : p));
    onChange(copia);
  }

  if (esDocumento) {
    return (
      <div className="space-y-5">
        <div className="flex gap-3 rounded-2xl border border-border bg-accent-soft p-4 text-accent-foreground">
          <FileText className="size-5 shrink-0" />
          <p className="text-sm">
            Este instrumento es un documento de texto; no se tipifican preguntas individuales. Se
            registrará como una sola pregunta abierta con el contenido completo.
          </p>
        </div>
        <Notas notas={notas} />
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <p className="text-sm text-muted-foreground">
        El sistema propuso un tipo para cada pregunta. Confirma o corrige los tipos antes de
        continuar.
      </p>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[40%]">Pregunta</TableHead>
            <TableHead>Tipo</TableHead>
            <TableHead>Escala</TableHead>
            <TableHead>¿Demográfica?</TableHead>
            <TableHead>Confianza</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {preguntas.map((p, i) => {
            const esLikert = p.type === "likert";
            return (
              <TableRow key={p.question_id}>
                <TableCell className="align-top">
                  <span className="block text-sm" title={p.text}>
                    {truncar(p.text)}
                  </span>
                </TableCell>
                <TableCell className="align-top">
                  <Select
                    value={tipoPreguntaAUI(p.type)}
                    onValueChange={(v) =>
                      actualizar(i, { type: tipoPreguntaABackend(v as TipoPreguntaUI) })
                    }
                  >
                    <SelectTrigger
                      aria-label={`Tipo de ${p.question_id}`}
                      className="min-w-[11rem]"
                    >
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {TIPOS_PREGUNTA_UI.map((t) => (
                        <SelectItem key={t} value={t}>
                          {t}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </TableCell>
                <TableCell className="align-top">
                  {esLikert ? (
                    <div className="flex items-center gap-2">
                      <Label htmlFor={`${p.question_id}-min`} className="sr-only">
                        Mínimo
                      </Label>
                      <Input
                        id={`${p.question_id}-min`}
                        type="number"
                        min={1}
                        max={100}
                        className="w-16"
                        value={p.scale_min ?? ""}
                        onChange={(e) =>
                          actualizar(i, {
                            scale_min: e.target.value === "" ? null : Number(e.target.value),
                          })
                        }
                      />
                      <span className="text-muted-foreground">a</span>
                      <Label htmlFor={`${p.question_id}-max`} className="sr-only">
                        Máximo
                      </Label>
                      <Input
                        id={`${p.question_id}-max`}
                        type="number"
                        min={1}
                        max={100}
                        className="w-16"
                        value={p.scale_max ?? ""}
                        onChange={(e) =>
                          actualizar(i, {
                            scale_max: e.target.value === "" ? null : Number(e.target.value),
                          })
                        }
                      />
                    </div>
                  ) : (
                    <span className="text-sm text-muted-foreground">—</span>
                  )}
                </TableCell>
                <TableCell className="align-top">
                  <Switch
                    aria-label={`¿${p.question_id} es demográfica?`}
                    checked={p.es_demografica}
                    onCheckedChange={(v) => actualizar(i, { es_demografica: v })}
                  />
                </TableCell>
                <TableCell className="align-top">
                  <Badge variant={VARIANTE_CONFIANZA[p.confianza]}>
                    {ETIQUETA_CONFIANZA[p.confianza]}
                  </Badge>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>

      <Notas notas={notas} />
    </div>
  );
}

function Notas({ notas }: { notas: string[] }) {
  if (notas.length === 0) return null;
  return (
    <div className="space-y-2 rounded-2xl border border-border bg-muted/30 p-4">
      <p className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        <Info className="size-3.5" /> Observaciones del análisis
      </p>
      <ul className="list-inside list-disc space-y-1 text-xs text-muted-foreground">
        {notas.map((nota, i) => (
          <li key={i}>{nota}</li>
        ))}
      </ul>
    </div>
  );
}
