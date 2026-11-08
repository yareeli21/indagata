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

import difflib
import re

from services import enrutador
from services.catalogo import Catalogo
from services.dominio import normalizar
from services import plan_consulta
from services.plan_consulta import CondicionContexto, Filtro, Orden, PlanConsulta, _es_escala

_CONTEO = re.compile(r"\b(?:cuantos|cuantas|cuanto|que\s+porcentaje|que\s+tanto\s+por\s+ciento|numero\s+de)\b")
_LISTAR = re.compile(r"\b(?:quienes|cuales|dame|da\s?me|lista|enlista|muestra|muestrame|ids?|identificadores)\b")
_FILTRADO = ("filtrar_respondentes", "conteo_porcentaje")
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
    # «Menos consenso / menos acuerdo» es lo contrario de coincidir (en una encuesta, «más desacuerdo» es un nivel de la escala): respuestas repartidas (7 nov,
    # PRU-13: «¿en qué reactivo hubo menos consenso?» daba el reactivo MÁS concentrado). Va antes que «coincidencia».
    ("repartida", re.compile(r"\b(?:dividid\w*|repartid\w*|dispers\w*|polarizad\w*)\b"
                             r"|\bmenos (?:consenso|acuerdo|coincidencia|unanimidad)\b|\bmas division\b")),
    ("coincidencia", re.compile(r"\b(?:casi todos|coincid\w*|lo mismo|la misma|unanim\w*|consenso)\b")),
)
# «¿cuántos mencionaron la ansiedad?», «¿quiénes hablaron del estrés?»: menciones de un tema en respuestas abiertas.
_MENCION = re.compile(r"\b(?:mencion\w*|nombr(?:an|aron|a|o)|habl(?:an|aron|a|o) (?:de|del|sobre|acerca de)|"
                      r"(?:dijeron|dicen|dijo|dice) algo (?:de|del|sobre|acerca de)|se refier\w* a|se refirieron a|"
                      r"comentaron (?:sobre|de|del))\s+(.{1,40}?)(?=[,;?.]|\s+y\s+|\s+en\s+(?:la|el|las|los|sus)\s+|$)")
_RELLENO_MENCION = {"la", "el", "los", "las", "lo", "un", "una", "algo", "de", "del", "al", "a", "sobre", "su", "sus",
                    "tema", "temas", "que", "alguna", "algun", "vez"}
_SEGUIMIENTO = re.compile(r"\b(?:de|entre) (?:ellos|ellas|esos|esas|estos|estas)\b")
# «¿Y los que tienen beca contra los que no?»: comparar los grupos de una variable, no quedarse con uno (consulta 2187).
_CONTRA = re.compile(r"\b(?:contra|versus|vs|frente a|comparad[oa]s? con|en comparacion con|a diferencia de)\b")
# «¿cuántos dejaron alguna pregunta sin responder?»: se pregunta por personas, no por la pregunta con más omisiones.
_PERSONAS = re.compile(r"\b(?:cuant[oa]s|quienes|respondentes?|alumn[oa]s?|estudiantes?|encuestad[oa]s?|personas?|"
                       r"participantes?|alguien|nadie)\b")
_NEGACION_OPCION = ("no", "ningun", "ninguna", "ninguno", "nunca", "nada")


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
    # Un grupo de contexto se sostiene si la consulta dice su valor; en una variable de sí/no basta con nombrarla
    # («los que tienen beca»). Nombrar solo la variable no basta: «¿cuántos estudian ingeniería?» se convertía en
    # nivel_estudio = «pregrado» porque «estudian» comparte raíz con la variable (consulta 2195, 7 nov).
    contexto = {k: v for k, v in plan.contexto.items()
                if dicho(str(v)) or (normalizar(str(v)) in _VERDADEROS | _FALSOS and dicho(k))}
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
        variable_nombrada = _filtros_sin_inventos(plan, cat, raices, dicho, cambios, notas)
        if not variable_nombrada and not cambios.get("filtros", plan.filtros) and not cambios.get("contexto", plan.contexto) \
                and not cambios.get("contexto_num", plan.contexto_num) and not cambios.get("preguntas", plan.preguntas):
            # Antes de rendirse: la condición puede estar en las opciones de una pregunta que no usa las palabras de
            # la consulta («¿cuántos trabajan?» → p12 «¿Cuál es tu situación laboral actual?», consulta 2149).
            if por_opcion := opciones_por_raiz(pregunta, cat):
                cambios["filtros"] = [Filtro(pregunta=pid, valor=ops) for pid, ops in por_opcion.items()]
                notas += [f"filtro {pid} = «{', '.join(ops)}» (sus opciones dicen lo que pide la pregunta)"
                          for pid, ops in por_opcion.items()]
                return plan.model_copy(update=cambios), notas
            # Pedía una condición y ninguna se sostiene: se dice que no existe en lugar de contar a todos
            # («¿cuántos estudian ingeniería?» en una prueba sin carrera, consulta 1612).
            notas.append(NINGUNA_CONDICION)
            nuevo = _aclarar_condicion(plan, pregunta, cat)
            return nuevo, notas + ([AVISO_INEXISTENTE] if nuevo.intencion != "aclaracion" else [])
    return (plan.model_copy(update=cambios) if cambios else plan), notas


# Nota que marca un plan cuya condición no existe en el instrumento: su aclaración ya es la respuesta (dice que no
# existe y qué opciones hay), así que no se cambia por una respuesta con lo recuperado del RAG (consulta 2147).
NINGUNA_CONDICION = "ninguna condición respaldada: se pide aclaración"
# 7 nov (Fase 3): lo que se pide no existe (una opción, un reactivo, una segunda participante). El plan calcula lo que
# SÍ hay y `aclaracion` lleva el aviso; la respuesta es el aviso más el resultado, sin redacción ni texto recuperado.
AVISO_INEXISTENTE = "lo que pide no existe en el instrumento: se responde con lo que sí hay"
_OPCION_LETRA = re.compile(r"\bopcion\s+([a-h])\b")
_OTRA_PERSONA = re.compile(r"\b(?:segund[oa]|tercer[oa]|otr[oa]s?|demas|resto de (?:los|las))\s+"
                           r"(?:participantes?|entrevistad\w*|personas?|estudiantes?)\b")


