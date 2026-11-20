"""¿Quién calcula mejor las cifras: el modelo de lenguaje o el código? (Pruebas 6.7.3)

Las mismas 20 preguntas numéricas, con su cifra correcta calculada aparte (directo de `respuesta_interpretada`),
se responden de tres formas:

  A. Solo RAG     el modelo recibe los 8 fragmentos más parecidos de ChromaDB (mismo modelo de embeddings, colección
                  y filtro que el chat: sin chunks de personas) y calcula él la cifra.
  B. Con datos    el modelo recibe las respuestas de cada respondente a las preguntas necesarias y cuenta él. Solo
                  cuando caben en la ventana del modelo (8192 tokens); en la encuesta de 2000 no caben.
  C. Sistema      el chat completo (`/rag/chat`, sin caché): el modelo interpreta, el código calcula y el modelo redacta.

Una respuesta es correcta si contiene la cifra esperada: el conteo exacto, el porcentaje con un decimal (±0.1) o el
promedio (±0.05). Se ignoran los identificadores (p04, R017…) para no confundirlos con cifras.

Uso (con la app levantada):
    # A y B, dentro de visualization-service (tiene ChromaDB, el modelo de embeddings, la base y Ollama):
    MSYS_NO_PATHCONV=1 docker compose exec -T visualization-service python - modelo < tools/rag/aritmetica.py > evidencias/aritmetica_2026-11-09/modelo.json
    # C, desde el equipo, por el gateway:
    .venv\\Scripts\\python.exe tools\\rag\\aritmetica.py sistema evidencias\\aritmetica_2026-11-09
    # Solo algunas preguntas (segunda prueba, tras corregir la base del porcentaje):
    .venv\\Scripts\\python.exe tools\\rag\\aritmetica.py sistema evidencias\\aritmetica_2026-11-10 A01,A02,A15,A16,A20
    # Resumen y calificación:
    .venv\\Scripts\\python.exe tools\\rag\\aritmetica.py resumen evidencias\\aritmetica_2026-11-09
"""
from __future__ import annotations

import json
import re
import sys
import time
import unicodedata
from pathlib import Path

