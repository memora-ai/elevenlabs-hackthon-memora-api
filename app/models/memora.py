from pydantic import BaseModel
from datetime import date, datetime, timezone
from typing import Optional
from enum import Enum
from sqlalchemy import Column, Integer, String, Date, Enum as SQLAEnum, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base

# Enums
class PrivacyStatus(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"

class MemoraStatus(str, Enum):
    BASIC_INFO_COMPLETED = "basic_info_completed"
    VIDEO_INFO_COMPLETED = "video_info_completed"
    ERROR_PROCESSING_VIDEO = "error_processing_video"
    PROCESSING_SOCIALMEDIA_DATA = "processing_socialmedia_data"
    CONCLUDED = "concluded"
    CONCLUDED_WITH_ANALYZER_ERROR = "concluded_with_analyzer_error"
    ERROR = "error"

# Database Model
class DBMemora(Base):
    __tablename__ = "memoras"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    bio = Column(String)
    description = Column(String)
    speak_pattern = Column(String)
    language = Column(String)
    birthday = Column(Date)
    privacy_status = Column(SQLAEnum(PrivacyStatus), default=PrivacyStatus.PRIVATE)
    status = Column(SQLAEnum(MemoraStatus), default=MemoraStatus.BASIC_INFO_COMPLETED)
    status_message = Column(String, nullable=True)
    shared_with = Column(JSON, default=list)
    video_path = Column(String, nullable=True)
    audio_path = Column(String, nullable=True)
    profile_picture_base64 = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="memoras")
    messages = relationship("DBMessage", back_populates="memora", cascade="all, delete-orphan")

# Pydantic Models for API
class MemoraBase(BaseModel):
    full_name: str
    bio: Optional[str] = None   
    description: Optional[str] = None
    speak_pattern: Optional[str] = None
    language: str
    birthday: date
    privacy_status: Optional[PrivacyStatus] = PrivacyStatus.PRIVATE


class MemoraCreate(BaseModel):
    full_name: str
    language: str
    birthday: date
    privacy_status: Optional[PrivacyStatus] = PrivacyStatus.PRIVATE
    profile_picture_base64: Optional[str] = None

class MemoraUpdate(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = None
    birthday: Optional[date] = None
    privacy_status: Optional[PrivacyStatus] = None
    status: Optional[MemoraStatus] = None
    status_message: Optional[str] = None
    profile_picture_base64: Optional[str] = None

class MemoraResponse(MemoraBase):
    id: int
    user_id: str
    status: MemoraStatus
    status_message: Optional[str] = None
    video_path: Optional[str] = None
    audio_path: Optional[str] = None
    profile_picture_base64: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True 