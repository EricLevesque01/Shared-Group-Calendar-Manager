"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

# Import routers
from app.routers import users, groups, events, attendees, change_requests, agent

app = FastAPI(
    title="Shared Group Calendar",
    description="AI-Agent Shared Group Calendar — collaborative scheduling for friend groups (≤15 users)",
    version="0.1.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(groups.router, prefix="/api/groups", tags=["Groups"])
app.include_router(events.router, prefix="/api/events", tags=["Events"])
app.include_router(attendees.router, prefix="/api/attendees", tags=["Attendees"])
app.include_router(change_requests.router, prefix="/api/change-requests", tags=["ChangeRequests"])
app.include_router(agent.router, prefix="/api/agent", tags=["Agent"])


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