_PRIMEROS_ULTIMOS = re.compile(r"\bprimer[oa]s\s+(\d{1,4})\b.{0,60}\bultim[oa]s\s+(\d{1,4})\b")
_POR_SECCION = re.compile(r"\b(?:por|entre|en (?:alguna|cada|que)|de (?:la|cada)) secci\w*\b|\bsecciones?\b.{0,40}\b(?:compar\w*|"
                          r"concentr\w*|mas|menos)\b|\bcompar\w*\b.{0,60}\bseccion\b")
_SEGUN = re.compile(r"\b(?:segun|dependiendo de|de acuerdo con|en funcion de)\s+(?:la|el|los|las|su|sus)?\s*(.{3,60}?)(?:[?,.]|$)")


_PREOCUPANTE = re.compile(r"\b(?:preocupa\w*|alarma\w*|negativ\w*|peor(?:es)?|problema\w*|debilidad\w*|riesgos?|"
                          r"critic\w*|desfavorable\w*|atender primero|focos? rojos?)\b")
_FAVORABLE = re.compile(r"\b(?:lo mejor|mejores resultados|fortaleza\w*|positiv\w*|favorable\w*|destaca para bien|"
                        r"salio mejor|salieron mejor)\b")


def sentido(pregunta: str) -> str | None:
    texto = normalizar(pregunta)
    if _PREOCUPANTE.search(texto):
        return "desfavorable"
    if _FAVORABLE.search(texto):
        return "favorable"
    return None


_RELLENO_TEXTO = {"que", "los", "las", "del", "con", "por", "una", "uno", "sus", "eligieron", "respondieron", "marcaron",
                  "reactivo", "pregunta", "sobre", "cual", "cuales", "como", "mas"}
_DE_LOS_QUE = re.compile(r"^(?:y\s+)?de\s+(?:los|las|quienes)\s+que\s+(.+?)[,?¿]\s*(?:que|cuantos|cuantas|como|cual)\b(.+)$")
_CONTRASTE = re.compile(r"\b(?:que|contra|frente a|comparados? con|vs\.?)\s+(?:los|las)?\s*(?:que|quienes)\b")


def _pregunta_por_texto(frase: str, cat: Catalogo, excluir: set[str]) -> str | None:
    """La pregunta cuyo texto comparte más raíces con la frase (una sola, sin empate)."""
    def raices(t: str) -> set[str]:  # también siglas de tres letras («VPN», «PDF»)
        return {w[:5] for w in re.findall(r"[a-z0-9]+", normalizar(t)) if len(w) >= 3 and w not in enrutador._STOP_FILTRO
                and w not in _RELLENO_TEXTO}

    propias = raices(frase)
    # Coincidencias y, para desempatar, qué tanto de la pregunta es lo que se nombra: «el reactivo de la VPN» es
    # «¿Cuál es la principal función de una VPN?» antes que «Usar redes Wi-Fi públicas sin VPN es seguro» (PRU-09).
    puntos = [(len(propias & raices(q.texto)), len(propias & raices(q.texto)) / max(1, len(raices(q.texto))), pid)
              for pid, q in cat.preguntas.items() if pid not in excluir]
    mejor = max(puntos, default=(0, 0.0, None))
    empates = [x for x in puntos if x[0] == mejor[0]]
    if mejor[0] < 1:
        return None
    if len(empates) == 1:
        return mejor[2]
    densas = sorted(empates, key=lambda x: -x[1])
    return densas[0][2] if densas[0][1] > densas[1][1] else None


def _opcion_en(frase: str, pid: str, cat: Catalogo) -> list[str]:
    """Opciones de `pid` que la frase nombra (tal cual, o por su raíz y polaridad)."""
    q = cat.preguntas[pid]
    tal_cual = [o for o in q.opciones if _menciona(normalizar(frase), o)]
    return tal_cual or opciones_por_raiz(frase, catalogo_de_una(cat, pid), con_ausentes=True).get(pid, [])


def catalogo_de_una(cat: Catalogo, pid: str) -> Catalogo:
    return Catalogo(cat.id, cat.titulo, cat.tipo, {pid: cat.preguntas[pid]}, cat.respondentes, cat.contexto, cat.kpis,
                    cat.numericas)


def _cruce_de(plan: PlanConsulta, pregunta: str, cat: Catalogo) -> tuple[PlanConsulta, list[str]] | None:
    """«De los que marcaron Verdadero en «el correo es seguro», ¿qué eligieron en el reactivo de la VPN?»: la condición
    sale de la primera parte (pregunta + opción) y la pregunta que se resume, de la segunda (7 nov, PRU-09)."""
    m = _DE_LOS_QUE.search(normalizar(pregunta))
    if not m:
        return None
    condicion, resto = m.group(1), m.group(2)
    citado = re.findall(r"«([^»]+)»", pregunta)
    origen = _pregunta_por_texto(citado[0] if citado else condicion, cat, set())
    if origen is None:
        return None
    opciones = _opcion_en(condicion, origen, cat)
    destino = _pregunta_por_texto(resto, cat, {origen})
    if not opciones or destino is None:
        return None
    return plan.model_copy(update={"intencion": "resumen_pregunta", "preguntas": [destino], "agrupar_por": None,
                                   "filtros": [Filtro(pregunta=origen, valor=opciones if len(opciones) > 1 else opciones[0])],
                                   "aclaracion": "", "consulta_semantica": "", "nivel": None}), [
        f"cruce: {destino} entre quienes respondieron «{', '.join(opciones)}» en {origen}"]


def _los_que_contra_los_que(plan: PlanConsulta, pregunta: str, cat: Catalogo) -> tuple[PlanConsulta, list[str]] | None:
    """«¿Los que trabajan en algo relacionado aprobaron más certificaciones que los que no trabajan?»: dos grupos de una
    misma pregunta (uno por cada lado) y la pregunta que se compara (7 nov, ENC-09, ENC-12, CEN-02)."""
    texto = normalizar(pregunta)
    m = _CONTRASTE.search(texto)
    if not m or not re.search(r"\b(?:los|las|quienes)\s+que\b|\bquienes\b", texto[:m.start()]):
        return None
    izquierda, derecha = texto[:m.start()], texto[m.end():]
    for pid in cat.preguntas:
        a, b = _opcion_en(izquierda, pid, cat), _opcion_en(derecha, pid, cat)
        if a and b and set(a) != set(b):
            objetivo = [q for q in plan.preguntas if q != pid and q in cat.preguntas] or \
                       [x for x in [_pregunta_por_texto(izquierda + " " + derecha, cat, {pid})] if x]
            if objetivo:
                return plan.model_copy(update={"intencion": "comparar_grupos", "agrupar_por": pid, "preguntas": objetivo[:1],
                                               "filtros": [Filtro(pregunta=pid, valor=list(dict.fromkeys(a + b)))],
                                               "aclaracion": "", "consulta_semantica": "", "limite": None, "nivel": None}), [
                    f"comparar {objetivo[0]} entre «{', '.join(a)}» y «{', '.join(b)}» de {pid}"]
    return None


