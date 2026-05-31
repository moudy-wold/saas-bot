import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import DEFAULT_SETTINGS
from utils.form_schema import validate_form_config
from utils.security import hash_password, verify_password


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify_tenant(raw_slug: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in raw_slug.strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    cleaned = cleaned.strip("-")
    if not cleaned:
        raise ValueError("Tenant slug is required")
    return cleaned


def _tenant_db_path(tenants_dir: Path, tenant_slug: str) -> Path:
    return tenants_dir / f"{tenant_slug}.db"


def list_tenant_db_paths(tenants_dir: Path) -> list[Path]:
    tenants_dir.mkdir(parents=True, exist_ok=True)
    return sorted(tenants_dir.glob("*.db"))


class TenantSettingsRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @classmethod
    def for_slug(cls, tenants_dir: Path, tenant_slug: str) -> "TenantSettingsRepository":
        normalized_slug = slugify_tenant(tenant_slug)
        db_path = _tenant_db_path(tenants_dir, normalized_slug)
        if not db_path.exists():
            raise ValueError("Tenant not found")
        return cls(db_path)

    @classmethod
    def create_tenant(
        cls,
        tenants_dir: Path,
        tenant_slug: str,
        tenant_name: str,
        admin_username: str,
        admin_password: str,
    ) -> "TenantSettingsRepository":
        normalized_slug = slugify_tenant(tenant_slug)
        normalized_name = tenant_name.strip()
        normalized_user = admin_username.strip()

        if not normalized_name:
            raise ValueError("Tenant name cannot be empty")

        if not normalized_user:
            raise ValueError("Admin username cannot be empty")

        if len(admin_password) < 6:
            raise ValueError("Admin password must be at least 6 characters")

        db_path = _tenant_db_path(tenants_dir, normalized_slug)
        if db_path.exists():
            raise ValueError("Tenant slug already exists")

        repo = cls(db_path)
        repo._seed_tenant(
            tenant_slug=normalized_slug,
            tenant_name=normalized_name,
            admin_username=normalized_user,
            admin_password=admin_password,
        )
        return repo

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS tenant_info (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    slug TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS bot_settings (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    bot_token TEXT NOT NULL,
                    webhook_url TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS form_settings (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    form_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

            conn.execute(
                """
                INSERT OR IGNORE INTO bot_settings (id, bot_token, webhook_url, updated_at)
                VALUES (1, ?, ?, ?)
                """,
                (
                    DEFAULT_SETTINGS["bot_token"],
                    DEFAULT_SETTINGS["webhook_url"],
                    _now_iso(),
                ),
            )

            conn.execute(
                """
                INSERT OR IGNORE INTO form_settings (id, form_json, updated_at)
                VALUES (1, ?, ?)
                """,
                (json.dumps(DEFAULT_SETTINGS["form"], ensure_ascii=True), _now_iso()),
            )

            conn.commit()

    def _seed_tenant(
        self,
        tenant_slug: str,
        tenant_name: str,
        admin_username: str,
        admin_password: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO tenant_info (id, slug, name, created_at)
                VALUES (1, ?, ?, ?)
                """,
                (tenant_slug, tenant_name, _now_iso()),
            )

            conn.execute("DELETE FROM admins")
            conn.execute(
                """
                INSERT INTO admins (username, password_hash, created_at)
                VALUES (?, ?, ?)
                """,
                (admin_username, hash_password(admin_password), _now_iso()),
            )
            conn.commit()

    def get_tenant_info(self) -> dict[str, str]:
        with self._connect() as conn:
            row = conn.execute("SELECT slug, name FROM tenant_info WHERE id = 1").fetchone()

        if row is None:
            fallback_slug = self.db_path.stem
            return {"slug": fallback_slug, "name": fallback_slug}

        return {"slug": str(row["slug"]), "name": str(row["name"])}

    def verify_admin_credentials(self, username: str, password: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT username, password_hash FROM admins WHERE username = ?",
                (username.strip(),),
            ).fetchone()

        if row is None:
            return False

        return verify_password(password, str(row["password_hash"]))

    def get_bot_token(self) -> str:
        with self._connect() as conn:
            row = conn.execute("SELECT bot_token FROM bot_settings WHERE id = 1").fetchone()
        return "" if row is None else str(row["bot_token"])

    def get_webhook_url(self) -> str:
        with self._connect() as conn:
            row = conn.execute("SELECT webhook_url FROM bot_settings WHERE id = 1").fetchone()
        return "" if row is None else str(row["webhook_url"])

    def get_active_form(self) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT form_json FROM form_settings WHERE id = 1").fetchone()

        if row is None:
            raise ValueError("Form settings not found")

        parsed = json.loads(str(row["form_json"]))
        if not isinstance(parsed, dict):
            raise ValueError("Stored form is invalid")

        return parsed

    def update_general(self, bot_token: str, webhook_url: str) -> None:
        token = bot_token.strip()
        url = webhook_url.strip()

        if not token:
            raise ValueError("Bot token cannot be empty")

        if not url:
            raise ValueError("Webhook URL cannot be empty")

        with self._connect() as conn:
            conn.execute(
                """
                UPDATE bot_settings
                SET bot_token = ?, webhook_url = ?, updated_at = ?
                WHERE id = 1
                """,
                (token, url, _now_iso()),
            )
            conn.commit()

    def update_form(self, form: dict[str, Any]) -> None:
        normalized_form = validate_form_config(form)

        with self._connect() as conn:
            conn.execute(
                """
                UPDATE form_settings
                SET form_json = ?, updated_at = ?
                WHERE id = 1
                """,
                (json.dumps(normalized_form, ensure_ascii=True), _now_iso()),
            )
            conn.commit()

    def get_dashboard_data(self) -> dict[str, Any]:
        tenant = self.get_tenant_info()
        return {
            "tenant_slug": tenant["slug"],
            "tenant_name": tenant["name"],
            "bot_token": self.get_bot_token(),
            "webhook_url": self.get_webhook_url(),
            "form_json": json.dumps(self.get_active_form(), ensure_ascii=True, indent=2),
        }
