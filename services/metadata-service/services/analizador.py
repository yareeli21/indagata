"""Análisis del contenido del instrumento para proponer metadatos.

Lee el instrumento A TRAVÉS del storage-service (archivo limpio si existe; si no,
el crudo) y extrae lo que se puede inferir de él:

  - Tabular (encuestas CSV/XLSX): cada columna es un reactivo. Se detecta su tipo
    (Likert, escala numérica, opción múltiple, numérica, abierta), sus opciones y
    estadísticas (n, vacíos, media, distribución). Los encabezados con forma
    «Bloque [ítem]» (Google Forms) definen dimensiones.
  - Documento (entrevistas/pruebas PDF/DOCX/TXT): preguntas numeradas, turnos del
    entrevistador, opciones de respuesta, secciones y hallazgos por expresiones
    regulares (institución, campus, ciclo escolar, grado, grupo, tipo de prueba,
    verbos de la taxonomía de Bloom, metodología…).
  - JSON v1 (instrumentos de la demo): reutiliza su Dublin Core y metadatos.

Nada de esto modifica el archivo. El resultado (`Analisis`) alimenta las
propuestas de dc_manager y enrichment_engine y el JSON estandarizado.
"""
from __future__ import annotations

import json
import logging
import re
import statistics
import threading
import time
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from services import storage_client

logger = logging.getLogger("metadata-service")

SECCION_GENERAL = "Reactivos"
_TABULARES = {".csv", ".xlsx", ".xls"}

# Columnas técnicas de las plataformas de encuestas (no son reactivos).
_COLUMNA_TECNICA = re.compile(
    r"^(marca temporal|timestamp|fecha( y hora)?|hora|direcci[oó]n de correo.*|correo( electr[oó]nico)?|"
    r"e-?mail|id|folio|respondent_id|n[uú]mero de respuesta|response id|ip)$",
    re.IGNORECASE,
)
_COLUMNA_CARRERA = re.compile(r"\b(carrera|programa( educativo)?|licenciatura)\b", re.IGNORECASE)
_ENCABEZADO_BLOQUE = re.compile(r"^(.*?)\s*\[(.+?)\]\s*$")

_STOPWORDS_ES = set(
    """a al algo algunas algunos ante antes aqui asi aun aunque bajo bien cada casi como con contra cual cuales
    cuando cuanto de del desde donde dos el ella ellas ellos en entre era eran es esa esas ese eso esos esta estas
    este esto estos estoy fue fueron ha han hasta hay la las le les lo los mas me mi mis mucho muy nada ni no nos
    nosotros o otra otras otro otros para pero poco por porque que quien quienes se ser si sin sobre su sus tambien
    tan tanto te tiene tienen todo todos tu tus un una unas uno unos usted ustedes y ya yo cual cuales cuanta
    cuantas cuantos sea sean siendo puede pueden hacer hace sido estar esta estan""".split()
)
_STOPWORDS_EN = set(
    "the and of to in is are was were for with that this on as by be or from at it an your you how what".split()
)
# Palabras propias del formato de los instrumentos, sin valor temático.
_GENERICAS = set(
    """pregunta preguntas respuesta respuestas indica siguiente siguientes afirmacion afirmaciones acuerdo desacuerdo
    totalmente escala opcion opciones marca selecciona responde respondes instrumento encuesta entrevista prueba
    favor cada parte seccion item items reactivo reactivos nunca siempre veces frecuencia medida grado ninguno
    ninguna cosas manera forma general alguna alguno""".split()
)
_ACUERDO = ("desacuerdo", "de acuerdo", "acuerdo")
_FRECUENCIA = ("nunca", "casi nunca", "a veces", "algunas veces", "ocasionalmente", "frecuentemente", "casi siempre", "siempre")
_INTENSIDAD = ("nada", "poco", "regular", "moderad", "bastante", "mucho", "muy")

