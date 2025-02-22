import logging
import zipfile
import os
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from PIL import Image
import whisper
from mutagen import File as MutagenFile
from transformers import BlipProcessor, BlipForConditionalGeneration

# Group app imports together
from app.agents.user_analyzer import UserAnalyzer
from app.models.memora import DBMemora, MemoraStatus
from app.utils.db_handler import DatabaseHandler
from app.core.database import get_db

logger = logging.getLogger(__name__)

async def setup_document_converter():
    """Configure and return a DocumentConverter instance"""
    logger.info("Setting up DocumentConverter...")
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True

    converter = DocumentConverter(
        allowed_formats=[
            InputFormat.IMAGE,
            InputFormat.HTML
        ]
    )
    logger.info("DocumentConverter setup completed")
    return converter

async def setup_image_model():
    """Configure and return image processing models"""
    logger.info("Setting up BLIP image captioning models...")
    processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
    logger.info("BLIP models setup completed")
    return processor, model

async def get_description_from_image(image: Image.Image, processor, model) -> str:
    """Get description from image using BLIP model"""
    try:
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        inputs = processor(image, return_tensors="pt")
        output = model.generate(**inputs)
        description = processor.decode(output[0], skip_special_tokens=True)
        return description
    except Exception as e:
        logger.error("Error getting image description: %s", str(e))
        return ""

async def setup_whisper_model():
    """Configure and return Whisper model"""
    logger.info("Setting up Whisper model...")
    model = whisper.load_model("base")
    logger.info("Whisper model setup completed")
    return model

async def process_audio_file(file_path: str, whisper_model) -> dict:
    """Process audio file using Whisper for transcription and metadata"""
    try:
        audio = MutagenFile(file_path)
        metadata = {
            "length": audio.info.length if audio else None,
            "bitrate": audio.info.bitrate if audio else None,
            "type": "audio"
        }
        
        logger.info("Transcribing audio file: %s", file_path)
        result = await whisper_model.transcribe(file_path)
        
        return {
            "path": file_path,
            "metadata": metadata,
            "text": result["text"],
            "segments": result["segments"],
            "language": result["language"],
            "media_type": "audio"
        }
    except Exception as e:
        logger.error("Error processing audio file %s: %s", file_path, str(e))
        return {
            "path": file_path,
            "metadata": {},
            "text": "",
            "segments": [],
            "language": "",
            "media_type": "audio"
        }

async def process_files_batch(file_paths: list[str]) -> list[dict]:
    """Process a batch of files using Docling"""
    try:
        logger.info("Starting batch processing of %d files", len(file_paths))
        
        # Setup models based on file types
        image_processor = None
        image_model = None
        whisper_model = None
        
        # Group files by type
        image_files = []
        audio_files = []
        video_files = []
        
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
        audio_extensions = {'.mp3', '.wav', '.ogg'}
        video_extensions = {'.webm', '.mp4', '.mov', '.avi'}
        
        for file_path in file_paths:
            ext = Path(file_path).suffix.lower()
            if ext in image_extensions:
                image_files.append(file_path)
            elif ext in audio_extensions:
                audio_files.append(file_path)
            elif ext in video_extensions:
                video_files.append(file_path)
        
        # Load required models
        if image_files:
            image_processor, image_model = await setup_image_model()
        if audio_files:
            whisper_model = await setup_whisper_model()
        
        results = []
        
        # Process audio files
        for file_path in audio_files:
            logger.info("Processing audio file: %s", file_path)
            result = await process_audio_file(file_path, whisper_model)
            results.append(result)
        
        # Process image files
        for file_path in image_files:
            try:
                with Image.open(file_path) as img:
                    metadata = {
                        "size": img.size,
                        "format": img.format,
                        "mode": img.mode,
                        "type": "image"
                    }
                    media_description = ""
                    if image_processor and image_model:
                        logger.info("Getting description from image %s", file_path)
                        media_description = await get_description_from_image(img, image_processor, image_model)
                    
                    results.append({
                        "path": file_path,
                        "metadata": metadata,
                        "media_description": media_description,
                        "media_type": "image"
                    })
            except Exception as e:
                logger.error("Error processing image %s: %s", file_path, str(e))
        
        # Process video files (metadata only for now)
        #for file_path in video_files:
        #    try:                
        #        results.append({
        #            "path": file_path,
        #            "metadata": metadata,
        #            "media_description": "",
        #            "media_type": "video"
        #        })
        #    except Exception as e:
        #        logger.error("Error processing video %s: %s", file_path, str(e))

        logger.info("Batch processing completed. Successfully processed %d files", len(results))
        return results
    except Exception as e:
        logger.error("Error in batch processing: %s", str(e))
        return []

