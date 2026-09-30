import { useEffect, useMemo, useState } from "react";
import { Link } from "@tanstack/react-router";
import { FileUp, Loader2, SearchX, Upload } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { descargarInstrumento, eliminarInstrumento, getCatalogoKpis, getInstrumentos, getInvestigadores } from "@/api/instrumentos";
import { useAuth } from "@/features/auth/AuthContext";
import type { Instrumento, Investigador } from "@/types";
import { FiltrosPanel } from "./FiltrosPanel";
import { ChipsFiltros } from "./ChipsFiltros";
import { TablaInstrumentos } from "./TablaInstrumentos";
import { VistaRapida } from "./VistaRapida";
import { DialogoEliminar } from "./DialogoEliminar";
import { EstadoVacio } from "./EstadoVacio";
import { FILTROS_VACIOS, aplicarFiltros, type Filtros } from "./filtros";

type Vista = "mios" | "todos";

export function InstrumentosPage() {
  const { usuario } = useAuth();
  const miId = usuario?.investigadorId ?? "";
  const [vista, setVista] = useState<Vista>(usuario?.rol === "Administrador" ? "todos" : "mios");
  const [lista, setLista] = useState<Instrumento[] | null>(null);
  const [investigadores, setInvestigadores] = useState<Investigador[]>([]);
  const [catalogo, setCatalogo] = useState<string[]>([]);
  const [filtros, setFiltros] = useState<Filtros>(FILTROS_VACIOS);
  const [seleccionado, setSeleccionado] = useState<Instrumento | null>(null);
  const [aEliminar, setAEliminar] = useState<Instrumento | null>(null);
  const [eliminando, setEliminando] = useState(false);

  useEffect(() => {
    Promise.all([getInstrumentos(), getInvestigadores(), getCatalogoKpis()]).then(([i, inv, k]) => {
      setLista(i); setInvestigadores(inv); setCatalogo(k);
    });
  }, []);

  const base = useMemo(() => (lista ?? []).filter((i) => vista === "todos" || i.autorId === miId), [lista, vista, miId]);
  const resultados = useMemo(() => aplicarFiltros(base, filtros), [base, filtros]);
  const nombreAutor = (id: string) => investigadores.find((x) => x.id === id)?.nombre ?? "—";

  async function confirmarEliminar() {
    if (!aEliminar) return;
    setEliminando(true);
    await eliminarInstrumento(aEliminar.id);
    setLista((l) => (l ?? []).filter((i) => i.id !== aEliminar.id));
    toast.success(`Se eliminó el instrumento «${aEliminar.titulo}»`);
    setEliminando(false);
    setAEliminar(null);
    setSeleccionado(null);
  }

  let contenido: React.ReactNode;
  if (!lista) {
    contenido = <div className="flex items-center justify-center gap-2 py-16 text-muted-foreground"><Loader2 className="size-5 animate-spin" /> Cargando instrumentos…</div>;
  } else if (vista === "mios" && base.length === 0) {
    contenido = (
      <EstadoVacio icono={FileUp} titulo="Aún no has subido instrumentos"
        descripcion="Sube tu primera encuesta, entrevista o prueba para empezar a construir tu acervo."
        accion={<Button asChild><Link to="/instrumentos/nuevo"><Upload /> Subir instrumento</Link></Button>} />
    );
  } else if (resultados.length === 0) {
    contenido = (
      <EstadoVacio icono={SearchX} titulo="No hay instrumentos con estos filtros"
        descripcion="Prueba quitando algunos filtros o cambiando las palabras clave."
        accion={<Button variant="outline" onClick={() => setFiltros(FILTROS_VACIOS)}>Limpiar filtros</Button>} />
    );
  } else {
    contenido = <TablaInstrumentos instrumentos={resultados} investigadores={investigadores} miId={miId} onSeleccionar={setSeleccionado} />;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Instrumentos</h1>
          <p className="text-muted-foreground">Consulta encuestas, entrevistas y pruebas estandarizadas.</p>
        </div>
        <ToggleGroup type="single" value={vista} onValueChange={(v) => v && setVista(v as Vista)}
          className="rounded-lg border bg-card p-1">
          <ToggleGroupItem value="mios" className="px-4 data-[state=on]:bg-primary data-[state=on]:text-primary-foreground">Mis instrumentos</ToggleGroupItem>
          <ToggleGroupItem value="todos" className="px-4 data-[state=on]:bg-primary data-[state=on]:text-primary-foreground">Todos los investigadores</ToggleGroupItem>
        </ToggleGroup>
      </div>

      <div className="grid gap-6 lg:grid-cols-[16rem_1fr]">
        <FiltrosPanel filtros={filtros} catalogoKpis={catalogo} onChange={setFiltros} />
        <div className="min-w-0 space-y-4">
          <ChipsFiltros filtros={filtros} onChange={setFiltros} />
          {lista && base.length > 0 && <p className="text-sm text-muted-foreground">{resultados.length} de {base.length} instrumentos</p>}
          {contenido}
        </div>
      </div>

      <VistaRapida
        instrumento={seleccionado}
        autor={seleccionado ? nombreAutor(seleccionado.autorId) : ""}
        ajeno={!!seleccionado && seleccionado.autorId !== miId}
        onCerrar={() => setSeleccionado(null)}
        onDescargar={(f) => seleccionado && descargarInstrumento(seleccionado.id, f)}
        onEliminar={() => setAEliminar(seleccionado)}
      />
      <DialogoEliminar titulo={aEliminar?.titulo ?? null} eliminando={eliminando}
        onCancelar={() => setAEliminar(null)} onConfirmar={confirmarEliminar} />
    </div>
  );
}
