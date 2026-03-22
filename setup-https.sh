#!/bin/bash
# HTTPS Setup Script for OpenRouter Gateway
# Domain: models.rapidmvp.io

set -e

echo "🔒 OpenRouter Models HTTPS Setup"
echo "==================================="
echo ""

# Check if running on the DO server
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found. Make sure you're in the openrouter-gateway directory."
    exit 1
fi

# Prompt for email address
read -p "📧 Enter your email for Let's Encrypt notifications: " EMAIL

if [ -z "$EMAIL" ]; then
    echo "❌ Error: Email is required"
    exit 1
fi

echo ""
echo "Step 1: Stopping existing containers..."
docker compose down

echo ""
echo "Step 2: Creating directories..."
mkdir -p nginx/conf.d certbot/conf certbot/www

echo ""
echo "Step 3: Starting services (HTTP only for initial cert)..."
docker compose up -d gateway nginx

echo ""
echo "Step 4: Waiting for services to be ready..."
sleep 10

echo ""
echo "Step 5: Requesting SSL certificate from Let's Encrypt..."
docker compose run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email "$EMAIL" \
  --agree-tos \
  --no-eff-email \
  -d models.rapidmvp.io

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to obtain SSL certificate"
    echo "Please check:"
    echo "  - DNS is correctly pointing to this server"
    echo "  - Port 80 is accessible from the internet"
    echo "  - The domain is not rate-limited by Let's Encrypt"
    exit 1
fi

echo ""
echo "Step 6: Restarting nginx with SSL configuration..."
docker compose restart nginx

echo ""
echo "Step 7: Starting certbot auto-renewal..."
docker compose up -d certbot

echo ""
echo "✅ HTTPS setup complete!"
echo ""
echo "Testing endpoints:"
echo "  - Health: curl -I https://models.rapidmvp.io/health"
echo "  - API: curl -H 'X-Internal-API-Key: YOUR_KEY' https://models.rapidmvp.io/api/models"
echo ""
echo "🎉 Your OpenRouter Models API is now secured with HTTPS!"
echo "   - models.rapidmvp.io"
echo ""
echo "Certificate will auto-renew every 90 days."
