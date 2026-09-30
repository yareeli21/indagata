import { useRef, useState } from "react";
import { ClipboardList, FileUp, FlaskConical, MessagesSquare } from "lucide-react";
import { cn } from "@/lib/utils";
import { TIPOS_INSTRUMENTO, type TipoInstrumento } from "@/types";

const ICONOS = { Encuesta: ClipboardList, Entrevista: MessagesSquare, "Prueba estandarizada": FlaskConical };
const DESCRIPCION = {
  Encuesta: "Cuestionarios con reactivos cerrados o escalas.",
  Entrevista: "Guías y transcripciones de preguntas abiertas.",
  "Prueba estandarizada": "Evaluaciones con clave de respuestas y puntajes.",
};

interface StepArchivoProps {
  archivo: File | null;
  tipo: TipoInstrumento | null;
  onArchivo: (f: File) => void;
  onTipo: (t: TipoInstrumento) => void;
}

export function StepArchivo({ archivo, tipo, onArchivo, onTipo }: StepArchivoProps) {
  const input = useRef<HTMLInputElement>(null);
  const [arrastrando, setArrastrando] = useState(false);

  return (
    <div className="space-y-8">
      <div
        role="button"
        tabIndex={0}
        onClick={() => input.current?.click()}
        onKeyDown={(e) => e.key === "Enter" && input.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setArrastrando(true); }}
        onDragLeave={() => setArrastrando(false)}
        onDrop={(e) => {
          e.preventDefault();
          setArrastrando(false);
          const f = e.dataTransfer.files[0];
          if (f) onArchivo(f);
        }}
        className={cn(
          "flex cursor-pointer flex-col items-center gap-3 rounded-xl border-2 border-dashed p-10 text-center transition-colors",
          arrastrando ? "border-primary bg-primary/5" : "border-border hover:border-primary/60",
        )}
      >
        <FileUp className="size-10 text-primary" />
        {archivo ? (
          <>
            <p className="font-medium">{archivo.name}</p>
            <p className="text-sm text-muted-foreground">{(archivo.size / 1024).toFixed(1)} KB · haz clic para cambiarlo</p>
          </>
        ) : (
          <>
            <p className="font-medium">Arrastra y suelta tu archivo aquí</p>
            <p className="text-sm text-muted-foreground">o haz clic para seleccionarlo · CSV, XLSX, DOCX o PDF</p>
          </>
        )}
        <input
          ref={input}
          type="file"
          className="hidden"
          accept=".csv,.xlsx,.xls,.docx,.pdf"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) onArchivo(f); }}
        />
      </div>

      <div className="space-y-3">
        <h3 className="font-semibold">Tipo de instrumento</h3>
        <div className="grid gap-4 sm:grid-cols-3">
          {TIPOS_INSTRUMENTO.map((t) => {
            const Icono = ICONOS[t];
            const sel = tipo === t;
            return (
              <button
                key={t}
                type="button"
                aria-pressed={sel}
                onClick={() => onTipo(t)}
                className={cn(
                  "flex flex-col items-start gap-2 rounded-xl border bg-card p-5 text-left shadow-sm transition-all",
                  sel ? "border-primary ring-2 ring-primary/30" : "hover:border-primary/50",
                )}
              >
                <Icono className={cn("size-6", sel ? "text-primary" : "text-muted-foreground")} />
                <span className="font-medium">{t}</span>
                <span className="text-sm text-muted-foreground">{DESCRIPCION[t]}</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
