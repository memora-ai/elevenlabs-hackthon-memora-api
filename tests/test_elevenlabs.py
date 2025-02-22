import asyncio
from app.utils.elevenlabs_handler import ElevenLabsHandler, OutputFormat, TextNormalization

async def test_elevenlabs():
    handler = ElevenLabsHandler()
    
    try:
        voice_id = "cGtQADqFzUJmjeSxrGkT"

        if not voice_id:
            # Step 1: Create voice clone
            print("Creating voice clone...")
            clone_result = await handler.create_voice_clone(
                name="Test Voice",
                audio_path="uploads/memora_1_audio.wav",
                description="Voz teste em português",
                labels={"language": "portuguese", "gender": "male"},
                remove_background_noise=True
            )
            
            voice_id = clone_result["voice_id"]
            print(f"Voice clone created with ID: {voice_id}")
        
        # Step 2: Get voice details
        print("\nGetting voice details...")
        voice_details = await handler.get_voice(voice_id)
        print(f"Voice details: {voice_details}")
        
        # Step 3: Generate speech
        print("\nGenerating speech...")
        text = """
        Olá! Tudo bem? Estou muito feliz em poder falar com você hoje. 
        A tecnologia é incrível, não é mesmo? Podemos criar vozes que soam 
        naturais e expressivas. Espero que você esteja gostando desta demonstração.
        """
        
        audio_data = await handler.create_speech(
            voice_id=voice_id,
            text=text,
            model_id="eleven_multilingual_v2",
            output_format=OutputFormat.mp3_44100_192,
            language_code="pt",
            text_normalization=TextNormalization.AUTO
        )
        
        # Save the generated audio
        output_path = "test_output.mp3"
        with open(output_path, "wb") as f:
            f.write(audio_data)
        
        print(f"\nSpeech generated and saved to: {output_path}")
        
    except Exception as e:
        print(f"Error during test: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_elevenlabs()) 