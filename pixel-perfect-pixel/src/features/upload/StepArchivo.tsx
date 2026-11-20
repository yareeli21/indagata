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
  "Prueba estandarizada": "Hojas de respuestas de los alumnos (no se califican).",
};

interface StepArchivoProps {
  archivo: File | null;
  tipo: TipoInstrumento | null;
  onArchivo: (f: File) => void;
  onTipo: (t: TipoInstrumento) => void;
  /** Instrumento original sin respuestas (opcional): mejora los metadatos y los KPIs. */
  archivoOriginal: File | null;
  onArchivoOriginal: (f: File | null) => void;
  /** Diccionario de datos de los microdatos (opcional): texto de las preguntas en código y significado de sus códigos. */
  archivoDiccionario: File | null;
  onArchivoDiccionario: (f: File | null) => void;
}

interface AdjuntoOpcionalProps {
  titulo: string;
  ayuda: string;
  archivo: File | null;
  aceptar: string;
  onArchivo: (f: File | null) => void;
}

/** Un archivo opcional que acompaña al respondido (instrumento original o diccionario de datos). */
function AdjuntoOpcional({ titulo, ayuda, archivo, aceptar, onArchivo }: AdjuntoOpcionalProps) {
  const input = useRef<HTMLInputElement>(null);
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-muted/30 px-4 py-3 text-sm">
      <div className="min-w-0">
        <p className="font-medium">{titulo}</p>
        <p className="truncate text-muted-foreground">{archivo ? archivo.name : ayuda}</p>
      </div>
      <div className="flex gap-2">
        {archivo && (
          <button
            type="button"
            className="text-sm text-muted-foreground underline-offset-2 hover:underline"
            onClick={() => onArchivo(null)}
          >
            Quitar
          </button>
        )}
        <button
          type="button"
          className="rounded-lg border border-border bg-card px-3 py-1.5 text-sm font-medium hover:border-primary/60"
          onClick={() => input.current?.click()}
        >
          {archivo ? "Cambiar" : "Adjuntar"}
        </button>
      </div>
      <input
        ref={input}
        type="file"
        className="hidden"
        accept={aceptar}
        onChange={(e) => onArchivo(e.target.files?.[0] ?? null)}
      />
    </div>
  );
}

export function StepArchivo({
  archivo,
  tipo,
  onArchivo,
  onTipo,
  archivoOriginal,
  onArchivoOriginal,
  archivoDiccionario,
  onArchivoDiccionario,
}: StepArchivoProps) {
  const input = useRef<HTMLInputElement>(null);
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

      <AdjuntoOpcional
        titulo="Instrumento original (opcional)"
        ayuda="Las preguntas sin respuestas (PDF, DOCX o TXT): mejoran los metadatos y los KPIs."
        archivo={archivoOriginal}
        aceptar=".docx,.pdf,.txt"
        onArchivo={onArchivoOriginal}
      />

      {tipo !== "Entrevista" && (
        <AdjuntoOpcional
          titulo="Diccionario de datos (opcional)"
          ayuda="Si tu archivo usa códigos (P1, P2… o 1 = Hombre, 2 = Mujer): CSV o Excel con variable, pregunta, valor y etiqueta."
          archivo={archivoDiccionario}
          aceptar=".csv,.xlsx,.xls"
          onArchivo={onArchivoDiccionario}
        />
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
