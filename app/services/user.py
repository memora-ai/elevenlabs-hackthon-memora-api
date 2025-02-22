from app.models.user import User
from sqlalchemy.future import select
from app.core.database import get_db
from sqlalchemy import or_
from app.services.base import BaseService
from typing import Optional, Dict, Any, List

class UserService(BaseService[User, dict, dict]):
    def __init__(self):
        super().__init__(User)

    async def get_user_by_id(self, user_id: str) -> User | None:
        """
        Retrieve a user by their ID.
        """
        async with get_db() as db:
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> User | None:
        """
        Retrieve a user by their email.
        """
        async with get_db() as db:
            stmt = select(User).where(User.email == email)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()

    async def create_user(self, user_data: dict) -> User:
        """
        Create a new user.
        """
        new_user = User(
            id=user_data.get("id", ""),
            name=user_data.get("name", ""),
            email=user_data.get("email", ""),
            permissions=user_data.get("permissions", []),
            picture=user_data.get("picture", None)
        )

        async with get_db() as db:
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)
            return new_user

    async def update_user(self, user_id: str, user_data: dict) -> User | None:
        """
        Update an existing user by ID.
        """
        async with get_db() as db:
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                return None

            # Update user fields
            user.name = user_data.get("name", user.name)
            user.email = user_data.get("email", user.email)
            user.permissions = user_data.get("permissions", user.permissions)

            db.add(user)
            await db.commit()
            await db.refresh(user)
            return user

    async def delete_user(self, user_id: str) -> bool:
        """
        Delete a user by their ID.
        """
        async with get_db() as db:
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                return False

            await db.delete(user)
            await db.commit()
            return True

    async def get_multi(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[User]:
        conditions = []
        
        async with get_db() as db:
            if filters:
                if "name" in filters:
                    conditions.append(self.model.name.ilike(f"%{filters['name']}%"))

            conditions.append(self.model.id != user_id)

            stmt = select(self.model)
            if conditions:
                stmt = stmt.filter(or_(*conditions))
            stmt = stmt.offset(skip).limit(limit)
            
            result = await db.execute(stmt)
            users = result.scalars().all()
            return users