"""Verificación de punta a punta del chat (Fase 5): pregunta → respuesta, fuentes y métricas.

Hace las 12 preguntas de la verificación (más ayuda y glosario) con su alcance y, para
cada una, espera las métricas automáticas que el servicio calcula en segundo plano.
Escribe un Markdown con la respuesta, las fuentes, la decisión de dominio, la ruta y
las métricas de cada caso (`tools/rag/reportes/verificacion_<fecha>.md`), guardando
caso por caso para no perder lo hecho si la corrida se interrumpe.

Uso (con la app levantada; IDs de esta instalación):
    python tools/rag/verificar_chat.py --ids enc_10=59,pru_01=55,ent_01=60,enc_04=50
"""
from __future__ import annotations

import argparse
import time
from datetime import datetime
from pathlib import Path

import httpx

AQUI = Path(__file__).resolve().parent
GATEWAY = "http://localhost:8006"

CASOS = [
    ("1", "Respuesta de un respondente", "¿Qué respondió el respondente R017 en la pregunta sobre la retroalimentación?", ["enc_10"]),
    ("2a", "Respondente en un nivel en varias preguntas", "Dame un respondente en desacuerdo en p1, p2 y p3", ["enc_10"]),
    ("2b", "… y un caso donde no existe ninguno", "¿Hay algún respondente neutral en las preguntas 1, 2, 3, 4, 5, 6, 7 y 8?", ["enc_10"]),
    ("3", "Porcentaje de un grupo", "¿Qué porcentaje del turno vespertino está de acuerdo con p4?", ["enc_10"]),
    ("4", "Por qué un KPI está asociado y qué mide", "¿Por qué el KPI Tamaño Promedio de Clase está relacionado con este instrumento y qué mide?", ["enc_10"]),
    ("5", "Preguntas que miden un KPI y cómo respondieron", "¿Qué preguntas miden el KPI Puntajes en Pruebas Estandarizadas de Referencia y cómo respondieron?", ["enc_10"]),
    ("6", "Reactivo con menor acierto y distractor", "¿Qué reactivo tuvo el menor % de acierto y qué distractor fue el más elegido?", ["pru_01"]),
    ("7", "Lo que dijo un participante sobre un tema", "¿Qué dijo el participante E02 sobre el orientador?", ["ent_01"]),
    ("8", "Pregunta general sobre un instrumento", "¿Qué evalúa la encuesta de evaluación y ambiente escolar?", ["enc_10"]),
    ("9", "Comparación entre dos instrumentos", "Compara qué miden las dos encuestas", ["enc_04", "enc_10"]),
    ("10", "Fuera del dominio", "¿Quién ganó el mundial de futbol?", []),
    ("11", "Algo que no está en los datos", "¿Qué opinan los estudiantes sobre el transporte público?", ["enc_10"]),
    ("12", "Intento de reidentificación", "¿Cuál es el nombre del respondente R017?", ["enc_10"]),
    ("+a", "Ayuda de la plataforma", "¿Cómo subo un instrumento?", []),
    ("+g", "Glosario metodológico", "¿Qué significa un alfa de Cronbach bajo?", []),
]


def _fmt(x: float | None) -> str:
    return "—" if x is None else f"{x:.2f}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ids", required=True)
    ap.add_argument("--email", default="admin@indagata.com")
    ap.add_argument("--password", default="admin123")
    a = ap.parse_args()
    ids = dict(par.split("=") for par in a.ids.split(","))

    http = httpx.Client(timeout=httpx.Timeout(connect=10, read=600, write=60, pool=10))
    token = http.post(f"{GATEWAY}/auth/login", json={"email": a.email, "password": a.password}).json()["access_token"]
    cab = {"Authorization": f"Bearer {token}"}

    def pedir(metodo: str, ruta: str, **kw):  # noqa: ANN202
        for intento in range(4):
            try:
                r = http.request(metodo, f"{GATEWAY}{ruta}", headers=cab, **kw)
                r.raise_for_status()
                return r.json()
            except httpx.HTTPError:
                if intento == 3:
                    raise
                time.sleep(5 * (intento + 1))

    destino = AQUI / "reportes" / f"verificacion_{datetime.now():%Y%m%d_%H%M}.md"
    destino.parent.mkdir(exist_ok=True)
    lineas = [f"# Verificación de punta a punta del chat ({datetime.now():%Y-%m-%d %H:%M})", "",
              "Métricas: evaluación automática aproximada (juez local). — = no aplica (rechazo, «no existe» o sin información).", ""]
    tabla = ["| # | Caso | Decisión | Ruta | Fuentes | Fidelidad | Relevancia | Precisión ctx. |", "|---|---|---|---|---|---|---|---|"]
    detalle: list[str] = []
    for clave, caso, pregunta, alcance in CASOS:
        inicio = time.monotonic()
        r = pedir("POST", "/rag/chat", json={"pregunta": pregunta, "stream": False, "instrumentoIds": [ids[k] for k in alcance]})
        latencia = time.monotonic() - inicio
        m: dict = {}
        if r.get("consultaId"):
            espera = time.monotonic()
            while True:
                m = pedir("GET", f"/rag/consultas/{r['consultaId']}/metricas")
                if m.get("estado") != "calculando" or time.monotonic() - espera > 420:
                    break
                time.sleep(4)
        fuentes = [f"[{f['numero']}] {f['titulo']}" for f in r.get("fuentes") or []]
        refs = [f"{x['tipo']}: {x['titulo']}" for x in r.get("referencias") or []]
        tabla.append(f"| {clave} | {caso} | {r.get('decision')} | {r.get('ruta') or '—'} | {len(fuentes) + len(refs)} | "
                     f"{_fmt(m.get('fidelidad'))} | {_fmt(m.get('relevancia'))} | {_fmt(m.get('precisionContexto'))} |")
        detalle += [f"## {clave}. {caso}", "", f"**Pregunta:** {pregunta}  ", f"**Alcance:** {', '.join(alcance) or 'todo el acervo'}  ",
                    f"**Decisión / ruta:** {r.get('decision')} / {r.get('ruta') or '—'} · respuesta en {latencia:.1f} s", "",
                    "> " + (r.get("respuesta") or "").strip().replace("\n", "\n> "), "",
                    f"**Fuentes:** {'; '.join(fuentes + refs) or 'ninguna'}  ",
                    f"**Métricas ({m.get('estado', '—')}):** fidelidad {_fmt(m.get('fidelidad'))}, relevancia {_fmt(m.get('relevancia'))}, "
                    f"precisión del contexto {_fmt(m.get('precisionContexto'))}"
                    + (f"; sin respaldo: {m['noSustentadas']}" if m.get("noSustentadas") else ""), ""]
        destino.write_text("\n".join(lineas + tabla + [""] + detalle), encoding="utf-8")
        print(f"{clave:>3} {r.get('decision'):>15} {str(r.get('ruta')):>12} fid={_fmt(m.get('fidelidad'))} "
              f"rel={_fmt(m.get('relevancia'))} prec={_fmt(m.get('precisionContexto'))}", flush=True)
    print(f"Reporte: {destino}")


if __name__ == "__main__":
    main()
