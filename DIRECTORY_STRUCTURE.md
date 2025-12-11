# Directory Structure

This document describes the reorganized directory structure of the Memory Mesh project.

## Root Level

```
Memory Mesh/
├── backend/              # Backend Python application
├── frontend/             # Frontend Next.js application
├── docs/                 # Documentation files
├── .env.example          # Environment variables template
├── docker-compose.yml    # Docker Compose configuration
├── render.yaml           # Render.com deployment config
├── README.md             # Main project documentation
├── README_PRODUCTION.md  # Production deployment guide
├── INTEGRATION.md        # Integration guide
└── LICENSE               # MIT License
```

## Backend Directory (`backend/`)

```
backend/
├── src/                  # Source code
│   └── ai_memory_layer/  # Main application package
├── tests/                # Test files
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   └── e2e/             # End-to-end tests
├── alembic/              # Database migrations
├── scripts/              # Utility scripts
├── static/               # Static files served by backend
│   ├── index.html       # Backend dashboard
│   └── assets/          # Backend assets
├── Dockerfile            # Backend Docker configuration
├── Makefile              # Backend build commands
├── pyproject.toml        # Python project configuration
├── alembic.ini           # Alembic configuration
├── uv.lock               # Dependency lock file
└── README.md             # Backend documentation
```

## Frontend Directory (`frontend/`)

```
frontend/
├── app/                  # Next.js app directory
├── lib/                  # Utility libraries
├── public/               # Static assets
├── Dockerfile            # Frontend Docker configuration
├── package.json          # Node.js dependencies
└── ...                   # Other Next.js config files
```

## Key Changes

1. **Backend files consolidated**: All backend-related files (src/, tests/, alembic/, scripts/) are now in the `backend/` directory
2. **Static files**: Backend static files moved to `backend/static/`
3. **Configuration updates**: All config files (Dockerfile, docker-compose.yml, render.yaml) updated to reflect new paths
4. **Documentation**: README files updated with new command paths

## Running Commands

### Backend Commands
All backend commands should be run from the `backend/` directory:
```bash
cd backend
alembic upgrade head
pytest
uvicorn ai_memory_layer.main:app --reload
```

### Frontend Commands
Frontend commands remain the same:
```bash
cd frontend
npm install
npm run dev
```

### Docker Commands
Docker commands work from the root:
```bash
docker compose up --build
```
