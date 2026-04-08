# scripts/create_video.py
# ====================
"""
Assemble video from images, voice, and subtitles using MoviePy.
Fixed for Pillow 10+ compatibility and GitHub Actions environment.
"""
# =====================================================================
# IMPORTANT: Pillow 10+ compatibility fix must be at the very top!
# =====================================================================
from PIL import Image
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS
# =====================================================================

from moviepy.editor import (
    ImageClip, AudioFileClip, TextClip, CompositeVideoClip, concatenate_videoclips
)
from moviepy.config import change_settings
from pathlib import Path
from typing import Optional
import subprocess
from utils.config import config
from utils.logger import logger

# Fix ImageMagick policy for GitHub Actions
def configure_imagemagick():
    """Ensure ImageMagick can write files (fix policy.xml)"""
    policy_path = Path("/etc/ImageMagick-6/policy.xml")
    if policy_path.exists():
        try:
            content = policy_path.read_text()
            if 'pattern="PNG"' in content and 'rights="none"' in content:
                updated = content.replace(
                    'pattern="PNG" rights="none"',
                    'pattern="PNG" rights="read|write"'
                )
                try:
                    policy_path.write_text(updated)
                    logger.info("ImageMagick policy updated for PNG support")
                except PermissionError:
                    logger.warning("Could not update ImageMagick policy (permission denied)")
        except Exception as e:
            logger.warning(f"ImageMagick config check failed: {e}")

# Apply config on module load
configure_imagemagick()
change_settings({"IMAGEMAGICK_BINARY": "magick"})


def create_subtitle_clip(
    text: str, 
    duration: float,
    position: tuple = ("center", 0.85),
    fontsize: int = 48,
    font: str = "Arial-Bold",
    color: str = "white",
    stroke_color: str = "black",
    stroke_width: int = 2
) -> TextClip:
    """
    Create a subtitle TextClip with consistent styling.
    """
    # Use method="caption" for text wrapping
    return TextClip(
        text,
        fontsize=fontsize,
        font=font,
        color=color,
        stroke_color=stroke_color,
        stroke_width=stroke_width,
        method="caption",
        size=(int(config.VIDEO_RESOLUTION[0] * 0.9), None),
        align="center"
    ).set_position(position).set_duration(duration)


def create_scene_clip(
    image_path: Path,
    audio_path: Optional[Path],
    subtitle_text: str,
    duration: float
) -> CompositeVideoClip:
    """
    Create a single scene: image + optional audio + subtitle
    """
    # Load image as clip
    img_clip = ImageClip(str(image_path)).set_duration(duration)
    
    # Simple resize to fit height (width will adjust automatically)
    # Removed problematic resample_fn argument
    img_clip = img_clip.resize(height=config.VIDEO_RESOLUTION[1])
    img_clip = img_clip.set_position("center")
    
    # Add audio if provided
    if audio_path and audio_path.exists():
        audio_clip = AudioFileClip(str(audio_path))
        # Trim or loop audio to match duration
        if audio_clip.duration < duration:
            audio_clip = audio_clip.loop(duration)
        else:
            audio_clip = audio_clip.subclip(0, duration)
        img_clip = img_clip.set_audio(audio_clip)
    
    # Add subtitle if text provided
    if subtitle_text and subtitle_text.strip():
        subtitle = create_subtitle_clip(subtitle_text.strip(), duration)
        img_clip = CompositeVideoClip([img_clip, subtitle])
    
    return img_clip


def create_video(
    script: dict,
    image_paths: list[Path],
    audio_paths: list[Path],
    output_path: Path = None,
    add_closing: bool = True
) -> Path:
    """
    Assemble complete video from script, images, and audio
    Optimized for GitHub Actions
    """
    if output_path is None:
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = config.OUTPUT_DIR / f"video_{timestamp}.mp4"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Creating video: {output_path.name}")
    logger.debug(f"Input: {len(image_paths)} images, {len(audio_paths)} audio files")
    
    scenes = []
    
    # Process each scene
    for i, scene in enumerate(script.get("scenes", [])):
        if i >= len(image_paths):
            logger.warning(f"No image for scene {i+1}, skipping")
            continue
            
        img_path = image_paths[i]
        audio_path = audio_paths[i] if i < len(audio_paths) else None
        subtitle = scene.get("subtitle", "")
        duration = scene.get("duration_seconds", 4)
        
        scene_clip = create_scene_clip(img_path, audio_path, subtitle, duration)
        scenes.append(scene_clip)
    
    # Add closing scene if requested
    if add_closing and script.get("closing_line"):
        closing_img = image_paths[-1] if image_paths else None
        if closing_img:
            closing_clip = create_scene_clip(
                closing_img,
                audio_paths[-1] if len(audio_paths) > len(script.get("scenes", [])) else None,
                script["closing_line"],
                duration=3
            )
            scenes.append(closing_clip)
    
    if not scenes:
        raise ValueError("No scenes to assemble - check inputs")
    
    # Concatenate all scenes
    final_clip = concatenate_videoclips(scenes, method="compose")
    
    # Ensure total duration within limits
    if final_clip.duration > config.VIDEO_MAX_DURATION:
        logger.warning(f"Video too long ({final_clip.duration:.1f}s), trimming to {config.VIDEO_MAX_DURATION}s")
        final_clip = final_clip.subclip(0, config.VIDEO_MAX_DURATION)
    
    # Export with GitHub Actions optimizations
    logger.info(f"Rendering video: {final_clip.duration:.1f}s @ {config.VIDEO_FPS}fps")
    
    final_clip.write_videofile(
        str(output_path),
        codec="libx264",
        audio_codec="aac",
        fps=config.VIDEO_FPS,
        threads=2,  # Match GitHub Actions 2-core CPU
        preset="ultrafast",  # Speed over compression
        logger=None,  # Suppress MoviePy progress bar
        temp_audiofile="temp-audio.m4a",
        remove_temp=True
    )
    
    # Verify output
    if not output_path.exists():
        raise RuntimeError("Video export failed - file not created")
    
    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"✅ Video created: {output_path.name} ({file_size_mb:.1f} MB, {final_clip.duration:.1f}s)")
    
    return output_path


def compress_video_if_needed(input_path: Path, target_mb: int = None) -> Path:
    """
    Compress video with FFmpeg if it exceeds size limit
    """
    target_mb = target_mb or config.VIDEO_TARGET_SIZE_MB
    target_bytes = target_mb * 1024 * 1024
    
    current_size = input_path.stat().st_size
    if current_size <= target_bytes:
        logger.info(f"Video size OK: {current_size / 1024 / 1024:.1f} MB <= {target_mb} MB")
        return input_path
    
    logger.info(f"Compressing video: {current_size / 1024 / 1024:.1f} MB → target {target_mb} MB")
    
    output_path = input_path.parent / f"{input_path.stem}_compressed{input_path.suffix}"
    
    cmd = [
        "ffmpeg", "-i", str(input_path),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "28",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        "-y",
        str(output_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    
    if result.returncode != 0:
        logger.error(f"FFmpeg compression failed: {result.stderr[:200]}")
        return input_path
    
    new_size = output_path.stat().st_size
    logger.info(f"Compressed: {current_size / 1024 / 1024:.1f} MB → {new_size / 1024 / 1024:.1f} MB")
    
    return output_path


if __name__ == "__main__":
    print("🎬 Video assembly module loaded (Pillow 10+ Compatible)")
# ====================
