# scripts klasöründe yeni dosya: generate_images.py
# İçeriği yapıştır:

# scripts/generate_images.py
# ====================
"""
Generate images for video scenes using free AI services
Supports: Hugging Face ZeroGPU (Wan 2.2), Leonardo.ai fallback
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
    """
    Load character reference images as base64 or URLs
    For now, returns placeholder - extend with actual image handling
    """
    ref_dir = config.CHARACTERS_DIR
    refs = []
    
    # Try to find reference images
    for ext in ["*.png", "*.jpg", "*.jpeg"]:
        for img_path in ref_dir.glob(ext):
            if "ref" in img_path.name.lower():
                # For GitHub Actions: upload to imgbb or use raw GitHub URL
                # For now, return descriptive text prompt instead
                refs.append(f"reference: {img_path.name}")
    
    if not refs:
        # Fallback: use style guide text as reference
        style_guide = config.CHARACTERS_DIR / "style_guide.txt"
        if style_guide.exists():
            with open(style_guide, "r", encoding="utf-8") as f:
                content = f.read()[:500]  # First 500 chars
                refs.append(f"style reference: {content}")
    
    return refs


def enhance_prompt_with_refs(base_prompt: str, refs: list[str]) -> str:
    """
    Enhance image generation prompt with character references
    """
    enhanced = f"""{base_prompt}

CHARACTER CONSISTENCY REQUIREMENTS:
- Main character: {config.CHARACTER_NAME}
- Colors: {config.CHARACTER_COLOR_PALETTE}
- Art style: {config.ART_STYLE}
- Always include: yellow hat on blue elephant
- Style: flat vector illustration, children's book, soft edges

REFERENCE ANCHORS:
{chr(10).join(f"- {ref}" for ref in refs)}

