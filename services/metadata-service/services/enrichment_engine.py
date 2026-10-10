"""Metadatos enriquecidos según el tipo de instrumento.

Después del Dublin Core, cada instrumento se completa con los metadatos de su
tipo (tablas `metadatos_enriquecidos_encuestas | _entrevistas | _pruebas`). El
motor propone los valores faltantes a partir del análisis del contenido y, si
está habilitado, del LLM local; el autor los revisa y aprueba junto con el
Dublin Core.

Tipos de dato (ver services/campos.py):
  - entero: int ≥ 0          - lista: JSONB list[str] (texto separado por comas)
  - mapa:   JSONB {sección: nº} (texto «Sección: 10» por línea o JSON)
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from services.analizador import Analisis
from services.campos import TABLA_POR_TIPO, Campo, campos_de


def _vacio(valor: Any) -> bool:
    return valor is None or valor == "" or valor == [] or valor == {}


def _a_entero(valor: Any) -> int | None | str:
    """int, None si está vacío, o el texto original si no es un número válido."""
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return None
    if isinstance(valor, bool):
        return str(valor)
    if isinstance(valor, int):
        return valor
    if isinstance(valor, float) and valor.is_integer():
        return int(valor)
    texto = str(valor).strip().replace(",", "").replace(" ", "")
    return int(texto) if re.fullmatch(r"-?\d+", texto) else str(valor)


def _a_lista(valor: Any) -> list[str] | None:
    if valor is None:
        return None
    if isinstance(valor, (list, tuple)):
        elementos = [str(v).strip() for v in valor]
    else:
        elementos = re.split(r"[,;\n]", str(valor))
    elementos = [e.strip() for e in elementos if e and e.strip()]
    return elementos or None


def _a_mapa(valor: Any) -> dict[str, Any] | None | str:
    if valor is None:
        return None
    if isinstance(valor, dict):
        datos = valor
    else:
        texto = str(valor).strip()
        if not texto:
            return None
        try:
            datos = json.loads(texto)
        except json.JSONDecodeError:
            datos = {}
            for linea in re.split(r"[\n;]", texto):
                if not linea.strip():
                    continue
                if ":" not in linea:
                    return texto  # formato inválido: lo reporta validar()
                clave, _, numero = linea.rpartition(":")
                datos[clave.strip()] = numero.strip()
        if not isinstance(datos, dict):
            return texto
    salida: dict[str, Any] = {}
    for clave, numero in datos.items():
        entero = _a_entero(numero)
        salida[str(clave).strip()] = entero if isinstance(entero, int) else str(numero).strip()
    return salida or None


def _normalizar_valor(campo: Campo, valor: Any) -> Any:
    if campo.tipo == "entero":
        return _a_entero(valor)
    if campo.tipo == "lista":
        return _a_lista(valor)
    if campo.tipo == "mapa":
        return _a_mapa(valor)
    if isinstance(valor, (list, tuple)):
        valor = ", ".join(str(v).strip() for v in valor if str(v).strip())
    texto = "" if valor is None else str(valor).strip()
    return texto or None


class EnrichmentEngine:
    """Lógica de negocio de los metadatos específicos por tipo."""

    @staticmethod
    def proponer(
        raw: Any, analisis: Analisis, dc_valores: dict[str, str]
    ) -> tuple[dict[str, Any], dict[str, str]]:
        tipo = (raw.tipo_instrumento or "").lower()
        campos = campos_de(tipo)
        h = analisis.hallazgos
        valores: dict[str, Any] = {c.clave: None for c in campos}
        origen: dict[str, str] = {}

        def poner(clave: str, valor: Any, fuente: str) -> None:
            if clave in valores and _vacio(valores[clave]) and not _vacio(valor):
                valores[clave], origen[clave] = valor, fuente

        # 1) Lo que el propio archivo ya declara (JSON de la demo).
        for clave, valor in analisis.especificos_archivo.items():
            poner(clave, valor, "archivo")

        # 2) Inferido del contenido.
        if tipo == "encuesta":
            poner("n_respondentes", analisis.n_registros, "inferido")
            poner("objetivo", h.get("objetivo"), "inferido")
            poner("carrera", ", ".join(analisis.carreras[:5]), "inferido")
            poner("poblacion_objetivo", h.get("poblacion"), "inferido")
            poner("palabras_clave", analisis.palabras_clave[:8], "inferido")
            poner("dimensiones", analisis.dimensiones, "inferido")
            notas = []
            if analisis.n_registros is not None:
                notas.append(f"{analisis.n_registros} registros con respuesta")
            if analisis.n_duplicados:
                notas.append(f"{analisis.n_duplicados} registros duplicados")
            if analisis.pct_vacios is not None:
                notas.append(f"{analisis.pct_vacios:.0%} de respuestas vacías")
            if notas:
                poner("notas_contextuales", "Calidad de los datos: " + "; ".join(notas) + ".", "inferido")
        elif tipo == "entrevista":
            poner("identificador_propio", Path(raw.nombre_archivo or "").stem, "automatico")
            poner("objetivo", h.get("objetivo"), "inferido")
            poner("metodologia", h.get("metodologia"), "inferido")
            poner("institucion", h.get("institucion"), "inferido")
            poner("derechos", dc_valores.get("dc_rights"), "inferido")
        elif tipo == "prueba_estandarizada":
            for clave in (
                "unidad_de_aprendizaje", "mapeo_de_reactivos_por_seccion", "institucion", "campus", "grado",
                "grupo", "ciclo_escolar", "tipo_de_prueba", "version", "taxonomia_bloom", "nivel_educativo",
                "subareas", "competencias",
            ):
                poner(clave, h.get(clave), "inferido")
            poner("objetivo_de_evaluacion", h.get("objetivo"), "inferido")
        return valores, origen

    @staticmethod
    def normalizar(tipo: str, payload: dict[str, Any] | None) -> dict[str, Any]:
        datos = payload or {}
        return {c.clave: _normalizar_valor(c, datos.get(c.clave)) for c in campos_de(tipo)}

    @staticmethod
    def validar(tipo: str, valores: dict[str, Any]) -> dict[str, str]:
        errores: dict[str, str] = {}
        for campo in campos_de(tipo):
            valor = valores.get(campo.clave)
            if campo.tipo == "entero" and isinstance(valor, str):
                errores[campo.clave] = f"«{campo.etiqueta}» debe ser un número entero."
            elif campo.tipo == "entero" and isinstance(valor, int) and valor < 0:
                errores[campo.clave] = f"«{campo.etiqueta}» no puede ser negativo."
            elif campo.tipo == "mapa" and isinstance(valor, str):
                errores[campo.clave] = f"«{campo.etiqueta}»: escribe una línea por sección con el formato «Sección: número»."
            elif campo.requerido and _vacio(valor):
                errores[campo.clave] = f"«{campo.etiqueta}» es obligatorio."
        n_resp, n_pob = valores.get("n_respondentes"), valores.get("n_poblacion")
        if isinstance(n_resp, int) and isinstance(n_pob, int) and n_pob < n_resp:
            errores["n_poblacion"] = "La población no puede ser menor que el número de respondentes."
        return errores

    @staticmethod
    def guardar(db: Session, tipo: str, id_crudo: int, valores: dict[str, Any]) -> Any:
        """Inserta o actualiza la fila del tipo correspondiente (sin commit)."""
        modelo = TABLA_POR_TIPO[tipo]
        fila = db.get(modelo, id_crudo)
        if fila is None:
            fila = modelo(id_crudo=id_crudo)
            db.add(fila)
        for campo in campos_de(tipo):
            setattr(fila, campo.clave, valores.get(campo.clave))
        return fila

    @staticmethod
    def obtener(db: Session, tipo: str, id_crudo: int) -> dict[str, Any] | None:
        modelo = TABLA_POR_TIPO.get(tipo)
        fila = db.get(modelo, id_crudo) if modelo else None
        if fila is None:
            return None
        return {c.clave: getattr(fila, c.clave) for c in campos_de(tipo)}

    @staticmethod
    def eliminar(db: Session, tipo: str, id_crudo: int) -> bool:
        modelo = TABLA_POR_TIPO.get(tipo)
        fila = db.get(modelo, id_crudo) if modelo else None
        if fila is None:
            return False
        db.delete(fila)
        return True
