# image_generation.py
import requests
from typing import List, Callable
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

@dataclass
class ImageConfig:
    api_url: str = ""
    token: str = ""
    default_img_size: int = 1024
    default_guidance_scale: int = 7
    default_num_inference_steps: int = 50

config = ImageConfig()

class ImageGenerator:
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {config.token}",
            "Content-Type": "application/json",
        }

    def generate_image(self, prompt: str) -> bytes:
        payload = {
            "prompt": prompt,
            "img_size": config.default_img_size,
            "guidance_scale": config.default_guidance_scale,
            "num_inference_steps": config.default_num_inference_steps,
        }
        logger.info(f"Sending request with prompt: {prompt}")
        response = requests.post(config.api_url, headers=self.headers, json=payload)

        if response.status_code == 200:
            logger.info("Image generation successful")
            return response.content
        else:
            logger.error(f"Image generation failed: {response.status_code}, {response.text}")
            raise Exception(f"Image generation failed: {response.status_code}, {response.text}")

    def generate_image_variations(self, prompt: str, num_variations: int, progress_callback: Callable[[float], None] = None) -> List[bytes]:
        variations = []
        enhancement_phrases = ["4K resolution", "ultra-realistic", "cinematic lighting", "high detail"]
        logger.info(f"Starting generation of {num_variations} variations for prompt: {prompt}")
        for i in range(num_variations):
            enhancement = enhancement_phrases[i % len(enhancement_phrases)]
            enhanced_prompt = f"{prompt}, {enhancement}"  # Modify the prompt with enhancements
            try:
                logger.info(f"Generating variation {i + 1}/{num_variations} with enhanced prompt: {enhanced_prompt}")
                image = self.generate_image(enhanced_prompt)
                variations.append(image)
                logger.info(f"Successfully generated variation {i + 1}/{num_variations}")
                if progress_callback:
                    progress_callback((i + 1) / num_variations)
            except Exception as e:
                logger.error(f"Failed to generate variation {i + 1}/{num_variations}: {e}")
        logger.info(f"Completed generation of {len(variations)} variations out of {num_variations}")
        return variations

output_dir = Path("generated_images")
output_dir.mkdir(exist_ok=True)
if __name__ == "__main__":
    generator = ImageGenerator()
    prompt = "a magical cosmic unicorn"
    variations = generator.generate_image_variations(prompt, 5)

    for idx, image in enumerate(variations):
        with open(output_dir / f"image_{idx + 1}.png", "wb") as f:
            f.write(image)
        logger.info(f"Saved: image_{idx + 1}.png")

