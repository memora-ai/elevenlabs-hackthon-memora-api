import os
import shutil
from fastapi import UploadFile
from moviepy.editor import VideoFileClip
import base64

class FileHandler:
    UPLOAD_DIR = "uploads"

    @classmethod
    def ensure_upload_dir(cls):
        """Ensure the upload directory exists"""
        os.makedirs(cls.UPLOAD_DIR, exist_ok=True)

    @classmethod
    async def save_upload_file(cls, file: UploadFile, filename: str) -> str:
        """
        Save an uploaded file to the upload directory
        Returns the full path to the saved file
        """
        cls.ensure_upload_dir()
        file_path = os.path.join(cls.UPLOAD_DIR, filename)
        
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        finally:
            file.file.close()
            
        return file_path

    @classmethod
    def delete_file(cls, file_path: str):
        """Delete a file if it exists"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error deleting file {file_path}: {str(e)}")

    @staticmethod
    async def extract_audio(video_path: str, audio_filename: str) -> str:
        """Extract audio from video file and save it."""
        try:
            video = VideoFileClip(video_path)
            audio = video.audio
            
            # Ensure the uploads directory exists
            os.makedirs("uploads", exist_ok=True)
            
            # Save the audio file
            audio_path = os.path.join("uploads", audio_filename)
            audio.write_audiofile(audio_path)
            
            # Close the video file
            video.close()
            audio.close()
            
            return audio_path
        except Exception as e:
            raise Exception(f"Failed to extract audio: {str(e)}")

    @staticmethod
    async def save_base64_image(base64_string: str, filename: str) -> str:
        """Save base64 image data to a file and return the file path."""
        try:
            # Remove potential base64 header (e.g., 'data:image/jpeg;base64,')
            if ',' in base64_string:
                base64_string = base64_string.split(',')[1]
            
            # Decode base64 string
            image_data = base64.b64decode(base64_string)
            
            # Ensure the uploads directory exists
            os.makedirs("uploads", exist_ok=True)
            
            # Save the image file
            file_path = os.path.join("uploads", filename)
            with open(file_path, "wb") as f:
                f.write(image_data)
            
            return file_path
        except Exception as e:
            raise Exception(f"Failed to save base64 image: {str(e)}") 