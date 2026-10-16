"""Motor de limpieza de entrevistas (DOCX, TXT, PDF).

Fase automática: extracción de texto → ciclo de limpieza de ruido (Figura 1) →
identificación de hablantes y turnos → roles sugeridos.

Fase asistida: el investigador confirma o corrige el rol de cada hablante, decide
qué hacer con el ruido que quedó y, si no se reconoce la estructura de hablantes,
recibe un aviso claro y confirma que se continúe por párrafos.

Salida: CSV con un turno por fila: n_turno; [participante;] hablante; rol; texto.
`participante` solo aparece si el archivo trae varias entrevistas («RESPONDENTE: R0001»).
"""
from __future__ import annotations

import re
from typing import Any

from shared.parsing import DocumentParseError, read_document

from services import configuracion
from services.configuracion import normalizar_texto
from services.motores import estadistica as estad
from services.motores import texto as limpieza_texto
from services.motores.base import Entrada, ErrorLimpieza, Hallazgo, ResultadoAutomatico, ResultadoFinal
from services.motores.entrevistas.hablantes import Estructura, Turno, segmentar, sugerir_roles

ROLES = ["entrevistador", "entrevistado", "otro"]
_TURNOS_VISTA = 12
_LARGO_TEXTO_VISTA = 280


def _cfg() -> dict[str, Any]:
    return configuracion.reglas()["entrevistas"]


