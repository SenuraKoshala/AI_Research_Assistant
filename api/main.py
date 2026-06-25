import json
import logging
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.models import ChatRequest, ChatResponse, SessionInfo
from api.chat import chat_with_kb
from config import SESSIONS_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Research Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _load_kb_sessions() -> list[dict]:
    sessions = []
    if not os.path.exists(SESSIONS_DIR):
        return sessions
    for fname in os.listdir(SESSIONS_DIR):
        if fname.endswith("_kb.json"):
            with open(os.path.join(SESSIONS_DIR, fname), encoding="utf-8") as f:
                data = json.load(f)
            sessions.append(data)
    return sessions


@app.get("/sessions", response_model=list[SessionInfo])
def get_sessions():
    """Return all available research sessions."""
    sessions = _load_kb_sessions()
    return [
        SessionInfo(
            session_id=s["session_id"],
            topic=s["topic"],
            created_at=s["created_at"][:19],
            paper_count=s["paper_count"],
        )
        for s in sessions
    ]


@app.get("/sessions/{session_id}/papers")
def get_session_papers(session_id: str):
    """Return papers for a specific session."""
    path = os.path.join(SESSIONS_DIR, f"{session_id}_kb.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Session not found")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {"papers": data.get("papers", [])}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """Main RAG chat endpoint."""
    # Load topic from session metadata
    path = os.path.join(SESSIONS_DIR, f"{request.session_id}_kb.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Session not found in knowledge base")

    with open(path, encoding="utf-8") as f:
        session_data = json.load(f)

    topic = session_data.get("topic", "research topic")

    reply, sources = chat_with_kb(
        session_id=request.session_id,
        message=request.message,
        history=[m.model_dump() for m in request.history],
        topic=topic,
    )

    return ChatResponse(reply=reply, sources=sources)


@app.get("/health")
def health():
    return {"status": "ok"}