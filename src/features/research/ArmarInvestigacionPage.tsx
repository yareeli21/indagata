import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import { buscarRelacionados, getInstrumentos, getInvestigadores } from "@/api/instrumentos";
import { useAuth } from "@/features/auth/AuthContext";
import { useResearch } from "@/features/research/ResearchContext";
import type { Instrumento, InstrumentoRelacionado, Investigador } from "@/types";
import { Stepper } from "./Stepper";
import { Paso1Seleccion } from "./Paso1Seleccion";
import { Paso2Relacionados } from "./Paso2Relacionados";
import { Paso3Revision } from "./Paso3Revision";

const PASOS = [
  { numero: 1, etiqueta: "Elige tus instrumentos" },
  { numero: 2, etiqueta: "Instrumentos relacionados" },
  { numero: 3, etiqueta: "Revisa tu selección" },
];

export function ArmarInvestigacionPage() {
  const { usuario } = useAuth();
  const { crear } = useResearch();
  const navigate = useNavigate();

  const miId = usuario?.investigadorId ?? "";

  // Datos cargados
  const [todosLosInstrumentos, setTodosLosInstrumentos] = useState<Instrumento[]>([]);
  const [investigadores, setInvestigadores] = useState<Investigador[]>([]);
  const [cargandoDatos, setCargandoDatos] = useState(true);

  useEffect(() => {
    Promise.all([getInstrumentos(), getInvestigadores()]).then(([insts, invs]) => {
      setTodosLosInstrumentos(insts);
      setInvestigadores(invs);
      setCargandoDatos(false);
    });
  }, []);

  // Paso actual
  const [paso, setPaso] = useState(1);

  // Paso 1 — selección propia
  const [seleccionadosPropios, setSeleccionadosPropios] = useState<string[]>([]);

  // Paso 2 — relacionados
  const [buscando, setBuscando] = useState(false);
  const [relacionados, setRelacionados] = useState<InstrumentoRelacionado[]>([]);
  const [seleccionadosAjenos, setSeleccionadosAjenos] = useState<string[]>([]);

  // Instrumentos derivados
  const instrumentosPropios = useMemo(
    () => todosLosInstrumentos.filter((i) => i.autorId === miId),
    [todosLosInstrumentos, miId],
  );

  const propiosSeleccionadosObj = useMemo(
    () => instrumentosPropios.filter((i) => seleccionadosPropios.includes(i.id)),
    [instrumentosPropios, seleccionadosPropios],
  );

  const ajenosSeleccionadosObj = useMemo(() => {
    const mapaRelacionados = new Map(
      relacionados.map((r) => [r.instrumento.id, r.instrumento]),
    );
    return seleccionadosAjenos
      .map((id) => mapaRelacionados.get(id))
      .filter((i): i is Instrumento => !!i);
  }, [relacionados, seleccionadosAjenos]);

  const nombreAutor = (id: string) =>
    investigadores.find((x) => x.id === id)?.nombre ?? "—";

  // Navegación del wizard
  async function irAPaso2() {
    setPaso(2);
    setBuscando(true);
    const resultados = await buscarRelacionados(seleccionadosPropios, miId);
    setRelacionados(resultados);
    setBuscando(false);
  }

  function omitirBusqueda() {
    setRelacionados([]);
    setSeleccionadosAjenos([]);
    setPaso(3);
  }

  function irAPaso3() {
    setPaso(3);
  }

  function volverA1() {
    setPaso(1);
    setRelacionados([]);
    setSeleccionadosAjenos([]);
  }

  function volverA2() {
    setPaso(2);
  }

  async function iniciarInvestigacion(nombre: string) {
    await crear(nombre);
    toast.success(`Investigación «${nombre}» creada. ¡Empieza a explorar!`);
    navigate({ to: "/chat" });
  }

  // Quitar de la selección final
  function quitarPropio(id: string) {
    setSeleccionadosPropios((prev) => prev.filter((x) => x !== id));
  }
  function quitarAjeno(id: string) {
    setSeleccionadosAjenos((prev) => prev.filter((x) => x !== id));
  }

  return (
    <div className="mx-auto max-w-2xl space-y-8 p-6 md:p-8">
      {/* Cabecera */}
      <div>
        <h1 className="text-2xl font-bold">Armar investigación</h1>
        <p className="text-muted-foreground">
          Selecciona instrumentos y dale un nombre a tu proyecto.
        </p>
      </div>

      {/* Stepper */}
      <Stepper pasos={PASOS} actual={paso} />

      {/* Contenido del paso */}
      <div className="rounded-xl border bg-card p-6 shadow-sm">
        <h2 className="mb-6 text-lg font-semibold">
          {PASOS[paso - 1].etiqueta}
        </h2>

        {paso === 1 && (
          <>
            {cargandoDatos ? (
              <p className="py-8 text-center text-sm text-muted-foreground">
                Cargando instrumentos…
              </p>
            ) : (
              <Paso1Seleccion
                instrumentos={instrumentosPropios}
                seleccionados={seleccionadosPropios}
                onCambiarSeleccion={setSeleccionadosPropios}
                onBuscar={irAPaso2}
                onOmitir={omitirBusqueda}
              />
            )}
          </>
        )}

        {paso === 2 && (
          <Paso2Relacionados
            cargando={buscando}
            relacionados={relacionados}
            propiosSeleccionados={propiosSeleccionadosObj}
            seleccionadosAjenos={seleccionadosAjenos}
            onCambiarSeleccion={setSeleccionadosAjenos}
            onSiguiente={irAPaso3}
            onAtras={volverA1}
          />
        )}

        {paso === 3 && (
          <Paso3Revision
            propios={propiosSeleccionadosObj}
            ajenos={ajenosSeleccionadosObj}
            onQuitarPropio={quitarPropio}
            onQuitarAjeno={quitarAjeno}
            onIniciar={iniciarInvestigacion}
            onAtras={seleccionadosAjenos.length > 0 || relacionados.length > 0 ? volverA2 : volverA1}
          />
        )}
      </div>
    </div>
  );
}
