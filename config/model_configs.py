MODEL_CONFIGS = {
    "cogvideoX2b": {
        "default_steps": 50,
        "default_guidance": 6.0,
        "min_frames": 8,
        "max_frames": 49,
        "default_frames": 24,
        "min_fps": 1,
        "max_fps": 60,
        "default_fps": 49,
        "default": True,
    },
    "cogvideoX5b": {
        "default_steps": 50,
        "default_guidance": 6.0,
        "min_frames": 8,
        "max_frames": 49,
        "default_frames": 24,
        "min_fps": 1,
        "max_fps": 60,
        "default_fps": 49,
        "default": False,
    },
    "animatediff": {
        "min_frames": 8,
        "max_frames": 32,
        "default_frames": 8,
        "min_fps": 1,
        "max_fps": 30,
        "default_fps": 8,
        "default_steps": 4,
        "valid_steps": [1, 2, 4, 8],
        "default_guidance": 1.0,
        "default": False,
    },
}
