import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useAuth } from "@/features/auth/AuthContext";

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [
      { title: "Iniciar sesión — INDAGATA" },
      {
        name: "description",
        content:
          "Accede a INDAGATA, la plataforma de instrumentos de investigación educativa en México.",
      },
      { property: "og:title", content: "Iniciar sesión — INDAGATA" },
      {
        property: "og:description",
        content: "Plataforma de instrumentos de investigación educativa en México.",
      },
    ],
  }),
  component: LoginPage,
});

function LoginPage() {
  const { usuario, entrar } = useAuth();
  const navigate = useNavigate();
  const [nombreUsuario, setNombreUsuario] = useState("");
  const [contrasena, setContrasena] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    if (usuario) navigate({ to: "/instrumentos" });
  }, [usuario, navigate]);

  const enviar = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      await entrar(nombreUsuario, contrasena);
      navigate({ to: "/instrumentos" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible iniciar sesión.");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-7 bg-muted px-5 py-12">
      {/* Tarjeta partida: visual + formulario */}
      <main className="flex w-full max-w-[1000px] min-h-[620px] flex-col overflow-hidden rounded-4xl bg-card shadow-elevated md:flex-row">
        {/* Lado visual: imagen de la biblioteca con etiqueta WELCOME */}
        <section className="relative min-h-[220px] flex-1 bg-primary md:basis-[46%]">
          <img src="/biblioteca.jpg" alt="Biblioteca" className="h-full w-full object-cover" />
          <span className="absolute bottom-[40%] left-10 font-display text-3xl tracking-[0.6em] text-accent-soft [text-shadow:0_2px_12px_rgba(0,0,0,0.45)]">
            WELCOME
          </span>
        </section>

        {/* Lado formulario */}
        <section className="flex flex-1 flex-col justify-center px-8 py-12 md:basis-[54%] md:px-[72px] md:py-16">
          <h1 className="mb-12 text-center font-display text-4xl font-semibold text-foreground">
            Iniciar sesión
          </h1>

          <form onSubmit={enviar} className="flex flex-col gap-9">
            <div className="relative">
              <input
                id="usuario"
                type="email"
                value={nombreUsuario}
                onChange={(e) => setNombreUsuario(e.target.value)}
                placeholder="Correo electrónico"
                autoComplete="username"
                required
                className="w-full border-0 border-b-[1.5px] border-border bg-transparent px-0.5 pb-3 pt-1.5 text-base text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary"
              />
            </div>

            <div className="flex items-end">
              <input
                id="contrasena"
                type="password"
                value={contrasena}
                onChange={(e) => setContrasena(e.target.value)}
                placeholder="Contraseña"
                autoComplete="current-password"
                required
                className="flex-1 border-0 border-b-[1.5px] border-border bg-transparent px-0.5 pb-3 pt-1.5 text-base text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary"
              />
              <a
                href="#"
                className="ml-4 shrink-0 whitespace-nowrap pb-3 text-[13px] text-primary hover:underline"
              >
                ¿Olvidaste tu contraseña?
              </a>
            </div>

            {error && (
              <p
                role="alert"
                className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive"
              >
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={enviando}
              className="mt-3 rounded-xl bg-primary px-4 py-4 text-[17px] font-bold text-primary-foreground transition-[background-color,transform] hover:bg-primary/90 active:translate-y-px disabled:cursor-not-allowed disabled:opacity-60"
            >
              {enviando ? "Entrando…" : "Iniciar sesión"}
            </button>

            <p className="mt-6 text-center text-sm text-foreground">
              ¿No tienes una cuenta?{" "}
              <a href="#" className="font-bold text-primary hover:underline">
                Regístrate
              </a>
            </p>

            <p className="text-center text-xs text-muted-foreground">
              Acceso de demostración: <strong>admin@indagata.local</strong> (Administrador) o{" "}
              <strong>investigador@indagata.local</strong> (Investigador).
            </p>
          </form>
        </section>
      </main>
    </div>
  );
}
