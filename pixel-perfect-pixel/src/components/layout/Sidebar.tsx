import { Link } from "@tanstack/react-router";
import { ArrowRight, Upload } from "lucide-react";
import { useAuth } from "@/features/auth/AuthContext";
import { cn } from "@/lib/utils";
import { GridPattern } from "@/components/efectos/GridPattern";
import { RUTAS_EXACTAS, gruposNavegacion } from "./navegacion";

/** Marca de INDAGATA: monograma + nombre (el nombre se oculta en modo compacto). */
export function Marca({ compacto = false }: { compacto?: boolean }) {
  return (
    <Link
      to="/inicio"
      className="flex items-center gap-3 rounded-xl px-1 py-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring"
      aria-label="INDAGATA — inicio"
    >
      <span className="relative flex size-11 shrink-0 items-center justify-center overflow-hidden rounded-2xl bg-hero font-display text-lg font-bold text-hero-foreground shadow-lift">
        I
        <span aria-hidden className="absolute bottom-2 right-2 size-1.5 rounded-full bg-accent" />
      </span>
      {!compacto && (
        <span className="flex flex-col leading-none">
          <span className="font-display text-xl font-bold tracking-tight text-sidebar-foreground">
            INDAGATA
          </span>
          <span className="mt-1 text-xs font-semibold text-muted-foreground">
            Investigación educativa
          </span>
        </span>
      )}
    </Link>
  );
}

interface ListaNavegacionProps {
  /** Solo iconos (sidebar en tablet). */
  compacto?: boolean;
  /** Se llama al elegir una opción (p. ej. para cerrar el menú móvil). */
  onNavegar?: () => void;
}

export function ListaNavegacion({ compacto = false, onNavegar }: ListaNavegacionProps) {
  const { usuario } = useAuth();
  const grupos = gruposNavegacion(usuario?.rol);

  return (
    <nav aria-label="Navegación principal" className="flex flex-col gap-5">
      {grupos.map((grupo, i) => (
        <div key={grupo.titulo ?? i} className="flex flex-col gap-1">
          {grupo.titulo &&
            (compacto ? (
              <span aria-hidden className="mx-auto mb-1 h-px w-8 bg-sidebar-border" />
            ) : (
              <p className="mb-1 px-3 text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">
                {grupo.titulo}
              </p>
            ))}
          {grupo.opciones.map(({ to, etiqueta, icono: Icono }) => (
            <Link
              key={to}
              to={to}
              onClick={onNavegar}
              title={compacto ? etiqueta : undefined}
              activeOptions={{ exact: RUTAS_EXACTAS.has(to) }}
              className={cn(
                "group relative flex items-center gap-3 rounded-xl py-2 text-sm font-semibold text-sidebar-foreground/80 transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring",
                compacto ? "justify-center px-0" : "px-3",
              )}
              activeProps={{
                className: "bg-sidebar-accent !text-sidebar-accent-foreground",
              }}
            >
              {({ isActive }) => (
                <>
                  <span
                    aria-hidden
                    className={cn(
                      "absolute left-0 top-1/2 h-6 w-1 -translate-y-1/2 rounded-full bg-accent transition-opacity",
                      isActive ? "opacity-100" : "opacity-0",
                    )}
                  />
                  <span
                    className={cn(
                      "flex size-9 shrink-0 items-center justify-center rounded-lg transition-colors",
                      isActive
                        ? "bg-primary text-primary-foreground shadow-card"
                        : "bg-transparent text-muted-foreground group-hover:text-sidebar-accent-foreground",
                    )}
                  >
                    <Icono className="size-5" />
                  </span>
                  <span className={cn(compacto && "sr-only")}>{etiqueta}</span>
                </>
              )}
            </Link>
          ))}
        </div>
      ))}
    </nav>
  );
}

/** Tarjeta de llamada a la acción al pie del menú. */
export function TarjetaSubir({ onNavegar }: { onNavegar?: () => void }) {
  return (
    <div className="relative overflow-hidden rounded-2xl bg-hero p-5 shadow-lift">
      <GridPattern className="text-hero-foreground/10" tamano={24} />
      <div className="relative space-y-3">
        <span className="flex size-10 items-center justify-center rounded-xl bg-accent text-accent-foreground">
          <Upload className="size-5" />
        </span>
        <p className="font-display text-base font-semibold leading-snug text-hero-foreground">
          Suma tu instrumento al acervo
        </p>
        <p className="text-sm leading-relaxed text-hero-muted">
          Estandarízalo y descubre qué KPIs educativos mide.
        </p>
        <Link
          to="/instrumentos/nuevo"
          onClick={onNavegar}
          className="inline-flex items-center gap-1.5 text-sm font-bold text-accent hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          Subir ahora <ArrowRight className="size-4" />
        </Link>
      </div>
    </div>
  );
}

export function Sidebar() {
  return (
    <aside className="sticky top-0 hidden h-screen shrink-0 flex-col border-r border-sidebar-border bg-sidebar md:flex md:w-20 lg:w-72">
      {/* Tablet: solo iconos */}
      <div className="flex h-full flex-col items-center gap-8 px-2 py-6 lg:hidden">
        <Marca compacto />
        <div className="scroll-discreto w-full flex-1 overflow-y-auto">
          <ListaNavegacion compacto />
        </div>
      </div>
      {/* Escritorio: completo */}
      <div className="hidden h-full flex-col gap-6 px-5 py-6 lg:flex">
        <Marca />
        <div className="scroll-discreto -mx-1 flex-1 overflow-y-auto px-1">
          <ListaNavegacion />
        </div>
        {/* En ventanas bajas se oculta para no esconder opciones del menú. */}
        <div className="[@media(max-height:880px)]:hidden">
          <TarjetaSubir />
        </div>
      </div>
    </aside>
  );
}
