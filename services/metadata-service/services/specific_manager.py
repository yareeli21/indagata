"""
Specific Metadata Manager - Core Business Logic (Bug 2)

Maneja los METADATOS ESPECÍFICOS POR TIPO del instrumento (paso 4 del wizard).

A diferencia de Dublin Core (`DCManager`, inmutable), estos metadatos son
EDITABLES: se hace UPSERT por `id_crudo` sobre el modelo del tipo. Reutiliza los
modelos ORM que YA EXISTEN en `shared/models/`:
- encuesta             -> MetadatosEnriquecidosEncuestas
- entrevista           -> MetadatosEnriquecidosEntrevistas
- prueba_estandarizada -> MetadatosEnriquecidosPruebas

Fuente de contratos: design.md §6.
"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status
import logging

from shared.models import (
    MetadatosEnriquecidosEncuestas,
    MetadatosEnriquecidosEntrevistas,
    MetadatosEnriquecidosPruebas,
)

logger = logging.getLogger(__name__)


# Mapa tipo (raw_data.tipo_instrumento) -> modelo ORM existente.
_MODELO_POR_TIPO = {
    "encuesta": MetadatosEnriquecidosEncuestas,
    "entrevista": MetadatosEnriquecidosEntrevistas,
    "prueba_estandarizada": MetadatosEnriquecidosPruebas,
}

# Campos que son enteros >= 0 (NULL si vacío). El resto se persiste tal cual.
_CAMPOS_ENTEROS = {"n_respondentes", "n_poblacion"}

# Campos JSONB: lista/objeto (NULL si string vacío). El resto es texto.
_CAMPOS_JSON = {"palabras_clave", "dimensiones", "mapeo_de_reactivos_por_seccion"}


def _columnas_del_modelo(modelo) -> set[str]:
    """Columnas persistibles del modelo, excluyendo la PK id_crudo."""
    return {c.name for c in modelo.__table__.columns if c.name != "id_crudo"}


def _coaccionar_entero(campo: str, valor) -> int | None:
    """Entero >= 0 o None (422 si no parsea / negativo)."""
    if valor is None:
        return None
    if isinstance(valor, str) and valor.strip() == "":
        return None
    if isinstance(valor, bool):
        # bool es subclase de int; no es un entero válido aquí.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"El campo '{campo}' debe ser un entero >= 0.",
        )
    try:
        n = int(valor)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"El campo '{campo}' debe ser un entero >= 0.",
        )
    if n < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"El campo '{campo}' debe ser un entero >= 0.",
        )
    return n


def _coaccionar_json(campo: str, valor):
    """Lista/objeto JSON o None. String vacío -> None.

    Un escalar imposible (int/float/bool suelto) para un campo que debe ser
    lista/objeto -> 422.
    """
    if valor is None:
        return None
    if isinstance(valor, str):
        if valor.strip() == "":
            return None
        # String no vacío: se guarda como lista de un elemento (tolerante).
        return [valor]
    if isinstance(valor, (list, dict)):
        return valor
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"El campo '{campo}' debe ser una lista u objeto.",
    )


def _coaccionar_texto(valor) -> str | None:
    """String no vacío o None (string vacío -> NULL)."""
    if valor is None:
        return None
    if isinstance(valor, str):
        return valor if valor.strip() != "" else None
    # Cualquier otro escalar se serializa a texto.
    return str(valor)


class SpecificMetadataManager:
    """Lógica de negocio para metadatos específicos por tipo (UPSERT)."""

    @staticmethod
    def upsert(db: Session, instrumento_id: int, tipo: str, campos: dict) -> dict:
        """UPSERT de metadatos específicos del tipo por `id_crudo`.

        - Resuelve `id_crudo` desde `instrumento_id` (= id_instrumento) vía
          InstrumentoProcesado (404 si no existe).
        - Valida `tipo` contra `raw_data.tipo_instrumento` (409 si no coincide).
        - Persiste solo los campos presentes/no vacíos (los ausentes quedan NULL).
        - Rollback + 500 ante SQLAlchemyError.
        """
        from shared.models.instrumento_procesado import InstrumentoProcesado
        from shared.models.raw_data import RawData

        # 1. Resolver instrumento (PK real: id_instrumento).
        instrumento = db.query(InstrumentoProcesado).filter(
            InstrumentoProcesado.id_instrumento == instrumento_id
        ).first()

        if not instrumento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Instrumento {instrumento_id} no encontrado.",
            )

        # 2. tipo real del instrumento vive en raw_data (via id_crudo).
        raw = db.query(RawData).filter(
            RawData.id_crudo == instrumento.id_crudo
        ).first()
        tipo_real = raw.tipo_instrumento if raw else None

        # 3. Validar el tipo recibido contra el tipo real.
        if tipo not in _MODELO_POR_TIPO:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Tipo inválido. Debe ser uno de: "
                    "encuesta, entrevista, prueba_estandarizada."
                ),
            )

        if tipo_real is not None and tipo != tipo_real:
            logger.warning(
                "Tipo '%s' no coincide con el instrumento %s (real: '%s')",
                tipo, instrumento_id, tipo_real,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El tipo no coincide con el instrumento.",
            )

        modelo = _MODELO_POR_TIPO[tipo]
        columnas = _columnas_del_modelo(modelo)
        campos = campos or {}

        # 4. Coaccionar solo los campos presentes y válidos para este modelo.
        valores: dict = {}
        for nombre, valor in campos.items():
            if nombre not in columnas:
                # Campo desconocido para este tipo: se ignora.
                continue
            if nombre in _CAMPOS_ENTEROS:
                valores[nombre] = _coaccionar_entero(nombre, valor)
            elif nombre in _CAMPOS_JSON:
                valores[nombre] = _coaccionar_json(nombre, valor)
            else:
                valores[nombre] = _coaccionar_texto(valor)

        # 5. UPSERT por id_crudo.
        try:
            fila = db.query(modelo).filter(
                modelo.id_crudo == instrumento.id_crudo
            ).first()

            if fila is None:
                fila = modelo(id_crudo=instrumento.id_crudo, **valores)
                db.add(fila)
            else:
                for nombre, valor in valores.items():
                    setattr(fila, nombre, valor)

            db.commit()
            db.refresh(fila)
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(
                "Error al persistir metadatos específicos del instrumento %s: %s",
                instrumento_id, e,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se pudieron guardar los metadatos específicos.",
            )

        logger.info(
            "✅ Metadatos específicos (%s) guardados para instrumento %s",
            tipo, instrumento_id,
        )

        # 6. Respuesta: campos persistidos + instrumento_id + mensaje.
        persistidos = {col: getattr(fila, col) for col in columnas}
        return {
            "instrumento_id": instrumento_id,
            "tipo": tipo,
            "campos": persistidos,
            "mensaje": "Metadatos específicos guardados correctamente.",
        }
