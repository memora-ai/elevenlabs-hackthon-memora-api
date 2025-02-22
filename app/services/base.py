from sqlalchemy.ext.asyncio import AsyncSession
from typing import Generic, TypeVar, Type, Optional, List, Dict, Any
from pydantic import BaseModel
from sqlalchemy import select, and_
from fastapi import HTTPException

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Base class for services with common CRUD operations.
    Includes user ownership and permission checks.
    """
    
    def __init__(self, model: Type[ModelType]):
        """
        Initialize service with model type.
        
        Args:
            model: The SQLAlchemy model class
        """
        self.model = model

    async def get(
        self, 
        db: AsyncSession, 
        id: Any,
        user_id: Optional[str] = None
    ) -> Optional[ModelType]:
        """
        Get a single record by ID, optionally checking user ownership.
        
        Args:
            db: AsyncSession for database operations
            id: ID of the record to get
            user_id: Optional user ID to check ownership
            
        Returns:
            Optional[ModelType]: The requested record if found and accessible
        """
        conditions = [self.model.id == id]
        if user_id is not None and hasattr(self.model, 'user_id'):
            conditions.append(self.model.user_id == user_id)
            
        stmt = select(self.model).filter(and_(*conditions))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        user_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """
        Get multiple records with optional filtering and pagination.
        
        Args:
            db: AsyncSession for database operations
            user_id: Optional user ID to filter by ownership
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Optional dictionary of filter conditions
            
        Returns:
            List[ModelType]: List of matching records
        """
        conditions = []
        if user_id is not None and hasattr(self.model, 'user_id'):
            conditions.append(self.model.user_id == user_id)
            
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    conditions.append(getattr(self.model, field) == value)

        stmt = select(self.model)
        if conditions:
            stmt = stmt.filter(and_(*conditions))
        stmt = stmt.offset(skip).limit(limit)
        
        result = await db.execute(stmt)
        return result.scalars().all()

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: CreateSchemaType,
        user_id: Optional[str] = None
    ) -> ModelType:
        """
        Create a new record.
        
        Args:
            db: AsyncSession for database operations
            obj_in: Create schema with new record data
            user_id: Optional user ID to set as owner
            
        Returns:
            ModelType: The created record
        """
        obj_in_data = obj_in.model_dump()
        if user_id is not None and hasattr(self.model, 'user_id'):
            obj_in_data['user_id'] = user_id
            
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | Dict[str, Any],
        user_id: Optional[str] = None
    ) -> ModelType:
        """
        Update a record, optionally verifying user ownership.
        
        Args:
            db: AsyncSession for database operations
            db_obj: Existing record to update
            obj_in: Update data
            user_id: Optional user ID to verify ownership
            
        Returns:
            ModelType: The updated record
            
        Raises:
            HTTPException: If user_id provided and doesn't match record ownership
        """
        if user_id is not None and hasattr(db_obj, 'user_id'):
            if db_obj.user_id != user_id:
                raise HTTPException(status_code=403, detail="Not authorized to modify this record")

        obj_data = db_obj.__dict__
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
            
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
                
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(
        self,
        db: AsyncSession,
        *,
        id: Any,
        user_id: Optional[str] = None
    ) -> Optional[ModelType]:
        """
        Delete a record, optionally verifying user ownership.
        
        Args:
            db: AsyncSession for database operations
            id: ID of the record to delete
            user_id: Optional user ID to verify ownership
            
        Returns:
            Optional[ModelType]: The deleted record if found and accessible
        """
        obj = await self.get(db, id, user_id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj

    async def exists(
        self,
        db: AsyncSession,
        id: Any,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Check if a record exists and is accessible to the user.
        
        Args:
            db: AsyncSession for database operations
            id: ID of the record to check
            user_id: Optional user ID to verify ownership
            
        Returns:
            bool: True if record exists and is accessible
        """
        obj = await self.get(db, id, user_id)
        return obj is not None 