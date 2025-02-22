import requests
import logging
import os
import json
from typing import List, Optional, Dict
from app.core.config import settings
from enum import Enum

logger = logging.getLogger(__name__)

class OutputFormat(str, Enum):
    mp3_22050_32 = "mp3_22050_32"
    mp3_44100_32 = "mp3_44100_32"
    mp3_44100_64 = "mp3_44100_64"
    mp3_44100_96 = "mp3_44100_96"
    mp3_44100_128 = "mp3_44100_128"
    mp3_44100_192 = "mp3_44100_192"
    pcm_16000 = "pcm_16000"

class TextNormalization(str, Enum):
    AUTO = "auto"
    ON = "on"
    OFF = "off"

class ElevenLabsHandler:
    BASE_URL = "https://api.elevenlabs.io/v1"
    
    def __init__(self):
        self.api_key = settings.ELEVENLABS_APIKEY
        self.headers = {
            "xi-api-key": self.api_key
        }

    async def create_voice_clone(
        self,
        name: str,
        audio_path: str,
        description: Optional[str] = None,
        labels: Optional[Dict[str, str]] = {},
        remove_background_noise: bool = False
    ) -> Dict[str, str]:
        """
        Create a voice clone using ElevenLabs API
        
        Args:
            name: The name that identifies this voice
            audio_path: Path to the audio file for voice cloning
            description: Optional description of the voice
            labels: Optional dictionary of labels for the voice
            remove_background_noise: Whether to remove background noise from samples
            
        Returns:
            Dict containing voice_id and requires_verification status
        """
        try:
            url = f"{self.BASE_URL}/voices/add"
            
            # Read the audio file content first
            with open(audio_path, 'rb') as audio_file:
                audio_content = audio_file.read()
            
            # Prepare the form data
            form_data = {
                "name": (None, name),
                "remove_background_noise": (None, str(remove_background_noise).lower())
            }
            
            if description:
                form_data["description"] = (None, description)
                
            if labels:
                form_data["labels"] = (None, json.dumps(labels))
            
            # Add audio file to form data
            filename = os.path.basename(audio_path)
            form_data["files"] = (filename, audio_content, 'audio/wav')
            
            # Make the request
            response = requests.post(
                url,
                headers=self.headers,
                files=form_data,
                timeout=30
            )
            
            # Check for successful response
            response.raise_for_status()
            
            result = response.json()
            return {
                "voice_id": result["voice_id"],
                "requires_verification": result["requires_verification"]
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating voice clone: {str(e)}")
            if hasattr(e.response, 'json'):
                error_detail = e.response.json()
                logger.error(f"API Error details: {error_detail}")
            raise Exception(f"Failed to create voice clone: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error creating voice clone: {str(e)}")
            raise Exception(f"Unexpected error creating voice clone: {str(e)}")

    async def get_voice(self, voice_id: str) -> Dict:
        """
        Get metadata about a specific voice
        
        Args:
            voice_id: ID of the voice to retrieve
            
        Returns:
            Dict containing voice metadata including:
            - voice_id: Unique identifier of the voice
            - name: Name of the voice
            - samples: List of voice samples
            - category: Voice category
            - fine_tuning: Fine tuning settings
            - labels: Voice labels
            - description: Voice description
            - preview_url: URL to preview the voice
            - settings: Voice settings
            And other metadata fields
        """
        try:
            url = f"{self.BASE_URL}/voices/{voice_id}"
            
            response = requests.get(
                url,
                headers=self.headers,
                timeout=30
            )
            
            # Check for successful response
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting voice details: {str(e)}")
            if hasattr(e.response, 'json'):
                error_detail = e.response.json()
                logger.error(f"API Error details: {error_detail}")
            raise Exception(f"Failed to get voice details: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error getting voice details: {str(e)}")
            raise Exception(f"Unexpected error getting voice details: {str(e)}")

    async def create_speech(
        self,
        voice_id: str,
        text: str,
        model_id: str = "eleven_multilingual_v2",
        output_format: OutputFormat = OutputFormat.mp3_44100_32,
        voice_settings: Optional[Dict] = None,
        enable_logging: bool = True,
        text_normalization: TextNormalization = TextNormalization.AUTO,
        previous_text: Optional[str] = None,
        next_text: Optional[str] = None,
        previous_request_ids: Optional[List[str]] = None,
        next_request_ids: Optional[List[str]] = None,
        seed: Optional[int] = None,
    ) -> bytes:
        """
        Convert text to speech using ElevenLabs API
        
        Args:
            voice_id: ID of the voice to be used
            text: The text to convert to speech
            model_id: Identifier of the model to use
            output_format: The output format of the generated audio
            language_code: Optional language code (ISO 639-1)
            voice_settings: Optional voice settings overriding stored settings
            enable_logging: Whether to enable request logging
            text_normalization: Text normalization mode
            previous_text: Optional text that came before
            next_text: Optional text that comes after
            previous_request_ids: Optional list of previous request IDs
            next_request_ids: Optional list of next request IDs
            seed: Optional seed for deterministic generation
            
        Returns:
            bytes: The generated audio data
        """
        try:
            url = f"{self.BASE_URL}/text-to-speech/{voice_id}"
            
            # Prepare request payload
            payload = {
                "text": text,
                "model_id": model_id,
                "text_normalization": text_normalization
            }
            
            # Add optional parameters if provided
            if voice_settings:
                payload["voice_settings"] = voice_settings
            if previous_text:
                payload["previous_text"] = previous_text
            if next_text:
                payload["next_text"] = next_text
            if previous_request_ids:
                payload["previous_request_ids"] = previous_request_ids[:3]  # Max 3 allowed
            if next_request_ids:
                payload["next_request_ids"] = next_request_ids[:3]  # Max 3 allowed
            if seed is not None:
                payload["seed"] = max(0, min(seed, 4294967295))  # Ensure valid range
            
            # Add query parameters
            params = {
                "enable_logging": str(enable_logging).lower(),
                "output_format": output_format.value
            }
            
            # Make the request
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                params=params,
                timeout=30
            )
            
            # Check for successful response
            response.raise_for_status()
            
            return response.content
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating speech: {str(e)}")
            if hasattr(e.response, 'json'):
                error_detail = e.response.json()
                logger.error(f"API Error details: {error_detail}")
            raise Exception(f"Failed to create speech: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error creating speech: {str(e)}")
            raise Exception(f"Unexpected error creating speech: {str(e)}") 