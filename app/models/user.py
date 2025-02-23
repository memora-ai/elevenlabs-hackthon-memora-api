from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

from sqlalchemy import Column, DateTime, String, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base

class User(Base):
    __tablename__ = 'users'
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True)
    picture = Column(String)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)

    permissions = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    memoras = relationship("DBMemora", back_populates="user", cascade="all, delete-orphan")
    messages = relationship("DBMessage", back_populates="sent_by", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'permissions': self.permissions
        }

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    picture: Optional[str] = None
    is_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True

