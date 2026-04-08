# scripts/generate_images.py
# ====================
"""
Generate images for video scenes with robust 3-layer fallback:
1. Hugging Face Inference API (with auth)
2. Leonardo.ai (if API key provided)
3. Placeholder image (PIL) - guaranteed fallback
"""
import requests
import time
import base64
from pathlib import Path
from typing import Optional
from utils.config import config
from utils.logger import logger
from utils.api_wrapper import retry_with_fallback

def load_reference_images() -> list[str]:
    """Load character reference images or style guide"""
    ref_dir = config.CHARACTERS_DIR
    refs = []
    for ext in ["*.png", "*.jpg", "*.jpeg"]:
        for img_path in ref_dir.glob(ext):
            if "ref" in img_path.name.lower():
                refs.append(f"reference: {img_path.name}")
    if not refs:
        style_guide = config.CHARACTERS_DIR / "style_guide.txt"
        if style_guide.exists():
            with open(style_guide, "r", encoding="utf-8") as f:
                content = f.read()[:500]
                refs.append(f"style reference: {content}")
    return refs

def enhance_prompt_with_refs(base_prompt: str, refs: list[str]) -> str:
    """Enhance prompt with character consistency instructions"""
    enhanced = f"""{base_prompt}

CHARACTER CONSISTENCY:
- Main character: {config.CHARACTER_NAME}
- Colors: {config.CHARACTER_COLOR_PALETTE}
- Art style: {config.ART_STYLE}
- Always include signature item (e.g., red bow)
- Style: flat vector illustration, children's book, soft edges

REFERENCE ANCHORS: {chr(10).join(f'- {ref}' for ref in refs)}

TECHNICAL: 1080x1920 vertical, no text, bright child-friendly colors, simple background"""
    return enhanced.strip()

@retry_with_fallback(max_retries=1, timeout_seconds=30)
def call_hf_api(prompt: str, model_id: str = None) -> Optional[bytes]:
    """Call Hugging Face Inference API with proper auth"""
    model_id = model_id or config.HF_MODEL_ID
    
    # New endpoint (requires auth even for public models)
    url = f"https://router.huggingface.co/hf-inference/models/{model_id}"
    
    headers = {"Content-Type": "application/json"}
    if config.HF_ZERO_GPU_TOKEN:
        headers["Authorization"] = f"Bearer {config.HF_ZERO_GPU_TOKEN}"
    
    payload = {
        "inputs": prompt,
        "parameters": {
            "width": 1080, "height": 1920,
            "num_inference_steps": 20, "guidance_scale": 7.5
        }
    }
    
    logger.info(f"Calling HF API: {model_id[:40]}...")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=45)
        
        if response.status_code == 200:
            return response.content
        elif response.status_code == 401:
            logger.warning("HF API requires authentication (401)")
            return None
        elif response.status_code == 503:
            logger.warning("Model loading, waiting 10s...")
            time.sleep(10)
            return call_hf_api(prompt, model_id)
        else:
            logger.warning(f"HF API error {response.status_code}")
            return None
    except Exception as e:
        logger.warning(f"HF API exception: {e}")
        return None

@retry_with_fallback(max_retries=1, timeout_seconds=30)
def call_leonardo_api(prompt: str) -> Optional[bytes]:
    """Call Leonardo.ai API (150 free tokens/day)"""
    if not config.LEONARDO_API_KEY:
        return None
    
    headers = {"Authorization": f"Bearer {config.LEONARDO_API_KEY}", "Content-Type": "application/json"}
    
    # Step 1: Create generation job
    create_url = "https://cloud.leonardo.ai/api/rest/v1/generations"
    payload = {
        "prompt": prompt,
        "modelId": "6bef9f1b-29cb-40c7-b9df-32b51c1f67d3",  # Leonardo Phoenix
        "width": 1080, "height": 1920,
        "num_images": 1, "sd_version": "LEONARDO_PHOENIX"
    }
    
    logger.info("Calling Leonardo.ai API...")
    
    create_resp = requests.post(create_url, headers=headers, json=payload, timeout=30)
    if create_resp.status_code != 200:
        logger.warning(f"Leonardo create failed: {create_resp.status_code}")
        return None
        
    generation_id = create_resp.json().get("sdGenerationJob", {}).get("generationId")
    if not generation_id:
        return None
    
    # Step 2: Poll for completion (max 45 seconds)
    for _ in range(9):
        time.sleep(5)
        status_url = f"https://cloud.leonardo.ai/api/rest/v1/generations/{generation_id}"
        status_resp = requests.get(status_url, headers=headers, timeout=10)
        if status_resp.status_code != 200:
            continue
            
        status_data = status_resp.json()
        if status_data.get("status") == "COMPLETE":
            image_url = status_data["generated_images"][0]["url"]
            img_resp = requests.get(image_url, timeout=10)
            if img_resp.status_code == 200:
                return img_resp.content
        elif status_data.get("status") == "FAILED":
            break
    
    return None

