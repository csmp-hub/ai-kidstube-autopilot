# scripts klasöründe yeni dosya: send_telegram.py
# İçeriği yapıştır:

# scripts/send_telegram.py
# ====================
"""
Upload video to Telegram via Bot API
"""
import requests
from pathlib import Path
from utils.config import config
from utils.logger import logger


def send_to_telegram(
    video_path: Path,
    caption: str = None,
    chat_id: str = None,
    bot_token: str = None
) -> bool:
    """
    Send video file to Telegram chat via Bot API
    
    Args:
        video_path: Path to MP4 file
        caption: Optional caption text
        chat_id: Telegram chat/user ID (defaults to config)
        bot_token: Bot token (defaults to config)
        
    Returns:
        bool: True if sent successfully
    """
    chat_id = chat_id or config.TELEGRAM_CHAT_ID
    bot_token = bot_token or config.TELEGRAM_BOT_TOKEN
    
    if not bot_token or not chat_id:
        logger.error("Telegram credentials not configured")
        return False
    
    if not video_path.exists():
        logger.error(f"Video file not found: {video_path}")
        return False
    
    # Check file size (Telegram limit: 50MB for bots)
    file_size = video_path.stat().st_size
    max_size = config.TELEGRAM_MAX_FILE_SIZE
    
    if file_size > max_size:
        logger.error(f"File too large: {file_size / 1024 / 1024:.1f} MB > {max_size / 1024 / 1024:.1f} MB limit")
        return False
    
    # Prepare API call
    url = f"https://api.telegram.org/bot{bot_token}/sendVideo"
    
    # Caption: auto-generate if not provided
    if caption is None:
        video_name = video_path.stem.replace("_meta", "").replace("_compressed", "")
        caption = f"🎬 Yeni video hazır!\n\n📁 {video_name}\n📏 {file_size / 1024 / 1024:.1f} MB\n\n✅ Kalite kontrolü yap, beğenirsen TikTok/YouTube'a yükle!"
    
    # Send request
    logger.info(f"Uploading to Telegram: {video_path.name} ({file_size / 1024 / 1024:.1f} MB)")
    
    with open(video_path, "rb") as video_file:
        files = {"video": (video_path.name, video_file, "video/mp4")}
        data = {"chat_id": chat_id, "caption": caption, "parse_mode": "Markdown"}
        
        response = requests.post(url, files=files, data=data, timeout=120)
    
    if response.status_code == 200:
        result = response.json()
        if result.get("ok"):
            message_id = result["result"]["message_id"]
            logger.info(f"✅ Sent to Telegram: message_id={message_id}")
            return True
        else:
            logger.error(f"Telegram API error: {result}")
            return False
    else:
        logger.error(f"HTTP {response.status_code}: {response.text[:200]}")
        return False


if __name__ == "__main__":
    # Test with dummy file
    print("📤 Telegram upload module ready")
    print("💡 Configure TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in secrets")
# ====================
# Dosyayı kaydet ✅