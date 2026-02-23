"""User API routes."""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserOut

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    """Create a new user with timezone and DND preferences."""
    user = User(**payload.model_dump())
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Created user %s (%s)", user.user_id, user.display_name)
    return user


@router.get("/", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    """List all users."""
    return db.query(User).all()


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: str, db: Session = Depends(get_db)):
    """Fetch a single user by ID."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: str, payload: UserUpdate, db: Session = Depends(get_db)):
    """Update user preferences (partial update)."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    logger.info("Updated user %s", user_id)
    return user
