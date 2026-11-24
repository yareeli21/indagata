import { useState } from "react";
import { KeyRound } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { cambiarMiPassword } from "@/api/usuarios";

/** Botón del encabezado: cualquier usuario cambia su contraseña (pide la actual). */
export function CambiarPassword() {
  const [abierto, setAbierto] = useState(false);
  const [actual, setActual] = useState("");
  const [nueva, setNueva] = useState("");
  const [repetida, setRepetida] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  function cerrar(valor: boolean) {
    setAbierto(valor);
    if (!valor) {
      setActual("");
      setNueva("");
      setRepetida("");
      setError(null);
    }
  }

  async function guardar(e: React.FormEvent) {
    e.preventDefault();
    if (nueva !== repetida) {
      setError("Las contraseñas nuevas no coinciden.");
      return;
    }
    setEnviando(true);
    setError(null);
    try {
      await cambiarMiPassword(actual, nueva);
      toast.success("Contraseña actualizada.");
      cerrar(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible cambiar la contraseña.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Dialog open={abierto} onOpenChange={cerrar}>
      <DialogTrigger asChild>
        <Button variant="ghost" className="px-3 text-muted-foreground">
          <KeyRound />
          <span className="hidden xl:inline">Cambiar contraseña</span>
          <span className="sr-only xl:hidden">Cambiar contraseña</span>
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={guardar} className="space-y-4">
          <DialogHeader>
            <DialogTitle>Cambiar contraseña</DialogTitle>
            <DialogDescription>La nueva debe tener al menos 8 caracteres.</DialogDescription>
          </DialogHeader>
          <Input
            type="password"
            value={actual}
            onChange={(e) => setActual(e.target.value)}
            placeholder="Contraseña actual"
            autoComplete="current-password"
            required
          />
          <Input
            type="password"
            value={nueva}
            onChange={(e) => setNueva(e.target.value)}
            placeholder="Contraseña nueva"
            autoComplete="new-password"
            minLength={8}
            required
          />
          <Input
            type="password"
            value={repetida}
            onChange={(e) => setRepetida(e.target.value)}
            placeholder="Repite la contraseña nueva"
            autoComplete="new-password"
            minLength={8}
            required
          />
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => cerrar(false)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={enviando}>
              Guardar
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