def _agrupamiento(plan: PlanConsulta, pregunta: str, cat: Catalogo) -> tuple[PlanConsulta, list[str]] | None:
    """Comparaciones que la consulta dice con todas sus letras (7 nov, Fase 4), sin importar lo que propuso el modelo:
      - «compara los primeros 100 con los últimos 100 en…» → grupos por posición (N en `limite`);
      - «¿las respuestas en blanco se concentran en alguna sección?» / «compara la sección A con la B» → por sección;
      - «¿cambia X según la carga académica?» → grupos por la respuesta a la pregunta de la carga;
      - «compara X entre <opción A> y <opción B>» de una misma pregunta → grupos por esa pregunta, solo esas opciones."""
    texto = normalizar(pregunta)
    objetivo = [q for q in plan.preguntas if q in cat.preguntas]
    if (cruce := _cruce_de(plan, pregunta, cat)) is not None:
        return cruce
    if (contraste := _los_que_contra_los_que(plan, pregunta, cat)) is not None:
        return contraste
    if m := _PRIMEROS_ULTIMOS.search(texto):
        n = min(int(m.group(1)), int(m.group(2)))
        if not objetivo:
            # «… en el reactivo de la contraseña segura»: el modelo no puso la pregunta y la tabla salía sin columna
            # (8 nov, Fase 5, PRU-10); se busca por el texto que sigue a «primeros N … últimos N».
            objetivo = [x for x in [_pregunta_por_texto(texto[m.end():], cat, set())] if x]
        return plan.model_copy(update={"intencion": "comparar_grupos", "agrupar_por": "posicion", "limite": n,
                                       "filtros": [], "aclaracion": "", "consulta_semantica": "",
                                       "orden": None, "preguntas": objetivo or plan.preguntas}), [
            f"comparar los primeros {n} con los últimos {n}"]
    if _POR_SECCION.search(texto) and len({q.texto for q in cat.preguntas.values()}) > 1 and cat.tipo == "prueba_estandarizada":
        return plan.model_copy(update={"intencion": "comparar_grupos", "agrupar_por": "seccion", "filtros": [],
                                       "aclaracion": "", "consulta_semantica": "", "preguntas": []}), [
            "comparar por sección (respuestas en blanco o nulas)"]
    if (m := _SEGUN.search(texto)) and plan.intencion in ("comparar_grupos", "resumen_pregunta", "conteo_porcentaje",
                                                         "aclaracion", "semantica_abierta", "hallazgo"):
        frase = enrutador._raices(m.group(1))
        candidatas = [(len(frase & enrutador._raices(q.texto)), pid) for pid, q in cat.preguntas.items()
                      if q.opciones and pid not in objetivo]
        mejor = max(candidatas, default=(0, None))
        if mejor[0] >= 1 and sum(1 for x, _ in candidatas if x == mejor[0]) == 1:
            resto = texto[:m.start()]
            objetivo = objetivo or [pid for x, pid in sorted(
                ((len(enrutador._raices(resto) & enrutador._raices(q.texto)), pid) for pid, q in cat.preguntas.items()
                 if pid != mejor[1]), reverse=True)[:1] if x >= 1]
            if objetivo:
                return plan.model_copy(update={"intencion": "comparar_grupos", "agrupar_por": mejor[1], "preguntas": objetivo,
                                               "filtros": [], "aclaracion": "", "consulta_semantica": ""}), [
                    f"comparar {', '.join(objetivo)} según {mejor[1]} (la consulta dice «según…»)"]
    if re.search(r"\bcompar\w*\b|\bentre\b", texto):
        for pid, ops in _opciones_mencionadas(texto, cat).items():
            if len(ops) >= 2 and pid not in objetivo:
                objetivo = objetivo or [q for q in plan.preguntas if q != pid]
                if objetivo:
                    return plan.model_copy(update={"intencion": "comparar_grupos", "agrupar_por": pid, "preguntas": objetivo,
                                                   "filtros": [Filtro(pregunta=pid, valor=ops)], "aclaracion": "",
                                                   "consulta_semantica": ""}), [
                        f"comparar {', '.join(objetivo)} entre «{'» y «'.join(ops)}» de {pid}"]
    return None


def inexistente(plan: PlanConsulta, pregunta: str, cat: Catalogo) -> tuple[PlanConsulta, list[str]] | None:
    """Plan con el aviso si la consulta pide algo que el instrumento no tiene: una opción con letra que el reactivo no
    tiene («la opción E en el reactivo 3») o a otra persona en una entrevista de una sola participante. None si no."""
    texto = normalizar(pregunta)
    m = _OPCION_LETRA.search(texto)
    if m:
        numeradas = [pid for n in enrutador._preguntas(texto) if (pid := _id_pregunta(cat, n))]
        for pid in numeradas or plan.preguntas[:1]:
            q = cat.preguntas.get(pid)
            letras = {o[0].upper() for o in (q.opciones if q else []) if re.match(r"^[A-Ha-h]\)", o)}
            if q and letras and m.group(1).upper() not in letras:
                aviso = (f"No existe la opción {m.group(1).upper()} en {pid} («{q.texto[:80]}»): sus opciones son "
                         f"{', '.join(sorted(letras))}. Así se repartieron las respuestas:")
                return PlanConsulta(intencion="resumen_pregunta", preguntas=[pid], instrumentos=plan.instrumentos,
                                    aclaracion=aviso[:300]), [f"opción {m.group(1).upper()} inexistente en {pid}", AVISO_INEXISTENTE]
    if cat.tipo == "entrevista" and len(cat.respondentes) == 1 and (
            _OTRA_PERSONA.search(texto) or re.search(r"\bcompar\w*\b.{0,60}\b(?:participantes|entrevistad\w*|demas)\b", texto)):
        unica = cat.respondentes[0]
        aviso = (f"«{cat.titulo}» tiene una sola participante ({unica}): no hay otra persona entrevistada ni con quién "
                 "comparar sus respuestas.")
        return PlanConsulta(intencion="aclaracion", instrumentos=plan.instrumentos, aclaracion=aviso[:300]), [
            "otra participante pedida en una entrevista de una sola persona", AVISO_INEXISTENTE]
    return None


