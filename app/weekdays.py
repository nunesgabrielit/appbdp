"""Dias da semana no padrão unificado 1-7.

Padrão:
1=segunda-feira ... 7=domingo (ISO-8601 / EXTRACT(ISODOW) no PostgreSQL).
"""

from __future__ import annotations

import re
import unicodedata


WEEKDAY_INT_TO_NAME_PT: dict[int, str] = {
    1: "Segunda-feira",
    2: "Terça-feira",
    3: "Quarta-feira",
    4: "Quinta-feira",
    5: "Sexta-feira",
    6: "Sábado",
    7: "Domingo",
}

WEEKDAY_NAME_TO_INT_PT: dict[str, int] = {
    "segunda": 1,
    "terca": 2,
    "terça": 2,
    "quarta": 3,
    "quinta": 4,
    "sexta": 5,
    "sabado": 6,
    "sábado": 6,
    "domingo": 7,
}


def weekday_int_to_name(day: int) -> str:
    try:
        return WEEKDAY_INT_TO_NAME_PT[int(day)]
    except Exception as exc:
        raise ValueError("Dia da semana inválido. Use 1-7 (1=segunda ... 7=domingo).") from exc


def weekday_name_to_int(name: str) -> int:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Nome do dia da semana inválido.")

    normalized = name.strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = normalized.replace("-feira", "")
    normalized = normalized.replace(" feira", "")

    if normalized in WEEKDAY_NAME_TO_INT_PT:
        return WEEKDAY_NAME_TO_INT_PT[normalized]

    ascii_normalized = (
        unicodedata.normalize("NFKD", normalized)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    if ascii_normalized in WEEKDAY_NAME_TO_INT_PT:
        return WEEKDAY_NAME_TO_INT_PT[ascii_normalized]

    raise ValueError("Nome do dia da semana inválido. Exemplos: segunda, terça, domingo.")


def validate_weekday_int(day: int) -> int:
    if not isinstance(day, int):
        raise ValueError("Dia da semana inválido. Use inteiro 1-7.")
    if day < 1 or day > 7:
        raise ValueError("Dia da semana inválido. Use 1-7 (1=segunda ... 7=domingo).")
    return day
