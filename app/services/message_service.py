from typing import List
import uuid
from sqlalchemy import select
from app.models.message import DBMessage, MessageCreate, MessageResponse
from app.models.memora import DBMemora
from app.agents.memora_agent import MemoraAgent
from app.core.database import get_db

class MessageService:
    def __init__(self):
        self._memora_agent = MemoraAgent()

    async def create_message(
        self,
        message: MessageCreate,
        user_id: str
    ) -> MessageResponse:
        """
        Create a new message and generate a response using the Memora agent.
        
        Args:
            message: MessageCreate object containing message details
            
        Returns:
            MessageResponse: Created message with the generated response
            
        Raises:
            ValueError: If the memora is not found
        """
        async with get_db() as db:
            # Get memora info
            stmt = select(DBMemora).filter(DBMemora.id == message.memora_id)
            result = await db.execute(stmt)
            memora = result.scalar_one_or_none()
            
            if not memora:
                raise ValueError(f"Memora with id {message.memora_id} not found")
            
            # Get chat history
            chat_history = await self.get_messages(message.memora_id, user_id, 3)
            
            # Generate response using the Memora agent
            response = await self._memora_agent.generate_response(
                question=message.content,
                memora_name=memora.full_name,
                memora_bio=memora.bio,
                memora_description=memora.description,
                speak_pattern=memora.speak_pattern,
                chat_history=chat_history
            )
            
            # Create new message in the database
            db_message = DBMessage(
                id=str(uuid.uuid4()),
                content=message.content,
                memora_id=message.memora_id,
                sent_by_id=user_id,
                response=response
            )
            
            db.add(db_message)
            await db.commit()
            await db.refresh(db_message)
            
            return MessageResponse(
                id=db_message.id,
                content=db_message.content,
                memora_id=db_message.memora_id,
                sent_by_id=db_message.sent_by_id,
                timestamp=db_message.timestamp,
                response=db_message.response
            )

    async def get_messages(
        self, 
        memora_id: int,
        user_id: str,
        limit: int = 50,
    ) -> List[MessageResponse]:
        """
        Get messages for a specific memora.
        
        Args:
            memora_id: ID of the memora to get messages for
            limit: Maximum number of messages to return (default: 50)
            
        Returns:
            List[MessageResponse]: List of messages ordered by timestamp
        """
        async with get_db() as db:
            stmt = (
                select(DBMessage)
                .filter(DBMessage.memora_id == memora_id)
                .order_by(DBMessage.timestamp.desc())
                .limit(limit)
            )
            result = await db.execute(stmt)
            messages = result.scalars().all()
            
            return [
                MessageResponse(
                    id=message.id,
                    content=message.content,
                    memora_id=message.memora_id,
                    sent_by_id=user_id,
                    timestamp=message.timestamp,
                    response=message.response
                )
                for message in messages
            ]

    async def get_user_messages(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[MessageResponse]:
        """
        Get all messages sent by a specific user.
        
        Args:
            user_id: ID of the user to get messages for
            skip: Number of messages to skip (for pagination)
            limit: Maximum number of messages to return
            
        Returns:
            List[MessageResponse]: List of messages sent by the user
        """
        async with get_db() as db:
            stmt = (
                select(DBMessage)
                .filter(DBMessage.sent_by_id == user_id)
                .order_by(DBMessage.timestamp.desc())
                .offset(skip)
                .limit(limit)
            )
            result = await db.execute(stmt)
            messages = await result.scalars().all()
            
            return [
                MessageResponse(
                    id=message.id,
                    content=message.content,
                    memora_id=message.memora_id,
                    sent_by_id=message.sent_by_id,
                    timestamp=message.timestamp,
                    response=message.response
                )
                for message in messages
            ]

    async def delete_message(
        self,
        message_id: str,
        user_id: str
    ) -> bool:
        """
        Delete a message if the user is the sender.
        
        Args:
            message_id: ID of the message to delete
            user_id: ID of the user attempting to delete
            
        Returns:
            bool: True if message was deleted, False if not found or not authorized
        """
        async with get_db() as db:
            stmt = select(DBMessage).filter(
                DBMessage.id == message_id,
                DBMessage.sent_by_id == user_id
            )
            result = await db.execute(stmt)
            message = result.scalar_one_or_none()
            
            if message:
                await db.delete(message)
                await db.commit()
                return True
            return False 