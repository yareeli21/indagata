"""Anclaje del plan a lo que la pregunta dice literalmente (después de la interpretación, sin LLM).

El modelo de 3B arma bien la forma del plan, pero en la medición del 28 oct (instrumento 127) se equivocó en
detalles que el esquema no puede detectar porque el plan sigue siendo válido:
  - «¿cuántos tienen carga minima…?» → filtro «Carga media/normal» (otra opción real de la misma pregunta);
  - «¿qué respondió R017 en la pregunta 3?» → plan sin el respondente ni la pregunta;
  - «¿y de ellos cuántos están en modalidad en línea?» → un filtro inventado en otra pregunta, sin «En linea», y
    como lista en lugar de conteo.

Este paso corrige el plan con las menciones explícitas de la pregunta, que son inequívocas: IDs de respondente,
números de pregunta, opciones del catálogo escritas tal cual (sin acentos ni mayúsculas) y «cuántos» como conteo.
Lo que el modelo aporta y la pregunta no dice literalmente (sinónimos: «alguna certificación» → «Sí, …») se
conserva si comparte alguna palabra con la pregunta o con el historial; si no, se descarta. Cada cambio queda
anotado en las correcciones del plan.
"""
from __future__ import annotations

import re

from services import enrutador
from services.catalogo import Catalogo
from services.dominio import normalizar
from services.plan_consulta import CondicionContexto, Filtro, Orden, PlanConsulta

_CONTEO = re.compile(r"\b(?:cuantos|cuantas|cuanto|que\s+porcentaje|que\s+tanto\s+por\s+ciento|numero\s+de)\b")
_LISTAR = re.compile(r"\b(?:quienes|cuales|dame|da\s?me|lista|enlista|muestra|muestrame|ids?|identificadores)\b")
_FILTRADO = ("filtrar_respondentes", "conteo_porcentaje")
_RAICES_NO_PREGUNTA = {"tiene", "tenia", "tenga", "hacen", "hicie", "estan", "estab", "fuero", "cuant", "quien",
                       "ellos", "ellas", "tambi", "entre", "mismo"}
# «¿Cuántas personas respondieron la encuesta?», «¿cuántos alumnos presentaron la prueba?»: el total, sin condición.
_TOTAL = re.compile(r"^(?:y\s+)?(?:en\s+total\s+)?cuant[oa]s\s+(?:personas|respondentes|estudiantes|alumn[oa]s|participantes|"
                    r"encuestad[oa]s|entrevistad[oa]s|sujetos)?\s*(?:la\s+|lo\s+)?(?:respondieron|contestaron|participaron|"
                    r"presentaron|hicieron|tiene|hay|son|fueron)(?:\s+(?:en\s+)?(?:la|el|esta|este|esa|ese)\s+"
                    r"(?:encuesta|prueba|entrevista|instrumento|examen|cuestionario)(?:\s+(?:de|del|sobre)\s+(?:(?!\b(?:que|quienes|donde|cuando|cuant[oa]s|pero)\b)[a-z0-9 ]){1,80}?)?)?"
                    r"(?:\s+en\s+total)?$")
_GENERICAS = {"si", "no", "otro", "otra", "ninguno", "ninguna"}
# Niveles del enrutador de reglas → niveles del plan.
_NIVEL_PLAN = {"acuerdo": "acuerdo", "desacuerdo": "desacuerdo", "neutral": "neutral", "satisfaccion": "alto",
               "insatisfaccion": "bajo"}
_POSICION = re.compile(r"\b(primer[oa]?|ultim[oa])\s+(?:respondente|estudiante|alumn[oa]|encuestad[oa]|participante|persona)")
_TODAS = re.compile(r"\btod[oa]s\b")
_POLARES = ("si", "no", "verdadero", "falso")
# Palabras del nombre de una variable de contexto que no la nombran por sí solas («tipo_universidad» → «universidad»).
_VARIABLE_GENERICA = {"tipo", "nivel", "tiene", "numer", "grupo", "dato", "datos"}  # raíces de 5 letras
# «más de 20 horas», «menos de 25 años», «al menos 3 semestres»: comparación sobre un dato de contexto numérico.
_COMPARACION = re.compile(
    r"\b(mas de|mas que|mayor(?:es)? (?:de|a|que)|arriba de|menos de|menos que|menor(?:es)? (?:de|a|que)|"
    r"debajo de|al menos|por lo menos|como minimo|minimo|como maximo|a lo mas|maximo|hasta)\s+(\d+(?:[.,]\d+)?)\s*(\w*)")
_OPERADOR = {"mas": ">", "mayor": ">", "mayores": ">", "arriba": ">", "menos": "<", "menor": "<", "menores": "<",
             "debajo": "<", "al": ">=", "por": ">=", "como minimo": ">=", "minimo": ">=", "como maximo": "<=",
             "a": "<=", "maximo": "<=", "hasta": "<="}
# «sin contar la de la contraseña», «excepto la pregunta 10», «aparte del reactivo de phishing».
_EXCLUSION = re.compile(r"\b(?:sin contar|sin incluir|sin tomar en cuenta|excepto|salvo|aparte de|quitando|"
                        r"excluyendo|dejando fuera)\s+(?:a\s+)?(.{1,60}?)(?=[,;?.]|\s+y\s+|$)")
_RELLENO_EXCLUSION = {"la", "el", "los", "las", "de", "del", "pregunta", "preguntas", "reactivo", "reactivos", "que",
                      "habla", "sobre", "trata", "item"}
# Señales de un ranking de preguntas: «¿en qué pregunta…?», «¿hay alguna donde…?», y el criterio.
_PIDE_PREGUNTA = re.compile(r"\b(?:en )?(?:que|cual|cuales) (?:pregunta|reactivo|item)s?\b|\b(?:hay )?(?:alguna|algun) "
                            r"(?:pregunta |reactivo )?(?:donde|en la que|en el que)\b|\b(?:pregunta|reactivo)s? (?:con|donde) (?:mas|menos)\b")
_CRITERIOS_RANKING = (
    ("no_respuesta", re.compile(r"\b(?:nulas?|sin (?:contestar|responder|respuesta)|no respuesta|en blanco|"
                                r"vacias?|omitid\w*|no contestad\w*|no respondid\w*)\b")),
    ("coincidencia", re.compile(r"\b(?:casi todos|coincid\w*|lo mismo|la misma|unanim\w*|consenso)\b")),
    ("repartida", re.compile(r"\b(?:dividid\w*|repartid\w*|dispers\w*|polarizad\w*)\b")),
    # «¿Qué pregunta tuvo respuestas más negativas?» se volvía «repartida» y mostraba el «De acuerdo» de cada una
    # (26 nov). Lo negativo va antes: «desacuerdo» contiene «acuerdo».
    ("negativa", re.compile(r"\b(?:mas negativ\w*|peor(?:es)? (?:evaluad|calificad|valorad|opinion)\w*|"
                            r"mas (?:respuestas? )?(?:en )?desacuerdo|menos (?:respuestas? )?(?:de )?acuerdo|"
                            r"mas (?:respuestas? )?insatisf\w*)\b")),
    ("positiva", re.compile(r"\b(?:mas positiv\w*|mejor(?:es)? (?:evaluad|calificad|valorad|opinion)\w*|"
                            r"mas (?:respuestas? )?(?:de )?acuerdo|mas (?:respuestas? )?satisf\w*)\b")),
)
# «¿cuántos mencionaron la ansiedad?», «¿quiénes hablaron del estrés?»: menciones de un tema en respuestas abiertas.
_MENCION = re.compile(r"\b(?:mencion\w*|nombr(?:an|aron|a|o)|habl(?:an|aron|a|o) (?:de|del|sobre|acerca de)|"
                      r"(?:dijeron|dicen|dijo|dice) algo (?:de|del|sobre|acerca de)|se refier\w* a|se refirieron a|"
                      r"comentaron (?:sobre|de|del))\s+(.{1,60}?)(?=[,;?.]|\s+y\s+|\s+en\s+(?:la|el|las|los|sus)\s+|$)")
