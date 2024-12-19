# Video Generation API Documentation

This document provides details for interacting with the Video Generation API, which supports multiple video generation models.

## Base URL & Port Configuration

**Local Development (on the same host as the service is setup):**
```
http://localhost:9000  # Default port
```

**Cloudflare Tunnel (Evaluation Only):**
1. Start the tunnel (default port 9000):
```bash
./tunnel.sh
```

2. Or specify a custom port:
```bash
./tunnel.sh --port <custom_port>
```

After running the tunnel script, you'll get a Cloudflare URL like:
```
https://<random-string>.trycloudflare.com
```

> **Note:** 
> - The default port is 9000
> - Change the port only if the default port conflicts with other services
> - When using a custom port, ensure your application is configured to use the same port

## Supported Models
- **cogvideoX2b** (default): CogVideoX 2B parameter model
- **cogvideoX5b**: CogVideoX 5B parameter model
- **animatediff**: AnimateDiff-Lightning model

## Authentication
All endpoints require authentication using a Bearer token:
```
Authorization: Bearer <your_token>
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

#### Example
```bash
curl -X GET \
  -H "Authorization: Bearer $VALID_TOKEN" \
  http://localhost:9000/imagine/health
```

---

### 2. **Model and System Information**

#### **GET** `/info`
Retrieve information about the loaded model and system.

#### Response
```json
{
  "model": "cogvideoX2b",
  "is_loaded": true,
  "error": null,
  "config": {
    "default_steps": 50,
    "default_guidance": 6.0,
    "min_frames": 8,
    "max_frames": 49,
    "default_frames": 49,
    "min_fps": 1,
    "max_fps": 60,
    "default_fps": 49
  }
}
```

#### Example
```bash
curl -X GET \
  -H "Authorization: Bearer $VALID_TOKEN" \
  http://localhost:9000/imagine/info
```

---

### 3. **Video Generation**

#### **POST** `/generate`
Generate a video based on the given parameters.

#### Request Headers
- **`Authorization`** *(required)*: Bearer token
- **`Content-Type`**: application/json

#### Request Body Parameters
| Parameter | Type | Description | Model-Specific Limits |
|-----------|------|-------------|---------------------|
| `prompt` | string | Text description of the video to generate | Required for all models |
| `num_frames` | integer | Number of frames to generate | CogVideoX: 8-49 frames (default: 49)<br>AnimateDiff: 8-32 frames (default: 16) |
| `fps` | integer | Frames per second | CogVideoX: 1-60 (default: 49)<br>AnimateDiff: 1-30 (default: 8) |
| `guidance_scale` | float | Guidance scale for generation | CogVideoX: 1-10 (default: 6.0)<br>AnimateDiff: 1-10 (default: 1.0) |
| `num_inference_steps` | integer | Number of inference steps | CogVideoX: 1-50 (default: 50)<br>AnimateDiff: [1,2,4,8] only (default: 4) |

#### Example Requests

**CogVideoX (2B/5B)**:
```bash
curl -X POST \
  -H "Authorization: Bearer $VALID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A serene sunset over the ocean with birds flying in the sky.",
    "num_frames": 49,
    "fps": 49,
    "guidance_scale": 6.0,
    "num_inference_steps": 50
  }' \
  http://localhost:9000/imagine/generate
```

**AnimateDiff**:
```bash
curl -X POST \
  -H "Authorization: Bearer $VALID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A serene sunset over the ocean with birds flying in the sky.",
    "num_frames": 16,
    "fps": 8,
    "guidance_scale": 1.0,
    "num_inference_steps": 4
  }' \
  http://localhost:9000/imagine/generate
```

#### Response
- CogVideoX models return MP4 video files
- AnimateDiff returns GIF files

## Notes
- Each model has different optimal parameters and limitations
- Use the `/info` endpoint to get model-specific configurations
- For public access (evaluation only), use the Cloudflare tunnel URL instead of localhost
- The API validates parameters based on the selected model's constraints


