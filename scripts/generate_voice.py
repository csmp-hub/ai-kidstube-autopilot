# scripts/generate_voice.py
# ====================
"""
Generate voiceover using Edge-TTS (free, no model download required)
"""
import asyncio
import edge_tts
from pathlib import Path
from typing import Optional
from utils.config import config
from utils.logger import logger

# Edge-TTS voice for English kids content (clear, friendly)
EDGE_TTS_VOICE = "en-US-EmmaNeural"  # Female, clear, child-friendly
# Alternatives: "en-US-GuyNeural" (male), "en-US-AnaNeural" (female)

async def generate_voice_async(
    text: str, 
    output_path: Path,
    voice: str = None,
    rate: str = "+0%"  # Speed: "+10%" faster, "-10%" slower
) -> Path:
    """
    Generate speech using Edge-TTS (async)
    """
    voice = voice or EDGE_TTS_VOICE
    
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        volume="+0%",
        pitch="+0Hz"
    )
    
    await communicate.save(str(output_path))
    return output_path

def generate_voice(
    text: str, 
    output_path: Path = None,
    voice: str = None,
    speed: float = 1.0
) -> Path:
    """
    Generate speech from text using Edge-TTS (sync wrapper)
    
    Args:
        text: English text to synthesize
        output_path: Output MP3 file path (auto-generated if None)
        voice: Edge-TTS voice name (default: en-US-EmmaNeural)
        speed: Speech speed multiplier (1.0 = normal)
        
    Returns:
        Path to generated audio file (MP3)
    """
    if output_path is None:
        import hashlib
        import datetime
        hash_id = hashlib.md5(text.encode()).hexdigest()[:8]
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = config.OUTPUT_DIR / f"voice_{timestamp}_{hash_id}.mp3"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert speed to Edge-TTS rate format
    if speed == 1.0:
        rate = "+0%"
    elif speed > 1.0:
        rate = f"+{int((speed - 1.0) * 100)}%"
    else:
        rate = f"-{int((1.0 - speed) * 100)}%"
    
    logger.info(f"Generating voice with Edge-TTS: '{text[:50]}...'")
    
    try:
        # Run async function in sync context
        asyncio.run(generate_voice_async(text, output_path, voice, rate))
        
        if not output_path.exists():
            raise RuntimeError("Edge-TTS completed but output file not created")
        
        logger.info(f"Voice generated: {output_path} ({output_path.stat().st_size / 1024:.1f} KB)")
        return output_path
        
    except Exception as e:
        logger.error(f"Edge-TTS failed: {e}")
        raise RuntimeError(f"TTS generation failed: {str(e)[:200]}")


def generate_script_voices(script: dict, output_dir: Path = None) -> list[Path]:
    """
    Generate voice files for all scenes in a script
    
    Returns list of audio file paths in scene order
    """
    if output_dir is None:
        output_dir = config.OUTPUT_DIR
    
    audio_paths = []
    
    for i, scene in enumerate(script.get("scenes", []), 1):
        narration = scene.get("narration", "")
        if not narration:
            continue
            
        # Generate filename with scene number (.mp3 for Edge-TTS)
        output_path = output_dir / f"voice_scene_{i:02d}.mp3"
        audio_path = generate_voice(narration, output_path)
        audio_paths.append(audio_path)
    
    # Generate closing line if present
    if script.get("closing_line"):
        output_path = output_dir / "voice_closing.mp3"
        audio_path = generate_voice(script["closing_line"], output_path)
        audio_paths.append(audio_path)
    
    logger.info(f"Generated {len(audio_paths)} voice files")
    return audio_paths


if __name__ == "__main__":
    # Test with sample English text
    test_texts = [
        "Hello friends! Today we will learn colors.",
        "This is blue. Blue like the sky!",
        "Great job! See you in the next video!"
    ]
    
    print("🎤 Testing Edge-TTS with English...")
    for i, text in enumerate(test_texts, 1):
        try:
            path = generate_voice(text, config.OUTPUT_DIR / f"test_voice_{i}.mp3")
            print(f"✅ Voice {i}: {path} ({path.stat().st_size / 1024:.1f} KB)")
        except Exception as e:
            print(f"❌ Voice {i} failed: {e}")
    
    print("\n💡 Edge-TTS: No model download, just internet required")
# ====================
