"""
Database operations for user management (Postgres via async SQLAlchemy)
"""
import os
from typing import Optional, Dict

from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set. Please configure it in your environment (.env).")

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    discord_id = Column(String, primary_key=True)
    spreadsheet_id = Column(String, nullable=False)
    sheet_name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Database:
    """Handles all database operations"""

    def __init__(self):
        self.engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
        self.SessionLocal = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def initialize(self):
        """Create tables if they don't exist"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def add_user(self, discord_id: str, spreadsheet_id: str, sheet_name: str) -> bool:
        """Add a new user or update an existing user"""
        async with self.SessionLocal() as session:
            existing = await session.get(User, discord_id)
            if existing:
                existing.spreadsheet_id = spreadsheet_id
                existing.sheet_name = sheet_name
            else:
                session.add(User(
                    discord_id=discord_id,
                    spreadsheet_id=spreadsheet_id,
                    sheet_name=sheet_name
                ))
            await session.commit()
            return True

    async def get_user(self, discord_id: str) -> Optional[Dict[str, str]]:
        """Get user information by Discord ID"""
        async with self.SessionLocal() as session:
            user = await session.get(User, discord_id)
            if not user:
                return None
            return {
                "discord_id": user.discord_id,
                "spreadsheet_id": user.spreadsheet_id,
                "sheet_name": user.sheet_name,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
            }

    async def update_user(self, discord_id: str, spreadsheet_id: str = None, sheet_name: str = None) -> bool:
        """Update user information"""
        async with self.SessionLocal() as session:
            user = await session.get(User, discord_id)
            if not user:
                return False
            if spreadsheet_id:
                user.spreadsheet_id = spreadsheet_id
            if sheet_name:
                user.sheet_name = sheet_name
            await session.commit()
            return True

    async def delete_user(self, discord_id: str) -> bool:
        """Delete a user from the database"""
        async with self.SessionLocal() as session:
            user = await session.get(User, discord_id)
            if not user:
                return False
            await session.delete(user)
            await session.commit()
            return True

    async def user_exists(self, discord_id: str) -> bool:
        """Check if a user exists in the database"""
        return (await self.get_user(discord_id)) is not None

    async def get_user_by_spreadsheet(self, spreadsheet_id: str) -> Optional[Dict[str, str]]:
        """Get user information by spreadsheet ID"""
        from sqlalchemy import select
        async with self.SessionLocal() as session:
            result = await session.execute(
                select(User).where(User.spreadsheet_id == spreadsheet_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                return None

            return {
                "discord_id": user.discord_id,
                "spreadsheet_id": user.spreadsheet_id,
                "sheet_name": user.sheet_name,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
            }
