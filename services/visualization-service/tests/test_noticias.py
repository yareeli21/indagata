"""Panel de noticias: lectura de RSS/Atom, caché y caída sin red (sin salir a internet)."""
from __future__ import annotations

import httpx
import pytest

from conftest import token
from services import noticias

RSS = """<?xml version="1.0"?><rss version="2.0"><channel><title>Google Noticias</title>
<item><title>Nueva reforma a la educación superior - El Universal</title><link>https://ejemplo.mx/a</link>
<pubDate>Fri, 16 Oct 2026 10:00:00 GMT</pubDate><description>&lt;a href="x"&gt;Resumen &amp;amp; más&lt;/a&gt;</description>
<source url="https://eluniversal.com.mx">El Universal</source></item>
<item><title>Investigación educativa en 2026</title><link>https://ejemplo.mx/b</link>
<pubDate>Sat, 17 Oct 2026 09:00:00 GMT</pubDate><description>Otra nota</description></item>
</channel></rss>"""
ATOM = """<?xml version="1.0" encoding="utf-8"?><feed xmlns="http://www.w3.org/2005/Atom"><title>Campus</title>
<entry><title>Investigación educativa en 2026</title><link href="https://otro.mx/b"/><updated>2026-10-15T08:00:00Z</updated>
<summary>Repetida con otro enlace</summary></entry>
<entry><title>Becas para posgrado</title><link href="https://otro.mx/c"/><updated>2026-10-18T08:00:00Z</updated>
<summary>&lt;p&gt;Convocatoria abierta&lt;/p&gt;</summary></entry></feed>"""


def test_parsear_rss_quita_html_y_el_medio_del_titulo():
    [a, b] = noticias.parsear(RSS, "Google Noticias")
    assert a["titulo"] == "Nueva reforma a la educación superior" and a["medio"] == "El Universal"
    assert a["resumen"] == "Resumen & más" and a["fecha"].isoformat().startswith("2026-10-16")
    assert b["medio"] == "Google Noticias"


def test_parsear_atom():
    [_, c] = noticias.parsear(ATOM.encode("utf-8"), "Campus")
    assert c == {"titulo": "Becas para posgrado", "resumen": "Convocatoria abierta", "url": "https://otro.mx/c",
                 "fecha": c["fecha"], "medio": "Campus"} and c["fecha"].day == 18


class _Cliente:
    """httpx.Client falso: responde por URL; `caido` simula no tener red."""

    respuestas: dict[str, str] = {}
    caido = False
    llamadas = 0

    def __init__(self, *a, **kw):  # noqa: ANN002, ANN003
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):  # noqa: ANN002
        return False

    def get(self, url, **kw):  # noqa: ANN001, ANN003
        type(self).llamadas += 1
        if type(self).caido:
            raise httpx.ConnectError("sin red")
        return httpx.Response(200, text=self.respuestas[url], request=httpx.Request("GET", url))


@pytest.fixture()
def fuentes(monkeypatch):
    from shared.db.core.config import settings

    _Cliente.respuestas = {"https://g/rss": RSS, "https://c/atom": ATOM}
    _Cliente.caido, _Cliente.llamadas = False, 0
    monkeypatch.setattr(noticias.httpx, "Client", _Cliente)
    monkeypatch.setattr(noticias, "config", lambda: {"fuentes": [{"nombre": "Google Noticias", "url": "https://g/rss"},
                                                                 {"nombre": "Campus", "url": "https://c/atom"}], "maximo": 10})
    monkeypatch.setattr(settings, "NOTICIAS_API_KEY", "")
    monkeypatch.setattr(noticias, "_cache", {"hasta": 0.0, "datos": None})
    return _Cliente


def test_ordena_por_fecha_quita_repetidas_y_usa_cache(cliente, fuentes, db):
    from shared.models.usuario import Usuario

    db.add(Usuario(usuario_id=2, nombre="Ana", email="ana@x.com", password_hash="x", rol="investigador"))
    db.commit()
    r = cliente.get("/visualizacion/noticias", headers=token(2))
    assert r.status_code == 200, r.text
    datos = r.json()
    assert [n["titulo"] for n in datos["noticias"]] == [
        "Becas para posgrado", "Investigación educativa en 2026", "Nueva reforma a la educación superior"]
    assert datos["noticias"][0]["fecha"] == "2026-10-18" and datos["aviso"] is None
    llamadas = fuentes.llamadas
    cliente.get("/visualizacion/noticias", headers=token(2))
    assert fuentes.llamadas == llamadas  # de la caché
    cliente.get("/visualizacion/noticias", params={"actualizar": "true"}, headers=token(2))
    assert fuentes.llamadas == llamadas + 2


def test_sin_red_devuelve_lo_ultimo_o_un_aviso(fuentes):
    fuentes.caido = True
    vacio = noticias.obtener()
    assert vacio["noticias"] == [] and "sin conexión" in vacio["aviso"].lower()
    fuentes.caido = False
    assert len(noticias.obtener(forzar=True)["noticias"]) == 3
    fuentes.caido = True
    previo = noticias.obtener(forzar=True)
    assert len(previo["noticias"]) == 3 and "últimas obtenidas" in previo["aviso"]


def test_requiere_sesion(cliente, fuentes):
    assert cliente.get("/visualizacion/noticias").status_code == 401
