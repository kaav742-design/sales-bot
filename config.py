import os

# Токен бота — получен у @BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN", "8556280839:AAEn-omPPXbp0Ln3jqqydu1RsiSDg_EzZJc")

# Валюта — используется только для отображения цены
CURRENCY = os.getenv("CURRENCY", "EUR")

# ID администратора(ов) — узнать свой Telegram ID можно у бота @userinfobot
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "8791811928").split(",") if x.strip()]

# Chat ID, куда слать уведомления о новых заказах
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "") or (ADMIN_IDS[0] if ADMIN_IDS else None)