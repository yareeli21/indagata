"""Motor de limpieza de pruebas estandarizadas.

Indagata NO califica las pruebas: no recibe clave de respuestas ni marca respuestas como
correctas o incorrectas. Limpia y describe lo que contestó cada alumno.

TABULAR (respuestas de los alumnos), en el orden de la Tabla 5:
  1. Validación del archivo: formato admisible, delimitador (, o ;) y estructura
     (columnas = reactivos, filas = alumnos).
  2. Normalización a UTF-8.
  3. Validación estructural: reactivos detectados por sus valores (ver `tipos.py`); columnas
     que no son reactivos ni contexto → aviso; IDs duplicados → fase asistida; filas vacías → se eliminan.
     También: acentos rotos reparados, encabezado repetido a mitad del archivo descartado, filas corridas
     una columna (`motores/filas.py`) → fase asistida, columna de reactivo sin ninguna respuesta → fase
     asistida (conservarla con 100 % NR o eliminarla) e IDs escritos distinto («r0067», «R082») → fase asistida.
  4. Validación de respuestas: opciones válidas (por defecto A, B, C, D, NR), V/F, enteros, Sí/No. Antes se
     normaliza la forma (`tipos.normalizar_respuesta`): «B)», «(C)», «AA», letras de otro alfabeto y otras
     formas de «no respondió» («N/R», «Sin respuesta», «-»).
  5. Nulificación: varias respuestas, caracteres inválidos o ilegibles → nula; vacía → NR.
  6. Por respuesta: estado (valida / nula / NR) y motivo
     (duplicado / no_respondida / respuesta_multiple / caracter_invalido / ilegible).

Descripción de reactivos (antes y después de las decisiones): distribución de respuestas,
opción más elegida, opciones que nadie eligió, nulas y no respondidas, y media en los
reactivos numéricos.

Salida (formato largo, una fila por alumno y reactivo):
  id_alumno; pregunta; respuesta; estado; motivo[; contexto…]
  (las columnas de contexto del alumno —turno, semestre…— se conservan al final)

DOCUMENTO (el examen en texto): limpieza de texto de la Figura 1, sin hablantes;
salida n_bloque; texto (un párrafo por fila).
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from shared.parsing import DocumentParseError, RawTable, TabularParseError, read_document, read_tabular

from services import configuracion
from services.configuracion import normalizar_texto
from services.motores import codificacion
from services.motores import estadistica as estad
from services.motores import filas as estructura_filas
from services.motores import texto as limpieza_texto
from services.motores.base import Entrada, ErrorLimpieza, Hallazgo, ResultadoAutomatico, ResultadoFinal
from services.motores.encuestas.universales import identificador
from services.motores.pruebas import tipos as tp

_FILAS_VISTA = 12
_COLUMNAS_SALIDA = ["id_alumno", "pregunta", "respuesta", "estado", "motivo"]


def _cfg() -> dict[str, Any]:
    return configuracion.reglas()["pruebas"]


def _opciones() -> set[str]:
    """Letras válidas de opción múltiple (sin «NR»)."""
    return {o.upper() for o in _cfg().get("opciones_validas", [])} - {"NR"}


def _tokens_nr() -> set[str]:
    return {normalizar_texto(t) for t in _cfg().get("tokens_no_respondida", [])}


def _id_normalizado(alumno: str) -> str:
    """«r0067» y «R67» → «R67»: mayúsculas y sin ceros a la izquierda en la parte numérica."""
    return re.sub(r"(?<!\d)0+(?=\d)", "", alumno.strip().upper())


# ── 1. Validación del archivo ──────────────────────────────────────────────────


def _leer_tabla(contenido: bytes, extension: str) -> RawTable:
    if extension not in (".csv", ".xlsx", ".xls"):
        raise ErrorLimpieza(f"La hoja de respuestas debe ser un archivo .csv, .xlsx o .xls (recibido: {extension or 'sin extensión'}).")
    try:
        tabla = read_tabular(contenido, extension)
    except TabularParseError as exc:
        raise ErrorLimpieza(f"No se pudo leer la hoja de respuestas: {exc}") from exc
    if extension == ".csv" and len(tabla.headers) < 2:
        raise ErrorLimpieza("La hoja de respuestas no usa un delimitador reconocido: separa las columnas con coma (,) o punto y coma (;).")
    if not tabla.rows:
        raise ErrorLimpieza("La hoja de respuestas no tiene filas de datos.")
    return tabla


# ── 3. Validación estructural ──────────────────────────────────────────────────


@dataclass
class Estructura:
    id_col: int
    preguntas: list[tuple[str, int]]  # (reactivo, columna)
    extras: list[str]  # columnas que no son reactivos ni contexto: no se incluyen
    filas: list[tuple[int, str, list[str]]]  # (fila original 1-indexada, id_alumno, celdas)
    filas_vacias: int
    sin_id: int
    duplicados: dict[str, list[int]] = field(default_factory=dict)  # id → filas (1-indexadas)
    encoding: str | None = None
    # Columnas de contexto del alumno (turno, semestre…): (id en el CSV limpio, encabezado, columna).
    contexto: list[tuple[str, str, int]] = field(default_factory=list)
    # Tipo de cada reactivo: {reactivo: (opcion_multiple | verdadero_falso | puntos | escala | si_no | numerica, máximo)}.
    tipos: dict[str, tuple[str, int | None]] = field(default_factory=dict)
    # Estructura de las filas (encabezado repetido, filas corridas o con celdas de más) y acentos reparados.
    revision: estructura_filas.RevisionFilas = field(default_factory=estructura_filas.RevisionFilas)
    acentos: int = 0
    # Reactivos sin ninguna respuesta (la columna existe pero nadie la contestó): {reactivo: columna}.
    vacios: dict[str, int] = field(default_factory=dict)
    vacios_conservados: list[str] = field(default_factory=list)
    # IDs que solo difieren en mayúsculas o ceros («r0067», «R0067»): {id normalizado: [(fila, id tal cual)]}.
    parecidos: dict[str, list[tuple[int, str]]] = field(default_factory=dict)
    encabezados: list[str] = field(default_factory=list)
    reparadas: list[int] = field(default_factory=list)  # filas corridas devueltas a su lugar (número de fila)
    eliminadas_estructura: list[int] = field(default_factory=list)


def _estructura(entrada: Entrada, decisiones: dict[str, str] | None = None) -> Estructura:
    decisiones = decisiones or {}
    tabla = _leer_tabla(entrada.contenido, entrada.extension)
    encabezados = [h.strip() for h in tabla.headers]
    opciones = _opciones()

    patrones = [re.compile(p, re.I) for p in _cfg().get("columna_id", [])]
    # Sin un encabezado reconocible, la primera columna identifica al alumno.
    id_col = next((i for i, h in enumerate(encabezados) if any(p.match(normalizar_texto(h)) for p in patrones)), 0)

    # Acentos rotos, encabezado repetido y filas corridas, antes de detectar los reactivos.
    reparadas_celdas, casos_acentos = codificacion.reparar_filas([[c.strip() for c in f] for f in tabla.rows])
    revision = estructura_filas.revisar(encabezados, reparadas_celdas, tabla.irregulares, buscar_resumen=False, buscar_segunda=False)
    quitar = set(revision.repetidas)
    reparadas, eliminadas = [], []
    for fc in revision.corridas:
        decision = decisiones.get(f"fila-corrida:{fc.fila + 2}", "reparar")
        if decision == "reparar":
            reparadas_celdas[fc.fila] = fc.reparada
            reparadas.append(fc.fila + 2)
        elif decision == "eliminar":
            quitar.add(fc.fila)
            eliminadas.append(fc.fila + 2)
    for i, _ in revision.largas:
        if decisiones.get(f"fila-larga:{i + 2}", "recortar") == "eliminar":
            quitar.add(i)
            eliminadas.append(i + 2)

    filas_crudas = [f for i, f in enumerate(reparadas_celdas) if i not in quitar and any(f)]
    excluidas = {id_col} | {i for i, h in enumerate(encabezados) if configuracion.es_contexto(h)}
    detectados, puntaje_col = tp.detectar(encabezados, filas_crudas, excluidas, opciones, set(_cfg().get("caracteres_ilegibles", [])),
                                          _tokens_nr())
    if not detectados:
        raise ErrorLimpieza(
            "No se encontraron columnas de reactivos en la hoja de respuestas: se esperan letras (A–D), "
            "V/F o, en columnas con nombre de reactivo (P1, item_2…), números o Sí/No."
        )
    preguntas = [(d.nombre, d.columna) for d in detectados]
    tipos = {d.nombre: (d.tipo, d.puntos_max) for d in detectados}
    # Reactivos sin ninguna respuesta: con nombre de reactivo y todas sus celdas vacías (o «N/R», «-»…). Antes
    # desaparecían con un aviso genérico de «columna que no parece reactivo».
    tokens = _tokens_nr()
    vacios = {
        encabezados[j]: j for j in range(len(encabezados))
        if j not in excluidas and j not in {c for _, c in preguntas} and encabezados[j] and tp.parece_reactivo(encabezados[j])
        and all(not tp.normalizar_respuesta(f[j] if j < len(f) else "", opciones, tokens)[0].strip() for f in filas_crudas)
    }
    conservados = [h for h in vacios if decisiones.get(f"reactivo-vacio:{h}", "conservar") == "conservar"]
    if conservados:
        tipo_comun = Counter(t for t, _ in tipos.values()).most_common(1)[0][0]
        preguntas = sorted(preguntas + [(h, vacios[h]) for h in conservados], key=lambda x: x[1])
        tipos = {p: tipos.get(p, (tipo_comun, None)) for p, _ in preguntas}
    usadas = {id_col} | {c for _, c in preguntas} | set(vacios.values())
    # Las columnas de contexto se conservan al final del CSV largo (para consultas como
    # «¿qué eligió el turno vespertino en P3?»); el resto de columnas extra no.
    ids = set(_COLUMNAS_SALIDA)
    contexto = [
        (identificador(encabezados[i], ids), encabezados[i], i)
        for i in range(len(encabezados))
        # El puntaje global (score_estimado…) también es un dato del alumno, no un reactivo.
        if i not in usadas and encabezados[i] and (configuracion.es_contexto(encabezados[i]) or i == puntaje_col)
    ]
    usadas |= {i for _, _, i in contexto}
    extras = [encabezados[i] or f"Columna {i + 1}" for i in range(len(encabezados)) if i not in usadas]

    filas: list[tuple[int, str, list[str]]] = []
    vacias = 0
    sin_id = 0
    for n, celdas in enumerate(reparadas_celdas, start=2):  # fila 1 = encabezados
        if n - 2 in quitar:
            continue
        if not any(celdas):
            vacias += 1
            continue
        alumno = celdas[id_col] if id_col < len(celdas) else ""
        if not alumno:
            sin_id += 1
            alumno = f"sin_id_fila_{n}"
        filas.append((n, alumno, celdas))
    if not filas:
        raise ErrorLimpieza("La hoja de respuestas no tiene alumnos (todas las filas están vacías).")
    por_id: dict[str, list[int]] = {}
    for n, alumno, _ in filas:
        por_id.setdefault(alumno, []).append(n)
    duplicados = {a: ns for a, ns in por_id.items() if len(ns) > 1}
    grupos: dict[str, list[tuple[int, str]]] = {}
    for n, alumno, _ in filas:
        if not alumno.startswith("sin_id_fila_"):
            grupos.setdefault(_id_normalizado(alumno), []).append((n, alumno))
    parecidos = {k: v for k, v in grupos.items() if len({a for _, a in v}) > 1}
    return Estructura(id_col, preguntas, extras, filas, vacias, sin_id, duplicados, tabla.encoding, contexto, tipos,
                      revision, len(casos_acentos), vacios, conservados, parecidos, encabezados, reparadas, eliminadas)


# ── 4–6. Respuestas ────────────────────────────────────────────────────────────


def clasificar(
    valor: str,
    validas: set[str],
    ilegibles: set[str],
    tipo: str = tp.OPCION_MULTIPLE,
    puntos_max: int | None = None,
) -> tuple[str, str]:
    """(estado, motivo) de una respuesta. No se juzga si es correcta: solo si es una respuesta válida."""
    texto = valor.strip().upper()
    if not texto or texto == "NR":
        return "NR", "no_respondida"
    if any(c in texto for c in ilegibles):
        return "nula", "ilegible"
    if tipo == tp.VERDADERO_FALSO:
        ok = tp.normalizar_vf(texto) is not None
    elif tipo == tp.PUNTOS:
        ok = texto.isdigit() and puntos_max is not None and int(texto) <= puntos_max
    elif tipo == tp.ESCALA:
        ok = texto.isdigit() and puntos_max is not None and 1 <= int(texto) <= puntos_max
    elif tipo == tp.SI_NO:
        ok = tp.normalizar_si_no(texto) is not None
    elif tipo == tp.NUMERICA:
        ok = tp.es_numero(texto)
    else:
        letras = [c for c in re.split(r"[\s,;/|+-]+", texto) if c]
        # «AB» o «A,B»: varias opciones marcadas.
        if len(letras) == 1 and len(letras[0]) > 1 and all(ch in validas for ch in letras[0]):
            letras = list(letras[0])
        if len(letras) > 1 and all(l in validas for l in letras):
            return "nula", "respuesta_multiple"
        ok = texto in validas
    return ("valida", "") if ok else ("nula", "caracter_invalido")


def _elegida(valor: str, tipo: str) -> str:
    """Forma en que se cuenta una respuesta válida en la distribución."""
    if tipo == tp.VERDADERO_FALSO:
        return tp.normalizar_vf(valor) or valor.strip().upper()
    if tipo == tp.SI_NO:
        return tp.normalizar_si_no(valor) or valor.strip()
    return valor.strip().upper()


def _sugerencia_parecido(est: Estructura, filas_grupo: list[tuple[int, str]]) -> str:
    """Si todas las filas del grupo traen las mismas respuestas, es el mismo alumno capturado dos veces."""
    por_fila = {n: celdas for n, _, celdas in est.filas}
    respuestas = {tuple(por_fila[n][c] if c < len(por_fila[n]) else "" for _, c in est.preguntas) for n, _ in filas_grupo}
    return "conservar_primero" if len(respuestas) == 1 else "conservar_todos"


def _evaluar(est: Estructura, decisiones: dict[str, str]) -> tuple[list[list[str]], dict[str, Any]]:
    cfg = _cfg()
    validas = _opciones()
    ilegibles = set(cfg.get("caracteres_ilegibles", []))
    tokens = _tokens_nr()
    filas_salida: list[list[str]] = []
    vistos: Counter = Counter()
    eliminadas = 0
    elegidas: list[Counter] = [Counter() for _ in est.preguntas]
    normalizadas: Counter = Counter()
    casos_normalizadas: list[dict] = []
    # IDs escritos distinto: la primera forma que aparece es la que se conserva.
    primero_de = {k: grupo[0][1] for k, grupo in est.parecidos.items()}
    decision_parecido = {k: decisiones.get(f"id-parecido:{k}") or _sugerencia_parecido(est, grupo) for k, grupo in est.parecidos.items()}
    for n, alumno, celdas in est.filas:
        vistos[alumno] += 1
        repetida = alumno in est.duplicados and vistos[alumno] > 1
        decision = decisiones.get(f"id-duplicado:{alumno}", "conservar_primero")
        if alumno in est.duplicados and decision == "eliminar_todos":
            eliminadas += 1
            continue
        clave = _id_normalizado(alumno)
        otra_forma = clave in est.parecidos and alumno != primero_de[clave]
        if clave in est.parecidos and decision_parecido[clave] == "eliminar_todos":
            eliminadas += 1
            continue
        anulado = (repetida and decision == "conservar_primero") or (otra_forma and decision_parecido[clave] == "conservar_primero")
        if otra_forma and decision_parecido[clave] == "conservar_primero":
            alumno = primero_de[clave]  # es el mismo alumno: sus respuestas quedan nulas («duplicado») bajo un solo ID
        valores_contexto = [celdas[c] if c < len(celdas) else "" for _, _, c in est.contexto]
        for j, (pregunta, col) in enumerate(est.preguntas):
            valor = celdas[col] if col < len(celdas) else ""
            nuevo, regla = tp.normalizar_respuesta(valor, validas, tokens)
            if regla:
                normalizadas[regla] += 1
                if len(casos_normalizadas) < 300:
                    casos_normalizadas.append({"fila": n, "columna": pregunta, "antes": valor, "despues": nuevo})
                valor = nuevo
            if anulado:
                estado, motivo = "nula", "duplicado"
            else:
                tipo, puntos_max = est.tipos.get(pregunta, (tp.OPCION_MULTIPLE, None))
                estado, motivo = clasificar(valor, validas, ilegibles, tipo, puntos_max)
                elegidas[j][_elegida(valor, tipo) if estado == "valida" else estado] += 1
            filas_salida.append([alumno, pregunta, valor, estado, motivo, *valores_contexto])
    estados = Counter(f[3] for f in filas_salida)
    motivos = Counter(f[4] for f in filas_salida if f[4])
    alumnos = {f[0] for f in filas_salida}
    resumen = {
        "n_alumnos": len(alumnos),
        "n_preguntas": len(est.preguntas),
        "n_respuestas": len(filas_salida),
        "conteos": {"valida": estados.get("valida", 0), "nula": estados.get("nula", 0), "NR": estados.get("NR", 0)},
        "motivos": {m: motivos.get(m, 0) for m in ("duplicado", "no_respondida", "respuesta_multiple", "caracter_invalido", "ilegible")},
        "pct_validas": round(estados.get("valida", 0) / len(filas_salida), 4) if filas_salida else 0.0,
        "filas_eliminadas_por_duplicado": eliminadas,
        "estadistica": _estadistica(est, elegidas, sorted(validas)),
        "normalizadas": dict(normalizadas),
        "casos_normalizadas": casos_normalizadas,
    }
    return filas_salida, resumen


def _opciones_de(tipo: str, puntos_max: int | None, letras: list[str]) -> list[str]:
    """Opciones posibles de un reactivo, en orden (vacío si la respuesta es un número libre)."""
    if tipo == tp.VERDADERO_FALSO:
        return ["V", "F"]
    if tipo == tp.PUNTOS:
        return [str(i) for i in range(0, (puntos_max or 0) + 1)]
    if tipo == tp.ESCALA:
        return [str(i) for i in range(1, (puntos_max or 0) + 1)]
    if tipo == tp.SI_NO:
        return ["Sí", "No"]
    if tipo == tp.NUMERICA:
        return []
    return letras


def _estadistica(est: Estructura, elegidas: list[Counter], letras: list[str]) -> dict[str, Any]:
    """Descripción de cada reactivo: qué contestaron los alumnos (sin calificar)."""
    cfg = _cfg()
    umbral_sin = float(cfg.get("umbral_sin_respuesta", 0.2))
    umbral_unanime = float(cfg.get("umbral_casi_unanime", 0.9))
    reactivos = []
    for j, (pregunta, _) in enumerate(est.preguntas):
        conteo = elegidas[j]
        total = sum(conteo.values())
        tipo, puntos_max = est.tipos.get(pregunta, (tp.OPCION_MULTIPLE, None))
        opciones_item = _opciones_de(tipo, puntos_max, letras)
        respondidas = {o: c for o, c in conteo.items() if o not in ("nula", "NR")}
        n_validas = sum(respondidas.values())
        orden = opciones_item or sorted(respondidas, key=lambda o: (-respondidas[o], o))[:15]
        distribucion = [
            {"opcion": o, "n": conteo.get(o, 0), "pct": round(conteo.get(o, 0) / total, 4) if total else 0.0}
            for o in [*orden, "nula", "NR"]
        ]
        mas = max(respondidas.items(), key=lambda x: (x[1], -orden.index(x[0]) if x[0] in orden else 0), default=None)
        mas_elegida = (
            {"opcion": mas[0], "n": mas[1], "pct": round(mas[1] / total, 4) if total else 0.0,
             "pct_validas": round(mas[1] / n_validas, 4) if n_validas else 0.0}
            if mas else None
        )
        sin_respuesta = conteo.get("nula", 0) + conteo.get("NR", 0)
        item: dict[str, Any] = {
            "pregunta": pregunta,
            "tipo_reactivo": tipo,
            "n": total,
            "distribucion": distribucion,
            "opcion_mas_elegida": mas_elegida,
            # Opciones que nadie eligió (solo con opciones cerradas: letras y V/F).
            "opciones_sin_elegir": [o for o in opciones_item if conteo.get(o, 0) == 0] if tipo in (tp.OPCION_MULTIPLE, tp.VERDADERO_FALSO) else [],
            "n_nulas": conteo.get("nula", 0),
            "n_no_respondidas": conteo.get("NR", 0),
            "pct_sin_respuesta": round(sin_respuesta / total, 4) if total else 0.0,
            "mucha_no_respuesta": bool(total) and sin_respuesta / total > umbral_sin,
            "casi_unanime": bool(mas_elegida) and n_validas >= 3 and mas_elegida["pct_validas"] >= umbral_unanime,
        }
        if puntos_max is not None:
            item["puntos_max"] = puntos_max
        if tipo in tp.NUMERICOS:
            numeros = [float(o.replace(",", ".")) for o, c in respondidas.items() for _ in range(c) if tp.es_numero(o)]
            item["descriptivos"] = estad.descriptivos(numeros)
        reactivos.append(item)
    total_resp = sum(r["n"] for r in reactivos)
    sin_resp = sum(r["n_nulas"] + r["n_no_respondidas"] for r in reactivos)
    return {
        "reactivos": reactivos,
        "respuestas": {
            "n_alumnos": len({a for _, a, _ in est.filas}),
            "n_reactivos": len(reactivos),
            "pct_sin_respuesta": round(sin_resp / total_resp, 4) if total_resp else 0.0,
        },
        "resumen_reactivos": {
            "con_opciones_sin_elegir": sum(1 for r in reactivos if r["opciones_sin_elegir"]),
            "mucha_no_respuesta": sum(1 for r in reactivos if r["mucha_no_respuesta"]),
            "casi_unanimes": sum(1 for r in reactivos if r["casi_unanime"]),
        },
        "umbrales": {"sin_respuesta": umbral_sin, "casi_unanime": umbral_unanime},
    }


# ── Motores ────────────────────────────────────────────────────────────────────


class MotorPruebasTabular:
    """Limpieza de pruebas estandarizadas en tabla (hoja de respuestas de los alumnos)."""

    nombre = "pruebas_tabular"

    def automatica(self, entrada: Entrada) -> ResultadoAutomatico:
        est = _estructura(entrada)  # con las opciones sugeridas: fila corrida reparada, reactivo vacío conservado
        cfg = _cfg()
        _, resumen = _evaluar(est, {})
        transformaciones = [
            {"regla": "validacion_archivo", "detalle": "Formato, delimitador y estructura (reactivos en columnas, alumnos en filas) válidos.", "afectados": None},
            {"regla": "codificacion_utf8", "detalle": f"Texto convertido a UTF-8 (origen: {est.encoding or 'Excel'}).", "afectados": None},
        ]
        if est.acentos:
            transformaciones.append({"regla": "acentos_reparados", "detalle": "Acentos rotos al copiar entre programas, reparados («SÃ­» → «Sí»).", "afectados": est.acentos})
        if est.revision.repetidas:
            transformaciones.append({"regla": "encabezado_repetido", "detalle": "Filas iguales al encabezado (dos exportaciones pegadas) descartadas: filas "
                                     + ", ".join(str(i + 2) for i in est.revision.repetidas[:10]) + ".", "afectados": len(est.revision.repetidas)})
        if est.revision.cortas:
            transformaciones.append({"regla": "filas_completadas", "detalle": "Filas con menos celdas que el encabezado, completadas con celdas vacías al final.",
                                     "afectados": len(est.revision.cortas)})
        if est.filas_vacias:
            transformaciones.append({"regla": "filas_vacias", "detalle": "Filas vacías eliminadas.", "afectados": est.filas_vacias})
        if resumen["normalizadas"]:
            detalle = {
                "letra_con_signos": "letra con signos («B)», «(C)», «c.»)",
                "letra_parecida": "letra de otro alfabeto que se ve igual («А» cirílica, «Ｃ»)",
                "misma_letra_repetida": "la misma letra dos veces («AA»)",
                "no_respondida_escrita": "otras formas de «no respondió» («N/R», «Sin respuesta», «-»)",
            }
            partes = [f"{detalle[r]}: {n}" for r, n in resumen["normalizadas"].items()]
            transformaciones.append({"regla": "respuestas_normalizadas", "detalle": "Respuestas escritas de otra forma, normalizadas: " + "; ".join(partes) + ".",
                                     "afectados": sum(resumen["normalizadas"].values()), "casos": resumen["casos_normalizadas"]})
        transformaciones.append({"regla": "respuestas_validadas", "detalle": f"Respuestas comparadas con las opciones válidas ({', '.join(cfg.get('opciones_validas', []))}).", "afectados": resumen["n_respuestas"]})
        # Las nulas por ID duplicado dependen de la decisión del investigador: no son automáticas.
        nulas = resumen["conteos"]["nula"] - resumen["motivos"]["duplicado"]
        if nulas:
            transformaciones.append({"regla": "respuestas_nulificadas", "detalle": "Respuestas múltiples, ilegibles o con caracteres inválidos marcadas como nulas.", "afectados": nulas})
        if resumen["conteos"]["NR"]:
            transformaciones.append({"regla": "no_respondidas", "detalle": "Respuestas vacías marcadas como NR (no respondida).", "afectados": resumen["conteos"]["NR"]})

        avisos = []
        if est.contexto:
            avisos.append(f"Se conservan como datos de contexto del alumno: {', '.join(e for _, e, _ in est.contexto)}.")
        if est.extras:
            avisos.append(f"La hoja de respuestas tiene {len(est.extras)} columna(s) que no parecen reactivos ni datos de contexto y no se incluirán: {', '.join(est.extras[:6])}.")
        if est.sin_id:
            avisos.append(f"{est.sin_id} fila(s) no tienen identificador de alumno; se les asignó uno con su número de fila.")

        hallazgos = [
            Hallazgo(
                id=f"id-duplicado:{alumno}", tipo="id_duplicado", tema="Identificadores repetidos", objetivo=alumno,
                titulo=f"El alumno «{alumno}» aparece {len(filas)} veces",
                descripcion="Te sugerimos conservar la primera aparición y marcar las demás como nulas (motivo «duplicado»).",
                opciones=["conservar_primero", "conservar_todos", "eliminar_todos"], sugerida="conservar_primero",
                detalle={"filas": filas},
            )
            for alumno, filas in est.duplicados.items()
        ]
        hallazgos = [*self._hallazgos_estructura(est), *hallazgos, *self._hallazgos_parecidos(est)]
        metricas = {
            "n_alumnos": len({a for _, a, _ in est.filas}),
            "n_filas": len(est.filas) + est.filas_vacias,
            "n_preguntas": len(est.preguntas),
            "n_filas_vacias": est.filas_vacias,
            "n_ids_duplicados": len(est.duplicados),
            "columnas_extra": est.extras,
            "conteos": resumen["conteos"],
            "motivos": resumen["motivos"],
            "pct_validas": resumen["pct_validas"],
        }
        especifico = {
            "opciones_validas": cfg.get("opciones_validas", []),
            "ilegibles": cfg.get("caracteres_ilegibles", []),
            "ids_duplicados": list(est.duplicados),
            "columnas_extra": est.extras,
            "columnas_contexto": [{"id": i, "etiqueta": e} for i, e, _ in est.contexto],
            "tipos_reactivo": {p: t for p, (t, _) in est.tipos.items()},
            # El orden de la hoja de respuestas, como LISTA: el reporte se guarda en JSONB, que reordena las
            # llaves de los diccionarios, y knowledge-service empareja los reactivos con el original por posición.
            "orden_reactivos": list(est.tipos),
            "puntos_max": {p: m for p, (t, m) in est.tipos.items() if t in (tp.PUNTOS, tp.ESCALA)},
        }
        return ResultadoAutomatico(hallazgos, transformaciones, metricas, especifico, avisos, resumen["estadistica"])

    @staticmethod
    def _hallazgos_estructura(est: Estructura) -> list[Hallazgo]:
        """Filas corridas o con celdas de más, y reactivos sin ninguna respuesta."""
        salida: list[Hallazgo] = []
        nombre = lambda j: (est.encabezados[j] if j < len(est.encabezados) else "") or f"Columna {j + 1}"  # noqa: E731
        for fc in est.revision.corridas:
            n, k = fc.fila + 2, fc.columna
            if fc.tipo == "falta":
                titulo = f"La fila {n} está corrida una columna: falta el dato de «{nombre(k)}»"
                explicacion = (f"Desde «{nombre(k)}», cada valor quedó una columna a la izquierda (por ejemplo, «{fc.celdas[k]}» "
                               f"quedó en «{nombre(k)}» y corresponde a «{nombre(k + 1)}»), así que las respuestas quedaron en el "
                               f"reactivo equivocado. Si la reparas, «{nombre(k)}» queda vacía y los demás valores vuelven a su columna.")
            else:
                titulo = f"La fila {n} está corrida una columna: sobra una celda en «{nombre(k)}»"
                explicacion = (f"Hay una celda de más en «{nombre(k)}» («{fc.celdas[k]}»): desde ahí, cada valor quedó una columna "
                               "a la derecha. Si la reparas, se quita esa celda y los demás valores vuelven a su columna.")
            ubicacion = [{"fila": n, "columna": nombre(j), "antes": fc.celdas[j] if j < len(fc.celdas) else "", "despues": fc.reparada[j]}
                         for j in range(max(0, k - 1), min(len(est.encabezados), k + 6))]
            salida.append(Hallazgo(
                id=f"fila-corrida:{n}", tipo="fila_corrida", tema="Estructura del archivo", objetivo=str(n), titulo=titulo,
                descripcion=f"{explicacion} Tal como viene, {fc.fallas_antes} valores no corresponden a su columna; reparada, {fc.fallas_despues}.",
                opciones=["reparar", "eliminar", "conservar"], sugerida="reparar",
                detalle={"filas": [n], "total": len(ubicacion), "ubicacion": ubicacion},
            ))
        for i, celdas in est.revision.largas:
            extra = [c for c in celdas[len(est.encabezados):] if c.strip()]
            salida.append(Hallazgo(
                id=f"fila-larga:{i + 2}", tipo="fila_larga", tema="Estructura del archivo", objetivo=str(i + 2),
                titulo=f"La fila {i + 2} tiene {len(celdas) - len(est.encabezados)} celda(s) más que el encabezado",
                descripcion=(f"No encontramos en qué columna sobra. Si la recortas, se conservan sus primeras {len(est.encabezados)} "
                             f"celdas y se pierden las de más («{' · '.join(extra[:3])}»); también puedes eliminar la fila."),
                opciones=["recortar", "eliminar"], sugerida="recortar", detalle={"filas": [i + 2], "total": 1},
            ))
        for reactivo in est.vacios:
            salida.append(Hallazgo(
                id=f"reactivo-vacio:{reactivo}", tipo="reactivo_vacio", tema="Reactivos", objetivo=reactivo,
                titulo=f"Nadie respondió el reactivo «{reactivo}»",
                descripcion=("La columna existe, pero todas sus celdas están vacías (quizá no se aplicó). Te sugerimos conservarlo "
                             "con 100 % de no respondidas, para que el reporte muestre que el reactivo existe; si no pertenece a la "
                             "prueba, elimínalo."),
                opciones=["conservar", "eliminar"], sugerida="conservar", detalle={"columna": reactivo},
            ))
        return salida

    @staticmethod
    def _hallazgos_parecidos(est: Estructura) -> list[Hallazgo]:
        """IDs que solo difieren en mayúsculas o ceros a la izquierda."""
        salida: list[Hallazgo] = []
        for clave, grupo in est.parecidos.items():
            formas = list(dict.fromkeys(a for _, a in grupo))
            sugerida = _sugerencia_parecido(est, grupo)
            iguales = sugerida == "conservar_primero"
            salida.append(Hallazgo(
                id=f"id-parecido:{clave}", tipo="id_parecido", tema="Identificadores repetidos", objetivo=clave,
                titulo=f"Los alumnos {' y '.join(f'«{f}»' for f in formas)} podrían ser el mismo",
                descripcion=(
                    "Sus identificadores solo cambian en mayúsculas o en ceros a la izquierda"
                    + (" y tienen exactamente las mismas respuestas: parece el mismo alumno capturado dos veces. Te sugerimos "
                       f"conservar «{formas[0]}» y marcar las demás como nulas (motivo «duplicado»)." if iguales else
                       ", pero sus respuestas son distintas: pueden ser alumnos diferentes. Te sugerimos conservarlos todos.")
                ),
                opciones=["conservar_primero", "conservar_todos", "eliminar_todos"], sugerida=sugerida,
                detalle={"filas": [n for n, _ in grupo], "ejemplos": formas},
            ))
        return salida

    def aplicar(self, entrada: Entrada, automatico: ResultadoAutomatico, decisiones: dict[str, str]) -> ResultadoFinal:
        est = _estructura(entrada, decisiones)
        filas, resumen = _evaluar(est, decisiones)
        transformaciones = []
        if est.reparadas:
            transformaciones.append({"regla": "filas_corridas_reparadas", "detalle": "Filas corridas una columna, devueltas a su lugar: "
                                     + ", ".join(map(str, est.reparadas)) + ".", "afectados": len(est.reparadas)})
        if est.eliminadas_estructura:
            transformaciones.append({"regla": "filas_irregulares_eliminadas", "detalle": "Filas corridas o con celdas de más, eliminadas.",
                                     "afectados": len(est.eliminadas_estructura)})
        if est.vacios_conservados:
            transformaciones.append({"regla": "reactivos_vacios_conservados", "detalle": "Reactivos sin respuestas conservados (100 % no respondidas): "
                                     + ", ".join(est.vacios_conservados) + ".", "afectados": len(est.vacios_conservados)})
        if resumen["motivos"]["duplicado"]:
            transformaciones.append({"regla": "duplicados_nulificados", "detalle": "Respuestas de alumnos repetidos marcadas como nulas (motivo «duplicado»).", "afectados": resumen["motivos"]["duplicado"]})
        if resumen["filas_eliminadas_por_duplicado"]:
            transformaciones.append({"regla": "duplicados_eliminados", "detalle": "Registros de alumnos repetidos eliminados.", "afectados": resumen["filas_eliminadas_por_duplicado"]})
        especifico = dict(automatico.especifico)
        especifico.update({k: resumen[k] for k in ("n_alumnos", "n_preguntas", "conteos", "motivos", "pct_validas")})
        metricas = {
            "n_alumnos": resumen["n_alumnos"],
            "n_preguntas": resumen["n_preguntas"],
            "n_respuestas": resumen["n_respuestas"],
            "n_ids_duplicados": sum(1 for a in est.duplicados if decisiones.get(f"id-duplicado:{a}") == "conservar_todos"),
            "conteos": resumen["conteos"],
            "motivos": resumen["motivos"],
            "pct_validas": resumen["pct_validas"],
        }
        return ResultadoFinal(
            encabezados=_COLUMNAS_SALIDA + [i for i, _, _ in est.contexto],
            filas=filas,
            metricas=metricas,
            especifico=especifico,
            transformaciones=transformaciones,
            cifras=[
                {"etiqueta": "Alumnos", "valor": resumen["n_alumnos"]},
                {"etiqueta": "Reactivos", "valor": resumen["n_preguntas"]},
                {"etiqueta": "Respuestas nulas", "valor": resumen["conteos"]["nula"]},
                {"etiqueta": "No respondidas", "valor": resumen["conteos"]["NR"]},
            ],
            vista={
                "forma": "tabla",
                "columnas": ["Alumno", "Reactivo", "Respuesta", "Estado", "Motivo"],
                "filas": [[f[0], f[1], f[2] or "—", f[3], f[4].replace("_", " ")] for f in filas[:_FILAS_VISTA]],
            },
            estadistica=resumen["estadistica"],
        )


class MotorPruebasDocumento:
    """Limpieza de pruebas entregadas como documento (el examen en texto)."""

    nombre = "pruebas_documento"

    def _preparar(self, entrada: Entrada) -> limpieza_texto.ResultadoTexto:
        try:
            doc = read_document(entrada.contenido, entrada.extension)
        except DocumentParseError as exc:
            raise ErrorLimpieza(f"No se pudo leer la prueba: {exc}") from exc
        if not doc.text.strip():
            raise ErrorLimpieza("No se pudo extraer texto del archivo (si es un PDF escaneado, necesita OCR).")
        maximo = int(configuracion.reglas()["entrevistas"].get("max_iteraciones_ruido", 3))
        resultado = limpieza_texto.limpiar(doc.text, maximo)
        if not resultado.texto.strip():
            raise ErrorLimpieza("Después de quitar el ruido, la prueba quedó sin texto.")
        return resultado

    @staticmethod
    def _bloques(texto: str) -> list[str]:
        bloques = [" ".join(b.split()) for b in re.split(r"\n\s*\n", texto) if b.strip()]
        return bloques if len(bloques) > 1 else [l.strip() for l in texto.split("\n") if l.strip()]

    def automatica(self, entrada: Entrada) -> ResultadoAutomatico:
        resultado = self._preparar(entrada)
        hallazgos = []
        if resultado.residual:
            hallazgos.append(
                Hallazgo(
                    id="ruido-residual", tipo="ruido_residual", tema="Ruido", objetivo="texto",
                    titulo=f"{len(resultado.residual)} fragmento(s) de ruido sin resolver",
                    descripcion="Puedes eliminar esas líneas o conservarlas.",
                    opciones=["eliminar", "conservar"], sugerida="conservar",
                    detalle={"ejemplos": [r["texto"] for r in resultado.residual[:4]]},
                )
            )
        metricas = {"n_palabras": len(resultado.texto.split()), "ruido_detectado": len(resultado.residual) + sum(resultado.eliminado.values())}
        especifico = {"formato": "documento", "iteraciones_ruido": resultado.iteraciones, "ruido_eliminado": resultado.eliminado, "ruido_residual": resultado.residual}
        return ResultadoAutomatico(hallazgos, resultado.transformaciones, metricas, especifico, [])

    def aplicar(self, entrada: Entrada, automatico: ResultadoAutomatico, decisiones: dict[str, str]) -> ResultadoFinal:
        resultado = self._preparar(entrada)
        texto = resultado.texto
        if resultado.residual and decisiones.get("ruido-residual") == "eliminar":
            texto = limpieza_texto.quitar_lineas(texto, {r["linea"] for r in resultado.residual})
        bloques = self._bloques(texto)
        filas = [[str(i), b] for i, b in enumerate(bloques, start=1)]
        palabras = sum(len(b.split()) for b in bloques)
        ruido = sum(v for k, v in resultado.eliminado.items() if k != "palabras_reconstruidas")
        return ResultadoFinal(
            encabezados=["n_bloque", "texto"],
            filas=filas,
            metricas={"n_bloques": len(bloques), "n_palabras": palabras, "ruido_detectado": len(limpieza_texto.detectar_ruido(texto))},
            especifico={**automatico.especifico, "n_bloques": len(bloques)},
            transformaciones=[],
            cifras=[
                {"etiqueta": "Bloques de texto", "valor": len(bloques)},
                {"etiqueta": "Palabras", "valor": palabras},
                {"etiqueta": "Ruido eliminado", "valor": ruido},
            ],
            vista={"forma": "turnos", "columnas": ["#", "Texto"], "filas": [[f[0], f[1][:280] + ("…" if len(f[1]) > 280 else "")] for f in filas[:_FILAS_VISTA]]},
        )
