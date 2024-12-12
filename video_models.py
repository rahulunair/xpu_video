import warnings

warnings.filterwarnings("ignore")

import logging
from typing import Any, Dict, List
import torch
import intel_extension_for_pytorch as ipex
from diffusers import CogVideoXPipeline
from diffusers.utils import export_to_video
import time

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING)


def optimize_transformer(model, device="xpu", dtype=torch.bfloat16):
    """Optimize transformer models with IPEX"""
    model = model.to(device=device, dtype=dtype)
    try:
        logger.info(f"Optimizing transformer: {type(model).__name__}")
        return ipex.optimize_transformers(
            model.eval(), device=device, dtype=model.dtype, inplace=True
        )
    except Exception as e:
        logger.warning(
            f"IPEX transformer optimization failed: {e}, continuing without optimization"
        )
        return model


def perform_inference(pipe, prompt: str, **kwargs) -> List[torch.Tensor]:
    """Perform inference with optimized settings."""
    try:
        with torch.inference_mode(), torch.xpu.amp.autocast():
            return pipe(
                prompt=prompt,
                num_videos_per_prompt=kwargs.get("num_videos_per_prompt", 1),
                num_inference_steps=kwargs.get("num_inference_steps", 50),
                num_frames=kwargs.get("num_frames", 49),
                guidance_scale=kwargs.get("guidance_scale", 6),
                generator=torch.Generator(
                    device=kwargs.get("device", "xpu")
                ).manual_seed(42),
            ).frames[0]
    except Exception as e:
        logger.error(f"Generation failed: {str(e)}")
        raise
    finally:
        if hasattr(torch.xpu, "empty_cache"):
            torch.xpu.empty_cache()


class BaseVideoModel:
    def generate(self, prompt: str, **kwargs) -> str:
        raise NotImplementedError

    def get_model_info(self) -> Dict[str, Any]:
        raise NotImplementedError


class CogVideoXModel(BaseVideoModel):
    def __init__(self, device: str = "xpu", dtype: torch.dtype = torch.bfloat16):
        self.model_id = "THUDM/CogVideoX-2b"
        self.device = device
        self.dtype = dtype
        self._initialize_model()

    def _initialize_model(self):
        self.pipe = CogVideoXPipeline.from_pretrained(
            self.model_id, torch_dtype=self.dtype
        )
        self.pipe = self.pipe.to(device=self.device, dtype=self.dtype)

        # Enable optimizations
        self.pipe.vae.enable_slicing()
        self.pipe.vae.enable_tiling()
        self.pipe = self.pipe.to(self.device)

        # Optimize components
        self.pipe.text_encoder = self.pipe.text_encoder.to(
            device=self.device, dtype=self.dtype
        )
        self.pipe.text_encoder = optimize_transformer(self.pipe.text_encoder)

        self.pipe.vae = self.pipe.vae.to(device=self.device, dtype=self.dtype)
        self.pipe.vae = ipex.optimize(self.pipe.vae, dtype=self.dtype, inplace=True)

        self.pipe.transformer = self.pipe.transformer.to(
            device=self.device, dtype=self.dtype
        )
        self.pipe.transformer = optimize_transformer(self.pipe.transformer)

        # Perform warmup
        self._warmup()

        logger.info(
            f"Initialized {self.model_id} with device={self.device}, dtype={self.dtype}"
        )

    def _warmup(self):
        """Perform warmup inference"""
        logger.info("Starting warmup...")
        with torch.inference_mode(), torch.xpu.amp.autocast():
            _ = self.pipe(
                prompt="test",
                num_videos_per_prompt=1,
                num_inference_steps=1,
                num_frames=8,
                guidance_scale=6,
                generator=torch.Generator(device=self.device).manual_seed(42),
            )
        if torch.xpu.is_available():
            torch.xpu.synchronize()
        logger.info("Warmup completed")

    def generate(self, prompt: str, **kwargs) -> str:
        start_time = time.time()
        video_frames = perform_inference(
            self.pipe, prompt, device=self.device, **kwargs
        )

        output_path = kwargs.get("output_path", "output.mp4")
        fps = kwargs.get("fps", 49)
        export_to_video(video_frames, output_path, fps=fps)

        inference_time = time.time() - start_time
        logger.info(f"Inference time: {inference_time:.2f} seconds")
        logger.info(f"Video saved as: {output_path}")

        return output_path

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "model_type": "CogVideoX",
            "device": self.device,
            "dtype": str(self.dtype),
        }


class CogVideoX5BModel(BaseVideoModel):
    def __init__(self, device: str = "xpu", dtype: torch.dtype = torch.bfloat16):
        self.model_id = "THUDM/CogVideoX-5b"
        self.device = device
        self.dtype = dtype
        self._initialize_model()

    def _initialize_model(self):
        self.pipe = CogVideoXPipeline.from_pretrained(
            self.model_id, torch_dtype=self.dtype
        )
        self.pipe = self.pipe.to(device=self.device, dtype=self.dtype)

        # Enable optimizations
        self.pipe.vae.enable_slicing()
        self.pipe.vae.enable_tiling()
        self.pipe = self.pipe.to(self.device)

        # Optimize components
        self.pipe.text_encoder = self.pipe.text_encoder.to(
            device=self.device, dtype=self.dtype
        )
        self.pipe.text_encoder = optimize_transformer(self.pipe.text_encoder)

        self.pipe.vae = self.pipe.vae.to(device=self.device, dtype=self.dtype)
        self.pipe.vae = ipex.optimize(self.pipe.vae, dtype=self.dtype, inplace=True)

        self.pipe.transformer = self.pipe.transformer.to(
            device=self.device, dtype=self.dtype
        )
        self.pipe.transformer = optimize_transformer(self.pipe.transformer)

        # Perform warmup
        self._warmup()

        logger.info(
            f"Initialized {self.model_id} with device={self.device}, dtype={self.dtype}"
        )

    def _warmup(self):
        """Perform warmup inference"""
        logger.info("Starting warmup...")
        with torch.inference_mode(), torch.xpu.amp.autocast():
            _ = self.pipe(
                prompt="test",
                num_videos_per_prompt=1,
                num_inference_steps=1,
                num_frames=8,
                guidance_scale=6,
                generator=torch.Generator(device=self.device).manual_seed(42),
            )
        if torch.xpu.is_available():
            torch.xpu.synchronize()
        logger.info("Warmup completed")

    def generate(self, prompt: str, **kwargs) -> str:
        start_time = time.time()
        video_frames = perform_inference(
            self.pipe, prompt, device=self.device, **kwargs
        )

        output_path = kwargs.get("output_path", "output.mp4")
        fps = kwargs.get("fps", 49)
        export_to_video(video_frames, output_path, fps=fps)

        inference_time = time.time() - start_time
        logger.info(f"Inference time: {inference_time:.2f} seconds")
        logger.info(f"Video saved as: {output_path}")

        return output_path

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "model_type": "CogVideo5B",
            "device": self.device,
            "dtype": str(self.dtype),
        }


class VideoModelFactory:
    @staticmethod
    def create_model(model_type: str, **kwargs) -> BaseVideoModel:
        models = {
            "cogvideox": CogVideoXModel,
            "cogvideo5b": CogVideoX5BModel,
        }
        if model_type not in models:
            raise ValueError(f"Unknown model type: {model_type}")
        return models[model_type](**kwargs)
