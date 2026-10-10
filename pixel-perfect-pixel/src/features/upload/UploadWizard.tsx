import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { AlertTriangle, ArrowLeft, ArrowRight, Loader2, Save, ShieldCheck } from "lucide-react";
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
  CAMPO_DC_POR_COLUMNA,
  aprobarMetadatos,
  confirmarKpis,
  dublinCoreDesdePropuesta,
  getPropuestaDublinCore,
  getPropuestaEnriquecida,
  guardarInstrumento,
  metadatosTipoDesdePropuesta,
  previsualizarMetadatos,
  proponerKpis,
  subirInstrumento,
  type ResultadoAprobacion,
  type VistaPrevia,
} from "@/api/carga";
import { useAuth } from "@/features/auth/AuthContext";
import type {
  DublinCore,
  KpiSugerido,
  MetadatosTipo,
  OrigenMetadato,
  ReporteLimpieza,
  TipoInstrumento,
} from "@/types";
import { PageHeader } from "@/components/layout/PageHeader";
import { Stepper } from "./Stepper";
import { StepArchivo } from "./StepArchivo";
import { StepLimpieza } from "./StepLimpieza";
import { StepDublinCore } from "./StepDublinCore";
import { CAMPOS_POR_TIPO, StepMetadatosTipo } from "./StepMetadatosTipo";
import { StepAprobacion } from "./StepAprobacion";
import { StepKpis, type DecisionKpi } from "./StepKpis";
import { StepGuardar } from "./StepGuardar";

const PASOS = [
  "Archivo",
  "Limpieza",
  "Dublin Core",
  "Metadatos del tipo",
  "Aprobar metadatos",
  "KPIs sugeridos",
  "Guardar",
];

/** Campos Dublin Core que el formulario exige antes de continuar. */
const DC_OBLIGATORIOS: (keyof DublinCore)[] = [
  "titulo",
  "creador",
  "tema",
  "descripcion",
  "fecha",
  "idioma",
  "cobertura",
  "editor",
  "derechos",
];

const ETIQUETAS_DC: Record<string, string> = {
  dc_title: "Título",
  dc_creator: "Creador",
  dc_subject: "Tema",
  dc_description: "Descripción",
  dc_type: "Tipo",
  dc_date: "Fecha",
  dc_language: "Idioma",
  dc_coverage: "Cobertura",
  dc_publisher: "Editor",
  dc_rights: "Derechos",
  dc_format: "Formato",
  dc_source: "Fuente",
  dc_relation: "Relación",
};

function dublinCoreInicial(creador: string): DublinCore {
  return {
    titulo: "",
    creador,
    tema: "",
    descripcion: "",
    tipo: "",
    fecha: new Date().toISOString().slice(0, 10),
    idioma: "es",
    cobertura: "",
    coberturaDetalle: "",
    editor: "",
    derechos: "",
    formato: "",
    fuente: "",
    relacion: "",
  };
}

function mensajeDe(e: unknown, defecto: string): string {
  return e instanceof Error && e.message ? e.message : defecto;
}