def opciones_por_raiz(pregunta: str, cat: Catalogo, ya_usadas: set[str] | None = None,
                      explicadas: set[str] | None = None, con_ausentes: bool = False) -> dict[str, list[str]]:
    """{pregunta: opciones} cuya redacción contiene una palabra de la consulta que no está explicada por otra
    condición. La palabra debe estar en las opciones de UNA sola pregunta y no en todas sus opciones (eso no filtra):
    «trabajan» → p12 «Trabajo en un area relacionada…», «Trabajo en un area no relacionada». Se respeta la polaridad:
    sin negación en la consulta no entran las opciones que empiezan negando («No trabajo ni busco empleo»), y con
    negación solo entran esas."""
    texto = normalizar(pregunta)
    if not con_ausentes and _ausentes(pregunta, cat):
        # Una palabra que el instrumento no registra es la condición («modalidad nocturna»): no se cambia por otra
        # palabra que sí aparece en alguna opción («estudian» → «…mi plan de estudios», consulta 2204, 7 nov).
        # `con_ausentes`: en un seguimiento («de ellos, ¿cuántos la consiguieron por convenio?») el verbo que el
        # instrumento no registra no es la condición; la opción nombrada sí.
        return {}
    ya_usadas, explicadas = ya_usadas or set(), explicadas or set()
    salida: dict[str, list[str]] = {}
    # Lo citado entre comillas es el enunciado de una pregunta («la nube elimina por completo el riesgo de perder
    # datos»), no una opción: «completo» y «datos» filtraban opciones de otros reactivos (7 nov, PRU-14).
    texto = re.sub(r"«[^»]*»|\"[^\"]*\"|“[^”]*”", " ", texto)
    for palabra in dict.fromkeys(re.findall(r"[a-z]+", texto)):
        raiz = palabra[:5]
        if len(palabra) < 5 or palabra in enrutador._STOP_FILTRO or raiz in explicadas or raiz in _VERBOS_CONSULTA:
            continue
        negada = re.search(rf"\b(?:no|sin|ningun\w*|ni|nunca)\s+(?:\w+\s+){{0,2}}{palabra}", texto) is not None
        candidatas = {}
        for pid, p in cat.preguntas.items():
            ops = [o for o in p.opciones if raiz in enrutador._raices(o) and comparte_raiz(palabra, o)]
            # La polaridad decide antes que el conteo: «no trabajan» en «No trabajo / Trabajo menos de 20h / Trabajo más
            # de 30h» es «No trabajo», aunque la palabra esté en todas las opciones (7 nov, CEN-03).
            ops = [o for o in ops if (normalizar(o).split(" ")[0].strip(",.") in _NEGACION_OPCION) == negada]
            if ops and len(ops) < len(p.opciones):
                candidatas[pid] = ops
        if len(candidatas) != 1:
            continue
        pid, ops = next(iter(candidatas.items()))
        if pid in ya_usadas or pid in salida:
            continue
        salida[pid] = ops
    return salida


def _prefijo_comun(a: str, b: str) -> int:
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def comparte_raiz(palabra: str, opcion: str) -> bool:
    """¿La palabra de la consulta es la misma que una de la opción, salvo su terminación? Cinco letras iguales no
    bastan: «consiguieron» y «considerando» comparten «consi» y la consulta «¿cuántos la consiguieron por convenio?»
    filtraba «Estoy considerando abandonar» (7 nov, ENC-13). Se piden seis letras en común, o la palabra entera si una
    de las dos es más corta («mixta», «turno»)."""
    for w in re.findall(r"[a-z]+", normalizar(opcion)):
        comun = _prefijo_comun(palabra, w)
        corta = min(len(palabra), len(w))
        # Seis letras, o la palabra corta entera, o le falta solo la última letra («diario» ~ «diariamente»).
        if comun >= 6 or (comun >= 5 and comun >= corta - (1 if corta <= 6 else 0)):
            return True
    return False


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


def _raices_de_variables(cat: Catalogo) -> set[str]:
    """Raíces de los nombres de las variables de contexto («tiene_beca» → «beca»), sin las genéricas («tiene»)."""
    nombres = [*cat.contexto, *cat.numericas]
    return {r for v in nombres for r in enrutador._raices(v.replace("_", " ")) if r not in _VARIABLE_GENERICA}


def _filtros_sin_inventos(plan: PlanConsulta, cat: Catalogo, raices: set[str], dicho, cambios: dict,  # noqa: ANN001
                          notas: list[str]) -> bool:
    """Filtros que la validación volvía una aclaración absurda antes de que el anclaje los revisara (Fase 6):
    - un dato de contexto puesto como pregunta («horas_trabajo_semana > 20», «primera_generacion = sí»; consultas
      1583 y 1594: «No encontré la pregunta "horas_trabajo_semana"») pasa al contexto;
    - un valor que no es opción de la pregunta y que la consulta no dice («A)» en r01 para «¿cuántos estudian
      ingeniería?», 1612) se descarta;
    - un valor que son palabras del enunciado del reactivo («Big Data» en r22, cuyo texto es «… Big Data ↔», 1617) se
      descarta y el reactivo queda como la pregunta de la que se habla."""
    filtros: list[Filtro] = []
    variable_nombrada = False  # True: un valor descartado nombraba un dato de contexto (la condición existe)
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
        # «p04» en una prueba es r04: la validación lo corregiría después, cuando el filtro ya pasó (consulta 2246).
        p = cat.preguntas.get(plan_consulta._id_pregunta(f.pregunta, cat) or f.pregunta)
        if p is None or f.nivel is not None or isinstance(f.valor, (int, float)) or not valores \
                or all(_es_opcion(v, p.opciones) for v in valores):
            filtros.append(f)  # la validación decide (pregunta inexistente, nivel, número u opción reconocible)
            continue
        del_reactivo = enrutador._raices(p.texto)
        del_valor = set().union(*(enrutador._raices(v.replace("_", " ")) for v in valores))  # «tiene_beca» → beca
        if del_valor and del_valor <= del_reactivo and del_valor & raices:
            notas.append(f"filtro {f.pregunta} = «{f.valor}» descartado (son palabras del enunciado, no una opción)")
            if f.pregunta not in preguntas:
                preguntas.append(f.pregunta)
        elif (del_valor & raices) and (del_valor & raices) <= _raices_de_variables(cat) \
                and not (del_valor & set().union(*(enrutador._raices(o) for o in p.opciones))):
            # Las palabras dichas nombran un dato de contexto, no una opción del reactivo: «no_beca» en r04 para «¿y
            # los que tienen beca contra los que no?» pedía elegir una opción del phishing (consulta 2242).
            notas.append(f"filtro {f.pregunta} = «{f.valor}» descartado (nombra un dato de contexto, no una opción)")
            variable_nombrada = True
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
    return variable_nombrada


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


