import { useRef, useState } from "react";
import { ClipboardList, FileUp, FlaskConical, KeyRound, MessagesSquare } from "lucide-react";
import { cn } from "@/lib/utils";
import { TIPOS_INSTRUMENTO, type TipoInstrumento } from "@/types";
import { requiereClave } from "./archivos";

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
  tipo: TipoInstrumento | null;
  onArchivo: (f: File) => void;
  onTipo: (t: TipoInstrumento) => void;
  /** Instrumento original sin respuestas (opcional): mejora los metadatos y los KPIs. */
  archivoOriginal: File | null;
  onArchivoOriginal: (f: File | null) => void;
  /** Clave de respuestas (pruebas estandarizadas en tabla). */
  archivoClave: File | null;
  onArchivoClave: (f: File | null) => void;
}

export function StepArchivo({
  archivo,
  tipo,
  onArchivo,
  onTipo,
  archivoOriginal,
  onArchivoOriginal,
  archivoClave,
  onArchivoClave,
}: StepArchivoProps) {
  const input = useRef<HTMLInputElement>(null);
  const inputOriginal = useRef<HTMLInputElement>(null);
  const inputClave = useRef<HTMLInputElement>(null);
  const conClave = requiereClave(tipo, archivo);
  const [arrastrando, setArrastrando] = useState(false);

  return (
    <div className="space-y-8">
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
              o haz clic para seleccionarlo · CSV o XLSX (encuestas y pruebas) · PDF, DOCX o TXT
            </p>
          </>
        )}
        <input
          ref={input}
          type="file"
          className="hidden"
          accept=".csv,.xlsx,.xls,.docx,.pdf,.txt"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) onArchivo(f);
          }}
        />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-muted/30 px-4 py-3 text-sm">
        <div className="min-w-0">
          <p className="font-medium">Instrumento original (opcional)</p>
          <p className="truncate text-muted-foreground">
            {archivoOriginal
              ? archivoOriginal.name
              : "Las preguntas sin respuestas (PDF, DOCX o TXT): mejoran los metadatos y los KPIs."}
          </p>
        </div>
        <div className="flex gap-2">
          {archivoOriginal && (
            <button
              type="button"
              className="text-sm text-muted-foreground underline-offset-2 hover:underline"
              onClick={() => onArchivoOriginal(null)}
            >
              Quitar
            </button>
          )}
          <button
            type="button"
            className="rounded-lg border border-border bg-card px-3 py-1.5 text-sm font-medium hover:border-primary/60"
            onClick={() => inputOriginal.current?.click()}
          >
            {archivoOriginal ? "Cambiar" : "Adjuntar"}
          </button>
        </div>
        <input
          ref={inputOriginal}
          type="file"
          className="hidden"
          accept=".docx,.pdf,.txt"
          onChange={(e) => onArchivoOriginal(e.target.files?.[0] ?? null)}
        />
      </div>

      {conClave && (
        <div
          className={cn(
            "flex flex-wrap items-center justify-between gap-3 rounded-xl border px-4 py-3 text-sm",
            "border-border bg-muted/30",
          )}
        >
          <div className="flex min-w-0 items-start gap-3">
            <KeyRound className="mt-0.5 size-5 shrink-0 text-accent-strong" aria-hidden />
            <div className="min-w-0">
              <p className="font-medium">Clave de respuestas (opcional)</p>
              <p className="text-muted-foreground">
                {archivoClave
                  ? archivoClave.name
                  : "CSV o XLSX con la respuesta correcta de cada pregunta. Si no la tienes, te propondremos una a partir de las respuestas y la revisarás en la limpieza."}
              </p>
            </div>
          </div>
          <button
            type="button"
            className="rounded-lg border border-border bg-card px-3 py-1.5 text-sm font-medium hover:border-primary/60"
            onClick={() => inputClave.current?.click()}
          >
            {archivoClave ? "Cambiar" : "Adjuntar clave"}
          </button>
          <input
            ref={inputClave}
            type="file"
            className="hidden"
            aria-label="Clave de respuestas"
            accept=".csv,.xlsx,.xls"
            onChange={(e) => onArchivoClave(e.target.files?.[0] ?? null)}
          />
        </div>
      )}

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
