"""Etapas 1–3 del chat juntas: interpretar → ejecutar → preparar la redacción (28 oct, Fase 3).

`rag_service.planear` llama a `preparar` después de las reglas fijas de PA (privacidad, manipulación) y de la
ayuda. Con el plan:
  - intenciones estructuradas → `ejecutor.ejecutar`; la redacción recibe SOLO ese resultado;
  - `aclaracion` → la pregunta breve del plan, sin LLM;
  - `fuera_de_dominio` → mensaje fijo, salvo que la pregunta hable de algo del catálogo (entonces es semántica:
    con instrumentos seleccionados, preguntar por respondentes, preguntas o respuestas siempre es del dominio);
  - `semantica_abierta` / `metodologia` → búsqueda en el RAG con la `consulta_semantica` reformulada, sin el
    clasificador de la zona gris (la interpretación ya decidió que es del dominio);
  - `uso_plataforma` → base de ayuda.
Si Ollama no responde o el plan no es válido dos veces, `preparar` devuelve el motivo y el chat sigue con las
reglas anteriores (degradación).

Redacción por intención (`FORMATO`): tabla para respondentes y sus respuestas, cifra con su contexto para conteos,
2–4 oraciones para hallazgos. Las tablas no las escribe el modelo: se anexan tal cual del cálculo (`anexo`), y el
modelo solo redacta la presentación (criterio aplicado y cuántos cumplen en total). Las fuentes son las que el
resultado usó: instrumento, preguntas y respondentes; los KPIs solo si la consulta trata de KPIs.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

from models import FuenteChatOut
from services import ejecutor, enrutador, interpretacion
from services.catalogo import Catalogo, construir as construir_catalogo
from services.dominio import normalizar
from services.ejecutor import Ejecucion
from services.interpretacion import Interpretacion
from services.plan_consulta import PlanConsulta

# Intenciones cuya respuesta es una tabla de respondentes: la presentación es fija (criterio y conteo calculados) y
# la tabla sale del cálculo. Al redactarlas, el modelo de 3B llegó a inventar una tabla con respuestas falsas que
# no traía cifras y pasaba la verificación (28 oct, «qué respondió el primer respondente»). Desde el 4 nov
# `datos_respondente` sí se redacta: el modelo interpreta lo que dijo la persona (en las entrevistas solo se veía la
# transcripción), con la tabla en el prompt y la verificación de tablas, IDs, cifras y citas textuales. Desde el 5 nov
# (RAG primero) también `filtrar_respondentes`: el modelo escribe el criterio y el conteo con el texto recuperado, y la
# tabla se sigue anexando del cálculo.
SIN_REDACCION: set[str] = set()
# Qué tablas van también en el prompt (las chicas); las de respuestas por persona solo se anexan, salvo las de
# `datos_respondente`, que el modelo debe leer para interpretarlas (recortadas a `_MAX_TABLA_EN_PROMPT`).
_TABLAS_EN_PROMPT = {"comparar_grupos", "resumen_pregunta", "kpi", "datos_respondente"}
_MAX_TABLA_EN_PROMPT = 4500
_ALCANCE = re.compile(r"\b(?:respondente|encuestad|estudiante|alumn|participante|entrevistad|pregunta|respuesta|reactivo|"
                      r"kpi|indicador|instrumento|encuesta|prueba|entrevista|escala|opcion)\w*")

# Palabras que se refieren a algo dicho antes («¿qué opinan de eso?»): la pregunta es ambigua, no ajena.
REFERENCIA = re.compile(r"\b(?:eso|esto|ello|ellos|ellas|esa|ese|esas|esos|aquello|lo anterior|lo mismo)\b")

FORMATO = {
    "datos_respondente": "Responde SOLO lo que pide la PREGUNTA, en DOS o TRES oraciones, con lo que dijo o respondió la "
                         "persona según la tabla del RESULTADO CALCULADO: parafrasea con tus palabras y di brevemente qué "
                         "significa para ella (por ejemplo, si le pareció mucho o poco). No agregues otros temas de la "
                         "tabla ni causas o relaciones que la persona no dice. Menciona su ID y la pregunta de donde sale "
                         "(por ejemplo, E01 en p04). Si citas textualmente, copia la frase exacta entre comillas. No "
                         "copies la tabla: se muestra debajo.",
    "filtrar_respondentes": "Escribe UNA o DOS oraciones: el criterio aplicado, cuántos cumplen en total (de cuántos) y "
                            "cuántos se muestran. No copies la tabla ni la lista de respuestas: se muestra debajo.",
    "conteo_porcentaje": "Responde en UNA o DOS oraciones con la cifra exacta, de cuántos y el porcentaje, y el criterio "
                         "aplicado. Nombra las opciones del criterio tal como aparecen, todas, sin resumirlas ni "
                         "cambiarlas (si dice «Sí, y lo aprobé» o «Sí, y no lo aprobé», no escribas «aprobada»).",
    "comparar_grupos": "Escribe DOS o TRES oraciones con la diferencia principal entre los grupos, con sus cifras. La "
                       "tabla completa se muestra debajo.",
    "resumen_pregunta": "Escribe DOS o TRES oraciones con lo más importante de la distribución, con sus cifras. La tabla "
                        "se muestra debajo.",
    "ranking_preguntas": "Responde en UNA o DOS oraciones cuál es la primera pregunta del ranking, con su cifra exacta, y "
                         "si hay empate dilo. Si el criterio dice «sin contar», menciónalo. La tabla se muestra debajo.",
    "kpi": "Escribe DOS o TRES oraciones sobre los KPIs y las preguntas que los sustentan. La tabla se muestra debajo.",
    "hallazgo": "Presenta TRES o CUATRO patrones (todos si hay menos), los más interesantes de los datos numerados, "
                "como una lista con viñetas. En cada viñeta: la cifra exacta tal como está en su dato y lo que "
                "respondieron, y UNA frase breve con lo que podría indicar para la investigación, con cautela («podría "
                "indicar», «sugiere»). Interpreta por las opciones que eligieron, no por las palabras «nivel alto» o "
                "«nivel bajo»: si ante un problema respondieron «Nunca» o «Rara vez», el problema es poco frecuente. "
                "Si dos se relacionan, dilo. El TEXTO RECUPERADO dice de qué trata cada pregunta: "
                "úsalo para entenderla, no para sacar cifras. No menciones respondentes. No uses la palabra «dato» ni "
                "su número.",
    # Entrevistas: los patrones salen del texto recuperado del RAG (con uno o pocos participantes no hay conteos).
    "hallazgo_texto": "Con el TEXTO RECUPERADO (lo que dijeron los participantes), presenta de TRES a CINCO temas o "
                      "patrones que se repiten o destacan, como una lista con viñetas. En cada viñeta: el tema, quién lo "
                      "dice y en qué pregunta (por ejemplo, E01 en p02) y una cita breve copiada exacta entre comillas. "
                      "Si un tema se relaciona con otro, dilo. No inventes temas que no estén en el texto.",
}


@dataclass
class Preparada:
    """Lo que salió de interpretar y ejecutar una pregunta."""

    interp: Interpretacion
    instrumentos: list[enrutador.Instrumento] = field(default_factory=list)
    catalogos: list[Catalogo] = field(default_factory=list)
    ejecuciones: list[Ejecucion] = field(default_factory=list)
    ms_ejecucion: int = 0

    @property
    def plan(self) -> PlanConsulta | None:
        return self.interp.plan

    def registro(self) -> dict[str, Any]:
        """Lo que se guarda en rag_log.plan."""
        return {"plan": self.plan.model_dump(exclude_defaults=True) if self.plan else None,
                "correcciones": self.interp.correcciones, "intentos": self.interp.intentos, "error": self.interp.error}


async def preparar(pregunta: str, historial: list[tuple[str, str]], ids: list[str], sesion: Any,
                   tema: str = "", pistas: str = "") -> Preparada:
    """Interpreta la pregunta con el catálogo del alcance y, si la intención es estructurada, ejecuta el plan.

    `tema`: de qué trató la respuesta anterior (seguimientos). `pistas`: lo que recuperó el RAG."""
    instrumentos = enrutador.cargar_documentos(sesion, ids)
    catalogos = [construir_catalogo(i.id_crudo, i.titulo, i.tipo, i.doc) for i in instrumentos]
    interp = await interpretacion.interpretar(pregunta, historial, catalogos, tema, pistas)
    preparada = Preparada(interp, instrumentos, catalogos)
    if interp.plan is not None:
        inicio = time.perf_counter()
        preparada.ejecuciones = ejecutor.ejecutar(interp.plan, instrumentos, ejecutor.fiabilidad_de(sesion, instrumentos))
        preparada.ms_ejecucion = round((time.perf_counter() - inicio) * 1000)
    return preparada


# Palabras de los datos de contexto que no los nombran por sí solas (raíces de 5 letras).
_CONTEXTO_GENERICO = {"tipo", "nivel", "tiene", "numer", "grupo", "dato", "datos", "true", "false", "otro", "otra",
                      "ningu"}


def del_alcance(pregunta: str, catalogos: list[Catalogo]) -> bool:
    """¿La pregunta habla de algo de los instrumentos? Respondentes, preguntas, IDs; el nombre o un valor de un dato de
    contexto («beca» → tiene_beca), o dos palabras del instrumento aunque estén en preguntas distintas («¿cuánto esperó
    para que la atendieran en psicología?»: «atend» en p05, «psico» en p03; Fase 6, consulta 1535)."""
    texto = normalizar(pregunta)
    if _ALCANCE.search(texto) or enrutador.refiere_al_alcance(pregunta) or re.search(r"\b[rpae]-?\d{1,4}\b", texto):
        return True
    raices = enrutador._raices(texto)
    for c in catalogos:
        contexto: set[str] = set()
        for var in c.numericas:
            contexto |= enrutador._raices(var.replace("_", " "))
        for var, valores in c.contexto.items():
            contexto |= enrutador._raices(var.replace("_", " "))
            contexto |= {r for v in valores for r in enrutador._raices(str(v))}
        # Sin números: «P1» o «1.8» no nombran nada.
        if any(not r[0].isdigit() for r in raices & (contexto - _CONTEXTO_GENERICO)):
            return True
        vocabulario = set().union(*(enrutador._raices(p.texto) for p in c.preguntas.values()))
        if len(raices & vocabulario) >= 2:
            return True
    return False


def _tipo_ui(ins: enrutador.Instrumento) -> str:
    return ins.tipo_ui


def fuentes(ejecuciones: list[Ejecucion]) -> list[FuenteChatOut]:
    """Una tarjeta por instrumento con lo que el resultado usó; KPIs solo si los usó."""
    salida = []
    for n, e in enumerate(ejecuciones, start=1):
        nombres = {str(k.get("kpi_id")): str(k.get("nombre", "")) for k in e.instrumento.doc.get("kpis_asociados") or []}
        partes = [e.criterio] if e.criterio else []
        if e.preguntas:
            partes.append("Preguntas: " + ", ".join(p.rsplit("-", 1)[-1] for p in e.preguntas[:20]))
        if e.respondentes:
            partes.append("Respondentes: " + ", ".join(r.rsplit("-", 1)[-1] for r in e.respondentes[:20]))
        salida.append(FuenteChatOut(numero=n, instrumentoId=e.instrumento.id_crudo, titulo=e.instrumento.titulo,
                                    tipo=_tipo_ui(e.instrumento), investigador="",
                                    kpis=[nombres.get(k, k) for k in e.kpis], fragmento=" · ".join(partes)[:600]))
    return salida


def _bloque(n: int, e: Ejecucion, con_tablas: bool, recortar: bool = False) -> str:
    lineas = [f"[Fuente {n}] {e.instrumento.titulo} ({e.instrumento.tipo_ui})"]
    if e.criterio:
        lineas.append(f"- Criterio: {e.criterio}")
    lineas += [f"- {l}" for l in e.lineas]
    if con_tablas:
        tablas = [t.markdown() for t in e.tablas]
        if recortar and e.intencion == "datos_respondente":
            tablas = [t if len(t) <= _MAX_TABLA_EN_PROMPT else f"{t[:_MAX_TABLA_EN_PROMPT]}\n(tabla recortada)"
                      for t in tablas]
        lineas += tablas
    elif e.tablas:
        lineas.append(f"- (Debajo de tu respuesta se muestra la tabla «{e.tablas[0].titulo}».)")
    return "\n".join(lineas)


def resultado_completo(ejecuciones: list[Ejecucion]) -> str:
    """Todo lo calculado (para el registro, las métricas y la verificación de cifras)."""
    return "\n\n".join(_bloque(n, e, True) for n, e in enumerate(ejecuciones, start=1))


def resultado_para_prompt(ejecuciones: list[Ejecucion], intencion: str) -> str:
    return "\n\n".join(_bloque(n, e, intencion in _TABLAS_EN_PROMPT, recortar=True)
                       for n, e in enumerate(ejecuciones, start=1))


def anexo(ejecuciones: list[Ejecucion]) -> str:
    """Tablas que se muestran tal cual debajo de la redacción."""
    bloques = []
    for n, e in enumerate(ejecuciones, start=1):
        for t in e.tablas:
            titulo = f"{t.titulo} — {e.instrumento.titulo} [Fuente {n}]" if len(ejecuciones) > 1 else f"{t.titulo} [Fuente {n}]"
            bloques.append(ejecutor.Tabla(titulo, t.columnas, t.filas).markdown())
    return "\n\n".join(bloques)


def directa(ejecuciones: list[Ejecucion]) -> str:
    """Respuesta sin redacción (respaldo si la del modelo no pasa la verificación): criterio y líneas calculadas."""
    bloques = []
    for n, e in enumerate(ejecuciones, start=1):
        lineas = [f"Criterio: {e.criterio}."] if e.criterio and e.intencion not in ("hallazgo", "datos_respondente") else []
        if e.intencion == "datos_respondente" and e.respondentes:
            ids = ", ".join(r.rsplit("-", 1)[-1] for r in e.respondentes)
            lineas.append(f"Respuestas interpretadas de {ids} ({e.criterio}).")
        elif e.intencion == "hallazgo":
            lineas += [f"- {c['texto']}" for c in e.candidatos[:3]] if e.candidatos else e.lineas
        else:
            lineas += e.lineas
        cuerpo = "\n".join(lineas) or "Resultado calculado."
        bloques.append(f"{cuerpo} [Fuente {n}]" if len(ejecuciones) == 1 else f"{e.instrumento.titulo}:\n{cuerpo} [Fuente {n}]")
    return "\n\n".join(bloques)


_CONTEO = re.compile(r"(\d+) de (\d+)|(\d+(?:\.\d+)?) %")


def cifras_clave(ejecuciones: list[Ejecucion]) -> set[float]:
    """Cifras que la redacción DEBE conservar: cuántos cumplen, de cuántos y su porcentaje («382 de 2000 (19.1 %)»).

    Se toman de las líneas de conteo (en un conteo, de todas sus líneas). En un hallazgo el modelo elige un
    candidato, así que no hay cifras obligatorias: solo se exige que las que use existan (`cifras_fieles`).
    """
    claves: set[float] = set()
    for e in ejecuciones:
        if e.intencion == "hallazgo":
            continue
        for l in e.lineas:
            if e.intencion == "conteo_porcentaje" or l.startswith(("Cumplen la condición", "Se muestran")):
                for m in _CONTEO.finditer(l):
                    claves |= {float(x) for x in m.groups() if x}
    return claves