def anclar(plan: PlanConsulta, pregunta: str, historial: list[tuple[str, str]], cat: Catalogo,
           heredar_texto: bool = True) -> tuple[PlanConsulta, list[str]]:
    """El plan corregido con las menciones explícitas de la pregunta, y las correcciones aplicadas.

    `heredar_texto`: en un seguimiento («de ellos…») busca las condiciones en el TEXTO de la pregunta anterior. Con el
    plan anterior a mano no hace falta (`seguimiento.combinar` hereda sus condiciones exactas): desde el texto se heredó
    «p01 = Sí» porque el enunciado sucio de p01 empieza con «Cargas máxima» (consulta 2149, 7 nov)."""
    texto = normalizar(pregunta)
    notas: list[str] = []
    cambios: dict = {}
    intencion = plan.intencion
    if (no_existe := inexistente(plan, pregunta, cat)) is not None:
        return no_existe
    if plan.agrupar_por == "posicion" and not _PRIMEROS_ULTIMOS.search(texto):
        # El modelo copió el ejemplo de «primeros N y últimos N» sin que la consulta lo dijera (7 nov, CEN-02).
        plan = plan.model_copy(update={"agrupar_por": None, "limite": None})
        notas.append("agrupar por posición quitado (la consulta no habla de primeros y últimos)")
    if (agrupado := _agrupamiento(plan, pregunta, cat)) is not None:
        plan, notas = agrupado[0], list(agrupado[1])
        intencion = plan.intencion
    nombra_pregunta = bool(enrutador._preguntas(texto)) or "«" in pregunta
    if cat.tipo == "encuesta" and (s := sentido(pregunta)) and not nombra_pregunta and not plan.filtros \
            and intencion in ("hallazgo", "resumen_pregunta", "semantica_abierta", "aclaracion", "ranking_preguntas"):
        # «¿Qué es lo más preocupante de los resultados?»: hallazgo con la polaridad de cada pregunta (7 nov, ENC-16).
        notas.append(f"intención {intencion} → hallazgo con sentido {s}" if intencion != "hallazgo" else f"sentido {s}")
        return plan.model_copy(update={"intencion": "hallazgo", "sentido": s, "aclaracion": "", "consulta_semantica": "",
                                       "criterio_ranking": None, "preguntas": []}), notas

    # 0. Ranking de preguntas («¿en qué pregunta hubo más nulas, sin contar la de la contraseña?»): el plan solo tenía
    # el hallazgo, que da UNA pregunta y no permite excluir (Fase 6, consultas 1493, 1498 y 1529). Se revisa también
    # una aclaración: en 1529 el modelo filtró «A» en r10 y la validación lo volvió una pregunta absurda.
    criterio = _criterio_ranking(texto)
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
    # 0c. «¿Cuántos dejaron alguna pregunta sin responder?» / «¿hay respondentes que dejaron en blanco algunas?»:
    # se cuentan personas con omisiones, no se ordena las preguntas (consultas 2165 y 2189, 7 nov).
    elif criterio == "no_respuesta" and _PERSONAS.search(texto) and not enrutador._persona(texto) \
            and intencion in ("hallazgo", "resumen_pregunta", "semantica_abierta", "aclaracion", "ranking_preguntas",
                              *_FILTRADO):
        nueva = "filtrar_respondentes" if _LISTAR.search(texto) and not _CONTEO.search(texto) else "conteo_porcentaje"
        cambios.update(intencion=nueva, con_omisiones=True, criterio_ranking=None, nivel=None, aclaracion="",
                       consulta_semantica="", preguntas=[], filtros=[f for f in plan.filtros if f.pregunta in cat.preguntas]
                       if intencion in _FILTRADO else [])
        notas.append((f"intención {intencion} → {nueva}: " if nueva != intencion else "")
                     + "personas que dejaron alguna pregunta sin responder")
        excluidas = _excluidas(texto, cat)
        if excluidas:
            cambios["excluir_preguntas"] = excluidas
        return plan.model_copy(update=cambios), notas
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
    if intencion in ("fuera_de_dominio", "uso_plataforma", "metodologia", "aclaracion"):
        return plan, []
    excluidas = _excluidas(texto, cat)
    if excluidas and set(excluidas) != set(plan.excluir_preguntas):
        cambios["excluir_preguntas"] = list(dict.fromkeys([*plan.excluir_preguntas, *excluidas]))
        notas.append(f"sin contar {', '.join(excluidas)} (lo pide la pregunta)")
    elif plan.excluir_preguntas and not _EXCLUSION.search(texto):
        # Solo se excluye lo que la consulta pide no contar: el modelo puso los 22 reactivos en «excluir_preguntas» y
        # el ranking se quedó sin preguntas («No hay resúmenes calculados», 7 nov, PRU-03 y PRU-07).
        cambios["excluir_preguntas"] = []
        notas.append(f"excluir {', '.join(plan.excluir_preguntas[:5])}{'…' if len(plan.excluir_preguntas) > 5 else ''} "
                     "descartado (la pregunta no pide excluir nada)")
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
        elif not set(pids) <= set(plan.preguntas):
            cambios["preguntas"] = list(dict.fromkeys([*plan.preguntas, *pids]))
            notas.append(f"preguntas {', '.join(pids)} tomadas de la pregunta")

    # 3. Grupo de contexto escrito tal cual («del turno vespertino» → {turno: Vespertino}). Con «contra» / «frente a»
    # se comparan los grupos de esa variable («los de pública contra los de privada»).
    contra = _CONTRA.search(texto) is not None
    # Dos valores de la misma variable también son una comparación: «¿responden distinto los de universidad pública
    # y los de privada?» filtraba solo «publica» (consulta 2239).
    nombrados = {var: [v for v in valores if len(v) >= 3 and not v.isdigit() and _menciona(texto, v)]
                 for var, valores in cat.contexto.items()}
    varios = any(len(set(vs)) >= 2 for vs in nombrados.values())
    if (not plan.contexto or contra or varios) and intencion in (*_FILTRADO, "comparar_grupos", "resumen_pregunta"):
        for var, valores in cat.contexto.items():
            if var == plan.agrupar_por:
                continue
            valor = next(iter(nombrados[var]), None)
            if valor and _valor_de_un_reactivo(texto, var, valor, cat):
                notas.append(f"contexto {var} = «{valor}» no se toma («{valor}» es parte del reactivo citado)")
                continue
            if valor and (contra or len(set(nombrados[var])) >= 2):
                intencion = _comparar_por(var, intencion, cambios, notas)
                break
            if valor:
                cambios["contexto"] = {var: valor}
                notas.append(f"contexto {var} = «{valor}» (escrito en la pregunta)")
                break

    # 3c. Variable de sí/no nombrada («los de primera generación», «los que no tienen beca»): su valor no se escribe,
    # se deduce del nombre y de una negación justo antes (Fase 6, consultas 1594 y 1617).
    if (not cambios.get("contexto", plan.contexto) or contra) and not cambios.get("agrupar_por") \
            and intencion in (*_FILTRADO, "comparar_grupos", "resumen_pregunta"):
        for var, valores in cat.contexto.items():
            nombre = [t[:5] for t in re.findall(r"[a-z]+", normalizar(var.replace("_", " ")))  # en orden
                      if len(t) >= 4 and t[:5] not in _VARIABLE_GENERICA]
            if var == plan.agrupar_por or not nombre or not all(normalizar(v) in _VERDADEROS | _FALSOS for v in valores):
                continue
            if not (m := re.search(r"\b" + r"\w*\s+(?:\w+\s+)?".join(map(re.escape, nombre)), texto)):
                continue
            if contra:  # «¿y los que tienen beca contra los que no?» (consulta 2187)
                intencion = _comparar_por(var, intencion, cambios, notas)
                break
            negada = re.search(r"\b(?:no|sin|ni)\s+(?:\w+\s+){0,2}$", texto[:m.start()]) is not None
            if valor := _booleano(valores, not negada):
                cambios["contexto"] = {var: valor}
                notas.append(f"contexto {var} = «{valor}» (la pregunta nombra la variable)")
                break

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
    # Un nivel solo existe en preguntas de escala y si la consulta lo dice: «¿cuántos respondieron la de la
    # contraseña?» salía «0 de 0 están de acuerdo (nivel alto)» en un reactivo de opción múltiple (consulta 2220).
    if plan.nivel and not nivel and preguntas_plan and not any(
            cat.preguntas[q].escala or cat.preguntas[q].tipo in ("likert", "escala_lineal", "cuadricula")
            for q in preguntas_plan if q in cat.preguntas):
        cambios["nivel"] = None
        notas.append(f"nivel {plan.nivel} quitado (ni la consulta lo dice ni la pregunta es de escala)")
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
        # Palabras de la consulta que solo aparecen en las opciones de una pregunta («trabajan» → p12 «Trabajo en…»),
        # si ninguna condición del plan las explica (consulta 2149: el modelo copió «horas > 30» del ejemplo).
        explicadas = _raices_explicadas(plan, cambios, filtros, cat)
        for pid, ops in opciones_por_raiz(pregunta, cat, {f.pregunta for f in filtros}, explicadas).items():
            filtros.append(Filtro(pregunta=pid, op="=", valor=ops[0] if len(ops) == 1 else ops))
            notas.append(f"filtro {pid} = «{', '.join(ops)}» (sus opciones dicen lo que pide la pregunta)")
        filtros = [_ajustar_filtro(f, texto, nivel, cat, notas) for f in filtros]
        filtros = _por_cantidad_escrita(filtros, texto, notas)
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
        if heredar_texto and _SEGUIMIENTO.search(texto):
            previa = next((normalizar(t) for rol, t in reversed(historial) if rol == "usuario"), "")
            for f in _condiciones_de(previa, cat):
                if not any(x.pregunta == f.pregunta for x in filtros):
                    filtros.append(f)
                    notas.append(f"filtro {f.pregunta} heredado de la pregunta anterior")
        # Filtros que la pregunta no respalda: ni su valor ni su pregunta comparten palabras con la consulta ni
        # con lo que el usuario preguntó antes (las preguntas de seguimiento heredan sus condiciones).
        previas = " ".join(t for rol, t in historial[-4:] if rol == "usuario")
        raices = enrutador._raices(texto) | enrutador._raices(previas)
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
            nuevo = _aclarar_condicion(plan, pregunta, cat)
            return nuevo, notas + [NINGUNA_CONDICION, *([AVISO_INEXISTENTE] if nuevo.intencion != "aclaracion" else [])]

    # 6. «¿Cuántos…?» sin pedir quiénes: es un conteo, no una lista.
    if intencion == "filtrar_respondentes" and _CONTEO.search(texto) and not _LISTAR.search(texto) \
            and plan.campos != "todas_las_respuestas":
        notas.append("intención filtrar_respondentes → conteo_porcentaje («cuántos» sin pedir quiénes)")
        intencion = "conteo_porcentaje"
        cambios.update(limite=None, orden=None, campos="solo_ids")

    # 6a. «Dejaron alguna pregunta sin responder» solo si la consulta lo dice: el modelo lo agregó a «de ellos, ¿cuántos
    # no trabajan?» y el conteo dio 0 (7 nov, CEN-03). Lo que viene del plan anterior lo hereda `seguimiento` después.
    if plan.con_omisiones and not cambios.get("con_omisiones") and _criterio_ranking(texto) != "no_respuesta":
        cambios["con_omisiones"] = False
        notas.append("«dejaron alguna sin responder» quitado (la pregunta no lo dice)")

    # 6b. «¿Cuántos usan la meditación como estrategia…?»: un conteo sin condición cuya consulta nombra algo que el
    # instrumento no registra es la condición que no existe; contar a todos («tiene 160 respondentes») era falso
    # (7 nov, CEN-06). Se dice que no existe y qué opciones hay en la pregunta más parecida.
    if intencion in _FILTRADO and not cambios.get("filtros", plan.filtros) and not cambios.get("contexto", plan.contexto) \
            and not cambios.get("contexto_num", plan.contexto_num) and not cambios.get("menciona", plan.menciona) \
            and not cambios.get("con_omisiones", plan.con_omisiones) and not cambios.get("preguntas", plan.preguntas) \
            and _CONTEO.search(texto) and _ausentes(pregunta, cat):
        nuevo = _aclarar_condicion(plan, pregunta, cat)
        return nuevo, notas + [NINGUNA_CONDICION, *([AVISO_INEXISTENTE] if nuevo.intencion != "aclaracion" else [])]

    # 6b2. «¿Cuántos marcaron Verdadero en «la nube elimina…»?» sin pregunta en el plan: el enunciado citado nombra la
    # pregunta (7 nov, PRU-14: el modelo lo puso como mención, se descartó y se contó a todos).
    citados = re.findall(r"«([^»]{8,})»", pregunta)
    if intencion in _FILTRADO and citados and not cambios.get("preguntas", plan.preguntas) and not cambios.get("filtros", plan.filtros):
        if pid := _pregunta_por_texto(citados[0], cat, set()):
            cambios["preguntas"] = [pid]
            notas.append(f"el enunciado citado es {pid}")

    # 6c. «¿Cuántos han hecho prácticas?» resuelto como resumen de una pregunta de sí / no: es contar a quienes dicen
    # «sí» (todas las opciones que empiezan con «Sí»), no mostrar la distribución (7 nov, ENC-13).
    preguntas_6c = cambios.get("preguntas", plan.preguntas)
    if intencion == "resumen_pregunta" and _CONTEO.search(texto) and len(preguntas_6c) == 1 \
            and not cambios.get("filtros", plan.filtros) and not re.search(r"\bno\b", texto):
        q6 = cat.preguntas.get(preguntas_6c[0])
        si = [o for o in (q6.opciones if q6 else []) if normalizar(o).split(" ")[0].strip(",.") == "si"]
        if q6 and si and len(si) < len(q6.opciones) and not [o for o in q6.opciones if _menciona(texto, o)]:
            intencion = "conteo_porcentaje"
            cambios["filtros"] = [Filtro(pregunta=preguntas_6c[0], valor=si if len(si) > 1 else si[0])]
            notas.append(f"«¿cuántos…?» sobre {preguntas_6c[0]}: se cuentan las respuestas que empiezan con «Sí»")

    # 7. «¿Cuántos marcaron Verdadero en el reactivo de la nube?»: el conteo de UNA opción escrita tal cual es una
    # condición, no el resumen de la pregunta. Sin ella, el seguimiento «de ellos, ¿qué respondieron…?» no tenía grupo
    # que heredar (7 nov, PRU-14 y CEN-03).
    preguntas_final = cambios.get("preguntas", plan.preguntas)
    q7 = cat.preguntas.get(preguntas_final[0]) if len(preguntas_final) == 1 else None
    # El nivel solo cuenta en una pregunta de escala (en un reactivo de verdadero o falso el modelo ponía «acuerdo»).
    if intencion == "conteo_porcentaje" and not cambios.get("filtros", plan.filtros) and q7 is not None \
            and not (cambios.get("nivel", plan.nivel) and _es_escala(q7)):
        # Solo las opciones de ESA pregunta: «Verdadero» está en todos los reactivos de verdadero o falso y
        # `_opciones_mencionadas` exige que la opción sea de una sola pregunta del instrumento.
        dichas = [o for o in q7.opciones if _menciona(texto, o)]
        dichas = [o for o in dichas if not any(o != x and normalizar(o) in normalizar(x) for x in dichas)]
        if dichas:
            cambios["filtros"] = [Filtro(pregunta=preguntas_final[0], valor=dichas[0] if len(dichas) == 1 else dichas)]
            cambios["nivel"] = None
            notas.append(f"conteo de {preguntas_final[0]} = «{', '.join(dichas)}» como condición (la consulta nombra la opción)")

    if intencion != plan.intencion:
        cambios["intencion"] = intencion
    return (plan.model_copy(update=cambios) if cambios else plan), notas


