# Phase 5: Deployment Guide

## Overview
This guide covers deploying CropAI Backend and Frontend to production.

## Backend Deployment (Django + Gunicorn + Nginx)

### Prerequisites
- Ubuntu 20.04+ or similar Linux distribution
- PostgreSQL 12+
- Python 3.10+
- nginx
- SSL certificate (Let's Encrypt)

### 1. Server Setup

```bash
# Create app user
sudo useradd -m -s /bin/bash cropai
sudo usermod -aG sudo cropai

# Create directories
sudo mkdir -p /var/www/cropai-backend
sudo mkdir -p /var/log/cropai
sudo mkdir -p /var/run/cropai
sudo chown -R cropai:cropai /var/www/cropai-backend /var/log/cropai /var/run/cropai
```

### 2. Clone and Setup Repository

```bash
cd /var/www/cropai-backend
git clone <repository-url> .
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn psycopg2-binary

# Create .env.production from .env.production.example
cp .env.production.example .env.production
# Edit .env.production with production values
```

### 3. Database Migration

```bash
source venv/bin/activate
export $(cat .env.production | xargs)
python manage.py collectstatic --noinput
python manage.py migrate
```

### 4. Setup Systemd Service

```bash
# Copy service file
sudo cp cropai/cropai-backend.service /etc/systemd/system/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable cropai-backend
sudo systemctl start cropai-backend
sudo systemctl status cropai-backend
```

### 5. Configure Nginx

```bash
# Copy nginx config
sudo cp nginx_config.conf /etc/nginx/sites-available/cropai

# Enable site
sudo ln -s /etc/nginx/sites-available/cropai /etc/nginx/sites-enabled/

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

### 6. Setup SSL with Let's Encrypt

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot certonly --nginx -d api.cropai.example.com -d cropai.example.com

# Auto-renewal is handled by systemd timer
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

### 7. Setup PostgreSQL

```bash
sudo -u postgres createdb cropai_db
sudo -u postgres createuser cropai_user
sudo -u postgres psql -c "ALTER USER cropai_user WITH PASSWORD 'secure-password';"
sudo -u postgres psql -c "ALTER ROLE cropai_user SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE cropai_db TO cropai_user;"
```

### 8. Monitoring Logs

```bash
# Backend logs
tail -f /var/log/cropai/access.log
tail -f /var/log/cropai/error.log

# System logs
sudo journalctl -u cropai-backend -f
sudo journalctl -u nginx -f
```

## Frontend Deployment (Next.js on Vercel)

### 1. Setup Vercel Project

```bash
cd cropai-frontend

# Install Vercel CLI
npm install -g vercel

# Deploy
vercel --prod
```

### 2. Configure Environment Variables in Vercel Dashboard

- Go to Settings → Environment Variables
- Add `NEXT_PUBLIC_API_URL=https://api.cropai.example.com`

### 3. Configure Custom Domain

- Go to Settings → Domains
- Add custom domain (e.g., cropai.example.com)
- Update DNS records with Vercel's nameservers

### 4. Enable Auto-Deployment

- Connect GitHub repository
- Enable automatic deployments on push to main branch

## Verification Steps

### Backend
```bash
# Check health
curl -H "Authorization: Bearer <token>" https://api.cropai.example.com/api/v1/auth/current-user/

# Check CORS
curl -H "Origin: https://cropai.example.com" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: Content-Type" \
     -X OPTIONS https://api.cropai.example.com/api/v1/predictions/
```

### Frontend
- Visit https://cropai.example.com
- Test login flow
- Create a prediction
- Verify API integration

## Security Checklist

- [x] DEBUG=False in production settings
- [x] SECRET_KEY is secure and unique
- [x] Database password is strong
- [x] SSL/TLS is enabled
- [x] CORS is restricted to allowed origins
- [x] JWT tokens are httpOnly
- [x] CSRF protection is enabled
- [x] Security headers are set (HSTS, CSP, etc.)
- [x] Database backups are configured
- [x] Logs are monitored
- [x] Rate limiting is considered

## Troubleshooting

### 502 Bad Gateway
```bash
# Check if gunicorn is running
sudo systemctl status cropai-backend

# Check if port 8000 is listening
sudo ss -tlnp | grep 8000

# Check logs
tail -50 /var/log/cropai/error.log
```

### CORS Errors
- Verify CORS_ALLOWED_ORIGINS in .env.production
- Check Nginx proxy headers are set correctly
- Ensure preflight requests are allowed

### SSL Certificate Issues
```bash
# Check certificate status
sudo certbot certificates

# Renew certificate
sudo certbot renew
```

## Rollback Procedure

```bash
# If deployment fails, rollback to previous version
cd /var/www/cropai-backend
git log --oneline
git checkout <previous-commit>

# Restart service
sudo systemctl restart cropai-backend
```

## Backup Strategy

### Database Backup
```bash
# Daily backup script
#!/bin/bash
BACKUP_DIR="/backups/cropai"
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -U cropai_user cropai_db | gzip > $BACKUP_DIR/cropai_db_$DATE.sql.gz
```

### File Backup
- Regular snapshots of /var/www/cropai-backend
- Store in S3 or backup service

## Maintenance

### Regular Tasks
- Monitor disk space
- Check database size
- Review logs for errors
- Update dependencies monthly
- Test backup restoration

### Version Updates
```bash
# Update requirements
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt --upgrade
python manage.py migrate
sudo systemctl restart cropai-backend
```
