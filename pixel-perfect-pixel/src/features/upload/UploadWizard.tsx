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
import {
  confirmarKpis,
  getMetadatosInit,
  guardarInstrumento,
  proponerKpis,
  registrarMetadatos,
  subirInstrumento,
  type RegistroMetadatos,
} from "@/api/carga";
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
  // Ids reales que fluyen por el pipeline (§1.1 del diseño): id_crudo ≠ id_instrumento.
  const [idInstrumento, setIdInstrumento] = useState<number | null>(null);
  const [idCrudo, setIdCrudo] = useState<number | null>(null);
  // El instrumento ORIGINAL (.md, solo preguntas) y el JSON enriquecido solo existen
  // por la ruta de artefactos sembrados; en el flujo de upload puro quedan nulos.
  const [archivoOriginal, setArchivoOriginal] = useState<File | null>(null);
  const [jsonInstrumento, setJsonInstrumento] = useState<Record<string, unknown> | null>(null);
  const [avanzando, setAvanzando] = useState(false);
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

  // Pre-poblado de Dublin Core al entrar al paso de metadatos (paso === 2).
  useEffect(() => {
    if (paso !== 2 || idInstrumento == null) return;
    let cancelado = false;
    getMetadatosInit(idInstrumento)
      .then((init) => {
        if (cancelado) return;
        setDc((prev) => ({
          ...prev,
          // Solo pre-rellena el título si el sugerido es útil; NO toca `creador`
          // (el init.dc_creator es "Sistema" hardcodeado; §4.3 del diseño).
          titulo:
            prev.titulo ||
            (init.dc_title_sugerido && init.dc_title_sugerido !== "Sin título"
              ? init.dc_title_sugerido
              : prev.titulo),
          fecha: init.dc_date || prev.fecha,
          idioma: init.dc_language === "es" ? "Español" : prev.idioma,
        }));
      })
      .catch(() => {
        /* pre-poblado best-effort: si falla, el usuario captura los campos */
      });
    return () => {
      cancelado = true;
    };
  }, [paso, idInstrumento]);

  // Propuesta real de KPIs (paso === 5). Reemplaza a `getKpisSugeridos`.
  // ⚠️ Solo ejecutable con artefactos sembrados (`archivoJson` + `.md` original):
  // el upload puro NO produce el JSON enriquecido, así que en ese flujo el paso
  // queda sin fuente (sugeridos = []). TODO: no hay endpoint que devuelva el JSON
  // enriquecido tras el upload para alimentar las propuestas end-to-end.
  useEffect(() => {
    if (paso !== 5 || sugeridos || idInstrumento == null || !tipo) return;
    if (!jsonInstrumento || !archivoOriginal) {
      setSugeridos([]);
      return;
    }
    let cancelado = false;
    proponerKpis({
      idInstrumento,
      archivoJson: new Blob([JSON.stringify(jsonInstrumento)], { type: "application/json" }),
      instrumentoOriginal: archivoOriginal,
      tipo,
    })
      .then((lista) => {
        if (!cancelado) setSugeridos(lista);
      })
      .catch(() => {
        if (!cancelado) setSugeridos([]);
      });
    return () => {
      cancelado = true;
    };
  }, [paso, sugeridos, idInstrumento, tipo, jsonInstrumento, archivoOriginal]);

  const kpisAceptados = (sugeridos ?? []).filter((k) => decisiones[k.id] === "aceptado");

  const documento = useMemo(
    () => ({
      id_instrumento: idInstrumento,
      id_crudo: idCrudo,
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
    [idInstrumento, idCrudo, tipo, archivo, dc, meta, reporte, kpisAceptados],
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

  /** Avanza al siguiente paso, ejecutando la llamada real de red que corresponde. */
  async function avanzar() {
    // Paso 0 → 1: subir el instrumento. Captura ambos ids y el reporte real
    // (derivado del parseo del upload) ANTES de avanzar al paso de limpieza.
    if (paso === 0) {
      if (!archivo || !tipo) return;
      setAvanzando(true);
      try {
        const resultado = await subirInstrumento(archivo, tipo, archivoOriginal ?? undefined);
        setIdCrudo(resultado.idCrudo);
        setIdInstrumento(resultado.idInstrumento);
        setReporte(resultado.reporte);
        setPaso(1);
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "No se pudo subir el instrumento.");
      } finally {
        setAvanzando(false);
      }
      return;
    }

    // Paso 2 → 3: registrar los metadatos Dublin Core (inmutable: 2ª vez → 409).
    if (paso === 2 && idInstrumento != null) {
      setAvanzando(true);
      try {
        const metadatos: RegistroMetadatos = {
          dc_title: dc.titulo,
          dc_creator: dc.creador,
          dc_subject: dc.tema
            .split(",")
            .map((t) => t.trim())
            .filter(Boolean),
          dc_description: dc.descripcion,
        };
        if (dc.cobertura) metadatos.dc_coverage = dc.cobertura;
        if (dc.derechos) metadatos.dc_rights = dc.derechos;
        await registrarMetadatos(idInstrumento, metadatos);
        setPaso(3);
      } catch (e) {
        const status = (e as { status?: number })?.status;
        if (status === 409) {
          // Ya registrado (inmutable): se continúa sin reintentar.
          setPaso(3);
        } else {
          toast.error(e instanceof Error ? e.message : "No se pudieron registrar los metadatos.");
        }
      } finally {
        setAvanzando(false);
      }
      return;
    }

    setPaso(paso + 1);
  }

  async function guardar() {
    setGuardando(true);
    // Confirmar los KPIs aceptados enriquece el JSON y persiste el dominio de KPIs.
    // Solo se intenta si hubo propuesta real (jsonInstrumento presente).
    if (idInstrumento != null && jsonInstrumento) {
      try {
        await confirmarKpis({
          idInstrumento,
          decisiones: (sugeridos ?? []).map((k) => ({
            kpiId: Number(k.id),
            aceptado: decisiones[k.id] === "aceptado",
            score: k.coincidencia / 100,
          })),
          jsonInstrumento,
        });
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "No se pudieron confirmar los KPIs.");
      }
    }
    await guardarInstrumento(documento);
    setGuardando(false);
    setConfirmar(false);
    toast.success("Instrumento guardado", {
      action: {
        label: "Ver espacio vectorial",
        onClick: () => navigate({ to: "/espacio" }),
      },
    });
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
                setIdCrudo(null);
                setIdInstrumento(null);
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
            <Button disabled={!puedeContinuar || avanzando} onClick={avanzar}>
              {avanzando && <Loader2 className="animate-spin" />} Continuar <ArrowRight />
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
