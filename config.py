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
    "bot_profile": {
        "start_behavior": "menu",
        "welcome_message": "Welcome! Please choose a service.",
        "commands": [
            {
                "command": "menu",
                "description": "Show main menu",
                "action": "show_buttons",
            },
            {
                "command": "services",
                "description": "Show available services",
                "action": "show_services",
            },
            {
                "command": "book",
                "description": "Start default booking/order form",
                "action": "start_form",
            },
        ],
        "buttons": [
            {"label": "Book / Order", "action": "start_form"},
            {"label": "Services", "action": "show_services"},
            {"label": "Help", "action": "reply", "reply_text": "Use /menu to see all options."},
        ],
        "services": [
            {
                "name": "General Service",
                "description": "Default service entry",
                "price": "",
                "api_endpoint": "",
            }
        ],
        "forms": [],
    },
}
