from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, LargeBinary
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

# Database Model
class DBMessage(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, index=True)
    content = Column(String, nullable=False)
    response = Column(String, nullable=False)
    memora_id = Column(Integer, ForeignKey("memoras.id"), index=True)
    sent_by_id = Column(String, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    audio_data = Column(LargeBinary, nullable=True)
    video_url = Column(String, nullable=True)
    
    memora = relationship("DBMemora", back_populates="messages")
    sent_by = relationship("User", back_populates="messages")

# Pydantic Models for API
class MessageBase(BaseModel):
    content: str
    memora_id: int
    video_url: Optional[str] = None

class MessageCreate(MessageBase):
    pass

class MessageResponse(MessageBase):
    id: str
    response: str
    timestamp: datetime
    sent_by_id: str

    class Config:
        from_attributes = True 