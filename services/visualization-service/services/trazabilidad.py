"""Trazabilidad de las fuentes del chat: de qué parte de qué instrumento salió cada dato.

Antes cada tarjeta de fuente traía un solo fragmento de texto, sin decir qué parte del
instrumento era ni dejar ver el documento. Ahora:

  - `adjuntar(fuentes, fragmentos)`: a cada tarjeta le pone los pasajes que se le dieron
    al modelo (`plan.fragmentos`, ya numerados con su [Fuente n]), con su etiqueta
    («Pregunta p04», «Respondente R017 · p04»), su similitud y su posición en el documento.
  - `documento(db, id_crudo, desde, hasta)`: un tramo del documento indexado (las mismas
    piezas que puede recuperar el RAG, en orden), leído de `documento_vectorizado`. La UI
    lo abre en la posición del pasaje y lo resalta.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from shared.db.core.config import settings
from shared.models.coleccion_vectorial import ColeccionVectorial
from shared.models.documento_vectorizado import DocumentoVectorizado
from shared.models.instrumento_procesado import InstrumentoProcesado

from models import DocumentoFuenteOut, FragmentoDocumentoOut, FuenteChatOut, PasajeOut

MAX_TRAMO = 200  # fragmentos por petición: el instrumento más grande tiene ~600

_SECCIONES = {
    "encabezado": "Ficha",
    "pregunta": "Pregunta",
    "respondente": "Respondente",
    "reactivo": "Reactivo",
    "alumno": "Alumno",
    "intercambio": "Intercambio",
    "kpi": "KPI",
    "contenido": "Texto",
}


def _corto(ident: Any) -> str:
    """«INS-0012-R017» → «R017»: el ID que se muestra; la metadata guarda el completo."""
    texto = str(ident or "").strip()
    return texto.rsplit("-", 1)[-1] if texto else ""


def _entero(valor: Any) -> int | None:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def etiqueta(seccion: str, pregunta_id: Any = "", respondente_id: Any = "") -> str:
    """«Ficha», «Pregunta p04», «Respondente R017 · p04»: qué parte del instrumento es."""
    nombre = _SECCIONES.get(seccion or "", (seccion or "fragmento").capitalize())
    partes = [p for p in (_corto(respondente_id), _corto(pregunta_id)) if p]
    return f"{nombre} {' · '.join(partes)}" if partes else nombre


def pasajes(fragmentos: list[dict[str, Any]], numero: int) -> list[PasajeOut]:
    """Los fragmentos de la fuente `numero`, sin repetidos, del más al menos parecido a la pregunta."""
    salida: list[PasajeOut] = []
    vistos: set[Any] = set()
    for f in fragmentos:
        if f.get("numero") != numero:
            continue
        indice = _entero(f.get("chunkIndex"))
        texto = str(f.get("fragmentoOriginal") or f.get("fragmento") or "")
        # Mismo fragmento (posición) o mismo texto en otra posición (respondentes con respuestas idénticas o
        # piezas que se solapan): se muestra una sola vez.
        claves = {indice, " ".join(texto.split()).lower()} - {None}
        if claves & vistos:
            continue
        vistos |= claves
        seccion = str(f.get("seccion") or "")
        salida.append(PasajeOut(
            seccion=seccion,
            etiqueta=etiqueta(seccion, f.get("preguntaId"), f.get("respondenteId")),
            texto=texto,
            score=f.get("score"),
            chunkIndex=indice,
            preguntaId=_corto(f.get("preguntaId")),
            respondenteId=_corto(f.get("respondenteId")),
        ))
    salida.sort(key=lambda p: -(p.score if p.score is not None else -1.0))
    return salida


def adjuntar(fuentes: list[FuenteChatOut], fragmentos: list[dict[str, Any]]) -> list[FuenteChatOut]:
    """Pone en cada tarjeta los pasajes que se usaron de su instrumento."""
    for fuente in fuentes:
        fuente.pasajes = pasajes(fragmentos, fuente.numero)
    return fuentes


# ── Solo las fuentes que usó la respuesta ──────────────────────────────────────
# Antes se mostraba una tarjeta por cada instrumento recuperado, aunque la respuesta no lo usara: con «¿qué es la
# escala RAU?» salían cuatro cuestionarios que no tenían que ver (9 nov). Ahora una fuente se muestra si la respuesta
# la cita ([Fuente n], (Fuentes 3 y 5)…) o si es parte del resultado calculado. Si la respuesta no cita nada (el
# modelo de 3B a veces omite las citas), quedan solo las fuentes con las que comparte contenido.

# Las mismas formas de cita que reconoce el frontend (BurbujaMensaje.tsx, RE_CITA).
_RE_CITA = re.compile(r"[\[(]\s*Fuentes?\s+(\d+(?:\s*(?:,|y|e)\s*(?:Fuente\s+)?\d+)*)\s*[\])]", re.IGNORECASE)
_RE_PALABRA = re.compile(r"[a-zñ]{5,}")
_VACIAS = {
    "segun", "sobre", "entre", "tambien", "donde", "cuando", "estos", "estas", "este", "esta", "tiene", "tienen",
    "puede", "pueden", "parte", "otros", "otras", "mismo", "misma", "fuente", "fuentes", "contexto", "informacion",
    "instrumento", "instrumentos", "respuesta", "respuestas", "pregunta", "preguntas", "estudiantes", "menciona",
    "mencionan", "embargo", "aunque", "porque", "relacionada", "relacionado", "explicitamente", "proporcionado",
}
_MIN_COMPARTIDAS = 4
_PROPORCION_COMPARTIDAS = 0.2


def numeros_citados(texto: str | None) -> set[int]:
    """Los n de las citas «[Fuente n]» (y sus variantes) de un texto."""
    return {int(n) for m in _RE_CITA.finditer(texto or "") for n in re.findall(r"\d+", m.group(1))}


_RAIZ = 6  # «equilibrados» y «equilibrado» → «equili»: el plural y el género no separan dos menciones


def _palabras(texto: str) -> set[str]:
    """Raíces de las palabras de contenido (5+ letras, sin acentos ni palabras vacías)."""
    plano = unicodedata.normalize("NFKD", texto.lower()).encode("ascii", "ignore").decode()
    return {p[:_RAIZ] for p in _RE_PALABRA.findall(plano) if p not in _VACIAS}


# ── Citas que faltan ──────────────────────────────────────────────────────────
# El modelo de 3B cita «[Fuente n]» solo a veces (4 de 12 respuestas el 9 nov). Sin la cita no hay forma de ir de
# una afirmación al documento de donde salió. Si la respuesta no cita nada, cada línea con contenido se cita con la
# fuente cuyos pasajes (lo que se le dio al modelo) comparten claramente sus palabras; si no es claro, no se cita:
# es preferible una línea sin cita a una cita equivocada. No cambia el texto ni las cifras: solo agrega la marca.
_MIN_PALABRAS_LINEA = 3
_UMBRAL_LINEA = 0.25  # parte de las palabras de la línea que debe estar en la fuente
_EMPATE = 0.75  # otra fuente tan cercana como esto a la mejor también se cita (máximo 2)
_RE_FIN_LINEA = re.compile(r"([.;:,]?)(\s*)$")


def citar(respuesta: str, fuentes: list[FuenteChatOut]) -> str:
    """La respuesta con «[Fuente n]» al final de cada línea sin cita que sale claramente de una fuente."""
    if not fuentes or numeros_citados(respuesta):
        return respuesta
    vocabulario = {
        f.numero: _palabras(" ".join([f.titulo, *(p.texto for p in f.pasajes)] if f.pasajes else [f.titulo, f.fragmento]))
        for f in fuentes
    }
    lineas = respuesta.split("\n")
    for i, linea in enumerate(lineas):
        palabras = _palabras(linea)
        if len(palabras) < _MIN_PALABRAS_LINEA:
            continue
        puntajes = sorted(((len(palabras & v), n) for n, v in vocabulario.items()), reverse=True)
        mejor = puntajes[0][0]
        if mejor < max(_MIN_PALABRAS_LINEA, round(_UMBRAL_LINEA * len(palabras))):
            continue
        cercanas = sorted(n for s, n in puntajes if s >= _EMPATE * mejor)
        if len(cercanas) > 2:
            continue  # ambiguo: varias fuentes dicen lo mismo
        marcas = " ".join(f"[Fuente {n}]" for n in cercanas)
        lineas[i] = _RE_FIN_LINEA.sub(lambda m: f" {marcas}{m.group(1)}{m.group(2)}", linea.rstrip(), count=1) \
            if not linea.rstrip().endswith(":") else linea
    return "\n".join(lineas)


def _por_bloque_del_resultado(fuentes: list[FuenteChatOut], respuesta: str, resultado: str) -> list[FuenteChatOut]:
    palabras = _palabras(respuesta)
    if not palabras:
        return []
    bloques: dict[int, set[str]] = {}
    marcas = list(re.finditer(r"\[Fuente (\d+)\]", resultado))
    for i, m in enumerate(marcas):
        fin = marcas[i + 1].start() if i + 1 < len(marcas) else len(resultado)
        n = int(m.group(1))
        bloques[n] = bloques.get(n, set()) | _palabras(resultado[m.start():fin])
    puntajes = {f.numero: len(palabras & bloques.get(f.numero, set())) for f in fuentes}
    mejor = max(puntajes.values(), default=0)
    if mejor < max(_MIN_COMPARTIDAS, round(_PROPORCION_COMPARTIDAS * len(palabras))):
        return []
    return [f for f in fuentes if puntajes[f.numero] >= _EMPATE * mejor]


def citadas(fuentes: list[FuenteChatOut], respuesta: str, resultado: str | None = None) -> list[FuenteChatOut]:
    """Las fuentes que usó la respuesta: citadas en ella o en el resultado calculado; si no cita ninguna que
    exista, las que comparten contenido con la respuesta (título, fragmento o pasajes)."""
    # Primero lo que la respuesta cita: con todo el acervo como alcance el cálculo corre sobre cada instrumento y
    # el resultado los nombra a todos (9 tarjetas para una respuesta que solo usó la Fuente 1, 9 nov). Las del
    # resultado calculado cuentan solo si la respuesta no cita ninguna.
    elegidas = [f for f in fuentes if f.numero in numeros_citados(respuesta)]
    if elegidas:
        return elegidas
    del_calculo = [f for f in fuentes if f.numero in numeros_citados(resultado)]
    if del_calculo:
        # Sin citas en la respuesta: de las fuentes del cálculo, las cuyo bloque del resultado («[Fuente n] …» hasta el
        # siguiente) comparte claramente las palabras de la respuesta; si ninguna destaca, todas las del cálculo.
        return _por_bloque_del_resultado(del_calculo, respuesta, resultado or "") or del_calculo
    palabras = _palabras(respuesta)
    if not palabras:
        return []
    minimo = max(_MIN_COMPARTIDAS, round(_PROPORCION_COMPARTIDAS * len(palabras)))
    return [
        f for f in fuentes
        if len(palabras & _palabras(" ".join([f.titulo, f.fragmento, *(p.texto for p in f.pasajes)]))) >= minimo
    ]


def documento(db: Session, id_crudo: int, desde: int = 0, hasta: int | None = None) -> DocumentoFuenteOut | None:
    """Fragmentos [desde, hasta) del documento indexado del instrumento, en orden; None si no está indexado.

    Se toman los del procesamiento más reciente que tenga fragmentos en la colección `instrumentos`
    (la reingesta borra y vuelve a escribir los del procesamiento vigente).
    """
    coleccion = (
        db.query(ColeccionVectorial)
        .filter(ColeccionVectorial.nombre == settings.CHROMA_COLLECTION_INSTRUMENTOS)
        .first()
    )
    if coleccion is None:
        return None
    id_instrumento = (
        db.query(func.max(DocumentoVectorizado.instrumento_id))
        .join(InstrumentoProcesado, InstrumentoProcesado.id_instrumento == DocumentoVectorizado.instrumento_id)
        .filter(InstrumentoProcesado.id_crudo == id_crudo, DocumentoVectorizado.coleccion_id == coleccion.coleccion_id)
        .scalar()
    )
    if id_instrumento is None:
        return None
    base = db.query(DocumentoVectorizado).filter(
        DocumentoVectorizado.instrumento_id == id_instrumento,
        DocumentoVectorizado.coleccion_id == coleccion.coleccion_id,
    )
    total = base.count()
    desde = max(0, desde)
    hasta = min(total, hasta if hasta is not None else desde + MAX_TRAMO, desde + MAX_TRAMO)
    filas = (
        base.filter(DocumentoVectorizado.chunk_index >= desde, DocumentoVectorizado.chunk_index < hasta)
        .order_by(DocumentoVectorizado.chunk_index)
        .all()
    )
    primera = base.order_by(DocumentoVectorizado.chunk_index).first()
    meta0 = (primera.chunk_metadata if primera is not None else None) or {}
    fragmentos = []
    for fila in filas:
        meta = fila.chunk_metadata or {}
        seccion = str(fila.seccion or meta.get("seccion") or "")
        fragmentos.append(FragmentoDocumentoOut(
            chunkIndex=int(fila.chunk_index or 0),
            seccion=seccion,
            etiqueta=etiqueta(seccion, meta.get("preguntaId"), meta.get("respondenteId")),
            texto=fila.chunk_texto,
            preguntaId=_corto(meta.get("preguntaId")),
            respondenteId=_corto(meta.get("respondenteId")),
        ))
    return DocumentoFuenteOut(
        instrumentoId=str(id_crudo),
        titulo=str(meta0.get("titulo") or ""),
        tipo=str(meta0.get("tipo") or ""),
        origen=str(meta0.get("fuente") or "json_tecnico"),
        total=total,
        desde=desde,
        hasta=max(desde, hasta),
        fragmentos=fragmentos,
    )
