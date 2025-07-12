# Docker Deployment

ArBot supports containerized deployment using Docker, providing isolated, reproducible, and scalable deployment options. This guide covers Docker setup, configuration, orchestration, and best practices for production deployment.

## Overview

### Benefits of Docker Deployment

**Isolation & Consistency:**
- Consistent runtime environment across development and production
- Isolated dependencies and system requirements
- Eliminates "works on my machine" issues

**Scalability & Orchestration:**
- Easy horizontal scaling with container orchestration
- Load balancing and service discovery
- Rolling updates with zero downtime

**Resource Efficiency:**
- Lightweight containers compared to virtual machines
- Efficient resource utilization
- Fast startup and shutdown times

### Architecture Overview

```
┌───────────────────────┐
│      Load Balancer        │
│      (nginx/traefik)      │
└─────────┬─────────────┘
            │
  ┌─────────┼─────────┐
  │         │         │
┌─┼─────────┼─────────┼─┐
│ ArBot   │ ArBot   │ ArBot │
│ Instance│ Instance│ Instance│
└1        └2        └3      │
└─────────┼─────────┼───────┘
          │         │
  ┌───────┼─────────┐
  │     Database    │
  │    (PostgreSQL) │
  └─────────────────┘
```

## Docker Images

### Base Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd --create-home --shell /bin/bash app
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .
RUN chown -R app:app /app

# Switch to app user
USER app

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/api/v1/health || exit 1

# Default command
CMD ["python", "main.py"]
```

### Multi-stage Production Build

```dockerfile
# Dockerfile.prod
# Build stage
FROM python:3.11-slim as builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim as production

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/app/.local/bin:$PATH"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash app

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /root/.local /home/app/.local

# Copy application code
COPY --chown=app:app . .

# Switch to app user
USER app

# Create data directory
RUN mkdir -p /app/data /app/logs

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/api/v1/health || exit 1

CMD ["python", "main.py"]
```

### Development Dockerfile

```dockerfile
# Dockerfile.dev
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install development dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    sqlite3 \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r requirements-dev.txt

# Copy application code
COPY . .

# Create volumes for development
VOLUME ["/app/data", "/app/logs"]

EXPOSE 8080

# Development command with hot reload
CMD ["python", "-m", "arbot.main", "--dev"]
```

## Docker Compose

### Development Environment

```yaml
# docker-compose.yml
version: '3.8'

services:
  arbot:
    build:
      context: .
      dockerfile: Dockerfile.dev
    container_name: arbot-dev
    ports:
      - "8080:8080"
    volumes:
      - .:/app
      - arbot-data:/app/data
      - arbot-logs:/app/logs
    environment:
      - ARBOT_ENV=development
      - ARBOT_LOG_LEVEL=DEBUG
      - ARBOT_API_ENABLED=true
    env_file:
      - .env.dev
    depends_on:
      - redis
      - postgres
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    container_name: arbot-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    container_name: arbot-postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init.sql
    environment:
      - POSTGRES_DB=arbot
      - POSTGRES_USER=arbot
      - POSTGRES_PASSWORD=arbot_password
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    container_name: arbot-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - arbot
    restart: unless-stopped

volumes:
  arbot-data:
  arbot-logs:
  redis-data:
  postgres-data:

networks:
  default:
    name: arbot-network
```

### Production Environment

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  arbot:
    build:
      context: .
      dockerfile: Dockerfile.prod
    image: arbot:latest
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
      restart_policy:
        condition: on-failure
        delay: 10s
        max_attempts: 3
    ports:
      - "8080-8082:8080"
    volumes:
      - arbot-data:/app/data
      - arbot-logs:/app/logs
      - /etc/ssl/certs:/etc/ssl/certs:ro
    environment:
      - ARBOT_ENV=production
      - ARBOT_LOG_LEVEL=INFO
      - ARBOT_API_ENABLED=true
      - ARBOT_DATABASE_URL=postgresql://arbot:${POSTGRES_PASSWORD}@postgres:5432/arbot
      - ARBOT_REDIS_URL=redis://redis:6379/0
    env_file:
      - .env.prod
    depends_on:
      - postgres
      - redis
    networks:
      - arbot-network
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  postgres:
    image: postgres:15-alpine
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./backups:/backups
    environment:
      - POSTGRES_DB=arbot
      - POSTGRES_USER=arbot
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
    networks:
      - arbot-network
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    deploy:
      resources:
        limits:
          cpus: '0.25'
          memory: 256M
    networks:
      - arbot-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.prod.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - nginx-logs:/var/log/nginx
    depends_on:
      - arbot
    deploy:
      resources:
        limits:
          cpus: '0.25'
          memory: 128M
    networks:
      - arbot-network

  monitoring:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
    networks:
      - arbot-network

volumes:
  arbot-data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/arbot/data
  arbot-logs:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/arbot/logs
  postgres-data:
  redis-data:
  nginx-logs:
  prometheus-data:

networks:
  arbot-network:
    driver: bridge
```

