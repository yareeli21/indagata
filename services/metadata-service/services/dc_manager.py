"""Dublin Core — propuesta, normalización, validación y persistencia.

Todo instrumento DEBE tener sus 13 campos Dublin Core (tabla `metadatos_dc`,
clave `id_crudo`). El servicio los propone a partir de hechos del sistema
(autor, fecha de carga, formato del archivo) y de lo inferido del contenido; el
autor los revisa y los aprueba. Solo `dc_relation` es opcional.

Origen de cada valor propuesto:
  - automatico: hecho del sistema (usuario, archivo, fecha).
  - archivo:    leído del propio instrumento (JSON con Dublin Core).
  - inferido:   heurística sobre el contenido.
  - llm:        sugerido por el modelo local.
  - aprobado:   ya aprobado por el autor (valor guardado en BD).
"""
from __future__ import annotations

import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from shared.db.core.config import settings
from shared.models.metadatos_dc import MetadatosDC

from services.analizador import Analisis
from services.campos import CAMPOS_DC, TIPO_UI

CLAVES_DC: tuple[str, ...] = tuple(c.clave for c in CAMPOS_DC)
DERECHOS_POR_DEFECTO = (
    "Uso académico. Datos de investigación educativa: citar a la autoría y "
    "solicitar autorización para su reutilización."
)
_MIME = {
    ".csv": "text/csv",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".json": "application/json",
    ".md": "text/markdown",
}


def _texto(valor: Any) -> str:
    if valor is None:
        return ""
    if isinstance(valor, (list, tuple)):
        return ", ".join(t for t in (_texto(v) for v in valor) if t)
    return str(valor).strip()


def formato_de(nombre: str) -> str:
    extension = Path(nombre or "").suffix.lower()
    return _MIME.get(extension) or mimetypes.guess_type(nombre or "")[0] or "application/octet-stream"


def cobertura_sugerida(analisis: Analisis) -> str:
    """«Nivel — población» a partir de lo inferido del instrumento."""
    nivel = analisis.hallazgos.get("nivel_educativo", "")
    if not nivel and analisis.carreras:
        nivel = "Licenciatura"
    if nivel in ("Maestría", "Doctorado"):
        nivel = f"Posgrado ({nivel.lower()})"
    poblacion = analisis.hallazgos.get("poblacion", "")
    return " — ".join(p for p in (nivel, poblacion) if p)


class DCManager:
    """Lógica de negocio de los metadatos Dublin Core."""

    @staticmethod
    def proponer(raw: Any, autor_nombre: str, analisis: Analisis) -> tuple[dict[str, str], dict[str, str]]:
        archivo = analisis.dc_archivo
        valores: dict[str, str] = {}
        origen: dict[str, str] = {}

        def poner(clave: str, *candidatos: tuple[Any, str]) -> None:
            for valor, fuente in candidatos:
                texto = _texto(valor)
                if texto:
                    valores[clave], origen[clave] = texto, fuente
                    return
            valores[clave] = ""

        fecha = raw.fecha_carga.date().isoformat() if isinstance(raw.fecha_carga, datetime) else ""
        tipo = (raw.tipo_instrumento or "").lower()

        poner("dc_title", (archivo.get("dc_title"), "archivo"), (analisis.titulo, "inferido"))
        poner("dc_creator", (archivo.get("dc_creator"), "archivo"), (autor_nombre, "automatico"))
        poner("dc_subject", (archivo.get("dc_subject"), "archivo"), (analisis.palabras_clave[:6], "inferido"))
        poner("dc_description", (archivo.get("dc_description"), "archivo"), (analisis.descripcion, "inferido"))
        poner("dc_type", (TIPO_UI.get(tipo, raw.tipo_instrumento), "automatico"))
        poner("dc_date", (archivo.get("dc_date"), "archivo"), (fecha, "automatico"))
        poner("dc_language", (archivo.get("dc_language"), "archivo"), (analisis.idioma, "automatico"))
        poner("dc_coverage", (archivo.get("dc_coverage"), "archivo"), (cobertura_sugerida(analisis), "inferido"))
        poner(
            "dc_publisher",
            (archivo.get("dc_publisher"), "archivo"),
            (analisis.hallazgos.get("institucion"), "inferido"),
            (settings.APP_NAME, "automatico"),
        )
        poner("dc_rights", (archivo.get("dc_rights"), "archivo"), (DERECHOS_POR_DEFECTO, "inferido"))
        poner("dc_format", (archivo.get("dc_format"), "archivo"), (formato_de(raw.nombre_archivo), "automatico"))
        poner("dc_source", (archivo.get("dc_source"), "archivo"), (raw.nombre_archivo, "automatico"))
        poner("dc_relation", (archivo.get("dc_relation"), "archivo"))
        return valores, origen

    @staticmethod
    def normalizar(payload: dict[str, Any] | None) -> dict[str, str | None]:
        """Recorta textos, une listas con comas y deja None en los vacíos."""
        datos = payload or {}
        return {clave: (_texto(datos.get(clave)) or None) for clave in CLAVES_DC}

    @staticmethod
    def validar(valores: dict[str, str | None]) -> dict[str, str]:
        """Errores por campo ({clave: mensaje}); vacío si todo es válido."""
        errores: dict[str, str] = {}
        for campo in CAMPOS_DC:
            valor = valores.get(campo.clave)
            if campo.requerido and not valor:
                errores[campo.clave] = f"«{campo.etiqueta}» es obligatorio."
            elif valor and campo.max_longitud and len(valor) > campo.max_longitud:
                errores[campo.clave] = f"«{campo.etiqueta}» admite como máximo {campo.max_longitud} caracteres."
        return errores

    @staticmethod
    def guardar(db: Session, id_crudo: int, valores: dict[str, str | None]) -> MetadatosDC:
        """Inserta o actualiza la fila Dublin Core (sin commit)."""
        fila = db.get(MetadatosDC, id_crudo)
        if fila is None:
            fila = MetadatosDC(id_crudo=id_crudo, dc_title=valores["dc_title"] or "")
            db.add(fila)
        for clave in CLAVES_DC:
            setattr(fila, clave, valores.get(clave))
        return fila

    @staticmethod
    def obtener(db: Session, id_crudo: int) -> dict[str, str] | None:
        fila = db.get(MetadatosDC, id_crudo)
        if fila is None:
            return None
        return {clave: getattr(fila, clave) or "" for clave in CLAVES_DC}

    @staticmethod
    def eliminar(db: Session, id_crudo: int) -> bool:
        fila = db.get(MetadatosDC, id_crudo)
        if fila is None:
            return False
        db.delete(fila)
        return True

    @staticmethod
    def listar(db: Session, skip: int = 0, limit: int = 20) -> tuple[int, list[MetadatosDC]]:
        consulta = db.query(MetadatosDC).order_by(MetadatosDC.id_crudo)
        return consulta.count(), consulta.offset(skip).limit(limit).all()
