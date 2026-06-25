from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str   # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    session_id: str
    message: str
    history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    reply: str
    sources: list[dict] = []


class SessionInfo(BaseModel):
    session_id: str
    topic: str
    created_at: str
    paper_count: int