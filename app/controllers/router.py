from fastapi import APIRouter
from app.controllers import memora, memora_messages

router = APIRouter()

router.include_router(memora.router, prefix="/memora", tags=["memora"])
router.include_router(memora_messages.router, prefix="/memora/messages", tags=["memora-messages"])

@router.get("/")
async def root():
    return {"message": "Hello Memora"} 