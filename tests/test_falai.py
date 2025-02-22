import asyncio
from app.utils.falai_utils import sync_lipsync

async def test_sync_lipsync():
    # Define paths to test files
    audio_path = "uploads/memora_1_audio.wav"
    video_path = "uploads/memora_2_video.webm"

    result = await sync_lipsync(
        video_url=video_path,
        audio_url=audio_path,
    )

    print(result)
    print(type(result))

if __name__ == "__main__":
    asyncio.run(test_sync_lipsync()) 