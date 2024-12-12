import gc
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional, Union
import tempfile

import ray.serve as serve
import torch
from fastapi import FastAPI, HTTPException, Response, Body
from fastapi.responses import FileResponse

from config.model_configs import MODEL_CONFIGS as VIDEO_MODEL_CONFIGS
from video_models import VideoModelFactory
from utils.system_monitor import SystemMonitor
from utils.validators import VideoGenerationValidator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@dataclass
class ModelStatus:
    """Status and metadata for the loaded model."""

    is_loaded: bool = False
    error: Optional[str] = None
    model: Optional[Any] = None

    def __str__(self) -> str:
        return f"Loaded: {self.is_loaded}, Error: {self.error}"


@serve.deployment(
    ray_actor_options={"num_cpus": 24},
    num_replicas=1,
    max_ongoing_requests=50,
    max_queued_requests=100,
)
@serve.ingress(app)
class VideoGenerationServer:
    """Server for handling video generation requests."""

    def __init__(self):
        """Initialize the video generation server with a single model."""
        logger.info("Initializing Video Generation Server")
        self.model_name = os.environ.get("DEFAULT_MODEL", "cogvideox")
        logger.info(f"Using model: {self.model_name}")
        self.model_status = ModelStatus()
        self._load_model()

    def _load_model(self) -> None:
        """Load the configured model."""
        try:
            logger.info(f"Loading model: {self.model_name}")
            model = VideoModelFactory.create_model(self.model_name)
            self.model_status.model = model
            self.model_status.is_loaded = True
            self.model_status.error = None
            logger.info(f"Successfully loaded model: {self.model_name}")
        except Exception as e:
            error_msg = f"Failed to load model {self.model_name}: {str(e)}"
            logger.error(error_msg)
            self.model_status.is_loaded = False
            self.model_status.error = error_msg
            self.model_status.model = None

    @app.get("/info")
    def get_info(self) -> Dict[str, Any]:
        """Get information about the model and system status."""
        return {
            "model": self.model_name,
            "is_loaded": self.model_status.is_loaded,
            "error": self.model_status.error,
            "config": VIDEO_MODEL_CONFIGS[self.model_name],
            "system_info": SystemMonitor.get_system_info(),
        }

    @app.get("/health")
    def health_check(self) -> Dict[str, Any]:
        """Health check endpoint."""
        return {
            "status": "healthy" if self.model_status.is_loaded else "degraded",
        }

    @app.post("/imagine")
    async def generate(
        self,
        prompt: str = Body(..., description="The prompt for video generation"),
        num_frames: Optional[int] = Body(49, description="Number of frames to generate"),
        fps: Optional[int] = Body(49, description="Frames per second"),
        guidance_scale: Optional[Union[float, int, str]] = Body(
            None, description="Guidance scale"
        ),
        num_inference_steps: Optional[Union[int, str]] = Body(
            None, description="Number of inference steps"
        ),
    ) -> FileResponse:
        """Generate a video using the loaded model."""
        try:
            VideoGenerationValidator.validate_prompt(prompt)
            params = VideoGenerationValidator.validate_all(
                self.model_name,
                prompt,
                guidance_scale,
                num_inference_steps,
                num_frames,
                fps
            )

            if not self.model_status.is_loaded:
                raise HTTPException(
                    status_code=503,
                    detail=f"Model is not available. Error: {self.model_status.error}",
                )

            try:
                # Create temporary file for video
                with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
                    video_path = tmp_file.name
                    
                video = self.model_status.model.generate(
                    prompt=prompt,
                    num_frames=params["num_frames"],
                    fps=params["fps"],
                    guidance_scale=params["guidance_scale"],
                    num_inference_steps=params["num_inference_steps"],
                    output_path=video_path
                )

                # Return the video file
                return FileResponse(
                    path=video_path,
                    media_type="video/mp4",
                    filename=f"generated_video.mp4",
                    background=None  # The file will be removed after the response is sent
                )

            except Exception as e:
                logger.error(f"Error generating video: {e}")
                self.model_status.is_loaded = False
                self.model_status.error = str(e)
                gc.collect()
                torch.xpu.empty_cache()
                raise HTTPException(
                    status_code=500, detail=f"Error generating video: {str(e)}"
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in generate: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            # Cleanup temporary file if it exists
            if 'video_path' in locals():
                try:
                    os.unlink(video_path)
                except Exception as e:
                    logger.error(f"Error removing temporary file: {e}")


entrypoint = VideoGenerationServer.bind()