PREGUNTAS = [
    # enc_10_turno (59): 60 respondentes, turno y género como contexto
    {"id": "A01", "ins": 59, "tipo": "porcentaje", "grupo": {"turno": "Vespertino"}, "cond": [{"p": "p04", "nivel": "acuerdo"}],
     "texto": "¿Qué porcentaje del turno vespertino está de acuerdo con que las evaluaciones están relacionadas con lo que se ve en clase?"},
    {"id": "A02", "ins": 59, "tipo": "porcentaje", "grupo": {"turno": "Matutino"}, "cond": [{"p": "p04", "nivel": "acuerdo"}],
     "texto": "¿Qué porcentaje del turno matutino está de acuerdo con que las evaluaciones están relacionadas con lo que se ve en clase?"},
    {"id": "A03", "ins": 59, "tipo": "conteo", "cond": [{"p": "p02", "nivel": "desacuerdo"}],
     "texto": "¿Cuántos respondentes están en desacuerdo con que las calificaciones reflejan lo que realmente aprendieron?"},
    {"id": "A04", "ins": 59, "tipo": "porcentaje", "cond": [{"p": "p08", "nivel": "acuerdo"}],
     "texto": "¿Qué porcentaje de los respondentes está de acuerdo con sentirse parte de la comunidad escolar?"},
    {"id": "A05", "ins": 59, "tipo": "conteo", "grupo": {"genero": "femenino"}, "cond": [{"p": "p05", "nivel": "acuerdo"}],
     "texto": "¿Cuántas mujeres están de acuerdo con que se sienten seguras dentro de las instalaciones de la escuela?"},
    {"id": "A06", "ins": 59, "tipo": "porcentaje", "grupo": {"turno": "Vespertino"}, "cond": [{"p": "p01", "nivel": "desacuerdo"}],
     "texto": "¿Qué porcentaje del turno vespertino está en desacuerdo con que los criterios de evaluación se explican con claridad?"},
    # enc_09 (61): 160 respondentes, tipo de universidad como contexto
    {"id": "A07", "ins": 61, "tipo": "conteo", "cond": [{"p": "p14", "igual": "Trabajo más de 30h"}],
     "texto": "¿Cuántos estudiantes trabajan más de 30 horas?"},
    {"id": "A08", "ins": 61, "tipo": "porcentaje", "cond": [{"p": "p15", "igual": "Sí"}],
     "texto": "¿Qué porcentaje de los estudiantes tiene dificultades para equilibrar trabajo y estudios?"},
    {"id": "A09", "ins": 61, "tipo": "conteo", "cond": [{"p": "p13", "empieza": "Sí"}],
     "texto": "¿Cuántos estudiantes han reprobado alguna materia por falta de tiempo para estudiar?"},
    {"id": "A10", "ins": 61, "tipo": "promedio", "p": "p17",
     "texto": "¿Cuál es el promedio de horas por semana que los estudiantes dedican al estudio fuera de clases?"},
    {"id": "A11", "ins": 61, "tipo": "conteo", "grupo": {"tipo_universidad": "publica"}, "cond": [{"p": "p16", "igual": "Sí"}],
     "texto": "¿Cuántos estudiantes de universidad pública dicen que su institución ofrece talleres de gestión del tiempo?"},
    {"id": "A12", "ins": 61, "tipo": "porcentaje", "cond": [{"p": "p03", "nivel": "acuerdo"}],
     "texto": "¿Qué porcentaje de los estudiantes está de acuerdo con que tiene tiempo suficiente para estudiar cada materia?"},
    {"id": "A13", "ins": 61, "tipo": "conteo", "cond": [{"p": "p14", "igual": "Trabajo más de 30h"}, {"p": "p15", "igual": "Sí"}],
     "texto": "¿Cuántos estudiantes que trabajan más de 30 horas tienen dificultades para equilibrar trabajo y estudios?"},
    # Encuesta de 2000 respondentes (127)
    {"id": "A14", "ins": 127, "tipo": "conteo", "cond": [{"p": "p03", "contiene": "Cargas maxima"}],
     "texto": "¿Cuántos estudiantes llevan carga académica máxima?"},
    {"id": "A15", "ins": 127, "tipo": "porcentaje", "cond": [{"p": "p02", "igual": "En linea"}],
     "texto": "¿Qué porcentaje de los estudiantes cursa su programa en línea?"},
    {"id": "A16", "ins": 127, "tipo": "porcentaje", "cond": [{"p": "p17", "nivel": "desacuerdo"}],
     "texto": "¿Qué porcentaje está en desacuerdo con que los laboratorios, equipos y espacios son adecuados para su formación?"},
    {"id": "A17", "ins": 127, "tipo": "conteo", "cond": [{"p": "p12", "igual": "Trabajo en un area relacionada con mi carrera"}],
     "texto": "¿Cuántos estudiantes trabajan en un área relacionada con su carrera?"},
    {"id": "A18", "ins": 127, "tipo": "conteo", "cond": [{"p": "p11", "igual": "Si, y lo aprobe"}],
     "texto": "¿Cuántos estudiantes presentaron un examen de certificación profesional y lo aprobaron?"},
    {"id": "A19", "ins": 127, "tipo": "porcentaje", "cond": [{"p": "p10", "igual": "En el tiempo que marca mi plan de estudios"}],
     "texto": "¿Qué porcentaje espera titularse en el tiempo que marca su plan de estudios?"},
    {"id": "A20", "ins": 127, "tipo": "conteo", "cond": [{"p": "p02", "igual": "Presencial"}, {"p": "p03", "contiene": "Cargas maxima"}],
     "texto": "¿Cuántos estudiantes de modalidad presencial llevan carga académica máxima?"},
]
# Prueba ciega (10 nov): 20 preguntas nuevas, escritas antes de correrlas y después de terminar las correcciones hechas
# con las A01–A20. Se corren una sola vez y no se ajusta nada con sus resultados: miden si el sistema acierta con
# preguntas que no se usaron para corregirlo. Mismos instrumentos, otras preguntas del instrumento y otra redacción.
PREGUNTAS_CIEGA = [
    # 59: turno, género y semestre como contexto
    {"id": "B01", "ins": 59, "tipo": "conteo", "cond": [{"p": "p06", "nivel": "acuerdo"}],
     "texto": "¿Cuántos estudiantes consideran que las relaciones entre compañeros son respetuosas?"},
    {"id": "B02", "ins": 59, "tipo": "porcentaje", "grupo": {"genero": "masculino"}, "cond": [{"p": "p07", "nivel": "desacuerdo"}],
     "texto": "Entre los hombres, ¿qué porcentaje no está de acuerdo con que los profesores están disponibles para resolver dudas?"},
    {"id": "B03", "ins": 59, "tipo": "conteo", "grupo": {"turno": "Matutino"}, "cond": [{"p": "p03", "nivel": "desacuerdo"}],
     "texto": "¿Cuántos alumnos del turno matutino están en desacuerdo con que reciben retroalimentación a tiempo para mejorar?"},
    {"id": "B04", "ins": 59, "tipo": "porcentaje", "grupo": {"turno": "Vespertino"}, "cond": [{"p": "p08", "nivel": "acuerdo"}],
     "texto": "En el turno vespertino, ¿qué porcentaje se siente parte de la comunidad escolar?"},
    {"id": "B05", "ins": 59, "tipo": "conteo", "cond": [{"p": "p02", "nivel": "acuerdo"}, {"p": "p04", "nivel": "acuerdo"}],
     "texto": "¿Cuántos están de acuerdo tanto con que las calificaciones reflejan lo aprendido como con que las evaluaciones se relacionan con la clase?"},
    # 61: tipo de universidad como contexto
    {"id": "B06", "ins": 61, "tipo": "conteo", "cond": [{"p": "p14", "igual": "No trabajo"}],
     "texto": "¿Cuántos estudiantes no trabajan?"},
    {"id": "B07", "ins": 61, "tipo": "porcentaje", "cond": [{"p": "p11", "igual": "App digital"}],
     "texto": "¿Qué porcentaje usa una app digital como su principal estrategia para gestionar el tiempo?"},
    {"id": "B08", "ins": 61, "tipo": "conteo", "grupo": {"tipo_universidad": "privada"}, "cond": [{"p": "p09", "igual": "7 o más"}],
     "texto": "En las universidades privadas, ¿cuántos estudiantes cursan 7 o más materias?"},
    {"id": "B09", "ins": 61, "tipo": "promedio", "p": "p20",
     "texto": "En promedio, ¿cuántos créditos cursan los estudiantes este semestre?"},
    {"id": "B10", "ins": 61, "tipo": "porcentaje", "cond": [{"p": "p10", "nivel": "alta"}],
     "texto": "¿Qué porcentaje deja con frecuencia las tareas para el último momento?"},
    {"id": "B11", "ins": 61, "tipo": "conteo", "cond": [{"p": "p14", "igual": "No trabajo"}, {"p": "p15", "igual": "Sí"}],
     "texto": "¿Cuántos estudiantes que no trabajan dicen tener dificultades para equilibrar trabajo y estudios?"},
    {"id": "B12", "ins": 61, "tipo": "conteo", "cond": [{"p": "p13", "empieza": "No"}],
     "texto": "¿Cuántos estudiantes nunca han reprobado una materia por falta de tiempo?"},
    {"id": "B13", "ins": 61, "tipo": "porcentaje", "grupo": {"tipo_universidad": "mixta"}, "cond": [{"p": "p16", "igual": "No"}],
     "texto": "De los estudiantes de universidad mixta, ¿qué porcentaje dice que su institución no ofrece talleres de gestión del tiempo?"},
    # 127: 2000 respondentes
    {"id": "B14", "ins": 127, "tipo": "porcentaje", "cond": [{"p": "p09", "igual": "Diariamente"}],
     "texto": "¿Qué porcentaje de los estudiantes usa una plataforma virtual diariamente?"},
    {"id": "B15", "ins": 127, "tipo": "conteo", "cond": [{"p": "p10", "igual": "Estoy considerando abandonar"}],
     "texto": "¿Cuántos estudiantes están considerando abandonar sus estudios?"},
    {"id": "B16", "ins": 127, "tipo": "conteo", "cond": [{"p": "p01", "igual": "No"}],
     "texto": "¿Cuántos dicen que su programa no cuenta con acreditación vigente?"},
    {"id": "B17", "ins": 127, "tipo": "porcentaje", "cond": [{"p": "p13", "nivel": "alta"}],
     "texto": "¿Qué porcentaje ve probable volver a estudiar en esta institución?"},
    {"id": "B18", "ins": 127, "tipo": "conteo", "cond": [{"p": "p02", "igual": "Mixta/hibrida"}, {"p": "p12", "igual": "Busco empleo"}],
     "texto": "¿Cuántos estudiantes de modalidad mixta o híbrida están buscando empleo?"},
    {"id": "B19", "ins": 127, "tipo": "porcentaje", "cond": [{"p": "p18", "nivel": "acuerdo"}],
     "texto": "¿Qué porcentaje está de acuerdo con que encuentra lo que necesita en la biblioteca y las bases de datos académicas?"},
    {"id": "B20", "ins": 127, "tipo": "conteo", "cond": [{"p": "p14", "igual": "Si, en una empresa con convenio de mi institucion"}],
     "texto": "¿Cuántos estudiantes hicieron prácticas profesionales en una empresa con convenio de su institución?"},
]
CONJUNTOS = {"aritmetica": PREGUNTAS, "ciega": PREGUNTAS_CIEGA}
VENTANA_DATOS = 8192
SISTEMA = ("Eres un asistente de análisis de datos de instrumentos educativos. Responde en español, en una o dos "
           "oraciones, con la cifra exacta que se pide (conteo y, si aplica, porcentaje con un decimal). Usa solo los "
           "datos que se te dan.")


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(t.replace(".", " ").split())


