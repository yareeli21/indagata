"""Sugerencias de análisis a partir de las medidas estadísticas de la limpieza (sin LLM).

Lee la `estadistica` que cleaning-service guarda en `reporte_limpieza.vista_final`
(la misma que se ve en el paso «Limpieza») y propone qué análisis conviene hacer y
con qué cautelas. Los umbrales son los de `markdowns/METRICAS_LIMPIEZA.md`:
  - α de Cronbach / KR-20: ≥ 0.7 aceptable, 0.6–0.7 cuestionable, < 0.6 pobre; > 0.95 posible redundancia.
  - correlación ítem-total < 0.3: el ítem «va por su lado».
  - vacíos > 20 %: pregunta confusa, opcional o mal ubicada.
  - asimetría fuera de ±1: distribución sesgada (mejor mediana y rango intercuartílico).
  - discriminación < 0.2 o negativa: reactivo a revisar.

La usan cleaning-service (`GET /limpieza/{id}/resumen`, que se ve en el catálogo) y el
chat (intención `calidad` del enrutador de visualization-service).
"""
from __future__ import annotations

from typing import Any

BIEN, INFO, ATENCION, ALERTA = "bien", "info", "atencion", "alerta"
_ORDEN = {ALERTA: 0, ATENCION: 1, BIEN: 2, INFO: 3}


def _s(nivel: str, texto: str, porque: str) -> dict[str, str]:
    return {"nivel": nivel, "texto": texto, "porque": porque}


def _fmt(x: float) -> str:
    return f"{x:.2f}".rstrip("0").rstrip(".") if isinstance(x, float) else str(x)


def _encuesta(e: dict[str, Any]) -> list[dict[str, str]]:
    salida: list[dict[str, str]] = []
    columnas = e.get("columnas") or []
    preguntas = [c for c in columnas if c.get("rol") == "pregunta"]
    contexto = [c for c in columnas if c.get("rol") == "contexto" and c.get("tipo") in ("categorica", "binaria")]
    n = max((c.get("n") or 0 for c in columnas), default=0)

    bloques = e.get("fiabilidad") if isinstance(e.get("fiabilidad"), list) else []
    for b in bloques:
        alfa, nombre, k = b.get("alfa"), b.get("bloque") or "sin nombre", b.get("n_items") or len(b.get("items") or [])
        if alfa is None:
            continue
        if alfa > 0.95:
            salida.append(_s(ATENCION, f"El bloque «{nombre}» tiene α = {_fmt(alfa)}: revisa si hay ítems redundantes antes de promediarlo.",
                             "Un α mayor a 0.95 suele indicar la misma pregunta dicha de varias formas."))
        elif alfa >= 0.7:
            salida.append(_s(BIEN, f"Puedes promediar los {k} ítems del bloque «{nombre}» y analizarlo como una escala (α = {_fmt(alfa)}).",
                             "Con α ≥ 0.7 los ítems miden lo mismo de forma consistente."))
        elif alfa >= 0.6:
            salida.append(_s(ATENCION, f"Usa el bloque «{nombre}» como escala solo con cautela (α = {_fmt(alfa)}, cuestionable).",
                             "Entre 0.6 y 0.7 la consistencia interna es dudosa; repórtalo junto con el resultado."))
        else:
            salida.append(_s(ALERTA, f"No promedies el bloque «{nombre}» (α = {_fmt(alfa)}): analiza sus ítems uno por uno.",
                             "Con α < 0.6 los ítems no miden lo mismo; el promedio mezclaría cosas distintas."))
        flojos = [i for i in b.get("por_item") or [] if (i.get("correlacion_item_total") or 1) < 0.3]
        mejora = [i for i in b.get("por_item") or [] if (i.get("alfa_si_se_elimina") or 0) > alfa + 0.02]
        if flojos or mejora:
            items = ", ".join(sorted({str(i.get("item")) for i in flojos + mejora}))
            salida.append(_s(ATENCION, f"Revisa en «{nombre}»: {items} (correlación ítem-total baja o el α sube si se quita).",
                             "Un ítem con correlación ítem-total < 0.3 no va de la mano con su bloque."))

    if any(c.get("tipo") == "likert" for c in preguntas):
        salida.append(_s(INFO, "En los ítems Likert reporta la mediana y el % de acuerdo (de acuerdo + totalmente de acuerdo), no solo la media.",
                         "Las escalas Likert son ordinales: la distancia entre opciones no es necesariamente igual."))
    if contexto:
        nombres = ", ".join(f"«{c.get('etiqueta') or c.get('id')}»" for c in contexto[:4])
        salida.append(_s(INFO, f"Compara grupos de {nombres}: Mann-Whitney (2 grupos) o Kruskal-Wallis (3 o más) para ítems "
                               "Likert y numéricos; χ² para preguntas categóricas.",
                         "Son pruebas no paramétricas, adecuadas para datos ordinales o sin normalidad."))
    numericas = [c for c in preguntas if c.get("numerico") and c.get("tipo") != "likert"]
    sesgadas = [c for c in numericas if abs((c.get("numerico") or {}).get("asimetria") or 0) > 1]
    if sesgadas:
        salida.append(_s(INFO, "Distribuciones sesgadas en " + ", ".join(f"«{c.get('etiqueta') or c.get('id')}»" for c in sesgadas[:4])
                         + ": resume con mediana y rango intercuartílico.", "Con asimetría fuera de ±1 la media se va hacia la cola."))
    if numericas and (bloques or any(c.get("tipo") == "likert" for c in preguntas)):
        salida.append(_s(INFO, "Para relacionar escalas y preguntas numéricas usa la correlación de Spearman.",
                         "No supone normalidad y funciona con datos ordinales."))
    vacias = [c for c in preguntas if (c.get("pct_nulos") or 0) > 20]
    if vacias:
        salida.append(_s(ATENCION, "Más del 20 % sin respuesta en " + ", ".join(f"«{c.get('etiqueta') or c.get('id')}»" for c in vacias[:4])
                         + ": interpreta esos resultados con cautela.", "Muchos vacíos sugieren una pregunta confusa, opcional o mal ubicada."))
    encuestados = e.get("encuestados") or {}
    recta = encuestados.get("linea_recta") or 0
    if n and recta / n > 0.1:
        salida.append(_s(ATENCION, f"{recta} de {n} encuestados ({round(100 * recta / n, 1)} %) respondieron en línea recta: repite los "
                                   "análisis principales sin ellos para ver si cambian.",
                         "Responder siempre la misma opción puede ser falta de atención, no una opinión real."))
    return salida


