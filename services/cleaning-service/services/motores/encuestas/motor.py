"""Motor de limpieza de encuestas (CSV, XLSX, XLS).

Fase automática (sin decisiones):
  transformaciones universales → columnas ajenas al instrumento (propuestas) →
  roles sugeridos → tipos canónicos provisionales → métricas (Tabla 3) → hallazgos.

Fase asistida (decide el investigador): columnas ajenas, roles dudosos, columnas
muy incompletas, filas duplicadas, valores fuera de rango, escalas que parecen
Likert pero no están en el diccionario, ítems Likert invertidos, encuestados que
responden en línea recta, encuestados que dejaron casi todo sin responder y respuestas
«No sé / No aplica» (conservarlas marcadas o dejarlas vacías).

Medidas estadísticas (antes y después): descriptivos por columna, frecuencias,
atípicos (±4σ e IQR) y fiabilidad (alfa de Cronbach por bloque de ítems Likert).

`aplicar` repite la preparación (determinista) y aplica las decisiones.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from shared.parsing import TabularParseError, read_tabular

from services import configuracion
from services.configuracion import normalizar_texto
from services.motores import estadistica as est
from services.motores.base import Entrada, ErrorLimpieza, Hallazgo, ResultadoAutomatico, ResultadoFinal
from services.motores.encuestas import universales
from services.motores.encuestas.likert import Likert, likert_desde_orden, no_respuestas, numero
from services.motores.encuestas.tipos import InfoTipo, grupo_bloque, grupo_de, inferir, metodo_atipicos

_FILAS_VISTA = 10
_EJEMPLOS = 4


@dataclass
class Estado:
    """Todo lo que deciden juntas la fase automática y la aplicación."""

    tabla: universales.TablaPreparada
    tipos: dict[str, InfoTipo]  # por id de columna
    ajenas: set[str]
    rol_auto: dict[str, str]  # roles decididos automáticamente (encabezado > 25 caracteres)
    duplicadas: list[int]  # filas repetidas (se conserva la primera aparición)
    metricas_antes: dict[str, Any]
    linea_recta: list[int] = field(default_factory=list)  # encuestados con la misma respuesta en todo un bloque
    bloques_linea_recta: list[str] = field(default_factory=list)
    incompletos: list[int] = field(default_factory=list)  # encuestados que dejaron casi todo vacío


def _cfg() -> dict[str, Any]:
    return configuracion.reglas()["encuestas"]


# ── Preparación (común a ambas fases) ──────────────────────────────────────────


def _leer(entrada: Entrada):  # noqa: ANN202
    try:
        tabla = read_tabular(entrada.contenido, entrada.extension)
    except TabularParseError as exc:
        raise ErrorLimpieza(f"No se pudo leer la encuesta: {exc}") from exc
    if not tabla.headers or not any(h.strip() for h in tabla.headers):
        raise ErrorLimpieza("La encuesta no tiene encabezados de columna en la primera fila.")
    if not tabla.rows:
        raise ErrorLimpieza("La encuesta no tiene respuestas (solo encabezados).")
    return tabla


def _es_ajena(etiqueta: str, patrones: list[str]) -> bool:
    texto = normalizar_texto(etiqueta)
    return any(re.search(p, texto) for p in patrones)


def _preparar(entrada: Entrada) -> Estado:
    cfg = _cfg()
    crudo = _leer(entrada)
    metricas_antes = _metricas_crudas(crudo, cfg)
    tabla = universales.preparar(crudo, cfg.get("tokens_vacio", []))
    if not tabla.columnas or tabla.n_filas == 0:
        raise ErrorLimpieza("Después de quitar filas y columnas vacías, la encuesta no tiene datos.")

    tipos = {c.id: inferir(c.etiqueta, c.valores, cfg) for c in tabla.columnas}
    ajenas = {c.id for c in tabla.columnas if _es_ajena(c.etiqueta, cfg.get("columnas_ajenas", []))}
    largo = int(cfg.get("largo_minimo_pregunta", 25))
    rol_auto = {c.id: "pregunta" for c in tabla.columnas if c.id not in ajenas and len(c.etiqueta) > largo}

    # Duplicados: filas idénticas sin contar las columnas ajenas (marcas de tiempo e IDs
    # hacen única cualquier fila aunque las respuestas sean las mismas).
    instrumento = [c for c in tabla.columnas if c.id not in ajenas] or tabla.columnas
    vistos: set[tuple] = set()
    duplicadas: list[int] = []
    for i in range(tabla.n_filas):
        clave = tuple(c.valores[i] for c in instrumento)
        if clave in vistos:
            duplicadas.append(i)
        vistos.add(clave)

    estado = Estado(tabla, tipos, ajenas, rol_auto, duplicadas, metricas_antes)
    todas = list(range(tabla.n_filas))
    propias = [c for c in tabla.columnas if c.id not in ajenas]
    lr, bloques = _linea_recta(estado, propias, todas)
    estado.linea_recta, estado.bloques_linea_recta = sorted(lr), bloques
    estado.incompletos = sorted(_incompletos(propias, todas))
    metricas_antes["n_linea_recta"] = len(lr)
    metricas_antes["n_incompletos"] = len(estado.incompletos)
    return estado


# ── Encuestados (filas) ────────────────────────────────────────────────────────


def _est_cfg() -> dict[str, Any]:
    return _cfg().get("estadistica") or {}


def _codigo(info: InfoTipo, valor: str | None, excluir: set[str]) -> float | None:
    """Código numérico de una respuesta Likert (None si falta, se excluye o no es de la escala)."""
    if valor is None or not info.likert:
        return None
    if info.likert.escala == "numerica":
        return numero(valor)
    n = normalizar_texto(valor)
    if n in excluir:
        return None
    codigo = info.likert.codigos.get(n)
    return float(codigo) if codigo is not None else None


def _extremos(info: InfoTipo) -> tuple[float, float]:
    lik = info.likert
    if lik and lik.escala == "numerica":
        return float(lik.etiquetas[0]), float(lik.etiquetas[-1])
    return 1.0, float(lik.puntos if lik else 1)


_TODAS = "Todas las escalas Likert"


def _bloques_likert(estado: Estado, columnas: list) -> list[tuple[str, list]]:  # noqa: ANN001
    """Bloques de ítems Likert: cada cuadrícula «Pregunta [aspecto]» o prefijo numerado
    («Aportación_item1…») y, si hay varias escalas que no forman un solo bloque, el
    conjunto de todas las escalas."""
    likert = [c for c in columnas if estado.tipos[c.id].likert]
    grupos: dict[str, list] = {}
    for c in likert:
        g = grupo_bloque(c.etiqueta)
        if g:
            grupos.setdefault(g[0], []).append(c)
    bloques = [(padre, cols) for padre, cols in grupos.items() if len(cols) >= 2]
    if len(likert) >= 2 and not (len(bloques) == 1 and len(bloques[0][1]) == len(likert)):
        bloques.append((_TODAS, likert))
    return bloques


def _linea_recta(estado: Estado, columnas: list, filas: list[int]) -> tuple[set[int], list[str]]:  # noqa: ANN001
    """Encuestados que eligieron la MISMA opción en todos los ítems de un bloque Likert
    (respondieron todos y el bloque tiene al menos `linea_recta_min_items` ítems)."""
    minimo = int(_est_cfg().get("linea_recta_min_items", 4))
    excluir = no_respuestas()
    bloques = [(n, cols) for n, cols in _bloques_likert(estado, columnas) if len(cols) >= minimo]
    # Las cuadrículas son el caso clásico; el bloque global solo cuenta si no hay cuadrículas grandes.
    if len(bloques) > 1:
        bloques = [b for b in bloques if b[0] != _TODAS]
    marcadas: set[int] = set()
    usados: list[str] = []
    for nombre, cols in bloques:
        hubo = False
        for i in filas:
            codigos = [_codigo(estado.tipos[c.id], c.valores[i], excluir) for c in cols]
            if all(x is not None for x in codigos) and len(set(codigos)) == 1:
                marcadas.add(i)
                hubo = True
        if hubo:
            usados.append(nombre)
    return marcadas, usados


def _incompletos(columnas: list, filas: list[int]) -> set[int]:  # noqa: ANN001
    """Encuestados que dejaron sin responder más del umbral de las columnas del instrumento."""
    umbral = float(_est_cfg().get("encuestado_incompleto", 0.5))
    if len(columnas) < 2:
        return set()
    return {i for i in filas if sum(1 for c in columnas if c.valores[i] is None) / len(columnas) > umbral}


# ── Estadística descriptiva y fiabilidad ───────────────────────────────────────

_NUMERICOS = ("numerica", "escala_lineal", "calificacion")


def _estadistica(
    estado: Estado,
    columnas: list,  # noqa: ANN001
    valores: dict[str, list[str | None]],
    roles: dict[str, str],
) -> dict[str, Any]:
    """Medidas por columna y fiabilidad por bloque Likert.

    `valores` son las respuestas (antes de codificar las escalas) de las filas que se analizan.
    """
    cfg = _cfg()
    excluir = no_respuestas()
    metodo, _ = metodo_atipicos(cfg)
    k_sigma = float(cfg["umbrales"].get("sigma_fuera_de_rango", 4))
    k_iqr = float(_est_cfg().get("factor_iqr", 1.5))
    minimo_atipicos = int(cfg["umbrales"].get("filas_minimas_sigma", 10))
    separadores = cfg["tipos"].get("separadores_multiple", [",", ";"])
    salida_cols = []
    for c in columnas:
        info = estado.tipos[c.id]
        vals = valores[c.id]
        presentes = [v for v in vals if v is not None]
        n = len(vals)
        fila: dict[str, Any] = {
            "id": c.id,
            "etiqueta": c.etiqueta,
            "tipo": info.tipo,
            "rol": roles.get(c.id),
            "n": len(presentes),
            "n_nulos": n - len(presentes),
            "pct_nulos": round((n - len(presentes)) / n, 4) if n else 0.0,
        }
        if info.likert:
            lik = info.likert
            codigos = [_codigo(info, v, excluir) for v in presentes]
            if lik.escala == "numerica":
                etiqueta_de = {float(e): e for e in lik.etiquetas}
            else:
                etiqueta_de = {float(p): e for p, e in enumerate(lik.etiquetas, start=1)}
            fila["numerico"] = est.descriptivos([x for x in codigos if x is not None])
            fila["frecuencias"] = est.frecuencias(
                [etiqueta_de[x] for x in codigos if x is not None and x in etiqueta_de], orden=lik.etiquetas
            )
            fila["n_excluidos"] = sum(1 for v in presentes if normalizar_texto(v) in excluir)
            fila["escala"] = {"puntos": lik.puntos, "invertido": lik.invertido}
        elif info.tipo in _NUMERICOS:
            xs = [x for x in (numero(v) for v in presentes) if x is not None]
            fila["numerico"] = est.descriptivos(xs)
            if len(xs) >= minimo_atipicos:
                fila["atipicos"] = {
                    "metodo": metodo,
                    "sigma": est.contar_fuera(xs, est.limites_atipicos(xs, "sigma", k_sigma)),
                    "iqr": est.contar_fuera(xs, est.limites_atipicos(xs, "iqr", k_iqr)),
                    "factor_sigma": k_sigma,
                    "factor_iqr": k_iqr,
                }
        elif info.tipo in ("binaria", "categorica"):
            fila["frecuencias"] = est.frecuencias(presentes)
        elif info.tipo == "opcion_multiple_varias":
            patron = "|".join(re.escape(s) for s in separadores)
            opciones = [o.strip() for v in presentes for o in re.split(patron, v) if o.strip()]
            fila["frecuencias"] = est.frecuencias(opciones)
        elif info.tipo in ("texto_corto", "texto_largo"):
            palabras = [len(v.split()) for v in presentes]
            fila["texto"] = {
                "palabras_promedio": round(sum(palabras) / len(palabras), 1) if palabras else 0.0,
                "respuestas_distintas": len({normalizar_texto(v) for v in presentes}),
            }
        salida_cols.append(fila)

    # Fiabilidad: alfa de Cronbach por bloque (los ítems invertidos se recodifican).
    min_casos = int(_est_cfg().get("fiabilidad_min_casos", 3))
    fiabilidad = []
    n_filas = len(next(iter(valores.values()), []))
    for nombre, cols in _bloques_likert(estado, columnas):
        matriz: list[list[float | None]] = []
        for k in range(n_filas):
            fila_codigos = []
            for c in cols:
                info = estado.tipos[c.id]
                x = _codigo(info, valores[c.id][k], excluir)
                if x is not None and info.likert.invertido:
                    lo, hi = _extremos(info)
                    x = lo + hi - x
                fila_codigos.append(x)
            matriz.append(fila_codigos)
        items = [(grupo_bloque(c.etiqueta) or (None, c.etiqueta))[1] for c in cols] if nombre != _TODAS else [c.etiqueta for c in cols]
        resultado = est.cronbach(matriz, items, min_casos) or {
            "n_items": len(cols), "n_casos": 0, "n_excluidos": n_filas, "alfa": None, "interpretacion": None, "por_item": []
        }
        fiabilidad.append(
            {
                "bloque": nombre,
                "items": items,
                "invertidos": [items[j] for j, c in enumerate(cols) if estado.tipos[c.id].likert.invertido],
                **resultado,
            }
        )
    return {"columnas": salida_cols, "fiabilidad": fiabilidad}


# ── Métricas (Tabla 3) ─────────────────────────────────────────────────────────


def _metricas(
    columnas: list[tuple[str, list[str | None]]],
    n_duplicados: int,
    n_imposibles: int,
    grupos: list[dict],
    umbrales: dict[str, Any],
) -> dict[str, Any]:
    n_filas = len(columnas[0][1]) if columnas else 0
    celdas = n_filas * len(columnas)
    nulas = sum(1 for _, vals in columnas for v in vals if v is None)
    pct_nulos = round(nulas / celdas, 4) if celdas else 0.0
    por_columna = sorted(
        ((etq, round(sum(1 for v in vals if v is None) / n_filas, 4) if n_filas else 0.0) for etq, vals in columnas),
        key=lambda x: -x[1],
    )
    metricas = {
        "n_respondentes": n_filas,
        "n_columnas": len(columnas),
        "pct_completitud": round(1 - pct_nulos, 4) if celdas else 0.0,
        "pct_nulos": pct_nulos,
        "n_duplicados": n_duplicados,
        "n_imposibles": n_imposibles,
        "cols_mas_nulos": [{"columna": etq, "pct_nulos": p} for etq, p in por_columna[:5] if p > 0],
        "grupos_detectados": grupos,
    }
    alertas = []
    if metricas["pct_completitud"] < umbrales.get("completitud_minima", 0.6):
        alertas.append("completitud_baja")
    if pct_nulos > umbrales.get("nulos_maximo", 0.4):
        alertas.append("nulos_altos")
    if n_duplicados > 0:
        alertas.append("duplicados")
    if n_imposibles > 0:
        alertas.append("valores_imposibles")
    metricas["alertas"] = alertas
    return metricas


def _metricas_crudas(crudo, cfg: dict[str, Any]) -> dict[str, Any]:  # noqa: ANN001
    """Métricas del archivo tal como llegó (los tokens de vacío cuentan como vacíos)."""
    vacios = {normalizar_texto(t) for t in cfg.get("tokens_vacio", [])}
    columnas = []
    for j, h in enumerate(crudo.headers):
        vals = [None if normalizar_texto(f[j] if j < len(f) else "") in vacios else f[j] for f in crudo.rows]
        columnas.append((h or f"Columna {j + 1}", vals))
    # Duplicados con la misma definición que el hallazgo: sin contar columnas ajenas
    # (una marca temporal distinta no hace distinta una respuesta repetida).
    patrones = cfg.get("columnas_ajenas", [])
    instrumento = [vals for etq, vals in columnas if not _es_ajena(etq, patrones)] or [v for _, v in columnas]
    filas = [tuple(vals[i] for vals in instrumento) for i in range(len(crudo.rows))]
    filas_con_dato = [f for f in filas if any(v is not None for v in f)]
    n_dup = len(filas_con_dato) - len(set(filas_con_dato))
    tipos = {etq: inferir(etq, vals, cfg) for etq, vals in columnas if any(v is not None for v in vals)}
    n_imp = sum(len(t.fuera) for t in tipos.values())
    return _metricas(columnas, n_dup, n_imp, _grupos([(etq, tipos.get(etq)) for etq, _ in columnas]), cfg["umbrales"])


def _grupos(columnas: list[tuple[str, InfoTipo | None]]) -> list[dict]:
    """Grupos padre-hijo («Pregunta [aspecto]») con el tipo más común de sus hijos."""
    grupos: dict[str, dict] = {}
    for etiqueta, info in columnas:
        g = grupo_de(etiqueta)
        if not g:
            continue
        datos = grupos.setdefault(g[0], {"padre": g[0], "hijos": [], "tipos": []})
        datos["hijos"].append(g[1])
        if info:
            datos["tipos"].append(info.tipo)
    salida = []
    for datos in grupos.values():
        if len(datos["hijos"]) < 2:
            continue
        tipos = datos.pop("tipos")
        datos["tipo"] = max(set(tipos), key=tipos.count) if tipos else None
        salida.append(datos)
    return salida


# ── Hallazgos ──────────────────────────────────────────────────────────────────


def _ejemplos(valores: list[str | None]) -> list[str]:
    vistos: list[str] = []
    for v in valores:
        if v is not None and v not in vistos:
            vistos.append(v)
        if len(vistos) >= _EJEMPLOS:
            break
    return vistos


def _no_respuestas_por_columna(estado: Estado) -> dict[str, list[str]]:
    """{id de columna: valores «No sé / No aplica» (tal cual)} en las escalas Likert de texto.

    No son puntos de la escala (no cuentan en promedios ni en la fiabilidad), pero
    tampoco son celdas vacías: el investigador decide si se conservan marcadas.
    """
    excluir = no_respuestas()
    salida: dict[str, list[str]] = {}
    for c in estado.tabla.columnas:
        info = estado.tipos[c.id]
        if c.id in estado.ajenas or not info.likert or info.likert.escala == "numerica":
            continue
        valores = [v for v in c.valores if v is not None and normalizar_texto(v) in excluir]
        if valores:
            salida[c.id] = valores
    return salida


def _hallazgos(estado: Estado) -> list[Hallazgo]:
    cfg = _cfg()
    umbrales = cfg["umbrales"]
    patron_codigo = re.compile(cfg.get("patron_codigo_corto", r"^[A-Za-z]{1,3}\d+([_.]\d+)*$"))
    contexto = [normalizar_texto(p) for p in cfg.get("palabras_contexto", [])]
    invertidas = [normalizar_texto(p).strip() for p in cfg["tipos"].get("palabras_invertido", [])]
    n = estado.tabla.n_filas
    salida: list[Hallazgo] = []

    for c in estado.tabla.columnas:
        info = estado.tipos[c.id]
        ejemplos = _ejemplos(c.valores)
        pct_nulos = round(sum(1 for v in c.valores if v is None) / n, 4) if n else 0.0
        base = {"columna": c.etiqueta, "ejemplos": ejemplos, "tipo": info.tipo, "pct_nulos": pct_nulos}

        # Columnas que no pertenecen al instrumento (preseleccionadas para eliminar).
        if c.id in estado.ajenas:
            salida.append(
                Hallazgo(
                    id=f"col-ajena:{c.id}", tipo="columna_ajena", tema="Columnas que no son del instrumento",
                    objetivo=c.id, titulo=f"«{c.etiqueta}» no parece parte del instrumento",
                    descripcion="Parece un dato de la plataforma (identificador, fecha u hora, sesión). Te sugerimos eliminarla.",
                    opciones=["eliminar", "conservar"], sugerida="eliminar", detalle=base,
                )
            )
            continue

        # Roles: > 25 caracteres ya es pregunta; códigos cortos los decide el investigador.
        if c.id not in estado.rol_auto:
            es_codigo = bool(patron_codigo.match(c.etiqueta.strip()))
            etq = f" {normalizar_texto(c.etiqueta)} "
            sugerida = None if es_codigo else ("contexto" if any(f" {p} " in etq for p in contexto) else "pregunta")
            salida.append(
                Hallazgo(
                    id=f"rol:{c.id}", tipo="rol_columna", tema="Rol de las columnas", objetivo=c.id,
                    titulo=f"¿Qué es «{c.etiqueta}»?",
                    descripcion=(
                        "Es un código corto: revisa sus valores y elige si es una pregunta del instrumento, "
                        "un dato de contexto o una columna a eliminar."
                        if es_codigo
                        else "El encabezado es corto; confirma si es una pregunta del instrumento o un dato de contexto."
                    ),
                    opciones=["pregunta", "contexto", "eliminar"], sugerida=sugerida, obligatoria=es_codigo, detalle=base,
                )
            )

        # Columnas muy incompletas (umbrales de la Tabla 3).
        if pct_nulos > umbrales.get("nulos_maximo", 0.4) or (1 - pct_nulos) < umbrales.get("completitud_minima", 0.6):
            sugerir_eliminar = pct_nulos >= umbrales.get("nulos_sugerir_eliminar", 0.9)
            salida.append(
                Hallazgo(
                    id=f"incompleta:{c.id}", tipo="columna_incompleta", tema="Calidad de los datos", objetivo=c.id,
                    titulo=f"«{c.etiqueta}» está vacía en el {round(pct_nulos * 100)} % de las respuestas",
                    descripcion="Supera el umbral de vacíos (40 %). Puedes conservarla o eliminarla.",
                    opciones=["conservar", "eliminar"], sugerida="eliminar" if sugerir_eliminar else "conservar", detalle=base,
                )
            )

        # Valores fuera de rango.
        if info.fuera:
            filas = sorted(info.fuera)
            valores = _ejemplos([c.valores[i] for i in filas])
            rango = (
                f"entre {_fmt(info.rango[0])} y {_fmt(info.rango[1])}" if info.rango else "dentro de la escala"
            )
            if info.tipo != "numerica":
                explicacion = f"La escala va {rango}; estos valores no pertenecen a ella."
            elif info.metodo_atipicos == "iqr":
                explicacion = f"Son atípicos según el rango intercuartílico (fuera de {rango})."
            else:
                k = _fmt(float(umbrales.get("sigma_fuera_de_rango", 4)))
                explicacion = f"Están a más de {k} desviaciones estándar del promedio (fuera de {rango})."
            salida.append(
                Hallazgo(
                    id=f"rango:{c.id}", tipo="fuera_de_rango", tema="Calidad de los datos", objetivo=c.id,
                    titulo=f"{len(filas)} valor(es) fuera de rango en «{c.etiqueta}»",
                    descripcion=explicacion + " Te sugerimos dejarlos vacíos.",
                    opciones=["anular", "conservar"], sugerida="anular",
                    detalle={**base, "valores": valores, "filas": [i + 1 for i in filas[:20]], "rango": info.rango},
                )
            )

        # Escalas que parecen Likert pero no están en el diccionario.
        if info.dudosa and not info.likert:
            seguro = info.dudosa["cobertura"] >= 0.5
            salida.append(
                Hallazgo(
                    id=f"likert-orden:{c.id}", tipo="likert_orden", tema="Escalas", objetivo=c.id,
                    titulo=f"«{c.etiqueta}» parece una escala",
                    descripcion="No está en el diccionario de escalas. Confirma el orden de sus opciones (de menor a mayor) o indica que no es una escala.",
                    opciones=["usar_orden_propuesto", "invertir_orden", "no_es_likert"],
                    sugerida="usar_orden_propuesto" if seguro else None, obligatoria=not seguro,
                    detalle={**base, "orden_propuesto": info.dudosa["orden_propuesto"]},
                )
            )

        # Ítems Likert invertidos (la pregunta está redactada en negativo).
        if info.likert and info.tipo in ("likert", "cuadricula"):
            # Solo palabras: «[nunca …]» o «¿No …?» también cuentan.
            etq = f" {re.sub(r'[^\w]+', ' ', normalizar_texto(c.etiqueta))} "
            if any(f" {p} " in etq for p in invertidas):
                salida.append(
                    Hallazgo(
                        id=f"invertido:{c.id}", tipo="item_invertido", tema="Escalas", objetivo=c.id,
                        titulo=f"«{c.etiqueta}» podría ser un ítem invertido",
                        descripcion="Está redactado en negativo: un valor alto podría significar lo contrario que en las demás preguntas. Se marca en los metadatos; los datos no se modifican.",
                        opciones=["invertido", "no_invertido"], sugerida="invertido",
                        detalle={**base, "etiquetas": info.likert.etiquetas},
                    )
                )

    no_resp = _no_respuestas_por_columna(estado)
    if no_resp:
        total = sum(len(v) for v in no_resp.values())
        etiquetas = {c.id: c.etiqueta for c in estado.tabla.columnas}
        distintos = sorted({v for vals in no_resp.values() for v in vals})
        salida.append(
            Hallazgo(
                id="no-respuestas", tipo="no_respuestas", tema="Calidad de las respuestas", objetivo="celdas",
                titulo=f"{total} respuesta(s) «{' / '.join(distintos[:3])}» en {len(no_resp)} escala(s)",
                descripcion=(
                    "No son puntos de la escala: no cuentan en promedios ni en la fiabilidad. Te sugerimos "
                    "conservarlas marcadas para distinguirlas de las preguntas que se dejaron en blanco; "
                    "si prefieres, pueden quedar como celdas vacías."
                ),
                opciones=["conservar_marcadas", "vaciar"], sugerida="conservar_marcadas",
                detalle={
                    "ejemplos": distintos[:6],
                    "total": total,
                    "columnas": [{"columna": etiquetas[cid], "n": len(v)} for cid, v in no_resp.items()][:20],
                },
            )
        )
    if estado.duplicadas:
        salida.append(
            Hallazgo(
                id="duplicados", tipo="duplicados", tema="Calidad de los datos", objetivo="filas",
                titulo=f"{len(estado.duplicadas)} fila(s) duplicada(s)",
                descripcion="Tienen exactamente las mismas respuestas que otra fila (sin contar identificadores ni marcas de tiempo). Te sugerimos eliminarlas y conservar la primera.",
                opciones=["eliminar", "conservar"], sugerida="eliminar",
                detalle={"filas": [i + 1 for i in estado.duplicadas[:20]], "total": len(estado.duplicadas)},
            )
        )
    if estado.linea_recta:
        bloques = ", ".join(f"«{b}»" for b in estado.bloques_linea_recta)
        salida.append(
            Hallazgo(
                id="linea-recta", tipo="linea_recta", tema="Calidad de las respuestas", objetivo="filas",
                titulo=f"{len(estado.linea_recta)} encuestado(s) respondieron en línea recta",
                descripcion=(
                    f"Eligieron la misma opción en todos los ítems de {bloques}. Puede indicar que respondieron "
                    "sin leer, aunque también puede ser una opinión genuina. Te sugerimos conservarlos y tenerlo en cuenta en el análisis."
                ),
                opciones=["conservar", "eliminar"], sugerida="conservar",
                detalle={"filas": [i + 1 for i in estado.linea_recta[:20]], "total": len(estado.linea_recta), "bloques": estado.bloques_linea_recta},
            )
        )
    if estado.incompletos:
        umbral = float(_est_cfg().get("encuestado_incompleto", 0.5))
        salida.append(
            Hallazgo(
                id="incompletos", tipo="encuestados_incompletos", tema="Calidad de las respuestas", objetivo="filas",
                titulo=f"{len(estado.incompletos)} encuestado(s) dejaron sin responder más del {round(umbral * 100)} %",
                descripcion="Sus respuestas aportan poca información y pueden sesgar los resultados. Te sugerimos eliminarlos.",
                opciones=["eliminar", "conservar"], sugerida="eliminar",
                detalle={"filas": [i + 1 for i in estado.incompletos[:20]], "total": len(estado.incompletos), "umbral": umbral},
            )
        )
    return salida


def _fmt(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else str(x)


def _especifico(estado: Estado, roles: dict[str, str], eliminadas: dict[str, str]) -> dict[str, Any]:
    columnas = []
    n = estado.tabla.n_filas
    for c in estado.tabla.columnas:
        info = estado.tipos[c.id]
        columnas.append(
            {
                "id": c.id,
                "etiqueta": c.etiqueta,
                "rol": roles.get(c.id),
                "tipo_canonico": info.tipo,
                "pct_nulos": round(sum(1 for v in c.valores if v is None) / n, 4) if n else 0.0,
                "likert": info.likert.a_reporte() if info.likert else None,
                "rango": list(info.rango) if info.rango else None,
                "estadisticos": info.estadisticos or None,
                "estado": "eliminada" if c.id in eliminadas else "conservada",
                "motivo_eliminacion": eliminadas.get(c.id),
            }
        )
    return {
        "columnas": columnas,
        "grupos_detectados": _grupos([(c.etiqueta, estado.tipos[c.id]) for c in estado.tabla.columnas]),
        "columnas_vacias_eliminadas": estado.tabla.columnas_vacias,
        "filas_eliminadas": {"vacias": estado.tabla.filas_vacias, "duplicadas": 0},
    }


# ── Motor ──────────────────────────────────────────────────────────────────────


class MotorEncuestas:
    """Limpieza de encuestas tabulares."""

    nombre = "encuestas"

    def automatica(self, entrada: Entrada) -> ResultadoAutomatico:
        estado = _preparar(entrada)
        hallazgos = _hallazgos(estado)
        transformaciones = list(estado.tabla.transformaciones)
        if estado.rol_auto:
            transformaciones.append(
                {
                    "regla": "roles_automaticos",
                    "detalle": "Columnas con encabezado largo (más de 25 caracteres) clasificadas como pregunta.",
                    "afectados": len(estado.rol_auto),
                }
            )
        roles = dict(estado.rol_auto)
        propias = [c for c in estado.tabla.columnas if c.id not in estado.ajenas]
        estadistica = _estadistica(estado, propias, {c.id: c.valores for c in propias}, roles)
        estadistica["encuestados"] = {"linea_recta": len(estado.linea_recta), "incompletos": len(estado.incompletos)}
        avisos = []
        if any(h.obligatoria for h in hallazgos):
            avisos.append("Hay columnas con códigos cortos: revisa su rol antes de continuar.")
        return ResultadoAutomatico(
            hallazgos=hallazgos,
            transformaciones=transformaciones,
            metricas=estado.metricas_antes,
            especifico=_especifico(estado, roles, {}),
            avisos=avisos,
            estadistica=estadistica,
        )

    def aplicar(self, entrada: Entrada, automatico: ResultadoAutomatico, decisiones: dict[str, str]) -> ResultadoFinal:
        estado = _preparar(entrada)
        cfg = _cfg()
        excluir = no_respuestas()

        roles: dict[str, str] = dict(estado.rol_auto)
        eliminadas: dict[str, str] = {}
        for c in estado.tabla.columnas:
            if c.id in estado.ajenas:
                if decisiones.get(f"col-ajena:{c.id}", "eliminar") == "eliminar":
                    eliminadas[c.id] = "no pertenece al instrumento"
                else:
                    roles[c.id] = "contexto"
                continue
            rol = decisiones.get(f"rol:{c.id}") or roles.get(c.id) or "pregunta"
            if rol == "eliminar":
                eliminadas[c.id] = "decisión del investigador"
                continue
            roles[c.id] = rol
            if decisiones.get(f"incompleta:{c.id}") == "eliminar":
                eliminadas[c.id] = "demasiados valores vacíos"

        # Escalas: orden confirmado e ítems invertidos (solo metadatos; los datos no se recodifican).
        for c in estado.tabla.columnas:
            info = estado.tipos[c.id]
            decision = decisiones.get(f"likert-orden:{c.id}")
            if info.dudosa and not info.likert and decision in ("usar_orden_propuesto", "invertir_orden"):
                orden = list(info.dudosa["orden_propuesto"])
                if decision == "invertir_orden":
                    orden.reverse()
                info.likert = likert_desde_orden(orden, info.dudosa.get("excluidos", []), c.valores)
                info.tipo = "likert"
                info.rango = (1.0, float(len(orden)))
                info.fuera = set(info.likert.fuera)
            if info.likert and decisiones.get(f"invertido:{c.id}") == "invertido":
                info.likert.invertido = True

        # Filas: duplicadas (se conserva la primera aparición).
        quitar_dup = set(estado.duplicadas) if decisiones.get("duplicados", "eliminar") == "eliminar" else set()
        quitar_lr = set(estado.linea_recta) if decisiones.get("linea-recta", "conservar") == "eliminar" else set()
        quitar_inc = set(estado.incompletos) if decisiones.get("incompletos", "eliminar") == "eliminar" else set()
        quitar_filas = quitar_dup | quitar_lr | quitar_inc
        filas_idx = [i for i in range(estado.tabla.n_filas) if i not in quitar_filas]

        conservadas = [c for c in estado.tabla.columnas if c.id not in eliminadas]
        if not conservadas:
            raise ErrorLimpieza("Con las decisiones tomadas no queda ninguna columna. Conserva al menos una.")

        anulados = 0
        convertidos = 0
        # «No sé / No aplica»: conservarlas marcadas (texto original) o dejarlas vacías.
        marcar_no_resp = decisiones.get("no-respuestas", "conservar_marcadas") == "conservar_marcadas"
        no_resp_conservadas = 0
        no_resp_vaciadas = 0
        columnas_finales: list[tuple[str, list[str | None]]] = []
        sin_codificar: dict[str, list[str | None]] = {}  # para la estadística (etiquetas originales)
        for c in conservadas:
            info = estado.tipos[c.id]
            anular = decisiones.get(f"rango:{c.id}", "anular") == "anular" and info.fuera
            valores: list[str | None] = []
            originales: list[str | None] = []
            for i in filas_idx:
                v = c.valores[i]
                if v is not None and anular and i in info.fuera:
                    v = None
                    anulados += 1
                originales.append(v)
                if v is not None and info.likert and info.likert.escala != "numerica":
                    n = normalizar_texto(v)
                    if n in excluir:
                        # No es punto de la escala: queda marcada con su texto original
                        # (distinta de una celda vacía) o vacía, según decidió el investigador.
                        if marcar_no_resp:
                            no_resp_conservadas += 1
                        else:
                            v = None
                            no_resp_vaciadas += 1
                    elif n in info.likert.codigos:
                        v = str(info.likert.codigos[n])
                        convertidos += 1
                valores.append(v)
            columnas_finales.append((c.id, valores))
            sin_codificar[c.id] = originales

        transformaciones = []
        if eliminadas:
            transformaciones.append(
                {"regla": "columnas_eliminadas", "detalle": ", ".join(c.etiqueta for c in estado.tabla.columnas if c.id in eliminadas), "afectados": len(eliminadas)}
            )
        if quitar_dup:
            transformaciones.append({"regla": "duplicados_eliminados", "detalle": "Filas duplicadas eliminadas (se conservó la primera).", "afectados": len(quitar_dup)})
        if quitar_lr:
            transformaciones.append({"regla": "linea_recta_eliminados", "detalle": "Encuestados que respondieron en línea recta eliminados.", "afectados": len(quitar_lr)})
        if quitar_inc:
            transformaciones.append({"regla": "incompletos_eliminados", "detalle": "Encuestados con demasiadas preguntas sin responder eliminados.", "afectados": len(quitar_inc)})
        if anulados:
            transformaciones.append({"regla": "fuera_de_rango_anulados", "detalle": "Valores fuera de rango dejados vacíos.", "afectados": anulados})
        if no_resp_conservadas:
            transformaciones.append({"regla": "no_respuestas_conservadas", "detalle": "Respuestas «No sé / No aplica» conservadas con su texto (no son puntos de la escala).", "afectados": no_resp_conservadas})
        if no_resp_vaciadas:
            transformaciones.append({"regla": "no_respuestas_vaciadas", "detalle": "Respuestas «No sé / No aplica» dejadas como celdas vacías.", "afectados": no_resp_vaciadas})
        if convertidos:
            transformaciones.append({"regla": "likert_a_numeros", "detalle": "Respuestas Likert en texto convertidas a números (ver libro de códigos).", "afectados": convertidos})

        # Métricas después: duplicados e imposibles que quedan tras aplicar las decisiones.
        restantes_dup = len(estado.duplicadas) - len(quitar_dup)
        restantes_imp = sum(
            0 if decisiones.get(f"rango:{c.id}", "anular") == "anular" else len(estado.tipos[c.id].fuera) for c in conservadas
        )
        etiquetas = {c.id: c.etiqueta for c in conservadas}
        metricas = _metricas(
            [(etiquetas[cid], vals) for cid, vals in columnas_finales],
            restantes_dup,
            restantes_imp,
            _grupos([(c.etiqueta, estado.tipos[c.id]) for c in conservadas]),
            cfg["umbrales"],
        )
        lr_restantes, _ = _linea_recta(estado, conservadas, filas_idx)
        metricas["n_linea_recta"] = len(lr_restantes)
        metricas["n_incompletos"] = len(_incompletos(conservadas, filas_idx))

        estadistica = _estadistica(estado, conservadas, sin_codificar, roles)
        estadistica["encuestados"] = {"linea_recta": metricas["n_linea_recta"], "incompletos": metricas["n_incompletos"]}

        especifico = _especifico(estado, roles, eliminadas)
        especifico["filas_eliminadas"].update(
            {"duplicadas": len(quitar_dup), "linea_recta": len(quitar_lr - quitar_dup), "incompletas": len(quitar_inc - quitar_dup - quitar_lr)}
        )
        especifico["fiabilidad"] = estadistica["fiabilidad"]
        # Cómo quedaron en el CSV las respuestas «No sé / No aplica» de las escalas.
        especifico["no_respuestas"] = "marcadas" if marcar_no_resp else "vacias"

        encabezados = [cid for cid, _ in columnas_finales]
        filas = [[vals[k] or "" for _, vals in columnas_finales] for k in range(len(filas_idx))]
        preguntas = sum(1 for c in conservadas if roles.get(c.id) == "pregunta")
        return ResultadoFinal(
            encabezados=encabezados,
            filas=filas,
            metricas=metricas,
            especifico=especifico,
            transformaciones=transformaciones,
            cifras=[
                {"etiqueta": "Respondentes", "valor": len(filas)},
                {"etiqueta": "Preguntas", "valor": preguntas},
                {"etiqueta": "Columnas eliminadas", "valor": len(eliminadas) + len(estado.tabla.columnas_vacias)},
                {"etiqueta": "Encuestados removidos", "valor": len(quitar_filas)},
            ],
            vista={"forma": "tabla", "columnas": [etiquetas[cid] for cid in encabezados], "filas": filas[:_FILAS_VISTA]},
            estadistica=estadistica,
        )
