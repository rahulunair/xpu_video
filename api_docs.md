# Video Generation API Documentation

This document provides the details and `curl` examples for interacting with the Video Generation API.

## Base URL

```
http://localhost:9000
```

## Endpoints

### 1. **Health Check**

#### **GET** `/health`

Check the health status of the server and model.

#### Response
```json
{
  "status": "healthy"
}
```

#### `curl` Example
```bash
curl -X GET http://localhost:9000/health
```

---

### 2. **Model and System Information**

#### **GET** `/info`

Retrieve information about the loaded model and system.

#### Response
```json
{
  "model": "cogvideox",
  "is_loaded": true,
  "error": null,
  "config": {
    "default_steps": 50,
    "default_guidance": 6.0,
    "min_frames": 8,
    "max_frames": 100,
    "default_fps": 24
  },
  "system_info": {
    "cpu_usage": "10%",
    "memory_usage": "30%",
    "gpu_usage": "50%"
  }
}
```

#### `curl` Example
```bash
curl -X GET http://localhost:9000/info
```

---

### 3. **Video Generation**

#### **POST** `/generate`

Generate a video based on the given parameters.

#### Request Body (JSON)
- **`prompt`** *(string, required)*: The prompt for video generation.
- **`num_frames`** *(integer, optional)*: Number of frames to generate.
- **`fps`** *(integer, optional)*: Frames per second.
- **`guidance_scale`** *(float, optional)*: Guidance scale for generation.
- **`num_inference_steps`** *(integer, optional)*: Number of inference steps for generation.

#### Example Request Body
```json
{
  "prompt": "A serene sunset over the ocean with birds flying in the sky.",
  "num_frames": 49,
  "fps": 24,
  "guidance_scale": 7.5,
  "num_inference_steps": 50
}
```

#### Response
- Returns an MP4 video file.

#### `curl` Example
```bash
curl -X POST \
  -H "Authorization: Bearer $VALID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A serene sunset over the ocean with birds flying in the sky.",
    "num_frames": 49,
    "fps": 24,
    "guidance_scale": 7.5,
    "num_inference_steps": 50
  }' \
  http://localhost:9000/generate -o generated_video.mp4
```

This command will save the generated video as `generated_video.mp4` locally.

---

## Notes
- Ensure the `Authorization` header includes a valid bearer token.
- The `num_frames` and `fps` parameters determine the length and quality of the generated video.
- Use the `/info` endpoint to get detailed model and system configurations before generating a video.


