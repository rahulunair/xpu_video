# ⚡ XPU Ray Video Generation Service

A high-performance video generation service powered by Intel XPU and Ray Serve, supporting multiple video models with authentication and load balancing.

- [Video 01](generated_videos/01.mp4)
- [Video 02](generated_videos/02.mp4)
- [Video 03](generated_videos/03.mp4)
- [Video 04](generated_videos/04.mp4)

<div align="center">
  <p><i>Videos generated using CogVideoX-2B and CogVideoX-5B models on Intel Max Series GPU VM 1100</i></p>
</div>

## ✨ Features

- Multiple Model Support:
  - CogVideoX-2B
  - CogVideoX-5B

- Intel XPU Optimization:
  - Optimized for Intel GPUs using Intel Extension for PyTorch
  - Efficient memory management
  - Hardware-accelerated inference

- Production-Ready Features:
  - Token-based authentication
  - Load balancing with Traefik
  - Health checks and monitoring
  - Automatic model management
  - Request queuing and rate limiting

- Cloud Deployment:
  - For cloud deployments, explore Intel Tiber AI Cloud at [https://cloud.intel.com](https://cloud.intel.com)

## Prerequisites

- Docker and Docker Compose
- Intel GPU with appropriate drivers
- 32GB+ RAM recommended
- Ubuntu 22.04 or later

## Model Selection

### Available Models
- **CogVideoX-2B**: Optimized for standard video generation with 49-frame limits.
- **CogVideoX-5B**: Capable of generating videos up to 6 seconds (48 frames at 8 FPS).

### Choosing a Model
```bash
# Deploy with specific model
./deploy.sh <model-name>

# Examples:
./deploy.sh cogvideox-2b    # Standard video generation
./deploy.sh cogvideox-5b    # Higher quality and longer videos
```

### Switching Models
To switch models without restarting base services:
```bash
./deploy.sh <model-name> --skip-base
```

## Quick Start

1. Clone the repository:
```bash
git clone https://github.com/rahulunair/xpu_video.git
cd xpu_video
```

2. Deploy the service:
```bash
./deploy.sh
```

The script will:
- Generate an authentication token
- Start all services
- Wait for model to load
- Display the API endpoint and token

## Authentication Setup

1. Source the token file:
```bash
source .auth_token.env
```

2. Verify token is set:
```bash
echo $VALID_TOKEN
```

See `./examples.md` for detailed API usage examples.

## API Overview

Main endpoints:
- `/imagine/generate` - Generate videos
- `/imagine/health` - Check service health
- `/imagine/info` - Get model information

See `./api.md` for complete API documentation.

## Model Configurations

| Model          | Max Frames | FPS  | Guidance | Default Steps |
|----------------|------------|------|----------|---------------|
| CogVideoX-2B   | 49         | 24   | 7.5      | 50            |
| CogVideoX-5B   | 48         | 8    | 7.5      | 75            |

## Management Commands

```bash
# Start services
docker compose up -d

# Stop services
docker compose down

# View logs
docker compose logs -f

# Monitor video generation service
./monitor_video.sh

# Clean up all running services
./cleanup.sh
```

## Security & Performance

- Token-based authentication
- Production-grade rate limiting:
  - Global limit: 30 requests/sec, burst up to 60
  - Per-IP limit: 15 requests/sec, burst up to 30
- Model caching and efficient memory management
- Optimized for Intel GPUs

### Single GPU Performance Guidelines (Intel Max GPU)

Testing with CogVideoX-2B on a single Intel Max GPU VM using the service:
- ~ 1 video (49 frames at 24 FPS) every 2 minutes
- Can serve ~15-20 users/hour

An 8-GPU system can typically support ~100-120 users/hour with CogVideoX-2B.

### Performance Tuning

The service includes benchmark tools to test and optimize for your specific hardware:
```bash
cd benchmarks
./scripts/stress_test.sh
```

You can adjust:
- Traefik rate limits in `config/traefik/dynamic.yml`
- Ray Serve settings in `serve_config.yaml`
- Model parameters in deployment scripts

See `benchmarks/README.md` for detailed performance testing instructions.

## Model Cache

Models are cached in `${HOME}/.cache/huggingface` to improve load times and reduce bandwidth usage.

## Benchmarking

For load testing and performance benchmarking tools, see the `benchmarks` directory.

The benchmarks include:
- Stress testing
- Concurrent request handling
- Service health monitoring
- Performance metrics collection

See `benchmarks/README.md` for setup and usage instructions.

## Acknowledgments

Built with Intel Extension for PyTorch, Hugging Face Diffusers, and Ray Project


