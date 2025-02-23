from fastapi import APIRouter, Depends
from typing import List
from app.models.user import UserResponse
from app.services.user import UserService
from app.core.auth import get_current_user

router = APIRouter()
user_service = UserService()

@router.get("/", response_model=List[UserResponse])
async def list_users_by_name(
    name: str,
    skip: int = 0,
    limit: int = 100,
    current_user: dict = Depends(get_current_user)
):
    """Get users with name filter"""
    return await user_service.search_users(
        current_user_id=current_user["id"],
        skip=skip,
        limit=limit,
        name=name
    ) 