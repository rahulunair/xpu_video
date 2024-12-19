import gc
import logging
import os
import tempfile
from typing import Any, Dict, Optional, Union

import intel_extension_for_pytorch as ipex
import ray.serve as serve
import torch
from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from config.model_configs import MODEL_CONFIGS as VIDEO_MODEL_CONFIGS
from utils.system_monitor import SystemMonitor
from utils.validators import VideoGenerationValidator
from video_models import VideoModelFactory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Video Generation API",
    description="AI-powered video generation service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@serve.deployment(
    ray_actor_options={"num_cpus": 28},
    num_replicas=1,
    max_ongoing_requests=4,
    max_queued_requests=20,
)
@serve.ingress(app)
class VideoGenerationServer:
    """Handles video generation requests synchronously via a RESTful API."""

    def __init__(self):
        logger.info("Initializing Video Generation Server")
        self.model_name = os.getenv("DEFAULT_MODEL", "cogvideoX2b")
        logger.info(f"Using model: {self.model_name}")
        self.model_status = {"is_loaded": False, "error": None, "model": None}
        self._load_model()

    def _load_model(self):
        """Load the configured model."""
        try:
            logger.info(f"Loading model: {self.model_name}")
            model = VideoModelFactory.create_model(self.model_name)
            self.model_status.update({"is_loaded": True, "model": model, "error": None})
            logger.info(f"Successfully loaded model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {e}")
            self.model_status.update({"is_loaded": False, "error": str(e)})

    @app.get("/info")
    def get_info(self) -> Dict[str, Any]:
        """Get information about the model and system status."""
        return {
            "model": self.model_name,
            "is_loaded": self.model_status["is_loaded"],
            "error": self.model_status["error"],
            "config": VIDEO_MODEL_CONFIGS.get(self.model_name, {}),
            "system_info": SystemMonitor.get_system_info(),
        }

    @app.get("/health")
    def health_check(self) -> Dict[str, Any]:
        """Health check endpoint."""
        return {
            "status": "healthy" if self.model_status["is_loaded"] else "degraded",
        }

    @app.post("/generate")
    def generate(
        self,
        prompt: str = Body(..., description="The prompt for video generation"),
        num_frames: Optional[int] = Body(
            None, description="Number of frames to generate"
        ),
        fps: Optional[int] = Body(None, description="Frames per second"),
        guidance_scale: Optional[Union[float, int]] = Body(
            None, description="Guidance scale for generation"
        ),
        num_inference_steps: Optional[int] = Body(
            None, description="Number of inference steps for generation"
        ),
    ) -> FileResponse:
        if not self.model_status["is_loaded"]:
            raise HTTPException(
                status_code=503,
                detail=f"Model is not available. Error: {self.model_status['error']}",
            )

        try:
            # Validate parameters
            params = VideoGenerationValidator.validate_all(
                self.model_name,
                prompt=prompt,
                guidance_scale=guidance_scale,
                num_inference_steps=num_inference_steps,
                num_frames=num_frames,
                fps=fps,
            )
            is_animatediff = self.model_name == "animatediff"
            file_extension = ".gif" if is_animatediff else ".mp4"
            media_type = "image/gif" if is_animatediff else "video/mp4"
            filename = (
                "generated_animation.gif" if is_animatediff else "generated_video.mp4"
            )
            output_path = tempfile.NamedTemporaryFile(
                suffix=file_extension, delete=False
            ).name
            self.model_status["model"].generate(
                prompt=prompt,
                num_frames=params["num_frames"],
                fps=params["fps"],
                guidance_scale=params["guidance_scale"],
                num_inference_steps=params["num_inference_steps"],
                output_path=output_path,
            )
            return FileResponse(
                path=output_path,
                media_type=media_type,
                filename=filename,
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Error during video generation: {e}")
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred during video generation.",
            )
        finally:
            gc.collect()
            torch.xpu.empty_cache()


entrypoint = VideoGenerationServer.bind()
