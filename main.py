import asyncio

from aiogram import Bot, Dispatcher

from config import TENANTS_DIR
from handlers.form_handler import register_form_handlers
from handlers.start import register_start_handler
from services.tenant_db import TenantSettingsRepository, list_tenant_db_paths
from state.session_manager import SessionManager
from utils.logger import setup_logger

logger = setup_logger(__name__)


async def run_tenant_bot(tenant_repo: TenantSettingsRepository) -> None:
    tenant = tenant_repo.get_tenant_info()
    tenant_slug = tenant["slug"]
    token = tenant_repo.get_bot_token()

    if not token or token == "YOUR_TELEGRAM_BOT_TOKEN":
        logger.warning("Skipping tenant %s because bot token is not configured", tenant_slug)
        return

    session_manager = SessionManager()
    dispatcher = Dispatcher()
    dispatcher.include_router(register_start_handler(session_manager, tenant_repo))
    dispatcher.include_router(register_form_handlers(session_manager, tenant_repo))

    bot = Bot(token=token)
    logger.info("Starting polling for tenant %s", tenant_slug)

    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


async def main() -> None:
    tenant_db_paths = list_tenant_db_paths(TENANTS_DIR)
    if not tenant_db_paths:
        logger.error("No tenant databases found. Create tenant first from dashboard.")
        return

    tasks = [
        asyncio.create_task(run_tenant_bot(TenantSettingsRepository(path)))
        for path in tenant_db_paths
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        if isinstance(result, Exception):
            logger.exception("A tenant polling task failed: %s", result)


if __name__ == "__main__":
    asyncio.run(main())