## Configuration Management

### Environment Files

**.env.dev (Development):**
```bash
# Development environment variables
ARBOT_ENV=development
ARBOT_LOG_LEVEL=DEBUG
ARBOT_API_ENABLED=true
ARBOT_API_HOST=0.0.0.0
ARBOT_API_PORT=8080

# Database
ARBOT_DATABASE_URL=sqlite:///app/data/arbot.db

# Exchange API Keys (testnet)
BINANCE_API_KEY=your_testnet_key
BINANCE_API_SECRET=your_testnet_secret
BINANCE_TESTNET=true

BYBIT_API_KEY=your_testnet_key
BYBIT_API_SECRET=your_testnet_secret
BYBIT_TESTNET=true

# Trading Configuration
ARBOT_TRADING_MODE=simulation
ARBOT_MIN_PROFIT_THRESHOLD=0.001
ARBOT_MAX_POSITION_SIZE=100.0
```

**.env.prod (Production):**
```bash
# Production environment variables
ARBOT_ENV=production
ARBOT_LOG_LEVEL=INFO
ARBOT_API_ENABLED=true
ARBOT_API_HOST=0.0.0.0
ARBOT_API_PORT=8080

# Database
ARBOT_DATABASE_URL=postgresql://arbot:${POSTGRES_PASSWORD}@postgres:5432/arbot
POSTGRES_PASSWORD=secure_production_password

# Redis
ARBOT_REDIS_URL=redis://redis:6379/0

# Exchange API Keys (production)
BINANCE_API_KEY=${BINANCE_API_KEY}
BINANCE_API_SECRET=${BINANCE_API_SECRET}
BINANCE_TESTNET=false

BYBIT_API_KEY=${BYBIT_API_KEY}
BYBIT_API_SECRET=${BYBIT_API_SECRET}
BYBIT_TESTNET=false

# Trading Configuration
ARBOT_TRADING_MODE=live
ARBOT_MIN_PROFIT_THRESHOLD=0.005
ARBOT_MAX_POSITION_SIZE=1000.0

# Security
ARBOT_API_KEY=${ARBOT_API_KEY}
ARBOT_JWT_SECRET=${JWT_SECRET}
```

### Docker Secrets

```yaml
# docker-compose.secrets.yml
version: '3.8'

services:
  arbot:
    image: arbot:latest
    secrets:
      - binance_api_key
      - binance_api_secret
      - bybit_api_key
      - bybit_api_secret
      - postgres_password
    environment:
      - BINANCE_API_KEY_FILE=/run/secrets/binance_api_key
      - BINANCE_API_SECRET_FILE=/run/secrets/binance_api_secret
      - BYBIT_API_KEY_FILE=/run/secrets/bybit_api_key
      - BYBIT_API_SECRET_FILE=/run/secrets/bybit_api_secret
      - POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password

secrets:
  binance_api_key:
    file: ./secrets/binance_api_key.txt
  binance_api_secret:
    file: ./secrets/binance_api_secret.txt
  bybit_api_key:
    file: ./secrets/bybit_api_key.txt
  bybit_api_secret:
    file: ./secrets/bybit_api_secret.txt
  postgres_password:
    file: ./secrets/postgres_password.txt
```

## Nginx Configuration

### Load Balancer Configuration

```nginx
# nginx/nginx.prod.conf
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging format
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    # Performance optimizations
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 10240;
    gzip_proxied expired no-cache no-store private must-revalidate;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=web:10m rate=1r/s;

    # Upstream for ArBot instances
    upstream arbot_backend {
        least_conn;
        server arbot_1:8080 max_fails=3 fail_timeout=30s;
        server arbot_2:8080 max_fails=3 fail_timeout=30s;
        server arbot_3:8080 max_fails=3 fail_timeout=30s;
        
        # Health check
        health_check uri=/api/v1/health;
    }

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # HTTPS server
    server {
        listen 443 ssl http2;
        server_name arbot.yourdomain.com;

        ssl_certificate /etc/nginx/ssl/arbot.crt;
        ssl_certificate_key /etc/nginx/ssl/arbot.key;

        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";

        # API endpoints
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            
            proxy_pass http://arbot_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # WebSocket support
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            
            # Timeouts
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # Health check endpoint
        location /health {
            access_log off;
            proxy_pass http://arbot_backend/api/v1/health;
        }

        # Static files (if any)
        location /static/ {
            alias /app/static/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # HTTP to HTTPS redirect
    server {
        listen 80;
        server_name arbot.yourdomain.com;
        return 301 https://$server_name$request_uri;
    }
}
```

