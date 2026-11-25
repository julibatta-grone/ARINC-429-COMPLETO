"""Operaciones CRUD de instrumentos."""

import json
import sqlite3

from fastapi import APIRouter, HTTPException, Response, status

from backend.app.database import get_connection
from backend.app.models import Instrument, InstrumentInput


router = APIRouter(prefix="/api/instruments", tags=["instruments"])


def _as_instrument(row: sqlite3.Row) -> Instrument:
    data = dict(row)
    data["arinc_config"] = (
        json.loads(data["arinc_config"]) if data["arinc_config"] is not None else None
    )
    return Instrument.model_validate(data)


@router.get("", response_model=list[Instrument])
def list_instruments() -> list[Instrument]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM instruments ORDER BY name COLLATE NOCASE"
        ).fetchall()
    return [_as_instrument(row) for row in rows]


@router.post("", response_model=Instrument, status_code=status.HTTP_201_CREATED)
def create_instrument(instrument: InstrumentInput) -> Instrument:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO instruments
                (name, arinc_label, min_value, max_value, encoding_type, arinc_config)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                instrument.name,
                instrument.arinc_label,
                instrument.min_value,
                instrument.max_value,
                instrument.encoding_type,
                json.dumps(instrument.arinc_config)
                if instrument.arinc_config is not None
                else None,
            ),
        )
        row = connection.execute(
            "SELECT * FROM instruments WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    return _as_instrument(row)


@router.put("/{instrument_id}", response_model=Instrument)
def update_instrument(instrument_id: int, instrument: InstrumentInput) -> Instrument:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE instruments
            SET name = ?, arinc_label = ?, min_value = ?, max_value = ?,
                encoding_type = ?, arinc_config = ?
            WHERE id = ?
            """,
            (
                instrument.name,
                instrument.arinc_label,
                instrument.min_value,
                instrument.max_value,
                instrument.encoding_type,
                json.dumps(instrument.arinc_config)
                if instrument.arinc_config is not None
                else None,
                instrument_id,
            ),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Instrumento no encontrado.")
        row = connection.execute(
            "SELECT * FROM instruments WHERE id = ?", (instrument_id,)
        ).fetchone()
    return _as_instrument(row)


@router.delete("/{instrument_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_instrument(instrument_id: int) -> Response:
    with get_connection() as connection:
        try:
            cursor = connection.execute(
                "DELETE FROM instruments WHERE id = ?", (instrument_id,)
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(
                status_code=409,
                detail="No se puede eliminar: el instrumento tiene envíos asociados.",
            ) from exc
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Instrumento no encontrado.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
