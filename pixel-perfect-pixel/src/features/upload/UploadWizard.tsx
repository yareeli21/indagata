import { useEffect, useMemo, useRef, useState } from "react";
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
  estandarizar,
  estandarizarPreview,
  getMetadatosInit,
  guardarInstrumento,
  preguntaPreviewAConfirmada,
  proponerKpis,
  registrarMetadatos,
  registrarMetadatosEspecificos,
  subirInstrumento,
  type RegistroMetadatos,
} from "@/api/carga";
import { useAuth } from "@/features/auth/AuthContext";
import type {
  DublinCore,
  KpiSugerido,
  MetadatosTipo,
  PreguntaPreview,
  ReporteLimpieza,
  TipoInstrumento,
} from "@/types";
import { PageHeader } from "@/components/layout/PageHeader";
import { Stepper } from "./Stepper";
import { StepArchivo } from "./StepArchivo";
import { StepLimpieza } from "./StepLimpieza";
import { StepTiposPregunta } from "./StepTiposPregunta";
import { StepDublinCore } from "./StepDublinCore";
import { StepMetadatosTipo } from "./StepMetadatosTipo";
import { JsonPreview } from "./JsonPreview";
import { StepKpis, type DecisionKpi } from "./StepKpis";
import { StepCalculoKpis, type EstadoCalculoKpi, type KpiAceptado } from "./StepCalculoKpis";
import { StepGuardar } from "./StepGuardar";
import { registrarCalculo } from "@/api/carga";

const PASOS = [
  "Archivo",
  "Limpieza",
  "Tipos de pregunta",
  "Dublin Core",
  "Metadatos del tipo",
  "Vista previa JSON",
  "KPIs sugeridos",
  "Calcular KPIs",
  "Guardar",
];

const TOTAL_PASOS = PASOS.length;
const PASO_CALCULO = 7;
const PASO_GUARDAR = 8;

/**
 * Claves de `survey_specific` que `metadata_extractor` lee para el summary, por tipo
 * (espejo de `CAMPOS_ESPECIFICOS_POR_TIPO` del analysis-service; design.md §1.4bis).
 * Solo estas claves se enriquecen en el JSON antes de proponer KPIs.
 */
const CLAVES_SURVEY_POR_TIPO: Record<TipoInstrumento, string[]> = {
  Encuesta: [
    "constructo_principal",
    "dimensiones",
    "palabras_clave",
    "carrera",
    "notas_contextuales",
    "notas_interpretacion",
  ],
  Entrevista: ["objetivo", "metodologia"],
  "Prueba estandarizada": [
    "unidad_de_aprendizaje",
    "taxonomia_bloom",
    "objetivo_de_evaluacion",
    "competencias",
  ],
};

/** Claves que el backend/summary tratan como listas (texto por comas → array). */
const CLAVES_LISTA_SURVEY = new Set(["dimensiones", "palabras_clave", "competencias"]);

/**
 * Arma el `survey_specific` del tipo a partir del estado del paso 4, limitándose a
 * las claves que lee `metadata_extractor` y parseando las listas por comas.
 */
function armarSurveyEspecifico(
  tipo: TipoInstrumento,
  meta: MetadatosTipo,
): Record<string, unknown> {
  const survey: Record<string, unknown> = {};
  for (const clave of CLAVES_SURVEY_POR_TIPO[tipo]) {
    const valor = (meta[clave] ?? "").trim();
    if (valor === "") continue;
    if (CLAVES_LISTA_SURVEY.has(clave)) {
      const lista = valor
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      if (lista.length > 0) survey[clave] = lista;
    } else {
      survey[clave] = valor;
    }
  }
  return survey;
}

/**
 * Enriquecimiento INMUTABLE del JSON de dominio (design.md §1.4bis). Devuelve una
 * copia nueva escribiendo SOLO las 4 claves `dc:` que lee `metadata_extractor`
 * (`DUBLIN_CORE_KEYS`) en `metadata.dublin_core`, y fusionando `survey_specific`.
 * NO muta `base` ni el estado de React.
 */
export function enriquecerJson(
  base: Record<string, unknown>,
  dc: DublinCore,
  surveyEspecifico: Record<string, unknown>,
): Record<string, unknown> {
  const dcJson: Record<string, string> = {};
  if (dc.titulo) dcJson["dc:title"] = dc.titulo;
  if (dc.tema) dcJson["dc:subject"] = dc.tema;
  if (dc.descripcion) dcJson["dc:description"] = dc.descripcion;
  if (dc.cobertura) dcJson["dc:coverage"] = dc.cobertura;
  const metaPrev = (base.metadata as Record<string, unknown>) ?? {};
  const surveyPrev = (metaPrev.survey_specific as Record<string, unknown>) ?? {};
  return {
    ...base,
    metadata: {
      ...metaPrev,
      dublin_core: dcJson,
      survey_specific: { ...surveyPrev, ...surveyEspecifico },
    },
  };
}

