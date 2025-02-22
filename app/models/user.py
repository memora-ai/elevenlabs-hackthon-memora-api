from sqlalchemy import Column, Integer, String, Boolean, JSON
from sqlalchemy.orm import relationship

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

    memoras = relationship("DBMemora", back_populates="user", cascade="all, delete-orphan")
    messages = relationship("DBMessage", back_populates="sent_by", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'permissions': self.permissions
        }
