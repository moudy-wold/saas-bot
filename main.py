import asyncio
from pathlib import Path

from aiogram import Bot, Dispatcher

from config import TENANTS_DIR
from handlers.form_handler import register_form_handlers
from handlers.start import register_start_handler
from services.tenant_db import TenantSettingsRepository, list_tenant_db_paths
from state.session_manager import SessionManager
from utils.logger import setup_logger

logger = setup_logger(__name__)


def _has_real_token(token: str) -> bool:
    normalized = token.strip()
    return bool(normalized) and normalized != "YOUR_TELEGRAM_BOT_TOKEN"


async def run_tenant_bot(tenant_repo: TenantSettingsRepository) -> None:
    tenant = tenant_repo.get_tenant_info()
    tenant_slug = tenant["slug"]
    token = tenant_repo.get_bot_token()

    if not _has_real_token(token):
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
        logger.error("No tenant databases found. Create a tenant from the web dashboard first.")
        return

    runnable_paths: list[Path] = []
    skipped_slugs: list[str] = []

    for path in tenant_db_paths:
        repo = TenantSettingsRepository(path)
        tenant_slug = repo.get_tenant_info()["slug"]

        if _has_real_token(repo.get_bot_token()):
            runnable_paths.append(path)
        else:
            skipped_slugs.append(tenant_slug)

    if skipped_slugs:
        logger.info(
            "Skipping %d tenant(s) without bot tokens: %s",
            len(skipped_slugs),
            ", ".join(skipped_slugs),
        )

    if not runnable_paths:
        logger.warning(
            "No tenant is ready for polling yet. Open the web dashboard, set a bot token, then run main.py again."
        )
        return

    tasks = [
        asyncio.create_task(run_tenant_bot(TenantSettingsRepository(path)))
        for path in runnable_paths
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        if isinstance(result, Exception):
            logger.exception("A tenant polling task failed: %s", result)


if __name__ == "__main__":
    asyncio.run(main())
