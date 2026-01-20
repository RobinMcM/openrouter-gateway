# OpenRouter Gateway - Deployment Guide

Quick deployment guide for DigitalOcean using Docker Compose.

## Prerequisites
- DigitalOcean Droplet with Docker installed
- Git installed
- OpenRouter API account and key

---

## 🚀 Quick Start Deployment

### 1. Clone Repository
```bash
cd /root
git clone https://github.com/RobinMcM/openrouter-gateway.git
cd openrouter-gateway
```

### 2. Generate Internal API Key
```bash
# Generate a secure 64-character key
INTERNAL_KEY=$(openssl rand -hex 32)
echo "Your Internal API Key: $INTERNAL_KEY"
echo "Save this key securely!"
```

### 3. Create Environment File
```bash
# Copy the example env file
cp .env.example .env

# Edit with your keys
nano .env
```

Add your keys:
```bash
INTERNAL_API_KEY=your-generated-key-from-step-2
OPENROUTER_API_KEY=placeholder  # Will be configured via web UI
```

### 4. Start the Service
```bash
# Build and start with docker compose
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

### 5. Configure OpenRouter API Key

1. Get your OpenRouter key from https://openrouter.ai/keys
2. Visit: `http://YOUR_DROPLET_IP:8000/config`
3. Enter your Internal API Key when prompted
4. Paste your OpenRouter API Key
5. Click "Test Key" to verify
6. Click "Save Key" to persist

---

## 🔄 Update to Latest Version

```bash
cd /root/openrouter-gateway

# Pull latest code
git pull origin main

# Rebuild and restart
docker compose down
docker compose up -d --build

# Configuration persists across updates
```

---

## 📍 Access Points

- **Health Check**: `http://YOUR_IP:8000/health`
- **Models Page**: `http://YOUR_IP:8000/models`
- **Config Page**: `http://YOUR_IP:8000/config`
- **API Instructions**: `http://YOUR_IP:8000/api/instructions` (requires auth)

---

## 🛠️ Management Commands

### View Logs
```bash
docker compose logs -f gateway
```

### Restart Service
```bash
docker compose restart
```

### Stop Service
```bash
docker compose down
```

### Check Status
```bash
docker compose ps
docker compose logs gateway --tail 50
```

### View Configuration
```bash
# Check if OpenRouter key is saved
docker compose exec gateway ls -la /app/config/
```

---

## 🔒 Security

- Internal API Key: Stored in `.env` (never commit to git)
- OpenRouter API Key: Stored in `/app/config/openrouter.key` (write-only)
- Config volume persists across container restarts
- All API endpoints require authentication except `/health`

---

## 📊 Test the API

```bash
# Replace with your Internal API Key
export INTERNAL_KEY="your-key-here"

# Check configuration status
curl -H "X-Internal-API-Key: $INTERNAL_KEY" \
  http://localhost:8000/api/config/openrouter-key/status

# List available models
curl -H "X-Internal-API-Key: $INTERNAL_KEY" \
  http://localhost:8000/api/models
```

---

## 🐛 Troubleshooting

### Container won't start
```bash
# Check logs
docker compose logs gateway

# Verify environment file
cat .env

# Ensure Internal API Key is set
docker compose exec gateway env | grep INTERNAL_API_KEY
```

### Can't access web pages
```bash
# Check if port 8000 is open
curl http://localhost:8000/health

# Check firewall
ufw status
ufw allow 8000/tcp
```

### Configuration not persisting
```bash
# Check volume exists
docker volume ls | grep openrouter-config

# Inspect volume
docker volume inspect openrouter_openrouter-config
```

---

## 📦 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `INTERNAL_API_KEY` | Yes | - | Gateway authentication key |
| `OPENROUTER_API_KEY` | No | placeholder | Can be set via UI |
| `OPENROUTER_BASE_URL` | No | https://openrouter.ai/api/v1 | OpenRouter API base URL |
| `ADMIN_MARKUP_PERCENT` | No | 0.10 | Admin fee percentage |
| `ADMIN_FIXED_FEE` | No | 0.001 | Admin fixed fee |

---

For more details, see [README.md](README.md)
