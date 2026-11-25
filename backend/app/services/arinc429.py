"""Generación configurable de palabras ARINC 429 para codificación BNR."""

from typing import Any


class IncompleteConfiguration(ValueError):
    """La configuración del instrumento no alcanza para generar una palabra."""


class UnrepresentableValue(ValueError):
    """El valor no puede representarse con la resolución configurada."""


def _required_number(config: dict[str, Any], key: str) -> float:
    value = config.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise IncompleteConfiguration(f"Falta un valor numérico válido para '{key}'.")
    return float(value)


def _unsigned_field(value: Any, key: str, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
        raise IncompleteConfiguration(f"'{key}' debe ser un entero entre 0 y {maximum}.")
    return value


def _reverse_eight_bits(value: int) -> int:
    result = 0
    for bit_index in range(8):
        result |= ((value >> bit_index) & 1) << (7 - bit_index)
    return result


def generate_bnr_word(
    label_octal: str,
    value: float,
    config: dict[str, Any] | None,
) -> str:
    """Codifica label, SDI, datos BNR, SSM y paridad impar como 32 bits."""
    if config is None:
        raise IncompleteConfiguration("La configuración ARINC del instrumento está vacía.")
    if not isinstance(config, dict):
        raise IncompleteConfiguration("La configuración ARINC debe ser un objeto JSON.")

    sdi = _unsigned_field(config.get("sdi"), "sdi", 3)
    ssm = _unsigned_field(config.get("ssm"), "ssm", 3)
    resolution = _required_number(config, "resolution")
    offset = _required_number(config, "offset")
    sign_mode = config.get("sign_mode")

    if resolution <= 0:
        raise IncompleteConfiguration("'resolution' debe ser mayor que cero.")
    if sign_mode not in {"twos_complement", "sign_magnitude"}:
        raise IncompleteConfiguration(
            "'sign_mode' debe ser 'twos_complement' o 'sign_magnitude'."
        )

    scaled_value = (value - offset) / resolution
    integer_value = round(scaled_value)
    if abs(scaled_value - integer_value) > 1e-9:
        raise UnrepresentableValue(
            "El valor no coincide con la resolución configurada."
        )

    data_width = 19
    sign_bit = 1 << (data_width - 1)
    magnitude_limit = sign_bit - 1
    if sign_mode == "twos_complement":
        if not -sign_bit <= integer_value <= magnitude_limit:
            raise UnrepresentableValue(
                "El valor codificado excede el rango BNR de 19 bits."
            )
        data = integer_value & ((1 << data_width) - 1)
    else:
        if abs(integer_value) > magnitude_limit:
            raise UnrepresentableValue(
                "La magnitud excede el rango BNR de 19 bits."
            )
        data = abs(integer_value)
        if integer_value < 0:
            data |= sign_bit

    label = int(label_octal, 8)
    word = _reverse_eight_bits(label)
    word |= sdi << 8
    word |= data << 10
    word |= ssm << 29

    if word.bit_count() % 2 == 0:
        word |= 1 << 31

    return f"{word:032b}"
