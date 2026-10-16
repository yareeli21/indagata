"""Hablantes y turnos de una entrevista.

Un turno empieza con una etiqueta de hablante al inicio de la línea
(«Entrevistador:», «E:», «María López:», «P -»). Las líneas sin etiqueta continúan
el turno anterior. Para no confundir «Nota: …» o «Objetivo: …» con un hablante,
una etiqueta solo cuenta si aparece al menos dos veces o es una etiqueta de rol
conocida (entrevistador, entrevistado, E, P, R…).

Formatos con varias entrevistas en un archivo (guion aplicado a N personas):
  - Las preguntas numeradas («P1:», «Pregunta 3:») son UN solo hablante («P», el
    entrevistador); el número se conserva en el turno. «R1:» se une a «R».
  - Una línea «RESPONDENTE: R0001» (o PARTICIPANTE, ENTREVISTADO, INFORMANTE, CASO)
    abre la entrevista de una persona: los turnos siguientes llevan `participante`.
  - Las líneas «Clave: valor | Clave: valor» entre esa línea y el primer turno
    (Perfil, Edad, Género…) son el contexto de la persona, no hablantes.
  - Lo que hay antes del primer bloque (título, ID, N° de respondentes…) es el
    preámbulo del archivo y no forma turnos.

El rol se sugiere por la etiqueta y, si no lo dice, por la proporción de turnos
que son preguntas (quien más pregunta suele ser quien entrevista). El
investigador siempre confirma o corrige los roles.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from services.configuracion import normalizar_texto

# Etiqueta al inicio de línea: hasta 4 palabras (o una inicial) seguidas de «:» o « - ».
_ETIQUETA = re.compile(
    r"^\s*(?P<etq>[A-Za-zÁÉÍÓÚÑÜáéíóúñü][\wÁÉÍÓÚÑÜáéíóúñü.]*(?:\s+[\wÁÉÍÓÚÑÜáéíóúñü.]+){0,3}?)\s*(?::|\s[-–—]\s)\s*(?P<texto>.*)$"
)
_MAX_LARGO_ETIQUETA = 35
# «P1», «P 12», «Pregunta 3», «Preg. 4» → «P»;  «R1», «Respuesta 3» → «R».
_NUMERADA = re.compile(r"^(?P<base>p|preg|pregunta|r|resp|respuesta)\.?\s*(?P<n>\d{1,3})$", re.I)
_BASE_NUMERADA = {"p": "P", "preg": "P", "pregunta": "P", "r": "R", "resp": "R", "respuesta": "R"}
# «RESPONDENTE: R0001», «Participante 3», «ENTREVISTADO #E02», «Caso: 7».
_BLOQUE = re.compile(
    r"^\s*(?P<etq>respondente|participante|entrevistad[oa]|informante|caso)\s*(?:n[°º.o]*\s*)?[:#\-–]?\s*(?P<id>[\w\-]{1,20})\s*$",
    re.I,
)
# «Edad: 23 | Género: masculino | Semestre: 3» (uno o varios pares separados por «|»).
_PAR = re.compile(r"^\s*(?P<clave>[^:|]{1,40}?)\s*:\s*(?P<valor>[^|]*?)\s*$")
_FIN = re.compile(r"^\s*(?:fin(?:\s+del?\s+(?:instrumento|documento|entrevista|archivo))?|[=\-_─━*·•.]{3,})\s*\.?\s*$", re.I)


@dataclass
class Turno:
    hablante: str
    texto: str
    participante: str = ""
    numero: int | None = None  # número de la pregunta («P3» → 3)


@dataclass
class Hablante:
    nombre: str
    turnos: int = 0
    palabras: int = 0
    preguntas: int = 0
    numerada: bool = False  # etiqueta formada por preguntas numeradas («P1», «P2»…)
    ejemplos: list[str] = field(default_factory=list)

    @property
    def proporcion_preguntas(self) -> float:
        return self.preguntas / self.turnos if self.turnos else 0.0


@dataclass
class Participante:
    id: str
    contexto: dict[str, str] = field(default_factory=dict)


@dataclass
class Estructura:
    reconocida: bool
    turnos: list[Turno]
    hablantes: list[Hablante]
    participantes: list[Participante] = field(default_factory=list)
    preambulo: list[str] = field(default_factory=list)


def _etiqueta(linea: str) -> tuple[str, str] | None:
    m = _ETIQUETA.match(linea)
    if not m:
        return None
    etq = m.group("etq").strip().rstrip(".")
    if len(etq) > _MAX_LARGO_ETIQUETA or not m.group("texto").strip() and etq.count(" ") > 1:
        return None
    return etq, m.group("texto").strip()


def _canonica(etq: str) -> tuple[str, int | None]:
    """«P3» → («P», 3); el resto queda igual."""
    m = _NUMERADA.match(etq.strip())
    if m:
        return _BASE_NUMERADA[m.group("base").lower()], int(m.group("n"))
    return etq, None


def _bloque(linea: str) -> str | None:
    """ID del participante si la línea abre su entrevista. El ID debe tener un dígito o la
    etiqueta ir en mayúsculas («Entrevistado: Sí.» es un turno, no un bloque)."""
    m = _BLOQUE.match(linea)
    if not m:
        return None
    ident = m.group("id")
    return ident if any(c.isdigit() for c in ident) or m.group("etq").isupper() else None


def _pares(linea: str) -> dict[str, str] | None:
    """{clave: valor} de una línea de contexto, o None si no lo es."""
    salida: dict[str, str] = {}
    for parte in linea.split("|"):
        m = _PAR.match(parte)
        # Un valor largo o con «?» es un turno («María: ¿Cómo estás?»), no un dato.
        if not m or not m.group("valor") or len(m.group("valor")) > 80 or "?" in m.group("valor"):
            return None
        salida[m.group("clave").strip()] = m.group("valor").strip()
    return salida or None


def _clasificar(lineas: list[str], etiquetas_rol: set[str]) -> tuple[dict[int, str], dict[int, dict[str, str]], set[int]]:
    """Índices de las líneas que abren un bloque, las de contexto y las que se ignoran
    (preámbulo y marcas de fin)."""
    bloques = {i: b for i, l in enumerate(lineas) if (b := _bloque(l))}
    contexto: dict[int, dict[str, str]] = {}
    ignorar: set[int] = {i for i, l in enumerate(lineas) if _FIN.match(l)}
    if not bloques:
        return bloques, contexto, ignorar
    ignorar |= set(range(min(bloques)))  # preámbulo del archivo
    for inicio in bloques:
        for i in range(inicio + 1, len(lineas)):
            linea = lineas[i]
            if not linea.strip():
                continue
            if i in bloques:
                break
            e = _etiqueta(linea)
            if e:
                base, numero = _canonica(e[0])
                # El primer turno real (P1:, Entrevistador:…) cierra el encabezado.
                if numero is not None or normalizar_texto(base) in etiquetas_rol:
                    break
            pares = _pares(linea)
            if pares is None:
                break
            contexto[i] = pares
    return bloques, contexto, ignorar


def segmentar(texto: str, etiquetas_rol: set[str]) -> Estructura:
    """Divide el texto en turnos por hablante (o en párrafos si no hay estructura)."""
    lineas = texto.split("\n")
    bloques, contexto, ignorar = _clasificar(lineas, etiquetas_rol)
    especiales = set(bloques) | set(contexto) | ignorar

    etiquetadas: dict[int, tuple[str, str, int | None]] = {}
    for i, l in enumerate(lineas):
        if i in especiales or not (e := _etiqueta(l)):
            continue
        base, numero = _canonica(e[0])
        etiquetadas[i] = (base, e[1], numero)
    candidatas = Counter(b for b, _, _ in etiquetadas.values())
    numeradas = {b for b, _, n in etiquetadas.values() if n is not None}
    validas = {e for e, n in candidatas.items() if n >= 2 or normalizar_texto(e) in etiquetas_rol}

    participantes: list[Participante] = []
    turnos: list[Turno] = []
    if len(validas) >= 2:
        actual = ""
        for i, linea in enumerate(lineas):
            if i in bloques:
                actual = bloques[i]
                participantes.append(Participante(actual))
                continue
            if i in contexto:
                participantes[-1].contexto.update(contexto[i])
                continue
            if i in ignorar:
                continue
            e = etiquetadas.get(i)
            if e and e[0] in validas:
                turnos.append(Turno(e[0], e[1], actual, e[2]))
            elif linea.strip():
                if turnos and turnos[-1].participante == actual:
                    turnos[-1].texto = f"{turnos[-1].texto} {linea.strip()}".strip()
                else:
                    turnos.append(Turno("", linea.strip(), actual))  # texto previo al primer hablante
        turnos = [t for t in turnos if t.texto]
        con_hablante = [t for t in turnos if t.hablante]
        # Estructura reconocida si al menos 2 hablantes y la mayoría del texto está en turnos.
        palabras_total = sum(len(t.texto.split()) for t in turnos) or 1
        palabras_con = sum(len(t.texto.split()) for t in con_hablante)
        if len({t.hablante for t in con_hablante}) >= 2 and palabras_con / palabras_total >= 0.6:
            preambulo = [lineas[i].strip() for i in sorted(ignorar) if i < min(bloques, default=0) and lineas[i].strip() and not _FIN.match(lineas[i])]
            return Estructura(True, turnos, _resumen(con_hablante, numeradas), participantes, preambulo)

    # Sin estructura de hablantes: un turno por párrafo (bloques separados por línea en blanco).
    parrafos = [" ".join(p.split()) for p in re.split(r"\n\s*\n", texto) if p.strip()]
    if len(parrafos) <= 1:
        parrafos = [l.strip() for l in lineas if l.strip()]
    return Estructura(False, [Turno("", p) for p in parrafos], [])


def _resumen(turnos: list[Turno], numeradas: set[str]) -> list[Hablante]:
    por_nombre: dict[str, Hablante] = {}
    for t in turnos:
        h = por_nombre.setdefault(t.hablante, Hablante(t.hablante, numerada=t.hablante in numeradas))
        h.turnos += 1
        h.palabras += len(t.texto.split())
        if "?" in t.texto:
            h.preguntas += 1
        if len(h.ejemplos) < 2:
            h.ejemplos.append(t.texto[:90] + ("…" if len(t.texto) > 90 else ""))
    return sorted(por_nombre.values(), key=lambda h: -h.turnos)


def sugerir_roles(
    hablantes: list[Hablante], entrevistador: set[str], entrevistado: set[str]
) -> dict[str, tuple[str | None, str]]:
    """{hablante: (rol sugerido o None si es ambiguo, motivo)}."""
    salida: dict[str, tuple[str | None, str]] = {}
    for h in hablantes:
        n = normalizar_texto(h.nombre)
        primera = n.split()[0] if n else ""
        if h.numerada and h.nombre == "P" and h.proporcion_preguntas >= 0.5:
            salida[h.nombre] = ("entrevistador", "porque sus turnos son las preguntas numeradas del guion")
        elif n in entrevistador or primera in entrevistador:
            salida[h.nombre] = ("entrevistador", "por su etiqueta")
        elif n in entrevistado or primera in entrevistado:
            salida[h.nombre] = ("entrevistado", "por su etiqueta")
    sin_rol = [h for h in hablantes if h.nombre not in salida]
    if sin_rol:
        ya_hay_entrevistador = any(r == "entrevistador" for r, _ in salida.values())
        orden = sorted(sin_rol, key=lambda h: -h.proporcion_preguntas)
        mayor = orden[0]
        # Quien más pregunta (con margen claro) se sugiere como entrevistador.
        empate = len(orden) > 1 and abs(orden[1].proporcion_preguntas - mayor.proporcion_preguntas) < 0.15
        for h in sin_rol:
            if not ya_hay_entrevistador and h is mayor and mayor.proporcion_preguntas >= 0.3 and not empate:
                salida[h.nombre] = ("entrevistador", f"porque hace preguntas en el {round(h.proporcion_preguntas * 100)} % de sus turnos")
            elif ya_hay_entrevistador or (not empate and mayor.proporcion_preguntas >= 0.3):
                salida[h.nombre] = ("entrevistado", "porque responde más de lo que pregunta")
            else:
                salida[h.nombre] = (None, "no se pudo inferir")
    return salida
