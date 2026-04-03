# Qwen CLI OpenAI-Compatible API

An OpenAI-compatible API wrapper for Qwen CLI that allows you to use Qwen Coder with any LLM client (AnythingLLM, Open WebUI, etc.).

## Features

- ✅ OpenAI-compatible `/v1/chat/completions` endpoint
- ✅ Streaming support
- ✅ Model listing via `/v1/models`
- ✅ Optional API key authentication
- ✅ Docker-ready for Coolify deployment
- ✅ Cloudflare Tunnel ready

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Qwen CLI installed and configured
- Docker (for containerized deployment)

### 2. Local Setup

```bash
# Clone/copy this project
cd "Remote Qwen CLI + API"

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your settings

# Run the server
python main.py
```

The API will be available at `http://localhost:8000`

### 3. Docker Setup

```bash
# Copy and configure environment
cp .env.example .env

# Build and run with Docker Compose
docker-compose up -d

# Or build and run manually
docker build -t qwen-openai-api .
docker run -d -p 8000:8000 --env-file .env qwen-openai-api
```

## API Endpoints

### Health Check
```
GET /health
```

### List Models
```
GET /v1/models
Authorization: Bearer YOUR_API_KEY
```

### Chat Completions
```
POST /v1/chat/completions
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json

{
  "model": "qwen2.5-coder",
  "messages": [
    {"role": "system", "content": "You are a helpful coding assistant."},
    {"role": "user", "content": "Write a Python function to calculate fibonacci"}
  ],
  "temperature": 0.7,
  "max_tokens": 4096,
  "stream": false
}
```

### Streaming Chat Completions
```
POST /v1/chat/completions
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json

{
  "model": "qwen2.5-coder",
  "messages": [...],
  "stream": true
}
```

## Configuration

All configuration is done via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8000` |
| `QWEN_MODEL` | Qwen model to use | `qwen2.5-coder` |
| `QWEN_CLI_PATH` | Path to qwen-cli executable | `qwen` |
| `QWEN_TIMEOUT` | Max execution time (seconds) | `300` |
| `API_KEY` | API key for authentication (optional) | - |
| `MAX_TOKENS` | Default max tokens | `4096` |
| `TEMPERATURE` | Default temperature | `0.7` |

## Using with AnythingLLM / Other LLM Clients

### AnythingLLM Configuration

1. Go to Settings → LLM Providers
2. Select "OpenAI Compatible"
3. Set the following:
   - **Base URL**: `http://your-server:8000/v1`
   - **API Key**: Your configured API key (or leave empty if not set)
   - **Model**: `qwen2.5-coder`
4. Save and test

### Open WebUI Configuration

1. Go to Settings → Admin Settings → Connections
2. Add OpenAI-compatible endpoint:
   - **URL**: `http://your-server:8000/v1`
   - **API Key**: Your configured API key
3. Save and refresh

## Cloudflare Tunnel Setup

To expose the API to the internet securely:

### 1. Install Cloudflared

```bash
# Ubuntu/Debian
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt update && sudo apt install cloudflared
```

### 2. Create Tunnel

```bash
# Login to Cloudflare
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create qwen-api

# Configure tunnel
cat > ~/.cloudflared/config.yml << EOF
tunnel: qwen-api
credentials-file: /root/.cloudflared/YOUR_TUNNEL_ID.json

ingress:
  - hostname: qwen-api.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404
EOF

# Route DNS
cloudflared tunnel route dns qwen-api qwen-api.yourdomain.com
```

### 3. Run Tunnel

```bash
cloudflared tunnel run qwen-api
```

Or run as a service:
```bash
cloudflared service install
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

## Coolify Deployment

### 1. Push to Git Repository

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin your-repo-url
git push -u origin main
```

### 2. Deploy on Coolify

1. Go to your Coolify dashboard
2. Click "New Resource" → "Git Repository"
3. Select your repository
4. Coolify will auto-detect Docker Compose
5. Configure environment variables from `.env.example`
6. Deploy!

### 3. Alternative: Docker Image Deployment

```bash
# Build and push to registry
docker build -t your-registry/qwen-openai-api:latest .
docker push your-registry/qwen-openai-api:latest

# On Coolify, use "Docker Image" resource
# Image: your-registry/qwen-openai-api:latest
# Port: 8000
```

## Testing the API

### Using curl

```bash
# Health check
curl http://localhost:8000/health

# List models
curl http://localhost:8000/v1/models \
  -H "Authorization: Bearer your-api-key"

# Chat completion
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "qwen2.5-coder",
    "messages": [
      {"role": "user", "content": "Write a hello world in Python"}
    ]
  }'

# Streaming
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "qwen2.5-coder",
    "messages": [
      {"role": "user", "content": "Explain async/await"}
    ],
    "stream": true
  }'
```

### Using Python

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="your-api-key"  # or empty if not configured
)

response = client.chat.completions.create(
    model="qwen2.5-coder",
    messages=[
        {"role": "user", "content": "Write a function to reverse a string"}
    ]
)

print(response.choices[0].message.content)
```

## Troubleshooting

### Qwen CLI not found
- Ensure Qwen CLI is installed and in PATH
- Update `QWEN_CLI_PATH` in `.env` to the full path

### Timeout errors
- Increase `QWEN_TIMEOUT` value (default: 300s)
- Check system resources (RAM/CPU)

### API not accessible externally
- Verify firewall rules
- Check Cloudflare tunnel status
- Ensure `HOST=0.0.0.0` in configuration

### Authentication errors
- Verify API key matches exactly
- Check Authorization header format: `Bearer YOUR_API_KEY`
- Leave `API_KEY` empty to disable authentication

## Project Structure

```
Remote Qwen CLI + API/
├── main.py              # FastAPI application
├── schemas.py           # Pydantic models
├── qwen_client.py       # Qwen CLI client
├── config.py            # Configuration management
├── requirements.txt     # Python dependencies
├── Dockerfile           # Docker image
├── docker-compose.yml   # Docker Compose config
├── .env.example         # Environment template
└── .dockerignore        # Docker ignore rules
```

## License

MIT
