"""Quick MongoDB Atlas connectivity check.

Usage (from backend/ with venv active):
    python test_mongo.py

Reads MONGO_URL and DB_NAME from backend/.env. Deletes itself concerns: none —
this is a throwaway diagnostic, safe to remove once your connection works.
"""
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(Path(__file__).parent / ".env")


async def main() -> None:
    url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME", "gita_wisdom")
    if not url or "<" in url:
        raise SystemExit("MONGO_URL is missing or still has a <placeholder> — edit backend/.env")

    client = AsyncIOMotorClient(url, serverSelectionTimeoutMS=8000)
    try:
        await client.admin.command("ping")
        names = await client.list_database_names()
        print(f"✅ Connected to Atlas. DB in use: {db_name!r}")
        print(f"   Existing databases: {names}")
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
