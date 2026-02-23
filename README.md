# AI-Agent Shared Group Calendar

A closed-group collaborative scheduling platform (≤15 users) with an AI reasoning layer (ReAct pattern) above a deterministic backend.

## Architecture

- **Frontend**: Next.js (React)
- **Backend API**: FastAPI (Python)
- **Database**: PostgreSQL
- **AI Agent**: Tool-enabled ReAct agent (OpenAI function-calling)

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
# Edit .env with your API keys and database URL
cp .env.example .env

# Create database
createdb group_calendar

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### API Documentation
Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
project_2/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI entry point
│   │   ├── config.py          # Environment-based settings
│   │   ├── database.py        # SQLAlchemy engine + session
│   │   ├── models/            # ORM models
│   │   ├── schemas/           # Pydantic request/response
│   │   ├── routers/           # API route modules
│   │   ├── services/          # Business logic + invariants
│   │   └── agent/             # AI agent (ReAct loop)
│   ├── alembic/               # Database migrations
│   ├── tests/                 # Test suite
│   ├── .env                   # API keys (git-ignored)
│   └── requirements.txt
├── frontend/                  # Next.js app
└── .gitignore
```

## Key Design Decisions

- **Agent reasons, backend enforces** — AI agent can only mutate through validated service layer
- **Optimistic locking** — all event mutations require version match
- **Soft deletes** — cancelled events are never hard-deleted
- **Mutation ledger** — append-only EventMutations for full auditability
- **DND evaluation** — timezone math always handled by backend (never agent)

## License

Private — GRAD 5900 Project 2
