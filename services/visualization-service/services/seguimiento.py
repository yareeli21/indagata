"""Seguimientos de inferencia: el hilo de la conversación del chat (10 nov).

«¿Y por qué crees que pasa eso?», «¿qué podría hacer la universidad para ayudarles?», «¿qué implica eso?» o «¿quién
lo dijo?» no piden datos nuevos: piden razonar sobre la respuesta anterior. Antes pasaban por la interpretación como
preguntas nuevas y el plan se calculaba sobre toda la colección («hallazgo» de 31 instrumentos, 100–130 s y cifras
sin relación) o pedía aclaración.

Aquí se detectan y se responden con la MISMA evidencia de la respuesta anterior, leída de `rag_log`: sus fuentes
(con los pasajes exactos y su numeración) y el resultado calculado que vio el modelo. Lo que pide datos nuevos
(«¿y de ellos cuántos tienen beca?», «¿quiénes…?», «p04», «R017») sigue por la interpretación, que ya sabe filtrar
sobre lo anterior.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from shared.models.rag_log import RagLog

from services.dominio import normalizar

logger = logging.getLogger("visualization-service")

# Piden razonar, explicar o rastrear lo ya dicho.
_INFERENCIA = re.compile(
    r"\b(?:por que|porque|crees|piensas|opinas|podria\w*|deberia\w*|implic\w*|afect\w*|signific\w*|se debe\w*|"
    r"a que se debe|explic\w*|interpret\w*|recomend\w*|suger\w*|conclu\w*|causa\w*|consecuencia\w*|influ\w*|"
    r"relacion\w*|que harias|que se puede hacer|como (?:se )?(?:podria|puede)|ayudar\w*|mejorar\w*|apoyar\w*|"
    r"quien lo dijo|quien dijo|quienes lo dijeron|de donde sale|en que te basas|de que instrumento|en que pregunta|"
    r"en que parte)\b"
)
# Piden datos nuevos: van a la interpretación (filtros y conteos sobre lo anterior).
_DATO_NUEVO = re.compile(r"\b(?:cuant\w*|porcentaje\w*|proporcion\w*|quienes son|cuales son|lista\w*|enumera\w*|"
                         r"[rpae]-?\d{1,4})\b|%")
# Se refiere a lo anterior: demostrativos, «lo dijo», «ellos», o un verbo con pronombre («ayudarles», «explicarlo»).
_REFERENCIA = re.compile(r"\b(?:eso|esto|ello|ellos|ellas|esa|ese|esas|esos|aquello|lo anterior|lo mismo|"
                         r"lo dijo|lo dijeron|les|y si)\b|\b\w+(?:ar|er|ir)(?:les|los|las|le|lo|la)\b")
_PALABRAS_CORTA = 8  # una pregunta así de corta en una conversación casi siempre continúa lo anterior

# Sin palabras en mayúsculas del prompt («CONTEXTO», «DATOS»): el modelo de 3B las copiaba en la respuesta.
FORMATO = (
    "Es una pregunta de seguimiento: quien investiga quiere que razones sobre lo que le respondiste antes (está en la "
    "conversación previa). Usa como evidencia los fragmentos de las fuentes de arriba, que son los mismos en que se "
    "basó esa respuesta. Contesta directamente lo nuevo que pregunta (posibles causas, implicaciones, acciones que "
    "se desprenden, o de quién y de dónde sale lo dicho) sin repetir la respuesta anterior. Habla en primera persona "
    "y no te refieras a «la respuesta del asistente», «el contexto» ni «los datos del contexto». Presenta las "
    "inferencias como interpretación («podría deberse a…», «una explicación posible es…»), sin inventar cifras, IDs "
    "ni citas textuales, y cita con [Fuente n] lo que las respalda. Si la evidencia no alcanza, dilo y explica qué "
    "haría falta saber."
)

_MAX_RESPUESTA = 1200  # caracteres de la respuesta anterior que ve la redacción
_MAX_RESULTADO = 2500  # caracteres del resultado calculado anterior


_ID_PERSONA = re.compile(r"\b[RAE]\d{2,5}\b")


def formato(fragmentos: list[dict[str, Any]]) -> str:
    """FORMATO más las personas que de verdad aparecen en la evidencia: con «¿quién lo dijo?» el modelo de 3B
    contestaba «R017» cuando el intercambio era de E02 (10 nov, consulta 163)."""
    ids = sorted({i for f in fragmentos for i in _ID_PERSONA.findall(f"{f.get('fragmento') or ''} "
                                                                      f"{f.get('respondenteId') or ''}")})
    if not ids:
        return FORMATO + " En la evidencia no aparece ninguna persona por su ID: no menciones ninguno."
    return FORMATO + f" Las únicas personas que aparecen en la evidencia son {', '.join(ids)}: si mencionas a alguien, usa solo esos IDs."


def es_inferencia(pregunta: str) -> bool:
    texto = normalizar(pregunta)
    if not _INFERENCIA.search(texto) or _DATO_NUEVO.search(texto):
        return False
    return bool(_REFERENCIA.search(texto)) or len(texto.split()) <= _PALABRAS_CORTA


@dataclass
class Anterior:
    """La respuesta anterior y su evidencia, como quedó en rag_log."""

    consulta_id: int
    pregunta: str
    respuesta: str
    fuentes: list[dict[str, Any]] = field(default_factory=list)  # FuenteChatOut con sus pasajes
    resultados: list[str] = field(default_factory=list)  # bloques «[Fuente n] …» del resultado calculado
    ultima: bool = True  # es la última respuesta de la conversación (no una anterior a una aclaración)
    intencion: str = ""  # la del plan de la interpretación, si la hubo

    def fragmentos(self) -> list[dict[str, Any]]:
        """Los pasajes y el resultado anterior como fragmentos del prompt, con el número de su fuente."""
        salida: list[dict[str, Any]] = []
        por_numero = {f.get("numero"): f for f in self.fuentes}
        for f in self.fuentes:
            for p in f.get("pasajes") or []:
                salida.append({
                    "numero": f.get("numero"), "instrumentoId": str(f.get("instrumentoId") or ""),
                    "titulo": f.get("titulo"), "tipo": f.get("tipo"), "investigador": f.get("investigador"),
                    "seccion": p.get("seccion") or "", "fragmento": p.get("texto") or "", "score": p.get("score"),
                    "chunkIndex": p.get("chunkIndex"), "preguntaId": p.get("preguntaId") or "",
                    "respondenteId": p.get("respondenteId") or "",
                })
        restante = _MAX_RESULTADO
        for bloque in self.resultados:
            m = re.match(r"\[Fuente (\d+)\]", bloque)
            fuente = por_numero.get(int(m.group(1))) if m else (self.fuentes[0] if len(self.fuentes) == 1 else None)
            if fuente is None or restante <= 0:
                continue
            texto = bloque[:restante]
            restante -= len(texto)
            salida.append({
                "numero": fuente.get("numero"), "instrumentoId": str(fuente.get("instrumentoId") or ""),
                "titulo": fuente.get("titulo"), "tipo": fuente.get("tipo"), "investigador": fuente.get("investigador"),
                "seccion": "resultado", "fragmento": texto, "score": None, "chunkIndex": None,
                "preguntaId": "", "respondenteId": "",
            })
        return salida


def _turnos(historial: list[Any]) -> list[tuple[str, Any]]:
    """(pregunta del usuario, respuesta del asistente con consultaId), de la más reciente a la más antigua."""
    salida = []
    for i in range(len(historial) - 1, 0, -1):
        m, antes = historial[i], historial[i - 1]
        if m.rol == "asistente" and m.consultaId and antes.rol == "usuario":
            salida.append((antes.texto, m))
    return salida


def leer_anterior(historial: list[Any], fabrica_sesiones: Callable[[], Any]) -> Anterior | None:
    """La respuesta más reciente con evidencia (se salta aclaraciones y «sin información»: «¿qué podría implicar
    eso?» tras «¿y de ellos…?» → aclaración se refiere al conteo de antes). Su pregunta debe ser el mensaje del usuario
    que la precede en el historial: así un consultaId ajeno no lee otra consulta."""
    try:
        sesion = fabrica_sesiones()
        try:
            for n, (pregunta, m) in enumerate(_turnos(historial)):
                fila = sesion.get(RagLog, m.consultaId)
                if fila is None or fila.pregunta.strip() != pregunta.strip() or fila.decision_dominio != "dentro":
                    continue
                fuentes = [f for f in ((fila.salida or {}).get("fuentes") or []) if isinstance(f, dict)]
                if not fuentes:
                    continue
                resultados = [str(c.get("texto") or "") for c in (fila.contexto_usado or [])
                              if isinstance(c, dict) and c.get("tipo") == "resultado" and c.get("texto")]
                intencion = str(((fila.plan or {}).get("plan") or {}).get("intencion") or "")
                return Anterior(fila.rag_log_id, fila.pregunta, (fila.respuesta or "")[:_MAX_RESPUESTA], fuentes,
                                resultados, ultima=n == 0, intencion=intencion)
            return None
        finally:
            sesion.close()
    except Exception as exc:  # noqa: BLE001 — sin BD el seguimiento sigue por la interpretación
        logger.warning("No se pudo leer la respuesta anterior para el seguimiento: %s", exc)
        return None


# «¿Cómo inferiste que no existen estrategias?», «¿por qué dices que no hay información?»: piden cuentas de la
# respuesta anterior. Si fue «sin información», se explica con la traza (qué se buscó, lo más parecido y su similitud).
_PIDE_CUENTAS = re.compile(r"\b(?:como (?:lo )?(?:inferiste|infieres|sabes|supiste|llegaste|determinaste|concluiste|"
                           r"buscaste|decidiste)|por que (?:dices|respondiste|contestaste|no (?:hay|tienes|encontraste|"
                           r"sabes))|en que te basas|en que te basaste|de donde (?:sacaste|sale))\b")


def pide_cuentas(pregunta: str) -> bool:
    return bool(_PIDE_CUENTAS.search(normalizar(pregunta)))


@dataclass
class SinRespuesta:
    """La última consulta, cuando se respondió que no había información (o que estaba fuera del dominio)."""

    consulta_id: int
    pregunta: str
    decision: str
    score_max: float | None
    instrumentos: list[str]


def leer_sin_respuesta(historial: list[Any], fabrica_sesiones: Callable[[], Any]) -> SinRespuesta | None:
    turnos = _turnos(historial)
    if not turnos:
        return None
    pregunta, m = turnos[0]
    try:
        sesion = fabrica_sesiones()
        try:
            fila = sesion.get(RagLog, m.consultaId)
            if fila is None or fila.pregunta.strip() != pregunta.strip() \
                    or fila.decision_dominio not in ("sin_informacion", "fuera"):
                return None
            return SinRespuesta(fila.rag_log_id, fila.pregunta, fila.decision_dominio, fila.score_max,
                                [str(i) for i in (fila.instrumentos or [])])
        finally:
            sesion.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo leer la consulta anterior sin respuesta: %s", exc)
        return None


def explicar_sin_respuesta(anterior: SinRespuesta, cercano: dict[str, Any] | None, minimo: float) -> str:
    """Explicación sin LLM (no puede inventar): qué se buscó, qué fue lo más parecido y por qué no alcanzó."""
    texto = (f"Respondí que no tenía información porque busqué «{anterior.pregunta.strip()}» en los instrumentos "
             f"consultados y ninguna parte se parece lo suficiente: el chat solo responde con partes que alcanzan "
             f"{round(minimo * 100)} % de similitud con tu pregunta, para no inventar.")
    if cercano is None:
        return texto + " No encontré ninguna parte cercana al tema."
    fragmento = " ".join(str(cercano.get("fragmento") or "").split())[:220]
    return (f"{texto}\n\nLo más parecido que encontré fue {cercano['etiqueta']} de «{cercano.get('titulo') or 'el instrumento'}», "
            f"con {round(float(cercano['score']) * 100)} % de similitud [Fuente 1]: «{fragmento}…»\n\n"
            "Si eso es lo que buscas, pregúntame por esa parte directamente o reformula la pregunta con las palabras "
            "del instrumento.")


# «¿Qué significa eso?» justo después de un resultado calculado: lo resuelve la interpretación volviendo a calcular el
# plan anterior con sus cifras verificadas (rag_service._retomar_anterior, 4 nov); aquí no se intercepta.
_SIGNIFICADO = re.compile(r"\b(?:signific\w*|que quiere decir|que puede decir)\b")


def lo_retoma_el_plan(pregunta: str, anterior: Anterior, estructuradas: frozenset[str]) -> bool:
    return anterior.ultima and anterior.intencion in estructuradas and bool(_SIGNIFICADO.search(normalizar(pregunta)))


def conversacion(anterior: Anterior, quitar_tablas: Callable[[str], str]) -> str:
    return f"Usuario: {anterior.pregunta}\nAsistente: {quitar_tablas(anterior.respuesta)}"
