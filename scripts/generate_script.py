# scripts/generate_script.py
# ====================
"""
Generate educational video scripts using LLM (Self-Healing OpenRouter Integration)
Automatically cycles through available free models. No more 400/404 errors.
"""
import json
import requests
import os
from pathlib import Path
from utils.config import config
from utils.logger import logger
from utils.api_wrapper import retry_with_fallback

def load_system_prompt() -> str:
    """Load and customize system prompt with character info"""
    prompt_path = config.PROMPTS_DIR / "system_prompt.txt"
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt = f.read()
    prompt = prompt.replace("{CHARACTER_NAME}", config.CHARACTER_NAME)
    prompt = prompt.replace("{CHARACTER_COLOR_PALETTE}", config.CHARACTER_COLOR_PALETTE)
    prompt = prompt.replace("{ART_STYLE}", config.ART_STYLE)
    return prompt

def generate_topic_ideas() -> list[str]:
    return [
        "Colors: Blue, red, yellow",
        "Numbers: Counting 1 to 5",
        "Shapes: Circle, square, triangle",
        "Animals and their sounds",
        "Fruits and their colors",
        "Opposites: Big-small, up-down",
        "Daily activities",
        "Basic polite words"
    ]

@retry_with_fallback(max_retries=1, timeout_seconds=30)
def call_openrouter_api(user_prompt: str) -> dict:
    """
    Self-healing API call: tries openrouter/auto first, then falls back to specific free models.
    Forces free tier via max_price: 0. Automatically cleans JSON output.
    """
    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://github.com/csmp-hub/ai-kidstube-autopilot",
        "X-Title": "AI-KidsTube Autopilot",
        "Content-Type": "application/json"
    }
    
    # Official OpenRouter free-tier model rotation list
    model_pool = [
        "openrouter/auto",  # Official router: picks best available free model dynamically
        "meta-llama/llama-3-8b-instruct:free",
        "qwen/qwen-2-7b-instruct:free",
        "mistralai/mistral-7b-instruct:free",
        "google/gemma-7b-it:free"
    ]
    
    last_error = None
    for model_id in model_pool:
        try:
            logger.info(f"🔄 Trying model: {model_id}")
            payload = {
                "model": model_id,
                "messages": [
                    {"role": "system", "content": load_system_prompt()},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 1000,
                "max_price": 0  # 🔑 FORCES FREE TIER ONLY
            }
            
            resp = requests.post(
                f"{config.OPENROUTER_BASE_URL}/chat/completions",
                headers=headers, json=payload, timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()
            
            # Clean markdown/JSON wrappers
            if content.startswith("```json"): content = content.replace("```json", "").replace("```", "").strip()
            elif content.startswith("```"): content = content.replace("```", "").strip()
            
            parsed = json.loads(content)
            logger.info(f"✅ Successfully generated script with model: {model_id}")
            return parsed
            
        except Exception as e:
            last_error = e
            logger.warning(f"⚠️ Model {model_id} failed: {type(e).__name__}")
            continue
            
    raise last_error or RuntimeError("All free models failed. Check OPENROUTER_API_KEY or quota.")

def generate_daily_script(topic: str = None) -> dict:
    if not topic:
        import random
        topic = random.choice(generate_topic_ideas())
        
    logger.info(f"Generating script for topic: {topic}")
    user_prompt = f"Generate a children's educational video script about: {topic}. Output JSON only."
    
    script = call_openrouter_api(user_prompt)
    
    # Validate
    required = ["title", "scenes", "topic"]
    if any(k not in script for k in required):
        raise ValueError(f"Invalid script structure. Missing: {[k for k in required if k not in script]}")
        
    script["generated_at"] = __import__("datetime").datetime.now().isoformat()
    script["config"] = {"character": config.CHARACTER_NAME, "style": config.ART_STYLE}
    return script

def save_script(script: dict, output_path: Path = None) -> Path:
    if output_path is None:
        output_path = config.OUTPUT_DIR / f"script_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)
    logger.info(f"💾 Script saved to: {output_path}")
    return output_path

if __name__ == "__main__":
    import sys
    if not config.is_ready():
        print(f"❌ Missing config: {config.validate()}")
        sys.exit(1)
    try:
        script = generate_daily_script()
        print(f"✅ Script: {script['title']} | Scenes: {len(script['scenes'])}")
        print(f"💾 Saved: {save_script(script)}")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
# ====================
