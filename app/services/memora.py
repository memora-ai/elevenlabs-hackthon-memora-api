from typing import List, Optional
import logging
import asyncio
from fastapi import UploadFile, BackgroundTasks
from sqlalchemy import select, or_
from sqlalchemy import cast, Text

from app.models.memora import (
    DBMemora,
    MemoraCreate,
    MemoraUpdate,
    PrivacyStatus,
    MemoraStatus
)   
from app.utils.file_handler import FileHandler
from app.tasks.social_media_processor import process_social_media_data
from app.core.database import get_db
from app.models.message import DBMessage
from app.agents.user_analyzer import UserAnalyzer
from app.utils.elevenlabs_handler import ElevenLabsHandler
from app.models.user import User, UserResponse

logger = logging.getLogger(__name__)

class MemoraService:
    @staticmethod
    async def create_basic_info(memora: MemoraCreate, user_id: str) -> DBMemora:
        """Create a new Memora with basic information."""
        async with get_db() as db:
            # Create memora dict from model
            memora_data = memora.model_dump()
            
            db_memora = DBMemora(
                **memora_data,
                user_id=user_id,
                status=MemoraStatus.BASIC_INFO_COMPLETED,
                status_message="Basic information provided successfully"
            )

            db.add(db_memora)
            await db.commit()
            await db.refresh(db_memora)
            return db_memora

    @staticmethod
    async def process_video(memora_id: int, video_file: UploadFile) -> Optional[DBMemora]:
        """Process voice data for a Memora."""
        async with get_db() as db:
            stmt = select(DBMemora).filter(DBMemora.id == memora_id)
            result = await db.execute(stmt)
            db_memora = result.scalar_one_or_none()
            
            if not db_memora:
                return None

            try:
                # Save video file with original extension
                original_extension = video_file.filename.split('.')[-1].lower()
                video_filename = f"memora_{memora_id}_video.{original_extension}"
                video_path = await FileHandler.save_upload_file(video_file, video_filename)
                db_memora.video_path = video_path

                # Extract audio from video (output will be WAV)
                audio_filename = f"memora_{memora_id}_audio.wav"
                audio_path = await FileHandler.extract_audio(video_path, audio_filename)
                db_memora.audio_path = audio_path

                logger.info(f"Creating voice clone for memora {db_memora.full_name}")

                voice_clone = await ElevenLabsHandler().create_voice_clone(
                    name=db_memora.full_name,
                    audio_path=audio_path,
                    description=f"Voice clone for memora {db_memora.full_name}"
                )

                logger.info(f"Voice clone created for memora {db_memora.full_name} with voice_id {voice_clone['voice_id']}")

                db_memora.voice_clone_id = voice_clone["voice_id"]

                db_memora.status = MemoraStatus.VIDEO_INFO_COMPLETED
                db_memora.status_message = "Video processed and audio extracted successfully"
                await db.commit()
                await db.refresh(db_memora)
                return db_memora
            except Exception as e:
                db_memora.status = MemoraStatus.ERROR_PROCESSING_VIDEO
                db_memora.status_message = f"Video processing failed: {str(e)}"
                await db.commit()
                return db_memora


    @staticmethod
    async def process_social_media_async(memora_id, file_path, language):
        """Process social media data asynchronously"""
        try:
            # Convert the synchronous function call to asynchronous
            await asyncio.to_thread(process_social_media_data, memora_id, file_path, language)
            
            async with get_db() as db:
                # Update memora status after processing
                stmt = select(DBMemora).filter(DBMemora.id == memora_id)
                result = await db.execute(stmt)
                db_memora = result.scalar_one_or_none()
                
                if db_memora:
                    db_memora.status = MemoraStatus.SOCIALMEDIA_DATA_COMPLETED
                    db_memora.status_message = "Social media data processed successfully"
                    await db.commit()
                    await db.refresh(db_memora)
                
        except Exception as e:
            logger.error(f"Error processing social media data: {str(e)}")
            async with get_db() as db:
                stmt = select(DBMemora).filter(DBMemora.id == memora_id)
                result = await db.execute(stmt)
                db_memora = result.scalar_one_or_none()
                
                if db_memora:
                    db_memora.status = MemoraStatus.ERROR
                    db_memora.status_message = f"Error processing social media data: {str(e)}"
                    await db.commit()
                    await db.refresh(db_memora)


    @staticmethod
    async def process_social_media(
        memora_id: int,
        zip_file: UploadFile,
        background_tasks: BackgroundTasks
    ) -> Optional[DBMemora]:
        """Process social media data for a Memora."""
        async with get_db() as db:
            stmt = select(DBMemora).filter(DBMemora.id == memora_id)
            result = await db.execute(stmt)
            db_memora = result.scalar_one_or_none()
            
            if not db_memora:
                return None

            try:
                # Update status immediately
                db_memora.status = MemoraStatus.PROCESSING_SOCIALMEDIA_DATA
                db_memora.status_message = "Started processing social media data"
                await db.commit()
                await db.refresh(db_memora)
                
                # Save file first
                filename = f"memora_{memora_id}.zip"
                file_path = await FileHandler.save_upload_file(zip_file, filename)
                
                # Add processing task to background tasks instead of using multiprocessing
                background_tasks.add_task(
                    process_social_media_data,
                    memora_id,
                    file_path,
                    db_memora.language
                )
                
                return db_memora
            except Exception as e:
                db_memora.status = MemoraStatus.ERROR
                db_memora.status_message = f"Social media processing failed: {str(e)}"
                await db.commit()
                await db.refresh(db_memora)
                return db_memora

    @staticmethod
    async def get_memora(memora_id: int) -> Optional[DBMemora]:
        """Get a single Memora by ID."""
        async with get_db() as db:
            stmt = select(DBMemora).filter(DBMemora.id == memora_id)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()

    @staticmethod
    async def get_memoras(
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[DBMemora]:
        """Get all Memoras owned by a user."""
        async with get_db() as db:
            stmt = select(DBMemora)\
                .filter(DBMemora.user_id == user_id)\
                .offset(skip).limit(limit)
            result = await db.execute(stmt)
            return result.scalars().all()

    @staticmethod
    async def update_memora(
        memora_id: int,
        memora: MemoraUpdate
    ) -> Optional[DBMemora]:
        """Update a Memora's information."""
        async with get_db() as db:
            stmt = select(DBMemora).filter(DBMemora.id == memora_id)
            result = await db.execute(stmt)
            db_memora = result.scalar_one_or_none()
            
            if db_memora:
                update_data = memora.model_dump(exclude_unset=True)
                for field, value in update_data.items():
                    setattr(db_memora, field, value)

                await db.commit()
                await db.refresh(db_memora)
            return db_memora

    @staticmethod
    async def delete_memora(memora_id: int) -> bool:
        """Delete a Memora."""
        async with get_db() as db:
            stmt = select(DBMemora).filter(DBMemora.id == memora_id)
            result = await db.execute(stmt)
            db_memora = result.scalar_one_or_none()
            
            if db_memora:
                await db.delete(db_memora)
                await db.commit()
                return True
            return False

    @staticmethod
    async def is_owner(memora_id: int, user_id: str) -> bool:
        """Check if a user is the owner of a Memora."""
        async with get_db() as db:
            stmt = select(DBMemora).filter(
                DBMemora.id == memora_id,
                DBMemora.user_id == user_id
            )
            result = await db.execute(stmt)
            return result.scalar_one_or_none() is not None

    @staticmethod
    async def can_access(memora_id: int, user_id: str) -> bool:
        """Check if a user can access a Memora based on privacy settings."""
        async with get_db() as db:
            stmt = select(DBMemora).filter(DBMemora.id == memora_id)
            result = await db.execute(stmt)
            memora = result.scalar_one_or_none()
            
            if not memora:
                return False
            
            # Owner can always access
            if memora.user_id == user_id:
                return True
            
            # Check privacy settings
            if memora.privacy_status == PrivacyStatus.PUBLIC:
                return True
            elif memora.privacy_status == PrivacyStatus.PRIVATE:
                return False
            # For RESTRICTED status, you might want to add additional logic here
            
            return False

    @staticmethod
    async def get_accessible_memoras(
        user_id: str, 
        skip: int = 0, 
        limit: int = 100, 
        name: Optional[str] = None,
        privacy_status: Optional[str] = None,
        has_chat: Optional[bool] = None
    ) -> List[DBMemora]:
        """Get memoras accessible by a user with optional filters"""
        async with get_db() as db:
            if privacy_status and privacy_status == PrivacyStatus.PRIVATE:
                # For private memoras, check user ownership and shared_with
                query = select(DBMemora).where(cast(DBMemora.shared_with, Text).contains(user_id))
                query = query.where(DBMemora.user_id != user_id)
            else:
                # Default to public memoras
                query = select(DBMemora).where(DBMemora.privacy_status == PrivacyStatus.PUBLIC)

            # Apply name filter if provided
            if name:
                query = query.where(DBMemora.name.ilike(f"%{name}%"))

            # Apply has_chat filter if provided
            if has_chat:
                # Assuming you have a Message model with a memora_id field
                message_subquery = (
                    select(DBMessage.memora_id)
                    .where(DBMessage.sent_by_id == user_id)
                    .group_by(DBMessage.memora_id)
                    .scalar_subquery()
                )
                query = query.where(DBMemora.id.in_(message_subquery))

            # Show only concluded memoras
            query = query.where(DBMemora.status == MemoraStatus.CONCLUDED)

            # Apply pagination
            query = query.offset(skip).limit(limit)
            
            result = await db.execute(query)
            return list(result.scalars().all())

    @staticmethod
    async def get_user_memoras(user_id: str, skip: int = 0, limit: int = 100) -> List[DBMemora]:
        """Get memoras owned by a specific user"""
        async with get_db() as db:
            query = select(DBMemora).where(
                DBMemora.user_id == user_id
            ).offset(skip).limit(limit)
            result = await db.execute(query)
            return list(result.scalars().all())

    @staticmethod
    async def share_memora(memora_id: int, owner_id: str, share_with_id: str) -> Optional[DBMemora]:
        """Share a memora with another user"""
        async with get_db() as db:
            # Check if memora exists and user is the owner
            stmt = select(DBMemora).filter(
                DBMemora.id == memora_id,
                DBMemora.user_id == owner_id
            )
            result = await db.execute(stmt)
            memora = result.scalar_one_or_none()
            
            if not memora:
                return None
            
            # Add user to shared_with if not already there
            if share_with_id not in memora.shared_with:
                memora.shared_with = memora.shared_with + [share_with_id]
                await db.commit()
                await db.refresh(memora)
            
            return memora

    @staticmethod
    async def unshare_memora(memora_id: int, owner_id: str, unshare_with_id: str) -> Optional[DBMemora]:
        """Remove sharing access for a user"""
        async with get_db() as db:
            stmt = select(DBMemora).filter(
                DBMemora.id == memora_id,
                DBMemora.user_id == owner_id
            )
            result = await db.execute(stmt)
            memora = result.scalar_one_or_none()
            
            if not memora:
                return None
            
            # Remove user from shared_with if present
            if unshare_with_id in memora.shared_with:
                memora.shared_with = [uid for uid in memora.shared_with if uid != unshare_with_id]
                await db.commit()
                await db.refresh(memora)
            
            return memora

    @staticmethod
    async def get_shared_users(memora_id: int, owner_id: str) -> Optional[List[str]]:
        """Get list of users a memora is shared with"""
        async with get_db() as db:
            stmt = select(DBMemora).filter(
                DBMemora.id == memora_id,
                DBMemora.user_id == owner_id
            )
            result = await db.execute(stmt)
            memora = result.scalar_one_or_none()
            
            if not memora:
                return None
            
            return memora.shared_with 

    @staticmethod
    async def retry_analysis(memora_id: int) -> Optional[DBMemora]:
        """Retry processing a failed memora."""
        async with get_db() as db:
            stmt = select(DBMemora).filter(DBMemora.id == memora_id)
            result = await db.execute(stmt)
            db_memora = result.scalar_one_or_none()
            
            if not db_memora:
                return None

            try:
                db_path = f"memora_{memora_id}.db"
                
                logger.info(f"Analyzing memora {memora_id} with db_path {db_path}")

                analyzer = UserAnalyzer(db_path)
                analysis_results = analyzer.analyze_user(db_memora.language)
                
                db_memora.bio = analysis_results["short_bio"]
                db_memora.description = analysis_results["detailed_profile"]
                db_memora.speak_pattern = analysis_results["speak_pattern"]
                db_memora.status = MemoraStatus.CONCLUDED

                await db.commit()
                
                return db_memora
            except Exception as e:
                import traceback
                traceback.print_exc()
                db_memora.status = MemoraStatus.CONCLUDED_WITH_ANALYZER_ERROR
                db_memora.status_message = f"Retry failed: {str(e)}"
                await db.commit()
                await db.refresh(db_memora)
                return db_memora 

    @staticmethod
    async def get_shared_with_users(memora_id: int) -> Optional[List[UserResponse]]:
        """Get detailed information about users a memora is shared with"""
        async with get_db() as db:
            # First get the memora to access shared_with list
            stmt = select(DBMemora).filter(DBMemora.id == memora_id)
            result = await db.execute(stmt)
            memora = result.scalar_one_or_none()
            
            if not memora:
                return None
            
            # Get user details for each shared_with user_id
            if not memora.shared_with:
                return []
            
            stmt = select(User).filter(User.id.in_(memora.shared_with))
            result = await db.execute(stmt)
            users = result.scalars().all()
            
            return [UserResponse.model_validate(user) for user in users] 