_RELLENO_MENCION = {"la", "el", "los", "las", "lo", "un", "una", "algo", "de", "del", "al", "a", "sobre", "su", "sus",
                    "tema", "temas", "que", "alguna", "algun", "vez"}
_SEGUIMIENTO = re.compile(r"\b(?:de|entre) (?:ellos|ellas|esos|esas|estos|estas)\b")


def _menciona(texto: str, opcion: str) -> bool:
    n = normalizar(opcion).strip(" .")
    return len(n) >= 4 and n not in _GENERICAS and re.search(rf"(?<![a-z0-9]){re.escape(n)}(?![a-z0-9])", texto) is not None


def _opciones_mencionadas(texto: str, cat: Catalogo) -> dict[str, list[str]]:
    """{pregunta: opciones escritas tal cual en la consulta}, solo opciones que pertenecen a UNA pregunta."""
    por_opcion: dict[str, set[str]] = {}
    for pid, p in cat.preguntas.items():
        for o in p.opciones:
            if _menciona(texto, o):
                por_opcion.setdefault(o, set()).add(pid)
    salida: dict[str, list[str]] = {}
    for o, pids in por_opcion.items():
        if len(pids) == 1:
            salida.setdefault(next(iter(pids)), []).append(o)
    # «Trabajo más de 30h» contiene «30h»: se queda la opción más larga de cada pregunta si una contiene a otra.
    for pid, ops in salida.items():
        salida[pid] = [o for o in ops if not any(o != x and normalizar(o) in normalizar(x) for x in ops)]
    return salida


def _valor_de_un_reactivo(texto: str, var: str, valor: str, cat: Catalogo) -> bool:
    """¿La palabra del valor de contexto está ahí porque la consulta cita un reactivo que la contiene, y no nombra la
    variable? «¿cuántos piensan que usar Wi-Fi pública sin VPN es seguro?» citaba el reactivo y se filtraba por
    tipo_universidad = «publica» (Fase 6, consultas 1490 y 1526); «¿cuántos de universidad pública…?» sí la nombra."""
    raices = enrutador._raices(texto)
    nombre = {r for r in enrutador._raices(var.replace("_", " ")) if r not in _VARIABLE_GENERICA}
    if raices & nombre:
        return False
    del_valor = enrutador._raices(valor)  # raíz: el reactivo dice «públicas» y la consulta «pública»
    return bool(del_valor) and any(del_valor <= enrutador._raices(p.texto)
                                   and len((raices - del_valor) & enrutador._raices(p.texto)) >= 2
                                   for p in cat.preguntas.values())


def _comparaciones_de_contexto(texto: str, cat: Catalogo) -> list[CondicionContexto]:
    """«¿cuántos trabajan más de 20 horas a la semana?» → horas_trabajo_semana > 20, si la consulta nombra la variable
    («horas», «trabajan», «semana» comparten raíz con su nombre). Sin nombrarla («más de 20») no se adivina."""
    if not cat.numericas:
        return []
    raices = enrutador._raices(texto)
    salida = []
    for m in _COMPARACION.finditer(texto):
        frase = m.group(1)
        op = _OPERADOR.get(frase) or _OPERADOR.get(frase.split(" ")[0], ">")
        # La variable con más palabras en común con la consulta (la palabra junto al número cuenta doble).
        junto = enrutador._raices(m.group(3))
        puntajes = []
        for var in cat.numericas:
            nombre = {r for r in enrutador._raices(var.replace("_", " ")) if r not in _VARIABLE_GENERICA}
            puntajes.append((len(nombre & raices) + len(nombre & junto), var))
        mejor, var = max(puntajes)
        empatadas = [v for pt, v in puntajes if pt == mejor]
        if mejor and len(empatadas) == 1:
            salida.append(CondicionContexto(variable=var, op=op, valor=float(m.group(2).replace(",", "."))))
    return salida


def _excluidas(texto: str, cat: Catalogo) -> list[str]:
    """IDs de las preguntas que la consulta pide no contar. Cada exclusión se resuelve por un número («excepto la
    pregunta 10») o por una palabra que aparece en UNA sola pregunta («la de la contraseña» → r10); si la palabra
    está en varias o en ninguna, no se adivina."""
    salida = []
    for m in _EXCLUSION.finditer(texto):
        frase = m.group(1)
        pids = [pid for n in enrutador._preguntas(frase) if (pid := _id_pregunta(cat, n))]
        if not pids:
            for palabra in (w for w in re.findall(r"[a-z]+", frase) if len(w) >= 4 and w not in _RELLENO_EXCLUSION):
                base = palabra[:-1] if palabra.endswith("s") and len(palabra) > 5 else palabra
                candidatas = [pid for pid, q in cat.preguntas.items()
                              if re.search(rf"\b{re.escape(base)}", normalizar(q.texto))]
                if len(candidatas) == 1:
                    pids = candidatas
                    break
        salida += [pid for pid in pids if pid not in salida]
    return salida


def sin_inventos(plan: PlanConsulta, pregunta: str, historial: list[tuple[str, str]],
                 catalogos: list[Catalogo] | None = None) -> tuple[PlanConsulta, list[str]]:
    """Quita del plan, ANTES de validarlo, las condiciones de contexto y la mención que ni la pregunta ni lo que el
    usuario preguntó antes dicen. Con el contexto visible en el catálogo y los campos nuevos, el modelo inventó
    «Trabaja = sí» (1548), copió «Edad > 25» del ejemplo del prompt (1556) y buscó la mención «detenerse» (1551).
    Con los `catalogos`, también los filtros que la validación volvería una aclaración (`_filtros_sin_inventos`)."""
    texto = normalizar(pregunta)
    previas = normalizar(" ".join(t for rol, t in historial[-4:] if rol == "usuario"))
    raices = enrutador._raices(texto) | enrutador._raices(previas)

    def dicho(*partes: str) -> bool:
        return any({r for r in enrutador._raices(p.replace("_", " ")) if r not in _VARIABLE_GENERICA} & raices
                   for p in partes)

    cambios: dict = {}
    notas: list[str] = []
    contexto = {k: v for k, v in plan.contexto.items() if dicho(k, str(v))}
    if contexto != plan.contexto:
        cambios["contexto"] = contexto
        notas += [f"contexto {k} = «{v}» descartado (la pregunta no lo menciona)" for k, v in plan.contexto.items()
                  if k not in contexto]
    numericas = [c for c in plan.contexto_num if dicho(c.variable)]
    if numericas != plan.contexto_num:
        cambios["contexto_num"] = numericas
        notas += [f"contexto {c.variable} {c.op} {c.valor:g} descartado (la pregunta no lo menciona)"
                  for c in plan.contexto_num if c not in numericas]
    if plan.menciona and not (_termino_mencionado(texto) or _termino_mencionado(previas)):
        cambios["menciona"] = ""
        notas.append(f"mención «{plan.menciona}» descartada (la pregunta no pregunta quién lo mencionó)")
    if catalogos and plan.filtros:
        cat = next((c for c in catalogos if c.id in plan.instrumentos), catalogos[0])
        _filtros_sin_inventos(plan, cat, raices, dicho, cambios, notas)
        if not cambios.get("filtros", plan.filtros) and not cambios.get("contexto", plan.contexto) \
                and not cambios.get("contexto_num", plan.contexto_num) and not cambios.get("preguntas", plan.preguntas):
            # Pedía una condición y ninguna se sostiene: se pregunta en lugar de contar a todos («¿cuántos estudian
            # ingeniería?» en una prueba sin carrera, consulta 1612).
            notas.append("ninguna condición respaldada: se pide aclaración")
            return _aclarar_condicion(plan, texto, cat), notas
    return (plan.model_copy(update=cambios) if cambios else plan), notas


