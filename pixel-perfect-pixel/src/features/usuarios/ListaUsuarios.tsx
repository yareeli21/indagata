import { useState } from "react";
import { KeyRound, Pencil, Power, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  actualizarUsuario,
  eliminarUsuario,
  restablecerPassword,
  type UsuarioAdmin,
} from "@/api/usuarios";
import type { Rol } from "@/types";

interface ListaUsuariosProps {
  usuarios: UsuarioAdmin[];
  miId: string;
  onCambio: () => void;
}

type Accion =
  | { tipo: "editar"; usuario: UsuarioAdmin }
  | { tipo: "password"; usuario: UsuarioAdmin }
  | { tipo: "activar"; usuario: UsuarioAdmin }
  | { tipo: "eliminar"; usuario: UsuarioAdmin };

const rolUI = (rol: string): Rol => (rol === "administrador" ? "Administrador" : "Investigador");

/** Tabla de usuarios con editar, restablecer contraseña, desactivar/reactivar y eliminar. */
export function ListaUsuarios({ usuarios, miId, onCambio }: ListaUsuariosProps) {
  const [accion, setAccion] = useState<Accion | null>(null);
  const [nombre, setNombre] = useState("");
  const [rol, setRol] = useState<Rol>("Investigador");
  const [password, setPassword] = useState("");
  const [enviando, setEnviando] = useState(false);

  function abrir(a: Accion) {
    setAccion(a);
    setNombre(a.usuario.nombre);
    setRol(rolUI(a.usuario.rol));
    setPassword("");
  }

  async function ejecutar(tarea: () => Promise<unknown>, mensaje: string) {
    setEnviando(true);
    try {
      await tarea();
      toast.success(mensaje);
      setAccion(null);
      onCambio();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "No se pudo completar la acción.");
    } finally {
      setEnviando(false);
    }
  }

  const u = accion?.usuario;

  return (
    <>
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nombre</TableHead>
              <TableHead>Correo</TableHead>
              <TableHead>Rol</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead className="text-right">Instrumentos</TableHead>
              <TableHead className="text-right">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {usuarios.map((x) => {
              const yo = String(x.usuario_id) === miId;
              return (
                <TableRow key={x.usuario_id} className={x.activo ? "" : "opacity-60"}>
                  <TableCell className="font-medium">
                    {x.nombre}
                    {yo && <span className="ml-2 text-xs text-muted-foreground">(tú)</span>}
                  </TableCell>
                  <TableCell>{x.email}</TableCell>
                  <TableCell>{rolUI(x.rol)}</TableCell>
                  <TableCell>
                    {!x.activo ? "Desactivada" : x.bloqueado ? "Bloqueada (intentos)" : "Activa"}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{x.instrumentos}</TableCell>
                  <TableCell>
                    <div className="flex justify-end gap-1">
                      <Button
                        size="icon"
                        variant="ghost"
                        aria-label={`Editar a ${x.nombre}`}
                        title="Editar"
                        onClick={() => abrir({ tipo: "editar", usuario: x })}
                      >
                        <Pencil className="size-4" />
                      </Button>
                      <Button
                        size="icon"
                        variant="ghost"
                        aria-label={`Restablecer la contraseña de ${x.nombre}`}
                        title="Restablecer contraseña"
                        onClick={() => abrir({ tipo: "password", usuario: x })}
                      >
                        <KeyRound className="size-4" />
                      </Button>
                      <Button
                        size="icon"
                        variant="ghost"
                        disabled={yo}
                        aria-label={`${x.activo ? "Desactivar" : "Reactivar"} a ${x.nombre}`}
                        title={x.activo ? "Desactivar" : "Reactivar"}
                        onClick={() => abrir({ tipo: "activar", usuario: x })}
                      >
                        <Power className="size-4" />
                      </Button>
                      <Button
                        size="icon"
                        variant="ghost"
                        disabled={yo || x.instrumentos > 0}
                        aria-label={`Eliminar a ${x.nombre}`}
                        title={
                          x.instrumentos > 0
                            ? "Tiene instrumentos: desactívala en lugar de eliminarla"
                            : "Eliminar"
                        }
                        onClick={() => abrir({ tipo: "eliminar", usuario: x })}
                      >
                        <Trash2 className="size-4 text-destructive" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      {/* Editar nombre y rol */}
      <Dialog
        open={accion?.tipo === "editar"}
        onOpenChange={(abierto) => !abierto && setAccion(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Editar usuario</DialogTitle>
            <DialogDescription>{u?.email}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <Input
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              placeholder="Nombre"
            />
            <Select value={rol} onValueChange={(v) => setRol(v as Rol)}>
              <SelectTrigger aria-label="Rol">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Investigador">Investigador</SelectItem>
                <SelectItem value="Administrador">Administrador</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setAccion(null)}>
              Cancelar
            </Button>
            <Button
              disabled={enviando || !nombre.trim()}
              onClick={() =>
                u &&
                void ejecutar(
                  () => actualizarUsuario(u.usuario_id, { nombre: nombre.trim(), rol }),
                  "Usuario actualizado.",
                )
              }
            >
              Guardar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Restablecer contraseña */}
      <Dialog
        open={accion?.tipo === "password"}
        onOpenChange={(abierto) => !abierto && setAccion(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Restablecer contraseña</DialogTitle>
            <DialogDescription>
              Escribe una contraseña nueva para {u?.nombre}. Compártela por un medio seguro y pídele
              que la cambie en «Cambiar contraseña». También quita un bloqueo por intentos.
            </DialogDescription>
          </DialogHeader>
          <Input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Contraseña nueva (mínimo 8 caracteres)"
            autoComplete="new-password"
          />
          <DialogFooter>
            <Button variant="ghost" onClick={() => setAccion(null)}>
              Cancelar
            </Button>
            <Button
              disabled={enviando || password.length < 8}
              onClick={() =>
                u &&
                void ejecutar(
                  () => restablecerPassword(u.usuario_id, password),
                  "Contraseña restablecida.",
                )
              }
            >
              Restablecer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Desactivar / reactivar */}
      <AlertDialog
        open={accion?.tipo === "activar"}
        onOpenChange={(abierto) => !abierto && setAccion(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {u?.activo ? "¿Desactivar la cuenta?" : "¿Reactivar la cuenta?"}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {u?.activo
                ? `${u?.nombre} ya no podrá iniciar sesión. Sus instrumentos e investigaciones se conservan y puedes reactivarla cuando quieras.`
                : `${u?.nombre} podrá volver a iniciar sesión con su contraseña.`}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              disabled={enviando}
              onClick={(e) => {
                e.preventDefault();
                if (u)
                  void ejecutar(
                    () => actualizarUsuario(u.usuario_id, { activo: !u.activo }),
                    u.activo ? "Cuenta desactivada." : "Cuenta reactivada.",
                  );
              }}
            >
              {u?.activo ? "Desactivar" : "Reactivar"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Eliminar */}
      <AlertDialog
        open={accion?.tipo === "eliminar"}
        onOpenChange={(abierto) => !abierto && setAccion(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Eliminar la cuenta?</AlertDialogTitle>
            <AlertDialogDescription>
              Se borrará la cuenta de {u?.nombre} ({u?.email}). Esta acción no se puede deshacer.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              disabled={enviando}
              onClick={(e) => {
                e.preventDefault();
                if (u) void ejecutar(() => eliminarUsuario(u.usuario_id), "Cuenta eliminada.");
              }}
            >
              Eliminar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
