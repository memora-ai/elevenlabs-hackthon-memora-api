from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.models.message import MessageCreate, MessageResponse
from app.services.message_service import MessageService
from app.services.memora import MemoraService
from app.core.auth import get_current_user

router = APIRouter()
message_service = MessageService()

@router.post("/", response_model=MessageResponse)
async def create_message(
    message: MessageCreate,
    current_user: dict = Depends(get_current_user)
) -> MessageResponse:
    # Check if user can access the memora
    if not await MemoraService.can_access(message.memora_id, current_user["id"]):
        raise HTTPException(status_code=403, detail="Not authorized to send messages to this Memora")
    
    return await message_service.create_message(
        message=message,
        user_id=current_user["id"]
    )

@router.get("/{memora_id}", response_model=List[MessageResponse])
async def get_messages(
    memora_id: int,
    current_user: dict = Depends(get_current_user)
) -> List[MessageResponse]:
    # Check if user can access the memora
    if not await MemoraService.can_access(memora_id, current_user["id"]):
        raise HTTPException(status_code=403, detail="Not authorized to view messages from this Memora")
    
    return await message_service.get_messages(memora_id, current_user["id"])