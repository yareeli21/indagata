import { useState } from "react";
import { PageHeader } from "@/components/layout/PageHeader";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { registrarUsuario } from "@/api/usuarios";
import type { Rol } from "@/types";

export function GestionUsuariosPage() {
  const [nombre, setNombre] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rol, setRol] = useState<Rol>("Investigador");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exito, setExito] = useState<string | null>(null);

  const enviar = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setExito(null);
    setEnviando(true);
    try {
      const creado = await registrarUsuario({ nombre, email, password, rol });
      setExito(`Usuario creado: ${creado.email}`);
      setNombre("");
      setEmail("");
      setPassword("");
      setRol("Investigador");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible crear el usuario.");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="space-y-8 p-6 md:p-8">
      <PageHeader
        titulo="Gestión de usuarios"
        descripcion="Da de alta nuevos usuarios de INDAGATA. Solo disponible para administradores."
      />

      <section className="max-w-xl rounded-2xl border border-border bg-card p-6 shadow-card md:p-8">
        <form onSubmit={enviar} className="flex flex-col gap-9">
          <div className="relative">
            <input
              id="nombre"
              type="text"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              placeholder="Nombre"
              autoComplete="name"
              required
              className="w-full border-0 border-b-[1.5px] border-border bg-transparent px-0.5 pb-3 pt-1.5 text-base text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary"
            />
          </div>

          <div className="relative">
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Correo electrónico"
              autoComplete="email"
              required
              className="w-full border-0 border-b-[1.5px] border-border bg-transparent px-0.5 pb-3 pt-1.5 text-base text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary"
            />
          </div>

          <div className="relative">
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Contraseña (mínimo 6 caracteres)"
              autoComplete="new-password"
              minLength={6}
              required
              className="w-full border-0 border-b-[1.5px] border-border bg-transparent px-0.5 pb-3 pt-1.5 text-base text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary"
            />
          </div>

          <div className="flex flex-col gap-2">
            <label htmlFor="rol" className="text-sm font-medium text-foreground">
              Rol
            </label>
            <Select value={rol} onValueChange={(valor) => setRol(valor as Rol)}>
              <SelectTrigger id="rol">
                <SelectValue placeholder="Selecciona un rol" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Investigador">Investigador</SelectItem>
                <SelectItem value="Administrador">Administrador</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {error && (
            <p
              role="alert"
              className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive"
            >
              {error}
            </p>
          )}

          {exito && (
            <p
              role="status"
              className="rounded-md border border-primary/30 bg-primary/10 px-3 py-2 text-sm text-primary"
            >
              {exito}
            </p>
          )}

          <button
            type="submit"
            disabled={enviando}
            className="mt-3 rounded-xl bg-primary px-4 py-4 text-[17px] font-bold text-primary-foreground transition-[background-color,transform] hover:bg-primary/90 active:translate-y-px disabled:cursor-not-allowed disabled:opacity-60"
          >
            {enviando ? "Creando…" : "Crear usuario"}
          </button>
        </form>
      </section>
    </div>
  );
}
