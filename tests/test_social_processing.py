import asyncio
import os
from app.tasks.social_media_processor import process_social_media_data

async def run_test():    
    try:
        # Path to the Instagram ZIP file
        zip_path = "instagram-dhicorrea-2025-02-22-ljmQ7A49.zip"
        
        if not os.path.exists(zip_path):
            print(f"Error: ZIP file not found at {zip_path}")
            return

        # Process the file
        await process_social_media_data(1, zip_path, 'pt')
    except Exception as e:
        print(f"Error during test: {str(e)}")

if __name__ == "__main__":
    asyncio.run(run_test()) 