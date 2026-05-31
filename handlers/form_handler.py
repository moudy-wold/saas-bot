from aiogram import Router
from aiogram.types import CallbackQuery, Message

from keyboards.control_keyboard import build_control_keyboard
from keyboards.dynamic_keyboard import build_select_keyboard
from services.tenant_db import TenantSettingsRepository
from services.webhook_sender import send_to_webhook
from state.session_manager import SessionManager, UserInfo
from utils.logger import setup_logger
from utils.validators import validate_field_value

logger = setup_logger(__name__)


async def _execute_profile_action(
    *,
    message: Message,
    action: str,
    tenant_repo: TenantSettingsRepository,
    session_manager: SessionManager,
    form_id: str = "",
    reply_text: str = "",
) -> bool:
    action_name = action.strip()

    if action_name == "show_services":
        services = tenant_repo.get_bot_profile().get("services", [])
        if not services:
            await message.answer("No services configured yet.")
            return True

        lines = ["Available services:"]
        for item in services:
            name = str(item.get("name", "")).strip()
            if not name:
                continue
            description = str(item.get("description", "")).strip()
            price = str(item.get("price", "")).strip()
            line = f"- {name}"
            if description:
                line += f" | {description}"
            if price:
                line += f" | Price: {price}"
            lines.append(line)

        await message.answer("\n".join(lines))
        return True

    if action_name == "start_form":
        chosen_form = tenant_repo.get_active_form()
        if form_id:
            for profile_form in tenant_repo.get_bot_profile().get("forms", []):
                if str(profile_form.get("id", "")).strip() == form_id:
                    chosen_form = profile_form
                    break

        if message.from_user is None:
            return True

        session_manager.start_session(
            user=UserInfo(
                id=message.from_user.id,
                username=message.from_user.username,
                full_name=message.from_user.full_name,
            ),
            form=chosen_form,
        )
        await message.answer("Let's start.")
        await ask_current_question(
            message=message,
            session_manager=session_manager,
            tenant_repo=tenant_repo,
        )
        return True

    if action_name == "show_buttons":
        buttons = tenant_repo.get_bot_profile().get("buttons", [])
        await message.answer("Main menu:", reply_markup=build_control_keyboard(buttons))
        return True

    if action_name == "reply":
        await message.answer(reply_text or "Done.")
        return True

    return False


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

    @router.callback_query(lambda cb: cb.data is not None and cb.data.startswith("control_btn:"))
    async def control_button(callback: CallbackQuery) -> None:
        if callback.message is None or callback.data is None:
            return

        profile = tenant_repo.get_bot_profile()
        token = callback.data.split("control_btn:", maxsplit=1)[1]

        action = ""
        form_id = ""
        reply_text = ""

        if token == "start_form":
            action = "start_form"
        else:
            try:
                index = int(token)
                button = profile.get("buttons", [])[index]
                action = str(button.get("action", "")).strip()
                form_id = str(button.get("form_id", "")).strip()
                reply_text = str(button.get("reply_text", "")).strip()
            except (ValueError, IndexError, TypeError):
                await callback.answer("Invalid action", show_alert=True)
                return

        await callback.answer("OK")
        await _execute_profile_action(
            message=callback.message,
            action=action,
            tenant_repo=tenant_repo,
            session_manager=session_manager,
            form_id=form_id,
            reply_text=reply_text,
        )

    @router.message()
    async def message_answer(message: Message) -> None:
        if message.from_user is None:
            return

        user_id = message.from_user.id
        session = session_manager.get_session(user_id)
        if session is None:
            if message.text and message.text.startswith("/"):
                profile = tenant_repo.get_bot_profile()
                command_name = message.text[1:].strip().split(" ", maxsplit=1)[0].lower()
                for command in profile.get("commands", []):
                    if str(command.get("command", "")).strip().lower() == command_name:
                        await _execute_profile_action(
                            message=message,
                            action=str(command.get("action", "")),
                            tenant_repo=tenant_repo,
                            session_manager=session_manager,
                            form_id=str(command.get("form_id", "")).strip(),
                            reply_text=str(command.get("reply_text", "")).strip(),
                        )
                        return
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