def _condiciones_de(texto: str, cat: Catalogo) -> list[Filtro]:
    """Condiciones que una pregunta dice explícitamente: opciones escritas tal cual y, si una palabra nombra una sola
    pregunta de opciones «Sí…»/«No…» («alguna certificación»), sus opciones «Sí…» (o «No…» con «sin», «no», «ningún»)."""
    if not texto:
        return []
    salida = [Filtro(pregunta=pid, valor=ops[0] if len(ops) == 1 else ops) for pid, ops in _opciones_mencionadas(texto, cat).items()]
    usadas = {f.pregunta for f in salida}
    for palabra in {t for t in re.findall(r"[a-z]+", texto) if len(t) >= 6}:
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


def _comparar_por(var: str, intencion: str, cambios: dict, notas: list[str]) -> str:
    """«contra los que no» / «frente a»: comparación de los grupos de `var` en lugar de quedarse con uno."""
    cambios.update(agrupar_por=var, contexto={}, limite=None, orden=None, campos="solo_ids")
    notas.append(f"comparar por {var} («contra» o dos de sus valores en la pregunta)")
    if intencion != "comparar_grupos":
        notas.append(f"intención {intencion} → comparar_grupos")
    return "comparar_grupos"


def _raices_explicadas(plan: PlanConsulta, cambios: dict, filtros: list[Filtro], cat: Catalogo) -> set[str]:
    """Raíces que ya explica alguna condición del plan (sus opciones, sus preguntas, sus variables de contexto)."""
    raices: set[str] = set()
    for f in filtros:
        raices |= set().union(*(enrutador._raices(str(v)) for v in _valores(f))) if _valores(f) else set()
        if f.pregunta in cat.preguntas:
            raices |= enrutador._raices(cat.preguntas[f.pregunta].texto)
    for k, v in cambios.get("contexto", plan.contexto).items():
        raices |= enrutador._raices(f"{k.replace('_', ' ')} {v}")
    for c in cambios.get("contexto_num", plan.contexto_num):
        raices |= enrutador._raices(c.variable.replace("_", " "))
    for q in cambios.get("preguntas", plan.preguntas):
        if q in cat.preguntas:
            raices |= enrutador._raices(cat.preguntas[q].texto)
    return raices


