from typing import Any, Dict, Optional, Union
from fastapi import HTTPException

from config.model_configs import MODEL_CONFIGS as VIDEO_MODEL_CONFIGS

class VideoGenerationValidator:
    """Validation utilities for video generation parameters."""

    MAX_PROMPT_LENGTH: int = 300
    MAX_GUIDANCE_SCALE: float = 10.0
    MAX_INFERENCE_STEPS: int = 50
    
    @classmethod
    def validate_prompt(cls, prompt: str) -> None:
        """Validate generation prompt."""
        if not prompt or not prompt.strip():
            raise HTTPException(status_code=400, detail="Prompt cannot be empty")
        if len(prompt) > cls.MAX_PROMPT_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"Prompt too long (max {cls.MAX_PROMPT_LENGTH} characters)"
            )

    @classmethod
    def validate_num_frames(cls, model_name: str, num_frames: Union[int, str]) -> int:
        """Validate number of frames is within model's allowed range."""
        config = VIDEO_MODEL_CONFIGS[model_name]

        try:
            frames_int = int(num_frames)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Number of frames must be an integer")

        if frames_int < config["min_frames"] or frames_int > config["max_frames"]:
            raise HTTPException(
                status_code=400,
                detail=f"Number of frames must be between {config['min_frames']} and {config['max_frames']}"
            )
        
        return frames_int

    @classmethod
    def validate_fps(cls, model_name: str, fps: Optional[Union[int, str]] = None) -> int:
        """Validate FPS value."""
        config = VIDEO_MODEL_CONFIGS[model_name]
        
        if fps is None:
            return config["default_fps"]

        try:
            fps_int = int(fps)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="FPS must be an integer")

        min_fps, max_fps = config["fps_range"]
        if fps_int < min_fps or fps_int > max_fps:
            raise HTTPException(
                status_code=400,
                detail=f"FPS must be between {min_fps} and {max_fps}"
            )
        
        return fps_int

    @classmethod
    def validate_generation_params(
        cls,
        model_name: str,
        guidance_scale: Optional[Union[float, int, str]] = None,
        num_inference_steps: Optional[Union[int, str]] = None,
        num_frames: Optional[Union[int, str]] = None,
        fps: Optional[Union[int, str]] = None
    ) -> Dict[str, Any]:
        """Validate and prepare generation parameters."""
        if model_name not in VIDEO_MODEL_CONFIGS:
            raise HTTPException(status_code=400, detail=f"Unknown model: {model_name}")

        config = VIDEO_MODEL_CONFIGS[model_name]

        # Validate guidance scale
        if guidance_scale is not None:
            try:
                guidance_scale_float = float(guidance_scale)
            except (ValueError, TypeError):
                raise HTTPException(status_code=400, detail="Guidance scale must be a number")

            if guidance_scale_float < 0 or guidance_scale_float > cls.MAX_GUIDANCE_SCALE:
                raise HTTPException(
                    status_code=400,
                    detail=f"Guidance scale must be between 0 and {cls.MAX_GUIDANCE_SCALE}"
                )
        else:
            guidance_scale_float = config["default_guidance"]

        # Validate inference steps
        if num_inference_steps is not None:
            try:
                steps_int = int(num_inference_steps)
            except (ValueError, TypeError):
                raise HTTPException(status_code=400, detail="Number of steps must be an integer")

            if steps_int < 1 or steps_int > cls.MAX_INFERENCE_STEPS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Number of steps must be between 1 and {cls.MAX_INFERENCE_STEPS}"
                )
        else:
            steps_int = config["default_steps"]

        # Validate number of frames
        frames_int = (
            cls.validate_num_frames(model_name, num_frames)
            if num_frames is not None
            else config["default_frames"]
        )

        # Validate FPS
        fps_int = cls.validate_fps(model_name, fps)

        return {
            "guidance_scale": guidance_scale_float,
            "num_inference_steps": steps_int,
            "num_frames": frames_int,
            "fps": fps_int
        }

    @classmethod
    def validate_all(
        cls,
        model_name: str,
        prompt: str,
        guidance_scale: Optional[Union[float, int, str]] = None,
        num_inference_steps: Optional[Union[int, str]] = None,
        num_frames: Optional[Union[int, str]] = None,
        fps: Optional[Union[int, str]] = None
    ) -> Dict[str, Any]:
        """Validate all parameters at once."""
        cls.validate_prompt(prompt)
        params = cls.validate_generation_params(
            model_name,
            guidance_scale,
            num_inference_steps,
            num_frames,
            fps
        )
        return params