/**
 * Respaldo SOLO tabular: una línea por `question.text`. Para documentos, el JSON ya
 * contiene una sola pregunta abierta con el texto completo, de modo que esto devuelve
 * ese texto íntegro (design.md §4, Hallazgo 3).
 */
function textoDerivadoDePreguntas(json: Record<string, unknown>): string {
  const instrument = json.instrument as
    { sections?: { questions?: { text?: string }[] }[] } | undefined;
  const secciones = instrument?.sections ?? [];
  return secciones
    .flatMap((s) => s.questions ?? [])
    .map((q) => q.text ?? "")
    .filter(Boolean)
    .join("\n");
}

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
  // El instrumento ORIGINAL (.md/.txt, solo preguntas) es opcional; si no hay, el
  // paso de KPIs deriva el texto del JSON (textoDerivadoDePreguntas).
  const [archivoOriginal, setArchivoOriginal] = useState<File | null>(null);
  const [jsonInstrumento, setJsonInstrumento] = useState<Record<string, unknown> | null>(null);
  const [avanzando, setAvanzando] = useState(false);
  // JSON enriquecido (DC + survey_specific) que produce el paso de KPIs. Vive en una ref
  // —no en estado— para NO re-disparar el efecto de propuesta (evita el bucle de render).
  // `guardar()` lo usa en confirmarKpis con fallback a jsonInstrumento.
  const jsonEnriquecidoRef = useRef<Record<string, unknown> | null>(null);
  // Guard: la propuesta de KPIs se dispara una sola vez por id_instrumento (paso 6).
  const propuestaDisparadaRef = useRef<number | null>(null);
  // Estandarización (paso 2): preview propuesto + tipos confirmados por el investigador.
  const [tiposDetectados, setTiposDetectados] = useState<PreguntaPreview[] | null>(null);
  const [tiposConfirmados, setTiposConfirmados] = useState<PreguntaPreview[] | null>(null);
  const [notasPreview, setNotasPreview] = useState<string[]>([]);
  const [nRespondentesDetectados, setNRespondentesDetectados] = useState<number | null>(null);
  const [dc, setDc] = useState<DublinCore>({
    titulo: "",
    creador: usuario?.nombre ?? "",
    tema: "",
    descripcion: "",
    fecha: new Date().toISOString().slice(0, 10),
    idioma: "Español",
    derechos: "",
    cobertura: "",
    fuente: "",
    relacion: "",
  });
  const [meta, setMeta] = useState<MetadatosTipo>({});
  const [sugeridos, setSugeridos] = useState<KpiSugerido[] | null>(null);
  const [decisiones, setDecisiones] = useState<Record<string, DecisionKpi>>({});
  const [confirmar, setConfirmar] = useState(false);
  const [guardando, setGuardando] = useState(false);
  // Paso 7 — cálculo real de KPIs: estado por kpi_id (variables, resultado, semáforo…).
  const [calculos, setCalculos] = useState<Record<number, EstadoCalculoKpi>>({});

  // Preview de tipos de pregunta al ENTRAR al paso 2 (estandarización).
  useEffect(() => {
    if (paso !== 2 || idCrudo == null || tiposDetectados) return;
    let cancelado = false;
    estandarizarPreview(idCrudo)
      .then((resp) => {
        if (cancelado) return;
        setTiposDetectados(resp.preguntas);
        setTiposConfirmados(resp.preguntas);
        setNotasPreview(resp.notas ?? []);
        setNRespondentesDetectados(resp.n_respondentes_detectados);
      })
      .catch((e) => {
        if (cancelado) return;
        toast.error(e instanceof Error ? e.message : "No se pudieron analizar las preguntas.");
      });
    return () => {
      cancelado = true;
    };
  }, [paso, idCrudo, tiposDetectados]);

  // Pre-rellenar `n_respondentes` (encuesta) con el valor detectado, editable (NIT #3).
  useEffect(() => {
    if (nRespondentesDetectados == null || tipo !== "Encuesta") return;
    setMeta((prev) =>
      prev.n_respondentes != null && prev.n_respondentes !== ""
        ? prev
        : { ...prev, n_respondentes: String(nRespondentesDetectados) },
    );
  }, [nRespondentesDetectados, tipo]);

  // Pre-poblado de Dublin Core al entrar al paso DC (paso === 3).
  useEffect(() => {
    if (paso !== 3 || idInstrumento == null) return;
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

  // Propuesta real de KPIs (paso === 6). Enriquece el JSON (DC + survey_specific) de
  // forma inmutable antes de proponer, y diferencia 503 (servicio caído) de lista vacía.
  useEffect(() => {
    if (paso !== 6 || idInstrumento == null || !tipo) return;
    // Guard: dispara la propuesta UNA sola vez por id_instrumento. Sin esto, el
    // enriquecimiento del JSON (objeto nuevo en cada render) realimentaba el efecto
    // y provocaba un bucle infinito de peticiones (Maximum update depth exceeded).
    if (propuestaDisparadaRef.current === idInstrumento) return;
    if (!jsonInstrumento) {
      setSugeridos([]);
      return;
    }
    propuestaDisparadaRef.current = idInstrumento;
    let cancelado = false;
    const original = archivoOriginal
      ? archivoOriginal
      : new Blob([textoDerivadoDePreguntas(jsonInstrumento)], { type: "text/markdown" });
    const surveyEspecifico = armarSurveyEspecifico(tipo, meta);
    const jsonEnriquecido = enriquecerJson(jsonInstrumento, dc, surveyEspecifico);
    jsonEnriquecidoRef.current = jsonEnriquecido; // para confirmarKpis (paso 8), sin re-render
    const archivoJson = new Blob([JSON.stringify(jsonEnriquecido)], { type: "application/json" });

    proponerKpis({ idInstrumento, archivoJson, instrumentoOriginal: original, tipo })
      .then((lista) => {
        if (!cancelado) setSugeridos(lista);
      })
      .catch((e) => {
        if (cancelado) return;
        // Permite reintentar en una nueva entrada al paso si la propuesta falló.
        propuestaDisparadaRef.current = null;
        const status = (e as { status?: number })?.status;
        if (status === 503) {
          toast.error(
            "El servicio de vectorización no está disponible. Verifica que Chroma y Ollama " +
              "estén arriba y que la colección de KPIs esté reindexada " +
              "(POST /vectorizacion/kpis/reindex).",
          );
        } else {
          toast.error(e instanceof Error ? e.message : "No se pudieron proponer KPIs.");
        }
        setSugeridos([]); // lista vacía SOLO como estado terminal tras surfacar el error
      });
    return () => {
      cancelado = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paso, idInstrumento, tipo]);

  const kpisAceptados = (sugeridos ?? []).filter((k) => decisiones[k.id] === "aceptado");

  // KPIs confirmados que entran al paso de cálculo (id numérico + nombre).
  const kpisParaCalcular: KpiAceptado[] = kpisAceptados.map((k) => ({
    id: Number(k.id),
    nombre: k.nombre,
  }));

  /** El paso de cálculo está completo cuando cada KPI calculable fue resuelto u omitido. */
  function calculoCompleto(): boolean {
    return kpisParaCalcular.every((kpi) => {
      const estado = calculos[kpi.id];
      if (!estado || estado.omitido) return true;
      const prep = estado.preparado;
      if (!prep) return false; // aún preparando
      const noCalculable = prep.tipo === "descriptivo" || prep.variables.length === 0;
      if (noCalculable) return true;
      // Calculable: requiere resultado y referencia capturados.
      return estado.resultado != null && estado.referencia.trim() !== "";
    });
  }

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
    !!jsonInstrumento || !!tiposConfirmados,
    !!dc.titulo.trim() && !!dc.creador.trim() && !!dc.descripcion.trim() && !!dc.cobertura,
    true,
    true,
    !!sugeridos,
    calculoCompleto(),
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

    // Paso 2 → 3: estandarizar con los tipos confirmados. Persiste el JSON de dominio,
    // setea ruta_json y guarda el json_instrumento para alimentar la propuesta de KPIs.
    if (paso === 2 && idCrudo != null) {
      if (!tiposConfirmados) return;
      setAvanzando(true);
      try {
        const preguntas = tiposConfirmados.map(preguntaPreviewAConfirmada);
        const resp = await estandarizar(idCrudo, preguntas);
        setJsonInstrumento(resp.json_instrumento);
        setPaso(3);
      } catch (e) {
        const status = (e as { status?: number })?.status;
        if (status === 409) {
          toast.error("El instrumento ya fue vectorizado; no puede reestandarizarse.");
        } else {
          toast.error(e instanceof Error ? e.message : "No se pudo estandarizar el instrumento.");
        }
      } finally {
        setAvanzando(false);
      }
      return;
    }

    // Paso 3 → 4: registrar los metadatos Dublin Core (inmutable: 2ª vez → 409).
    if (paso === 3 && idInstrumento != null) {
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
        if (dc.fuente) metadatos.dc_source = dc.fuente;
        if (dc.relacion) metadatos.dc_relation = dc.relacion;
        await registrarMetadatos(idInstrumento, metadatos);
        setPaso(4);
      } catch (e) {
        const status = (e as { status?: number })?.status;
        if (status === 409) {
          // Ya registrado (inmutable): se continúa sin reintentar.
          setPaso(4);
        } else {
          toast.error(e instanceof Error ? e.message : "No se pudieron registrar los metadatos.");
        }
      } finally {
        setAvanzando(false);
      }
      return;
    }

    // Paso 4 → 5: registrar los metadatos específicos del tipo (UPSERT).
    if (paso === 4 && idInstrumento != null && tipo) {
      setAvanzando(true);
      try {
        await registrarMetadatosEspecificos(idInstrumento, tipo, meta);
        setPaso(5);
      } catch (e) {
        const status = (e as { status?: number })?.status;
        if (status === 409) {
          toast.error("El tipo no coincide con el instrumento.");
        } else {
          toast.error(
            e instanceof Error ? e.message : "No se pudieron registrar los metadatos del tipo.",
          );
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
    // Usa el JSON ENRIQUECIDO que calculó el paso 6 (ref); si no existe, cae al base.
    const jsonParaConfirmar = jsonEnriquecidoRef.current ?? jsonInstrumento;
    if (idInstrumento != null && jsonParaConfirmar) {
      try {
        await confirmarKpis({
          idInstrumento,
          decisiones: (sugeridos ?? []).map((k) => ({
            kpiId: Number(k.id),
            aceptado: decisiones[k.id] === "aceptado",
            score: k.coincidencia / 100,
          })),
          jsonInstrumento: jsonParaConfirmar,
        });
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "No se pudieron confirmar los KPIs.");
      }
    }
    // Registra el cálculo real de cada KPI resuelto (no omitido, con resultado y referencia).
    if (idInstrumento != null) {
      for (const kpi of kpisParaCalcular) {
        const estado = calculos[kpi.id];
        if (
          !estado ||
          estado.omitido ||
          estado.resultado == null ||
          estado.referencia.trim() === ""
        ) {
          continue;
        }
        const prep = estado.preparado;
        if (!prep || prep.tipo === "descriptivo" || prep.variables.length === 0) continue;
        const variablesInput: Record<string, number> = {};
        for (const v of prep.variables) {
          variablesInput[v.clave] = Number(estado.valores[v.clave]);
        }
        try {
          await registrarCalculo({
            id_instrumento: idInstrumento,
            kpi_id: kpi.id,
            variables_input: variablesInput,
            resultado_valor: estado.resultado,
            resultado_unidad: estado.unidad,
            referencia_valor: Number(estado.referencia),
            referencia_contexto: prep.descripcion_direccional,
          });
        } catch (e) {
          toast.error(
            e instanceof Error ? e.message : `No se pudo registrar el cálculo de ${kpi.nombre}.`,
          );
        }
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
        descripcion={`Carga, limpia y estandariza tu instrumento en ${TOTAL_PASOS} pasos.`}
      />
      <Stepper pasos={PASOS} actual={paso} />

      <section className="overflow-hidden rounded-3xl border border-border bg-card shadow-card">
        <header className="border-b border-border px-6 py-4">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Paso {paso + 1} de {TOTAL_PASOS}
          </p>
          <h2 className="font-display text-lg font-semibold">{PASOS[paso]}</h2>
        </header>
        <div className="p-6">
          {paso === 0 && (
            <StepArchivo
              archivo={archivo}
              archivoOriginal={archivoOriginal}
              tipo={tipo}
              onArchivo={(f) => {
                setArchivo(f);
                setReporte(null);
                setIdCrudo(null);
                setIdInstrumento(null);
                setJsonInstrumento(null);
                setTiposDetectados(null);
                setTiposConfirmados(null);
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
            <StepTiposPregunta
              preguntas={tiposConfirmados}
              notas={notasPreview}
              onChange={setTiposConfirmados}
            />
          )}
          {paso === 3 && <StepDublinCore valor={dc} onChange={setDc} />}
          {paso === 4 && tipo && <StepMetadatosTipo tipo={tipo} valor={meta} onChange={setMeta} />}
          {paso === 5 && <JsonPreview datos={documento} />}
          {paso === 6 && (
            <StepKpis
              sugeridos={sugeridos}
              decisiones={decisiones}
              onDecidir={(id, d) => setDecisiones({ ...decisiones, [id]: d })}
            />
          )}
          {paso === PASO_CALCULO && (
            <StepCalculoKpis
              idInstrumento={idInstrumento}
              kpis={kpisParaCalcular}
              estados={calculos}
              onCambio={(kpiId, estado) => setCalculos((prev) => ({ ...prev, [kpiId]: estado }))}
            />
          )}
          {paso === PASO_GUARDAR && (
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
          {paso < PASO_GUARDAR ? (
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
