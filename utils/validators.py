from typing import Any


def validate_text(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("Text value cannot be empty")
    return normalized


def validate_number(value: str) -> int:
    normalized = value.strip()
    if not normalized:
        raise ValueError("Number value cannot be empty")

    try:
        return int(normalized)
    except ValueError as exc:
        raise ValueError("Please enter a valid integer") from exc


def validate_select(value: str, options: list[str]) -> str:
    if value not in options:
        raise ValueError("Selected option is invalid")
    return value


def validate_field_value(field: dict[str, Any], raw_value: str) -> Any:
    field_type = field["type"]

    if field_type == "text":
        return validate_text(raw_value)

    if field_type == "number":
        return validate_number(raw_value)

    if field_type == "select":
        options = field.get("options", [])
        return validate_select(raw_value, options)

    raise ValueError(f"Unsupported field type: {field_type}")
