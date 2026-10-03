import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { AlertTriangle, ArrowLeft, ArrowRight, Loader2, Save } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
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
import { getKpisSugeridos, guardarInstrumento, limpiarArchivo } from "@/api/carga";
import { useAuth } from "@/features/auth/AuthContext";
import type {
  DublinCore,
  KpiSugerido,
  MetadatosTipo,
  ReporteLimpieza,
  TipoInstrumento,
} from "@/types";
import { PageHeader } from "@/components/layout/PageHeader";
import { Stepper } from "./Stepper";
import { StepArchivo } from "./StepArchivo";
import { StepLimpieza } from "./StepLimpieza";
import { StepDublinCore } from "./StepDublinCore";
import { StepMetadatosTipo } from "./StepMetadatosTipo";
import { JsonPreview } from "./JsonPreview";
import { StepKpis, type DecisionKpi } from "./StepKpis";
import { StepGuardar } from "./StepGuardar";

const PASOS = [
  "Archivo",
  "Limpieza",
  "Dublin Core",
  "Metadatos del tipo",
  "Vista previa JSON",
  "KPIs sugeridos",
  "Guardar",
];

export function UploadWizard() {
  const { usuario } = useAuth();
  const navigate = useNavigate();
  const [paso, setPaso] = useState(0);
  const [archivo, setArchivo] = useState<File | null>(null);
  const [tipo, setTipo] = useState<TipoInstrumento | null>(null);
  const [reporte, setReporte] = useState<ReporteLimpieza | null>(null);
  const [dc, setDc] = useState<DublinCore>({
    titulo: "",
    creador: usuario?.nombre ?? "",
    tema: "",
    descripcion: "",
    fecha: new Date().toISOString().slice(0, 10),
    idioma: "Español",
    derechos: "",
    cobertura: "",
  });
  const [meta, setMeta] = useState<MetadatosTipo>({});
  const [sugeridos, setSugeridos] = useState<KpiSugerido[] | null>(null);
  const [decisiones, setDecisiones] = useState<Record<string, DecisionKpi>>({});
  const [confirmar, setConfirmar] = useState(false);
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    if (paso === 1 && archivo && !reporte) limpiarArchivo(archivo).then(setReporte);
    if (paso === 5 && !sugeridos) getKpisSugeridos(dc.descripcion).then(setSugeridos);
  }, [paso, archivo, reporte, sugeridos, dc.descripcion]);

  const kpisAceptados = (sugeridos ?? []).filter((k) => decisiones[k.id] === "aceptado");

  const documento = useMemo(
    () => ({
      tipo,
      archivo: archivo?.name ?? null,
      dublin_core: { ...dc },
      metadatos_tipo: Object.fromEntries(
        Object.entries(meta).map(([k, v]) => [k, v !== "" && !isNaN(Number(v)) ? Number(v) : v]),
      ),
      limpieza: reporte && {
        duplicados_eliminados: reporte.duplicadosEliminados,
        nulos_tratados: reporte.nulosTratados,
        columnas_normalizadas: reporte.columnasNormalizadas,
      },
      kpis: kpisAceptados.map((k) => k.nombre),
    }),
    [tipo, archivo, dc, meta, reporte, kpisAceptados],
  );

  const puedeContinuar = [
    !!archivo && !!tipo,
    !!reporte,
    !!dc.titulo.trim() && !!dc.creador.trim() && !!dc.descripcion.trim() && !!dc.cobertura,
    true,
    true,
    !!sugeridos,
    true,
  ][paso];

  async function guardar() {
    setGuardando(true);
    await guardarInstrumento(documento);
    setGuardando(false);
    setConfirmar(false);
    toast.success("Instrumento guardado");
    navigate({ to: "/instrumentos" });
  }

  return (
    <div className="mx-auto max-w-4xl space-y-8 p-6 md:p-8">
      <PageHeader
        titulo="Subir instrumento"
        descripcion="Carga, limpia y estandariza tu instrumento en 7 pasos."
      />
      <Stepper pasos={PASOS} actual={paso} />

      <section className="overflow-hidden rounded-3xl border border-border bg-card shadow-card">
        <header className="border-b border-border px-6 py-4">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Paso {paso + 1} de 7
          </p>
          <h2 className="font-display text-lg font-semibold">{PASOS[paso]}</h2>
        </header>
        <div className="p-6">
          {paso === 0 && (
            <StepArchivo
              archivo={archivo}
              tipo={tipo}
              onArchivo={(f) => {
                setArchivo(f);
                setReporte(null);
              }}
              onTipo={(t) => {
                setTipo(t);
                setMeta({});
              }}
            />
          )}
          {paso === 1 && <StepLimpieza reporte={reporte} />}
          {paso === 2 && <StepDublinCore valor={dc} onChange={setDc} />}
          {paso === 3 && tipo && <StepMetadatosTipo tipo={tipo} valor={meta} onChange={setMeta} />}
          {paso === 4 && <JsonPreview datos={documento} />}
          {paso === 5 && (
            <StepKpis
              sugeridos={sugeridos}
              decisiones={decisiones}
              onDecidir={(id, d) => setDecisiones({ ...decisiones, [id]: d })}
            />
          )}
          {paso === 6 && (
            <StepGuardar
              resumen={[
                { etiqueta: "Archivo", valor: archivo?.name ?? "" },
                { etiqueta: "Tipo", valor: tipo ?? "" },
                { etiqueta: "Título", valor: dc.titulo },
                { etiqueta: "Creador", valor: dc.creador },
                { etiqueta: "Nivel educativo", valor: dc.cobertura },
                { etiqueta: "Fecha", valor: dc.fecha },
                {
                  etiqueta: "Registros limpiados",
                  valor: reporte
                    ? `${reporte.duplicadosEliminados} duplicados · ${reporte.nulosTratados} nulos`
                    : "",
                },
                {
                  etiqueta: "KPIs aceptados",
                  valor: kpisAceptados.map((k) => k.nombre).join(", "),
                },
              ]}
            />
          )}
        </div>
        <footer className="flex justify-between border-t border-border bg-muted/30 px-6 py-4">
          <Button variant="outline" disabled={paso === 0} onClick={() => setPaso(paso - 1)}>
            <ArrowLeft /> Atrás
          </Button>
          {paso < 6 ? (
            <Button disabled={!puedeContinuar} onClick={() => setPaso(paso + 1)}>
              Continuar <ArrowRight />
            </Button>
          ) : (
            <Button onClick={() => setConfirmar(true)}>
              <Save /> Guardar instrumento
            </Button>
          )}
        </footer>
      </section>

      <AlertDialog open={confirmar} onOpenChange={setConfirmar}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Guardar instrumento?</AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="flex gap-3 rounded-lg bg-accent-soft p-3 text-accent-foreground">
                <AlertTriangle className="size-5 shrink-0" />
                <span>Una vez guardado no podrás modificarlo; solo eliminarlo.</span>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={guardando}>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              disabled={guardando}
              onClick={(e) => {
                e.preventDefault();
                guardar();
              }}
            >
              {guardando && <Loader2 className="animate-spin" />} Guardar instrumento
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
