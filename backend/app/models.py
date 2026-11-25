"""Modelos de validación de la API."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


EncodingType = Literal["BNR", "BCD", "DISCRETE", "CUSTOM"]


class InstrumentInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    arinc_label: str = Field(min_length=1, max_length=3)
    min_value: float = Field(allow_inf_nan=False)
    max_value: float = Field(allow_inf_nan=False)
    encoding_type: EncodingType
    arinc_config: dict[str, Any] | None = None

    @field_validator("arinc_label")
    @classmethod
    def validate_octal_label(cls, value: str) -> str:
        if not value.isdigit() or any(character not in "01234567" for character in value):
            raise ValueError("La etiqueta debe ser un número octal de 1 a 3 dígitos.")
        if int(value, 8) > 0o377:
            raise ValueError("La etiqueta octal debe estar entre 000 y 377.")
        return value

    @model_validator(mode="after")
    def validate_range(self) -> "InstrumentInput":
        if self.min_value > self.max_value:
            raise ValueError("El valor mínimo no puede superar al valor máximo.")
        return self


class Instrument(InstrumentInput):
    id: int
    created_at: str


class SendInput(BaseModel):
    instrument_id: int = Field(gt=0)
    value: float = Field(allow_inf_nan=False)


class Send(BaseModel):
    id: int
    instrument_id: int
    instrument_name: str
    value: float
    sent_at: str
    validation_status: str
    generated_word: str | None
    details: str | None
