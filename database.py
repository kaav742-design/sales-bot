async def delete_product(product_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM products WHERE id = ?",
            (product_id,),
        )
        await db.commit()


async def get_all_products():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM products ORDER BY id"
        )
        return await cursor.fetchall()