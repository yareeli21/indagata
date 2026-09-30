import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Eye, EyeOff, LogIn } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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

/** Ilustración abstracta de nodos conectados sobre fondo azul petróleo. */
function IlustracionNodos() {
  const nodos: Array<[number, number, number]> = [
    [12, 78, 2.6],
    [28, 55, 1.8],
    [44, 70, 3.2],
    [58, 38, 2.2],
    [70, 62, 1.6],
    [82, 30, 2.8],
    [90, 55, 1.9],
    [36, 30, 1.7],
    [64, 85, 2.0],
  ];
  const aristas: Array<[number, number]> = [
    [0, 1],
    [1, 2],
    [2, 4],
    [1, 7],
    [7, 3],
    [3, 5],
    [5, 6],
    [4, 6],
    [3, 4],
    [2, 8],
    [4, 8],
    [5, 6],
  ];

  return (
    <svg
      viewBox="0 0 100 100"
      preserveAspectRatio="xMidYMid slice"
      className="pointer-events-none absolute inset-0 h-full w-full"
      aria-hidden="true"
    >
      {aristas.map(([a, b], i) => (
        <line
          key={i}
          x1={nodos[a][0]}
          y1={nodos[a][1]}
          x2={nodos[b][0]}
          y2={nodos[b][1]}
          stroke="currentColor"
          strokeWidth={0.35}
          className="text-primary-foreground/25"
        />
      ))}
      {nodos.map(([x, y, r], i) => (
        <g key={i}>
          <circle
            cx={x}
            cy={y}
            r={r * 2.4}
            className="text-primary-foreground/10"
            fill="currentColor"
          />
          <circle
            cx={x}
            cy={y}
            r={r}
            className="text-primary-foreground/45"
            fill="currentColor"
          />
        </g>
      ))}
    </svg>
  );
}

function LoginPage() {
  const { usuario, entrar } = useAuth();
  const navigate = useNavigate();
  const [nombreUsuario, setNombreUsuario] = useState("");
  const [contrasena, setContrasena] = useState("");
  const [mostrarContrasena, setMostrarContrasena] = useState(false);
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
    <div className="flex min-h-screen flex-col bg-background md:flex-row">
      {/* Mitad izquierda: marca e ilustración */}
      <aside className="relative flex flex-col justify-between overflow-hidden bg-primary p-10 text-primary-foreground md:w-1/2 md:p-14">
        <IlustracionNodos />

        <div className="relative">
          <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary-foreground text-lg font-bold text-primary">
            I
          </span>
          <p className="mt-4 text-2xl font-semibold tracking-tight">INDAGATA</p>
        </div>

        <div className="relative max-w-md">
          <h1 className="text-3xl font-semibold leading-snug tracking-tight md:text-4xl">
            Tus instrumentos de investigación, ordenados y consultables
          </h1>
          <p className="mt-4 text-sm text-primary-foreground/70">
            Instrumentos de investigación educativa en México.
          </p>
        </div>

        <p className="relative text-xs text-primary-foreground/50">
          © 2026 INDAGATA
        </p>
      </aside>

      {/* Mitad derecha: formulario */}
      <main className="flex flex-1 items-center justify-center px-6 py-12 md:w-1/2 md:px-16">
        <div className="w-full max-w-sm">
          <h2 className="text-2xl font-semibold tracking-tight text-foreground">
            Iniciar sesión
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Introduce tus credenciales para acceder a la plataforma.
          </p>

          <form onSubmit={enviar} className="mt-8 space-y-5">
            <div className="space-y-2">
              <Label htmlFor="usuario">Usuario</Label>
              <Input
                id="usuario"
                value={nombreUsuario}
                onChange={(e) => setNombreUsuario(e.target.value)}
                placeholder="Tu usuario"
                autoComplete="username"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="contrasena">Contraseña</Label>
              <div className="relative">
                <Input
                  id="contrasena"
                  type={mostrarContrasena ? "text" : "password"}
                  value={contrasena}
                  onChange={(e) => setContrasena(e.target.value)}
                  placeholder="Tu contraseña"
                  autoComplete="current-password"
                  className="pr-11"
                  required
                />
                <button
                  type="button"
                  onClick={() => setMostrarContrasena((v) => !v)}
                  aria-label={mostrarContrasena ? "Ocultar contraseña" : "Mostrar contraseña"}
                  className="absolute inset-y-0 right-0 flex w-11 items-center justify-center rounded-r-md text-muted-foreground transition-colors hover:text-foreground"
                >
                  {mostrarContrasena ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            {error && (
              <p
                role="alert"
                className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive"
              >
                {error}
              </p>
            )}

            <Button type="submit" className="w-full" disabled={enviando}>
              <LogIn className="mr-2 h-4 w-4" />
              {enviando ? "Entrando…" : "Iniciar sesión"}
            </Button>

            <p className="text-center text-xs text-muted-foreground">
              Acceso de demostración: <strong>ana</strong> (Investigador) o{" "}
              <strong>admin</strong> (Administrador), con cualquier contraseña.
            </p>
          </form>
        </div>
      </main>
    </div>
  );
}
