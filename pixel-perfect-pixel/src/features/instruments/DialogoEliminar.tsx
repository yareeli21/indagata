import { Loader2 } from "lucide-react";
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
import { buttonVariants } from "@/components/ui/button";

interface DialogoEliminarProps {
  titulo: string | null;
  eliminando: boolean;
  onCancelar: () => void;
  onConfirmar: () => void;
}

export function DialogoEliminar({
  titulo,
  eliminando,
  onCancelar,
  onConfirmar,
}: DialogoEliminarProps) {
  return (
    <AlertDialog open={!!titulo} onOpenChange={(o) => !o && !eliminando && onCancelar()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>¿Eliminar «{titulo}»?</AlertDialogTitle>
          <AlertDialogDescription>
            Se borrará el instrumento y también todo lo asociado: el archivo original, la versión
            limpia, sus metadatos, el JSON estandarizado y los KPIs vinculados. Esta acción no se
            puede deshacer.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={eliminando}>Cancelar</AlertDialogCancel>
          <AlertDialogAction
            disabled={eliminando}
            className={buttonVariants({ variant: "destructive" })}
            onClick={(e) => {
              e.preventDefault();
              onConfirmar();
            }}
          >
            {eliminando && <Loader2 className="animate-spin" />} Eliminar
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
