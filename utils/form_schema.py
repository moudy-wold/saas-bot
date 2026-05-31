from typing import Any

ALLOWED_FIELD_TYPES = {"text", "number", "select"}


def validate_form_config(form: dict[str, Any]) -> dict[str, Any]:
    form_id = form.get("id")
    fields = form.get("fields")

    if not isinstance(form_id, str) or not form_id.strip():
        raise ValueError("Form id is required and must be a non-empty string")

    if not isinstance(fields, list) or not fields:
        raise ValueError("Form fields are required and must be a non-empty list")

    validated_fields: list[dict[str, Any]] = []

    for index, field in enumerate(fields):
        if not isinstance(field, dict):
            raise ValueError(f"Field at index {index} must be an object")

        name = field.get("name")
        field_type = field.get("type")
        label = field.get("label")

        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Field at index {index} has invalid name")

        if field_type not in ALLOWED_FIELD_TYPES:
            raise ValueError(
                f"Field '{name}' has invalid type. Allowed: text, number, select"
            )

        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"Field '{name}' has invalid label")

        normalized_field: dict[str, Any] = {
            "name": name.strip(),
            "type": field_type,
            "label": label.strip(),
        }

        if field_type == "select":
            options = field.get("options")
            if not isinstance(options, list) or not options:
                raise ValueError(f"Field '{name}' must include non-empty options list")

            cleaned_options: list[str] = []
            for option in options:
                if not isinstance(option, str) or not option.strip():
                    raise ValueError(
                        f"Field '{name}' contains invalid option. All options must be non-empty strings"
                    )
                cleaned_options.append(option.strip())

            normalized_field["options"] = cleaned_options

        validated_fields.append(normalized_field)

    return {
        "id": form_id.strip(),
        "fields": validated_fields,
    }
