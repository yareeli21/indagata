"""Transcripciones automáticas (Whisper, Teams, Zoom, subtítulos) → texto con etiquetas de hablante.

Se aplica antes del ciclo de limpieza de ruido (`motores/texto.py`, que ya quita las
marcas de tiempo al inicio de línea, entre corchetes y los rangos «00:00:01 --> …»).
Aquí se resuelve lo que ese ciclo no puede:

  - WebVTT: la cabecera «WEBVTT», los bloques «NOTE» y los números de cue.
  - Teams (VTT): «<v Ana López>Texto</v>» → «Ana López: Texto».
  - Zoom / Teams (TXT): la etiqueta en su propia línea con la hora AL FINAL
    («Hablante 1   00:03» o «Ana López 0:03:12») y el texto en las líneas siguientes
    → «Hablante 1: texto».
  - Muletillas aisladas («eh», «em», «mmm», «ehm»): solo como palabra suelta, nunca dentro de
    otra palabra. Se quitan únicamente si el investigador lo decide (pueden expresar duda o
    incomodidad); `buscar_muletillas` las muestra en su frase. Lista en `config/limpieza.yaml`.
  - Minuto pegado a la etiqueta («Entrevistada (min 23):», «E [12 min]:»): se quita para que la
    etiqueta se reconozca; antes esa respuesta se pegaba a la pregunta anterior.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_TIEMPO = r"\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d{1,3})?"
_CABECERA_VTT = re.compile(r"^\s*WEBVTT\b.*$", re.I)
_NOTA_VTT = re.compile(r"^\s*NOTE\b")
_RANGO = re.compile(rf"^\s*{_TIEMPO}\s*-->\s*{_TIEMPO}.*$")
_NUMERO_CUE = re.compile(r"^\s*\d{1,5}\s*$")
_VOZ = re.compile(r"<v(?:\.[\w.-]+)?\s+([^>]{1,60})>(.*?)(?:</v>|$)", re.I)
_ETIQUETAS_HTML = re.compile(r"</?[a-z][^>]{0,40}>", re.I)
# «Hablante 1   00:03», «Ana López 0:03:12», «Speaker 2 (00:01:05)»: solo la etiqueta y la hora.
_MINUTO_EN_ETIQUETA = re.compile(
    r"^(?P<etq>\s*[A-Za-zÁÉÍÓÚÑÜáéíóúñü][\wÁÉÍÓÚÑÜáéíóúñü. ]{0,34}?)\s*[\[(]\s*"
    r"(?:min(?:uto)?s?\.?\s*\d{1,3}(?::\d{2})?|\d{1,3}\s*(?:min|mins|minutos?|seg|s)\.?)\s*[\])]\s*:",
    re.I | re.M,
)
_ENCABEZADO = re.compile(rf"^\s*(?P<h>[A-Za-zÁÉÍÓÚÑÜáéíóúñü][\wÁÉÍÓÚÑÜáéíóúñü.]*(?:\s+[\wÁÉÍÓÚÑÜáéíóúñü.]+){{0,3}}?)\s+[\[(]?{_TIEMPO}[\])]?\s*$")


@dataclass
class Normalizacion:
    texto: str
    formato: str | None = None   # webvtt | encabezados_con_hora | None
    cambios: dict[str, int] = field(default_factory=dict)


def _muletillas(patrones: list[str]) -> re.Pattern[str] | None:
    if not patrones:
        return None
    alternativas = "|".join(f"(?:{p})" for p in patrones)
    # Palabra suelta, con la coma o los puntos suspensivos que la acompañan.
    return re.compile(rf"(?<![\wÁÉÍÓÚÑÜáéíóúñü])(?:{alternativas})(?![\wÁÉÍÓÚÑÜáéíóúñü])\s*[,…]*(?:\.\.\.)?\s*", re.I)


def buscar_muletillas(texto: str, patrones: list[str]) -> list[str]:
    """Cada muletilla en su frase («… Mmm... Sí, fui a orientación…»), para mostrarla al investigador."""
    patron = _muletillas(patrones)
    if patron is None:
        return []
    frases = []
    for m in patron.finditer(texto):
        if not m.group(0).strip():
            continue
        # La línea de la muletilla, recortada a ~40 caracteres antes y ~50 después.
        inicio = max(texto.rfind("\n", 0, m.start()) + 1, m.start() - 40)
        fin = texto.find("\n", m.end())
        fin = min(fin if fin != -1 else len(texto), m.end() + 50)
        antes = "…" if inicio > 0 and texto[inicio - 1] != "\n" else ""
        despues = "…" if fin < len(texto) and texto[fin] != "\n" else ""
        frases.append(antes + texto[inicio:fin].strip() + despues)
    return frases


def normalizar(texto: str, muletillas: list[str] | None = None) -> Normalizacion:
    lineas = texto.split("\n")
    cambios: dict[str, int] = {}
    formato: str | None = None

    def contar(clave: str, n: int = 1) -> None:
        cambios[clave] = cambios.get(clave, 0) + n

    # 1. WebVTT / SRT: cabecera, notas, rangos y números de cue (solo si hay rangos).
    if any(_RANGO.match(l) for l in lineas):
        salida, en_nota = [], False
        for i, l in enumerate(lineas):
            if _CABECERA_VTT.match(l) or _NOTA_VTT.match(l):
                en_nota = bool(_NOTA_VTT.match(l))
                contar("cabeceras_subtitulos")
                continue
            if en_nota:
                if not l.strip():
                    en_nota = False
                continue
            siguiente = lineas[i + 1] if i + 1 < len(lineas) else ""
            if _RANGO.match(l) or (_NUMERO_CUE.match(l) and _RANGO.match(siguiente)):
                contar("marcas_subtitulos")
                continue
            salida.append(l)
        lineas, formato = salida, "webvtt"

    # 2. Voces de Teams: «<v Ana>texto</v>» → «Ana: texto»; otras etiquetas fuera.
    nuevas = []
    for l in lineas:
        if _VOZ.search(l):
            l = _VOZ.sub(lambda m: f"{m.group(1).strip()}: {m.group(2).strip()}", l)
            contar("voces_teams")
        nuevas.append(_ETIQUETAS_HTML.sub("", l))
    lineas = nuevas

    # 3. Encabezados con hora al final: la etiqueta pasa al inicio de su texto.
    encabezados = [i for i, l in enumerate(lineas) if _ENCABEZADO.match(l)]
    if len(encabezados) >= 2:
        salida, actual, partes = [], None, []

        def cerrar() -> None:
            if actual and partes:
                salida.append(f"{actual}: {' '.join(partes)}")

        for i, l in enumerate(lineas):
            if i in encabezados:
                cerrar()
                actual, partes = _ENCABEZADO.match(l).group("h").strip(), []
                contar("encabezados_con_hora")
            elif actual is not None and l.strip():
                partes.append(l.strip())
            elif actual is None:
                salida.append(l)
        cerrar()
        lineas, formato = salida, formato or "encabezados_con_hora"

    texto = "\n".join(lineas)
    # 4. Minuto pegado a la etiqueta del hablante.
    texto, n = _MINUTO_EN_ETIQUETA.subn(r"\g<etq>:", texto)
    if n:
        contar("minutos_en_etiqueta", n)
    # 5. Muletillas aisladas.
    if (patron := _muletillas(muletillas or [])) is not None:
        texto, n = patron.subn(lambda m: " " if m.group(0).strip() else m.group(0), texto)
        if n:
            contar("muletillas", n)
        texto = re.sub(r"[ \t]{2,}", " ", texto)
        texto = re.sub(r"(?m)^(\s*[^:\n]{1,40}:)\s+([,.])\s*", r"\1 ", texto)
    return Normalizacion(texto, formato, cambios)
