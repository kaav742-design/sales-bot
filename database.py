import aiosqlite

DB_PATH = "shop.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "CREATE TABLE IF NOT EXISTS products ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "name TEXT NOT NULL, "
            "description TEXT, "
            "price_cents INTEGER NOT NULL, "
            "photo_url TEXT, "
            "is_active INTEGER DEFAULT 1)"
        )
        await db.execute(
            "CREATE TABLE IF NOT EXISTS cart_items ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "user_id INTEGER NOT NULL, "
            "product_id INTEGER NOT NULL, "
            "quantity INTEGER NOT NULL DEFAULT 1)"
        )
        await db.execute(
            "CREATE TABLE IF NOT EXISTS orders ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "user_id INTEGER NOT NULL, "
            "username TEXT, "
            "total_cents INTEGER NOT NULL, "
            "items_json TEXT NOT NULL, "
            "status TEXT DEFAULT 'paid', "
            "created_at TEXT DEFAULT CURRENT_TIMESTAMP, "
            "telegram_payment_charge_id TEXT)"
        )
        await db.commit()

        cursor = await db.execute("SELECT COUNT(*) FROM products")
        row = await cursor.fetchone()
        count = row[0]
        if count == 0:
            demo_products = [
                ("Футболка Классика", "Хлопковая футболка", 150000, None),
                ("Кружка с логотипом", "Керамическая кружка", 80000, None),
                ("Стикерпак", "10 виниловых стикеров", 30000, None),
            ]
            await db.executemany(
                "INSERT INTO products "
                "(name, description, price_cents, photo_url) "
                "VALUES (?, ?, ?, ?)",
                demo_products,
            )
            await db.commit()


async def get_active_products():
    async with aiosql