## Orchestration with Docker Swarm

### Docker Swarm Stack

```yaml
# docker-stack.yml
version: '3.8'

services:
  arbot:
    image: arbot:latest
    deploy:
      replicas: 3
      placement:
        constraints:
          - node.role == worker
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
      restart_policy:
        condition: on-failure
        delay: 10s
        max_attempts: 3
      update_config:
        parallelism: 1
        delay: 30s
        failure_action: rollback
        order: start-first
      rollback_config:
        parallelism: 1
        delay: 30s
    networks:
      - arbot-network
    volumes:
      - arbot-data:/app/data
    environment:
      - ARBOT_ENV=production
    secrets:
      - binance_api_key
      - binance_api_secret
      - postgres_password
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    deploy:
      placement:
        constraints:
          - node.role == manager
      resources:
        limits:
          cpus: '0.25'
          memory: 128M
    volumes:
      - nginx-config:/etc/nginx:ro
      - nginx-ssl:/etc/nginx/ssl:ro
    networks:
      - arbot-network
    depends_on:
      - arbot

  postgres:
    image: postgres:15-alpine
    deploy:
      placement:
        constraints:
          - node.labels.postgres == true
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
    volumes:
      - postgres-data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=arbot
      - POSTGRES_USER=arbot
    secrets:
      - postgres_password
    networks:
      - arbot-network

networks:
  arbot-network:
    driver: overlay
    attachable: true

volumes:
  arbot-data:
    driver: local
  postgres-data:
    driver: local
  nginx-config:
    driver: local
  nginx-ssl:
    driver: local

secrets:
  binance_api_key:
    external: true
  binance_api_secret:
    external: true
  postgres_password:
    external: true
```

### Deployment Commands

```bash
# Initialize Docker Swarm
docker swarm init

# Add worker nodes
docker swarm join-token worker

# Create secrets
echo "your_binance_api_key" | docker secret create binance_api_key -
echo "your_binance_secret" | docker secret create binance_api_secret -
echo "secure_postgres_password" | docker secret create postgres_password -

# Deploy stack
docker stack deploy -c docker-stack.yml arbot

# Check services
docker service ls
docker service ps arbot_arbot

# Scale services
docker service scale arbot_arbot=5

# Update service
docker service update --image arbot:v2.0.0 arbot_arbot

# Remove stack
docker stack rm arbot
```

## Kubernetes Deployment

### Kubernetes Manifests

```yaml
# k8s/namespace.yml
apiVersion: v1
kind: Namespace
metadata:
  name: arbot
---
# k8s/configmap.yml
apiVersion: v1
kind: ConfigMap
metadata:
  name: arbot-config
  namespace: arbot
data:
  ARBOT_ENV: "production"
  ARBOT_LOG_LEVEL: "INFO"
  ARBOT_API_ENABLED: "true"
  ARBOT_API_HOST: "0.0.0.0"
  ARBOT_API_PORT: "8080"
  ARBOT_TRADING_MODE: "live"
---
# k8s/secret.yml
apiVersion: v1
kind: Secret
metadata:
  name: arbot-secrets
  namespace: arbot
type: Opaque
data:
  BINANCE_API_KEY: <base64-encoded-key>
  BINANCE_API_SECRET: <base64-encoded-secret>
  BYBIT_API_KEY: <base64-encoded-key>
  BYBIT_API_SECRET: <base64-encoded-secret>
---
# k8s/deployment.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: arbot
  namespace: arbot
  labels:
    app: arbot
spec:
  replicas: 3
  selector:
    matchLabels:
      app: arbot
  template:
    metadata:
      labels:
        app: arbot
    spec:
      containers:
      - name: arbot
        image: arbot:latest
        ports:
        - containerPort: 8080
        envFrom:
        - configMapRef:
            name: arbot-config
        - secretRef:
            name: arbot-secrets
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 8080
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /api/v1/health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        volumeMounts:
        - name: data-volume
          mountPath: /app/data
      volumes:
      - name: data-volume
        persistentVolumeClaim:
          claimName: arbot-data-pvc
---
# k8s/service.yml
apiVersion: v1
kind: Service
metadata:
  name: arbot-service
  namespace: arbot
spec:
  selector:
    app: arbot
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
  type: ClusterIP
---
# k8s/ingress.yml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: arbot-ingress
  namespace: arbot
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - arbot.yourdomain.com
    secretName: arbot-tls
  rules:
  - host: arbot.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: arbot-service
            port:
              number: 80
```

## Monitoring and Logging

