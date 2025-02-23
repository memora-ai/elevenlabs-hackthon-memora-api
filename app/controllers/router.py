from fastapi import APIRouter
from app.controllers import memora, memora_messages, user

router = APIRouter()

router.include_router(memora.router, prefix="/memora", tags=["memora"])
router.include_router(memora_messages.router, prefix="/memora/messages", tags=["memora-messages"])
router.include_router(user.router, prefix="/users", tags=["users"])

@router.get("/")
async def root():
    return {"message": "Hello Memora"} 