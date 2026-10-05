"""Parser documental — extrae texto plano de PDF, DOCX y TXT.

Para instrumentos narrativos (entrevistas, pruebas estandarizadas). Devuelve el
texto extraído y metadatos básicos (nº de páginas/párrafos). No interpreta ni
segmenta el contenido: eso es trabajo de etapas posteriores, fuera del alcance de
la carga. Autocontenido: sin dependencias de survey_intelligence.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field

_ENCODINGS = ("utf-8-sig", "utf-8", "cp1252", "latin-1")


class DocumentParseError(Exception):
    """El contenido no pudo interpretarse como documento de texto."""


@dataclass(frozen=True)
class ExtractedDocument:
    """Texto extraído de un documento + metadatos de lectura.

    Attributes:
        text:     Texto plano extraído.
        n_pages:  Nº de páginas (PDF) o None si no aplica.
        encoding: Codificación detectada (solo TXT) o None.
        notes:    Observaciones del parser.
    """

    text: str
    n_pages: int | None = None
    encoding: str | None = None
    notes: list[str] = field(default_factory=list)


def _read_txt(data: bytes) -> ExtractedDocument:
    last_error: Exception | None = None
    for enc in _ENCODINGS:
        try:
            text = data.decode(enc)
            notes = [] if enc in ("utf-8-sig", "utf-8") else [f"Codificación de respaldo: {enc}"]
            return ExtractedDocument(text=text, n_pages=None, encoding=enc, notes=notes)
        except UnicodeDecodeError as exc:
            last_error = exc
    raise DocumentParseError(f"No se pudo decodificar el TXT: {last_error}")


def _read_pdf(data: bytes) -> ExtractedDocument:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise DocumentParseError("pypdf no está disponible.") from exc

    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:
        raise DocumentParseError(f"No se pudo abrir el PDF: {exc}") from exc

    if reader.is_encrypted:
        # Intento de desbloqueo con contraseña vacía (PDFs "protegidos" sin clave).
        try:
            reader.decrypt("")
        except Exception as exc:
            raise DocumentParseError("El PDF está cifrado y requiere contraseña.") from exc

    parts: list[str] = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            parts.append("")

    text = "\n".join(parts).strip()
    notes: list[str] = []
    if not text:
        notes.append("No se extrajo texto (posible PDF escaneado sin OCR).")
    return ExtractedDocument(text=text, n_pages=len(reader.pages), encoding=None, notes=notes)


def _read_docx(data: bytes) -> ExtractedDocument:
    try:
        import docx  # python-docx
    except ImportError as exc:  # pragma: no cover
        raise DocumentParseError("python-docx no está disponible.") from exc

    try:
        document = docx.Document(io.BytesIO(data))
    except Exception as exc:
        raise DocumentParseError(f"No se pudo abrir el DOCX: {exc}") from exc

    paragraphs = [p.text for p in document.paragraphs if p.text and p.text.strip()]

    # También recoge el texto de las tablas (cuestionarios en formato tabla).
    for table in document.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text and c.text.strip()]
            if cells:
                paragraphs.append(" | ".join(cells))

    text = "\n".join(paragraphs).strip()
    notes: list[str] = []
    if not text:
        notes.append("El documento no contiene texto.")
    return ExtractedDocument(text=text, n_pages=None, encoding=None, notes=notes)


def read_document(data: bytes, extension: str) -> ExtractedDocument:
    """Extrae texto de un documento según su extensión (.pdf/.txt/.docx)."""
    if not data:
        raise DocumentParseError("El documento está vacío.")

    ext = extension.lower()
    if ext == ".pdf":
        return _read_pdf(data)
    if ext == ".txt":
        return _read_txt(data)
    if ext == ".docx":
        return _read_docx(data)
    raise DocumentParseError(f"Extensión de documento no soportada: {extension}")