def _slug(nombre: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", normalizar_texto(nombre)).strip("_") or "hablante"


def _leer(entrada: Entrada) -> str:
    try:
        doc = read_document(entrada.contenido, entrada.extension)
    except DocumentParseError as exc:
        raise ErrorLimpieza(f"No se pudo leer la entrevista: {exc}") from exc
    if not doc.text.strip():
        raise ErrorLimpieza(
            "No se pudo extraer texto del archivo (si es un PDF escaneado, necesita OCR). "
            "Sube la transcripción en DOCX o TXT."
        )
    return doc.text


def _preparar(entrada: Entrada) -> tuple[str, limpieza_texto.ResultadoTexto, Estructura]:
    cfg = _cfg()
    crudo = _leer(entrada)
    resultado = limpieza_texto.limpiar(crudo, int(cfg.get("max_iteraciones_ruido", 3)))
    if not resultado.texto.strip():
        raise ErrorLimpieza("Después de quitar el ruido, la entrevista quedó sin texto.")
    etiquetas_rol = {normalizar_texto(e) for e in cfg.get("etiquetas_entrevistador", []) + cfg.get("etiquetas_entrevistado", [])}
    return crudo, resultado, segmentar(resultado.texto, etiquetas_rol)


def _metricas(texto: str, estructura: Estructura | None = None) -> dict[str, Any]:
    lineas = [l for l in texto.split("\n") if l.strip()]
    metricas: dict[str, Any] = {
        "n_caracteres": len(texto),
        "n_palabras": len(texto.split()),
        "n_lineas": len(lineas),
    }
    if estructura is not None:
        metricas["n_turnos"] = len(estructura.turnos)
        metricas["n_hablantes"] = len(estructura.hablantes)
        metricas["estructura_reconocida"] = estructura.reconocida
    return metricas


def _palabras(texto: str) -> int:
    return len(texto.split())


def _es_pregunta(turno: Turno) -> bool:
    """Un turno del entrevistador abre una pregunta si es numerada, lleva «?» o es largo
    (no «Ajá» ni «Claro, continúa»)."""
    return turno.numero is not None or "?" in turno.texto or _palabras(turno.texto) >= 6


def _estadistica(estructura: Estructura, roles: dict[str, str]) -> dict[str, Any]:
    """Medidas centradas en las RESPUESTAS de los entrevistados.

    - Por pregunta del entrevistador: cuántas personas respondieron, cuántas no y la
      extensión de sus respuestas (las preguntas numeradas «P3» se agrupan por número;
      las demás, por su texto).
    - Por participante (bloque «RESPONDENTE: …» o, si no hay bloques, cada hablante
      entrevistado): número de preguntas respondidas y palabras.
    - Palabras por ROL (entrevistador frente a entrevistados), no por etiqueta.
    Se conserva la participación por hablante para los reportes anteriores.
    """
    turnos = estructura.turnos
    por_turno = estad.descriptivos([_palabras(t.texto) for t in turnos]) or {}
    if not estructura.reconocida:
        return {"palabras_por_turno": por_turno}

    total = sum(_palabras(t.texto) for t in turnos) or 1
    hablantes = []
    for h in estructura.hablantes:
        palabras = [_palabras(t.texto) for t in turnos if t.hablante == h.nombre]
        d = estad.descriptivos(palabras) or {}
        hablantes.append(
            {
                "nombre": h.nombre,
                "rol": roles.get(h.nombre),
                "turnos": len(palabras),
                "palabras": sum(palabras),
                "pct_palabras": round(sum(palabras) / total, 4),
                "palabras_por_turno": {k: d.get(k) for k in ("media", "mediana", "desviacion", "min", "max")},
                "pct_preguntas": round(h.proporcion_preguntas, 4),
            }
        )

    por_rol: dict[str, list[int]] = {}
    for t in turnos:
        por_rol.setdefault(roles.get(t.hablante) or "sin_rol", []).append(_palabras(t.texto))
    orden_rol = {"entrevistado": 0, "entrevistador": 1, "otro": 2}
    palabras_por_rol = [
        {"rol": r, "turnos": len(v), "palabras": sum(v), "pct_palabras": round(sum(v) / total, 4)}
        for r, v in sorted(por_rol.items(), key=lambda x: orden_rol.get(x[0], 3))
    ]

    # Respuestas: {pregunta: {persona: palabras}} y {persona: {pregunta: palabras}}.
    sin_pregunta = "(sin pregunta)"
    preguntas: dict[str, dict[str, Any]] = {}
    personas: dict[str, dict[str, int]] = {}
    actual: str | None = None
    bloque: str | None = None
    for t in turnos:
        if t.participante != bloque:
            bloque, actual = t.participante, None
        rol = roles.get(t.hablante)
        if rol == "entrevistador":
            if _es_pregunta(t):
                actual = f"P{t.numero}" if t.numero is not None else normalizar_texto(t.texto)[:160]
                preguntas.setdefault(actual, {"numero": t.numero, "texto": t.texto[:300], "respuestas": {}})
            continue
        if rol != "entrevistado":
            continue
        persona = t.participante or t.hablante
        clave = actual or sin_pregunta
        mias = personas.setdefault(persona, {})
        mias[clave] = mias.get(clave, 0) + _palabras(t.texto)
        if actual is not None:
            resp = preguntas[actual]["respuestas"]
            resp[persona] = resp.get(persona, 0) + _palabras(t.texto)

    n_personas = len(personas) or len(estructura.participantes)
    filas_preguntas = []
    for k, q in enumerate(preguntas.values(), start=1):
        valores = list(q["respuestas"].values())
        d = estad.descriptivos(valores) or {}
        filas_preguntas.append(
            {
                "pregunta": f"P{q['numero']}" if q["numero"] is not None else f"Pregunta {k}",
                "texto": q["texto"],
                "n_respuestas": len(valores),
                "sin_respuesta": max(0, n_personas - len(valores)),
                "palabras": {c: d.get(c) for c in ("media", "mediana", "min", "max")},
            }
        )
    filas_personas = []
    for persona, respuestas in personas.items():
        con_pregunta = [v for c, v in respuestas.items() if c != sin_pregunta]
        valores = con_pregunta or list(respuestas.values())
        filas_personas.append(
            {
                "id": persona,
                "respuestas": len(con_pregunta),
                "palabras": sum(respuestas.values()),
                "palabras_por_respuesta": round(sum(valores) / len(valores), 1) if valores else None,
            }
        )
    todas = [v for q in preguntas.values() for v in q["respuestas"].values()]
    return {
        "n_participantes": n_personas,
        "n_preguntas": len(preguntas),
        "n_respuestas": len(todas),
        "palabras_por_respuesta": estad.descriptivos(todas) or {},
        "preguntas": filas_preguntas,
        "participantes": filas_personas,
        "palabras_por_rol": palabras_por_rol,
        "hablantes": hablantes,
        "palabras_por_turno": por_turno,
    }


class MotorEntrevistas:
    """Limpieza de transcripciones de entrevistas."""

    nombre = "entrevistas"

    def automatica(self, entrada: Entrada) -> ResultadoAutomatico:
        cfg = _cfg()
        crudo, resultado, estructura = _preparar(entrada)
        metricas = _metricas(limpieza_texto.normalizar(crudo))
        metricas["ruido_detectado"] = len(limpieza_texto.detectar_ruido(limpieza_texto.normalizar(crudo)))

        hallazgos: list[Hallazgo] = []
        avisos: list[str] = []
        roles = sugerir_roles(
            estructura.hablantes,
            {normalizar_texto(e) for e in cfg.get("etiquetas_entrevistador", [])},
            {normalizar_texto(e) for e in cfg.get("etiquetas_entrevistado", [])},
        )
        if estructura.reconocida:
            for h in estructura.hablantes:
                sugerido, motivo = roles[h.nombre]
                hallazgos.append(
                    Hallazgo(
                        id=f"rol-hablante:{_slug(h.nombre)}", tipo="rol_hablante", tema="Hablantes", objetivo=h.nombre,
                        titulo=f"¿Quién es «{h.nombre}»?",
                        descripcion=(
                            f"Tiene {h.turnos} turno(s). Sugerimos «{sugerido}» {motivo}; confírmalo o corrígelo."
                            if sugerido
                            else f"Tiene {h.turnos} turno(s) y no pudimos inferir su rol: elígelo."
                        ),
                        opciones=ROLES, sugerida=sugerido, obligatoria=sugerido is None,
                        detalle={
                            "ejemplos": h.ejemplos,
                            "turnos": h.turnos,
                            "palabras": h.palabras,
                            "pct_preguntas": round(h.proporcion_preguntas, 4),
                        },
                    )
                )
        else:
            avisos.append(
                "No reconocimos la estructura de hablantes (por ejemplo «Entrevistador:» y «Entrevistado:» al inicio "
                "de cada intervención). El texto se dividirá por párrafos, sin hablantes ni roles. Si puedes, sube "
                "una transcripción con los hablantes marcados."
            )
            hallazgos.append(
                Hallazgo(
                    id="sin-hablantes", tipo="sin_hablantes", tema="Hablantes", objetivo="estructura",
                    titulo="No se reconocieron hablantes",
                    descripcion="Confirma que quieres continuar con el texto dividido por párrafos.",
                    opciones=["continuar_por_parrafos"], obligatoria=True,
                    detalle={"ejemplos": [t.texto[:90] for t in estructura.turnos[:2]], "parrafos": len(estructura.turnos)},
                )
            )

        if resultado.residual:
            avisos.append(f"Quedó ruido que no pudimos quitar automáticamente ({len(resultado.residual)} fragmento(s)).")
            hallazgos.append(
                Hallazgo(
                    id="ruido-residual", tipo="ruido_residual", tema="Ruido", objetivo="texto",
                    titulo=f"{len(resultado.residual)} fragmento(s) de ruido sin resolver",
                    descripcion=f"Tras {resultado.iteraciones} iteración(es) del ciclo de limpieza aún quedan. Puedes eliminar esas líneas o conservarlas.",
                    opciones=["eliminar", "conservar"], sugerida="conservar",
                    detalle={"ejemplos": [r["texto"] for r in resultado.residual[:4]], "lineas": sorted({r["linea"] for r in resultado.residual})[:20]},
                )
            )

        especifico = {
            "estructura_reconocida": estructura.reconocida,
            "hablantes": [
                {"nombre": h.nombre, "rol_sugerido": roles[h.nombre][0], "turnos": h.turnos, "palabras": h.palabras, "pct_preguntas": round(h.proporcion_preguntas, 4)}
                for h in estructura.hablantes
            ],
            "iteraciones_ruido": resultado.iteraciones,
            "ruido_eliminado": resultado.eliminado,
            "ruido_residual": resultado.residual,
            "n_turnos": len(estructura.turnos),
            # Varias entrevistas en un archivo: un bloque por persona con su contexto.
            "participantes": [{"id": p.id, "contexto": p.contexto} for p in estructura.participantes],
            "preambulo": estructura.preambulo,
        }
        sugeridos = {nombre: rol for nombre, (rol, *_resto) in roles.items()} if estructura.reconocida else {}
        return ResultadoAutomatico(
            hallazgos, resultado.transformaciones, metricas, especifico, avisos, _estadistica(estructura, sugeridos)
        )

    def aplicar(self, entrada: Entrada, automatico: ResultadoAutomatico, decisiones: dict[str, str]) -> ResultadoFinal:
        cfg = _cfg()
        _, resultado, estructura = _preparar(entrada)
        transformaciones: list[dict] = []

        if resultado.residual and decisiones.get("ruido-residual") == "eliminar":
            lineas = {r["linea"] for r in resultado.residual}
            texto = limpieza_texto.quitar_lineas(resultado.texto, lineas)
            etiquetas_rol = {normalizar_texto(e) for e in cfg.get("etiquetas_entrevistador", []) + cfg.get("etiquetas_entrevistado", [])}
            estructura = segmentar(limpieza_texto.normalizar_espacios(texto), etiquetas_rol)
            transformaciones.append({"regla": "ruido_residual_eliminado", "detalle": "Líneas con ruido residual eliminadas.", "afectados": len(lineas)})

        roles: dict[str, str] = {}
        if estructura.reconocida:
            sugeridos = sugerir_roles(
                estructura.hablantes,
                {normalizar_texto(e) for e in cfg.get("etiquetas_entrevistador", [])},
                {normalizar_texto(e) for e in cfg.get("etiquetas_entrevistado", [])},
            )
            for h in estructura.hablantes:
                roles[h.nombre] = decisiones.get(f"rol-hablante:{_slug(h.nombre)}") or sugeridos[h.nombre][0] or "otro"

        con_bloques = bool(estructura.participantes)
        filas = [
            [str(i), *([t.participante] if con_bloques else []), t.hablante,
             roles.get(t.hablante, "desconocido") if t.hablante else "desconocido", t.texto]
            for i, t in enumerate(estructura.turnos, start=1)
        ]
        texto_final = "\n".join(t.texto for t in estructura.turnos)
        metricas = _metricas(texto_final, estructura)
        metricas["ruido_detectado"] = len(limpieza_texto.detectar_ruido(texto_final))

        especifico = dict(automatico.especifico)
        especifico["hablantes"] = [
            {"nombre": h.nombre, "rol": roles.get(h.nombre), "turnos": h.turnos, "palabras": h.palabras}
            for h in estructura.hablantes
        ]
        especifico["n_turnos"] = len(estructura.turnos)
        especifico["participantes"] = [{"id": p.id, "contexto": p.contexto} for p in estructura.participantes]
        especifico["preambulo"] = estructura.preambulo
        if roles:
            transformaciones.append({"regla": "roles_asignados", "detalle": "Rol asignado a cada hablante (confirmado por el investigador).", "afectados": len(roles)})

        ruido = sum(v for k, v in resultado.eliminado.items() if k != "palabras_reconstruidas")
        estadistica = _estadistica(estructura, roles)
        cifras = (
            [
                {"etiqueta": "Entrevistados", "valor": estadistica["n_participantes"]},
                {"etiqueta": "Preguntas", "valor": estadistica["n_preguntas"]},
                {"etiqueta": "Respuestas", "valor": estadistica["n_respuestas"]},
            ]
            if estructura.reconocida
            else [{"etiqueta": "Párrafos", "valor": len(filas)}]
        )
        return ResultadoFinal(
            encabezados=["n_turno", *(["participante"] if con_bloques else []), "hablante", "rol", "texto"],
            filas=filas,
            metricas=metricas,
            especifico=especifico,
            transformaciones=transformaciones,
            cifras=[
                *cifras,
                {"etiqueta": "Turnos", "valor": len(filas)},
                {"etiqueta": "Hablantes", "valor": len(estructura.hablantes)},
                {"etiqueta": "Palabras", "valor": metricas["n_palabras"]},
                {"etiqueta": "Ruido eliminado", "valor": ruido},
            ],
            vista={
                "forma": "turnos",
                "columnas": ["#", *(["Entrevistado"] if con_bloques else []), "Hablante", "Rol", "Texto"],
                "filas": [
                    [*f[:-3], f[-3] or "—", f[-2], f[-1][:_LARGO_TEXTO_VISTA] + ("…" if len(f[-1]) > _LARGO_TEXTO_VISTA else "")]
                    for f in filas[:_TURNOS_VISTA]
                ],
            },
            estadistica=estadistica,
        )