async def scan_files(extract_path):
    """Scan extracted files and categorize them by extension"""
    logger.info("Starting file scan in %s", extract_path)
    file_mapping = {
        'html': [], 'json': [],
        'png': [], 'jpg': [], 'jpeg': [], 'gif': [], 'bmp': [], 'webp': [],
        'webm': [], 'mp4': [], 'mov': [], 'avi': [],
        'mp3': [], 'wav': [], 'ogg': []
    }
    
    total_files = 0
    for root, _, files in os.walk(extract_path):
        for file in files:
            total_files += 1
            file_path = os.path.join(root, file)
            extension = Path(file).suffix.lower()[1:]
            
            if extension in file_mapping:
                file_mapping[extension].append(file_path)
                logger.debug("Found %s file: %s", extension, file_path)
    
    logger.info("File scan completed. Found %d total files", total_files)
    for ext, files in file_mapping.items():
        if files:
            logger.info("- %d %s files", len(files), ext)
    
    return file_mapping

async def process_social_media_data(memora_id: int, file_path: str, language: str = 'en'):
    extract_path = None
    async with get_db() as db:
        try:
            db_path = f"memora_{memora_id}.db"
            
            if os.path.exists(db_path):
                logger.info("Database already exists for Memora %d, skipping to analysis", memora_id)
                
                db_memora = await db.execute(
                    select(DBMemora).filter(DBMemora.id == memora_id)
                )
                db_memora = db_memora.scalar_one_or_none()
                
                if not db_memora:
                    logger.error("Memora %d not found during async processing", memora_id)
                    return
                
                try:
                    logger.info("Starting user analysis for Memora %d in language %s", memora_id, language)
                    analyzer = UserAnalyzer(db_path)
                    analysis_results = analyzer.analyze_user(language)
                    
                    db_memora.bio = analysis_results["short_bio"]
                    db_memora.description = analysis_results["detailed_profile"]
                    db_memora.speak_pattern = analysis_results["speak_pattern"]
                    db_memora.status = MemoraStatus.CONCLUDED
                    await db.commit()
                    logger.info("User analysis completed and saved")
                except Exception as e:
                    logger.error("Error in user analysis: %s", str(e))
                    db_memora.status = MemoraStatus.CONCLUDED_WITH_ANALYZER_ERROR
                    db_memora.status_message = f"Error in user analysis: {str(e)}"
                    await db.commit()
                return

            # If database doesn't exist, continue with full processing
            extract_path = os.path.join(os.path.dirname(file_path), f"extract_memora_{memora_id}")
            os.makedirs(extract_path, exist_ok=True)
            
            logger.info("Starting to process ZIP file for Memora %d", memora_id)
            logger.info("Extraction directory: %s", extract_path)
            
            db_memora = await db.execute(
                select(DBMemora).filter(DBMemora.id == memora_id)
            )
            db_memora = db_memora.scalar_one_or_none()
            
            if not db_memora:
                logger.error("Memora %d not found during async processing", memora_id)
                return

            logger.info("Extracting ZIP file for Memora %d", memora_id)
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            logger.info("ZIP extraction completed")

            logger.info("Scanning extracted files for Memora %d", memora_id)
            file_mapping = await scan_files(extract_path)
            
            logger.info("Creating database for Memora %d", memora_id)
            connection_string = DatabaseHandler.create_memora_database(memora_id)
            
            all_results = []
            all_dataframes = {}
            
            if file_mapping['json']:
                logger.info("Processing %d JSON files...", len(file_mapping['json']))
                for json_file in file_mapping['json']:
                    logger.info("Processing JSON file: %s", json_file)
                    dfs = DatabaseHandler.process_json_file(json_file, extract_path)
                    all_dataframes.update(dfs)
                    logger.info("Extracted %d tables from %s", len(dfs), json_file)
            
            if file_mapping['html']:
                logger.info("Processing %d HTML files...", len(file_mapping['html']))
                for html_file in file_mapping['html']:
                    logger.info("Processing HTML file: %s", html_file)
                    dfs = DatabaseHandler.process_html_file(html_file, extract_path)
                    all_dataframes.update(dfs)
                    logger.info("Extracted %d tables from %s", len(dfs), html_file)
            
            if all_dataframes:
                logger.info("Saving %d tables to database...", len(all_dataframes))
                DatabaseHandler.save_dataframes(connection_string, all_dataframes)
                logger.info("Database save completed")

            # Process media files
            media_files = []
            for ext in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp']:
                media_files.extend(file_mapping[ext])
            
            if media_files:
                logger.info("Processing %d media files...", len(media_files))
                media_results = await process_files_batch(media_files)
                
                # Save media data to appropriate tables
                if media_results:
                    logger.info("Saving media data to tables...")
                    media_by_type = {}
                    for result in media_results:
                        media_type = result.get('media_type', 'unknown')
                        if media_type not in media_by_type:
                            media_by_type[media_type] = []
                        media_by_type[media_type].append(result)
                    
                    for media_type, type_results in media_by_type.items():
                        DatabaseHandler.save_media_data(connection_string, media_type, type_results)
                    logger.info("Media data save completed")

            status_message = (
                f"Social media data processed successfully. "
                f"Found: {sum(len(files) for files in file_mapping.values())} files "
                f"({', '.join(f'{len(files)} {ext}' for ext, files in file_mapping.items() if len(files) > 0)}). "
                f"Processed {len(all_results)} files with content. "
                f"Created {len(all_dataframes) + (1 if media_files else 0)} database tables."
            )
            
            logger.info("Updating Memora %d status to CONCLUDED", memora_id)
            db_memora.status = MemoraStatus.CONCLUDED
            db_memora.status_message = status_message
            await db.commit()

            logger.info("Successfully processed social media data for Memora %d", memora_id)

            # After processing all media and saving to database
            if db_memora.status != MemoraStatus.ERROR:
                try:
                    logger.info("Starting user analysis for Memora %d in language %s", memora_id, language)
                    analyzer = UserAnalyzer(db_path)
                    analysis_results = analyzer.analyze_user(language)
                    
                    # Save analysis results to memora record
                    db_memora.bio = analysis_results["short_bio"]
                    db_memora.description = analysis_results["detailed_profile"]
                    db_memora.speak_pattern = analysis_results["speak_pattern"]

                    await db.commit()
                    logger.info("User analysis completed and saved")
                except Exception as e:
                    logger.error("Error in user analysis: %s", str(e))
                    db_memora.status = MemoraStatus.CONCLUDED_WITH_ANALYZER_ERROR
                    db_memora.status_message = f"Error in user analysis: {str(e)}"
                    await db.commit()

        except Exception as e:
            logger.error("Error processing social media data for Memora %d: %s", memora_id, str(e))
            
            db_memora = await db.execute(
                select(DBMemora).filter(DBMemora.id == memora_id)
            )
            db_memora = db_memora.scalar_one_or_none()
            
            if db_memora:
                logger.info("Updating Memora %d status to ERROR", memora_id)
                db_memora.status = MemoraStatus.ERROR
                db_memora.status_message = f"Social media processing failed: {str(e)}"
                await db.commit()
        
        finally:
            logger.info("Starting cleanup...")
            if extract_path and os.path.exists(extract_path):
                import shutil
                shutil.rmtree(extract_path)
            logger.info("Cleanup completed") 