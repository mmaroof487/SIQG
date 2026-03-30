import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.connect() as conn:
        try:
            await conn.execute(text("SELECT id::uuid FROM users"))
            print("text() succeeded with ::")
        except Exception as e:
            print(f"text() failed with :: -> {e}")

asyncio.run(main())
