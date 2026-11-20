"""Eliminar una columna desde «Rol» o «Calidad» vuelve innecesaria la otra tarjeta de esa columna (19 nov)."""

from services.ejecuciones import columnas_eliminadas, pendientes_obligatorias


def _reporte(decisiones: dict[str, str], sugerida_incompleta: str = "conservar") -> dict:
    return {
        "hallazgos": [
            {"id": "rol:c1", "tipo": "rol_columna", "objetivo": "c1", "obligatoria": True, "sugerida": None},
            {"id": "incompleta:c1", "tipo": "columna_incompleta", "objetivo": "c1", "obligatoria": False,
             "sugerida": sugerida_incompleta},
            {"id": "rol:c2", "tipo": "rol_columna", "objetivo": "c2", "obligatoria": True, "sugerida": None},
        ],
        "decisiones": decisiones,
    }


def test_rol_obligatorio_sigue_pendiente_si_nadie_elimina_la_columna():
    assert pendientes_obligatorias(_reporte({})) == ["rol:c1", "rol:c2"]


def test_eliminar_desde_calidad_libera_el_rol_obligatorio_de_esa_columna():
    reporte = _reporte({"incompleta:c1": "eliminar"})
    assert columnas_eliminadas(reporte) == {"c1"}
    assert pendientes_obligatorias(reporte) == ["rol:c2"]


def test_la_sugerencia_vigente_de_eliminar_tambien_cuenta():
    assert pendientes_obligatorias(_reporte({}, sugerida_incompleta="eliminar")) == ["rol:c2"]
    # Si el investigador decide conservarla, el rol vuelve a ser obligatorio.
    assert pendientes_obligatorias(_reporte({"incompleta:c1": "conservar"}, "eliminar")) == ["rol:c1", "rol:c2"]
