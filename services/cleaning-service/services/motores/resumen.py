"""Resumen en lenguaje sencillo de las medidas estadísticas («En pocas palabras»).

Reglas fijas sobre las cifras que ya calcula cada motor (sin LLM): los mismos datos
dan siempre el mismo resumen. Cada frase lleva un nivel para la interfaz:
  - bien:      algo que está en orden.
  - info:      una descripción de los datos (tendencia, dispersión…).
  - atencion:  conviene revisarlo.
  - alerta:    probablemente hay un problema (p. ej. una clave mal capturada).
"""
from __future__ import annotations

from typing import Any

_TODAS = "Todas las escalas Likert"
_MAX_FRASES = 8
_MAX_NOMBRES = 3
_NUMERICOS = ("numerica", "escala_lineal", "calificacion")


def _n(x: float | None, d: int = 2) -> str:
    """Número corto: sin ceros de más («3.3», «0.94», «14»)."""
    if x is None:
        return "—"
    texto = f"{x:.{d}f}"
    if "." in texto:
        texto = texto.rstrip("0").rstrip(".")
    return texto if texto != "-0" else "0"


def _pct(x: float) -> str:
    return f"{_n(x * 100, 0)} %"


def _corto(texto: str, largo: int = 60) -> str:
    texto = " ".join(str(texto).split())
    return texto if len(texto) <= largo else texto[: largo - 1].rstrip() + "…"


def _nombres(nombres: list[str]) -> str:
    """«A», «A» y «B», «A», «B» y 3 más."""
    citados = [f"«{_corto(n, 50)}»" for n in nombres[:_MAX_NOMBRES]]
    resto = len(nombres) - len(citados)
    if resto:
        return f"{', '.join(citados)} y {resto} más"
    return citados[0] if len(citados) == 1 else f"{', '.join(citados[:-1])} y {citados[-1]}"


def _frase(nivel: str, texto: str) -> dict[str, str]:
    return {"nivel": nivel, "texto": texto}