export function UploadWizard() {
  const { usuario } = useAuth();
  const navigate = useNavigate();
  const [paso, setPaso] = useState(0);
  const [archivo, setArchivo] = useState<File | null>(null);
  const [archivoOriginal, setArchivoOriginal] = useState<File | null>(null);
  const [tipo, setTipo] = useState<TipoInstrumento | null>(null);
  const [reporte, setReporte] = useState<ReporteLimpieza | null>(null);
  // id_crudo: id canónico (metadatos, storage, visualización). El id_instrumento
  // que usa el analysis-service llega en el resultado de la aprobación.
  const [idCrudo, setIdCrudo] = useState<number | null>(null);
  const [avanzando, setAvanzando] = useState(false);

  // Dublin Core (propuesto por el metadata-service, editable por el autor).
  const [dc, setDc] = useState<DublinCore>(() => dublinCoreInicial(usuario?.nombre ?? ""));
  const [origenDc, setOrigenDc] = useState<Partial<Record<keyof DublinCore, OrigenMetadato>>>({});
  const [notasDc, setNotasDc] = useState<string[]>([]);
  const [dcPropuestoPara, setDcPropuestoPara] = useState<number | null>(null);

  // Metadatos del tipo.
  const [meta, setMeta] = useState<MetadatosTipo>({});
  const [origenMeta, setOrigenMeta] = useState<Record<string, OrigenMetadato>>({});
  const [obligatoriosMeta, setObligatoriosMeta] = useState<string[]>([]);
  const [metaPropuestoPara, setMetaPropuestoPara] = useState<number | null>(null);

  // Aprobación y KPIs.
  const [vistaPrevia, setVistaPrevia] = useState<VistaPrevia | null>(null);
  const [aprobacion, setAprobacion] = useState<ResultadoAprobacion | null>(null);
  const [sugeridos, setSugeridos] = useState<KpiSugerido[] | null>(null);
  const [decisiones, setDecisiones] = useState<Record<string, DecisionKpi>>({});
  const [confirmar, setConfirmar] = useState(false);
  const [guardando, setGuardando] = useState(false);

  const cargandoDc = paso === 2 && idCrudo != null && dcPropuestoPara !== idCrudo;
  const cargandoMeta = paso === 3 && idCrudo != null && metaPropuestoPara !== idCrudo;

  // Propuesta de Dublin Core al entrar al paso 3 (una vez por instrumento subido).
  useEffect(() => {
    if (!cargandoDc || idCrudo == null) return;
    let cancelado = false;
    getPropuestaDublinCore(idCrudo)
      .then((p) => {
        if (cancelado) return;
        setDc((prev) => dublinCoreDesdePropuesta(p.valores, prev));
        const origen: Partial<Record<keyof DublinCore, OrigenMetadato>> = {};
        for (const [columna, valor] of Object.entries(p.origen)) {
          const campo = CAMPO_DC_POR_COLUMNA[columna];
          if (campo) origen[campo] = valor;
        }
        setOrigenDc(origen);
        setNotasDc(p.notas);
      })
      .catch((e: unknown) => {
        if (!cancelado)
          toast.error(mensajeDe(e, "No se pudo proponer el Dublin Core; captúralo a mano."));
      })
      .finally(() => {
        if (!cancelado) setDcPropuestoPara(idCrudo);
      });
    return () => {
      cancelado = true;
    };
  }, [cargandoDc, idCrudo]);

  // Propuesta de metadatos del tipo al entrar al paso 4.
  useEffect(() => {
    if (!cargandoMeta || idCrudo == null) return;
    let cancelado = false;
    getPropuestaEnriquecida(idCrudo)
      .then((p) => {
        if (cancelado) return;
        setMeta(metadatosTipoDesdePropuesta(p.valores));
        setOrigenMeta(p.origen);
        setObligatoriosMeta(p.obligatorios);
      })
      .catch((e: unknown) => {
        if (!cancelado)
          toast.error(mensajeDe(e, "No se pudieron proponer los metadatos del tipo."));
      })
      .finally(() => {
        if (!cancelado) setMetaPropuestoPara(idCrudo);
      });
    return () => {
      cancelado = true;
    };
  }, [cargandoMeta, idCrudo]);

  // Propuesta de KPIs (paso 6) sobre el JSON aprobado y el instrumento en texto.
  useEffect(() => {
    if (paso !== 5 || sugeridos || !aprobacion || !tipo) return;
    let cancelado = false;
    proponerKpis({
      idInstrumento: aprobacion.idInstrumento,
      archivoJson: new Blob([JSON.stringify(aprobacion.json)], { type: "application/json" }),
      instrumentoOriginal: new Blob([aprobacion.textoInstrumento], { type: "text/markdown" }),
      tipo,
    })
      .then((lista) => {
        if (!cancelado) setSugeridos(lista);
      })
      .catch((e: unknown) => {
        if (cancelado) return;
        setSugeridos([]);
        toast.warning(mensajeDe(e, "No se pudieron proponer KPIs."));
      });
    return () => {
      cancelado = true;
    };
  }, [paso, sugeridos, aprobacion, tipo]);

  const kpisAceptados = (sugeridos ?? []).filter((k) => decisiones[k.id] === "aceptado");

  const etiquetas = useMemo(
    () => ({
      ...ETIQUETAS_DC,
      ...Object.fromEntries((tipo ? CAMPOS_POR_TIPO[tipo] : []).map((c) => [c.clave, c.etiqueta])),
    }),
    [tipo],
  );

  const puedeContinuar = [
    !!archivo && !!tipo,
    !!reporte,
    !cargandoDc && DC_OBLIGATORIOS.every((k) => String(dc[k]).trim() !== ""),
    !cargandoMeta && obligatoriosMeta.every((k) => (meta[k] ?? "").trim() !== ""),
    !!vistaPrevia?.valido,
    !!sugeridos,
    true,
  ][paso];

  function reiniciarMetadatos() {
    setDc(dublinCoreInicial(usuario?.nombre ?? ""));
    setOrigenDc({});
    setNotasDc([]);
    setMeta({});
    setOrigenMeta({});
    setObligatoriosMeta([]);
    setVistaPrevia(null);
    setAprobacion(null);
    setSugeridos(null);
    setDecisiones({});
  }

  /** Avanza al siguiente paso, ejecutando la llamada de red que corresponde. */
  async function avanzar() {
    setAvanzando(true);
    try {
      if (paso === 0) {
        if (!archivo || !tipo) return;
        const resultado = await subirInstrumento(archivo, tipo, archivoOriginal);
        reiniciarMetadatos();
        setIdCrudo(resultado.idCrudo);
        setReporte(resultado.reporte);
        setPaso(1);
        return;
      }
      if (paso === 3 && idCrudo != null) {
        setVistaPrevia(await previsualizarMetadatos(idCrudo, dc, meta));
        setPaso(4);
        return;
      }
      if (paso === 4 && idCrudo != null) {
        const resultado = await aprobarMetadatos(idCrudo, dc, meta);
        setAprobacion(resultado);
        setSugeridos(null);
        setDecisiones({});
        if (resultado.ingesta.indexado) toast.success(resultado.mensaje);
        else toast.warning(resultado.mensaje);
        setPaso(5);
        return;
      }
      setPaso(paso + 1);
    } catch (e) {
      toast.error(mensajeDe(e, "No se pudo completar el paso."));
    } finally {
      setAvanzando(false);
    }
  }

  async function guardar() {
    if (idCrudo == null || !aprobacion) return;
    setGuardando(true);
    try {
      if ((sugeridos ?? []).length > 0) {
        try {
          await confirmarKpis({
            idInstrumento: aprobacion.idInstrumento,
            decisiones: (sugeridos ?? []).map((k) => ({
              kpiId: Number(k.id),
              aceptado: decisiones[k.id] === "aceptado",
              score: k.coincidencia / 100,
            })),
            jsonInstrumento: aprobacion.json,
          });
        } catch (e) {
          toast.error(mensajeDe(e, "No se pudieron confirmar los KPIs."));
        }
      }
      await guardarInstrumento(idCrudo);
      setConfirmar(false);
      toast.success("Instrumento guardado", {
        action: { label: "Ver espacio vectorial", onClick: () => navigate({ to: "/espacio" }) },
      });
      navigate({ to: "/instrumentos" });
    } catch (e) {
      toast.error(mensajeDe(e, "No se pudo guardar el instrumento."));
    } finally {
      setGuardando(false);
    }
  }

  const ingesta = aprobacion?.ingesta;

  return (
    <div className="mx-auto max-w-4xl space-y-8 p-6 md:p-8">
      <PageHeader
        titulo="Subir instrumento"
        descripcion="Carga tu instrumento, revisa y aprueba sus metadatos, y asócialo a KPIs."
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
              archivoOriginal={archivoOriginal}
              onArchivo={(f) => {
                setArchivo(f);
                setReporte(null);
                setIdCrudo(null);
              }}
              onArchivoOriginal={setArchivoOriginal}
              onTipo={(t) => {
                setTipo(t);
                setMeta({});
              }}
            />
          )}
          {paso === 1 && <StepLimpieza reporte={reporte} />}
          {paso === 2 && (
            <StepDublinCore
              valor={dc}
              onChange={setDc}
              origen={origenDc}
              cargando={cargandoDc}
              notas={notasDc}
            />
          )}
          {paso === 3 && tipo && (
            <StepMetadatosTipo
              tipo={tipo}
              valor={meta}
              onChange={setMeta}
              origen={origenMeta}
              obligatorios={obligatoriosMeta}
              cargando={cargandoMeta}
            />
          )}
          {paso === 4 && <StepAprobacion vistaPrevia={vistaPrevia} etiquetas={etiquetas} />}
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
                { etiqueta: "Metadatos", valor: aprobacion ? "Aprobados por ti" : "" },
                {
                  etiqueta: "RAG",
                  valor: ingesta
                    ? ingesta.indexado
                      ? `Integrado (${ingesta.chunks} fragmentos)`
                      : `Pendiente: ${ingesta.motivo ?? "se reintentará"}`
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
          <Button
            variant="outline"
            disabled={paso === 0 || avanzando}
            onClick={() => setPaso(paso - 1)}
          >
            <ArrowLeft /> Atrás
          </Button>
          {paso < 6 ? (
            <Button disabled={!puedeContinuar || avanzando} onClick={avanzar}>
              {avanzando && <Loader2 className="animate-spin" />}
              {paso === 4 ? (
                <>
                  <ShieldCheck /> Aprobar metadatos
                </>
              ) : (
                <>
                  Continuar <ArrowRight />
                </>
              )}
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
