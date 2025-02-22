from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
import io
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

@router.get("/{message_id}/audio", response_class=StreamingResponse)
async def get_message_audio(
    message_id: str,
    current_user: dict = Depends(get_current_user)
) -> StreamingResponse:
    """Get the audio file for a specific message"""
    audio_data = await message_service.get_message_audio(message_id, current_user["id"])
    
    return StreamingResponse(
        io.BytesIO(audio_data),
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": f"attachment; filename=message_{message_id}.mp3"
        }
    )

