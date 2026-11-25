"""Pruebas del flujo de validación y persistencia de envíos."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from backend.app.models import InstrumentInput, SendInput
from backend.app.routers.instruments import create_instrument, delete_instrument
from backend.app.routers.sends import create_send, update_send


VALID_CONFIG = {
    "sdi": 0,
    "ssm": 0,
    "resolution": 1.0,
    "offset": 0.0,
    "sign_mode": "twos_complement",
}


class SendWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "test.sqlite"
        self.database_patch = patch(
            "backend.app.database.DATABASE_PATH", self.database_path
        )
        self.database_patch.start()
        from backend.app.database import initialize_database

        initialize_database()

    def tearDown(self) -> None:
        self.database_patch.stop()
        self.temp_dir.cleanup()

    def create_instrument(self, config: dict | None = None):
        return create_instrument(
            InstrumentInput(
                name="Instrumento de prueba",
                arinc_label="203",
                min_value=-10,
                max_value=10,
                encoding_type="BNR",
                arinc_config=config,
            )
        )

    def test_in_range_without_configuration_is_saved_as_pending(self) -> None:
        instrument = self.create_instrument()

        send = create_send(SendInput(instrument_id=instrument.id, value=4))

        self.assertEqual(send.validation_status, "pending_configuration")
        self.assertIsNone(send.generated_word)

    def test_out_of_range_value_is_rejected_without_word(self) -> None:
        instrument = self.create_instrument(VALID_CONFIG)

        send = create_send(SendInput(instrument_id=instrument.id, value=11))

        self.assertEqual(send.validation_status, "rejected_range")
        self.assertIsNone(send.generated_word)

    def test_in_range_configured_value_generates_a_32_bit_word(self) -> None:
        instrument = self.create_instrument(VALID_CONFIG)

        send = create_send(SendInput(instrument_id=instrument.id, value=4))

        self.assertEqual(send.validation_status, "generated")
        self.assertEqual(len(send.generated_word), 32)
        self.assertEqual(send.generated_word.count("1") % 2, 1)

    def test_editing_send_revalidates_its_value(self) -> None:
        instrument = self.create_instrument(VALID_CONFIG)
        send = create_send(SendInput(instrument_id=instrument.id, value=4))

        updated = update_send(
            send.id,
            SendInput(instrument_id=instrument.id, value=11),
        )

        self.assertEqual(updated.validation_status, "rejected_range")
        self.assertIsNone(updated.generated_word)
        self.assertEqual(updated.value, 11)

    def test_instrument_with_history_cannot_be_deleted(self) -> None:
        instrument = self.create_instrument()
        create_send(SendInput(instrument_id=instrument.id, value=4))

        with self.assertRaises(HTTPException) as raised:
            delete_instrument(instrument.id)

        self.assertEqual(raised.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()