_VERDADEROS = {"true", "si", "verdadero"}
_FALSOS = {"false", "no", "falso"}


def _variable_de_contexto(nombre: str, cat: Catalogo) -> str | None:
    """La variable de contexto que el modelo puso como si fuera una pregunta («primera_generacion»)."""
    if nombre in cat.preguntas:
        return None
    clave = normalizar(nombre).replace(" ", "_")
    return next((v for v in (*cat.contexto, *cat.numericas) if normalizar(v).replace(" ", "_") == clave), None)


def _booleano(valores: list[str], verdadero: bool) -> str | None:
    """El valor del catálogo que dice sí o no en una variable de sí/no («True»/«False», «Sí»/«No»)."""
    buscados = _VERDADEROS if verdadero else _FALSOS
    return next((v for v in valores if normalizar(v) in buscados), None)


def _es_opcion(valor: str, opciones: list[str]) -> bool:
    """¿El valor es (parte de) una opción de la pregunta? Una letra sola («A») no lo es: la validación la rechaza."""
    v = normalizar(valor).strip(" .)")
    return v.split(" ")[0] in (*_POLARES, "true", "false") or (
        len(v) >= 3 and any(v in normalizar(o) or normalizar(o).split(") ", 1)[-1] in v for o in opciones))


def _filtros_sin_inventos(plan: PlanConsulta, cat: Catalogo, raices: set[str], dicho, cambios: dict,  # noqa: ANN001
                          notas: list[str]) -> None:
    """Filtros que la validación volvía una aclaración absurda antes de que el anclaje los revisara (Fase 6):
    - un dato de contexto puesto como pregunta («horas_trabajo_semana > 20», «primera_generacion = sí»; consultas
      1583 y 1594: «No encontré la pregunta "horas_trabajo_semana"») pasa al contexto;
    - un valor que no es opción de la pregunta y que la consulta no dice («A)» en r01 para «¿cuántos estudian
      ingeniería?», 1612) se descarta;
    - un valor que son palabras del enunciado del reactivo («Big Data» en r22, cuyo texto es «… Big Data ↔», 1617) se
      descarta y el reactivo queda como la pregunta de la que se habla."""
    filtros: list[Filtro] = []
    contexto = dict(cambios.get("contexto", plan.contexto))
    numericas = list(cambios.get("contexto_num", plan.contexto_num))
    preguntas = list(plan.preguntas)
    for f in plan.filtros:
        valores = [str(v) for v in _valores(f)]
        if var := _variable_de_contexto(f.pregunta, cat):
            if not dicho(var, *valores):
                notas.append(f"filtro {f.pregunta} = «{f.valor}» descartado (la pregunta no lo menciona)")
            elif var in cat.numericas and isinstance(f.valor, (int, float)) and f.op in ("=", ">", "<", ">=", "<="):
                numericas.append(CondicionContexto(variable=var, op=f.op, valor=float(f.valor)))
                notas.append(f"filtro {f.pregunta} {f.op} {f.valor:g} → contexto numérico (es un dato de contexto)")
            elif var in cat.contexto and (valor := next(
                    (v for v in cat.contexto[var] if valores and normalizar(v) == normalizar(valores[0])), None)
                    or (_booleano(cat.contexto[var], normalizar(valores[0]) in _VERDADEROS) if valores
                        and normalizar(valores[0]) in _VERDADEROS | _FALSOS else None)):
                contexto[var] = valor
                notas.append(f"filtro {f.pregunta} = «{f.valor}» → contexto {var} = «{valor}» (es un dato de contexto)")
            else:
                notas.append(f"filtro {f.pregunta} = «{f.valor}» descartado (dato de contexto sin valor reconocible)")
            continue
        p = cat.preguntas.get(f.pregunta)
        if p is None or f.nivel is not None or isinstance(f.valor, (int, float)) or not valores \
                or all(_es_opcion(v, p.opciones) for v in valores):
            filtros.append(f)  # la validación decide (pregunta inexistente, nivel, número u opción reconocible)
            continue
        del_reactivo = enrutador._raices(p.texto)
        del_valor = set().union(*(enrutador._raices(v) for v in valores))
        if del_valor and del_valor <= del_reactivo and del_valor & raices:
            notas.append(f"filtro {f.pregunta} = «{f.valor}» descartado (son palabras del enunciado, no una opción)")
            if f.pregunta not in preguntas:
                preguntas.append(f.pregunta)
        elif del_valor & raices:
            filtros.append(f)  # la consulta sí dice ese valor: la validación pregunta cuál opción es
        else:
            notas.append(f"filtro {f.pregunta} = «{f.valor}» descartado (no es una opción y la pregunta no lo menciona)")
    if filtros != list(plan.filtros):
        cambios["filtros"] = filtros
    if contexto != plan.contexto:
        cambios["contexto"] = contexto
    if numericas != list(plan.contexto_num):
        cambios["contexto_num"] = numericas
    if preguntas != list(plan.preguntas):
        cambios["preguntas"] = preguntas


def acotar(plan: PlanConsulta, pregunta: str, cat: Catalogo, n_catalogos: int) -> tuple[PlanConsulta, list[str]]:
    """Último paso, con el plan ya validado y anclado (26 nov; lo destapó el manifiesto reparado, cuando el ejecutor
    volvió a correr en todo el acervo):
      * un conteo SIN ninguna condición es el total de respondentes: solo si la pregunta pide el total. «¿Cuántos
        consumen alcohol o tabaco?» (nada lo mide; la condición se descartó) respondía «el instrumento tiene 90
        respondentes» en diez instrumentos. Pasa a la ruta semántica, que dice «sin información» si nada lo trata;
      * los IDs de pregunta, filtro o respondente se validaron contra UN catálogo (`cat`): con varios instrumentos
        sin `instrumentos` en el plan, «p06» se calculaba en todos (p06 de una encuesta sobre aulas y p06 de una
        entrevista sobre inclusión). Se ejecuta solo en ese catálogo."""
    notas: list[str] = []
    sin_condicion = not (plan.filtros or plan.preguntas or plan.nivel or plan.contexto or plan.contexto_num
                         or plan.menciona or plan.agrupar_por or plan.respondentes)
    if plan.intencion == "conteo_porcentaje" and sin_condicion and not _TOTAL.match(normalizar(pregunta).strip(" ?¿.!")):
        notas.append("conteo sin condición y la pregunta no pide el total → búsqueda semántica")
        return plan.model_copy(update={"intencion": "semantica_abierta", "consulta_semantica": pregunta}), notas
    nombra_ids = bool(plan.preguntas or plan.filtros or plan.respondentes)
    if nombra_ids and not plan.instrumentos and n_catalogos > 1:
        notas.append(f"preguntas o respondentes de «{cat.titulo}»: el cálculo se hace solo en ese instrumento")
        plan = plan.model_copy(update={"instrumentos": [cat.id]})
    return plan, notas


def _termino_mencionado(texto: str) -> str:
    """El tema de «mencionaron la ansiedad» / «hablaron del estrés», sin artículos («ansiedad», «estres»)."""
    m = _MENCION.search(texto)
    if not m:
        return ""
    palabras = [w for w in re.findall(r"[a-z0-9]+", m.group(1)) if w not in _RELLENO_MENCION]
    return " ".join(palabras[:3])


def _criterio_ranking(texto: str) -> str | None:
    return next((c for c, patron in _CRITERIOS_RANKING if patron.search(texto)), None)