def _vocabulario(cat: Catalogo) -> set[str]:
    """Raíces de todo lo que el instrumento registra: título, preguntas, opciones y datos de contexto."""
    partes = [cat.titulo, *(p.texto for p in cat.preguntas.values()), *(o for p in cat.preguntas.values() for o in p.opciones),
              *(k.replace("_", " ") for k in (*cat.contexto, *cat.numericas)), *(v for vs in cat.contexto.values() for v in vs)]
    return set().union(*(enrutador._raices(t) for t in partes)) if partes else set()


def _palabras_del_catalogo(cat: Catalogo) -> list[str]:
    partes = [cat.titulo, *(p.texto for p in cat.preguntas.values()), *(o for p in cat.preguntas.values() for o in p.opciones),
              *(k.replace("_", " ") for k in (*cat.contexto, *cat.numericas)), *(v for vs in cat.contexto.values() for v in vs)]
    return sorted({w for t in partes for w in re.findall(r"[a-z]+", normalizar(t)) if len(w) >= 5})


_PARECIDO_ERRATA = 0.8


_CANTIDAD = re.compile(r"\b(?:mas|menos) de (\d+)\b")


def _por_cantidad_escrita(filtros: list[Filtro], texto: str, notas: list[str]) -> list[Filtro]:
    """«¿Cuántos trabajan más de 30 horas?»: si una opción dice «más de 30» tal cual, esa es la condición. Se quitan las
    demás opciones de esa pregunta que la raíz había sumado («Trabajo 20-30h», «Trabajo menos de 20h») y los filtros
    de otras preguntas armados con el mismo número (8 nov, Fase 5, CEN-01: salía «1 estudiante» con un filtro «30
    horas» en las horas de estudio)."""
    m = _CANTIDAD.search(texto)
    if not m:
        return filtros
    frase, numero = m.group(0), m.group(1)
    exactos = []
    salida = []
    for f in filtros:
        valores = _valores(f)
        con_frase = [v for v in valores if frase in normalizar(str(v))]
        if con_frase and len(con_frase) < len(valores):
            notas.append(f"filtro {f.pregunta}: solo «{', '.join(map(str, con_frase))}» (dice «{frase}» tal cual)")
            f = Filtro(pregunta=f.pregunta, op="=", valor=con_frase[0] if len(con_frase) == 1 else con_frase)
        if con_frase:
            exactos.append(f.pregunta)
        salida.append(f)
    if not exactos:
        return filtros
    mismo_numero = re.compile(rf"(?<!\d){numero}(?!\d)")
    quedan = []
    for f in salida:
        if f.pregunta not in exactos and any(mismo_numero.search(normalizar(str(v))) for v in _valores(f)):
            notas.append(f"filtro {f.pregunta} = «{f.valor}» quitado (el número ya es la opción de {exactos[0]})")
            continue
        quedan.append(f)
    return quedan


