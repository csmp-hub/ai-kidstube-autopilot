# scripts klasöründe yeni dosya: add_metadata.py
# İçeriği yapıştır:

# scripts/add_metadata.py
# ====================
"""
Add TikTok-optimized metadata to video using FFmpeg
"""
import subprocess
from pathlib import Path
from typing import Optional
from utils.config import config
from utils.logger import logger


def add_tiktok_metadata(
    video_path: Path,
    title: str,
    description: str,
    hashtags: list[str],
    output_path: Path = None
) -> Path:
    """
    Embed metadata into video file for better TikTok discovery
    
    Metadata fields:
    - title: Video title
    - description: Short description  
    - comment: Hashtags space-separated
    - genre: Education (for kids content)
    - encoding_tool: Our autopilot identifier
    """
    if output_path is None:
        output_path = video_path.parent / f"{video_path.stem}_meta{video_path.suffix}"
    
    # Prepare metadata arguments
    metadata_args = [
        "-metadata", f"title={title}",
        "-metadata", f"description={description}",
        "-metadata", "genre=Education",
        "-metadata", f"comment={' '.join(hashtags)}",
        "-metadata", "encoding_tool=AI-KidsTube-Autopilot-v2",
        "-metadata", "artist=AI-KidsTube",  # Channel name placeholder
    ]
    
    # FFmpeg command: copy streams (no re-encode) + add metadata
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-c", "copy",  # Stream copy = fast, no quality loss
        *metadata_args,
        "-y",  # Overwrite output
        str(output_path)
    ]
    
    logger.info(f"Adding metadata to: {video_path.name}")
    logger.debug(f"Title: {title}")
    logger.debug(f"Hashtags: {hashtags}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=30
        )
        
        if not output_path.exists():
            raise RuntimeError("FFmpeg completed but output not created")
        
        new_size = output_path.stat().st_size
        logger.info(f"✅ Metadata added: {output_path.name} ({new_size / 1024 / 1024:.1f} MB)")
        return output_path
        
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg metadata failed: {e.stderr[:200]}")
        logger.warning("Returning original video without metadata")
        return video_path
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return video_path


def generate_hashtags(script: dict) -> list[str]:
    """
    Generate relevant hashtags from script topic
    """
    base_tags = [
        "#eğitici", "#çocuk", "#okulöncesi", "#öğreniyorum",
        "#kids", "#learning", "#toddler", "#preschool"
    ]
    
    topic = script.get("topic", "").lower()
    
    # Topic-specific tags
    topic_tags = {
        "renk": ["#renkler", "#colors", "#mavi", "#kırmızı"],
        "sayı": ["#sayılar", "#numbers", "#sayma", "#math"],
        "şekil": ["#şekiller", "#shapes", "#geometri"],
        "hayvan": ["#hayvanlar", "#animals", "#sesler"],
        "meyve": ["#meyveler", "#fruits", "#sağlıklı"],
    }
    
    # Match topic to tags
    extra_tags = []
    for keyword, tags in topic_tags.items():
        if keyword in topic:
            extra_tags.extend(tags)
            break
    
    # Combine and deduplicate
    all_tags = list(dict.fromkeys(base_tags + extra_tags + script.get("hashtags", [])))
    
    # Limit to 10 tags (TikTok best practice)
    return all_tags[:10]


if __name__ == "__main__":
    # Test with dummy video
    print("🏷️  Metadata module ready")
    print("💡 Run via main pipeline")
# ====================
# Dosyayı kaydet ✅