def _id_pregunta(cat: Catalogo, numero: int) -> str | None:
    return next((pid for pid in cat.preguntas if re.fullmatch(rf"[a-z]+0*{numero}", pid)), None)


def anclar(plan: PlanConsulta, pregunta: str, historial: list[tuple[str, str]], cat: Catalogo) -> tuple[PlanConsulta, list[str]]:
    """El plan corregido con las menciones explícitas de la pregunta, y las correcciones aplicadas."""
    texto = normalizar(pregunta)
    notas: list[str] = []
    cambios: dict = {}
    intencion = plan.intencion

    # 00. El total de participantes: el plan del modelo variaba con las pistas del RAG y llegó a contestar el % de
    # acuerdo de una pregunta (26 nov). Sin condición escrita, es un conteo sin filtros («El instrumento tiene N»).
    if _TOTAL.match(texto.strip(" ?¿.!")):
        if intencion != "conteo_porcentaje" or plan.filtros or plan.preguntas or plan.nivel or plan.contexto \
                or plan.contexto_num or plan.menciona:
            notas.append(f"intención {intencion} → conteo_porcentaje sin condiciones: la pregunta pide el total")
        return plan.model_copy(update={"intencion": "conteo_porcentaje", "filtros": [], "preguntas": [], "nivel": None,
                                       "contexto": {}, "contexto_num": [], "agrupar_por": None, "respondentes": [],
                                       "aclaracion": "", "consulta_semantica": "", "menciona": "", "orden": None,
                                       "limite": None}), notas
    # 0. Ranking de preguntas («¿en qué pregunta hubo más nulas, sin contar la de la contraseña?»): el plan solo tenía
    # el hallazgo, que da UNA pregunta y no permite excluir (Fase 6, consultas 1493, 1498 y 1529). Se revisa también
    # una aclaración: en 1529 el modelo filtró «A» en r10 y la validación lo volvió una pregunta absurda.
    criterio = _criterio_ranking(texto)
    if criterio in ("negativa", "positiva") and cat.tipo == "prueba_estandarizada":
        criterio = None  # los reactivos no tienen niveles de acuerdo: sin clave, no hay respuestas «negativas»
    if criterio and _PIDE_PREGUNTA.search(texto) and not enrutador._persona(texto) \
            and intencion in ("hallazgo", "resumen_pregunta", "semantica_abierta", "conteo_porcentaje", "aclaracion",
                              "ranking_preguntas"):
        if intencion != "ranking_preguntas":
            notas.append(f"intención {intencion} → ranking_preguntas («{criterio}» por pregunta)")
            intencion = "ranking_preguntas"
            cambios.update(preguntas=[], filtros=[], nivel=None, aclaracion="")
        if plan.criterio_ranking != criterio:
            cambios["criterio_ranking"] = criterio
            notas.append(f"criterio del ranking: {criterio} (lo que dice la pregunta)")
    # 0b. Menciones de un tema en las respuestas abiertas, si la consulta pide cuántos o quiénes: no hay resumen ni
    # nivel que las cuente (Fase 6: «0 de 1 en nivel alto» en 1468, «sin resumen calculado» en 1540).
    termino = _termino_mencionado(texto)
    if termino and (_CONTEO.search(texto) or _LISTAR.search(texto)) \
            and intencion in ("hallazgo", "resumen_pregunta", "semantica_abierta", "aclaracion", *_FILTRADO):
        nueva = "filtrar_respondentes" if _LISTAR.search(texto) and not _CONTEO.search(texto) else "conteo_porcentaje"
        numeradas = [pid for n in enrutador._preguntas(texto) if (pid := _id_pregunta(cat, n))]
        cambios.update(intencion=nueva, menciona=termino, preguntas=numeradas, filtros=[], nivel=None, aclaracion="",
                       consulta_semantica="")
        notas.append((f"intención {intencion} → {nueva}: " if nueva != intencion else "")
                     + f"menciones de «{termino}» en las respuestas abiertas")
        return plan.model_copy(update=cambios), notas
    # 0c. «¿Cuántos…?» sobre una pregunta que la consulta señala sin ambigüedad: plan por el tipo de la pregunta.
    # Solo si el modelo no armó condiciones: un conteo con filtros del modelo lo revisan los pasos de abajo. Un conteo
    # que solo nombra la pregunta («¿cuántos reprueban materias?» → p01, sin condición) daba su resumen (24 nov, 351).
    sin_condiciones = intencion in ("hallazgo", "resumen_pregunta", "semantica_abierta", "aclaracion") or (
        intencion in _FILTRADO and not plan.filtros and not plan.nivel)
    if _CONTEO.search(texto) and not enrutador._persona(texto) and not _LISTAR.search(texto) and sin_condiciones \
            and (directo := _conteo_por_pregunta(texto, plan, cat)) is not None:
        nuevo, nota = directo
        notas.append(f"intención {intencion} → {nuevo['intencion']}: {nota}" if nuevo["intencion"] != intencion else nota)
        plan = plan.model_copy(update={"filtros": [], "preguntas": [], "nivel": None, "contexto": {}, "contexto_num": [],
                                       "agrupar_por": None, "respondentes": [], "aclaracion": "", "consulta_semantica": "",
                                       "menciona": "", "orden": None, "limite": None, **nuevo})
        intencion = plan.intencion
    elif _CONTEO.search(texto) and not enrutador._persona(texto) and intencion in ("hallazgo", "semantica_abierta") \
            and not plan.preguntas and not plan.filtros:
        # «¿Cuántos tienen dificultades socioeconómicas?», «¿cuántos trabajan más de 30 horas?»: la condición es un
        # dato de la persona, no una pregunta. Si la consulta lo escribe, es un conteo (los pasos 3 lo agregan).
        grupo = _grupo_contenido(texto, cat)
        if grupo or _comparaciones_de_contexto(texto, cat) or _si_no_nombrada(texto, cat):
            notas.append(f"intención {intencion} → conteo_porcentaje: la condición es un dato de contexto")
            plan = plan.model_copy(update={"intencion": "conteo_porcentaje", "contexto": dict([grupo]) if grupo else {},
                                           "contexto_num": [], "aclaracion": "", "consulta_semantica": ""})
            intencion = plan.intencion
            if grupo:
                notas.append(f"contexto {grupo[0]} = «{grupo[1]}» (escrito en la pregunta)")
    # 0d. «¿Cuántos intentos hicieron los hombres y cuántos las mujeres?»: dos grupos de una misma variable se
    # comparan; antes se tomaba solo el primero (22 nov, consultas 321 y 339).
    dos = _grupos_de_una_variable(texto, cat) if not enrutador._persona(texto) else None
    if dos and intencion in ("hallazgo", "resumen_pregunta", "semantica_abierta", *_FILTRADO):
        var, escritos = dos
        notas.append(f"intención {intencion} → comparar_grupos por {var} (la pregunta nombra {', '.join(escritos)})")
        plan = plan.model_copy(update={"intencion": "comparar_grupos", "agrupar_por": var, "aclaracion": "",
                                       "contexto": {k: v for k, v in plan.contexto.items() if k != var},
                                       "consulta_semantica": "", "orden": None, "limite": None})
        intencion = plan.intencion
    # 0e. «¿Hay inseguridad en la escuela?»: el modelo eligió «hallazgo» (datos notables de cualquier pregunta) para una
    # consulta que nombra sin ambigüedad una pregunta del instrumento (24 nov, consultas 348 y 350): se da la pregunta
    # (de opciones o numérica: su distribución; abierta: todas sus respuestas, agrupadas). En una encuesta, la búsqueda
    # semántica sobre una pregunta abierta solo traía el fragmento de resumen («50 respuestas abiertas», sin textos) y el
    # modelo inventó «98 % no ha sufrido inseguridad» (consulta 344): también pasa a sus respuestas.
    revisar = intencion == "hallazgo" or (intencion == "semantica_abierta" and cat.tipo == "encuesta")
    aludidas = _preguntas_aludidas(texto, cat) if revisar and not enrutador._persona(texto) else []
    if len(aludidas) == 1 and (intencion == "hallazgo" or not cat.preguntas[aludidas[0][0]].opciones):
        pid = aludidas[0][0]
        tipo = "de opciones" if cat.preguntas[pid].opciones else "abierta: todas sus respuestas"
        notas.append(f"intención {intencion} → resumen_pregunta de {pid} (la consulta trata de esa pregunta; {tipo})")
        plan = plan.model_copy(update={"intencion": "resumen_pregunta", "preguntas": [pid], "filtros": [],
                                       "consulta_semantica": ""})
        intencion = plan.intencion
    if intencion in ("fuera_de_dominio", "uso_plataforma", "metodologia", "aclaracion"):
        return plan, []
    excluidas = _excluidas(texto, cat)
    if excluidas and set(excluidas) != set(plan.excluir_preguntas):
        cambios["excluir_preguntas"] = list(dict.fromkeys([*plan.excluir_preguntas, *excluidas]))
        notas.append(f"sin contar {', '.join(excluidas)} (lo pide la pregunta)")
    if intencion == "ranking_preguntas":
        if intencion != plan.intencion:
            cambios["intencion"] = intencion
        return plan.model_copy(update=cambios), notas
    nivel = _NIVEL_PLAN.get(enrutador._nivel(texto) or "")

    # 1. Respondente nombrado por su ID («R017», «r-17»), o por su posición («el primero», «el último»).
    persona = enrutador._persona(texto)
    if persona:
        rid = enrutador._id_persona(persona)
        if rid in cat.respondentes and rid not in plan.respondentes:
            cambios.update(respondentes=[rid], orden=None, limite=None)
            if intencion not in ("datos_respondente",):
                notas.append(f"intención {intencion} → datos_respondente («{rid}» en la pregunta)")
                intencion = "datos_respondente"
            notas.append(f"respondente {rid} tomado de la pregunta")
    elif intencion == "datos_respondente" and not plan.respondentes and (m := _POSICION.search(texto)):
        direccion = "desc" if m.group(1).startswith("ultim") else "asc"
        if not plan.orden or plan.orden.dir != direccion or not plan.limite:
            cambios.update(orden=Orden(dir=direccion), limite=plan.limite or 1)
            notas.append(f"orden {direccion} por número de respondente («{m.group(1)}» en la pregunta)")

    # 2. Preguntas nombradas por su número («pregunta 3», «p03»).
    pids = [pid for n in enrutador._preguntas(texto) if (pid := _id_pregunta(cat, n))]
    if pids:
        if intencion == "datos_respondente":
            # «en la pregunta 1» manda sobre «todas las respuestas» salvo que la pregunta pida todas (regresión C27).
            if plan.campos != pids and not _TODAS.search(texto):
                cambios["campos"] = pids
                notas.append(f"campos {', '.join(pids)} tomados de la pregunta")
        elif intencion == "resumen_pregunta" and plan.preguntas != pids:
            # «¿Qué opción eligieron más en el reactivo 5?»: el modelo puso r09 y la suma daba dos tablas (26 nov).
            # En un resumen, las nombradas por número son las preguntas.
            cambios["preguntas"] = pids
            notas.append(f"preguntas {', '.join(pids)} tomadas de la pregunta (en lugar de {', '.join(plan.preguntas) or 'ninguna'})")
        elif not set(pids) <= set(plan.preguntas):
            cambios["preguntas"] = list(dict.fromkeys([*plan.preguntas, *pids]))
            notas.append(f"preguntas {', '.join(pids)} tomadas de la pregunta")

    # 3. Grupo de contexto escrito tal cual («del turno vespertino» → {turno: Vespertino}).
    if not plan.contexto and intencion in (*_FILTRADO, "comparar_grupos", "resumen_pregunta"):
        for var, valores in cat.contexto.items():
            if var == plan.agrupar_por:
                continue
            valor = next((v for v in valores if len(v) >= 3 and not v.isdigit() and _menciona_grupo(texto, v)), None)
            if valor and _valor_de_un_reactivo(texto, var, valor, cat):
                notas.append(f"contexto {var} = «{valor}» no se toma («{valor}» es parte del reactivo citado)")
                continue
            if valor:
                cambios["contexto"] = {var: valor}
                notas.append(f"contexto {var} = «{valor}» (escrito en la pregunta)")
                break

    # 3c. Variable de sí/no nombrada («los de primera generación», «los que no tienen beca»): su valor no se escribe,
    # se deduce del nombre y de una negación justo antes (Fase 6, consultas 1594 y 1617).
    if not cambios.get("contexto", plan.contexto) and intencion in (*_FILTRADO, "comparar_grupos", "resumen_pregunta"):
        for var, valores in cat.contexto.items():
            nombre = [t[:5] for t in re.findall(r"[a-z]+", normalizar(var.replace("_", " ")))  # en orden
                      if len(t) >= 4 and t[:5] not in _VARIABLE_GENERICA]
            if var == plan.agrupar_por or not nombre or not all(normalizar(v) in _VERDADEROS | _FALSOS for v in valores):
                continue
            if not (m := re.search(r"\b" + r"\w*\s+(?:\w+\s+)?".join(map(re.escape, nombre)), texto)):
                continue
            negada = re.search(r"\b(?:no|sin|ni)\s+(?:\w+\s+){0,2}$", texto[:m.start()]) is not None
            if valor := _booleano(valores, not negada):
                cambios["contexto"] = {var: valor}
                notas.append(f"contexto {var} = «{valor}» (la pregunta nombra la variable)")
                break

    # 3a. Comparación numérica del modelo cuyo número no escribió nadie: «¿cuántos reprobaron al menos una materia el
    # semestre anterior?» se contaba con «Semestre actual > 1» inventado (21 nov, consulta 312).
    previas_num = " ".join(normalizar(t) for rol, t in historial[-4:] if rol == "usuario")
    leidas = {c.variable for c in _comparaciones_de_contexto(f"{texto} {previas_num}", cat)}
    actuales = cambios.get("contexto_num", plan.contexto_num)
    inventadas = [c for c in actuales
                  if c.variable not in leidas and not _numero_junto_a(c, f"{texto} {previas_num}")]
    if inventadas:
        cambios["contexto_num"] = [c for c in actuales if c not in inventadas]
        notas += [f"contexto {c.variable} {c.op} {c.valor:g} descartado (ese número no está en la pregunta)"
                  for c in inventadas]
    # 3b. Comparación sobre un dato de contexto numérico («más de 20 horas»), si el modelo no la puso.
    comparaciones = []
    if intencion in (*_FILTRADO, "comparar_grupos", "resumen_pregunta"):
        comparaciones = [c for c in _comparaciones_de_contexto(texto, cat)
                         if not any(x.variable == c.variable for x in plan.contexto_num)]
        if comparaciones:
            cambios["contexto_num"] = [*plan.contexto_num, *comparaciones]
            notas += [f"contexto {c.variable} {c.op} {c.valor:g} (escrito en la pregunta)" for c in comparaciones]

    # 4. Nivel de la escala («de acuerdo», «en desacuerdo») en comparaciones y porcentajes de una pregunta.
    preguntas_plan = cambios.get("preguntas", plan.preguntas)
    if nivel and not plan.nivel and preguntas_plan and intencion in ("comparar_grupos", "conteo_porcentaje"):
        cambios["nivel"] = nivel
        notas.append(f"nivel {nivel} tomado de la pregunta")

    # 5. Filtros: opciones escritas tal cual, polaridad «sí/no», nivel y respaldo de la pregunta.
    if intencion in _FILTRADO:
        filtros = list(plan.filtros)
        for pid, ops in _opciones_mencionadas(texto, cat).items():
            valor: str | list[str] = ops[0] if len(ops) == 1 else ops
            actual = next((f for f in filtros if f.pregunta == pid), None)
            if actual is None:
                filtros.append(Filtro(pregunta=pid, op="=", valor=valor))
                notas.append(f"filtro {pid} = «{', '.join(ops)}» (escrito en la pregunta)")
            elif actual.nivel is None and not any(_menciona(texto, str(v)) for v in _valores(actual)):
                filtros[filtros.index(actual)] = Filtro(pregunta=pid, op=actual.op, valor=valor)
                notas.append(f"filtro {pid}: «{actual.valor}» → «{', '.join(ops)}» (lo que dice la pregunta)")
        filtros = [_ajustar_filtro(f, texto, nivel, cat, notas) for f in filtros]
        # El número de «más de 20 horas» ya es la condición de contexto: un filtro numérico con ese número en una
        # pregunta que no habla de eso es la misma condición mal ubicada (gemma: «r04 > 20», consulta 1486).
        for c in comparaciones:
            for f in [f for f in filtros if isinstance(f.valor, (int, float)) and float(f.valor) == c.valor]:
                texto_p = cat.preguntas[f.pregunta].texto if f.pregunta in cat.preguntas else ""
                if len(enrutador._raices(texto) & enrutador._raices(texto_p)) < 2:
                    filtros.remove(f)
                    notas.append(f"filtro {f.pregunta} {f.op} {f.valor:g} → contexto {c.variable}")
        # Seguimiento («¿y de ellos…?»): las condiciones de la pregunta anterior se heredan aunque el modelo las
        # olvide (regresión C06: contó a todos los de «en línea» y no a los de carga mínima con certificación).
        if _SEGUIMIENTO.search(texto):
            previa = next((normalizar(t) for rol, t in reversed(historial) if rol == "usuario"), "")
            for f in _condiciones_de(previa, cat):
                if not any(x.pregunta == f.pregunta for x in filtros):
                    filtros.append(f)
                    notas.append(f"filtro {f.pregunta} heredado de la pregunta anterior")
        # Filtros que la pregunta no respalda: ni su valor ni su pregunta comparten palabras con la consulta ni
        # con lo que el usuario preguntó antes (las preguntas de seguimiento heredan sus condiciones).
        previas = " ".join(t for rol, t in historial[-4:] if rol == "usuario")
        # Sin verbos genéricos: «¿cuántos tienen beca?» respaldaba p11 («¿Tienes experiencia laboral…?») por «tiene»
        # (26 nov).
        raices = ((enrutador._raices(texto) | enrutador._raices(previas))
                  - {v[:5] for v in enrutador._VERBOS_CONSULTA} - _RAICES_NO_PREGUNTA)
        respaldados = []
        for f in filtros:
            texto_p = cat.preguntas[f.pregunta].texto if f.pregunta in cat.preguntas else ""
            valores = [str(v) for v in _valores(f)]
            del_valor = (any(raices & enrutador._raices(v) for v in valores)
                         or any(_menciona(normalizar(previas), v) for v in valores))
            # Una opción concreta (ni nivel, ni número, ni «Sí…»/«No…», ni «Verdadero»/«Falso») solo se sostiene si la
            # consulta dice algo de ella: con «¿cuántos estudian en modalidad nocturna?» el modelo filtró «Presencial»
            # (la pregunta de la modalidad comparte «modalidad») y la redacción contó 1251 «en modalidad nocturna»
            # (regresión C13). En un reactivo de verdadero o falso, «¿cuántos piensan que [enunciado]?» es «Verdadero»
            # aunque no lo escriba: basta con que cite el enunciado (Fase 6, consultas 1490 y 1526).
            opcion_concreta = (f.nivel is None and not isinstance(f.valor, (int, float)) and valores
                               and not all(normalizar(v).split(" ")[0].strip(",.") in _POLARES for v in valores))
            if del_valor or (not opcion_concreta and raices & enrutador._raices(texto_p)):
                respaldados.append(f)
            else:
                notas.append(f"filtro {f.pregunta} = «{f.valor}» descartado (la pregunta no lo menciona)")
        if respaldados != list(plan.filtros):
            cambios["filtros"] = respaldados
        # Un nivel sin pregunta no significa nada (el modelo lo agregó junto a un filtro, regresión C08).
        if plan.nivel and not preguntas_plan:
            cambios["nivel"] = None
            notas.append(f"nivel {plan.nivel} sin pregunta: se quita")
        # Si la consulta pedía una condición y ninguna se sostiene, se pregunta en lugar de contar a todos
        # («¿cuántos estudian en modalidad nocturna?», regresión C13).
        if plan.filtros and not respaldados and not preguntas_plan and not cambios.get("contexto", plan.contexto) \
                and not cambios.get("contexto_num", plan.contexto_num):
            return _aclarar_condicion(plan, texto, cat), notas + ["ninguna condición respaldada: se pide aclaración"]

    # 6. «¿Cuántos…?» sin pedir quiénes: es un conteo, no una lista.
    if intencion == "filtrar_respondentes" and _CONTEO.search(texto) and not _LISTAR.search(texto) \
            and plan.campos != "todas_las_respuestas":
        notas.append("intención filtrar_respondentes → conteo_porcentaje («cuántos» sin pedir quiénes)")
        intencion = "conteo_porcentaje"
        cambios.update(limite=None, orden=None, campos="solo_ids")

    if intencion != plan.intencion:
        cambios["intencion"] = intencion
    return (plan.model_copy(update=cambios) if cambios else plan), notas


