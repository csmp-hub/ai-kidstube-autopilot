# scripts/generate_script.py
# ====================
"""
Generate educational video scripts using LLM (Robust OpenRouter Integration)
Includes detailed error logging and API key validation.
"""
import json
import requests
import os
from pathlib import Path
from utils.config import config
from utils.logger import logger

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

def call_openrouter_api(user_prompt: str) -> dict:
    """
    Robust API call with detailed error logging and proper request format.
    """
    # Validate API key first
    if not config.OPENROUTER_API_KEY or not config.OPENROUTER_API_KEY.startswith("sk-or-"):
        raise ValueError(f"❌ Invalid OPENROUTER_API_KEY format. Must start with 'sk-or-'. Got: {config.OPENROUTER_API_KEY[:10] if config.OPENROUTER_API_KEY else 'EMPTY'}...")
    
    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://github.com/csmp-hub/ai-kidstube-autopilot",
        "X-Title": "AI-KidsTube Autopilot",
        "Content-Type": "application/json"
    }
    
    # Use a single, known-working free model to isolate the issue
    # If this fails, we know it's auth/format, not model availability
    model_id = "meta-llama/llama-3-8b-instruct:free"
    
    payload = {
    "model": model_id,
    "messages": [
        {"role": "system", "content": load_system_prompt()},
        {"role": "user", "content": user_prompt}
    ],
    "temperature": 0.7,
    "max_tokens": 1000,
    # ✅ max_price must be an object with prompt/completion fields
    "max_price": {
        "prompt": 0,
        "completion": 0
    },
    # ✅ Alternative: Force free tier via provider routing
    "provider": {
        "order": ["Free"]
    }
}
    
    logger.info(f"🔍 Calling OpenRouter API with model: {model_id}")
    logger.debug(f"Request payload: {json.dumps(payload, indent=2)[:500]}...")
    
    try:
        response = requests.post(
            f"{config.OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=45
        )
        
        # Log full response for debugging
        logger.debug(f"Response status: {response.status_code}")
        logger.debug(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 401:
            raise ValueError(f"❌ API Key invalid or expired. Check your OPENROUTER_API_KEY secret.")
        elif response.status_code == 402:
            raise ValueError(f"❌ Account has no credits or free tier quota exceeded. Check https://openrouter.ai/keys")
        elif response.status_code == 400:
            # Log the actual error message from OpenRouter
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
                raise ValueError(f"❌ Bad Request: {error_msg}. Payload may be malformed.")
            except:
                raise ValueError(f"❌ Bad Request (400). Response: {response.text[:200]}")
        elif response.status_code != 200:
            raise ValueError(f"❌ Unexpected status {response.status_code}: {response.text[:200]}")
        
        # Parse successful response
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
        
        # Clean markdown/JSON wrappers
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()
        
        parsed = json.loads(content)
        logger.info(f"✅ Script generated successfully with {model_id}")
        return parsed
        
    except requests.exceptions.ConnectionError:
        raise ValueError("❌ Network error: Could not connect to OpenRouter. Check GitHub Actions internet access.")
    except requests.exceptions.Timeout:
        raise ValueError("❌ Request timed out. OpenRouter may be slow; try again.")
    except json.JSONDecodeError as e:
        logger.error(f"❌ Failed to parse JSON response. Raw content: {content[:300]}")
        raise ValueError(f"❌ Invalid JSON from API: {e}")

def generate_daily_script(topic: str = None) -> dict:
    if not topic:
        import random
        topic = random.choice(generate_topic_ideas())
        
    logger.info(f"Generating script for topic: {topic}")
    user_prompt = f"Generate a children's educational video script about: {topic}. Output JSON only, no extra text."
    
    script = call_openrouter_api(user_prompt)
    
    # Validate structure
    required = ["title", "scenes", "topic"]
    missing = [k for k in required if k not in script]
    if missing:
        raise ValueError(f"Invalid script structure. Missing fields: {missing}")
        
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
