import json
from pathlib import Path
from threading import RLock
from typing import Any

from config import DEFAULT_SETTINGS
from utils.form_schema import validate_form_config
from utils.security import verify_password


class SettingsManager:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._lock = RLock()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_file()

    def _ensure_file(self) -> None:
        if self._path.exists():
            return

        with self._path.open("w", encoding="utf-8") as file:
            json.dump(DEFAULT_SETTINGS, file, ensure_ascii=True, indent=2)

    def _read(self) -> dict[str, Any]:
        with self._path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError("Settings file content must be an object")

        merged = self._merge_with_defaults(data)
        if merged != data:
            self._write(merged)
            return merged

        return data

    def _merge_with_defaults(self, data: dict[str, Any]) -> dict[str, Any]:
        merged = dict(data)

        for key, default_value in DEFAULT_SETTINGS.items():
            if key not in merged:
                merged[key] = default_value
                continue

            if isinstance(default_value, dict) and isinstance(merged[key], dict):
                nested_merged = dict(merged[key])
                for nested_key, nested_default in default_value.items():
                    if nested_key not in nested_merged:
                        nested_merged[nested_key] = nested_default
                merged[key] = nested_merged

        return merged

    def _write(self, data: dict[str, Any]) -> None:
        with self._path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=True, indent=2)

    def get_settings(self) -> dict[str, Any]:
        with self._lock:
            return self._read()

    def get_bot_token(self) -> str:
        settings = self.get_settings()
        token = settings.get("bot_token", "")
        return token if isinstance(token, str) else ""

    def get_webhook_url(self) -> str:
        settings = self.get_settings()
        url = settings.get("webhook_url", "")
        return url if isinstance(url, str) else ""

    def get_active_form(self) -> dict[str, Any]:
        settings = self.get_settings()
        form = settings.get("form")
        if not isinstance(form, dict):
            raise ValueError("Form settings are missing")
        return form

    def verify_admin_credentials(self, username: str, password: str) -> bool:
        settings = self.get_settings()
        admin = settings.get("admin", {})
        if not isinstance(admin, dict):
            return False

        expected_username = admin.get("username", "")
        expected_password_hash = admin.get("password_hash", "")

        if not isinstance(expected_username, str) or not isinstance(
            expected_password_hash, str
        ):
            return False

        if username.strip() != expected_username:
            return False

        return verify_password(password, expected_password_hash)

    def update_general(self, bot_token: str, webhook_url: str) -> dict[str, Any]:
        token = bot_token.strip()
        url = webhook_url.strip()

        if not token:
            raise ValueError("Bot token cannot be empty")

        if not url:
            raise ValueError("Webhook URL cannot be empty")

        with self._lock:
            settings = self._read()
            settings["bot_token"] = token
            settings["webhook_url"] = url
            self._write(settings)
            return settings

    def update_form(self, form: dict[str, Any]) -> dict[str, Any]:
        normalized_form = validate_form_config(form)

        with self._lock:
            settings = self._read()
            settings["form"] = normalized_form
            self._write(settings)
            return settings
