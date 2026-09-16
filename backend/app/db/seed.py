import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import get_password_hash
from app.models import User


async def seed():
    DATABASE_URL = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Create Admin
        admin = User(
            email="admin@yarrow.local",
            hashed_password=get_password_hash("admin123"),
            is_admin=True,
            is_active=True,
            is_verified=True
        )
        session.add(admin)

        # Create User
        user = User(
            email="user@yarrow.local",
            hashed_password=get_password_hash("user123"),
            is_admin=False,
            is_active=True,
            is_verified=True
        )
        session.add(user)

        await session.commit()
        print("Database seeded with default users.")

if __name__ == "__main__":
    asyncio.run(seed())

