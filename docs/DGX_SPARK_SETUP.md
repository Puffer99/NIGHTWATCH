# NVIDIA DGX Spark Setup Guide (Step 635)

This document covers deploying NIGHTWATCH's AI inference capabilities on the NVIDIA DGX Spark platform for local LLM processing.

## Overview

The DGX Spark is a personal AI supercomputer designed for edge deployment. For NIGHTWATCH, it enables:

- Local LLM inference without cloud dependency
- Low-latency voice command processing
- Real-time image analysis and object detection
- Autonomous decision making during offline operation

## Hardware Requirements

### DGX Spark Specifications
- NVIDIA Grace CPU (72 ARM Neoverse cores)
- 128GB unified memory (CPU + GPU shared)
- NVIDIA Blackwell GPU with 1 PFLOP FP4 AI
- NVMe storage (minimum 512GB recommended)
- Ubuntu-based Linux OS

### Network Requirements
- Ethernet connection to observatory network
- Static IP recommended for service discovery
- Optional: WiFi for mobile deployment

## Software Prerequisites

### 1. NVIDIA Container Toolkit

```bash
# Add NVIDIA container repository
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

# Install container toolkit
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### 2. Python Environment

```bash
# Create NIGHTWATCH environment
python3 -m venv /opt/nightwatch/venv
source /opt/nightwatch/venv/bin/activate
pip install --upgrade pip

# Install NIGHTWATCH
pip install -r requirements.txt
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
```

## LLM Deployment Options

### Option A: Ollama (Recommended for Simplicity)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull recommended models
ollama pull llama3.2:8b        # Primary reasoning
ollama pull nomic-embed-text   # Embeddings
ollama pull llava:7b           # Vision tasks

# Configure Ollama service
sudo systemctl enable ollama
sudo systemctl start ollama
```

Configure NIGHTWATCH to use Ollama:

```yaml
# config/nightwatch.yaml
llm:
  provider: ollama
  base_url: http://localhost:11434
  model: llama3.2:8b
  vision_model: llava:7b
  embedding_model: nomic-embed-text
  timeout_sec: 30
```

### Option B: vLLM (Recommended for Performance)

```bash
# Install vLLM
pip install vllm

# Start vLLM server with Llama 3.2
vllm serve meta-llama/Llama-3.2-8B-Instruct \
  --host 0.0.0.0 \
  --port 8000 \
  --dtype auto \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.8
```

Configure for vLLM:

```yaml
# config/nightwatch.yaml
llm:
  provider: openai_compatible
  base_url: http://localhost:8000/v1
  api_key: "not-needed"
  model: meta-llama/Llama-3.2-8B-Instruct
```

### Option C: TensorRT-LLM (Maximum Performance)

For production deployments requiring maximum throughput:

```bash
# Clone TensorRT-LLM
git clone https://github.com/NVIDIA/TensorRT-LLM.git
cd TensorRT-LLM

# Build engine for Llama 3.2
python examples/llama/convert_checkpoint.py \
  --model_dir /models/Llama-3.2-8B-Instruct \
  --output_dir /models/llama-3.2-trtllm \
  --dtype float16

# Run with Triton Inference Server
docker run --gpus all -p 8000:8000 \
  -v /models:/models \
  nvcr.io/nvidia/tritonserver:24.10-trtllm-python-py3 \
  tritonserver --model-repository=/models/llama-3.2-trtllm
```

## Voice Processing Setup

### Whisper for Speech-to-Text

```bash
# Install faster-whisper (optimized for NVIDIA)
pip install faster-whisper

# Or use NVIDIA Riva for production
# See: https://docs.nvidia.com/deeplearning/riva/
```

Configure voice pipeline:

```yaml
# config/nightwatch.yaml
voice:
  stt:
    provider: faster_whisper
    model: large-v3
    device: cuda
    compute_type: float16

  tts:
    provider: piper
    model: en_US-lessac-medium
```

## Image Analysis Setup

### Object Detection for Astronomy

```bash
# Install dependencies
pip install ultralytics  # For YOLO models

# Download astronomy-specific model (if available)
# Or train custom model for satellite/meteor detection
```

### Plate Solving with GPU Acceleration

```bash
# Install astrometry.net with CUDA support
# Note: Requires building from source with CUDA enabled
```

## Service Configuration

### Systemd Service for NIGHTWATCH AI

Create `/etc/systemd/system/nightwatch-ai.service`:

```ini
[Unit]
Description=NIGHTWATCH AI Inference Service
After=network.target ollama.service

[Service]
Type=simple
User=nightwatch
WorkingDirectory=/opt/nightwatch
Environment="CUDA_VISIBLE_DEVICES=0"
ExecStart=/opt/nightwatch/venv/bin/python -m nightwatch.ai_service
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable nightwatch-ai
sudo systemctl start nightwatch-ai
```

## Performance Tuning

### Memory Management

```bash
# Set GPU memory fraction (in nightwatch config)
# Default: 0.8 (reserve 20% for system)

# For shared memory systems (like DGX Spark unified memory):
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
```

### Inference Optimization

```yaml
# config/nightwatch.yaml
inference:
  batch_size: 4
  use_flash_attention: true
  quantization: int8  # Options: none, int8, int4
  cache_prompt: true
  max_concurrent_requests: 8
```

## Network Configuration

### Firewall Rules

```bash
# Allow LLM API access from observatory network
sudo ufw allow from 192.168.1.0/24 to any port 11434  # Ollama
sudo ufw allow from 192.168.1.0/24 to any port 8000   # vLLM
```

### Service Discovery

NIGHTWATCH uses mDNS for automatic service discovery:

```yaml
# config/nightwatch.yaml
network:
  mdns:
    enabled: true
    service_name: nightwatch-ai
    service_type: _nightwatch._tcp
```

## Monitoring

### GPU Metrics

```bash
# Monitor GPU usage
watch -n 1 nvidia-smi

# Or use DCGM for detailed metrics
dcgmi dmon -e 155,156,157,200,201,203,204
```

### Log Files

- LLM inference: `/var/log/nightwatch/llm.log`
- Voice pipeline: `/var/log/nightwatch/voice.log`
- System metrics: `/var/log/nightwatch/metrics.log`

## Troubleshooting

### Common Issues

1. **Out of Memory (OOM)**
   - Reduce model size or batch size
   - Enable quantization (int8 or int4)
   - Check for memory leaks with `nvidia-smi`

2. **Slow Inference**
   - Verify GPU is being used: `watch nvidia-smi`
   - Check for thermal throttling
   - Enable flash attention if supported

3. **Service Won't Start**
   - Check CUDA installation: `nvcc --version`
   - Verify model files exist
   - Check permissions on model directory

### Diagnostic Commands

```bash
# Check CUDA
python -c "import torch; print(torch.cuda.is_available())"

# Check Ollama status
curl http://localhost:11434/api/tags

# Test inference
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2:8b",
  "prompt": "What is the current moon phase?"
}'
```

## Security Considerations

1. **API Security**: The LLM API should only be accessible from the local network
2. **Model Integrity**: Verify model checksums after download
3. **Prompt Injection**: NIGHTWATCH sanitizes all user inputs before LLM processing
4. **Logging**: Avoid logging sensitive observatory data

## References

- [NVIDIA DGX Spark Documentation](https://docs.nvidia.com/dgx/)
- [Ollama Documentation](https://ollama.com/docs)
- [vLLM Documentation](https://docs.vllm.ai/)
- [TensorRT-LLM](https://github.com/NVIDIA/TensorRT-LLM)
