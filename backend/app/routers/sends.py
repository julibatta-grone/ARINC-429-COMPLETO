"""Creación, consulta y eliminación de envíos."""

import json
import sqlite3

from fastapi import APIRouter, HTTPException, Response, status

from backend.app.database import get_connection
from backend.app.models import Send, SendInput
from backend.app.services.arinc429 import (
    IncompleteConfiguration,
    UnrepresentableValue,
    generate_bnr_word,
)


router = APIRouter(prefix="/api/sends", tags=["sends"])


def _as_send(row: sqlite3.Row) -> Send:
    return Send.model_validate(dict(row))


def _validate_send(instrument: sqlite3.Row, value: float) -> tuple[str, str | None, str | None]:
    """Valida el rango y, cuando hay configuración, genera la palabra."""
    if not instrument["min_value"] <= value <= instrument["max_value"]:
        return (
            "rejected_range",
            None,
            f"El valor debe estar entre {instrument['min_value']} "
            f"y {instrument['max_value']}.",
        )
    if instrument["encoding_type"] != "BNR":
        return (
            "pending_configuration",
            None,
            f"El codificador {instrument['encoding_type']} aún no está "
            "implementado; no se generó una palabra.",
        )

    config = (
        json.loads(instrument["arinc_config"])
        if instrument["arinc_config"] is not None
        else None
    )
    try:
        return (
            "generated",
            generate_bnr_word(instrument["arinc_label"], value, config),
            None,
        )
    except IncompleteConfiguration as exc:
        return "pending_configuration", None, str(exc)
    except UnrepresentableValue as exc:
        return "rejected_encoding", None, str(exc)


@router.get("", response_model=list[Send])
def list_sends() -> list[Send]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT s.*, i.name AS instrument_name
            FROM sends AS s
            JOIN instruments AS i ON i.id = s.instrument_id
            ORDER BY s.sent_at DESC, s.id DESC
            """
        ).fetchall()
    return [_as_send(row) for row in rows]


@router.post("", response_model=Send, status_code=status.HTTP_201_CREATED)
def create_send(send: SendInput) -> Send:
    with get_connection() as connection:
        instrument = connection.execute(
            "SELECT * FROM instruments WHERE id = ?", (send.instrument_id,)
        ).fetchone()
        if instrument is None:
            raise HTTPException(status_code=404, detail="Instrumento no encontrado.")

        validation_status, generated_word, details = _validate_send(
            instrument, send.value
        )

        cursor = connection.execute(
            """
            INSERT INTO sends
                (instrument_id, value, validation_status, generated_word, details)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                send.instrument_id,
                send.value,
                validation_status,
                generated_word,
                details,
            ),
        )
        row = connection.execute(
            """
            SELECT s.*, i.name AS instrument_name
            FROM sends AS s
            JOIN instruments AS i ON i.id = s.instrument_id
            WHERE s.id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
    return _as_send(row)


@router.put("/{send_id}", response_model=Send)
def update_send(send_id: int, send: SendInput) -> Send:
    with get_connection() as connection:
        instrument = connection.execute(
            "SELECT * FROM instruments WHERE id = ?", (send.instrument_id,)
        ).fetchone()
        if instrument is None:
            raise HTTPException(status_code=404, detail="Instrumento no encontrado.")

        validation_status, generated_word, details = _validate_send(
            instrument, send.value
        )
        cursor = connection.execute(
            """
            UPDATE sends
            SET instrument_id = ?, value = ?, sent_at = CURRENT_TIMESTAMP,
                validation_status = ?, generated_word = ?, details = ?
            WHERE id = ?
            """,
            (
                send.instrument_id,
                send.value,
                validation_status,
                generated_word,
                details,
                send_id,
            ),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Envío no encontrado.")
        row = connection.execute(
            """
            SELECT s.*, i.name AS instrument_name
            FROM sends AS s
            JOIN instruments AS i ON i.id = s.instrument_id
            WHERE s.id = ?
            """,
            (send_id,),
        ).fetchone()
    return _as_send(row)


@router.delete("/{send_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_send(send_id: int) -> Response:
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM sends WHERE id = ?", (send_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Envío no encontrado.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
