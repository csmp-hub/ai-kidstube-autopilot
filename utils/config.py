# utils klasöründe yeni dosya: config.py
# İçeriği yapıştır:

# utils/config.py
# ====================
"""
Configuration loader for AI-KidsTube Autopilot
Loads environment variables and provides typed config access
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load .env file if exists (for local development)
load_dotenv()

class Config:
    """Application configuration - all values from environment variables"""
    
    # === LLM ===
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "qwen/qwen-3.6-plus:free")
    OPENROUTER_FALLBACK_MODEL: str = os.getenv("OPENROUTER_FALLBACK_MODEL", "google/gemini-flash-1.5:free")
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    
    # === Image Generation ===
    HF_ZERO_GPU_TOKEN: Optional[str] = os.getenv("HF_ZERO_GPU_TOKEN")
    HF_MODEL_ID: str = os.getenv("HF_MODEL_ID", "wan-2-2/text-to-video")
    IMAGE_GENERATION_TIMEOUT: int = int(os.getenv("IMAGE_GENERATION_TIMEOUT", "120"))
    LEONARDO_API_KEY: Optional[str] = os.getenv("LEONARDO_API_KEY")
    
    # === Telegram ===
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
    TELEGRAM_MAX_FILE_SIZE: int = int(os.getenv("TELEGRAM_MAX_FILE_SIZE", "52428800"))  # 50MB
    
    # === Video ===
    VIDEO_RESOLUTION: tuple = (
        int(os.getenv("VIDEO_RESOLUTION_WIDTH", "1080")),
        int(os.getenv("VIDEO_RESOLUTION_HEIGHT", "1920"))
    )
    VIDEO_FPS: int = int(os.getenv("VIDEO_FPS", "24"))
    VIDEO_MAX_DURATION: int = int(os.getenv("VIDEO_MAX_DURATION", "60"))
    VIDEO_TARGET_SIZE_MB: int = int(os.getenv("VIDEO_TARGET_SIZE_MB", "45"))
    
    # === Character ===
    CHARACTER_NAME: str = os.getenv("CHARACTER_NAME", "Mavi Fil")
    CHARACTER_COLOR_PALETTE: str = os.getenv("CHARACTER_COLOR_PALETTE", "#4A90E2,#F5A623,#7ED321")
    ART_STYLE: str = os.getenv("ART_STYLE", "flat vector illustration, children book style")
    
    # === Paths ===
    BASE_DIR: Path = Path(__file__).parent.parent
    ASSETS_DIR: Path = BASE_DIR / "assets"
    CHARACTERS_DIR: Path = ASSETS_DIR / "characters"
    BACKGROUNDS_DIR: Path = ASSETS_DIR / "backgrounds"
    PROMPTS_DIR: Path = BASE_DIR / "prompts"
    OUTPUT_DIR: Path = BASE_DIR / "output"
    
    # === Validation ===
    @classmethod
    def validate(cls) -> list[str]:
        """Check required env vars, return list of missing keys"""
        required = [
            ("OPENROUTER_API_KEY", cls.OPENROUTER_API_KEY),
            ("TELEGRAM_BOT_TOKEN", cls.TELEGRAM_BOT_TOKEN),
            ("TELEGRAM_CHAT_ID", cls.TELEGRAM_CHAT_ID),
        ]
        return [key for key, value in required if not value]
    
    @classmethod
    def is_ready(cls) -> bool:
        """Check if config is complete for running"""
        return len(cls.validate()) == 0

# Global config instance
config = Config()
# ====================
# Dosyayı kaydet ✅