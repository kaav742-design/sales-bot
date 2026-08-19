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
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM products "
            "WHERE is_active = 1 ORDER BY id"
        )
        return await cursor.fetchall()


async def get_product(product_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM products WHERE id = ?",
            (product_id,),
        )
        return await cursor.fetchone()


async def add_product(name, description, price_cents, photo_url=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO products "
            "(name, description, price_cents, photo_url) "
            "VALUES (?, ?, ?, ?)",
            (name, description, price_cents, photo_url),
        )
        await db.commit()


async def add_to_cart(user_id: int, product_id: int, quantity: int = 1):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM cart_items "
            "WHERE user_id = ? AND product_id = ?",
            (user_id, product_id),
        )
        existing = await cursor.fetchone()
        if existing:
            await db.execute(
                "UPDATE cart_items SET quantity = quantity + ? "
                "WHERE id = ?",
                (quantity, existing["id"]),
            )
        else:
            await db.execute(
                "INSERT INTO cart_items "
                "(user_id, product_id, quantity) "
                "VALUES (?, ?, ?)",
                (user_id, product_id, quantity),
            )
        await db.commit()


async def get_cart(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT ci.id as cart_item_id, ci.quantity, p.* "
            "FROM cart_items ci "
            "JOIN products p ON p.id = ci.product_id "
            "WHERE ci.user_id = ?",
            (user_id,),
        )
        return await cursor.fetchall()


async def clear_cart(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM cart_items WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()


async def remove_cart_item(cart_item_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM cart_items WHERE id = ?",
            (cart_item_id,),
        )
        await db.commit()


async def save_order(user_id: int, username: str, total_cents: int, items_json: str, charge_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO orders "
            "(user_id, username, total_cents, items_json, "
            "telegram_payment_charge_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, username, total_cents, items_json, charge_id),
        )
        await db.commit()