def create_placeholder_image(output_path: Path, caption: str) -> Path:
    """Create a simple placeholder image when AI generators fail"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import textwrap
        
        # Create vertical canvas (1080x1920)
        img = Image.new("RGB", (1080, 1920), color=(70, 130, 180))  # Steel blue
        draw = ImageDraw.Draw(img)
        
        # Load font (fallback to default)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        except:
            font = ImageFont.load_default()
        
        # Wrap and draw text
        wrapped = textwrap.fill(f"🎨 {caption[:80]}", width=35)
        bbox = draw.textbbox((0, 0), wrapped, font=font)
        x = (1080 - (bbox[2] - bbox[0])) // 2
        y = (1920 - (bbox[3] - bbox[1])) // 2
        draw.text((x, y), wrapped, fill="white", font=font, align="center")
        
        # Add character name
        draw.text((540, 1850), f"✨ {config.CHARACTER_NAME}", fill="#FFD700", font=font, anchor="mm")
        
        img.save(output_path, "PNG")
        logger.info(f"Placeholder created: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Placeholder creation failed: {e}")
        # Ultimate fallback: return any existing PNG or create minimal file
        output_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)  # Minimal valid PNG header
        return output_path

def generate_scene_image(visual_prompt: str, output_path: Path = None) -> Path:
    """Generate image with 3-layer fallback: HF → Leonardo → Placeholder"""
    if output_path is None:
        import hashlib, datetime
        hash_id = hashlib.md5(visual_prompt.encode()).hexdigest()[:8]
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = config.OUTPUT_DIR / f"img_{timestamp}_{hash_id}.png"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Enhance prompt
    refs = load_reference_images()
    enhanced_prompt = enhance_prompt_with_refs(visual_prompt, refs)
    
    logger.info(f"Generating image: '{visual_prompt[:50]}...'")
    
    # Layer 1: Hugging Face
    image_bytes = call_hf_api(enhanced_prompt)
    
    # Layer 2: Leonardo.ai (if HF failed and key exists)
    if not image_bytes and config.LEONARDO_API_KEY:
        logger.info("HF failed, trying Leonardo.ai fallback...")
        image_bytes = call_leonardo_api(enhanced_prompt)
    
    # Layer 3: Placeholder (guaranteed)
    if not image_bytes:
        logger.warning("All AI generators failed, creating placeholder")
        return create_placeholder_image(output_path, visual_prompt[:100])
    
    # Save successful image
    with open(output_path, "wb") as f:
        f.write(image_bytes)
    
    logger.info(f"✅ Image saved: {output_path.name} ({len(image_bytes)//1024} KB)")
    return output_path

def generate_script_images(script: dict, output_dir: Path = None) -> list[Path]:
    """Generate images for all scenes"""
    if output_dir is None:
        output_dir = config.OUTPUT_DIR
    
    image_paths = []
    for i, scene in enumerate(script.get("scenes", []), 1):
        visual_prompt = scene.get("visual_prompt", "")
        if not visual_prompt:
            continue
        output_path = output_dir / f"img_scene_{i:02d}.png"
        img_path = generate_scene_image(visual_prompt, output_path)
        image_paths.append(img_path)
    
    logger.info(f"✅ Generated {len(image_paths)} images")
    return image_paths

if __name__ == "__main__":
    print("🎨 Image generation module ready")
# ====================