# ── Conteos por el tipo de la pregunta (21 nov) ──────────────────────────────────────────────────────────────────
# El modelo de 3B contestaba «¿cuántos practican actividades extracurriculares?» con un hallazgo de otra pregunta,
# daba la media en «¿cuántos reprobaron una o más materias?» e inventaba «Semestre actual > 1». Si la consulta pide
# «cuántos» y sus palabras señalan sin ambigüedad una pregunta del catálogo, el plan se arma por el TIPO de esa
# pregunta, no por la redacción de la consulta:
#   - Sí/No: se cuentan los «Sí…» (los «No…» si la consulta niega: «no practican», «sin beca»);
#   - numérica: la comparación escrita («al menos una», «dos o más», «más de 3», «ninguna»); sin comparación,
#     «¿cuántos reprobaron materias?» es tener al menos 1 (y «no reprobaron», menos de 1);
#   - «¿cuántos intentos…?» sobre una pregunta que pregunta «¿cuántos intentos…?»: la cantidad misma, su distribución;
#   - de opciones sin opción nombrada (solo si el modelo no armó ya un conteo): la distribución de la pregunta.
# Con dos preguntas («de los que practican…, ¿cuántos reprobaron?») se cuentan las dos condiciones. Los grupos de
# contexto («los hombres») los añaden los pasos siguientes, solo si la consulta los escribe.
_RAICES_GENERICAS = {"estud", "alumn", "encue", "respo", "perso", "parti", "entre", "prueb", "pregu", "cuant", "unive",
                     "menos", "minim", "maxim", "algun", "ningu", "veces", "mayor", "menor",
                     # La institución no nombra ninguna pregunta: «¿hay inseguridad en la escuela?» empataba con la de
                     # los donativos «a la escuela» (24 nov).
                     "escue", "facul", "insti", "plant"}
