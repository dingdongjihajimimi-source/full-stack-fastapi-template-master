import asyncio
import uuid
from datetime import datetime
from typing import Any, AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session, func, select

from app.api.deps import CurrentUser, SessionDep
from app.core.db import engine
from app.models import (
    ChatCreate,
    ChatMessage,
    ChatPublic,
    ChatSession,
    ChatSessionCreate,
    ChatSessionPublic,
    ChatSessionsPublic,
    ChatsPublic,
    Message,
)

router = APIRouter(prefix="/chat", tags=["chat"])


from app.core.config import settings

async def call_doubao_api(prompt: str, history: list[dict[str, str]]) -> AsyncGenerator[str, None]:
    """调用豆包 API 获取回复 (流式)"""
    if not settings.VOLC_API_KEY or not settings.VOLC_MODEL_ID:
        yield "AI 配置缺失，请检查环境变量 VOLC_API_KEY 和 VOLC_MODEL_ID"
        return

    try:
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(
            api_key=settings.VOLC_API_KEY,
            base_url="https://ark.cn-beijing.volces.com/api/v3",
        )
        
        messages = history + [{"role": "user", "content": prompt}]
        
        stream = await client.chat.completions.create(
            model=settings.VOLC_MODEL_ID,
            messages=messages,
            stream=True,
        )
        
        async for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
    except Exception as e:
        print(f"Error calling Doubao API: {e}")
        yield f"AI 调用失败: {str(e)}"


@router.delete("/sessions/{session_id}", response_model=Message)
def delete_session(
    session: SessionDep, current_user: CurrentUser, session_id: uuid.UUID
) -> Any:
    """
    Delete a chat session.
    """
    chat_session = session.get(ChatSession, session_id)
    if not chat_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if chat_session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    session.delete(chat_session)
    session.commit()
    return Message(message="Session deleted successfully")


@router.post("/sessions", response_model=ChatSessionPublic)
def create_session(
    *, session: SessionDep, current_user: CurrentUser
) -> Any:
    """
    Create a new chat session.
    """
    chat_session = ChatSession(
        title="New Chat",
        user_id=current_user.id,
    )
    session.add(chat_session)
    session.commit()
    session.refresh(chat_session)
    return chat_session


@router.get("/sessions", response_model=ChatSessionsPublic)
def read_sessions(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve chat sessions.
    """
    count_statement = (
        select(func.count())
        .select_from(ChatSession)
        .where(ChatSession.user_id == current_user.id)
    )
    count = session.exec(count_statement).one()
    statement = (
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    sessions = session.exec(statement).all()

    return ChatSessionsPublic(data=sessions, count=count)


@router.get("/", response_model=ChatsPublic)
def read_chats(
    session: SessionDep,
    current_user: CurrentUser,
    session_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve chat history for a specific session.
    """
    count_statement = (
        select(func.count())
        .select_from(ChatMessage)
        .where(ChatMessage.owner_id == current_user.id)
        .where(ChatMessage.session_id == session_id)
    )
    count = session.exec(count_statement).one()
    statement = (
        select(ChatMessage)
        .where(ChatMessage.owner_id == current_user.id)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .offset(skip)
        .limit(limit)
    )
    chats = session.exec(statement).all()

    return ChatsPublic(data=chats, count=count)


@router.post("/")
def create_chat(
    *, session: SessionDep, current_user: CurrentUser, chat_in: ChatCreate
) -> Any:
    """
    Send a new message and get AI response (Streaming).
    """
    # 0. Build context from history (Last 10 messages of current session)
    history_statement = (
        select(ChatMessage)
        .where(ChatMessage.owner_id == current_user.id)
        .where(ChatMessage.session_id == chat_in.session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(10)
    )
    history_msgs = session.exec(history_statement).all()
    # Reverse to chronological order
    history_msgs.reverse()
    
    formatted_history = []
    for msg in history_msgs:
        role = "assistant" if msg.role == "ai" else msg.role
        formatted_history.append({"role": role, "content": msg.content})

    # 1. Save user message
    user_message = ChatMessage(
        content=chat_in.content,
        role="user",
        owner_id=current_user.id,
        session_id=chat_in.session_id,
    )
    session.add(user_message)
    session.commit()
    session.refresh(user_message)

    # Update session title if it's the first message (or title is "New Chat")
    chat_session = session.get(ChatSession, chat_in.session_id)
    if chat_session and chat_session.title == "New Chat":
        chat_session.title = chat_in.content[:20] + "..." if len(chat_in.content) > 20 else chat_in.content
        chat_session.updated_at = datetime.now()
        session.add(chat_session)
        session.commit()
    elif chat_session:
        chat_session.updated_at = datetime.now()
        session.add(chat_session)
        session.commit()

    # Extract user_id and session_id to avoid DetachedInstanceError in async generator
    user_id = current_user.id
    session_id = chat_in.session_id

    # 2. Generator for streaming response
    async def generate():
        full_response = ""
        async for chunk in call_doubao_api(chat_in.content, formatted_history):
            full_response += chunk
            yield chunk
        
        # 3. Save AI message
        # Use a new session because the dependency session might be closed or invalid in async context
        with Session(engine) as db:
            ai_message = ChatMessage(
                content=full_response,
                role="ai",
                owner_id=user_id,
                session_id=session_id,
            )
            db.add(ai_message)
            db.commit()

    return StreamingResponse(generate(), media_type="text/event-stream")

