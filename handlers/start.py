from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from handlers.form_handler import ask_current_question
from services.tenant_db import TenantSettingsRepository
from state.session_manager import SessionManager, UserInfo

def register_start_handler(
    session_manager: SessionManager, tenant_repo: TenantSettingsRepository
) -> Router:
    router = Router()

    @router.message(CommandStart())
    async def start_command(message: Message) -> None:
        if message.from_user is None:
            return

        user = UserInfo(
            id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
        )

        form = tenant_repo.get_active_form()
        session_manager.start_session(user=user, form=form)
        await message.answer("Welcome! Let's start the form.")
        await ask_current_question(
            message=message,
            session_manager=session_manager,
            tenant_repo=tenant_repo,
        )

    return router
