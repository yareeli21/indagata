"""Estructura del instrumento: secciones y preguntas con IDs globales estables.

Es la base común del perfil semántico (que la muestra sin datos técnicos) y del
documento final (que le agrega respuestas y resúmenes). Por eso cada pregunta
conserva aquí su referencia interna (`columna`: id de columna del CSV limpio o
clave del reactivo), que NUNCA se publica en el perfil.

Determinismo: con las mismas entradas (misma versión de limpieza y mismo
original) produce los mismos IDs, así el documento final reconstruye la
estructura sin guardar la correspondencia en la base.

Fuentes, en orden de preferencia:
  1. Instrumento original (texto completo de las preguntas, secciones, opciones).
  2. Encabezados del archivo limpio + reporte de limpieza (tipos, grupos).
  3. JSON técnico de metadata-service (instrumentos anteriores a la limpieza).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from services import original as orig
from services.interpretacion.privacidad import es_dato_personal
from services.original import InstrumentoOriginal, PreguntaOriginal, normalizar

# Tipos cuyas opciones de respuesta describen la pregunta (las anclas Likert no).
TIPOS_CON_OPCIONES = {"categorica", "opcion_multiple_varias", "binaria"}
_MAX_OPCIONES = 20

# «Pregunta [aspecto]» (cuadrículas) y «Prefijo_item3» / «Prefijo 3» (bloques numerados).
_PATRON_GRUPO = re.compile(r"^(?P<padre>.+?)\s*\[(?P<hijo>[^\]]+)\]\s*$")
_PATRON_SUFIJO = re.compile(
    r"^(?P<padre>.*?[^\W\d_].*?)[\s_.\-]*(?:[ií]tem|reactivo)?[\s_.\-]*(?P<hijo>\d{1,3})$", re.IGNORECASE
)


def id_instrumento(id_crudo: int) -> str:
    """ID global del instrumento: el RAG consultará varios instrumentos a la vez."""
    return f"INS-{id_crudo:04d}"


@dataclass
class Seccion:
    id: str
    nombre: str
    descripcion: str = ""


@dataclass
class Pregunta:
    id: str
    seccion_id: str
    texto: str
    opciones: list[str] = field(default_factory=list)
    # ── Referencias internas (no se publican en el perfil) ──
    columna: str | None = None  # id de columna del CSV limpio, o clave del reactivo («P3»)
    tipo: str | None = None  # tipo canónico de la limpieza
    grupo: str | None = None
    aspecto: str | None = None
    letras: dict[str, str] = field(default_factory=dict)  # pruebas: {"A": "texto de la opción"}
    puntos_max: int | None = None  # pruebas: puntaje máximo (puntos) o máximo de la escala
    anclas: dict[int, str] = field(default_factory=dict)  # escalas: {1: "Nada", 5: "Mucho"}


@dataclass
class Estructura:
    secciones: list[Seccion] = field(default_factory=list)
    preguntas: list[Pregunta] = field(default_factory=list)
    fuente: str = "encabezados"  # original | encabezados | json_tecnico | ninguna
    avisos: list[dict[str, Any]] = field(default_factory=list)


class _Constructor:
    """Asigna IDs en orden de aparición (s1, s2…; p01, p02… o r01, r02…)."""

    def __init__(self, id_ins: str, prefijo: str = "p") -> None:
        self.id_ins = id_ins
        self.prefijo = prefijo
        self.e = Estructura()
        self._secciones: dict[str, Seccion] = {}

    def seccion(self, nombre: str) -> str:
        if nombre not in self._secciones:
            s = Seccion(id=f"{self.id_ins}-s{len(self._secciones) + 1}", nombre=nombre)
            self._secciones[nombre] = s
            self.e.secciones.append(s)
        return self._secciones[nombre].id

    def pregunta(self, seccion: str, texto: str, **kw: Any) -> Pregunta:
        p = Pregunta(
            id=f"{self.id_ins}-{self.prefijo}{len(self.e.preguntas) + 1:02d}",
            seccion_id=self.seccion(seccion),
            texto=" ".join(texto.split()),
            **kw,
        )
        self.e.preguntas.append(p)
        return p

    def aviso(self, codigo: str, mensaje: str, **kw: Any) -> None:
        self.e.avisos.append({"codigo": codigo, "mensaje": mensaje, **kw})


def grupo_de(etiqueta: str) -> tuple[str, str, bool] | None:
    """(padre, hijo, es_cuadricula) para «Pregunta [aspecto]» o «Prefijo_item3»."""
    if m := _PATRON_GRUPO.match(etiqueta):
        return m.group("padre").strip(), m.group("hijo").strip(), True
    if m := _PATRON_SUFIJO.match(etiqueta.strip()):
        padre = " ".join(m.group("padre").replace("_", " ").split()).strip(" -.")
        if padre:
            return padre, f"ítem {int(m.group('hijo'))}", False
    return None


def _opciones_de_original(p: PreguntaOriginal) -> list[str]:
    return [t for _, t in p.opciones][:_MAX_OPCIONES]


def _opciones_de_frecuencias(estadistica_col: dict[str, Any] | None) -> list[str]:
    tabla = ((estadistica_col or {}).get("frecuencias") or {}).get("tabla") or []
    return [str(f["valor"]) for f in tabla if f.get("n")][:_MAX_OPCIONES]


# ── Encuestas ──────────────────────────────────────────────────────────────────


def encuesta(id_crudo: int, reporte: dict[str, Any], original: InstrumentoOriginal | None) -> Estructura:
    """Preguntas de una encuesta a partir del reporte de limpieza (y del original, si hay)."""
    c = _Constructor(id_instrumento(id_crudo))
    esp = (reporte.get("especifico") or {}).get("encuesta") or {}
    # Las columnas con datos personales (nombre, correo, matrícula…) nunca son preguntas.
    columnas = [
        col for col in esp.get("columnas") or []
        if col.get("estado") != "eliminada" and (col.get("rol") or "pregunta") == "pregunta"
        and not es_dato_personal(col.get("etiqueta") or col.get("id") or "")
    ]
    est_cols = {x.get("id"): x for x in ((reporte.get("estadistica") or {}).get("despues") or {}).get("columnas") or []}

    def opciones(col: dict[str, Any], p_orig: PreguntaOriginal | None) -> list[str]:
        if col.get("tipo_canonico") not in TIPOS_CON_OPCIONES:
            return []
        # Regla: si la pregunta está en el original, manda el original (si ahí no tiene
        # opciones es abierta y no se listan las respuestas). Sin original, las opciones
        # son los valores distintos observados.
        if p_orig is not None:
            return _opciones_de_original(p_orig)
        return _opciones_de_frecuencias(est_cols.get(col.get("id")))

    def kw(col: dict[str, Any], grupo: tuple[str, str, bool] | None) -> dict[str, Any]:
        return {
            "columna": col.get("id"),
            "tipo": col.get("tipo_canonico"),
            "grupo": grupo[0] if grupo else None,
            "aspecto": grupo[1] if grupo else None,
        }

    if original and original.preguntas:
        c.e.fuente = "original"
        # Las columnas de una cuadrícula se emparejan por su pregunta padre (una sola vez).
        grupos = [grupo_de(col.get("etiqueta") or "") for col in columnas]
        claves: list[str] = []
        clave_de_col: list[int] = []
        for col, g in zip(columnas, grupos):
            clave = g[0] if g and g[2] else (col.get("etiqueta") or "")
            if clave not in claves:
                claves.append(clave)
            clave_de_col.append(claves.index(clave))
        # Las columnas de contexto (turno, semestre…) también se emparejan, solo para
        # saber qué preguntas del original son de contexto y dejarlas fuera del perfil.
        contexto = [col.get("etiqueta") or "" for col in esp.get("columnas") or []
                    if col.get("estado") != "eliminada" and col.get("rol") == "contexto"]
        pareja_total = orig.emparejar(claves + contexto, original.preguntas)
        pareja = {k: j for k, j in pareja_total.items() if k < len(claves)}  # {clave: pregunta original}
        de_contexto = {j for k, j in pareja_total.items() if k >= len(claves)}
        # Encabezados codificados («Falta_de_organi_item3»): se emparejan por sección + posición.
        _por_seccion_y_posicion(claves, grupos, clave_de_col, original, pareja, usadas=set(pareja_total.values()))
        cols_de_preg: dict[int, list[int]] = {}
        for i, k in enumerate(clave_de_col):
            if k in pareja:
                cols_de_preg.setdefault(pareja[k], []).append(i)

        for j, p in enumerate(original.preguntas):
            if j in de_contexto:
                continue  # datos del respondente (turno, semestre…): no describen el instrumento
            indices = cols_de_preg.get(j)
            if not indices:
                # Pregunta del original sin columna: igual describe el instrumento.
                c.pregunta(p.seccion, p.texto, opciones=_opciones_de_original(p), anclas=p.anclas or original.anclas_globales)
                continue
            for i in indices:
                col, g = columnas[i], grupos[i]
                texto = f"{p.texto}: {g[1]}" if g and g[2] else p.texto
                c.pregunta(p.seccion, texto, opciones=opciones(col, p), anclas=p.anclas or original.anclas_globales, **kw(col, g if g and g[2] else None))
        sueltas = [i for i, k in enumerate(clave_de_col) if k not in pareja]
        for i in sueltas:
            col = columnas[i]
            c.pregunta("Otras preguntas del archivo", col.get("etiqueta") or col.get("id"), opciones=opciones(col, None), **kw(col, grupos[i]))
        if sueltas:
            c.aviso(
                "preguntas_sin_original",
                f"{len(sueltas)} pregunta(s) del archivo no se encontraron en el instrumento original; se usa su encabezado.",
                n=len(sueltas),
            )
        return c.e

    # Sin original: secciones por grupo («Pregunta [aspecto]» o prefijo numerado) y «General».
    for col in columnas:
        etiqueta = col.get("etiqueta") or col.get("id") or ""
        g = grupo_de(etiqueta)
        seccion = g[0] if g else orig.SECCION_GENERAL
        texto = f"{g[0]}: {g[1]}" if g else etiqueta
        c.pregunta(seccion, texto, opciones=opciones(col, None), **kw(col, g))
    c.aviso("sin_original", "No se subió el instrumento original: las preguntas usan los encabezados del archivo.")
    return c.e


def _clave_seccion(texto: str) -> str:
    """Nombre de sección comparable: sin acentos, sin «Sección 2:», guiones ni signos."""
    t = normalizar(texto)
    t = re.sub(r"^(seccion|parte|bloque|dimension|apartado|modulo|eje)\s*[\divxlc]*\s*[:.\-]?\s*", "", t)
    return " ".join(re.sub(r"[^a-z0-9ñü ]+", " ", t).split())


def _por_seccion_y_posicion(
    claves: list[str],
    grupos: list[tuple[str, str, bool] | None],
    clave_de_col: list[int],
    original: InstrumentoOriginal,
    pareja: dict[int, int],
    usadas: set[int],
) -> None:
    """Empareja encabezados codificados con el original por sección y posición (en sitio).

    Regla no obvia: plataformas y paquetes estadísticos recortan los encabezados a un
    prefijo del nombre de la sección más el número del ítem («Falta_de_organi_item3»
    = 3.ª pregunta de «FALTA DE ORGANIZACIÓN DE RECURSOS»). Se acepta la sección cuyo
    nombre EMPIEZA con el prefijo (la última palabra puede venir truncada).
    """
    secciones: dict[str, list[int]] = {}
    for j, p in enumerate(original.preguntas):
        secciones.setdefault(p.seccion, []).append(j)
    for i, k in enumerate(clave_de_col):
        g = grupos[i]
        if k in pareja or not g or g[2]:
            continue
        prefijo = _clave_seccion(g[0])
        numero = re.search(r"\d+", g[1])
        if len(prefijo) < 4 or not numero:
            continue
        exactas = [s for s in secciones if _clave_seccion(s) == prefijo]
        candidatas = exactas or [s for s in secciones if _clave_seccion(s).startswith(prefijo)]
        if len(candidatas) != 1:
            continue  # ninguna o ambigua: mejor no adivinar
        indices = secciones[candidatas[0]]
        posicion = int(numero.group()) - 1
        if 0 <= posicion < len(indices) and indices[posicion] not in usadas:
            pareja[k] = indices[posicion]
            usadas.add(indices[posicion])


# ── Entrevistas ────────────────────────────────────────────────────────────────

_GUION = "Guion de la entrevista"


def entrevista(id_crudo: int, filas: list[dict[str, str]], original: InstrumentoOriginal | None) -> Estructura:
    """Preguntas de una entrevista: el guion original o, si no hay, los turnos del entrevistador."""
    c = _Constructor(id_instrumento(id_crudo))
    if original and original.preguntas:
        c.e.fuente = "original"
        for p in original.preguntas:
            c.pregunta(p.seccion if p.seccion != orig.SECCION_GENERAL else _GUION, p.texto)
        return c.e
    vistas: set[str] = set()
    for f in filas:
        if (f.get("rol") or "") != "entrevistador":
            continue
        texto = " ".join((f.get("texto") or "").split())
        # Solo turnos con forma de pregunta (evita «Ajá», «Claro, continúa»).
        if not ("?" in texto or len(texto.split()) >= 6):
            continue
        clave = normalizar(texto)
        if clave in vistas:
            continue
        vistas.add(clave)
        c.pregunta(_GUION, texto[:400])
    if not c.e.preguntas:
        c.aviso("sin_preguntas", "No se identificaron preguntas del entrevistador; revisa los roles en la limpieza.")
    c.aviso("sin_original", "No se subió el guion original: las preguntas se tomaron de los turnos del entrevistador.")
    return c.e


# ── Pruebas estandarizadas ─────────────────────────────────────────────────────

_REACTIVOS = "Reactivos"
_LETRAS = "ABCDEFGH"


def _numero(clave: str) -> int | None:
    """Número del reactivo: el ÚLTIMO número del nombre («P3» → 3, «pru_01_Algebra_q3» → 3)."""
    numeros = re.findall(r"\d+", clave)
    return int(numeros[-1]) if numeros else None


def prueba(id_crudo: int, reporte: dict[str, Any], original: InstrumentoOriginal | None, texto_documento: str = "") -> Estructura:
    """Reactivos de la hoja de respuestas (todos: calificables o no); texto y opciones del original.

    El orden y el tipo de cada reactivo salen de `tipos_reactivo` del reporte (opción
    múltiple, V/F, puntos, escala, Sí/No, numérico); en reportes anteriores, de la clave.
    """
    c = _Constructor(id_instrumento(id_crudo), prefijo="r")
    esp = (reporte.get("especifico") or {}).get("prueba_estandarizada") or {}
    clave: dict[str, str] = esp.get("clave") or {}
    tipos: dict[str, str] = esp.get("tipos_reactivo") or {}
    puntos_max: dict[str, int] = esp.get("puntos_max") or {}
    reactivos = list(tipos) or list(clave)
    if not reactivos:
        # Prueba subida como documento: el propio texto (o el original) son las preguntas.
        fuente = original if original and original.preguntas else orig.leer(texto_documento)
        c.e.fuente = "original" if original and original.preguntas else "encabezados"
        for p in fuente.preguntas:
            letras = _letras(p)
            c.pregunta(p.seccion if p.seccion != orig.SECCION_GENERAL else _REACTIVOS, p.texto,
                       opciones=[f"{k}) {v}" for k, v in letras.items()], letras=letras)
        if not c.e.preguntas:
            c.aviso("sin_preguntas", "No se reconocieron reactivos en el documento de la prueba.")
        return c.e

    preguntas_orig = original.preguntas if original else []
    por_numero = {p.numero: p for p in preguntas_orig if p.numero is not None}
    mismo_largo = len(preguntas_orig) == len(reactivos)
    if preguntas_orig:
        c.e.fuente = "original"
    # La respuesta correcta no es parte de la estructura (va en el documento final).
    for k, reactivo in enumerate(reactivos):
        # Regla: si el original tiene tantas preguntas como la clave, se emparejan en orden;
        # si no, por número («P3» ↔ pregunta 3).
        p = preguntas_orig[k] if mismo_largo else por_numero.get(_numero(reactivo))
        letras = _letras(p) if p else {}
        c.pregunta(
            (p.seccion if p and p.seccion != orig.SECCION_GENERAL else _REACTIVOS),
            p.texto if p else f"Reactivo {reactivo}",
            opciones=[f"{L}) {t}" for L, t in letras.items()],
            columna=reactivo,
            letras=letras,
            tipo=tipos.get(reactivo, "opcion_multiple"),
            puntos_max=puntos_max.get(reactivo),
        )
    if not preguntas_orig:
        c.aviso("sin_original", "No se subió la prueba original: los reactivos no tienen texto ni opciones.")
    elif not mismo_largo and not por_numero:
        c.aviso("reactivos_sin_texto", "No se pudo emparejar la prueba original con la clave de respuestas.")
    return c.e


def _letras(p: PreguntaOriginal) -> dict[str, str]:
    """Opciones del reactivo por letra (si el original usa viñetas, se asignan A, B, C…)."""
    if any(letra for letra, _ in p.opciones):
        return {letra: t for letra, t in p.opciones if letra}
    return {_LETRAS[i]: t for i, (_, t) in enumerate(p.opciones[: len(_LETRAS)])}


# ── Instrumentos anteriores a la limpieza ──────────────────────────────────────

_TIPOS_TECNICOS_CON_OPCIONES = {"categorica", "opcion_multiple", "opcion_multiple_varias", "binaria", "cerrada"}


def desde_json_tecnico(id_crudo: int, tipo: str, data: dict[str, Any]) -> Estructura:
    """Estructura desde el JSON técnico de metadata-service (sin limpieza confirmada)."""
    c = _Constructor(id_instrumento(id_crudo), prefijo="r" if tipo == "prueba_estandarizada" else "p")
    c.e.fuente = "json_tecnico"
    for s in (data.get("instrument") or {}).get("sections") or []:
        nombre = s.get("name") or orig.SECCION_GENERAL
        for q in s.get("questions") or []:
            if not q.get("text"):
                continue
            opciones = [str(o) for o in q.get("options") or []] if q.get("type") in _TIPOS_TECNICOS_CON_OPCIONES else []
            c.pregunta(nombre, str(q["text"]), opciones=opciones[:_MAX_OPCIONES], tipo=q.get("type"))
    c.aviso("sin_limpieza", "El instrumento es anterior a la limpieza: las preguntas salen del JSON técnico.")
    return c.e
