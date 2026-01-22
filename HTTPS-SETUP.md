# HTTPS Setup for usageflows.info

Quick guide to enable HTTPS for your OpenRouter Gateway.

## Prerequisites

✅ DNS records configured (already done):
- `usageflows.info` → `134.209.184.66`
- `www.usageflows.info` → `134.209.184.66`
- `api.usageflows.info` → `134.209.184.66`

## Quick Setup (Recommended)

### On your DO server (134.209.184.66):

```bash
# 1. Navigate to project directory
cd /root/openrouter-gateway

# 2. Pull latest code
git pull origin main

# 3. Make setup script executable
chmod +x setup-https.sh

# 4. Run the setup script
./setup-https.sh

# Follow the prompts - you'll need to enter your email address
```

The script will:
1. Stop existing containers
2. Create necessary directories
3. Start services
4. Request SSL certificate from Let's Encrypt
5. Configure nginx with HTTPS
6. Set up auto-renewal

## Manual Setup (Alternative)

If you prefer manual setup:

### 1. Pull Latest Code
```bash
cd /root/openrouter-gateway
git pull origin main
```

### 2. Create Directories
```bash
mkdir -p nginx/conf.d certbot/conf certbot/www
```

### 3. Configure Firewall
```bash
ufw allow 80/tcp
ufw allow 443/tcp
ufw reload
```

### 4. Start Services
```bash
docker compose down
docker compose up -d gateway nginx
```

### 5. Request Certificate
```bash
docker compose run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email your-email@example.com \
  --agree-tos \
  --no-eff-email \
  -d usageflows.info \
  -d www.usageflows.info \
  -d api.usageflows.info
```

### 6. Restart Nginx
```bash
docker compose restart nginx
docker compose up -d certbot
```

## Testing

### Test HTTP to HTTPS Redirect
```bash
curl -I http://usageflows.info/health
# Should return: 301 Moved Permanently
```

### Test HTTPS Health Endpoint
```bash
curl -I https://usageflows.info/health
# Should return: 200 OK
```

### Test API with HTTPS
```bash
curl -H "X-Internal-API-Key: YOUR_KEY" \
  https://usageflows.info/api/models
```

### Test All Domains
```bash
# Main domain
curl -I https://usageflows.info/health

# WWW subdomain
curl -I https://www.usageflows.info/health

# API subdomain
curl -I https://api.usageflows.info/health
```

## Update Frontend

Update your frontend `.env` file:

```bash
# Old
VITE_API_BASE_URL=http://134.209.184.66:8000

# New (choose one)
VITE_API_BASE_URL=https://usageflows.info
# or
VITE_API_BASE_URL=https://api.usageflows.info
```

## Certificate Management

### Check Certificate Status
```bash
docker compose run --rm certbot certificates
```

### Manual Renewal (if needed)
```bash
docker compose run --rm certbot renew
docker compose restart nginx
```

### View Certificate Expiry
```bash
echo | openssl s_client -servername usageflows.info -connect usageflows.info:443 2>/dev/null | openssl x509 -noout -dates
```

## Monitoring

### View Nginx Logs
```bash
docker compose logs -f nginx
```

### View All Service Logs
```bash
docker compose logs -f
```

### Check Service Status
```bash
docker compose ps
```

## Troubleshooting

### Certificate Request Fails

**Check DNS:**
```bash
nslookup usageflows.info
dig usageflows.info +short
```

**Check Port 80 is accessible:**
```bash
curl -I http://usageflows.info/.well-known/acme-challenge/test
```

**Check firewall:**
```bash
ufw status
```

### Nginx Won't Start

**Check configuration:**
```bash
docker compose exec nginx nginx -t
```

**View error logs:**
```bash
docker compose logs nginx
```

### HTTP Still Accessible on Port 8000

This is expected during initial setup. Once HTTPS is working, you can optionally close port 8000:

```bash
ufw delete allow 8000/tcp
ufw reload
```

## Rollback

If you need to revert to HTTP-only:

```bash
cd /root/openrouter-gateway
git checkout HEAD~1 docker-compose.yml
docker compose down
docker compose up -d
```

## Security Features

- ✅ TLS 1.2 and 1.3 only
- ✅ Strong cipher suites
- ✅ HSTS enabled (forces HTTPS)
- ✅ Security headers configured
- ✅ CORS headers preserved
- ✅ 90-day certificate with auto-renewal

## Support

For issues, check:
1. Docker logs: `docker compose logs`
2. Nginx configuration: `nginx/conf.d/usageflows.conf`
3. Certificate status: `docker compose run --rm certbot certificates`

---

**Need help?** Check the main [README.md](README.md) or [DEPLOYMENT.md](DEPLOYMENT.md)
