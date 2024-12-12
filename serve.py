import gc
import logging
import os
import tempfile
import asyncio
import uuid
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Dict, Optional, Union

import ray.serve as serve
import torch
import intel_extension_for_pytorch as ipex

from fastapi import FastAPI, HTTPException, Response, Body, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from config.model_configs import MODEL_CONFIGS as VIDEO_MODEL_CONFIGS
from video_models import VideoModelFactory
from utils.system_monitor import SystemMonitor
from utils.validators import VideoGenerationValidator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Video Generation API",
    description="AI-powered video generation service",
    version="0.1.0",
    docs_url="/imagine/docs",
    redoc_url="/imagine/redoc",
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter(prefix="/imagine")

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class ModelStatus:
    """Encapsulates the status and metadata of the loaded model."""
    is_loaded: bool = False
    error: Optional[str] = None
    model: Optional[Any] = None

    def __str__(self) -> str:
        return f"Loaded: {self.is_loaded}, Error: {self.error}"

@dataclass
class GenerationTask:
    """Encapsulates a video generation task."""
    id: str
    status: TaskStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    video_path: Optional[str] = None
    error: Optional[str] = None
    progress: float = 0.0
    prompt: str
    params: Dict[str, Any]

@serve.deployment(
    ray_actor_options={"num_cpus": 28},
    num_replicas=1,
    max_ongoing_requests=2,
    max_queued_requests=4,
)
@serve.ingress(app)
class VideoGenerationServer:
    """Handles video generation requests via a RESTful API."""

    def __init__(self):
        logger.info("Initializing Video Generation Server")
        self.model_name = os.getenv("DEFAULT_MODEL", "cogvideox")
        logger.info(f"Using model: {self.model_name}")
        self.model_status = ModelStatus()
        self.tasks: Dict[str, GenerationTask] = {}
        self._load_model()
        app.include_router(router)
        self._start_cleanup_task()

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

    def _start_cleanup_task(self):
        """Start background task to clean up old tasks."""
        async def cleanup():
            while True:
                await asyncio.sleep(3600)  # Run every hour
                self._cleanup_old_tasks()
        asyncio.create_task(cleanup())

    def _cleanup_old_tasks(self):
        """Remove tasks older than 2 hours."""
        cutoff = datetime.now() - timedelta(hours=2)
        tasks_to_remove = []  
        for task_id, task in self.tasks.items():
            if task.created_at < cutoff:
                if task.video_path and os.path.exists(task.video_path):
                    try:
                        os.unlink(task.video_path)
                    except Exception as e:
                        logger.error(f"Error removing file for task {task_id}: {e}")
                tasks_to_remove.append(task_id)
        for task_id in tasks_to_remove:
            del self.tasks[task_id]

    @router.get("/info")
    def get_info(self) -> Dict[str, Any]:
        """Get information about the model and system status."""
        return {
            "model": self.model_name,
            "is_loaded": self.model_status.is_loaded,
            "error": self.model_status.error,
            "config": VIDEO_MODEL_CONFIGS.get(self.model_name, {}),
            "system_info": SystemMonitor.get_system_info(),
            "replica_id": serve.get_replica_context().replica_tag,
        }

    @router.get("/health")
    def health_check(self) -> Dict[str, Any]:
        """Health check endpoint."""
        return {
            "status": "healthy" if self.model_status.is_loaded else "degraded",
            "replica": serve.get_replica_context().replica_tag,
        }

    @router.post("/generate")
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
    ) -> Dict[str, str]:
        """Start a video generation task and return a task ID."""
        if not self.model_status.is_loaded:
            raise HTTPException(
                status_code=503,
                detail=f"Model is not available. Error: {self.model_status.error}",
            )

        try:
            VideoGenerationValidator.validate_prompt(prompt)
            params = VideoGenerationValidator.validate_all(
                self.model_name,
                prompt,
                guidance_scale,
                num_inference_steps,
                num_frames,
                fps,
            )
            task_id = str(uuid.uuid4())
            task = GenerationTask(
                id=task_id,
                status=TaskStatus.PENDING,
                created_at=datetime.now(),
                prompt=prompt,
                params=params
            )
            self.tasks[task_id] = task
            asyncio.create_task(self._generate_video(task_id))
            return {
                "task_id": task_id,
                "status": TaskStatus.PENDING,
                "status_endpoint": f"/imagine/tasks/{task_id}/status",
                "video_endpoint": f"/imagine/tasks/{task_id}/video"
            }
        except Exception as e:
            logger.error(f"Error starting video generation: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def _generate_video(self, task_id: str):
        """Background task to generate the video."""
        task = self.tasks[task_id]
        task.status = TaskStatus.PROCESSING

        try:
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
                video_path = tmp_file.name
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.model_status.model.generate(
                    prompt=task.prompt,
                    num_frames=task.params["num_frames"],
                    fps=task.params["fps"],
                    guidance_scale=task.params["guidance_scale"],
                    num_inference_steps=task.params["num_inference_steps"],
                    output_path=video_path,
                )
            )

            if not os.path.exists(video_path):
                raise Exception("Video generation failed - file not created")
            task.status = TaskStatus.COMPLETED
            task.video_path = video_path
            task.completed_at = datetime.now()
        except Exception as e:
            logger.error(f"Error generating video for task {task_id}, cache collected: {e}")
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()
            gc.collect()
            torch.xpu.empty_cache()

    @router.get("/tasks/{task_id}/status")
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a generation task."""
        task = self.tasks.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return {
            "task_id": task.id,
            "status": task.status,
            "created_at": task.created_at.isoformat(),
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "error": task.error,
            "progress": task.progress
        }

    @router.get("/tasks/{task_id}/video")
    async def get_video(self, task_id: str) -> FileResponse:
        """Get the generated video for a completed task."""
        task = self.tasks.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if task.status != TaskStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail=f"Video not ready. Current status: {task.status}"
            )
        if not task.video_path or not os.path.exists(task.video_path):
            raise HTTPException(status_code=404, detail="Video file not found")
        headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
        return FileResponse(
            path=task.video_path,
            media_type="video/mp4",
            filename=f"generated_video_{task_id}.mp4",
            headers=headers
        )

    @router.delete("/tasks/{task_id}")
    async def delete_task(self, task_id: str):
        """Delete a task and its associated files."""
        task = self.tasks.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if task.video_path and os.path.exists(task.video_path):
            try:
                os.unlink(task.video_path)
            except Exception as e:
                logger.error(f"Error removing file for task {task_id}: {e}")
        del self.tasks[task_id]
        return {"status": "deleted"}

entrypoint = VideoGenerationServer.bind()
