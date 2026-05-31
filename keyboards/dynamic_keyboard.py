from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def build_select_keyboard(options: list[str]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=option, callback_data=f"form_select:{option}")]
        for option in options
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
