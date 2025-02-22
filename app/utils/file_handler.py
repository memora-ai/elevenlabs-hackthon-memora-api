import os
import shutil
from fastapi import UploadFile
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
            # Ensure the uploads directory exists
            os.makedirs("uploads", exist_ok=True)
            audio_path = os.path.join("uploads", audio_filename)
            
            # Use ffmpeg for all video formats
            import subprocess
            command = [
                'ffmpeg', '-i', video_path,
                '-vn',  # No video
                '-acodec', 'pcm_s16le',  # Convert to PCM WAV
                '-ar', '44100',  # 44.1kHz sample rate
                '-ac', '1',  # Mono
                '-y',  # Overwrite output file if it exists
                audio_path
            ]
            process = subprocess.run(command, capture_output=True, text=True)
            if process.returncode != 0:
                raise Exception(f"FFmpeg error: {process.stderr}")
            
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