_NUMERO_PALABRA = {"cero": 0, "un": 1, "una": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6,
                   "siete": 7, "ocho": 8, "nueve": 9, "diez": 10}
_N = r"([0-9]+(?:[.,][0-9]+)?|cero|una|uno|un|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)"
_COMPARACIONES_PREGUNTA = (
    (re.compile(r"(?<![a-z])(?:al menos|por lo menos|como minimo|minimo) +" + _N + r"(?![a-z0-9])"), ">="),
    (re.compile(r"(?<![a-z0-9])" + _N + r" +o +mas(?![a-z])"), ">="),
    (re.compile(r"(?<![a-z])mas +de +" + _N + r"(?![a-z0-9])"), ">"),
    (re.compile(r"(?<![a-z0-9])" + _N + r" +o +menos(?![a-z])"), "<="),
    (re.compile(r"(?<![a-z])menos +de +" + _N + r"(?![a-z0-9])"), "<"),
    (re.compile(r"(?<![a-z])(?:como maximo|a lo mas|maximo) +" + _N + r"(?![a-z0-9])"), "<="),
)
_NINGUNO = re.compile(r"(?<![a-z])ningun[oa]?(?![a-z])")
_NEGACIONES = {"no", "sin", "nunca", "jamas"}
_DOS_CONDICIONES = re.compile(r"(?<![a-z])(?:de|entre) +(?:los|las) +que(?![a-z])|(?<![a-z])de +quienes(?![a-z])|"
                              r"(?<![a-z])y +(?:tambien|ademas)(?![a-z])")
