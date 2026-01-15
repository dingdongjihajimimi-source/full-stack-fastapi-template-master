import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .user import User


# 聊天会话模型
class ChatSessionBase(SQLModel):
    title: str = Field(max_length=255)


class ChatSessionCreate(ChatSessionBase):
    pass


class ChatSession(ChatSessionBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    messages: list["ChatMessage"] = Relationship(back_populates="session", cascade_delete=True)


class ChatSessionPublic(ChatSessionBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ChatSessionsPublic(SQLModel):
    data: list[ChatSessionPublic]
    count: int


# 聊天消息模型
class ChatMessageBase(SQLModel):
    content: str
    role: str = Field(max_length=50)  # "user"（用户）或 "ai"（人工智能）


class ChatCreate(SQLModel):
    content: str
    session_id: uuid.UUID


class ChatMessage(ChatMessageBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(foreign_key="user.id", nullable=False)
    session_id: uuid.UUID = Field(foreign_key="chatsession.id", nullable=False, ondelete="CASCADE")
    created_at: datetime = Field(default_factory=datetime.now)
    session: ChatSession = Relationship(back_populates="messages")


class ChatPublic(ChatMessageBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    session_id: uuid.UUID
    created_at: datetime


class ChatsPublic(SQLModel):
    data: list[ChatPublic]
    count: int
