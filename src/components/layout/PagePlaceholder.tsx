import type { LucideIcon } from "lucide-react";

interface PagePlaceholderProps {
  titulo: string;
  descripcion: string;
  icono: LucideIcon;
}

export function PagePlaceholder({ titulo, descripcion, icono: Icono }: PagePlaceholderProps) {
  return (
    <section className="mx-auto w-full max-w-5xl px-4 py-10 md:px-8">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">{titulo}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{descripcion}</p>
      </header>

      <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-border bg-card px-6 py-20 text-center shadow-card">
        <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary-soft text-primary">
          <Icono className="h-6 w-6" />
        </span>
        <p className="text-sm font-medium text-foreground">Pantalla en construcción</p>
        <p className="max-w-sm text-sm text-muted-foreground">
          El contenido de esta sección se agregará en el siguiente paso.
        </p>
      </div>
    </section>
  );
}
