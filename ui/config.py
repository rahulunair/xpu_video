from dataclasses import dataclass
import os
from pathlib import Path
import logging


@dataclass
class AppConfig:
    base_url: str = "http://localhost:9000/imagine/generate"
    max_frames: int = 49
    max_fps: int = 60
    max_queue_size: int = 100
    max_storage_mb: int = 1000
    rate_limit_requests: int = 5
    rate_limit_window: int = 60


config = AppConfig()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)
output_dir = Path("generated_videos")
output_dir.mkdir(exist_ok=True)
VALID_TOKEN = os.environ.get("VALID_TOKEN")
if not VALID_TOKEN:
    raise ValueError("Missing VALID_TOKEN environment variable")

rate_limit_cache = {}
queue_cache = {}