def _cumple(fila: dict | None, c: dict) -> bool:
    if not fila or fila["estado"] != "respondida":
        return False
    if "nivel" in c:
        return fila["nivel"] == c["nivel"]
    s = _norm(fila["significado"])
    if "igual" in c:
        return s == _norm(c["igual"])
    if "empieza" in c:
        return s.startswith(_norm(c["empieza"]))
    return any(_norm(c["contiene"]) == _norm(o) for o in str(fila["significado"]).split(","))


def esperado(q: dict, datos: dict) -> dict:
    grupo = q.get("grupo") or {}
    personas = [r for r in datos.values() if all(r["contexto"].get(k) == v for k, v in grupo.items())]
    if q["tipo"] == "promedio":
        vals = []
        for r in personas:
            f = r["resp"].get(q["p"])
            if f and f["estado"] == "respondida":
                m = re.search(r"-?\d+(?:\.\d+)?", str(f["valor"]))
                if m:
                    vals.append(float(m.group()))
        return {"valor": round(sum(vals) / len(vals), 2), "n": len(vals)}
    k = sum(all(_cumple(r["resp"].get(c["p"]), c) for c in q["cond"]) for r in personas)
    n = sum(all((r["resp"].get(c["p"]) or {}).get("estado") == "respondida" for c in q["cond"]) for r in personas)
    return {"k": k, "n": n, "pct": round(100 * k / n, 1) if n else None}


