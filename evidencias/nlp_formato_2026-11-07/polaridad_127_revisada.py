from services import documento, storage_client
from services.documento import polaridad
from shared.db.session import SessionLocal
from shared.models.version_conocimiento import VersionConocimiento
# Decisión de la investigadora (7 nov): «todas como tu sugerencia». Escalas por punto; opciones por texto.
D = {
 "p01": (["Si"], ["No"]), "p02": ([], []),
 "p04": (["Mas de la mitad", "Todos"], ["Menos de la mitad", "Ninguno"]),
 "p05": (["Nunca", "Rara vez"], ["Frecuentemente", "Siempre"]),
 "p06": (["2-3", "4 o mas"], ["Ninguno"]),
 "p08": (["Si, conozco al menos una", "Si, y participe en alguna"], ["No ha obtenido"]),
 "p09": (["Diariamente", "Semanalmente"], ["Menos de una vez al mes", "Nunca"]),
 "p10": (["En el tiempo que marca mi plan de estudios"], ["Con hasta un año de retraso", "Con mas de un año de retraso", "Estoy considerando abandonar"]),
 "p11": (["Si, y lo aprobe"], ["No, y no lo planeo"]),
 "p12": (["Trabajo en un area relacionada con mi carrera"], ["Busco empleo"]),
 "p13": ([4, 5], [1, 2]), "p14": (["Si, en una empresa con convenio de mi institucion", "Si, pero la consegui por mi cuenta"], ["No"]),
 "p16": ([4, 5], [1, 2]), "p17": ([4, 5], [1, 2]), "p18": ([4, 5], [1, 2]),
}
db = SessionLocal()
f = db.query(VersionConocimiento).filter_by(id_crudo=127, estado="vigente").one()
doc = storage_client.descargar_json(f.ruta_documento)
for p in doc["preguntas"]:
    corto = p["id"].rsplit("-", 1)[-1]
    if corto not in D:
        continue
    fav, desf = D[corto]
    etq = (p.get("escala") or {}).get("etiquetas") or {}
    a_texto = lambda xs: [etq[str(x)] if isinstance(x, int) else x for x in xs]
    fav, desf = a_texto(fav), a_texto(desf)
    ops = polaridad.opciones_de(p)
    assert all(o in ops for o in fav + desf), (corto, fav, desf, ops)
    p["polaridad"] = {"favorables": fav, "desfavorables": desf, "origen": "investigador", "estado": "revisado"}
    print(corto, fav, "/", desf)
documento.validar(doc)
ref = storage_client.guardar_json(127, "documento", doc, f"v{f.version}_documento_final")
f.ruta_documento, f.sha256 = ref["key"], ref.get("sha256"); db.commit(); print("guardado", ref["key"])