_CUANTOS_SUSTANTIVO = re.compile(r"(?<![a-z])cuant[oa]s +(?:de +)?([a-z]+)")


def _numero_junto_a(c: CondicionContexto, texto: str) -> bool:
    """¿El número de la comparación está escrito en cifras junto a una palabra de su variable («30 horas»)?"""
    raices = {t[:5] for t in re.findall(r"[a-z]+", normalizar(c.variable.replace("_", " ")))
              if len(t) >= 4} - _VARIABLE_GENERICA
    palabras = re.findall(r"[0-9]+(?:[.,][0-9]+)?|[a-z]+", texto)
    for i, w in enumerate(palabras):
        if w[0].isdigit() and float(w.replace(",", ".")) == float(c.valor) \
                and any(v[:5] in raices for v in palabras[max(0, i - 3):i + 4]):
            return True
    return False


def _numero_de(token: str) -> float:
    return float(_NUMERO_PALABRA[token]) if token in _NUMERO_PALABRA else float(token.replace(",", "."))


def _es_polar(opciones: list[str]) -> bool:
    """Pregunta de Sí/No: todas sus opciones empiezan por «sí» o «no», y hay de las dos."""
    polos = {normalizar(o).split(" ")[0].strip(",.") for o in opciones}
    return bool(opciones) and polos == {"si", "no"}


def _negada(texto: str, raices: set[str]) -> bool:
    """«no practican», «no han reprobado»: una negación hasta tres palabras antes de una palabra del tema."""
    palabras = re.findall(r"[a-z]+", texto)
    return any(w[:5] in raices and _NEGACIONES & set(palabras[max(0, i - 3):i]) for i, w in enumerate(palabras))


def _comparacion_escrita(texto: str) -> tuple[str, float] | None:
    for patron, op in _COMPARACIONES_PREGUNTA:
        if m := patron.search(texto):
            return op, _numero_de(m.group(1))
    return ("<", 1.0) if _NINGUNO.search(texto) else None


def _preguntas_aludidas(texto: str, cat: Catalogo) -> list[tuple[str, int]]:
    """(pregunta, palabras en común) de las que la consulta señala sin ambigüedad: cada una tiene al menos una palabra
    de la consulta que ninguna otra pregunta tiene. Máximo dos, y dos solo si la consulta encadena condiciones."""
    contexto: set[str] = set()
    for var, valores in cat.contexto.items():  # «los hombres», «del semestre…»: son grupos, no preguntas
        contexto |= enrutador._raices(f"{var} {' '.join(valores)}")
    verbos = {v[:5] for v in enrutador._VERBOS_CONSULTA}
    # Las palabras del título nombran el instrumento, no una pregunta: «¿cómo califican las instalaciones de la ESCOM?»
    # señalaba p15 («¿qué otra carrera… en la ESCOM?») solo por «escom» y daba su resumen (26 nov).
    titulo = enrutador._raices(cat.titulo or "")
    raices = {r for r in enrutador._raices(texto) - _RAICES_GENERICAS - contexto - verbos - titulo if not r[0].isdigit()}
    comunes = {pid: raices & enrutador._raices(p.texto) for pid, p in cat.preguntas.items()}
    duenos: dict[str, list[str]] = {}
    for pid, rs in comunes.items():
        for r in rs:
            duenos.setdefault(r, []).append(pid)
    decisivas = {ps[0] for ps in duenos.values() if len(ps) == 1}
    if not decisivas:
        return []
    puntaje = {pid: len(comunes[pid]) for pid in decisivas}
    mejor = max(puntaje.values())
    primeras = [pid for pid in decisivas if puntaje[pid] == mejor]
    if _DOS_CONDICIONES.search(texto):
        elegidas = [q for q in sorted(decisivas, key=lambda q: -puntaje[q]) if puntaje[q] >= 2 or q in primeras][:2]
    elif len(primeras) == 1:
        elegidas = primeras
    else:
        return []  # dos preguntas igual de nombradas: decide el modelo
    # En el orden en que la consulta las nombra: «de los que practican…, ¿cuántos reprobaron?» → la base va primero.
    palabras = [w[:5] for w in re.findall(r"[a-z]+", texto)]
    def posicion(q: str) -> int:
        return min((i for i, w in enumerate(palabras) if w in comunes[q]), default=len(palabras))
    return [(q, puntaje[q]) for q in sorted(elegidas, key=posicion)]


def _grupo_contenido(texto: str, cat: Catalogo) -> tuple[str, str] | None:
    """El único grupo de contexto escrito en la consulta, completo o sin su código («dificultades socioeconómicas»
    por «P8 — Dificultades socioeconómicas»; «los hombres» por «Hombre»)."""
    hallados = set()
    for var, valores in cat.contexto.items():
        for v in valores:
            partes = [normalizar(v)] + [p for p in re.split(r" *[—–-] *", normalizar(v)) if len(p) >= 6]
            if any(_menciona_grupo(texto, p) for p in partes):
                hallados.add((var, v))
    return hallados.pop() if len(hallados) == 1 else None


def _conteo_por_pregunta(texto: str, plan: PlanConsulta, cat: Catalogo) -> tuple[dict, str] | None:
    """Plan de conteo (o de distribución) armado por el tipo de la pregunta aludida; None si no aplica."""
    aludidas = _preguntas_aludidas(texto, cat)
    if not aludidas:
        return None
    m = _CUANTOS_SUSTANTIVO.search(texto)
    sustantivo = m.group(1)[:5] if m else ""
    filtros: list[Filtro] = []
    for pid, puntaje in aludidas:
        p = cat.preguntas[pid]
        raices_p = enrutador._raices(p.texto)
        if _es_polar(p.opciones):
            polo = "no" if _negada(texto, raices_p) else "si"
            filtros.append(Filtro(pregunta=pid, valor=[o for o in p.opciones
                                                       if normalizar(o).split(" ")[0].strip(",.") == polo]))
        elif p.tipo == "numerica":
            if len(aludidas) == 1 and sustantivo and sustantivo in raices_p and "cuant" in normalizar(p.texto):
                return ({"intencion": "resumen_pregunta", "preguntas": [pid]},
                        f"distribución de {pid} («cuántos {m.group(1)}» pide la cantidad misma)")
            comparacion = _comparacion_escrita(texto) or (("<", 1.0) if _negada(texto, raices_p) else (">=", 1.0))
            filtros.append(Filtro(pregunta=pid, op=comparacion[0], valor=comparacion[1]))
        elif (len(aludidas) == 1 and p.opciones and puntaje >= 2 and not _opciones_mencionadas(texto, cat)
              and plan.intencion in ("hallazgo", "semantica_abierta", "resumen_pregunta")):
            return {"intencion": "resumen_pregunta", "preguntas": [pid]}, f"distribución de {pid} (pregunta de opciones)"
    if not filtros:
        return None
    descripcion = ", ".join(f"{f.pregunta} {f.op} {'/'.join(f.valor) if isinstance(f.valor, list) else f.valor}"
                            for f in filtros)
    return {"intencion": "conteo_porcentaje", "filtros": filtros}, f"conteo por el tipo de la pregunta ({descripcion})"


