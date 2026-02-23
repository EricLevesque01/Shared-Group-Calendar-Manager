"""Group and GroupMember ORM models — spec §5.2."""
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class GroupRole(str, enum.Enum):
    admin = "admin"
    member = "member"


class Group(Base):
    __tablename__ = "groups"

    group_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(150), nullable=False)
    created_by = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")


class GroupMember(Base):
    __tablename__ = "group_members"

    group_id = Column(String(36), ForeignKey("groups.group_id"), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.user_id"), primary_key=True)
    role = Column(SAEnum(GroupRole), nullable=False, default=GroupRole.member)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    group = relationship("Group", back_populates="members")
