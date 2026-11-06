"""Lectura heurística del instrumento original (el cuestionario sin respuestas).

Del texto plano (PDF/DOCX/TXT ya extraído por storage-service) obtiene:
  - secciones   («## Título», «Sección 2: …», «PARTE I», líneas cortas en MAYÚSCULAS),
  - preguntas   (numeradas «3.», «3)», «P3.», «Reactivo 3:», o con «?» / «¿»),
  - opciones    («A) …», «a. …», «(b) …», «- …», «• …») con su letra si la tienen,
  - anclas      de escalas («1 = Nada … 5 = Mucho», «1 (Nunca) a 5 (Siempre)»).

Es tolerante: lo que no reconoce se ignora y el perfil cae a los encabezados del
archivo limpio. Nunca inventa preguntas.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

SECCION_GENERAL = "General"
_NO_SON_SECCION = {"instrucciones", "instruccion", "indicaciones", "indicacion"}
_MAX_PREGUNTAS = 400
_MAX_OPCIONES = 20

_RE_SECCION = re.compile(
    r"^(secci[oó]n|parte|bloque|unidad|m[oó]dulo|apartado|dimensi[oó]n|eje|tema)\b.{0,90}$", re.IGNORECASE
)
# «3. ¿Qué…?», «3) …», «P3. …», «Pregunta 3: …», «Reactivo 3 - …», «Ítem 3. …»
_RE_NUMERADA = re.compile(
    r"^(?:(?:p|pregunta|reactivo|[ií]tem|item)\s*)?(\d{1,3})\s*[\.\)\-:]\s+(.{3,})$", re.IGNORECASE
)
# Turnos de un guion de entrevista: «E: …», «Entrevistador: …»
_RE_TURNO = re.compile(
    r"^(entrevistador[a]?|investigador[a]?|moderador[a]?|pregunta|e)\s*\d*\s*[:\.\-]\s*(.+)$", re.IGNORECASE
)
# Opciones con letra («A) …», «a. …», «(b) …») o con viñeta («- …», «• …», «○ …», «☐ …»).
_RE_OPCION_LETRA = re.compile(r"^\(?\s*([a-hA-H])\s*[\.\)]\s+(.+)$")
_RE_OPCION_VINETA = re.compile(r"^[-•*○◦☐□▪]\s+(.+)$")
# Anclas: «1 = Nada», «5: Mucho», «1 - Nunca», «1 (Nunca)».
_RE_ANCLA = re.compile(r"(?<![\d.])(\d{1,2})\s*(?:=|:|–|-)\s*([A-Za-zÁÉÍÓÚÑáéíóúñü][^,;=()\d]{0,40}?)(?=\s*(?:[,;]|\d{1,2}\s*(?:=|:|–|-|\()|$|\)))")
_RE_ANCLA_PAREN = re.compile(r"(?<![\d.])(\d{1,2})\s*\(\s*([^()\d]{2,40}?)\s*\)")
# Una línea de la escala general de las instrucciones: «1 = Totalmente en desacuerdo / Nunca».
# PDF de Google Forms: la última opción de la pregunta anterior («Cargas máxima», «Siempre») o el pie de página
# («Google no creó ni aprobó este contenido.») queda en la MISMA línea que la pregunta siguiente, separada por dos
# o más espacios: «Siempre  De tus profesores de este periodo, ¿cuántos tienen doctorado?  *» (28 oct).
_HUECO_PDF = re.compile(r"\s{2,}")
_MARCADOR = re.compile(r"^\(?\s*(?:\d{1,3}|[a-hA-H])\s*[.)\-:]?\s*\)?$")  # «1.», «a)»: numeración, no arrastre
_RE_ANCLA_LINEA = re.compile(r"^(\d{1,2})\s*=\s*([^\d=].{1,80})$")


@dataclass
class PreguntaOriginal:
    texto: str
    seccion: str
    numero: int | None = None
    opciones: list[tuple[str | None, str]] = field(default_factory=list)  # (letra, texto)
    anclas: dict[int, str] = field(default_factory=dict)


@dataclass
class InstrumentoOriginal:
    preguntas: list[PreguntaOriginal] = field(default_factory=list)
    # Escala general de las instrucciones (antes de la primera pregunta), que aplica a las
    # preguntas que no traen su propia escala: {1: "Totalmente en desacuerdo / Nunca", …}.
    anclas_globales: dict[int, str] = field(default_factory=dict)
    # Texto completo del original, para reconocer enunciados que el lector no tomó como pregunta.
    texto: str = ""

    @property
    def secciones(self) -> list[str]:
        vistas: list[str] = []
        for p in self.preguntas:
            if p.seccion not in vistas:
                vistas.append(p.seccion)
        return vistas


def normalizar(texto: str) -> str:
    """Minúsculas, sin acentos y con espacios colapsados (para comparar textos)."""
    sin = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    return " ".join(sin.lower().split())


def anclas_de(linea: str) -> dict[int, str]:
    """Anclas de escala en una línea; solo cuenta si hay al menos dos («1 = Nada, 5 = Mucho»)."""
    anclas: dict[int, str] = {}
    for patron in (_RE_ANCLA, _RE_ANCLA_PAREN):
        for m in patron.finditer(linea):
            etiqueta = m.group(2).strip(" .")
            if etiqueta:
                anclas.setdefault(int(m.group(1)), etiqueta)
    return anclas if len(anclas) >= 2 else {}


def _es_titulo_seccion(linea: str) -> bool:
    if "?" in linea or len(linea) > 100:
        return False
    if linea.startswith("#"):
        return linea.startswith("##")  # «# » es el título del documento
    if _RE_SECCION.match(linea):
        return True
    letras = [c for c in linea if c.isalpha()]
    return len(letras) >= 4 and linea.isupper() and len(linea) <= 80


def _sin_arrastre(linea: str) -> str:
    """La línea sin el texto arrastrado de la pregunta anterior o del pie de página (ver `_HUECO_PDF`).

    Solo se quita el primer tramo si no tiene «¿» ni «?», no es numeración («1.», «a)») y lo que sigue sí es una
    pregunta. «En tu opinión, ¿qué…?» no tiene hueco doble y se queda igual.
    """
    tramos = _HUECO_PDF.split(linea.strip())
    if (len(tramos) > 1 and not re.search(r"[¿?]", tramos[0]) and not _MARCADOR.match(tramos[0])
            and len(tramos[0]) <= 80 and re.search(r"[¿?]", " ".join(tramos[1:]))):
        return " ".join(tramos[1:])
    return linea


def leer(texto: str) -> InstrumentoOriginal:
    """Secciones, preguntas, opciones y anclas del instrumento original."""
    resultado = InstrumentoOriginal(texto=texto)
    vistas: set[str] = set()
    seccion = SECCION_GENERAL
    actual: PreguntaOriginal | None = None

    def agregar(contenido: str, numero: int | None = None) -> None:
        nonlocal actual
        contenido = contenido.strip(" *_")
        clave = normalizar(contenido)
        if len(contenido) < 4 or clave in vistas or len(resultado.preguntas) >= _MAX_PREGUNTAS:
            return
        vistas.add(clave)
        actual = PreguntaOriginal(texto=contenido[:600], seccion=seccion, numero=numero, anclas=anclas_de(contenido))
        resultado.preguntas.append(actual)

    for cruda in texto.splitlines():
        linea = _sin_arrastre(cruda).strip().strip("*_").strip()
        if not linea or linea.startswith("# "):
            continue
        if _es_titulo_seccion(linea):
            # Sin decoración: «--- DEDICACIÓN AL ESTUDIO ---» → «DEDICACIÓN AL ESTUDIO».
            seccion = linea.lstrip("# ").strip(" :-=*_—")[:100] or SECCION_GENERAL
            # «INSTRUCCIONES:» encabeza indicaciones, no preguntas: lo que siga es «General».
            if normalizar(seccion) in _NO_SON_SECCION:
                seccion = SECCION_GENERAL
            actual = None
            continue
        if actual is not None and (m := _RE_OPCION_LETRA.match(linea)):
            if len(actual.opciones) < _MAX_OPCIONES:
                actual.opciones.append((m.group(1).upper(), m.group(2).strip()[:200]))
            continue
        if m := _RE_NUMERADA.match(linea):
            agregar(m.group(2), int(m.group(1)))
            continue
        if m := _RE_TURNO.match(linea):
            agregar(m.group(2))
            continue
        if actual is not None and (m := _RE_OPCION_VINETA.match(linea)):
            if len(actual.opciones) < _MAX_OPCIONES:
                actual.opciones.append((None, m.group(1).strip()[:200]))
            continue
        if not resultado.preguntas and (m := _RE_ANCLA_LINEA.match(linea)):
            # Escala general de las instrucciones, una opción por línea.
            resultado.anclas_globales[int(m.group(1))] = m.group(2).strip(" .")
            continue
        if not resultado.preguntas and (anclas := anclas_de(linea)):
            resultado.anclas_globales.update(anclas)
            continue
        if actual is not None and (anclas := anclas_de(linea)):
            # Línea de escala debajo de la pregunta («1 = Nada … 5 = Mucho»).
            actual.anclas.update(anclas)
            continue
        if (actual is not None and actual.texto.count("¿") > actual.texto.count("?") and not linea.startswith("¿")
                and len(actual.texto) + len(linea) <= 600):
            # Pregunta partida en dos líneas («…una materia sin profesor» / «asignado?»): la segunda la completa
            # (28 oct, PDF de Google Forms: los finales de línea se tomaban como preguntas nuevas).
            vistas.discard(normalizar(actual.texto))
            actual.texto = f"{actual.texto} {linea}"
            vistas.add(normalizar(actual.texto))
            continue
        if ("?" in linea or linea.startswith("¿")) and len(linea) <= 400:
            agregar(linea)
    if len(resultado.anclas_globales) < 2:
        resultado.anclas_globales = {}
    return resultado


# ── Emparejamiento con los encabezados del archivo ─────────────────────────────

_VACIAS = {
    "de", "la", "el", "los", "las", "en", "y", "a", "que", "con", "por", "para", "del", "al", "un", "una",
    "tu", "su", "se", "es", "lo", "o", "u", "como", "cual", "mas", "muy", "te", "me", "mi", "sus", "tus",
}


def tokens(texto: str) -> set[str]:
    """Palabras significativas (sin acentos, sin palabras vacías ni números sueltos)."""
    return {t for t in re.findall(r"[a-zñü]+", normalizar(texto)) if len(t) > 2 and t not in _VACIAS}


_MIN_PREFIJO = 25  # caracteres: menos que eso, un inicio común puede ser casualidad («¿Cuál es tu…»)


def _compacto(texto: str) -> str:
    """Solo letras y números separados por un espacio («Cuál_es_tu…» → «cual es tu…»)."""
    return " ".join(re.findall(r"[a-zñü0-9]+", normalizar(texto)))


def parecido(a: str, b: str) -> float:
    """Similitud entre un encabezado y una pregunta del original (0–1).

    Regla no obvia: los encabezados suelen venir TRUNCADOS por la plataforma
    («¿Con qué frecuencia usas la biblioteca…»), así que además de Jaccard se usa
    el coeficiente de solapamiento (∩ / el conjunto menor), pero solo cuando hay
    al menos 3 palabras en común, para que dos palabras genéricas no basten.
    Si el recorte deja menos de 3 palabras o corta la última («…medio de transport»), basta
    con que el encabezado sea el INICIO literal de la pregunta (o al revés) con al menos
    `_MIN_PREFIJO` caracteres.
    """
    ca, cb = _compacto(a), _compacto(b)
    corto, largo = sorted((ca, cb), key=len)
    if len(corto) >= _MIN_PREFIJO and largo.startswith(corto):
        return 0.9
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    comunes = len(ta & tb)
    jaccard = comunes / len(ta | tb)
    solapamiento = comunes / min(len(ta), len(tb)) if comunes >= 3 else 0.0
    return max(jaccard, 0.9 * solapamiento)


UMBRAL_PARECIDO = 0.5


def aparece_en(encabezado: str, original: InstrumentoOriginal) -> bool:
    """¿El encabezado (completo, de al menos `_MIN_PREFIJO` caracteres) está escrito tal cual en el original?

    Caso real (28 oct): el PDF que exporta Google Forms separa los números de las preguntas de su texto, y
    los enunciados de escala («La oferta de programas… responde a mis intereses») no llevan «¿?» ni número,
    así que el lector no los toma como preguntas. Si el encabezado aparece literal en el texto, la pregunta
    sí es del original aunque no se haya podido aislar.
    """
    corto = _compacto(encabezado)
    return len(corto) >= _MIN_PREFIJO and corto in _compacto(original.texto)


def emparejar(etiquetas: list[str], preguntas: list[PreguntaOriginal]) -> dict[int, int]:
    """{índice de etiqueta: índice de pregunta del original}, voraz por mayor parecido.

    Cada pregunta del original se usa a lo más una vez, salvo las cuadrículas: varias
    columnas «Padre [aspecto]» pueden apuntar a la misma pregunta (el padre).
    """
    candidatos = []
    for i, etiqueta in enumerate(etiquetas):
        for j, p in enumerate(preguntas):
            s = parecido(etiqueta, p.texto)
            if s >= UMBRAL_PARECIDO:
                candidatos.append((s, i, j))
    candidatos.sort(key=lambda x: (-x[0], x[1], x[2]))
    asignadas: dict[int, int] = {}
    usadas: set[int] = set()
    for _, i, j in candidatos:
        if i in asignadas or j in usadas:
            continue
        asignadas[i] = j
        usadas.add(j)
    return asignadas