def _prueba(e: dict[str, Any]) -> list[dict[str, str]]:
    salida: list[dict[str, str]] = []
    fiab = e.get("fiabilidad") if isinstance(e.get("fiabilidad"), dict) else {}
    kr20 = fiab.get("kr20")
    if kr20 is not None:
        if kr20 >= 0.7:
            salida.append(_s(BIEN, f"La prueba es confiable en conjunto (KR-20 = {_fmt(kr20)}): puedes usar el puntaje total.",
                             "Con KR-20 ≥ 0.7 los reactivos miden la misma habilidad."))
        else:
            salida.append(_s(ATENCION, f"KR-20 = {_fmt(kr20)} ({fiab.get('interpretacion') or 'bajo'}): usa el puntaje total con cautela y "
                                       "analiza también por reactivo.",
                             f"Con {fiab.get('n_reactivos')} reactivos y {fiab.get('n_alumnos')} alumnos la fiabilidad está por debajo de 0.7."))
    reactivos = [r for r in e.get("reactivos") or [] if r.get("discriminacion") is not None]
    malos = [r for r in reactivos if r["discriminacion"] < 0.2]
    if malos:
        lista = ", ".join(f"{r.get('pregunta')} (D = {_fmt(r['discriminacion'])})" for r in malos[:6])
        salida.append(_s(ALERTA, f"Revisa los reactivos que no distinguen a quienes saben más: {lista}.",
                         "Discriminación < 0.2 es pobre; negativa casi siempre es una clave mal capturada o un reactivo confuso."))
    sin_elegir = [r for r in e.get("reactivos") or [] if r.get("distractores_sin_elegir")]
    if sin_elegir:
        salida.append(_s(INFO, f"{len(sin_elegir)} reactivos tienen distractores que nadie eligió: conviene reescribirlos.",
                         "Un distractor que nadie elige no aporta; el reactivo se vuelve más fácil de lo que parece."))
    resumen = e.get("resumen_reactivos") or {}
    total = sum(resumen.get(k) or 0 for k in ("faciles", "medios", "dificiles"))
    if total and (resumen.get("faciles") or 0) / total > 0.5:
        salida.append(_s(INFO, f"{resumen['faciles']} de {total} reactivos son fáciles: la prueba distingue poco entre alumnos con buen nivel.",
                         "Lo ideal es que la mayoría tenga dificultad media (0.3–0.7)."))
    if reactivos:
        salida.append(_s(INFO, "Para comparar grupos de alumnos usa el puntaje total (t de Student o Mann-Whitney si no es normal).",
                         "El puntaje total resume la prueba cuando la fiabilidad lo permite."))
    return salida


def _entrevista(e: dict[str, Any]) -> list[dict[str, str]]:
    salida: list[dict[str, str]] = []
    participantes = [p for p in e.get("participantes") or [] if p.get("palabras")]
    if len(participantes) >= 2:
        mas = max(participantes, key=lambda p: p["palabras"])
        menos = min(participantes, key=lambda p: p["palabras"])
        if menos["palabras"] and mas["palabras"] / menos["palabras"] > 3:
            salida.append(_s(ATENCION, f"La participación es desigual ({mas['id']}: {mas['palabras']} palabras; {menos['id']}: "
                                       f"{menos['palabras']}): cuida que una voz no domine las conclusiones.",
                             "Si un participante habla mucho más, sus temas pesan más en el análisis."))
    if e.get("n_preguntas") or e.get("preguntas"):
        salida.append(_s(INFO, "Haz una codificación temática por pregunta del guion y compara los temas entre participantes.",
                         "Las entrevistas se analizan por significado, no con estadística."))
    return salida


def sugerir(tipo: str, estadistica: dict[str, Any] | None) -> list[dict[str, str]]:
    """Sugerencias `{nivel, texto, porque}` ordenadas: primero alertas y cautelas."""
    if not estadistica:
        return []
    if tipo == "prueba_estandarizada" or estadistica.get("reactivos"):
        salida = _prueba(estadistica)
    elif tipo == "entrevista" or estadistica.get("hablantes") or estadistica.get("participantes"):
        salida = _entrevista(estadistica)
    else:
        salida = _encuesta(estadistica)
    return sorted(salida, key=lambda s: _ORDEN[s["nivel"]])