def resumir(
    tipo: str,
    estadistica: dict[str, Any] | None,
    metricas_antes: dict[str, Any] | None = None,
    metricas_despues: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Frases clave para el investigador, de la más a la menos importante."""
    if not estadistica:
        return []
    antes, despues = metricas_antes or {}, metricas_despues or {}
    if tipo == "encuesta":
        frases = _encuesta(estadistica, antes, despues)
    elif tipo == "prueba_estandarizada":
        frases = _prueba(estadistica)
    elif tipo == "entrevista":
        frases = _entrevista(estadistica)
    else:
        frases = []
    return frases[:_MAX_FRASES]


# ── Encuestas ──────────────────────────────────────────────────────────────────


def _bloques(estadistica: dict[str, Any]) -> list[dict[str, Any]]:
    """Bloques a comentar: los de cada dimensión; el global solo si no hay otros."""
    bloques = [b for b in estadistica.get("fiabilidad") or [] if isinstance(b, dict)]
    propios = [b for b in bloques if b.get("bloque") != _TODAS]
    return propios or bloques


def _fiabilidad(bloques: list[dict[str, Any]]) -> list[dict[str, str]]:
    frases = []
    sin_alfa = [b["bloque"] for b in bloques if b.get("alfa") is None]
    con_alfa = [b for b in bloques if b.get("alfa") is not None]
    solo_global = len(bloques) == 1 and bloques[0].get("bloque") == _TODAS

    if len(con_alfa) == 1:
        b = con_alfa[0]
        alfa, interp = b["alfa"], b.get("interpretacion") or ""
        nombre = "Las escalas Likert, en conjunto," if solo_global else f"El bloque «{_corto(b['bloque'])}»"
        if alfa >= 0.7:
            frases.append(_frase("bien", f"{nombre} {'son consistentes' if solo_global else 'es consistente'}: α = {_n(alfa, 3)} ({interp})."))
        else:
            frases.append(
                _frase(
                    "alerta" if alfa < 0.6 else "atencion",
                    f"{nombre} {'tienen' if solo_global else 'tiene'} poca consistencia interna: α = {_n(alfa, 3)} ({interp}). "
                    "Revisa los ítems marcados en «Por ítem» o si falta invertir alguno.",
                )
            )
        if solo_global and b.get("n_items", 0) >= 2:
            frases.append(
                _frase(
                    "atencion",
                    f"Ese α se calculó sobre las {b.get('n_items')} escalas juntas porque no se reconocieron dimensiones "
                    "en los encabezados. Si el cuestionario mide varias dimensiones, el α de cada una es el que importa.",
                )
            )
    elif con_alfa:
        buenos = [b for b in con_alfa if b["alfa"] >= 0.7]
        flojos = [b for b in con_alfa if b["alfa"] < 0.7]
        if not flojos:
            minimo = min(b["alfa"] for b in con_alfa)
            frases.append(_frase("bien", f"Los {len(con_alfa)} bloques de escalas son consistentes (α de {_n(minimo, 3)} o más)."))
        else:
            detalle = ", ".join(f"«{_corto(b['bloque'], 40)}» (α = {_n(b['alfa'], 3)})" for b in flojos[:_MAX_NOMBRES])
            mas = f" y {len(flojos) - _MAX_NOMBRES} más" if len(flojos) > _MAX_NOMBRES else ""
            peor = min(b["alfa"] for b in flojos)
            frases.append(
                _frase(
                    "alerta" if peor < 0.6 else "atencion",
                    f"{len(buenos)} de {len(con_alfa)} bloques son consistentes; con poca consistencia: {detalle}{mas}.",
                )
            )
    redundantes = [b["bloque"] for b in con_alfa if b["alfa"] > 0.95]
    if redundantes:
        frases.append(
            _frase(
                "atencion",
                f"α mayor a 0.95 en {_nombres(redundantes)}: puede haber ítems redundantes (la misma pregunta dicha de varias formas).",
            )
        )
    if sin_alfa:
        frases.append(
            _frase("atencion", f"No se pudo calcular el α de {_nombres(sin_alfa)}: hay muy pocas personas que respondieron todos sus ítems.")
        )
    return frases


def _items_problema(bloques: list[dict[str, Any]]) -> list[dict[str, str]]:
    negativos, flojos = [], []
    for b in bloques:
        alfa = b.get("alfa")
        if alfa is None:
            continue
        for it in b.get("por_item") or []:
            r, sin = it.get("correlacion_item_total"), it.get("alfa_si_se_elimina")
            if r is not None and r < 0:
                negativos.append(it["item"])
            elif (r is not None and r < 0.3) or (sin is not None and sin > alfa + 0.01):
                flojos.append(it["item"])
    frases = []
    if negativos:
        frases.append(
            _frase(
                "alerta",
                f"{_nombres(negativos)} va{'n' if len(negativos) > 1 else ''} en sentido contrario a su bloque: "
                "probablemente es un ítem invertido sin marcar.",
            )
        )
    if flojos:
        frases.append(
            _frase(
                "atencion",
                f"{_nombres(flojos)} se relaciona{'n' if len(flojos) > 1 else ''} poco con el resto de su bloque; "
                "conviene revisar su redacción.",
            )
        )
    return frases


def _neutral(col: dict[str, Any]) -> tuple[float, float, float] | None:
    """(mínimo, neutral, máximo) de la escala de una columna Likert."""
    tabla = (col.get("frecuencias") or {}).get("tabla") or []
    puntos = (col.get("escala") or {}).get("puntos")
    try:
        lo, hi = float(tabla[0]["valor"]), float(tabla[-1]["valor"])
    except (IndexError, KeyError, TypeError, ValueError):
        if not puntos:
            return None
        lo, hi = 1.0, float(puntos)
    return lo, (lo + hi) / 2, hi


def _tendencia(columnas: list[dict[str, Any]]) -> list[dict[str, str]]:
    datos = []
    for c in columnas:
        num = c.get("numerico") or {}
        escala = _neutral(c) if c.get("escala") else None
        if escala and num.get("media") is not None:
            lo, neutro, hi = escala
            if hi > lo:
                media = num["media"]
                # Ítems invertidos: lo alto de la escala significa lo contrario.
                if (c.get("escala") or {}).get("invertido"):
                    media = lo + hi - media
                datos.append((c, media, lo, neutro, hi, num.get("desviacion")))
    if not datos:
        return []
    # Solo se comparan ítems de la escala más común (no se mezclan 1–5 con 1–7).
    escalas = [(lo, hi) for _, _, lo, _, hi, _ in datos]
    lo0, hi0 = max(set(escalas), key=escalas.count)
    datos = [d for d in datos if (d[2], d[4]) == (lo0, hi0)]
    neutro0 = (lo0 + hi0) / 2
    frases = []
    # Media relativa a la escala (0 = extremo bajo, 1 = extremo alto).
    relativas = [(m - lo) / (hi - lo) for _, m, lo, _, hi, _ in datos]
    promedio = sum(relativas) / len(relativas)
    referencia = (
        f" (promedio {_n(lo0 + promedio * (hi0 - lo0), 1)} en una escala de {_n(lo0, 0)} a {_n(hi0, 0)}; "
        f"el punto neutral es {_n(neutro0, 1)})"
    )
    if promedio >= 0.65:
        texto = "se inclinan claramente hacia los valores altos de la escala"
    elif promedio > 0.55:
        texto = "se inclinan ligeramente hacia los valores altos de la escala"
    elif promedio >= 0.45:
        texto = "están cerca del punto neutral"
    elif promedio >= 0.35:
        texto = "se inclinan ligeramente hacia los valores bajos de la escala"
    else:
        texto = "se inclinan claramente hacia los valores bajos de la escala"
    frases.append(_frase("info", f"En general, las respuestas a las escalas {texto}{referencia}."))

    if len(datos) >= 3:
        alto = max(datos, key=lambda d: (d[1] - d[2]) / (d[4] - d[2]))
        bajo = min(datos, key=lambda d: (d[1] - d[2]) / (d[4] - d[2]))
        if (alto[1] - alto[2]) / (alto[4] - alto[2]) - (bajo[1] - bajo[2]) / (bajo[4] - bajo[2]) >= 0.15:
            frases.append(
                _frase(
                    "info",
                    f"La media más alta es la de «{_corto(alto[0]['etiqueta'], 50)}» ({_n(alto[1], 2)}) "
                    f"y la más baja, la de «{_corto(bajo[0]['etiqueta'], 50)}» ({_n(bajo[1], 2)}).",
                )
            )

    dispersiones = [d / (hi - lo) for _, _, lo, _, hi, d in datos if d is not None]
    if dispersiones:
        disp = sum(dispersiones) / len(dispersiones)
        if disp >= 0.25:
            frases.append(_frase("info", "Las opiniones están repartidas por toda la escala: no hay un consenso claro entre los encuestados."))
        elif disp <= 0.15:
            frases.append(_frase("info", "Hay bastante consenso: la mayoría de los encuestados elige opciones parecidas."))
    return frases


def _vacios(columnas: list[dict[str, Any]]) -> list[dict[str, str]]:
    if not columnas:
        return []
    altos = [c["etiqueta"] for c in columnas if (c.get("pct_nulos") or 0) > 0.2]
    if altos:
        return [_frase("atencion", f"{_nombres(altos)} tiene{'n' if len(altos) > 1 else ''} más del 20 % sin responder: puede ser confusa, opcional o estar mal ubicada.")]
    maximo = max((c.get("pct_nulos") or 0) for c in columnas)
    if maximo == 0:
        return [_frase("bien", "Todas las preguntas tienen respuesta de todos los encuestados.")]
    if maximo < 0.05:
        return [_frase("bien", "Casi no hay preguntas sin responder (menos del 5 % en cada una).")]
    return []


def _numericas(columnas: list[dict[str, Any]]) -> list[dict[str, str]]:
    frases = []
    for c in columnas:
        if c.get("tipo") not in _NUMERICOS or c.get("escala"):
            continue
        num = c.get("numerico") or {}
        if num.get("q1") is None or num.get("mediana") is None:
            continue
        texto = f"«{_corto(c['etiqueta'], 50)}»: la mitad de las respuestas está entre {_n(num['q1'], 1)} y {_n(num['q3'], 1)} (mediana {_n(num['mediana'], 1)})"
        asim = num.get("asimetria")
        if asim is not None and asim > 0.5:
            texto += f"; unos pocos valores altos (hasta {_n(num.get('max'), 1)}) suben el promedio a {_n(num.get('media'), 1)}"
        elif asim is not None and asim < -0.5:
            texto += f"; unos pocos valores bajos (desde {_n(num.get('min'), 1)}) bajan el promedio a {_n(num.get('media'), 1)}"
        atip = c.get("atipicos") or {}
        n_atip = atip.get(atip.get("metodo") or "sigma") or 0
        nivel = "info"
        if n_atip:
            texto += f". Hay {n_atip} valor{'es' if n_atip > 1 else ''} atípico{'s' if n_atip > 1 else ''}; revisa que no sean errores de captura"
            nivel = "atencion"
        frases.append(_frase(nivel, texto + "."))
    return frases[:2]


def _removidos(antes: dict[str, Any], despues: dict[str, Any]) -> list[dict[str, str]]:
    a, d = antes.get("n_respondentes"), despues.get("n_respondentes")
    if not isinstance(a, (int, float)) or not isinstance(d, (int, float)) or a <= 0 or d >= a:
        return []
    quitados = int(a - d)
    proporcion = quitados / a
    nivel = "atencion" if proporcion > 0.1 else "bien"
    extra = " Es más del 10 %: confirma que las decisiones de la limpieza fueron las correctas." if nivel == "atencion" else ""
    return [
        _frase(
            nivel,
            f"Se quitaron {quitados} encuestado{'s' if quitados > 1 else ''} ({_pct(proporcion)}: duplicados, incompletos u otros que decidiste eliminar); "
            f"quedan {int(d)}.{extra}",
        )
    ]


def _encuesta(estadistica: dict[str, Any], antes: dict[str, Any], despues: dict[str, Any]) -> list[dict[str, str]]:
    columnas = [c for c in estadistica.get("columnas") or [] if isinstance(c, dict)]
    bloques = _bloques(estadistica)
    return [
        *_fiabilidad(bloques),
        *_items_problema(bloques),
        *_vacios(columnas),
        *_removidos(antes, despues),
        *_tendencia(columnas),
        *_numericas(columnas),
    ]


# ── Pruebas estandarizadas ─────────────────────────────────────────────────────


def _prueba(estadistica: dict[str, Any]) -> list[dict[str, str]]:
    frases = []
    fiab = estadistica.get("fiabilidad") or {}
    kr, interp = fiab.get("kr20"), fiab.get("interpretacion") or ""
    n_alumnos, n_reactivos = fiab.get("n_alumnos") or 0, fiab.get("n_reactivos") or 0
    if kr is not None:
        if kr >= 0.7:
            frases.append(_frase("bien", f"La prueba es consistente: KR-20 = {_n(kr, 3)} ({interp})."))
        else:
            causa = " Con pocos reactivos o pocos alumnos suele salir bajo." if n_reactivos < 20 or n_alumnos < 30 else ""
            frases.append(
                _frase(
                    "alerta" if kr < 0.5 else "atencion",
                    f"La prueba tiene poca consistencia interna: KR-20 = {_n(kr, 3)} ({interp}).{causa}",
                )
            )

    punt = estadistica.get("puntajes") or {}
    maximo = punt.get("maximo_posible")
    if punt.get("media") is not None and maximo:
        frases.append(
            _frase(
                "info",
                f"En promedio, los alumnos acertaron {_n(punt['media'], 1)} de {maximo} reactivos "
                f"({_pct(punt['media'] / maximo)}; mediana {_n(punt.get('mediana'), 1)}).",
            )
        )

    reactivos = [r for r in estadistica.get("reactivos") or [] if isinstance(r, dict)]
    res = estadistica.get("resumen_reactivos") or {}
    total = len(reactivos)
    if total:
        faciles, medios, dificiles = res.get("faciles", 0), res.get("medios", 0), res.get("dificiles", 0)
        texto = f"De {total} reactivos: {faciles} fácil{'es' if faciles != 1 else ''}, {medios} de dificultad media y {dificiles} difícil{'es' if dificiles != 1 else ''}."
        if faciles > total / 2:
            texto += " La prueba resultó fácil para este grupo."
        elif dificiles > total / 2:
            texto += " La prueba resultó difícil para este grupo."
        frases.append(_frase("info", texto))

    negativos = [r["pregunta"] for r in reactivos if (r.get("discriminacion") or 0) < 0]
    pobres = [r["pregunta"] for r in reactivos if r.get("nivel_discriminacion") == "pobre" and (r.get("discriminacion") or 0) >= 0]
    if negativos:
        frases.append(
            _frase(
                "alerta",
                f"En {_nombres(negativos)} aciertan más los alumnos con peor puntaje que los de mejor puntaje: "
                "revisa que la respuesta correcta de la clave sea la adecuada.",
            )
        )
    if pobres:
        frases.append(
            _frase(
                "atencion",
                f"{_nombres(pobres)} casi no distingue{'n' if len(pobres) > 1 else ''} a quienes dominan el tema de quienes no "
                "(discriminación pobre); conviene revisar su redacción.",
            )
        )
    elif total and not negativos:
        frases.append(_frase("bien", "Todos los reactivos distinguen al menos regularmente a quienes dominan el tema de quienes no."))

    sin_elegir = [r["pregunta"] for r in reactivos if r.get("distractores_sin_elegir")]
    if sin_elegir:
        frases.append(
            _frase(
                "atencion",
                f"{len(sin_elegir)} reactivo{'s tienen' if len(sin_elegir) > 1 else ' tiene'} opciones que ningún alumno eligió "
                f"({_nombres(sin_elegir)}): esas opciones no funcionan como distractores creíbles.",
            )
        )
    return frases


# ── Entrevistas ────────────────────────────────────────────────────────────────


def _entrevista(estadistica: dict[str, Any]) -> list[dict[str, str]]:
    preguntas = [q for q in estadistica.get("preguntas") or [] if isinstance(q, dict)]
    if preguntas:
        return _entrevista_respuestas(estadistica, preguntas)
    return _entrevista_hablantes(estadistica)


def _entrevista_respuestas(estadistica: dict[str, Any], preguntas: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Frases sobre las RESPUESTAS de los entrevistados (las preguntas son del guion)."""
    n_part = estadistica.get("n_participantes") or 0
    n_resp = estadistica.get("n_respuestas") or 0
    frases = [
        _frase(
            "info",
            f"{n_part} entrevistado{'s' if n_part != 1 else ''} y {len(preguntas)} pregunta{'s' if len(preguntas) != 1 else ''} "
            f"del entrevistador: {n_resp} respuesta{'s' if n_resp != 1 else ''} en total.",
        )
    ]
    media = (estadistica.get("palabras_por_respuesta") or {}).get("media")
    if media is not None:
        if media < 10:
            frases.append(
                _frase(
                    "atencion",
                    f"Las respuestas son cortas ({_n(media, 1)} palabras en promedio): puede haber muchas respuestas de sí/no "
                    "o una transcripción incompleta.",
                )
            )
        else:
            frases.append(_frase("bien", f"Las respuestas tienen {_n(media, 1)} palabras en promedio."))
    sin = sorted((q for q in preguntas if (q.get("sin_respuesta") or 0) > 0), key=lambda q: -(q.get("sin_respuesta") or 0))
    for q in sin[:2]:
        n = q["sin_respuesta"]
        frases.append(
            _frase("atencion", f"«{q.get('pregunta')}: {_corto(q.get('texto') or '', 50)}» quedó sin respuesta en {n} entrevista{'s' if n > 1 else ''}.")
        )
    if not sin and n_part > 1:
        frases.append(_frase("bien", "Todos los entrevistados respondieron todas las preguntas."))
    con_media = [q for q in preguntas if (q.get("palabras") or {}).get("media") is not None]
    if len(con_media) >= 3:
        breve = min(con_media, key=lambda q: q["palabras"]["media"])
        frases.append(
            _frase(
                "info",
                f"Las respuestas más breves son las de «{breve.get('pregunta')}: {_corto(breve.get('texto') or '', 50)}» "
                f"({_n(breve['palabras']['media'], 1)} palabras en promedio).",
            )
        )
    roles = {r.get("rol"): r for r in estadistica.get("palabras_por_rol") or [] if isinstance(r, dict)}
    if "entrevistador" not in roles:
        frases.append(_frase("atencion", "No se identificó al entrevistador: asigna los roles para separar preguntas y respuestas."))
    elif (roles["entrevistador"].get("pct_palabras") or 0) > 0.5:
        frases.append(
            _frase(
                "atencion",
                f"Las preguntas suman el {_pct(roles['entrevistador']['pct_palabras'])} de las palabras: revisa que los roles estén bien asignados.",
            )
        )
    return frases


def _entrevista_hablantes(estadistica: dict[str, Any]) -> list[dict[str, str]]:
    """Reportes anteriores (sin medidas por pregunta): participación por hablante."""
    hablantes = [h for h in estadistica.get("hablantes") or [] if isinstance(h, dict)]
    if not hablantes:
        return []
    frases = []
    turnos = sum(h.get("turnos") or 0 for h in hablantes)
    frases.append(_frase("info", f"{turnos} turnos de palabra entre {len(hablantes)} hablante{'s' if len(hablantes) > 1 else ''}."))

    entrevistador = [h for h in hablantes if h.get("rol") == "entrevistador"]
    entrevistados = [h for h in hablantes if h.get("rol") == "entrevistado"]
    if entrevistador:
        pct = sum(h.get("pct_palabras") or 0 for h in entrevistador)
        if pct > 0.5:
            frases.append(
                _frase(
                    "atencion",
                    f"El entrevistador dice el {_pct(pct)} de las palabras. En una entrevista se espera que hable más el entrevistado; "
                    "revisa que los roles estén bien asignados.",
                )
            )
        else:
            frases.append(_frase("bien", f"El entrevistado lleva la conversación: el entrevistador dice solo el {_pct(pct)} de las palabras."))
    for h in entrevistados[:2]:
        media = (h.get("palabras_por_turno") or {}).get("media")
        if media is not None and media < 10:
            frases.append(
                _frase(
                    "atencion",
                    f"Las respuestas de «{_corto(h.get('nombre', ''), 30)}» son cortas ({_n(media, 1)} palabras por turno en promedio): "
                    "puede haber muchas respuestas de sí/no o una transcripción incompleta.",
                )
            )
    if not entrevistador and len(hablantes) > 1:
        frases.append(_frase("atencion", "No se identificó al entrevistador: asigna los roles para interpretar la participación."))
    return frases