def _menciona_grupo(texto: str, valor: str) -> bool:
    """Como `_menciona`, pero acepta el plural del grupo («los hombres» → «Hombre», «las mujeres» → «Mujer»)."""
    n = normalizar(valor).strip(" .")
    return (len(n) >= 4 and n not in _GENERICAS
            and re.search(r"(?<![a-z0-9])" + re.escape(n) + r"(?:e?s)?(?![a-z0-9])", texto) is not None)


def _condiciones_de(texto: str, cat: Catalogo) -> list[Filtro]:
    """Condiciones que una pregunta dice explícitamente: opciones escritas tal cual y, si una palabra nombra una sola
    pregunta de opciones «Sí…»/«No…» («alguna certificación»), sus opciones «Sí…» (o «No…» con «sin», «no», «ningún»)."""
    if not texto:
        return []
    salida = [Filtro(pregunta=pid, valor=ops[0] if len(ops) == 1 else ops) for pid, ops in _opciones_mencionadas(texto, cat).items()]
    usadas = {f.pregunta for f in salida}
    # Verbos y palabras de consulta no nombran una pregunta: «¿cuántos tienen beca?» filtraba p11 («¿Tienes
    # experiencia laboral…?») por «tienen» (26 nov).
    verbos = {v[:5] for v in enrutador._VERBOS_CONSULTA} | _RAICES_NO_PREGUNTA
    for palabra in {t for t in re.findall(r"[a-z]+", texto) if len(t) >= 6 and t[:5] not in verbos}:
        candidatas = [p for p in cat.preguntas.values() if p.id not in usadas and palabra[:5] in enrutador._raices(p.texto)]
        if len(candidatas) != 1:
            continue
        p = candidatas[0]
        negativa = re.search(rf"\b(?:sin|ningun\w*|no)\s+(?:\w+\s+){{0,2}}{palabra}", texto) is not None
        polo = "no" if negativa else "si"
        valores = [o for o in p.opciones if normalizar(o).split(" ")[0].strip(",.") == polo]
        if valores and len(valores) < len(p.opciones):
            salida.append(Filtro(pregunta=p.id, valor=valores))
            usadas.add(p.id)
    return salida


def _valores(f: Filtro) -> list:
    return [] if f.valor is None else (f.valor if isinstance(f.valor, list) else [f.valor])


def _ajustar_filtro(f: Filtro, texto: str, nivel: str | None, cat: Catalogo, notas: list[str]) -> Filtro:
    """Nivel de la escala en lugar de una sola opción, y todas las opciones «Sí…» / «No…» cuando la pregunta no
    nombra una en particular."""
    p = cat.preguntas.get(f.pregunta)
    if p is None or f.nivel is not None or isinstance(f.valor, (int, float)) or f.valor is None:
        return f
    valores = [str(v) for v in _valores(f)]
    escritos = any(_menciona(texto, v) for v in valores)
    # «están de acuerdo con la pregunta 1» → nivel acuerdo (todas sus opciones), no solo «Totalmente de acuerdo».
    if nivel and (p.escala or p.tipo in ("likert", "escala_lineal", "cuadricula")) and not escritos:
        notas.append(f"filtro {f.pregunta}: «{f.valor}» → nivel {nivel} (la pregunta habla del nivel)")
        return Filtro(pregunta=f.pregunta, op=f.op, nivel=nivel)
    # «no han presentado ningún examen» → todas las «No…», no solo «No, y no lo planeo» (regresión C08).
    polos = {normalizar(v).split(" ")[0].strip(",.") for v in valores}
    if len(polos) == 1 and (polo := polos.pop()) in ("si", "no") and not escritos:
        todas = [o for o in p.opciones if normalizar(o).split(" ")[0].strip(",.") == polo]
        if len(todas) > len(valores):
            notas.append(f"filtro {f.pregunta}: todas las opciones «{'Sí' if polo == 'si' else 'No'}…» ({len(todas)})")
            return Filtro(pregunta=f.pregunta, op=f.op, valor=todas)
    return f


def _aclarar_condicion(plan: PlanConsulta, texto: str, cat: Catalogo) -> PlanConsulta:
    """Pregunta de aclaración con las opciones reales de la pregunta del instrumento que más se parece a la consulta."""
    # Sin las palabras genéricas («estudiantes», «estudios»): sugería la pregunta de los compañeros que desertaron
    # «de los estudios» para «¿cuántos trabajan además de estudiar?» (21 nov, consulta 333).
    raices = enrutador._raices(texto) - _RAICES_GENERICAS
    parecida = max(cat.preguntas.values(), key=lambda q: len(raices & enrutador._raices(q.texto)), default=None)
    if parecida is not None and raices & enrutador._raices(parecida.texto) and parecida.opciones:
        mensaje = (f"No encontré esa condición en «{cat.titulo}». En {parecida.id} («{parecida.texto[:80]}») las opciones "
                   f"son: {', '.join(parecida.opciones[:10])}. ¿Cuál quieres?")
    else:
        mensaje = f"No encontré esa condición en «{cat.titulo}». ¿A qué pregunta u opción te refieres?"
    return PlanConsulta(intencion="aclaracion", instrumentos=plan.instrumentos, aclaracion=mensaje[:300])


def _si_no_nombrada(texto: str, cat: Catalogo, saltar: str | None = None) -> tuple[str, str] | None:
    """Variable de sí/no nombrada en la consulta («tienen beca», «no son de primera generación») y su valor."""
    for var, valores in cat.contexto.items():
        nombre = [t[:5] for t in re.findall(r"[a-z]+", normalizar(var.replace("_", " ")))  # en orden
                  if len(t) >= 4 and t[:5] not in _VARIABLE_GENERICA]
        if var == saltar or not nombre or not all(normalizar(v) in _VERDADEROS | _FALSOS for v in valores):
            continue
        if not (m := re.search(r"\b" + r"\w*\s+(?:\w+\s+)?".join(map(re.escape, nombre)), texto)):
            continue
        negada = re.search(r"\b(?:no|sin|ni)\s+(?:\w+\s+){0,2}$", texto[:m.start()]) is not None
        if valor := _booleano(valores, not negada):
            return var, valor
    return None


def _grupos_de_una_variable(texto: str, cat: Catalogo) -> tuple[str, list[str]] | None:
    """(variable, grupos) si la consulta escribe dos o más grupos de una misma variable («hombres y mujeres»)."""
    for var, valores in cat.contexto.items():
        escritos = [v for v in valores if len(v) >= 3 and not v.isdigit() and _menciona_grupo(texto, v)]
        if len(escritos) >= 2:
            return var, escritos
    return None


def partes_de_conteo(pregunta: str) -> list[str]:
    """«¿Cuántos tienen beca y cuántos son primera generación?» → las dos preguntas; [] si no es doble (22 nov)."""
    partes = [p.strip(" ,;?") for p in re.split(r" y (?=cuant[oa]s )", normalizar(pregunta))]
    return partes if len(partes) >= 2 and all(_CONTEO.search(p) for p in partes) else []
