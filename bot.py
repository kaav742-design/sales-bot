import asyncio
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

import config
import database as db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()

ORDER_CHAT_URL = "https://t.me/A73B78K"


def format_price(cents: int) -> str:
    return f"{cents / 100:.2f} {config.CURRENCY}"


def product_keyboard(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🛍 Заказать",
                url=ORDER_CHAT_URL,
            )],
            [InlineKeyboardButton(
                text="📋 Каталог",
                callback_data="catalog",
            )],
        ]
    )


# ---------- Команды ----------

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Добро пожаловать! 👋\n\n"
        "Здесь можно посмотреть каталог товаров. "
        "Чтобы заказать что-то — нажмите «Заказать» "
        "под товаром, это откроет чат со мной.\n\n"
        "Команды:\n"
        "/catalog — каталог товаров\n"
        "/help — помощь"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "/catalog — посмотреть товары\n"
        "Нажмите «Заказать» под товаром, чтобы "
        "написать мне напрямую."
    )


@router.message(Command("catalog"))
async def cmd_catalog(message: Message):
    await show_catalog(message)


async def show_catalog(target):
    products = await db.get_active_products()
    if not products:
        text = "Каталог пока пуст."
        if isinstance(target, Message):
            await target.answer(text)
        else:
            await target.message.answer(text)
        return

    for p in products:
        caption = (
            f"<b>{p['name']}</b>\n"
            f"{p['description'] or ''}\n\n"
            f"💰 {format_price(p['price_cents'])}"
        )
        kb = product_keyboard(p["id"])
        if isinstance(target, Message):
            if p["photo_url"]:
                await target.answer_photo(
                    p["photo_url"], caption=caption, reply_markup=kb
                )
            else:
                await target.answer(caption, reply_markup=kb)
        else:
            if p["photo_url"]:
                await target.message.answer_photo(
                    p["photo_url"], caption=caption, reply_markup=kb
                )
            else:
                await target.message.answer(caption, reply_markup=kb)


@router.callback_query(F.data == "catalog")
async def cb_catalog(callback: CallbackQuery):
    await show_catalog(callback)
    await callback.answer()


# ---------- Управление каталогом (только админ) ----------

@router.message(Command("addproduct"))
async def cmd_add_product(message: Message, command: CommandObject):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("Команда доступна только администратору.")
        return
    if not command.args:
        await message.answer(
            "Формат:\n"
            "/addproduct Название | Описание | Цена | "
            "Ссылка_на_фото(необязательно)"
        )
        return

    parts = [p.strip() for p in command.args.split("|")]
    if len(parts) < 3:
        await message.answer("Нужно минимум: Название | Описание | Цена")
        return

    name, description, price_str = parts[0], parts[1], parts[2]
    photo_url = parts[3] if len(parts) > 3 else None
    try:
        price_cents = int(float(price_str) * 100)
    except ValueError:
        await message.answer(
            "Цена должна быть числом, например 1500 или 1500.50"
        )
        return

    await db.add_product(name, description, price_cents, photo_url)
    await message.answer(f"Товар «{name}» добавлен ✅")


@router.message(Command("myproducts"))
async def cmd_my_products(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("Команда доступна только администратору.")
        return

    products = await db.get_all_products()
    if not products:
        await message.answer("Каталог пуст.")
        return

    for p in products:
        text = f"{p['name']} — {format_price(p['price_cents'])}"
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text="❌ Удалить",
                    callback_data=f"delprod:{p['id']}",
                )]
            ]
        )
        await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("delprod:"))
async def cb_delete_product(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("Только для администратора", show_alert=True)
        return
    product_id = int(callback.data.split(":")[1])
    await db.delete_product(product_id)
    await callback.message.edit_text("Товар удалён ✅")
    await callback.answer()


async def main():
    await db.init_db()
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())