# ---------------------------------------------------------------- A y B (dentro del contenedor)
def modelo() -> None:
    import chromadb
    import httpx
    from sentence_transformers import SentenceTransformer
    from sqlalchemy import create_engine, text

    from shared.db.core.config import settings

    motor = create_engine(settings.DATABASE_URL)
    emb = SentenceTransformer(settings.EMBEDDING_MODEL)
    col = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT).get_collection("instrumentos")
    datos_por_ins: dict[int, dict] = {}
    with motor.connect() as cx:
        for ins in sorted({q["ins"] for q in PREGUNTAS}):
            v = cx.execute(text("select version from tt_rag.version_conocimiento where id_crudo=:i and estado='vigente'"),
                           {"i": ins}).scalar()
            filas = cx.execute(text("select respondente_id, pregunta_id, valor, significado, nivel, estado, contexto "
                                    "from tt_rag.respuesta_interpretada where id_crudo=:i and version=:v"), {"i": ins, "v": v})
            d: dict = {}
            for r in filas.mappings():
                p = d.setdefault(r["respondente_id"].rsplit("-", 1)[-1], {"contexto": r["contexto"] or {}, "resp": {}})
                p["resp"][r["pregunta_id"].rsplit("-", 1)[-1]] = dict(r)
            datos_por_ins[ins] = d

    def preguntar(prompt: str, ctx: int) -> tuple[str, float]:
        t0 = time.monotonic()
        r = httpx.post(f"{settings.OLLAMA_HOST}/api/generate", timeout=600, json={
            "model": settings.OLLAMA_MODEL, "system": SISTEMA, "prompt": prompt, "stream": False, "keep_alive": -1,
            "options": {"temperature": 0.2, "num_ctx": ctx}})
        r.raise_for_status()
        return r.json()["response"].strip(), round(time.monotonic() - t0, 1)

    salida = []
    for q in PREGUNTAS:
        datos = datos_por_ins[q["ins"]]
        fila = {"id": q["id"], "ins": q["ins"], "tipo": q["tipo"], "texto": q["texto"], "esperado": esperado(q, datos)}
        # A. Solo los fragmentos recuperados
        vector = emb.encode([q["texto"]], normalize_embeddings=True).tolist()
        where = {"$and": [{"instrumentoId": str(q["ins"])}, {"seccion": {"$nin": ["respondente", "alumno"]}}]}
        r = col.query(query_embeddings=vector, n_results=8, where=where, include=["documents"])
        frags = r["documents"][0]
        prompt = "".join(f'<datos fuente="{i + 1}">\n{t}\n</datos>\n' for i, t in enumerate(frags)) + f"\nPregunta: {q['texto']}"
        fila["A"] = dict(zip(("respuesta", "segundos"), preguntar(prompt, 4096)), fragmentos=len(frags))
        # B. Las respuestas de cada persona a las preguntas necesarias
        preguntas = [q["p"]] if q["tipo"] == "promedio" else [c["p"] for c in q["cond"]]
        lineas = []
        for rid, p in sorted(datos.items()):
            ctx = ", ".join(f"{k}={v}" for k, v in p["contexto"].items())
            resp = "; ".join(f"{pid}={(p['resp'].get(pid) or {}).get('significado') or 'sin respuesta'}" for pid in preguntas)
            lineas.append(f"{rid} | {ctx} | {resp}" if ctx else f"{rid} | {resp}")
        tabla = "\n".join(lineas)
        tokens = len(emb.tokenizer.tokenize(tabla))
        fila["B"] = {"filas": len(lineas), "tokens_datos": tokens}
        if tokens + 600 > VENTANA_DATOS:
            fila["B"]["respuesta"] = None
            fila["B"]["motivo"] = f"no cabe: {tokens} tokens de datos en una ventana de {VENTANA_DATOS}"
        else:
            prompt = (f"Respuestas de cada persona (una fila por persona):\n{tabla}\n\nPregunta: {q['texto']}\n"
                      "Cuenta con cuidado en la tabla.")
            fila["B"].update(zip(("respuesta", "segundos"), preguntar(prompt, VENTANA_DATOS)))
        print(q["id"], fila["esperado"], file=sys.stderr)
        salida.append(fila)
    json.dump(salida, sys.stdout, ensure_ascii=False, indent=1)


