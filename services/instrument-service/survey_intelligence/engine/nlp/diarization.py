# survey_intelligence/engine/nlp/diarization.py
"""
Diarización textual determinística (sin LLM).

A partir del texto de una entrevista con etiquetas de hablante, reconstruye:
  - la lista de participantes (rol + identificador estable),
  - los turnos de diálogo (quién habla, qué dice, y a qué pregunta responde).

Detecta etiquetas al inicio de línea del estilo:
    "Entrevistador:", "Entrevistado 2:", "E1:", "P3:", "Moderador:", "Sujeto 1 -"
La heurística es conservadora: si no hay etiquetas reconocibles, devuelve un único
participante 'entrevistado_01' con el texto completo como un turno (degradación segura).
"""
from __future__ import annotations

import re
import unicodedata

from survey_intelligence.contracts.interview import DialogueTurn, Participant

# Etiqueta de hablante al inicio de línea, terminada en ':' o ' -'.
# Captura el rótulo (grupo 1) y el resto de la línea (grupo 2).
_SPEAKER_LINE = re.compile(
    r"^\s*([A-Za-zÁÉÍÓÚÑáéíóúñ]+(?:\s+[A-Za-zÁÉÍÓÚÑáéíóúñ]+)?\s*\d*)\s*[:\-]\s+(.*)$"
)

# Rótulos que indican rol de entrevistador (tras normalizar a minúsculas sin tildes).
_ROLES_ENTREVISTADOR = {"entrevistador", "moderador", "investigador", "e"}
_ROLES_ENTREVISTADO = {"entrevistado", "participante", "sujeto", "informante", "p"}


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _classify_label(label: str) -> tuple[str, str]:
    """
    Dado un rótulo original (p.ej. 'Entrevistado 2', 'E1', 'P3'), devuelve
    (rol, clave_normalizada) donde rol ∈ {entrevistador, entrevistado} y la clave
    normalizada agrupa turnos del mismo hablante (p.ej. 'entrevistado_2').
    """
    base = _strip_accents(label).lower().strip()
    # Separar palabra base y número (si lo hay): 'entrevistado 2' -> ('entrevistado','2')
    m = re.match(r"^([a-z]+)\s*(\d*)$", base)
    palabra, numero = (m.group(1), m.group(2)) if m else (base, "")

    if palabra in _ROLES_ENTREVISTADOR:
        rol = "entrevistador"
    elif palabra in _ROLES_ENTREVISTADO:
        rol = "entrevistado"
    else:
        # Rótulo desconocido: se asume entrevistado (voz analizada).
        rol = "entrevistado"

    clave = f"{palabra}_{numero}" if numero else palabra
    return rol, clave


def diarize(text: str) -> tuple[list[Participant], list[DialogueTurn]]:
    """
    Reconstruye participantes y turnos a partir del texto etiquetado.

    Returns:
        (participants, turns). Determinístico y sin LLM.
    """
    lines = [ln for ln in text.replace("\r\n", "\n").split("\n")]

    # Estructuras de acumulación.
    # clave_normalizada -> (rol, participant_id, display_label)
    participantes: dict[str, tuple[str, str, str]] = {}
    contador_por_rol: dict[str, int] = {}
    turns: list[DialogueTurn] = []

    def _asignar_id(rol: str, clave: str, display: str) -> str:
        if clave in participantes:
            return participantes[clave][1]
        contador_por_rol[rol] = contador_por_rol.get(rol, 0) + 1
        pid = f"{rol}_{contador_por_rol[rol]:02d}"
        participantes[clave] = (rol, pid, display)
        return pid

    turn_id = 0
    last_question_by_anyone: int | None = None
    current_speaker: str | None = None
    current_buffer: list[str] = []
    current_display: str = ""

    def _flush() -> None:
        nonlocal turn_id, last_question_by_anyone
        if current_speaker is None or not current_buffer:
            return
        texto = " ".join(s.strip() for s in current_buffer).strip()
        if not texto:
            return
        rol, clave = _classify_label(current_speaker)
        pid = _asignar_id(rol, clave, current_display)
        es_pregunta = texto.rstrip().endswith("?") or rol == "entrevistador"
        turn_id += 1
        answers_to = None
        if not es_pregunta and last_question_by_anyone is not None:
            answers_to = last_question_by_anyone
        turns.append(DialogueTurn(
            turn_id=turn_id,
            speaker_id=pid,
            turn_type="pregunta" if es_pregunta else "respuesta",
            text=texto,
            answers_to=answers_to,
            char_len=len(texto),
            word_len=len(texto.split()),
        ))
        if es_pregunta:
            last_question_by_anyone = turn_id

    for ln in lines:
        m = _SPEAKER_LINE.match(ln)
        if m:
            # Nueva etiqueta de hablante: cerrar el turno anterior.
            _flush()
            current_display = m.group(1).strip()
            current_speaker = current_display
            current_buffer = [m.group(2)] if m.group(2) else []
        else:
            # Continuación del turno actual.
            if current_speaker is not None:
                current_buffer.append(ln)
    _flush()

    # Degradación segura: si no se detectó ninguna etiqueta, un único entrevistado.
    if not turns:
        texto = " ".join(l.strip() for l in lines if l.strip()).strip()
        if texto:
            pid = _asignar_id("entrevistado", "entrevistado", "Entrevistado")
            turns.append(DialogueTurn(
                turn_id=1, speaker_id=pid, turn_type="respuesta", text=texto,
                answers_to=None, char_len=len(texto), word_len=len(texto.split()),
            ))

    participants = [
        Participant(participant_id=pid, role=rol, display_label=display)
        for (rol, pid, display) in participantes.values()
    ]
    # Orden estable por participant_id.
    participants.sort(key=lambda p: p.participant_id)
    return participants, turns
