import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import {
  AlertTriangle,
  History,
  ArrowLeft,
  ArrowRight,
  Loader2,
  Save,
  ShieldCheck,
  Upload,
} from "lucide-react";
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
  dublinCoreDesdePropuesta,
  getPropuestaDublinCore,
  getPropuestaEnriquecida,
  guardarInstrumento,
  metadatosTipoDesdePropuesta,
  previsualizarMetadatos,
  subirInstrumento,
  type ResultadoAprobacion,
  type VistaPrevia,
} from "@/api/carga";
import {
  confirmarKpisPerfil,
  generarDocumento,
  generarPerfil,
  getPerfil,
  previsualizarPerfil,
  proponerKpisPerfil,
  publicarDocumento,
} from "@/api/conocimiento";
import { useAuth } from "@/features/auth/AuthContext";
import type {
  DocumentoGenerado,
  DublinCore,
  EjecucionLimpieza,
  KpiPropuesto,
  MetadatosTipo,
  OrigenMetadato,
  PerfilGenerado,
  TipoInstrumento,
} from "@/types";
import { PageHeader } from "@/components/layout/PageHeader";
import { Pagina } from "@/components/layout/Pagina";
import { Stepper } from "./Stepper";
import {
  borrarCargaEnCurso,
  guardarCargaEnCurso,
  leerCargaEnCurso,
  type CargaEnCurso,
} from "./cargaEnCurso";
import { StepArchivo } from "./StepArchivo";
import { requiereClave } from "./archivos";
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
  const [archivoClave, setArchivoClave] = useState<File | null>(null);
  const [tipo, setTipo] = useState<TipoInstrumento | null>(null);
  // Versión vigente de la limpieza (cleaning-service); se conserva al navegar entre pasos.
  const [limpieza, setLimpieza] = useState<EjecucionLimpieza | null>(null);
  // id_crudo: id canónico (metadatos, storage, visualización). El id_instrumento
  // que usa el analysis-service llega en el resultado de la aprobación.
  const [idCrudo, setIdCrudo] = useState<number | null>(null);
  const [avanzando, setAvanzando] = useState(false);
  // Carga que quedó a medias (página cerrada en el paso «Limpieza»).
  const [pendiente, setPendiente] = useState<CargaEnCurso | null>(null);
  useEffect(() => setPendiente(leerCargaEnCurso()), []);

  function retomar(carga: CargaEnCurso) {
    reiniciarMetadatos();
    setTipo(carga.tipo);
    setIdCrudo(carga.idCrudo);
    setLimpieza(null);
    setPendiente(null);
    setPaso(1);
  }

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
  const [perfil, setPerfil] = useState<PerfilGenerado | null>(null);
  const [errorPerfil, setErrorPerfil] = useState<string | null>(null);
  const [aprobacion, setAprobacion] = useState<ResultadoAprobacion | null>(null);
  const [sugeridos, setSugeridos] = useState<KpiPropuesto[] | null>(null);
  // Versión del conocimiento a la que pertenecen las sugerencias (se confirma sobre ella).
  const [versionKpis, setVersionKpis] = useState<number | null>(null);
  const [justificaciones, setJustificaciones] = useState<Record<string, string>>({});
  // Documento final (paso «Guardar»): se genera al entrar y se publica al guardar.
  const [documento, setDocumento] = useState<DocumentoGenerado | null>(null);
  const [errorDocumento, setErrorDocumento] = useState<string | null>(null);
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

  // Propuesta de KPIs (paso 6) desde el perfil semántico aprobado (por pregunta, con evidencia).
  useEffect(() => {
    if (paso !== 5 || sugeridos || !aprobacion || idCrudo == null) return;
    let cancelado = false;
    proponerKpisPerfil(idCrudo)
      .then((propuesta) => {
        if (cancelado) return;
        setSugeridos(propuesta.kpis);
        setVersionKpis(propuesta.version);
      })
      .catch((e: unknown) => {
        if (cancelado) return;
        setSugeridos([]);
        toast.warning(mensajeDe(e, "No se pudieron proponer KPIs."));
      });
    return () => {
      cancelado = true;
    };
  }, [paso, sugeridos, aprobacion, idCrudo]);

  // Documento final (paso 7): se construye con el perfil y los KPIs ya confirmados.
  useEffect(() => {
    if (paso !== 6 || documento || errorDocumento || idCrudo == null) return;
    let cancelado = false;
    generarDocumento(idCrudo)
      .then((d) => {
        if (!cancelado) setDocumento(d);
      })
      .catch((e: unknown) => {
        if (!cancelado) setErrorDocumento(mensajeDe(e, "No se pudo generar el documento final."));
      });
    return () => {
      cancelado = true;
    };
  }, [paso, documento, errorDocumento, idCrudo]);

  const kpisAceptados = (sugeridos ?? []).filter((k) => decisiones[k.kpi_ref] === "aceptado");

  const etiquetas = useMemo(
    () => ({
      ...ETIQUETAS_DC,
      ...Object.fromEntries((tipo ? CAMPOS_POR_TIPO[tipo] : []).map((c) => [c.clave, c.etiqueta])),
    }),
    [tipo],
  );

  const puedeContinuar = [
    // La clave de una prueba en tabla es opcional: si falta, la limpieza propone una.
    !!archivo && !!tipo,
    limpieza?.estado === "confirmada",
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
    setPerfil(null);
    setErrorPerfil(null);
    setAprobacion(null);
    setSugeridos(null);
    setVersionKpis(null);
    setJustificaciones({});
    setDecisiones({});
    setDocumento(null);
    setErrorDocumento(null);
  }

  /** Avanza al siguiente paso, ejecutando la llamada de red que corresponde. */
  async function avanzar() {
    setAvanzando(true);
    try {
      if (paso === 0) {
        if (!archivo || !tipo) return;
        const resultado = await subirInstrumento(
          archivo,
          tipo,
          archivoOriginal,
          requiereClave(tipo, archivo) ? archivoClave : null,
        );
        reiniciarMetadatos();
        setIdCrudo(resultado.idCrudo);
        setLimpieza(null);
        setPendiente(null);
        guardarCargaEnCurso({ idCrudo: resultado.idCrudo, tipo, nombreArchivo: archivo.name });
        setPaso(1);
        return;
      }
      if (paso === 3 && idCrudo != null) {
        // El perfil semántico se genera en paralelo; si falla, no impide aprobar.
        const [previa, perfilPrevio] = await Promise.allSettled([
          previsualizarMetadatos(idCrudo, dc, meta),
          previsualizarPerfil(idCrudo, dc, meta),
        ]);
        if (previa.status === "rejected") throw previa.reason;
        setVistaPrevia(previa.value);
        setPerfil(perfilPrevio.status === "fulfilled" ? perfilPrevio.value : null);
        setErrorPerfil(
          perfilPrevio.status === "rejected"
            ? mensajeDe(perfilPrevio.reason, "No se pudo generar el perfil semántico.")
            : null,
        );
        setPaso(4);
        return;
      }
      if (paso === 4 && idCrudo != null) {
        const resultado = await aprobarMetadatos(idCrudo, dc, meta);
        setAprobacion(resultado);
        // Guarda el perfil con los metadatos ya aprobados (nueva versión del conocimiento).
        try {
          setPerfil(await generarPerfil(idCrudo));
        } catch (e) {
          toast.warning(mensajeDe(e, "No se pudo guardar el perfil semántico."));
        }
        setSugeridos(null);
        setVersionKpis(null);
        setJustificaciones({});
        setDecisiones({});
        setDocumento(null);
        setErrorDocumento(null);
        if (resultado.ingesta.indexado) toast.success(resultado.mensaje);
        else toast.warning(resultado.mensaje);
        setPaso(5);
        return;
      }
      if (paso === 5 && idCrudo != null && versionKpis != null && (sugeridos ?? []).length > 0) {
        // Aceptados y rechazados quedan en la versión del conocimiento; los no decididos
        // cuentan como rechazados (no se asocian).
        await confirmarKpisPerfil(
          idCrudo,
          versionKpis,
          (sugeridos ?? []).map((k) => ({
            kpi: k,
            aceptado: decisiones[k.kpi_ref] === "aceptado",
            justificacion: justificaciones[k.kpi_ref] ?? k.justificacion,
          })),
        );
      }
      if (paso === 5 && idCrudo != null) {
        // Con KPIs nuevos, el documento final se vuelve a generar al entrar a «Guardar»,
        // y el perfil se vuelve a leer: ya trae los KPIs integrados (kpis_asociados).
        setDocumento(null);
        setErrorDocumento(null);
        try {
          setPerfil(await getPerfil(idCrudo));
        } catch {
          /* el perfil anterior sigue siendo válido para mostrarse */
        }
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
      // Los KPIs ya se confirmaron al salir del paso «KPIs sugeridos».
      await guardarInstrumento(idCrudo);
      if (documento) {
        try {
          await publicarDocumento(idCrudo, documento.version);
        } catch (e) {
          toast.warning(
            mensajeDe(e, "El instrumento se guardó, pero no se pudo publicar el documento final."),
          );
        }
      }
      setConfirmar(false);
      toast.success("Instrumento guardado", {
        action: { label: "Ver espacio vectorial", onClick: () => navigate({ to: "/espacio" }) },
      });
      borrarCargaEnCurso();
      navigate({ to: "/instrumentos" });
    } catch (e) {
      toast.error(mensajeDe(e, "No se pudo guardar el instrumento."));
    } finally {
      setGuardando(false);
    }
  }

  const ingesta = aprobacion?.ingesta;

  return (
    <Pagina>
      <PageHeader
        icono={Upload}
        etiqueta="Nuevo instrumento"
        titulo="Subir instrumento"
        descripcion="Carga tu instrumento, revisa y aprueba sus metadatos, y asócialo a KPIs."
      />
      {pendiente && paso === 0 && (
        <div className="flex flex-col gap-3 rounded-2xl border border-primary/20 bg-primary-soft/60 p-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="flex items-center gap-2 text-sm text-foreground">
            <History className="size-5 shrink-0 text-primary" aria-hidden />
            <span>
              Tienes una carga sin terminar: <strong>{pendiente.nombreArchivo}</strong>. Tus
              decisiones de limpieza se guardaron.
            </span>
          </p>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              onClick={() => {
                borrarCargaEnCurso();
                setPendiente(null);
              }}
            >
              Descartar
            </Button>
            <Button onClick={() => retomar(pendiente)}>Retomar</Button>
          </div>
        </div>
      )}
      <Stepper pasos={PASOS} actual={paso} />

      <section className="superficie overflow-hidden rounded-3xl">
        <header className="border-b border-border/70 px-6 py-5 lg:px-8">
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-accent-strong">
            Paso {paso + 1} de 7
          </p>
          <h2 className="font-display text-2xl font-bold tracking-tight">{PASOS[paso]}</h2>
        </header>
        <div className="p-6 lg:p-8">
          {paso === 0 && (
            <StepArchivo
              archivo={archivo}
              tipo={tipo}
              archivoOriginal={archivoOriginal}
              onArchivo={(f) => {
                setArchivo(f);
                setLimpieza(null);
                setIdCrudo(null);
              }}
              onArchivoOriginal={setArchivoOriginal}
              archivoClave={archivoClave}
              onArchivoClave={setArchivoClave}
              onTipo={(t) => {
                setTipo(t);
                setMeta({});
              }}
            />
          )}
          {paso === 1 && idCrudo != null && (
            <StepLimpieza
              idCrudo={idCrudo}
              tipo={tipo}
              ejecucion={limpieza}
              onEjecucion={setLimpieza}
              onContinuar={() => setPaso(2)}
              onCambiarArchivo={() => setPaso(0)}
            />
          )}
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
          {paso === 4 && (
            <StepAprobacion
              vistaPrevia={vistaPrevia}
              perfil={perfil}
              errorPerfil={errorPerfil}
              etiquetas={etiquetas}
            />
          )}
          {paso === 5 && (
            <StepKpis
              sugeridos={sugeridos}
              decisiones={decisiones}
              onDecidir={(id, d) => setDecisiones((prev) => ({ ...prev, [id]: d }))}
              justificaciones={justificaciones}
              onJustificar={(id, texto) => setJustificaciones((prev) => ({ ...prev, [id]: texto }))}
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
              documento={documento}
              errorDocumento={errorDocumento}
              onReintentar={() => setErrorDocumento(null)}
              perfil={perfil}
            />
          )}
        </div>
        <footer className="flex justify-between gap-3 border-t border-border/70 bg-primary-soft/40 px-6 py-5 lg:px-8">
          <Button
            variant="outline"
            disabled={paso === 0 || avanzando}
            onClick={() => setPaso(paso - 1)}
          >
            <ArrowLeft /> Atrás
          </Button>
          {paso === 1 ? null : paso < 6 ? (
            // El paso «Limpieza» tiene sus propios botones (confirmar, continuar a metadatos).
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
            <Button disabled={!documento && !errorDocumento} onClick={() => setConfirmar(true)}>
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
    </Pagina>
  );
}
