"""Catálogo compacto de un instrumento para la etapa de interpretación del chat.

El LLM no ve los datos: ve este catálogo (preguntas con su ID, texto, tipo y opciones o escala; variables de
contexto con sus valores; KPIs asociados; rango de IDs de respondentes) y con él arma el plan JSON
(`services/plan_consulta.py`). El mismo catálogo sirve para validar el plan: una opción o pregunta que no está
aquí no existe en el instrumento.

Se arma del documento final vigente (el mismo que usa el ejecutor), así que lo que el plan nombra siempre se puede
calcular. El texto que va al prompt se recorta (`_MAX_TEXTO`, `_MAX_OPCIONES`) para que quepa en el contexto del
modelo de 3B junto con los ejemplos.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

_MAX_TEXTO = 90  # caracteres del texto de cada pregunta en el prompt
_MAX_OPCIONES = 10  # opciones por pregunta en el prompt (el catálogo completo se conserva para validar)
_MAX_VALORES_CONTEXTO = 8
_TIPO_UI = {"encuesta": "encuesta", "prueba_estandarizada": "prueba", "entrevista": "entrevista"}


@dataclass
class PreguntaCatalogo:
    id: str  # corto: «p03», «r01»
    texto: str
    tipo: str
    opciones: list[str] = field(default_factory=list)  # significados tal cual (para emparejar valores)
    escala: str = ""  # «1–5; niveles baja 1–2, media 3, alta 4–5»


@dataclass
class KpiCatalogo:
    id: str
    nombre: str
    preguntas: list[str] = field(default_factory=list)


@dataclass
class Catalogo:
    id: str  # id_crudo
    titulo: str
    tipo: str  # encuesta | prueba_estandarizada | entrevista
    preguntas: dict[str, PreguntaCatalogo]
    respondentes: list[str]  # IDs cortos en orden («R001», «R002»…)
    contexto: dict[str, list[str]]  # variable → valores
    kpis: list[KpiCatalogo]
    # Datos de contexto numéricos (edad, horas, semestre…) → (mínimo, máximo): admiten «más de» / «menos de».
    numericas: dict[str, tuple[float, float]] = field(default_factory=dict)

    def texto(self, compacto: bool = False) -> str:
        """Bloque para el prompt de interpretación; `compacto` recorta textos y opciones (varios instrumentos)."""
        max_texto, max_opciones = (50, 4) if compacto else (_MAX_TEXTO, _MAX_OPCIONES)
        lineas = [f"INSTRUMENTO {self.id} | {_TIPO_UI.get(self.tipo, self.tipo)} | «{self.titulo}»"]
        if self.respondentes:
            lineas.append(f"Respondentes: {len(self.respondentes)} ({self.respondentes[0]} a {self.respondentes[-1]})")
        if self.contexto:
            lineas.append("Contexto: " + "; ".join(f"{k} = {', '.join(v)}" for k, v in self.contexto.items()))
        if self.numericas:
            lineas.append("Contexto numérico: " + "; ".join(f"{k} ({_num(a)}–{_num(b)})" for k, (a, b) in self.numericas.items()))
        lineas.append("Preguntas:")
        for p in self.preguntas.values():
            escala = p.escala.split(" (")[0] if compacto else p.escala
            detalle = escala or ("; ".join(p.opciones[:max_opciones]) + (" …" if len(p.opciones) > max_opciones else ""))
            lineas.append(f"- {p.id} [{p.tipo}] {p.texto[:max_texto]}" + (f" → {detalle}" if detalle else ""))
        if self.kpis:
            lineas.append("KPIs: " + "; ".join(f"{k.id} {k.nombre}" for k in self.kpis))
        return "\n".join(lineas)


def _num(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else str(x)


def _numero(v: Any) -> float | None:
    if isinstance(v, bool):
        return None
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


def _numericas(contexto: dict[str, dict[str, None]]) -> dict[str, tuple[float, float]]:
    """Variables cuyos valores son todos números, con al menos 3 distintos («True»/«False» no cuentan)."""
    salida = {}
    for k, valores in contexto.items():
        numeros = [_numero(v) for v in valores]
        if len(numeros) >= 3 and all(n is not None for n in numeros):
            salida[k] = (min(numeros), max(numeros))
    return salida


def _corto(id_completo: str) -> str:
    return str(id_completo or "").rsplit("-", 1)[-1]


def _personas(doc: dict[str, Any]) -> list[dict[str, Any]]:
    if doc.get("entrevistas"):
        return [{"id": e.get("participante", ""), "contexto": e.get("contexto") or {}} for e in doc["entrevistas"]]
    return doc.get("respondentes") or doc.get("alumnos") or []


def _opciones_vistas(doc: dict[str, Any]) -> dict[str, list[str]]:
    """Significados que alguien eligió en cada pregunta (cuando la pregunta no declara sus opciones)."""
    vistas: dict[str, dict[str, None]] = {}
    for r in doc.get("respondentes") or []:
        for x in r.get("respuestas") or []:
            if x.get("estado") == "respondida" and x.get("significado") not in (None, ""):
                for s in x.get("seleccion") or [x["significado"]]:
                    vistas.setdefault(_corto(x["pregunta_id"]), {})[str(s)] = None
    return {k: list(v) for k, v in vistas.items()}


def _escala(p: dict[str, Any]) -> str:
    escala = p.get("escala") or {}
    if not escala.get("puntos"):
        return ""
    etiquetas = escala.get("etiquetas") or {}
    extremos = f"{etiquetas.get('1', '1')} … {etiquetas.get(str(escala['puntos']), escala['puntos'])}"
    niveles = "; ".join(f"{n} {'/'.join(str(x) for x in v)}" for n, v in (escala.get("niveles") or {}).items())
    return f"escala 1–{escala['puntos']} ({extremos})" + (f"; niveles {niveles}" if niveles else "")


def construir(id_crudo: str, titulo: str, tipo: str, doc: dict[str, Any]) -> Catalogo:
    """Catálogo de un documento final vigente."""
    vistas = _opciones_vistas(doc)
    preguntas: dict[str, PreguntaCatalogo] = {}
    for p in doc.get("preguntas") or doc.get("reactivos") or []:
        pid = _corto(p["id"])
        declaradas = p.get("opciones")
        if isinstance(declaradas, dict):  # reactivos: {"A": "56"} → «A) 56»
            opciones = [f"{k}) {v}" for k, v in declaradas.items()]
        else:
            opciones = list(declaradas or []) or vistas.get(pid, [])
        escala = _escala(p)
        if escala:  # en una escala las opciones son sus etiquetas; se conservan para validar
            opciones = list(dict.fromkeys([*(p.get("escala") or {}).get("etiquetas", {}).values(), *opciones]))
        preguntas[pid] = PreguntaCatalogo(pid, str(p.get("texto", "")), str(p.get("tipo") or p.get("tipo_reactivo") or ""),
                                          opciones, escala)
    personas = _personas(doc)
    contexto: dict[str, dict[str, None]] = {}
    for r in personas:
        for k, v in (r.get("contexto") or {}).items():
            if v not in (None, ""):
                contexto.setdefault(k, {})[str(v)] = None
    kpis = [KpiCatalogo(str(k.get("kpi_id", "")), str(k.get("nombre", "")),
                        [_corto(e["pregunta_id"]) for e in k.get("evidencia") or [] if e.get("pregunta_id")])
            for k in doc.get("kpis_asociados") or []]
    return Catalogo(
        id=str(id_crudo), titulo=titulo, tipo=tipo, preguntas=preguntas,
        respondentes=[_corto(r.get("id", "")) for r in personas if r.get("id")],
        contexto={k: list(v)[:_MAX_VALORES_CONTEXTO] for k, v in contexto.items() if len(v) <= 30},
        kpis=kpis,
        numericas=_numericas(contexto),
    )
