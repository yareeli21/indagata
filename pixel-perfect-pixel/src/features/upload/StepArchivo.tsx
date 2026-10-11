import { useRef, useState } from "react";
import { ClipboardList, FileUp, FlaskConical, MessagesSquare } from "lucide-react";
import { cn } from "@/lib/utils";
import { TIPOS_INSTRUMENTO, type TipoInstrumento } from "@/types";

const ICONOS = {
  Encuesta: ClipboardList,
  Entrevista: MessagesSquare,
  "Prueba estandarizada": FlaskConical,
};
const DESCRIPCION = {
  Encuesta: "Cuestionarios con reactivos cerrados o escalas.",
  Entrevista: "Guías y transcripciones de preguntas abiertas.",
  "Prueba estandarizada": "Evaluaciones con clave de respuestas y puntajes.",
};

interface StepArchivoProps {
  archivo: File | null;
  archivoOriginal: File | null;
  tipo: TipoInstrumento | null;
  onArchivo: (f: File) => void;
  onArchivoOriginal: (f: File) => void;
  onTipo: (t: TipoInstrumento) => void;
}

export function StepArchivo({
  archivo,
  archivoOriginal,
  tipo,
  onArchivo,
  onArchivoOriginal,
  onTipo,
}: StepArchivoProps) {
  const input = useRef<HTMLInputElement>(null);
  const inputOriginal = useRef<HTMLInputElement>(null);
  const [arrastrando, setArrastrando] = useState(false);
  const [arrastrandoOriginal, setArrastrandoOriginal] = useState(false);

  return (
    <div className="space-y-8">
      <div className="space-y-3">
        <h3 className="font-semibold">Archivo respondido (con las respuestas)</h3>
        <div
          role="button"
          tabIndex={0}
          onClick={() => input.current?.click()}
          onKeyDown={(e) => e.key === "Enter" && input.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setArrastrando(true);
          }}
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
              <p className="text-sm text-muted-foreground">
                {(archivo.size / 1024).toFixed(1)} KB · haz clic para cambiarlo
              </p>
            </>
          ) : (
            <>
              <p className="font-medium">Arrastra y suelta tu archivo aquí</p>
              <p className="text-sm text-muted-foreground">
                o haz clic para seleccionarlo · CSV, XLSX, DOCX o PDF
              </p>
            </>
          )}
          <input
            ref={input}
            type="file"
            className="hidden"
            accept=".csv,.xlsx,.xls,.docx,.pdf"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) onArchivo(f);
            }}
          />
        </div>
      </div>

      <div className="space-y-3">
        <h3 className="font-semibold">Instrumento original (solo preguntas) — opcional</h3>
        <div
          role="button"
          tabIndex={0}
          onClick={() => inputOriginal.current?.click()}
          onKeyDown={(e) => e.key === "Enter" && inputOriginal.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setArrastrandoOriginal(true);
          }}
          onDragLeave={() => setArrastrandoOriginal(false)}
          onDrop={(e) => {
            e.preventDefault();
            setArrastrandoOriginal(false);
            const f = e.dataTransfer.files[0];
            if (f) onArchivoOriginal(f);
          }}
          className={cn(
            "flex cursor-pointer flex-col items-center gap-3 rounded-xl border-2 border-dashed p-10 text-center transition-colors",
            arrastrandoOriginal
              ? "border-primary bg-primary/5"
              : "border-border hover:border-primary/60",
          )}
        >
          <FileUp className="size-10 text-primary" />
          {archivoOriginal ? (
            <>
              <p className="font-medium">{archivoOriginal.name}</p>
              <p className="text-sm text-muted-foreground">
                {(archivoOriginal.size / 1024).toFixed(1)} KB · haz clic para cambiarlo
              </p>
            </>
          ) : (
            <>
              <p className="font-medium">Arrastra y suelta el instrumento original aquí</p>
              <p className="text-sm text-muted-foreground">
                o haz clic para seleccionarlo · TXT, PDF o DOCX
              </p>
            </>
          )}
          <input
            ref={inputOriginal}
            type="file"
            className="hidden"
            accept=".txt,.pdf,.docx"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) onArchivoOriginal(f);
            }}
          />
        </div>
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
                  "flex flex-col items-start gap-2 rounded-2xl border border-border bg-card p-5 text-left shadow-card transition-all",
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
