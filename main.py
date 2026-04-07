# Proje ana klasöründe yeni dosya: main.py
# İçeriği yapıştır:

# main.py
# ====================
#!/usr/bin/env python3
"""
AI-KidsTube Autopilot - Main Pipeline Entry Point
Generates one educational kids video per day, fully automated
"""
import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.config import config
from utils.logger import logger, setup_logger
from scripts.generate_script import generate_daily_script, save_script
from scripts.generate_voice import generate_script_voices
from scripts.generate_images import generate_script_images
from scripts.create_video import create_video, compress_video_if_needed
from scripts.add_metadata import add_tiktok_metadata, generate_hashtags
from scripts.send_telegram import send_to_telegram


def main() -> int:
    """
    Execute full video generation pipeline
    Returns exit code: 0=success, 1=error
    """
    # Setup logging
    setup_logger(config.LOG_LEVEL if hasattr(config, 'LOG_LEVEL') else "INFO")
    
    logger.info("🚀 AI-KidsTube Autopilot starting", version="2.0")
    
    # Step 0: Validate configuration
    if not config.is_ready():
        missing = config.validate()
        logger.error(f"❌ Configuration incomplete: {missing}")
        logger.error("💡 Set environment variables in GitHub Secrets")
        return 1
    
    logger.info("✅ Configuration validated")
    
    try:
        # Step 1: Generate script
        logger.info("📝 Step 1/6: Generating script...")
        script = generate_daily_script()
        script_path = save_script(script)
        logger.info(f"✅ Script: {script['title']}")
        
        # Step 2: Generate voiceovers
        logger.info("🎤 Step 2/6: Generating voiceovers...")
        audio_paths = generate_script_voices(script)
        logger.info(f"✅ Generated {len(audio_paths)} voice files")
        
        # Step 3: Generate images
        logger.info("🎨 Step 3/6: Generating images...")
        image_paths = generate_script_images(script)
        logger.info(f"✅ Generated {len(image_paths)} images")
        
        # Step 4: Assemble video
        logger.info("🎬 Step 4/6: Assembling video...")
        video_path = create_video(script, image_paths, audio_paths)
        logger.info(f"✅ Video created: {video_path.name}")
        
        # Step 5: Compress if needed + add metadata
        logger.info("🗜️  Step 5/6: Optimizing video...")
        video_path = compress_video_if_needed(video_path)
        
        hashtags = generate_hashtags(script)
        video_path = add_tiktok_metadata(
            video_path,
            title=script["title"],
            description=f"Eğitici çocuk videosu: {script['topic']}",
            hashtags=hashtags
        )
        logger.info(f"✅ Optimized: {video_path.name}")
        
        # Step 6: Upload to Telegram
        logger.info("📤 Step 6/6: Uploading to Telegram...")
        caption = f"""🎬 *Yeni Video Hazır!*

📚 {script['title']}
🎯 Konu: {script['topic']}
⏱️ Süre: {script.get('duration_seconds', '~20')} saniye
🏷️ {', '.join(hashtags[:5])}

✅ İndir, kontrol et, beğenirsen TikTok/YouTube'a yükle!"""
        
        success = send_to_telegram(video_path, caption=caption)
        
        if success:
            logger.info("✅ Pipeline completed successfully! 🎉")
            logger.info(f"📱 Check your Telegram for: {video_path.name}")
            return 0
        else:
            logger.warning("⚠️ Video created but Telegram upload failed")
            logger.info(f"💾 Video saved locally: {video_path}")
            return 0  # Still success - video was made
            
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {type(e).__name__}: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
# ====================
# Dosyayı kaydet ✅