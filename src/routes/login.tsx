import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
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
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center text-center">
          <span className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-lg font-bold text-primary-foreground">
            I
          </span>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">INDAGATA</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Instrumentos de investigación educativa en México.
          </p>
        </div>

        <form
          onSubmit={enviar}
          className="space-y-5 rounded-2xl border border-border bg-card p-6 shadow-soft"
        >
          <div className="space-y-2">
            <Label htmlFor="usuario">Usuario</Label>
            <Input
              id="usuario"
              value={nombreUsuario}
              onChange={(e) => setNombreUsuario(e.target.value)}
              placeholder="ana o admin"
              autoComplete="username"
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="contrasena">Contraseña</Label>
            <Input
              id="contrasena"
              type="password"
              value={contrasena}
              onChange={(e) => setContrasena(e.target.value)}
              placeholder="Cualquier contraseña"
              autoComplete="current-password"
              required
            />
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <Button type="submit" className="w-full" disabled={enviando}>
            {enviando ? "Entrando…" : "Entrar"}
          </Button>

          <p className="text-center text-xs text-muted-foreground">
            Acceso de demostración: <strong>ana</strong> (Investigador) o{" "}
            <strong>admin</strong> (Administrador).
          </p>
        </form>
      </div>
    </div>
  );
}
