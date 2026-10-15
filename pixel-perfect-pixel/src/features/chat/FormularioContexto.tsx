import { useState } from "react";
import { BookOpen, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { NIVELES_EDUCATIVOS, type ContextoInvestigacion, type NivelEducativo } from "@/types";

interface FormularioContextoProps {
  nombreInvestigacion: string;
  onComenzar: (ctx: ContextoInvestigacion) => Promise<void>;
}

export function FormularioContexto({ nombreInvestigacion, onComenzar }: FormularioContextoProps) {
  const [objetivo, setObjetivo] = useState("");
  const [poblacion, setPoblacion] = useState("");
  const [nivel, setNivel] = useState<NivelEducativo | "">("");
  const [pregunta, setPregunta] = useState("");
  const [enviando, setEnviando] = useState(false);

  const nivelElegido = (n: NivelEducativo | ""): n is NivelEducativo => n.length > 0;

  const completo =
    objetivo.trim().length > 0 &&
    poblacion.trim().length > 0 &&
    nivelElegido(nivel) &&
    pregunta.trim().length > 0;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!completo || !nivelElegido(nivel)) return;
    setEnviando(true);
    await onComenzar({
      objetivo: objetivo.trim(),
      poblacion: poblacion.trim(),
      nivel,
      pregunta: pregunta.trim(),
    });
  }

  return (
    <div className="w-full">
      <div className="superficie w-full space-y-8 rounded-3xl p-6 md:p-8 lg:p-10">
        {/* Encabezado */}
        <div className="flex items-start gap-4">
          <span className="flex size-14 shrink-0 items-center justify-center rounded-2xl bg-primary-soft text-primary">
            <BookOpen className="size-7" />
          </span>
          <div>
            <h2 className="font-display text-2xl font-bold leading-tight tracking-tight">
              Cuéntame sobre tu investigación
            </h2>
            <p className="text-base text-muted-foreground">{nombreInvestigacion}</p>
          </div>
        </div>

        <form
          onSubmit={handleSubmit}
          className="grid gap-6 lg:grid-cols-2 [&>button]:lg:col-span-2 [&>button]:lg:w-auto [&>button]:lg:justify-self-start [&>button]:lg:px-12"
        >
          {/* Objetivo */}
          <div className="space-y-2">
            <Label htmlFor="ctx-objetivo">
              Objetivo de la investigación
              <span className="ml-1 text-destructive" aria-hidden>
                *
              </span>
            </Label>
            <Textarea
              id="ctx-objetivo"
              placeholder="Ej. Identificar los factores que inciden en el rendimiento académico…"
              rows={2}
              maxLength={300}
              value={objetivo}
              onChange={(e) => setObjetivo(e.target.value)}
            />
          </div>

          {/* Población */}
          <div className="space-y-2">
            <Label htmlFor="ctx-poblacion">
              Población de estudio
              <span className="ml-1 text-destructive" aria-hidden>
                *
              </span>
            </Label>
            <Input
              id="ctx-poblacion"
              placeholder="Ej. Estudiantes de licenciatura de universidades públicas"
              maxLength={150}
              value={poblacion}
              onChange={(e) => setPoblacion(e.target.value)}
            />
          </div>

          {/* Nivel educativo */}
          <div className="space-y-2">
            <Label htmlFor="ctx-nivel">
              Nivel educativo
              <span className="ml-1 text-destructive" aria-hidden>
                *
              </span>
            </Label>
            <Select value={nivel} onValueChange={(v) => setNivel(v as NivelEducativo)}>
              <SelectTrigger id="ctx-nivel">
                <SelectValue placeholder="Selecciona un nivel…" />
              </SelectTrigger>
              <SelectContent>
                {NIVELES_EDUCATIVOS.map((n) => (
                  <SelectItem key={n} value={n}>
                    {n}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Pregunta de investigación */}
          <div className="space-y-2">
            <Label htmlFor="ctx-pregunta">
              Pregunta de investigación
              <span className="ml-1 text-destructive" aria-hidden>
                *
              </span>
            </Label>
            <Textarea
              id="ctx-pregunta"
              placeholder="Ej. ¿Qué variables predicen mejor el rendimiento académico en licenciatura?"
              rows={2}
              maxLength={300}
              value={pregunta}
              onChange={(e) => setPregunta(e.target.value)}
            />
          </div>

          <Button type="submit" className="w-full" disabled={!completo || enviando}>
            {enviando && <Loader2 className="animate-spin" />}
            Comenzar
          </Button>
        </form>
      </div>
    </div>
  );
}
