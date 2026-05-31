from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def build_control_keyboard(buttons: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for button in buttons:
        label = str(button.get("label", "")).strip()
        if not label:
            continue
        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"control_btn:{len(rows)}",
                )
            ]
        )

    if not rows:
        rows = [[InlineKeyboardButton(text="Start Form", callback_data="control_btn:start_form")]]

    return InlineKeyboardMarkup(inline_keyboard=rows)