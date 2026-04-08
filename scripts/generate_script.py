# scripts klasöründe yeni dosya: generate_script.py
# İçeriği yapıştır:

# scripts/generate_script.py
# ====================
"""
Generate educational video scripts using LLM (Qwen via OpenRouter)
"""
import json
import os
from pathlib import Path
from openai import OpenAI
from utils.config import config
from utils.logger import logger
from utils.api_wrapper import retry_with_fallback

def load_system_prompt() -> str:
    """Load and customize system prompt with character info"""
    prompt_path = config.PROMPTS_DIR / "system_prompt.txt"
    
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt = f.read()
    
    # Replace placeholders with actual character info
    prompt = prompt.replace("{CHARACTER_NAME}", config.CHARACTER_NAME)
    prompt = prompt.replace("{CHARACTER_COLOR_PALETTE}", config.CHARACTER_COLOR_PALETTE)
    prompt = prompt.replace("{ART_STYLE}", config.ART_STYLE)
    
    return prompt


def generate_topic_ideas() -> list[str]:
    """Return list of educational topics for kids"""
    return [
        "Renkler: Mavi, kırmızı, sarı",
        "Sayılar: 1'den 5'e kadar sayma",
        "Şekiller: Daire, kare, üçgen",
        "Hayvanlar ve sesleri",
        "Meyveler ve renkleri",
        "Zıt kavramlar: Büyük-küçük, yukarı-aşağı",
        "Gün içinde yapılan aktiviteler",
        "Temel nezaket kelimeleri"
    ]


@retry_with_fallback(max_retries=3, timeout_seconds=45)
def call_openrouter_api(user_prompt: str, model: str = None) -> dict:
    """Call OpenRouter API with retry logic"""
    model = model or config.OPENROUTER_MODEL
    
    client = OpenAI(
        base_url=config.OPENROUTER_BASE_URL,
        api_key=config.OPENROUTER_API_KEY
    )
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": load_system_prompt()},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=1000,
        extra_headers={
            "HTTP-Referer": "https://github.com/yourusername/ai-kidstube-autopilot",
            "X-Title": "AI-KidsTube Autopilot"
        }
    )
    
    content = response.choices[0].message.content.strip()
    
    # Parse JSON response
    try:
        # Remove markdown code blocks if present
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()
        
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.debug(f"Raw response: {content[:200]}...")
        raise ValueError(f"Invalid JSON from LLM: {content[:100]}")


def generate_daily_script(topic: str = None) -> dict:
    """
    Generate a complete video script for today's video
    
    Args:
        topic: Optional specific topic, otherwise random from list
        
    Returns:
        dict: Parsed script JSON with scenes, narration, visual prompts
    """
    if not topic:
        import random
        topic = random.choice(generate_topic_ideas())
    
    logger.info(f"Generating script for topic: {topic}")
    

    user_prompt = f"""Generate a video script in ENGLISH ONLY.
Topic: {topic}
Target audience: Children ages 2-6
Duration: 15-30 seconds
Language: Simple, rhythmic English

Please output in JSON format."""


    
    script = call_openrouter_api(user_prompt)
    
    # Validate required fields
    required_fields = ["title", "scenes", "topic"]
    missing = [f for f in required_fields if f not in script]
    if missing:
        raise ValueError(f"Script missing required fields: {missing}")
    
    # Add metadata
    script["generated_at"] = __import__("datetime").datetime.now().isoformat()
    script["config"] = {
        "character": config.CHARACTER_NAME,
        "style": config.ART_STYLE
    }
    
    logger.info(f"Script generated successfully: {script['title']}")
    return script


def save_script(script: dict, output_path: Path = None) -> Path:
    """Save script to JSON file"""
    if output_path is None:
        output_path = config.OUTPUT_DIR / f"script_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Script saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    # Test run
    import sys
    if not config.is_ready():
        missing = config.validate()
        print(f"❌ Missing config: {missing}")
        print("Set environment variables or create .env file")
        sys.exit(1)
    
    try:
        script = generate_daily_script()
        print(f"✅ Script: {script['title']}")
        print(f"📝 Scenes: {len(script['scenes'])}")
        
        # Save for inspection
        path = save_script(script)
        print(f"💾 Saved: {path}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
# ====================
# Dosyayı kaydet ✅
