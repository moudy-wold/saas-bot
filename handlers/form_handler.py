from aiogram import Router
from aiogram.types import CallbackQuery, Message

from keyboards.dynamic_keyboard import build_select_keyboard
from services.tenant_db import TenantSettingsRepository
from services.webhook_sender import send_to_webhook
from state.session_manager import SessionManager
from utils.logger import setup_logger
from utils.validators import validate_field_value

logger = setup_logger(__name__)


async def ask_current_question(
    message: Message,
    session_manager: SessionManager,
    tenant_repo: TenantSettingsRepository,
) -> None:
    if message.from_user is None:
        return

    user_id = message.from_user.id
    field = session_manager.get_current_field(user_id)

    if field is None:
        await finalize_form(
            message=message,
            session_manager=session_manager,
            tenant_repo=tenant_repo,
        )
        return

    field_type = field["type"]
    label = field["label"]

    if field_type == "select":
        options = field.get("options", [])
        keyboard = build_select_keyboard(options)
        await message.answer(label, reply_markup=keyboard)
        return

    await message.answer(label)


async def finalize_form(
    message: Message,
    session_manager: SessionManager,
    tenant_repo: TenantSettingsRepository,
) -> None:
    if message.from_user is None:
        return

    user_id = message.from_user.id
    payload = session_manager.build_payload(user_id)
    if payload is None:
        await message.answer("Session not found. Please use /start.")
        return

    webhook_url = tenant_repo.get_webhook_url()
    sent = await send_to_webhook(payload, webhook_url)

    if sent:
        await message.answer("Form completed successfully. Data sent.")
    else:
        await message.answer("Form completed, but failed to send data to webhook.")

    logger.info("Submitted payload: %s", payload)
    session_manager.clear_session(user_id)


def register_form_handlers(
    session_manager: SessionManager, tenant_repo: TenantSettingsRepository
) -> Router:
    router = Router()

    @router.callback_query(lambda cb: cb.data is not None and cb.data.startswith("form_select:"))
    async def select_answer(callback: CallbackQuery) -> None:
        if callback.from_user is None or callback.message is None or callback.data is None:
            return

        user_id = callback.from_user.id
        field = session_manager.get_current_field(user_id)
        if field is None:
            await callback.answer("Session not found, use /start")
            return

        if field.get("type") != "select":
            await callback.answer("Current question is not a selection")
            return

        selected_value = callback.data.split("form_select:", maxsplit=1)[1]

        try:
            validated = validate_field_value(field, selected_value)
        except ValueError:
            await callback.answer("Invalid option", show_alert=True)
            return

        session_manager.save_response(user_id, field["name"], validated)
        session_manager.advance(user_id)

        await callback.answer("Selected")
        await callback.message.edit_reply_markup(reply_markup=None)
        await ask_current_question(
            message=callback.message,
            session_manager=session_manager,
            tenant_repo=tenant_repo,
        )

    @router.message()
    async def message_answer(message: Message) -> None:
        if message.from_user is None:
            return

        user_id = message.from_user.id
        session = session_manager.get_session(user_id)
        if session is None:
            return

        field = session_manager.get_current_field(user_id)
        if field is None:
            await finalize_form(
                message=message,
                session_manager=session_manager,
                tenant_repo=tenant_repo,
            )
            return

        if field.get("type") == "select":
            await message.answer("Please choose one of the options using the buttons.")
            return

        raw_text = message.text or ""
        try:
            validated = validate_field_value(field, raw_text)
        except ValueError as exc:
            await message.answer(str(exc))
            return

        session_manager.save_response(user_id, field["name"], validated)
        session_manager.advance(user_id)
        await ask_current_question(
            message=message,
            session_manager=session_manager,
            tenant_repo=tenant_repo,
        )

    return router
