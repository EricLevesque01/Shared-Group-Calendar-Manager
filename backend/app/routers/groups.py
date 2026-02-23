"""Group management API routes."""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.group import Group, GroupMember, GroupRole
from app.models.user import User
from app.schemas.group import GroupCreate, GroupMemberAdd, GroupOut, GroupMemberOut

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
def create_group(payload: GroupCreate, db: Session = Depends(get_db)):
    """Create a new group. Creator is automatically added as admin."""
    creator = db.query(User).filter(User.user_id == str(payload.created_by)).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator user not found")

    group = Group(name=payload.name, created_by=str(payload.created_by))
    db.add(group)
    db.flush()

    # Creator is auto-added as admin
    admin_member = GroupMember(
        group_id=group.group_id,
        user_id=str(payload.created_by),
        role=GroupRole.admin,
    )
    db.add(admin_member)
    db.commit()
    db.refresh(group)
    logger.info("Created group '%s' (%s) by user %s", group.name, group.group_id, payload.created_by)
    return group


@router.get("/", response_model=list[GroupOut])
def list_groups(db: Session = Depends(get_db)):
    """List all groups with their members."""
    return db.query(Group).all()


@router.get("/{group_id}", response_model=GroupOut)
def get_group(group_id: str, db: Session = Depends(get_db)):
    """Fetch a single group by ID with members."""
    group = db.query(Group).filter(Group.group_id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@router.post("/{group_id}/members", response_model=GroupMemberOut, status_code=status.HTTP_201_CREATED)
def add_member(group_id: str, payload: GroupMemberAdd, db: Session = Depends(get_db)):
    """Add a member to a group."""
    group = db.query(Group).filter(Group.group_id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    user = db.query(User).filter(User.user_id == str(payload.user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    existing = (
        db.query(GroupMember)
        .filter(GroupMember.group_id == group_id, GroupMember.user_id == str(payload.user_id))
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="User is already a member of this group")

    member = GroupMember(
        group_id=group_id,
        user_id=str(payload.user_id),
        role=GroupRole(payload.role),
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    logger.info("Added user %s to group %s as %s", payload.user_id, group_id, payload.role)
    return member


@router.delete("/{group_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(group_id: str, user_id: str, db: Session = Depends(get_db)):
    """Remove a member from a group."""
    member = (
        db.query(GroupMember)
        .filter(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="Membership not found")
    db.delete(member)
    db.commit()
    logger.info("Removed user %s from group %s", user_id, group_id)
