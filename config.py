from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = BASE_DIR / "data" / "bot_settings.json"
TENANTS_DIR = BASE_DIR / "data" / "tenants"
DASHBOARD_SESSION_SECRET = "CHANGE_THIS_DASHBOARD_SESSION_SECRET"

DEFAULT_SETTINGS: dict[str, Any] = {
    "bot_token": "YOUR_TELEGRAM_BOT_TOKEN",
    "webhook_url": "https://example.com/webhook",
    "admin": {
        "username": "admin",
        "password_hash": "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9",
    },
    "form": {
        "id": "order_form",
        "fields": [
            {
                "name": "product",
                "type": "select",
                "label": "Choose product",
                "options": ["Pizza", "Burger", "Shawarma"],
            },
            {
                "name": "quantity",
                "type": "number",
                "label": "Enter quantity",
            },
            {
                "name": "address",
                "type": "text",
                "label": "Enter your address",
            },
        ],
    },
}
