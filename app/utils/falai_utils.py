import os
import logging
import fal_client
from typing import Dict, Any, Callable, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

os.environ["FAL_KEY"] = settings.FALAI_APIKEY

async def sync_lipsync(
    video_url: str,
    audio_url: str,
):
    logger.info(f'Starting to encode video and audio files {video_url} and {audio_url}')

    if not video_url.startswith('https'):
        video_url = fal_client.upload_file(video_url)
    if not audio_url.startswith('https'):
        audio_url = fal_client.upload_file(audio_url)

    handler = await fal_client.submit_async(
        "fal-ai/latentsync",
        arguments={
            "video_url": video_url,
            "audio_url": audio_url,
            # "loop_mode": "loop"
        },
    )

    async for event in handler.iter_events(with_logs=True, interval=0.5):
        logger.info(event)

    result = await handler.get()

    return {
        'input_video_url': video_url,
        'input_audio_url': audio_url,
        'output_video_url': result['video']['url']
    }