import asyncio
import sys
import os
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.memora import Memora, MemoraStatus, PrivacyStatus
from app.tasks.social_media_processor import process_social_media_data
from datetime import date

async def run_test():
    # Setup
    db = SessionLocal()
    
    try:
        # Path to the Instagram ZIP file
        zip_path = "instagram-dhicorrea-2025-02-20-BQ4hVhzx.zip"
        
        if not os.path.exists(zip_path):
            print(f"Error: ZIP file not found at {zip_path}")
            return

        # Process the file
        await process_social_media_data(db, 1, zip_path, 'pt')
    except Exception as e:
        print(f"Error during test: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(run_test()) 