# ---------------------------------------------------------------- C (desde el equipo)
def sistema(carpeta: str, ids: set[str] | None = None, conjunto: str = "aritmetica") -> None:
    import httpx
    destino = Path(carpeta)
    http = httpx.Client(timeout=600)
    tok = http.post("http://localhost:8006/auth/login", json={"email": "admin@indagata.com", "password": "admin123"})
    cab = {"Authorization": f"Bearer {tok.json()['access_token']}"}
    archivo = destino / "sistema.json"
    salida = json.loads(archivo.read_text(encoding="utf-8")) if archivo.exists() else []
    hechas = {s["id"] for s in salida}
    for q in CONJUNTOS[conjunto]:
        if q["id"] in hechas or (ids and q["id"] not in ids):  # se guarda cada respuesta: una corrida interrumpida
            continue                                                # sigue donde se quedó
        cuerpo = {"pregunta": q["texto"], "instrumentoIds": [str(q["ins"])], "stream": False, "usarCache": False,
                  "calcularMetricas": False, "historial": []}
        t0 = time.monotonic()
        r = http.post("http://localhost:8006/rag/chat", json=cuerpo, headers=cab)
        r.raise_for_status()
        j = r.json()
        salida.append({"id": q["id"], "respuesta": j.get("respuesta", ""), "segundos": round(time.monotonic() - t0, 1),
                       "consultaId": j.get("consultaId"), "ruta": j.get("ruta")})
        archivo.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
        print(q["id"], salida[-1]["segundos"], "s", file=sys.stderr)


