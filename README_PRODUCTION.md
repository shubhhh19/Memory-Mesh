# MemoryMesh - Production Ready SaaS

A production-ready semantic memory layer for AI systems with full authentication, conversation management, analytics, and real-time features.

## 🎯 What's Been Implemented

### ✅ Backend (100% Complete)
- **Authentication System**: JWT tokens, user management, API keys, sessions
- **Conversation Management**: Full CRUD with statistics and pagination
- **Message Operations**: Create, update, delete, batch operations
- **Analytics**: Usage stats, trends, tenant analytics, embedding stats
- **Advanced Retention**: Rule-based lifecycle management with multiple rule types
- **WebSocket Support**: Real-time updates and streaming search
- **Distributed Tracing**: OpenTelemetry with Jaeger integration
- **API Versioning**: Proper version management with deprecation support
- **Security**: Secure CORS, encrypted storage, rate limiting, JWT validation

### ✅ Frontend (Core Features Complete)
- **Authentication Flow**: Login, register, JWT token management
- **Conversation UI**: List and view conversations with threading
- **Encrypted Storage**: Secure token storage with crypto-js
- **Error Handling**: Error boundaries, offline detection
- **Loading States**: Spinner components and loading indicators
- **Mobile Responsive**: Responsive design for all screen sizes
- **Data Export**: Export conversations in JSON/CSV format
- **Keyboard Shortcuts**: Common shortcuts support

### ✅ Infrastructure
- **CI/CD Pipeline**: GitHub Actions for testing and deployment
- **Monitoring**: Prometheus alerts and health checks
- **Backup/Restore**: Automated backup scripts
- **Deployment Docs**: Complete production deployment guide

## 🚀 Quick Start

### Prerequisites
- PostgreSQL 14+ with pgvector
- Redis (optional, for rate limiting)
- Python 3.11+
- Node.js 18+

### Installation

1. **Clone and setup backend:**
```bash
# Install dependencies
uv pip install -e ".[dev]"

# Setup database
export MEMORY_DATABASE_URL="postgresql+asyncpg://user:pass@localhost/memorymesh"
export JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Run migrations
alembic upgrade head

# Start server
uvicorn ai_memory_layer.main:app --host 0.0.0.0 --port 8000
```

2. **Setup frontend:**
```bash
cd frontend
npm install
npm run dev
```

3. **Access the application:**
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs
- Register a new account and start using!

## 📋 API Endpoints

### Authentication
- `POST /v1/auth/register` - Register new user
- `POST /v1/auth/login` - Login and get tokens
- `GET /v1/auth/me` - Get current user
- `POST /v1/auth/logout` - Logout

### Conversations
- `GET /v1/conversations` - List conversations
- `POST /v1/conversations` - Create conversation
- `GET /v1/conversations/{id}` - Get conversation
- `PUT /v1/conversations/{id}` - Update conversation
- `DELETE /v1/conversations/{id}` - Delete conversation
- `GET /v1/conversations/{id}/stats` - Get statistics

### Messages
- `POST /v1/messages` - Create message
- `GET /v1/messages/{id}` - Get message
- `PUT /v1/messages/{id}` - Update message
- `DELETE /v1/messages/{id}` - Delete message
- `POST /v1/messages/batch` - Batch create
- `POST /v1/messages/batch/update` - Batch update
- `POST /v1/messages/batch/delete` - Batch delete

### Analytics
- `GET /v1/analytics/usage` - Usage statistics
- `GET /v1/analytics/trends` - Message trends
- `GET /v1/analytics/top-conversations` - Top conversations
- `GET /v1/analytics/embeddings` - Embedding stats

### Retention
- `GET /v1/retention/policy` - Get retention policy
- `PUT /v1/retention/policy` - Update policy
- `GET /v1/retention/rules` - List rules
- `POST /v1/retention/rules` - Create rule
- `POST /v1/retention/execute` - Execute retention

### WebSocket
- `ws://localhost:8000/v1/ws/messages/{tenant_id}` - Real-time updates
- `ws://localhost:8000/v1/ws/stream/{tenant_id}` - Streaming search

## 🔒 Security Features

- JWT authentication with refresh tokens
- Encrypted token storage (crypto-js)
- Secure CORS configuration
- Rate limiting per tenant and globally
- API key management
- Role-based access control (admin, user, read_only)
- Input validation and sanitization

## 📊 Monitoring

- Prometheus metrics at `/metrics`
- Health checks at `/v1/admin/health`
- Readiness probe at `/v1/admin/readiness`
- Distributed tracing (if Jaeger configured)
- Alert rules in `docs/monitoring/alerts.yml`

## 🧪 Testing

```bash
# Backend tests
pytest tests/ -v --cov=src/ai_memory_layer

# Frontend tests (when implemented)
cd frontend && npm test
```

## 📦 Deployment

See `docs/DEPLOYMENT.md` for complete production deployment guide.

### Docker Compose
```bash
docker-compose up -d
```

### Manual Deployment
1. Set environment variables
2. Run migrations: `alembic upgrade head`
3. Start backend: `uvicorn ai_memory_layer.main:app`
4. Build frontend: `cd frontend && npm run build && npm start`

## 🔄 Backup & Restore

```bash
# Backup
./scripts/backup.sh

# Restore
./scripts/restore.sh /backups/memorymesh_20241208_120000.sql.gz
```

## 📈 What's Next (Optional Enhancements)

- [ ] Saved searches and bookmarks
- [ ] Data visualization charts
- [ ] Frontend unit tests
- [ ] i18n support
- [ ] Enhanced accessibility
- [ ] Performance benchmarks

## 📝 License

MIT

## 🤝 Contributing

Contributions welcome! Please read the contributing guidelines first.

