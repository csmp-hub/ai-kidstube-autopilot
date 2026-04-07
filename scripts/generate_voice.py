# scripts klasöründe yeni dosya: generate_voice.py
# İçeriği yapıştır:

# scripts/generate_voice.py
# ====================
"""
Generate voiceover using Piper TTS (offline, Turkish support)
"""
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from utils.config import config
from utils.logger import logger

# Piper model info for Turkish
PIPER_MODEL_NAME = "tr_TR-dfki-medium"
PIPER_MODEL_URL = f"https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/{PIPER_MODEL_NAME}/{PIPER_MODEL_NAME}.onnx"
PIPER_CONFIG_URL = f"https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/{PIPER_MODEL_NAME}/{PIPER_MODEL_NAME}.onnx.json"

def ensure_piper_model(model_dir: Path = None) -> Path:
    """
    Download Piper Turkish model if not present
    Returns path to model directory
    """
    if model_dir is None:
        model_dir = config.BASE_DIR / "models" / "piper"
    
    model_path = model_dir / f"{PIPER_MODEL_NAME}.onnx"
    config_path = model_dir / f"{PIPER_MODEL_NAME}.onnx.json"
    
    if model_path.exists() and config_path.exists():
        logger.info(f"Piper model already present: {model_dir}")
        return model_dir
    
    logger.info(f"Downloading Piper Turkish model to: {model_dir}")
    model_dir.mkdir(parents=True, exist_ok=True)
    
    import requests
    
    # Download model
    logger.info("Downloading model file...")
    response = requests.get(PIPER_MODEL_URL, stream=True)
    response.raise_for_status()
    with open(model_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    # Download config
    logger.info("Downloading config file...")
    response = requests.get(PIPER_CONFIG_URL)
    response.raise_for_status()
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(response.text)
    
    logger.info("Piper model download complete")
    return model_dir


def generate_voice(
    text: str, 
    output_path: Path = None,
    model_dir: Path = None,
    speed: float = 1.0
) -> Path:
    """
    Generate speech from text using Piper TTS
    
    Args:
        text: Turkish text to synthesize
        output_path: Output WAV file path (auto-generated if None)
        model_dir: Piper model directory
        speed: Speech speed multiplier (1.0 = normal)
        
    Returns:
        Path to generated audio file
    """
    if output_path is None:
        import hashlib
        import datetime
        hash_id = hashlib.md5(text.encode()).hexdigest()[:8]
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = config.OUTPUT_DIR / f"voice_{timestamp}_{hash_id}.wav"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Ensure model is available
    model_dir = ensure_piper_model(model_dir)
    model_path = model_dir / f"{PIPER_MODEL_NAME}.onnx"
    
    # Build Piper command
    cmd = [
        "piper",
        "--model", str(model_path),
        "--output_file", str(output_path),
        "--text", text,
    ]
    
    # Add speed if not default
    if speed != 1.0:
        cmd.extend(["--length_scale", str(1.0 / speed)])
    
    logger.info(f"Generating voice: '{text[:50]}...'")
    logger.debug(f"Piper command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=30
        )
        
        if not output_path.exists():
            raise RuntimeError("Piper completed but output file not created")
        
        logger.info(f"Voice generated: {output_path} ({output_path.stat().st_size / 1024:.1f} KB)")
        return output_path
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Piper failed: {e.stderr}")
        raise RuntimeError(f"TTS generation failed: {e.stderr[:200]}")
    except FileNotFoundError:
        logger.error("Piper binary not found. Installing...")
        # Fallback: try to install via pip
        try:
            subprocess.run(["pip", "install", "piper-tts"], check=True)
            return generate_voice(text, output_path, model_dir, speed)  # Retry
        except Exception as install_error:
            logger.error(f"Failed to install piper-tts: {install_error}")
            raise RuntimeError("Piper TTS not available. Please install: pip install piper-tts")


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
            
        # Generate filename with scene number
        output_path = output_dir / f"voice_scene_{i:02d}.wav"
        audio_path = generate_voice(narration, output_path)
        audio_paths.append(audio_path)
    
    # Generate closing line if present
    if script.get("closing_line"):
        output_path = output_dir / "voice_closing.wav"
        audio_path = generate_voice(script["closing_line"], output_path)
        audio_paths.append(audio_path)
    
    logger.info(f"Generated {len(audio_paths)} voice files")
    return audio_paths


if __name__ == "__main__":
    # Test with sample text
    test_texts = [
        "Merhaba arkadaşlar! Bugün renkleri öğreneceğiz.",
        "Bu mavi. Mavi gibi gökyüzü!",
        "Harika iş çıkardın! Bir sonraki videoda görüşürüz!"
    ]
    
    print("🎤 Testing Piper TTS with Turkish...")
    for i, text in enumerate(test_texts, 1):
        try:
            path = generate_voice(text, config.OUTPUT_DIR / f"test_voice_{i}.wav")
            print(f"✅ Voice {i}: {path} ({path.stat().st_size / 1024:.1f} KB)")
        except Exception as e:
            print(f"❌ Voice {i} failed: {e}")
    
    print("\n💡 Note: First run downloads ~50MB model file")
# ====================
# Dosyayı kaydet ✅