# ---------------------------------------------------------------- cifras esperadas y calificación de un conjunto
def esperados(conjunto: str) -> None:
    """Dentro del contenedor: la cifra correcta de cada pregunta del conjunto, directo de `respuesta_interpretada`."""
    from sqlalchemy import create_engine, text

    from shared.db.core.config import settings

    motor = create_engine(settings.DATABASE_URL)
    salida = {}
    with motor.connect() as cx:
        for ins in sorted({q["ins"] for q in CONJUNTOS[conjunto]}):
            v = cx.execute(text("select version from tt_rag.version_conocimiento where id_crudo=:i and estado='vigente'"),
                           {"i": ins}).scalar()
            filas = cx.execute(text("select respondente_id, pregunta_id, valor, significado, nivel, estado, contexto "
                                    "from tt_rag.respuesta_interpretada where id_crudo=:i and version=:v"), {"i": ins, "v": v})
            datos: dict = {}
            for r in filas.mappings():
                d = datos.setdefault(r["respondente_id"].rsplit("-", 1)[-1], {"contexto": r["contexto"] or {}, "resp": {}})
                d["resp"][r["pregunta_id"].rsplit("-", 1)[-1]] = dict(r)
            for q in (q for q in CONJUNTOS[conjunto] if q["ins"] == ins):
                salida[q["id"]] = {"ins": ins, "tipo": q["tipo"], "texto": q["texto"], "esperado": esperado(q, datos)}
    json.dump(salida, sys.stdout, ensure_ascii=False, indent=1)


