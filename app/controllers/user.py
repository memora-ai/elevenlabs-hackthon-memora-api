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
    filters = {}
    if name:
        filters["name"] = name 

    return await user_service.get_multi(
        user_id=current_user["id"],
        skip=skip,
        limit=limit,
        filters=filters
    ) 