from typing import Any, Dict, Optional, Union

from fastapi import HTTPException

from config.model_configs import MODEL_CONFIGS as VIDEO_MODEL_CONFIGS


class VideoGenerationValidator:
    """Validation utilities for video generation parameters."""

    MAX_PROMPT_LENGTH = 300
    MAX_GUIDANCE_SCALE = 10.0
    MAX_INFERENCE_STEPS = 50

    @classmethod
    def validate_prompt(cls, prompt: str) -> None:
        """Validate generation prompt."""
        prompt = prompt.strip()
        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt cannot be empty")
        if len(prompt) > cls.MAX_PROMPT_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"Prompt too long (max {cls.MAX_PROMPT_LENGTH} characters)",
            )

    @staticmethod
    def validate_range(
        value: Optional[Union[int, str]],
        min_val: int,
        max_val: int,
        name: str,
        default: int,
    ) -> int:
        """Validate a numeric value is within a given range, or use the default."""
        if value is None:
            return default
        try:
            value_int = int(value)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail=f"{name} must be an integer")
        if not min_val <= value_int <= max_val:
            raise HTTPException(
                status_code=400,
                detail=f"{name} must be between {min_val} and {max_val} (provided: {value})",
            )
        return value_int

    @classmethod
    def validate_generation_params(
        cls,
        model_name: str,
        guidance_scale: Optional[Union[float, int, str]] = None,
        num_inference_steps: Optional[Union[int, str]] = None,
        num_frames: Optional[Union[int, str]] = None,
        fps: Optional[Union[int, str]] = None,
    ) -> Dict[str, Any]:
        """Validate and prepare generation parameters."""
        config = VIDEO_MODEL_CONFIGS.get(model_name)
        if not config:
            raise HTTPException(status_code=400, detail=f"Unknown model: {model_name}")
        if guidance_scale is None:
            guidance_scale_float = config.get("default_guidance", 6.0)
        else:
            try:
                guidance_scale_float = float(guidance_scale)
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=400, detail="Guidance scale must be a number"
                )
            if not 0 <= guidance_scale_float <= cls.MAX_GUIDANCE_SCALE:
                raise HTTPException(
                    status_code=400,
                    detail=f"Guidance scale must be between 0 and {cls.MAX_GUIDANCE_SCALE}",
                )
        steps_int = cls.validate_range(
            num_inference_steps,
            1,
            cls.MAX_INFERENCE_STEPS,
            "Number of steps",
            config.get("default_steps", 50),
        )
        frames_int = cls.validate_range(
            num_frames,
            config["min_frames"],
            config["max_frames"],
            "Number of frames",
            config.get("default_frames", 49),
        )
        fps_int = cls.validate_range(
            fps,
            config.get("min_fps", 1),
            config.get("max_fps", 60),
            "FPS",
            config.get("default_fps", 24),
        )
        return {
            "guidance_scale": guidance_scale_float,
            "num_inference_steps": steps_int,
            "num_frames": frames_int,
            "fps": fps_int,
        }

    @classmethod
    def validate_all(
        cls,
        model_name: str,
        prompt: str,
        guidance_scale: Optional[Union[float, int, str]] = None,
        num_inference_steps: Optional[Union[int, str]] = None,
        num_frames: Optional[Union[int, str]] = None,
        fps: Optional[Union[int, str]] = None,
    ) -> Dict[str, Any]:
        """Validate all parameters at once."""
        cls.validate_prompt(prompt)
        return cls.validate_generation_params(
            model_name, guidance_scale, num_inference_steps, num_frames, fps
        )