def calificar(carpeta: str, archivo_esperados: str, conjunto: str) -> None:
    """Califica las respuestas del sistema (sistema.json) contra las cifras esperadas; escribe RESULTADO.md."""
    c = Path(carpeta)
    esp = json.loads(Path(archivo_esperados).read_text(encoding="utf-8-sig"))
    sis = {s["id"]: s for s in json.loads((c / "sistema.json").read_text(encoding="utf-8"))}
    filas, bien = [], 0
    for q in CONJUNTOS[conjunto]:
        e = esp[q["id"]]["esperado"]
        cifra = e.get("valor") if q["tipo"] == "promedio" else (f"{e['pct']} % ({e['k']} de {e['n']})" if q["tipo"] == "porcentaje" else f"{e['k']} de {e['n']}")
        r = sis.get(q["id"], {}).get("respuesta")
        ok = correcta(q["tipo"], e, r)
        bien += bool(ok)
        filas.append({"id": q["id"], "ins": q["ins"], "pregunta": q["texto"], "esperado": str(cifra), "correcta": ok,
                      "respuesta": r, "consultaId": sis.get(q["id"], {}).get("consultaId")})
    md = [f"# Prueba de aritmética, conjunto «{conjunto}»: el sistema completo", "",
          f"Correctas: {bien} de {len(filas)}", "", "| ID | Inst. | Pregunta | Esperado | Sistema |", "|---|---|---|---|---|"]
    md += [f"| {f['id']} | {f['ins']} | {f['pregunta']} | {f['esperado']} | {'✔' if f['correcta'] else ('pendiente' if f['correcta'] is None else '✘')} |" for f in filas]
    md += ["", "## Respuestas", ""] + [f"### {f['id']} (esperado: {f['esperado']}; rag_log {f['consultaId']})\n{f['respuesta']}\n"
                                        for f in filas]
    (c / "RESULTADO.md").write_text("\n".join(md), encoding="utf-8")
    (c / "resumen.json").write_text(json.dumps({"correctas": bien, "total": len(filas), "filas": filas}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(md[:len(filas) + 6]))


# ---------------------------------------------------------------- calificación
_ID = re.compile(r"\b[pPrReE]\d{1,4}\b|\bINS-\d+\S*")


def cifras(texto: str) -> list[float]:
    t = _ID.sub(" ", texto or "")
    t = re.sub(r"(\d),(\d{3})\b", r"\1\2", t)      # 1,303 → 1303
    return [float(x.replace(",", ".")) for x in re.findall(r"\d+(?:[.,]\d+)?", t)]


def correcta(tipo: str, esp: dict, texto: str | None) -> bool | None:
    if texto is None:
        return None
    nums = cifras(texto)
    if tipo == "promedio":
        return any(abs(x - esp["valor"]) <= 0.05 for x in nums)
    if tipo == "porcentaje":
        return any(abs(x - esp["pct"]) <= 0.1 for x in nums)
    return any(x == esp["k"] for x in nums)


def resumen(carpeta: str) -> None:
    c = Path(carpeta)
    mod = json.loads((c / "modelo.json").read_text(encoding="utf-8-sig"))
    sis = {s["id"]: s for s in json.loads((c / "sistema.json").read_text(encoding="utf-8"))}
    filas, tot = [], {"A": [0, 0], "B": [0, 0], "C": [0, 0]}
    for m in mod:
        e = m["esperado"]
        cifra = e.get("valor") if m["tipo"] == "promedio" else (f"{e['pct']} % ({e['k']} de {e['n']})" if m["tipo"] == "porcentaje" else f"{e['k']} de {e['n']}")
        res = {"A": correcta(m["tipo"], e, m["A"]["respuesta"]), "B": correcta(m["tipo"], e, m["B"].get("respuesta")),
               "C": correcta(m["tipo"], e, sis.get(m["id"], {}).get("respuesta"))}
        for k, v in res.items():
            if v is not None:
                tot[k][0] += v
                tot[k][1] += 1
        filas.append({"id": m["id"], "ins": m["ins"], "pregunta": m["texto"], "esperado": cifra, **{k: res[k] for k in res},
                      "A_texto": m["A"]["respuesta"], "B_texto": m["B"].get("respuesta") or m["B"].get("motivo"),
                      "C_texto": sis.get(m["id"], {}).get("respuesta")})
    md = ["# Prueba de aritmética: el modelo calcula frente al código calcula", "",
          "| ID | Inst. | Pregunta | Esperado | A. Solo RAG | B. Modelo con datos | C. Sistema |", "|---|---|---|---|---|---|---|"]
    marca = {True: "✔", False: "✘", None: "no cabe"}
    for f in filas:
        marca_c = "pendiente" if f["C"] is None else marca[f["C"]]
        md.append(f"| {f['id']} | {f['ins']} | {f['pregunta']} | {f['esperado']} | {marca[f['A']]} | {marca[f['B']]} | {marca_c} |")
    md += ["", "| Condición | Correctas |", "|---|---|"]
    for k, nombre in (("A", "A. Solo RAG"), ("B", "B. Modelo con datos"), ("C", "C. Sistema")):
        md.append(f"| {nombre} | {tot[k][0]} de {tot[k][1]} ({100 * tot[k][0] / max(tot[k][1], 1):.1f} %) |")
    md += ["", "## Respuestas", ""]
    for f in filas:
        md += [f"### {f['id']} — {f['pregunta']} (esperado: {f['esperado']})", f"- **A:** {f['A_texto']}",
               f"- **B:** {f['B_texto']}", f"- **C:** {f['C_texto']}", ""]
    (c / "RESULTADO.md").write_text("\n".join(md), encoding="utf-8")
    (c / "resumen.json").write_text(json.dumps({"totales": tot, "filas": filas}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(md[: len(filas) + 9]))


if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else ""
    if modo == "modelo":
        modelo()
    elif modo == "sistema":
        args = [a for a in sys.argv[3:] if not a.startswith("--")]
        conjunto = "ciega" if "--ciega" in sys.argv else "aritmetica"
        sistema(sys.argv[2], set(args[0].split(",")) if args else None, conjunto)
    elif modo == "esperados":
        esperados(sys.argv[2])
    elif modo == "calificar":
        calificar(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "aritmetica")
    elif modo == "resumen":
        resumen(sys.argv[2])
    else:
        sys.exit(__doc__)
