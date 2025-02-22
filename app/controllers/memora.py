from typing import List, Optional
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks

from app.models.memora import MemoraCreate, MemoraResponse, MemoraUpdate, PrivacyStatus
from app.services.memora import MemoraService
from app.core.auth import get_current_user
from app.models.user import UserResponse
from app.services.user import UserService

router = APIRouter()

@router.post("/basic-info", response_model=MemoraResponse)
async def create_memora_basic(
    memora: MemoraCreate,
    current_user: dict = Depends(get_current_user)
):
    return await MemoraService.create_basic_info(memora, current_user["id"])

@router.post("/{memora_id}/video", response_model=MemoraResponse)
async def upload_video(
    memora_id: int,
    video_file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    if not await MemoraService.is_owner(memora_id, current_user["id"]):
        raise HTTPException(status_code=403, detail="Not authorized to modify this Memora")
    
    db_memora = await MemoraService.process_video(memora_id, video_file)
    if db_memora is None:
        raise HTTPException(status_code=404, detail="Memora not found")
    return db_memora

@router.post("/{memora_id}/social-media", response_model=MemoraResponse)
async def upload_social_media(
    memora_id: int,
    zip_file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: dict = Depends(get_current_user)
):
    if not await MemoraService.is_owner(memora_id, current_user["id"]):
        raise HTTPException(status_code=403, detail="Not authorized to modify this Memora")
    
    if not zip_file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="File must be a ZIP archive")
    
    db_memora = await MemoraService.process_social_media(memora_id, zip_file, background_tasks)
    if db_memora is None:
        raise HTTPException(status_code=404, detail="Memora not found")
    return db_memora

@router.get("/my-memoras", response_model=List[MemoraResponse])
async def list_my_memoras(
    skip: int = 0, 
    limit: int = 100,
    current_user: dict = Depends(get_current_user)
):
    """Get only memoras owned by the current user"""
    return await MemoraService.get_user_memoras(
        user_id=current_user["id"],
        skip=skip,
        limit=limit
    )

@router.get("/{memora_id}", response_model=MemoraResponse)
async def get_memora(
    memora_id: int,
    current_user: dict = Depends(get_current_user)
):
    db_memora = await MemoraService.get_memora(memora_id)
    if db_memora is None:
        raise HTTPException(status_code=404, detail="Memora not found")
    
    if not await MemoraService.can_access(db_memora.id, current_user["id"]):
        raise HTTPException(status_code=403, detail="Not authorized to access this Memora")
    
    return db_memora

@router.get("/", response_model=List[MemoraResponse])
async def list_accessible_memoras(
    skip: int = 0, 
    limit: int = 100,
    name: Optional[str] = None,
    privacy_status: Optional[PrivacyStatus] = None,
    has_chat: Optional[bool] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get memoras that the user has access to (including shared ones)
    
    Args:
        name: Filter memoras by name (case-insensitive partial match)
        privacy_status: Filter by privacy status (public/private)
        has_chat: If True, only return memoras with chat history
    """
    return await MemoraService.get_accessible_memoras(
        user_id=current_user["id"],
        skip=skip,
        limit=limit,
        name=name,
        privacy_status=privacy_status,
        has_chat=has_chat
    )

@router.put("/{memora_id}", response_model=MemoraResponse)
async def update_memora(
    memora_id: int, 
    memora: MemoraUpdate,
    current_user: dict = Depends(get_current_user)
):
    if not await MemoraService.is_owner(memora_id, current_user["id"]):
        raise HTTPException(status_code=403, detail="Not authorized to modify this Memora")
    
    db_memora = await MemoraService.update_memora(memora_id, memora)
    if db_memora is None:
        raise HTTPException(status_code=404, detail="Memora not found")
    return db_memora

@router.delete("/{memora_id}")
async def delete_memora(
    memora_id: int,
    current_user: dict = Depends(get_current_user)
):
    if not await MemoraService.is_owner(memora_id, current_user["id"]):
        raise HTTPException(status_code=403, detail="Not authorized to delete this Memora")
    
    success = await MemoraService.delete_memora(memora_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memora not found")
    return {"message": "Memora deleted successfully"}

@router.get("/{memora_id}/shared-with", response_model=List[UserResponse])
async def get_shared_with_users(
    memora_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Get list of users (with details) that a memora is shared with"""
    if not await MemoraService.can_access(memora_id, current_user["id"]):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this Memora"
        )
    
    shared_users = await MemoraService.get_shared_with_users(
        memora_id=memora_id
    )
    if shared_users is None:
        raise HTTPException(
            status_code=404,
            detail="Memora not found"
        )
    return shared_users

@router.post("/{memora_id}/share/{user_id}", response_model=MemoraResponse)
async def share_memora(
    memora_id: int,
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Share a memora with another user"""
    memora = await MemoraService.share_memora(
        memora_id=memora_id,
        owner_id=current_user["id"],
        share_with_id=user_id
    )
    if not memora:
        raise HTTPException(
            status_code=404,
            detail="Memora not found or you're not the owner"
        )
    return memora

@router.delete("/{memora_id}/share/{user_id}", response_model=MemoraResponse)
async def unshare_memora(
    memora_id: int,
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove sharing access for a user"""
    memora = await MemoraService.unshare_memora(
        memora_id=memora_id,
        owner_id=current_user["id"],
        unshare_with_id=user_id
    )
    if not memora:
        raise HTTPException(
            status_code=404,
            detail="Memora not found or you're not the owner"
        )
    return memora

@router.get("/{memora_id}/shared-users", response_model=List[str])
async def get_shared_users(
    memora_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Get list of users a memora is shared with"""
    shared_users = await MemoraService.get_shared_users(
        memora_id=memora_id,
        owner_id=current_user["id"]
    )
    if shared_users is None:
        raise HTTPException(
            status_code=404,
            detail="Memora not found or you're not the owner"
        )
    return shared_users

@router.post("/{memora_id}/retry-analysis", response_model=MemoraResponse)
async def retry_memora_analysis(
    memora_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Retry processing a memora that failed during analysis"""
    if not await MemoraService.is_owner(memora_id, current_user["id"]):
        raise HTTPException(status_code=403, detail="Not authorized to modify this Memora")
    
    db_memora = await MemoraService.retry_analysis(memora_id)
    if db_memora is None:
        raise HTTPException(status_code=404, detail="Memora not found")
    return db_memora
