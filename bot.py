import asyncio
import json
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

import config
import database as db


class OrderStates(StatesGroup):
    waiting_for_phone = State()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()


def format_price(cents: int) -> str:
    return f"{cents / 100:.2f} {config.CURRENCY}"


def product_keyboard(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 В корзину", callback_data=f"add:{product_id}")],
            [InlineKeyboardButton(text="📋 Каталог", callback_data="catalog")],
        ]
    )


def cart_keyboard(cart_items) -> InlineKeyboardMarkup:
    rows = []
    for item in cart_items:
        rows.append([
            InlineKeyboardButton(
                text=f"❌ {item['name']} x{item['quantity']}",
                callback_data=f"remove:{item['cart_item_id']}",
            )
        ])
    if cart_items:
        rows.append([InlineKeyboardButton(text="✅ Оформить заказ", callback_data="checkout")])
    rows.append([InlineKeyboardButton(text="📋 Каталог", callback_data="catalog")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ---------- Команды ----------

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Добро пожаловать! 👋\n\n"
        "Здесь можно посмотреть каталог товаров, добавить их в корзину и оформить заказ. "
        "После оформления мы свяжемся с вами для подтверждения и оплаты.\n\n"
        "Команды:\n"
        "/catalog — каталог товаров\n"
        "/cart — корзина\n"
        "/help — помощь"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "/catalog — посмотреть товары\n"
        "/cart — посмотреть корзину и оформить заказ\n"
        "После оформления заказа с вами свяжется менеджер."
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
        caption = f"<b>{p['name']}</b>\n{p['description'] or ''}\n\n💰 {format_price(p['price_cents'])}"
        kb = product_keyboard(p["id"])
        if isinstance(target, Message):
            if p["photo_url"]:
                await target.answer_photo(p["photo_url"], caption=caption, reply_markup=kb)
            else:
                await target.answer(caption, reply_markup=kb)
        else:
            if p["photo_url"]:
                await target.message.answer_photo(p["photo_url"], caption=caption, reply_markup=kb)
            else:
                await target.message.answer(caption, reply_markup=kb)


@router.callback_query(F.data == "catalog")
async def cb_catalog(callback: CallbackQuery):
    await show_catalog(callback)
    await callback.answer()


@router.callback_query(F.data.startswith("add:"))
async def cb_add_to_cart(callback: CallbackQuery):
    product_id = int(callback.data.split(":")[1])
    await db.add_to_cart(callback.from_user.id, product_id, quantity=1)
    await callback.answer("Добавлено в корзину ✅")


@router.message(Command("cart"))
async def cmd_cart(message: Message):
    await show_cart(message)


async def show_cart(target):
    user_id = target.from_user.id
    items = await db.get_cart(user_id)
    if not items:
        text = "Корзина пуста. Загляните в /catalog 🙂"
    else:
        total = sum(item["price_cents"] * item["quantity"] for item in items)
        lines = ["<b>Ваша корзина:</b>\n"]
        for item in items:
            lines.append(f"• {item['name']} x{item['quantity']} — {format_price(item['price_cents'] * item['quantity'])}")
        lines.append(f"\n<b>Итого: {format_price(total)}</b>")
        text = "\n".join(lines)

    kb = cart_keyboard(items)
    if isinstance(target, Message):
        await target.answer(text, reply_markup=kb)
    else:
        await target.message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "cart")
async def cb_cart(callback: CallbackQuery):
    await show_cart(callback)
    await callback.answer()


@router.callback_query(F.data.startswith("remove:"))
async def cb_remove(callback: CallbackQuery):
    cart_item_id = int(callback.data.split(":")[1])
    await db.remove_cart_item(cart_item_id)
    await callback.answer("Удалено")
    await show_cart(callback)


# ---------- Оформление заказа (без оплаты в боте) ----------

@router.callback_query(F.data == "checkout")
async def cb_checkout(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    items = await db.get_cart(user_id)
    if not items:
        await callback.answer("Корзина пуста", show_alert=True)
        return

    total = sum(item["price_cents"] * item["quantity"] for item in items)
    order_items = [
        {"product_id": item["id"], "name": item["name"], "qty": item["quantity"], "price_cents": item["price_cents"]}
        for item in items
    ]
    await state.update_data(order_items=order_items, total_cents=total)
    await state.set_state(OrderStates.waiting_for_phone)

    phone_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await callback.message.answer(
        "Отлично! Остался последний шаг — оставьте номер телефона, чтобы мы могли связаться "
        "и договориться об оплате и доставке.\n\n"
        "Нажмите кнопку ниже или введите номер вручную.",
        reply_markup=phone_kb,
    )
    await callback.answer()


@router.message(OrderStates.waiting_for_phone, F.contact)
async def process_contact(message: Message, state: FSMContext):
    await finalize_order(message, state, message.contact.phone_number)


@router.message(OrderStates.waiting_for_phone, F.text)
async def process_phone_text(message: Message, state: FSMContext):
    phone = message.text.strip()
    if len(phone) < 5:
        await message.answer("Похоже, это не номер телефона. Попробуйте ещё раз.")
        return
    await finalize_order(message, state, phone)


async def finalize_order(message: Message, state: FSMContext, phone: str):
    data = await state.get_data()
    items = data.get("order_items", [])
    total = data.get("total_cents", 0)

    if not items:
        await message.answer("Корзина пуста.", reply_markup=ReplyKeyboardRemove())
        await state.clear()
        return

    await db.save_order(
        user_id=message.from_user.id,
        username=message.from_user.username or "",
        total_cents=total,
        items_json=json.dumps(items),
        charge_id="",
    )
    await db.clear_cart(message.from_user.id)
    await state.clear()

    lines = ["✅ Заказ оформлен! Мы свяжемся с вами в ближайшее время.\n", "<b>Состав заказа:</b>"]
    for item in items:
        lines.append(f"• {item['name']} x{item['qty']}")
    lines.append(f"\n<b>Итого: {format_price(total)}</b>")
    await message.answer("\n".join(lines), reply_markup=ReplyKeyboardRemove())

    # Уведомление продавцу
    if config.ADMIN_CHAT_ID:
        try:
            await message.bot.send_message(
                config.ADMIN_CHAT_ID,
                f"🆕 Новый заказ от @{message.from_user.username or message.from_user.id}\n"
                f"📞 Телефон: {phone}\n"
                + "\n".join(f"• {i['name']} x{i['qty']}" for i in items)
                + f"\nИтого: {format_price(total)}",
            )
        except Exception as e:
            logger.warning(f"Не удалось уведомить админа: {e}")


# ---------- Админ: добавление товара ----------
# Формат: /addproduct Название | Описание | Цена_в_рублях | ссылка_на_фото(необязательно)

@router.message(Command("addproduct"))
async def cmd_add_product(message: Message, command: CommandObject):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("Команда доступна только администратору.")
        return
    if not command.args:
        await message.answer(
            "Формат:\n/addproduct Название | Описание | Цена | Ссылка_на_фото(необязательно)"
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
        await message.answer("Цена должна быть числом, например 1500 или 1500.50")
        return

    await db.add_product(name, description, price_cents, photo_url)
    await message.answer(f"Товар «{name}» добавлен ✅")


async def main():
    await db.init_db()
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()  # хранилище состояний по умолчанию — в памяти, этого достаточно для одного процесса
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