TECHNICAL:
- Resolution: 1080x1920 (9:16 vertical)
- No text in image (text added in post)
- Bright, child-friendly colors
- Simple background, character focus
"""
    return enhanced.strip()


@retry_with_fallback(max_retries=2, timeout_seconds=60)
def call_hf_zerogpu(prompt: str, model_id: str = None) -> Optional[bytes]:
    """
    Call Hugging Face ZeroGPU API for image generation
    Returns image bytes or None if failed
    """
    model_id = model_id or config.HF_MODEL_ID
    
    # ZeroGPU endpoint (anon or with token)
    headers = {"Authorization": f"Bearer {config.HF_ZERO_GPU_TOKEN}"} if config.HF_ZERO_GPU_TOKEN else {}
    
    # Note: ZeroGPU API structure may vary - this is a template
    # Actual implementation depends on the specific Space's API
    url = f"https://api-inference.huggingface.co/models/{model_id}"
    
    payload = {
        "inputs": prompt,
        "parameters": {
            "width": 1080,
            "height": 1920,
            "num_inference_steps": 20,
            "guidance_scale": 7.5
        }
    }
    
    logger.info(f"Calling HF ZeroGPU: {model_id[:30]}... [function: call_hf_zerogpu]")
    
    response = requests.post(url, headers=headers, json=payload, timeout=config.IMAGE_GENERATION_TIMEOUT)
    
    if response.status_code == 200:
        return response.content
    elif response.status_code == 503:
        # Model loading - retry after delay
        logger.warning("Model loading, waiting 20s...")
        time.sleep(20)
        return call_hf_zerogpu(prompt, model_id)  # Recursive retry
    else:
        logger.error(f"HF API error {response.status_code}: {response.text[:200]}")
        return None


@retry_with_fallback(max_retries=2, timeout_seconds=30)
def call_leonardo_api(prompt: str) -> Optional[bytes]:
    """
    Call Leonardo.ai API as fallback (150 free tokens/day)
    Simplified implementation - extend with actual API calls
    """
    if not config.LEONARDO_API_KEY:
        logger.warning("Leonardo API key not set, skipping fallback")
        return None
    
    # Leonardo.ai API v1 structure (simplified)
    headers = {
        "Authorization": f"Bearer {config.LEONARDO_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Step 1: Create generation request
    create_url = "https://cloud.leonardo.ai/api/rest/v1/generations"
    payload = {
        "prompt": prompt,
        "modelId": "6bef9f1b-29cb-40c7-b9df-32b51c1f67d3",  # Leonardo Phoenix
        "width": 1080,
        "height": 1920,
        "num_images": 1,
        "sd_version": "LEONARDO_PHOENIX"
    }
    
    logger.info("Calling Leonardo.ai API...")
    
    create_resp = requests.post(create_url, headers=headers, json=payload, timeout=30)
    create_resp.raise_for_status()
    generation_id = create_resp.json()["sdGenerationJob"]["generationId"]
    
    # Step 2: Poll for completion
    for attempt in range(10):  # Max 50 seconds
        time.sleep(5)
        status_url = f"https://cloud.leonardo.ai/api/rest/v1/generations/{generation_id}"
        status_resp = requests.get(status_url, headers=headers, timeout=10)
        status_resp.raise_for_status()
        
        status_data = status_resp.json()
        if status_data.get("status") == "COMPLETE":
            image_url = status_data["generated_images"][0]["url"]
            # Download image
            img_resp = requests.get(image_url, timeout=10)
            img_resp.raise_for_status()
            return img_resp.content
        elif status_data.get("status") == "FAILED":
            raise RuntimeError(f"Leonardo generation failed: {status_data}")
    
    raise TimeoutError("Leonardo generation timed out")


def generate_scene_image(
    visual_prompt: str, 
    output_path: Path = None,
    use_fallback: bool = True
) -> Path:
    """
    Generate a single image for a video scene
    
    Tries: HF ZeroGPU → Leonardo.ai (if enabled)
    """
    if output_path is None:
        import hashlib
        import datetime
        hash_id = hashlib.md5(visual_prompt.encode()).hexdigest()[:8]
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = config.OUTPUT_DIR / f"img_{timestamp}_{hash_id}.png"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Enhance prompt with character references
    refs = load_reference_images()
    enhanced_prompt = enhance_prompt_with_refs(visual_prompt, refs)
    
    logger.info(f"Generating image for: '{visual_prompt[:60]}...'")
    
    # Try primary: HF ZeroGPU
    image_bytes = call_hf_zerogpu(enhanced_prompt)
    
    # Fallback to Leonardo if enabled and primary failed
    if not image_bytes and use_fallback and config.LEONARDO_API_KEY:
        logger.info("Primary failed, trying Leonardo.ai fallback...")
        image_bytes = call_leonardo_api(enhanced_prompt)
    
    if not image_bytes:
        raise RuntimeError("All image generation methods failed")
    
    # Save image
    with open(output_path, "wb") as f:
        f.write(image_bytes)
    
    logger.info(f"Image saved: {output_path} ({len(image_bytes) / 1024:.1f} KB)")
    return output_path


def generate_script_images(script: dict, output_dir: Path = None) -> list[Path]:
    """
    Generate images for all scenes in a script
    
    Returns list of image paths in scene order
    """
    if output_dir is None:
        output_dir = config.OUTPUT_DIR
    
    image_paths = []
    
    for i, scene in enumerate(script.get("scenes", []), 1):
        visual_prompt = scene.get("visual_prompt", "")
        if not visual_prompt:
            logger.warning(f"Scene {i} missing visual_prompt, skipping")
            continue
            
        output_path = output_dir / f"img_scene_{i:02d}.png"
        img_path = generate_scene_image(visual_prompt, output_path)
        image_paths.append(img_path)
    
    logger.info(f"Generated {len(image_paths)} images")
    return image_paths


if __name__ == "__main__":
    # Test with sample prompt
    test_prompt = "A cute blue elephant with yellow hat pointing at a big red circle, flat vector style, children book illustration, bright colors, simple background"
    
    print("🎨 Testing image generation...")
    try:
        path = generate_scene_image(test_prompt, config.OUTPUT_DIR / "test_image.png")
        print(f"✅ Image: {path} ({path.stat().st_size / 1024:.1f} KB)")
    except Exception as e:
        print(f"❌ Image generation failed: {e}")
        print("💡 This is expected if API keys not set or services unavailable")
# ====================
# Dosyayı kaydet ✅