### Prometheus Configuration

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'arbot'
    static_configs:
      - targets: ['arbot:8080']
    metrics_path: '/api/v1/metrics'
    scrape_interval: 30s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx:80']
```

### Logging Configuration

```yaml
# docker-compose.logging.yml
version: '3.8'

services:
  arbot:
    logging:
      driver: "fluentd"
      options:
        fluentd-address: "localhost:24224"
        tag: "arbot.{{.ContainerName}}"
        fluentd-async-connect: "true"

  fluentd:
    image: fluent/fluentd:v1.14-debian
    container_name: fluentd
    volumes:
      - ./logging/fluentd.conf:/fluentd/etc/fluent.conf:ro
      - ./logs:/var/log
    ports:
      - "24224:24224"
    environment:
      - FLUENTD_CONF=fluent.conf
```

## Best Practices

### Security

1. **Use Non-Root User**
   ```dockerfile
   RUN useradd --create-home --shell /bin/bash app
   USER app
   ```

2. **Minimal Base Images**
   ```dockerfile
   FROM python:3.11-slim  # Use slim variants
   # or
   FROM python:3.11-alpine  # Even smaller
   ```

3. **Secrets Management**
   ```bash
   # Use Docker secrets or external secret management
   docker secret create api_key /path/to/key/file
   ```

4. **Network Isolation**
   ```yaml
   networks:
     frontend:
       driver: bridge
     backend:
       driver: bridge
       internal: true  # No external access
   ```

### Performance

1. **Multi-stage Builds**
   - Reduce final image size
   - Separate build and runtime dependencies

2. **Layer Caching**
   ```dockerfile
   # Copy requirements first for better caching
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   # Then copy application code
   COPY . .
   ```

3. **Resource Limits**
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '1.0'
         memory: 1G
   ```

### Maintenance

1. **Health Checks**
   ```dockerfile
   HEALTHCHECK --interval=30s --timeout=10s \
     CMD curl -f http://localhost:8080/health || exit 1
   ```

2. **Graceful Shutdown**
   ```python
   # Handle SIGTERM for graceful shutdown
   import signal
   import sys
   
   def signal_handler(sig, frame):
       print('Graceful shutdown initiated...')
       # Clean up resources
       sys.exit(0)
   
   signal.signal(signal.SIGTERM, signal_handler)
   ```

3. **Log Management**
   ```yaml
   logging:
     driver: "json-file"
     options:
       max-size: "10m"
       max-file: "3"
   ```

## Deployment Scripts

### Build and Deploy Script

```bash
#!/bin/bash
# scripts/deploy.sh

set -e

# Configuration
IMAGE_NAME="arbot"
IMAGE_TAG="latest"
CONTAINER_REGISTRY="your-registry.com"
ENVIRONMENT="${1:-production}"

echo "Building ArBot Docker image..."
docker build -f Dockerfile.prod -t $IMAGE_NAME:$IMAGE_TAG .

echo "Tagging image for registry..."
docker tag $IMAGE_NAME:$IMAGE_TAG $CONTAINER_REGISTRY/$IMAGE_NAME:$IMAGE_TAG

echo "Pushing image to registry..."
docker push $CONTAINER_REGISTRY/$IMAGE_NAME:$IMAGE_TAG

echo "Deploying to $ENVIRONMENT environment..."
if [ "$ENVIRONMENT" = "production" ]; then
    docker stack deploy -c docker-stack.yml arbot
else
    docker-compose -f docker-compose.yml -f docker-compose.$ENVIRONMENT.yml up -d
fi

echo "Deployment completed successfully!"
```

### Backup Script

```bash
#!/bin/bash
# scripts/backup.sh

set -e

BACKUP_DIR="/opt/arbot/backups"
DATE=$(date +%Y%m%d_%H%M%S)

echo "Creating backup directory..."
mkdir -p $BACKUP_DIR

echo "Backing up database..."
docker exec arbot_postgres pg_dump -U arbot arbot > $BACKUP_DIR/arbot_db_$DATE.sql

echo "Backing up application data..."
docker run --rm -v arbot_data:/data -v $BACKUP_DIR:/backup alpine \
    tar czf /backup/arbot_data_$DATE.tar.gz -C /data .

echo "Cleaning old backups (keeping last 7 days)..."
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR"
```

!!! tip "Image Optimization"
    Use multi-stage builds and .dockerignore files to create smaller, more secure images. Consider using distroless or alpine base images for production.

!!! warning "Resource Management"
    Always set resource limits in production to prevent containers from consuming all available system resources. Monitor resource usage regularly.

!!! note "High Availability"
    For production deployments, run multiple replicas across different nodes and implement proper health checks and rolling updates for zero-downtime deployments.