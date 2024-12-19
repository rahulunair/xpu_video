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

## Environment Variables
- `DEFAULT_MODEL`: Set default model (default: "cogvideoX2b")
- `VALID_TOKEN`: Authentication token


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

#### **POST** `/imagine/generate`
Generate a video based on the given parameters.

#### Request Headers
- **`Authorization`** *(required)*: Bearer token
- **`Content-Type`**: application/json

#### Request Body Parameters
| Parameter | Type | Description | Required | Model-Specific Details |
|-----------|------|-------------|----------|----------------------|
| `prompt` | string | Text description of the video to generate | Yes | Required for all models |
| `guidance_scale` | float | Controls how closely the model follows the prompt | No | AnimateDiff: Default 1.0 (recommended)<br>CogVideoX: Default 6.0 |
| `num_frames` | integer | Number of frames to generate | No | AnimateDiff: Default 8 (8-32)<br>CogVideoX: Default 24 (8-49) |
| `fps` | integer | Frames per second | No | AnimateDiff: Default 8 (1-30)<br>CogVideoX: Default 49 (1-60) |
| `num_inference_steps` | integer | Number of inference steps | No | AnimateDiff: [1,2,4,8] only (default: 4)<br>CogVideoX: 1-50 (default: 50) |

#### Minimal Request Examples

**AnimateDiff (Recommended Settings)**:
```bash
curl -X POST \
  -H "Authorization: Bearer $VALID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A cute cartoon robot waving hello, digital art style",
    "guidance_scale": 1.0
  }' \
  http://localhost:9000/imagine/generate --output animation.gif
```

**CogVideoX**:
```bash
curl -X POST \
  -H "Authorization: Bearer $VALID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A friendly cartoon robot dancing, digital art style",
    "guidance_scale": 6.0
  }' \
  http://localhost:9000/imagine/generate --output video.mp4
```

#### Request Schema

#### Input JSON Schema
```json
{
  "prompt": "string",
  "guidance_scale": "number (optional)",
  "num_frames": "integer (optional)",
  "fps": "integer (optional)",
  "num_inference_steps": "integer (optional)"
}
```

#### Example Request Body
```json
{
  "prompt": "A cute cartoon robot waving hello, digital art style",
  "guidance_scale": 1.0,
  "num_frames": 16,
  "fps": 8,
  "num_inference_steps": 4
}
```

#### Response
For AnimateDiff:
- **Content-Type**: `image/gif`
- **File**: Binary GIF data
- **Filename**: `generated_animation.gif`

For CogVideoX:
- **Content-Type**: `video/mp4`
- **File**: Binary MP4 data
- **Filename**: `generated_video.mp4`

#### Error Response Schema
```json
{
  "detail": "string (error message)"
}
```

#### Example Error Response
```json
{
  "detail": "Prompt cannot be empty"
}
```


## Model-Specific Recommendations

### AnimateDiff
- Best for: Short animations, cartoon-style content
- Optimal settings:
  - `guidance_scale`: 1.0
  - `num_inference_steps`: 4
  - `num_frames`: 8-16
  - `fps`: 8

### CogVideoX
- Best for: Realistic videos, longer sequences
- Optimal settings:
  - `guidance_scale`: 6.0
  - `num_inference_steps`: 50
  - `num_frames`: 24-32
  - `fps`: 49


