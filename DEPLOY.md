# Deployment Guide — Store Intelligence

This guide covers multiple deployment options for the Store Intelligence application.

---

## Quick Deploy (Docker Compose) — RECOMMENDED

### Prerequisites
- Docker Desktop installed
- At least 4GB RAM available
- Ports 8000 and 8501 available

### Steps

```bash
# 1. Clone/Navigate to project
cd c:\purplle

# 2. Build and start all services
docker compose up --build -d

# 3. Verify services are running
docker compose ps

# 4. Access the application
# API: http://localhost:8000/docs
# Dashboard: http://localhost:8501
```

### Load Sample Data

```bash
# Run detection pipeline to generate events
docker compose exec api python pipeline/run.py --videos dataset/videos --store STORE_001 --api http://localhost:8000

# OR load from existing events file
docker compose exec api python load_events.py
```

### Management Commands

```bash
# View logs
docker compose logs -f

# Stop services
docker compose down

# Restart services
docker compose restart

# Remove everything including volumes
docker compose down -v
```

---

## Local Development Deploy

### Prerequisites
- Python 3.11+
- pip

### Steps

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start API (Terminal 1)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 3. Start Dashboard (Terminal 2)
streamlit run dashboard/app.py

# 4. Run detection pipeline (Terminal 3)
python pipeline/run.py --videos dataset/videos --store STORE_001 --api http://localhost:8000
```

Access:
- API: http://localhost:8000/docs
- Dashboard: http://localhost:8501

---

## Cloud Deployment Options

### Option 1: AWS EC2

```bash
# SSH into EC2 instance
ssh -i your-key.pem ec2-user@your-instance-ip

# Install Docker
sudo yum update -y
sudo yum install docker -y
sudo service docker start
sudo usermod -a -G docker ec2-user

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Clone repository
git clone <your-repo-url>
cd store-intelligence

# Deploy
docker-compose up -d

# Configure security group to allow:
# - Port 8000 (API)
# - Port 8501 (Dashboard)
```

### Option 2: AWS Elastic Beanstalk

```bash
# Install EB CLI
pip install awsebcli

# Initialize EB application
eb init -p docker store-intelligence --region us-east-1

# Create environment and deploy
eb create store-intelligence-prod

# Open application
eb open
```

### Option 3: Heroku

```bash
# Install Heroku CLI
# Create heroku.yml file (already provided)

# Login and create app
heroku login
heroku create store-intelligence-app

# Set stack to container
heroku stack:set container

# Deploy
git push heroku main

# Open app
heroku open
```

### Option 4: Google Cloud Run

```bash
# Build and push API container
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/store-api

# Deploy API
gcloud run deploy store-api \
  --image gcr.io/YOUR_PROJECT_ID/store-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated

# Build and push Dashboard container
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/store-dashboard -f Dockerfile.dashboard

# Deploy Dashboard
gcloud run deploy store-dashboard \
  --image gcr.io/YOUR_PROJECT_ID/store-dashboard \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars API_URL=https://store-api-xxx.run.app
```

---

## Production Considerations

### Environment Variables

Create `.env` file:

```bash
# API Configuration
DB_PATH=/app/data/store.db
API_HOST=0.0.0.0
API_PORT=8000

# Dashboard Configuration
API_URL=http://localhost:8000

# Security
API_KEY=your-secret-key-here
ALLOWED_ORIGINS=https://yourdomain.com
```

### Update docker-compose.yml for production:

```yaml
services:
  api:
    env_file: .env
    environment:
      - API_KEY=${API_KEY}
    # Add nginx reverse proxy
  
  dashboard:
    env_file: .env
```

### Database Persistence

For production, use PostgreSQL instead of SQLite:

```bash
# Add to docker-compose.yml
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: store_intelligence
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Monitoring & Logging

```bash
# Add Prometheus metrics
pip install prometheus-fastapi-instrumentator

# Add logging service
  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
```

### SSL/HTTPS

Use nginx as reverse proxy:

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com;
    
    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;
    
    location /api {
        proxy_pass http://localhost:8000;
    }
    
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## Health Checks

### API Health
```bash
curl http://localhost:8000/health
```

### Dashboard Health
```bash
curl http://localhost:8501/_stcore/health
```

---

## Troubleshooting

### Port Already in Use
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:8000 | xargs kill -9
```

### Container Issues
```bash
# View logs
docker compose logs api
docker compose logs dashboard

# Restart specific service
docker compose restart api

# Rebuild from scratch
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Database Lock Issues
```bash
# Remove existing database
rm data/store.db
docker compose restart api
```

---

## Scaling

### Horizontal Scaling with Docker Swarm

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml store_intelligence

# Scale API service
docker service scale store_intelligence_api=3
```

### Load Balancer Configuration

```yaml
# nginx.conf
upstream api_backend {
    server api1:8000;
    server api2:8000;
    server api3:8000;
}

server {
    location /api {
        proxy_pass http://api_backend;
    }
}
```

---

## Backup & Recovery

```bash
# Backup database
docker compose exec api tar -czf /app/data/backup-$(date +%Y%m%d).tar.gz /app/data/store.db

# Copy backup to host
docker cp store_intelligence_api:/app/data/backup-20240101.tar.gz ./backups/

# Restore from backup
docker cp ./backups/backup-20240101.tar.gz store_intelligence_api:/app/data/
docker compose exec api tar -xzf /app/data/backup-20240101.tar.gz
```

---

## Support

For issues or questions:
- Check logs: `docker compose logs -f`
- Review API docs: http://localhost:8000/docs
- Check system health: http://localhost:8000/health
