import { useState } from "react";
import { Check, ChevronDown, FolderPlus } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useResearch } from "@/features/research/ResearchContext";

export function ResearchSelector() {
  const { investigaciones, activa, seleccionar, crear } = useResearch();
  const [abierto, setAbierto] = useState(false);
  const [nombre, setNombre] = useState("");

  const guardar = async () => {
    if (!nombre.trim()) return;
    await crear(nombre.trim());
    setNombre("");
    setAbierto(false);
  };

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            className="flex items-center gap-2 rounded-full border border-border bg-card px-3.5 py-1.5 text-sm font-medium text-foreground shadow-card transition-colors hover:bg-secondary"
          >
            <span className="h-2 w-2 rounded-full bg-primary" aria-hidden />
            {activa ? activa.nombre : "Sin investigación activa"}
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-64">
          <DropdownMenuLabel>Investigación activa</DropdownMenuLabel>
          <DropdownMenuSeparator />
          {investigaciones.map((inv) => (
            <DropdownMenuItem key={inv.id} onSelect={() => seleccionar(inv.id)}>
              <Check className={`h-4 w-4 ${activa?.id === inv.id ? "opacity-100" : "opacity-0"}`} />
              <span className="truncate">{inv.nombre}</span>
            </DropdownMenuItem>
          ))}
          <DropdownMenuSeparator />
          <DropdownMenuItem onSelect={() => setAbierto(true)}>
            <FolderPlus className="h-4 w-4" />
            Crear investigación
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog open={abierto} onOpenChange={setAbierto}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nueva investigación</DialogTitle>
            <DialogDescription>
              Agrupa instrumentos y consultas bajo un mismo proyecto.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="nombre-investigacion">Nombre</Label>
            <Input
              id="nombre-investigacion"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              placeholder="Ej. Trayectorias académicas en licenciatura"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAbierto(false)}>
              Cancelar
            </Button>
            <Button onClick={guardar}>Crear</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
