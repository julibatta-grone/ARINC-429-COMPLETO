"""Pruebas del codificador BNR ARINC 429."""

import unittest

from backend.app.services.arinc429 import (
    IncompleteConfiguration,
    UnrepresentableValue,
    generate_bnr_word,
)


VALID_CONFIG = {
    "sdi": 0,
    "ssm": 0,
    "resolution": 1.0,
    "offset": 0.0,
    "sign_mode": "twos_complement",
}


class GenerateBnrWordTests(unittest.TestCase):
    def test_generates_exactly_32_bits_with_odd_parity(self) -> None:
        word = generate_bnr_word("203", 0, VALID_CONFIG)

        self.assertEqual(len(word), 32)
        self.assertEqual(set(word), {"0", "1"})
        self.assertEqual(word.count("1") % 2, 1)

    def test_uses_explicit_sign_representation(self) -> None:
        word = generate_bnr_word(
            "203",
            -1,
            {**VALID_CONFIG, "sign_mode": "sign_magnitude"},
        )

        self.assertEqual(len(word), 32)
        self.assertEqual(word.count("1") % 2, 1)

    def test_missing_configuration_is_reported(self) -> None:
        with self.assertRaises(IncompleteConfiguration):
            generate_bnr_word("203", 10, None)

    def test_value_must_match_configured_resolution(self) -> None:
        with self.assertRaises(UnrepresentableValue):
            generate_bnr_word("203", 0.5, VALID_CONFIG)

    def test_invalid_octal_label_is_not_accepted_by_encoder(self) -> None:
        with self.assertRaises(ValueError):
            generate_bnr_word("888", 0, VALID_CONFIG)


if __name__ == "__main__":
    unittest.main()