_BLOOM: dict[str, tuple[str, ...]] = {
    "Recordar": ("define", "defina", "identifica", "identifique", "enumera", "enumere", "menciona", "mencione", "nombra", "lista", "recuerda", "cual es", "que es"),
    "Comprender": ("explica", "explique", "describe", "describa", "resume", "resuma", "interpreta", "interprete", "clasifica", "ejemplifica"),
    "Aplicar": ("calcula", "calcule", "resuelve", "resuelva", "aplica", "aplique", "utiliza", "utilice", "demuestra", "determina", "determine"),
    "Analizar": ("analiza", "analice", "compara", "compare", "distingue", "distinga", "examina", "relaciona", "contrasta"),
    "Evaluar": ("evalua", "evalue", "justifica", "justifique", "argumenta", "argumente", "valora", "critica", "juzga", "decide"),
    "Crear": ("disena", "disene", "propone", "proponga", "elabora", "elabore", "crea", "cree", "planea", "construye", "redacta"),
}

_RE_NUMERADA = re.compile(r"^(\d{1,3})\s*[\.\)\-]\s+(.{3,})$")
_RE_OPCION = re.compile(r"^(?:[a-hA-H][\.\)]|[-•*]|\(\s*[a-hA-H]\s*\))\s+(.+)$")
_RE_TURNO = re.compile(
    r"^(entrevistador[a]?|investigador[a]?|moderador[a]?|pregunta|e)\s*\d*\s*[:\.\-]\s*(.+)$", re.IGNORECASE
)
_RE_SECCION = re.compile(
    r"^(secci[oó]n|parte|bloque|unidad|m[oó]dulo|apartado|dimensi[oó]n|eje)\b.{0,90}$", re.IGNORECASE
)


@dataclass
class Pregunta:
    id: str
    texto: str
    tipo: str = ""
    opciones: list[str] = field(default_factory=list)
    seccion: str = SECCION_GENERAL
    estadisticas: dict[str, Any] = field(default_factory=dict)


@dataclass
class Analisis:
    tipo: str
    familia: str  # tabular | documento | json
    titulo: str = ""
    descripcion: str = ""
    texto: str = ""
    preguntas: list[Pregunta] = field(default_factory=list)
    dimensiones: list[str] = field(default_factory=list)
    palabras_clave: list[str] = field(default_factory=list)
    idioma: str = "es"
    n_registros: int | None = None
    n_duplicados: int = 0
    pct_vacios: float | None = None
    carreras: list[str] = field(default_factory=list)
    hallazgos: dict[str, Any] = field(default_factory=dict)
    dc_archivo: dict[str, str] = field(default_factory=dict)
    especificos_archivo: dict[str, Any] = field(default_factory=dict)
    kpi_hints: list[str] = field(default_factory=list)
    notas: list[str] = field(default_factory=list)
    # Claves cuyo valor es una plantilla genérica (el LLM puede mejorarlas).
    plantillas: set[str] = field(default_factory=set)

    def contexto_llm(self) -> str:
        """Resumen textual del instrumento para pedir sugerencias al LLM."""
        partes = [f"Título tentativo: {self.titulo}"]
        if self.dimensiones:
            partes.append("Dimensiones: " + "; ".join(self.dimensiones))
        if self.preguntas:
            partes.append("Reactivos:")
            for p in self.preguntas[:25]:
                linea = f"- {p.texto}"
                if p.opciones:
                    linea += f" (opciones: {', '.join(p.opciones[:6])})"
                partes.append(linea)
        if self.texto:
            partes.append("Texto:\n" + self.texto[:1500])
        return "\n".join(partes)


# ── Utilidades de texto ────────────────────────────────────────────────────────