def _ausentes(pregunta: str, cat: Catalogo) -> list[str]:
    """Palabras de la consulta que el instrumento no registra en ninguna parte («nocturna», «ingeniería»).

    Una errata no es una palabra ausente (7 nov, Fase 3): «laboartorios» o «presencal» se parecen ≥ 80 % a una palabra
    del catálogo y no se responde que el instrumento «no registra» eso."""
    vocabulario = _vocabulario(cat)
    completas: list[str] | None = None
    salida = []
    for palabra in re.findall(r"\w+", pregunta):
        n = normalizar(palabra)
        if len(n) >= 5 and n.isalpha() and n not in enrutador._STOP_FILTRO and n[:5] not in vocabulario \
                and n[:5] not in _VERBOS_CONSULTA and palabra not in salida:
            completas = completas if completas is not None else _palabras_del_catalogo(cat)
            if difflib.get_close_matches(n, completas, n=1, cutoff=_PARECIDO_ERRATA):
                continue
            salida.append(palabra)
    return salida[:3]


# Verbos y palabras de la consulta que no nombran una condición («¿cuántos ESTUDIAN…?», «¿quiénes LLEVAN…?»).
_VERBOS_CONSULTA = {"estud", "lleva", "tiene", "hacen", "estan", "fuero", "eligi", "respo", "conte", "dijer", "cuant",
                    "quien", "cuale", "porce", "mayor", "menor", "hubie", "habia", "puede", "deber", "sabes",
                    "dimel", "decir", "mostr", "segun", "entre", "sobre", "donde", "cuand", "aquel", "ellos", "ellas",
                    "dicen", "digan", "opina", "piens", "creen",
                    # Palabras que nombran partes del instrumento, no una condición: «el REACTIVO de Wi-Fi» no es
                    # algo que la prueba «no registra» (8 nov, Fase 5, PRU-06).
                    "react", "pregu", "opcio", "respu", "secci", "alumn", "encue", "prueb", "instr", "marca"}


def _aclarar_condicion(plan: PlanConsulta, pregunta: str, cat: Catalogo) -> PlanConsulta:
    """La condición no existe en el instrumento: se dice qué palabra no registra y, si hay una pregunta parecida, cuáles
    son sus opciones reales; si no, qué datos de contexto sí registra. La investigadora pidió que dijera que no existe,
    no que preguntara cuál quiere (consultas 2147 y 2195, 7 nov)."""
    raices = enrutador._raices(normalizar(pregunta))
    ausentes = _ausentes(pregunta, cat)
    inicio = (f"«{cat.titulo}» no registra «{', '.join(ausentes)}»." if ausentes
              else f"No encontré esa condición en «{cat.titulo}».")
    parecida = max(cat.preguntas.values(), key=lambda q: len(raices & enrutador._raices(q.texto)), default=None)
    if parecida is not None and raices & enrutador._raices(parecida.texto) and parecida.opciones:
        # 7 nov (ENC-22): las opciones que sí existen, con cuántos eligieron cada una (el plan calcula su resumen).
        aviso = f"{inicio} En {parecida.id} («{parecida.texto[:80]}») las opciones que sí existen son estas:"
        return PlanConsulta(intencion="resumen_pregunta", preguntas=[parecida.id], instrumentos=plan.instrumentos,
                            aclaracion=aviso[:300])
    elif cat.contexto or cat.numericas:
        mensaje = (f"{inicio} Ninguna pregunta lo pregunta; los datos de contexto que sí registra son: "
                   f"{', '.join([*cat.contexto, *cat.numericas][:10])}.")
    else:
        mensaje = f"{inicio} Ninguna pregunta ni dato de contexto lo registra."
    return PlanConsulta(intencion="aclaracion", instrumentos=plan.instrumentos, aclaracion=mensaje[:300])
