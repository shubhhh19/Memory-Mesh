# Production Deployment Guide

This guide covers deploying MemoryMesh to production environments.

## Prerequisites

- PostgreSQL 14+ with pgvector extension
- Redis (for rate limiting and caching)
- Python 3.11+
- Node.js 18+ (for frontend)
- Docker & Docker Compose (optional but recommended)

## Environment Variables

### Required Variables

```bash
# Database
MEMORY_DATABASE_URL=postgresql+asyncpg://user:password@host:5432/memorymesh

# JWT Authentication (CRITICAL - Generate a secure random key)
JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# CORS (specify exact origins, not wildcard)
MEMORY_ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Environment
MEMORY_ENVIRONMENT=production
```

### Optional but Recommended

```bash
# Redis
MEMORY_REDIS_URL=redis://localhost:6379/0

# Embedding Provider
MEMORY_EMBEDDING_PROVIDER=google_gemini
MEMORY_GEMINI_API_KEY=your-key-here

# Rate Limiting
MEMORY_GLOBAL_RATE_LIMIT=1000/hour
MEMORY_TENANT_RATE_LIMIT=500/hour

# Distributed Tracing
JAEGER_ENDPOINT=jaeger:6831
```

## Database Setup

1. **Create PostgreSQL database:**
```bash
createdb memorymesh
```

2. **Enable pgvector extension:**
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

3. **Run migrations:**
```bash
alembic upgrade head
```

## Docker Deployment

### Backend

```dockerfile
# Use the existing Dockerfile
docker build -t memorymesh-api .
docker run -d \
  -p 8000:8000 \
  -e MEMORY_DATABASE_URL=postgresql+asyncpg://... \
  -e JWT_SECRET_KEY=... \
  -e MEMORY_ALLOWED_ORIGINS=https://yourdomain.com \
  memorymesh-api
```

### Frontend

```bash
cd frontend
npm run build
npm start
```

Or with Docker:
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

## Docker Compose (Full Stack)

```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_DB: memorymesh
      POSTGRES_USER: memorymesh
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  api:
    build: .
    environment:
      MEMORY_DATABASE_URL: postgresql+asyncpg://memorymesh:${DB_PASSWORD}@postgres:5432/memorymesh
      MEMORY_REDIS_URL: redis://redis:6379/0
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}
      MEMORY_ALLOWED_ORIGINS: ${ALLOWED_ORIGINS}
      MEMORY_ENVIRONMENT: production
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis

  frontend:
    build: ./frontend
    environment:
      NEXT_PUBLIC_API_URL: http://api:8000
    ports:
      - "3000:3000"
    depends_on:
      - api
```

## Security Checklist

- [ ] JWT_SECRET_KEY is set to a secure random value
- [ ] CORS origins are explicitly listed (no wildcard in production)
- [ ] Database credentials are secure
- [ ] API keys are stored securely (use secrets management)
- [ ] HTTPS is enabled
- [ ] Rate limiting is configured appropriately
- [ ] Database backups are configured
- [ ] Monitoring and alerting are set up
- [ ] Logs are aggregated and monitored

## Monitoring

### Health Checks

- `/v1/admin/health` - Basic health check
- `/v1/admin/readiness` - Readiness probe (includes DB check)
- `/metrics` - Prometheus metrics

### Recommended Monitoring

1. **Application Metrics**: Prometheus + Grafana
2. **Logs**: ELK Stack or CloudWatch
3. **Tracing**: Jaeger (if JAEGER_ENDPOINT is set)
4. **Uptime**: UptimeRobot or similar

## Scaling

### Horizontal Scaling

- Use a load balancer (nginx, AWS ALB, etc.)
- Ensure Redis is shared across instances
- Use read replicas for PostgreSQL
- Configure `MEMORY_READ_REPLICA_URLS` for read-heavy workloads

### Vertical Scaling

- Adjust `MEMORY_DATABASE_POOL_SIZE` based on connections
- Configure `MEMORY_MAX_RESULTS` based on memory
- Tune embedding batch sizes

## Backup & Restore

### Database Backup

```bash
# Backup
pg_dump -h localhost -U memorymesh memorymesh > backup.sql

# Restore
psql -h localhost -U memorymesh memorymesh < backup.sql
```

### Automated Backups

Use cron or a backup service:
```bash
0 2 * * * pg_dump -h localhost -U memorymesh memorymesh | gzip > /backups/memorymesh-$(date +\%Y\%m\%d).sql.gz
```

## Troubleshooting

### Common Issues

1. **Database connection errors**: Check connection string and network
2. **CORS errors**: Verify ALLOWED_ORIGINS matches your frontend URL
3. **Rate limiting**: Adjust limits in configuration
4. **Memory issues**: Reduce batch sizes or increase server memory

## Support

For issues and questions, check:
- GitHub Issues
- Documentation: `/docs` endpoint
- API Docs: `/docs` (Swagger UI)