def sin_acentos(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii").lower()


def _numero(valor: str) -> float | None:
    try:
        return float(valor.replace(",", ".").strip())
    except (ValueError, AttributeError):
        return None


def _capitalizar(texto: str) -> str:
    texto = texto.strip()
    return texto[:1].upper() + texto[1:] if texto else texto


def palabras_clave(textos: list[str], n: int = 8) -> list[str]:
    """Términos más frecuentes (sin palabras vacías ni de formato)."""
    conteo: Counter[str] = Counter()
    original: dict[str, str] = {}
    for texto in textos:
        for palabra in re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{4,}", texto or ""):
            clave = sin_acentos(palabra)
            if clave in _STOPWORDS_ES or clave in _GENERICAS or clave in _STOPWORDS_EN:
                continue
            conteo[clave] += 1
            original.setdefault(clave, palabra.lower())
    return [original[c] for c, _ in conteo.most_common(n)]


def detectar_idioma(texto: str) -> str:
    tokens = [sin_acentos(t) for t in re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", texto[:20000])]
    es = sum(1 for t in tokens if t in _STOPWORDS_ES)
    en = sum(1 for t in tokens if t in _STOPWORDS_EN)
    return "en" if en > es * 1.5 and en > 5 else "es"


def titulo_desde_nombre(nombre: str) -> str:
    raiz = Path(nombre or "instrumento").stem
    raiz = re.sub(r"^(\d+|[0-9a-f]{32})__", "", raiz)
    raiz = re.sub(r"[_\-\.]+", " ", raiz)
    return _capitalizar(re.sub(r"\s+", " ", raiz)) or "Instrumento"


def _oraciones(texto: str) -> list[str]:
    return [o.strip() for o in re.split(r"(?<=[\.\!\?])\s+|\n+", texto) if o.strip()]


def _oracion_con(texto: str, patron: str, minimo: int = 20, maximo: int = 400) -> str:
    regex = re.compile(patron, re.IGNORECASE)
    for oracion in _oraciones(texto):
        if regex.search(oracion) and minimo <= len(oracion) <= maximo:
            return re.sub(r"^(objetivo( general)?|prop[oó]sito)\s*[:\-]\s*", "", oracion, flags=re.IGNORECASE).strip()
    return ""


# ── Perfilado de reactivos tabulares ───────────────────────────────────────────


def _puntaje_likert(valor: str) -> float | None:
    v = sin_acentos(valor)
    if "desacuerdo" in v or "deesacuerdo" in v:
        return 1.0 if ("totalmente" in v or "muy en" in v) else 2.0
    if "ni de acuerdo" in v or "neutral" in v or "indiferente" in v:
        return 3.0
    if "acuerdo" in v:
        return 5.0 if ("totalmente" in v or "muy de" in v) else 4.0
    for puntaje, claves in ((2.0, ("casi nunca",)), (4.0, ("casi siempre", "frecuentemente")), (1.0, ("nunca",)),
                            (5.0, ("siempre",)), (3.0, ("a veces", "algunas veces", "ocasionalmente"))):
        if any(c in v for c in claves):
            return puntaje
    return None


def _perfilar(valores: list[str], n_total: int) -> tuple[str, list[str], dict[str, Any]]:
    n = len(valores)
    conteo = Counter(valores)
    distintos = len(conteo)
    numeros = [_numero(v) for v in valores]
    es_numerico = n > 0 and all(x is not None for x in numeros)
    normalizados = [sin_acentos(v) for v in conteo]
    likert = sum(1 for v in normalizados if any(k in v for k in (*_ACUERDO, *_FRECUENCIA, *_INTENSIDAD)))

    if n == 0:
        tipo = "sin_respuestas"
    elif es_numerico and distintos <= 11 and all(x is not None and x.is_integer() and 0 <= x <= 10 for x in numeros):
        tipo = "escala_numerica"
    elif not es_numerico and distintos <= 10 and likert >= 0.6 * distintos:
        tipo = "likert"
    elif distintos <= 12 and n >= 2 * distintos:
        tipo = "opcion_multiple"
    elif es_numerico:
        tipo = "numerica"
    else:
        tipo = "abierta"

    estadisticas: dict[str, Any] = {"type": tipo, "n": n, "n_vacios": max(n_total - n, 0)}
    if es_numerico and n:
        reales = [x for x in numeros if x is not None]
        estadisticas.update(
            mean=round(statistics.fmean(reales), 3),
            std=round(statistics.pstdev(reales), 3),
            min=min(reales),
            max=max(reales),
        )
    if 0 < distintos <= 20:
        estadisticas["distribution"] = dict(conteo.most_common())

    opciones: list[str] = []
    if tipo == "escala_numerica":
        opciones = sorted(conteo, key=lambda v: _numero(v) or 0.0)
    elif tipo in ("likert", "opcion_multiple"):
        puntajes = {v: _puntaje_likert(v) for v in conteo}
        if all(p is not None for p in puntajes.values()):
            opciones = sorted(conteo, key=lambda v: puntajes[v] or 0.0)
        else:
            opciones = [v for v, _ in conteo.most_common()]
    return tipo, opciones, estadisticas


def _partir_encabezado(encabezado: str) -> tuple[str, str]:
    m = _ENCABEZADO_BLOQUE.match(encabezado)
    if m and m.group(1).strip():
        return m.group(1).strip(), m.group(2).strip()
    return SECCION_GENERAL, encabezado


def etiqueta_dimension(bloque: str) -> str:
    texto = bloque.strip().rstrip(".:")
    m = re.search(r"\bsobre\s+(.+)$", texto, flags=re.IGNORECASE)
    if m:
        texto = m.group(1)
    return _capitalizar(texto)[:80]


# ── Hallazgos por expresiones regulares (documentos) ───────────────────────────


def _buscar(patron: str, texto: str, grupo: int = 1, flags: int = re.IGNORECASE) -> str:
    m = re.search(patron, texto, flags)
    return m.group(grupo).strip(" .,;:") if m else ""


def _nivel_educativo(texto: str) -> str:
    t = sin_acentos(texto)
    for clave, nivel in (
        ("doctorado", "Doctorado"),
        ("maestria", "Maestría"),
        ("posgrado", "Posgrado"),
        ("especialidad", "Posgrado"),
        ("licenciatura", "Licenciatura"),
        ("universitari", "Licenciatura"),
        ("pregrado", "Licenciatura"),
        ("bachillerato", "Bachillerato"),
        ("preparatoria", "Bachillerato"),
        ("media superior", "Bachillerato"),
        ("secundaria", "Secundaria"),
        ("primaria", "Primaria"),
    ):
        if clave in t:
            return nivel
    return ""


def _bloom(preguntas: list[Pregunta]) -> str:
    conteo: Counter[str] = Counter()
    for p in preguntas:
        inicio = sin_acentos(re.sub(r"^[¿\s]+", "", p.texto))[:40]
        for nivel, verbos in _BLOOM.items():
            if any(inicio.startswith(v) for v in verbos):
                conteo[nivel] += 1
                break
    orden = list(_BLOOM)
    return ", ".join(f"{nivel} ({conteo[nivel]})" for nivel in orden if conteo[nivel])


def hallazgos_texto(texto: str, preguntas: list[Pregunta]) -> dict[str, str]:
    h: dict[str, str] = {
        "objetivo": _oracion_con(texto, r"\b(objetivo|prop[oó]sito)\b"),
        "institucion": _buscar(
            r"\b((?:Universidad|Instituto|Escuela|Facultad|Colegio|Centro Universitario|Tecnol[oó]gico)\b[^\n,;:]{3,80})",
            texto,
            flags=0,
        ),
        "campus": _buscar(r"\bcampus\s+([^\n,.;]{2,40})", texto),
        "ciclo_escolar": _buscar(r"\b(20\d{2}\s*[-–/]\s*(?:20)?\d{2}(?:\s*[-–]\s*[12AB])?)\b", texto)
        or _buscar(r"ciclo escolar\s*[:\-]?\s*([^\n]{3,30})", texto),
        "grupo": _buscar(r"\b[Gg]rupo\s*[:\-]?\s*([A-Z0-9]{1,6})\b", texto, flags=0),
        "version": _buscar(r"\bversi[oó]n\s*[:\-]?\s*([A-Za-z0-9][\w\.\-]{0,15})", texto),
        "nivel_educativo": _nivel_educativo(texto),
        "unidad_de_aprendizaje": _buscar(
            r"(?:unidad de aprendizaje|asignatura|materia|curso)\s*[:\-]\s*([^\n]{3,80})", texto
        ),
        "competencias": _buscar(r"competencias?\s*[:\-]\s*([^\n]{5,300})", texto),
        "subareas": _buscar(r"(?:sub[áa]reas?|temas? evaluados?|contenidos?)\s*[:\-]\s*([^\n]{3,200})", texto),
        "poblacion": _oracion_con(texto, r"\b(estudiantes|alumn[oa]s|docentes|profesor(es|as)|egresad[oa]s|padres de familia)\b", 15, 250),
        "taxonomia_bloom": _bloom(preguntas),
    }
    # La oración del objetivo suele mencionar a los estudiantes: no es la población.
    if h["poblacion"] and h["poblacion"] == h["objetivo"]:
        h["poblacion"] = ""
    grado = re.search(r"\b(\d{1,2})\s*(?:°|º|er|do|ro|to|vo|no|o)?\s*(semestre|grado|año|cuatrimestre)\b", texto, re.IGNORECASE)
    h["grado"] = f"{grado.group(1)}° {grado.group(2).lower()}" if grado else ""
    tipo_prueba = _buscar(
        r"\b(diagn[oó]stic[ao]|formativ[ao]|sumativ[ao]|parcial|final|departamental|ordinari[ao]|extraordinari[ao]|de admisi[oó]n)\b",
        texto,
    )
    h["tipo_de_prueba"] = _capitalizar(tipo_prueba)
    metodologia = sin_acentos(_buscar(r"\b(semi[- ]?estructurada|no estructurada|estructurada|a profundidad|grupo focal)\b", texto))
    h["metodologia"] = {
        "semiestructurada": "Entrevista semiestructurada",
        "semi-estructurada": "Entrevista semiestructurada",
        "semi estructurada": "Entrevista semiestructurada",
        "no estructurada": "Entrevista no estructurada",
        "estructurada": "Entrevista estructurada",
        "a profundidad": "Entrevista a profundidad",
        "grupo focal": "Grupo focal",
    }.get(metodologia, "")
    return {k: v for k, v in h.items() if v}


# ── Documentos ─────────────────────────────────────────────────────────────────


def _es_titulo_seccion(linea: str) -> bool:
    if "?" in linea or len(linea) > 100:
        return False
    if linea.startswith("#"):
        return linea.startswith("##")  # "# " es el título del documento
    if _RE_SECCION.match(linea):
        return True
    letras = [c for c in linea if c.isalpha()]
    return len(letras) >= 4 and linea.isupper() and len(linea) <= 80


def extraer_preguntas(texto: str) -> list[Pregunta]:
    preguntas: list[Pregunta] = []
    vistas: set[str] = set()
    seccion = SECCION_GENERAL
    actual: Pregunta | None = None

    def agregar(contenido: str) -> None:
        nonlocal actual
        contenido = contenido.strip(" *_")
        clave = sin_acentos(contenido)
        if len(contenido) < 4 or clave in vistas or len(preguntas) >= 300:
            return
        vistas.add(clave)
        actual = Pregunta(id=f"q{len(preguntas) + 1}", texto=contenido[:500], seccion=seccion)
        preguntas.append(actual)

    for cruda in texto.splitlines():
        linea = cruda.strip().strip("*_").strip()
        if not linea or linea.startswith("# "):
            continue
        if _es_titulo_seccion(linea):
            seccion = linea.lstrip("# ").strip()[:80] or SECCION_GENERAL
            actual = None
            continue
        if m := _RE_TURNO.match(linea):
            agregar(m.group(2))
            continue
        if m := _RE_NUMERADA.match(linea):
            agregar(m.group(2))
            continue
        if actual is not None and (m := _RE_OPCION.match(linea)):
            opcion = m.group(1).strip()
            if opcion and len(actual.opciones) < 15:
                actual.opciones.append(opcion[:120])
            continue
        if ("?" in linea or linea.startswith("¿")) and len(linea) <= 400:
            agregar(linea)
            continue
    for p in preguntas:
        p.tipo = "opcion_multiple" if p.opciones else "abierta"
    return preguntas


def _titulo_documento(texto: str, nombre: str) -> str:
    for cruda in texto.splitlines()[:15]:
        linea = cruda.strip().lstrip("#").strip().strip("*_").strip()
        if 4 <= len(linea) <= 120 and "?" not in linea and not _RE_NUMERADA.match(linea):
            return linea
    return titulo_desde_nombre(nombre)


# ── Construcción del análisis ──────────────────────────────────────────────────


def _desde_tabla(tabla: dict[str, Any], tipo: str, nombre: str, texto_original: str) -> Analisis:
    headers: list[str] = tabla.get("headers") or []
    filas: list[list[str]] = tabla.get("rows") or []
    indices = [j for j, h in enumerate(headers) if h and not _COLUMNA_TECNICA.match(h.strip())]

    preguntas: list[Pregunta] = []
    bloques: list[str] = []
    vacias = 0
    for k, j in enumerate(indices, start=1):
        bloque, texto = _partir_encabezado(headers[j])
        valores = [f[j] for f in filas if j < len(f) and f[j].strip()]
        vacias += len(filas) - len(valores)
        tipo_p, opciones, stats = _perfilar(valores, len(filas))
        preguntas.append(Pregunta(f"q{k}", texto, tipo_p, opciones[:15], bloque, stats))
        if bloque != SECCION_GENERAL and bloque not in bloques:
            bloques.append(bloque)

    carreras: list[str] = []
    for j, h in enumerate(headers):
        if _COLUMNA_CARRERA.search(h):
            conteo = Counter(f[j] for f in filas if j < len(f) and f[j].strip())
            carreras = [c for c, _ in conteo.most_common(8)]
            break

    dimensiones = [etiqueta_dimension(b) for b in bloques]
    n = int(tabla.get("n_filas") or len(filas))
    titulo = _titulo_documento(texto_original, nombre) if texto_original else titulo_desde_nombre(nombre)
    tipo_ui = {"encuesta": "Encuesta", "entrevista": "Entrevista"}.get(tipo, "Instrumento")
    descripcion = f"{tipo_ui} de {len(preguntas)} reactivos aplicada a {n} respondentes."
    if dimensiones:
        descripcion += " Explora: " + "; ".join(d.lower() for d in dimensiones) + "."

    textos = [p.texto for p in preguntas] + bloques + [texto_original]
    analisis = Analisis(
        tipo=tipo,
        familia="tabular",
        titulo=titulo,
        descripcion=descripcion,
        texto=texto_original,
        preguntas=preguntas,
        dimensiones=dimensiones,
        palabras_clave=palabras_clave(textos),
        idioma=detectar_idioma(" ".join(textos)),
        n_registros=n,
        n_duplicados=len(filas) - len({tuple(f) for f in filas}),
        pct_vacios=round(vacias / (len(filas) * len(indices)), 4) if filas and indices else None,
        carreras=carreras,
        hallazgos=hallazgos_texto(texto_original + "\n" + "\n".join(bloques), preguntas),
        notas=list(tabla.get("notas") or []),
        plantillas={"dc_description"},
    )
    if not texto_original:
        analisis.plantillas.add("dc_title")
    if carreras:
        analisis.hallazgos.setdefault("poblacion", f"Estudiantes de {', '.join(carreras[:5])}")
    if tabla.get("truncado"):
        analisis.notas.append("Las estadísticas se calcularon con las primeras filas del archivo.")
    return analisis


def _desde_documento(texto: str, tipo: str, nombre: str) -> Analisis:
    preguntas = extraer_preguntas(texto)
    secciones: list[str] = []
    for p in preguntas:
        if p.seccion != SECCION_GENERAL and p.seccion not in secciones:
            secciones.append(p.seccion)
    tipo_ui = {"entrevista": "Guía de entrevista", "prueba_estandarizada": "Prueba"}.get(tipo, "Instrumento")
    titulo = _titulo_documento(texto, nombre)
    descripcion = _oracion_con(texto, r".", 60, 400) or f"{tipo_ui} con {len(preguntas)} preguntas."
    hallazgos = hallazgos_texto(texto, preguntas)
    if tipo == "prueba_estandarizada" and preguntas:
        mapeo = Counter(p.seccion for p in preguntas)
        hallazgos["mapeo_de_reactivos_por_seccion"] = dict(mapeo)
    analisis = Analisis(
        tipo=tipo,
        familia="documento",
        titulo=titulo,
        descripcion=descripcion,
        texto=texto,
        preguntas=preguntas,
        dimensiones=secciones,
        palabras_clave=palabras_clave([texto]),
        idioma=detectar_idioma(texto),
        hallazgos=hallazgos,
        plantillas={"dc_description"},
    )
    if not texto.strip():
        analisis.notas.append("No se pudo extraer texto del documento (¿PDF escaneado?).")
    return analisis


def _desde_json(data: dict[str, Any], tipo: str) -> Analisis:
    instrumento = data.get("instrument") if isinstance(data.get("instrument"), dict) else {}
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    dc_crudo = metadata.get("dublin_core") if isinstance(metadata.get("dublin_core"), dict) else {}
    especificos = metadata.get("survey_specific") if isinstance(metadata.get("survey_specific"), dict) else {}
    por_pregunta = (data.get("statistics") or {}).get("per_question") or {}

    preguntas: list[Pregunta] = []
    for seccion in instrumento.get("sections") or []:
        if not isinstance(seccion, dict):
            continue
        for q in seccion.get("questions") or []:
            if isinstance(q, dict) and q.get("text"):
                pid = str(q.get("question_id") or f"q{len(preguntas) + 1}")
                preguntas.append(
                    Pregunta(
                        id=pid,
                        texto=str(q["text"]),
                        tipo=str(q.get("type") or ""),
                        opciones=[str(o) for o in q.get("options") or []],
                        seccion=str(seccion.get("name") or SECCION_GENERAL),
                        estadisticas=por_pregunta.get(pid) or {},
                    )
                )
    respondentes = [r for r in data.get("respondents") or [] if isinstance(r, dict)]
    carreras = Counter(
        str((r.get("demographics") or {}).get("carrera"))
        for r in respondentes
        if (r.get("demographics") or {}).get("carrera")
    )
    texto = "\n".join(
        [str(instrumento.get("title") or ""), str(instrumento.get("objective") or "")]
        + [p.texto for p in preguntas]
        + [str(instrumento.get("contenido") or "")]
    ).strip()
    dc = {clave.replace(":", "_"): str(valor) for clave, valor in dc_crudo.items() if valor not in (None, "")}
    return Analisis(
        tipo=tipo,
        familia="json",
        titulo=str(instrumento.get("title") or dc.get("dc_title") or ""),
        descripcion=str(dc.get("dc_description") or instrumento.get("objective") or ""),
        texto=texto,
        preguntas=preguntas,
        dimensiones=[str(d) for d in instrumento.get("dimensions_explored") or especificos.get("dimensiones") or []],
        palabras_clave=[str(p) for p in especificos.get("palabras_clave") or []] or palabras_clave([texto]),
        idioma=str(dc.get("dc_language") or "es")[:10],
        n_registros=especificos.get("n_respondentes") or (len(respondentes) or None),
        carreras=[c for c, _ in carreras.most_common(8)],
        hallazgos={"objetivo": str(instrumento.get("objective") or "")} if instrumento.get("objective") else {},
        dc_archivo=dc,
        especificos_archivo=especificos,
        kpi_hints=[str(k) for k in (data.get("design_reference") or {}).get("kpi_hints") or []],
    )


def analizar_contenido(raw: Any, procesado: Any) -> Analisis:
    """Lee el instrumento (vía storage-service) y lo analiza. Puede lanzar StorageError."""
    ruta_datos = getattr(procesado, "ruta_de_archivo_limpio", None) or raw.raw_archivo
    nombre = raw.nombre_archivo or Path(raw.raw_archivo).name
    extension = Path(ruta_datos).suffix.lower() or Path(nombre).suffix.lower()
    tipo = (raw.tipo_instrumento or "encuesta").lower()

    if extension == ".json":
        try:
            data = json.loads(storage_client.descargar(ruta_datos).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise storage_client.StorageError(f"El JSON del instrumento no es válido: {exc}", 422) from exc
        return _desde_json(data if isinstance(data, dict) else {}, tipo)

    texto_original = ""
    original = raw.raw_archivo_original
    if original and original != raw.raw_archivo:
        try:
            texto_original = storage_client.texto(original).get("texto") or ""
        except storage_client.StorageError as exc:
            logger.warning("No se pudo leer el instrumento original %s: %s", original, exc)

    if extension in _TABULARES:
        return _desde_tabla(storage_client.tabla(ruta_datos), tipo, nombre, texto_original)

    texto = storage_client.texto(ruta_datos).get("texto") or ""
    if texto_original and texto_original not in texto:
        texto = f"{texto_original}\n\n{texto}"
    return _desde_documento(texto, tipo, nombre)


# ── Caché del análisis (las dos propuestas y la aprobación lo comparten) ──────

_CACHE_TTL = 900.0
_cache: dict[tuple, tuple[float, Analisis]] = {}
_cache_lock = threading.Lock()


def _clave(raw: Any, procesado: Any) -> tuple:
    return (
        raw.id_crudo,
        raw.raw_archivo,
        raw.raw_archivo_original,
        getattr(procesado, "ruta_de_archivo_limpio", None),
    )


def analizar(raw: Any, procesado: Any) -> Analisis:
    clave = _clave(raw, procesado)
    ahora = time.monotonic()
    with _cache_lock:
        entrada = _cache.get(clave)
        if entrada and entrada[0] > ahora:
            return entrada[1]
    analisis = analizar_contenido(raw, procesado)
    with _cache_lock:
        _cache[clave] = (ahora + _CACHE_TTL, analisis)
        if len(_cache) > 128:
            for k in sorted(_cache, key=lambda k: _cache[k][0])[:32]:
                _cache.pop(k, None)
    return analisis


def limpiar_cache() -> None:
    with _cache_lock:
        _cache.clear()
