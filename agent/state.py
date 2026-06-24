import json
import os
import uuid
from datetime import datetime
from config import SESSIONS_DIR

STEPS = [
    "search_papers",
    "download_pdfs",
    "chunk_texts",
    "summarize_papers",
    "compare_papers",
    "generate_report",
    "save_to_kb",
]


class AgentState:
    def __init__(self, topic: str, session_id: str = None):
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.topic = topic
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at

        # Step tracking
        self.completed_steps: list[str] = []
        self.current_step: str | None = None
        self.failed_steps: list[str] = []

        # Data accumulated across steps
        self.papers: list[dict] = []        # PaperMetadata list
        self.summaries: list[dict] = []     # PaperSummary list
        self.comparison: dict = {}          # Comparison table
        self.report_path: str | None = None

        # Counters
        self.llm_calls: int = 0

    def mark_step_complete(self, step: str):
        if step not in self.completed_steps:
            self.completed_steps.append(step)
        self.current_step = None
        self.updated_at = datetime.now().isoformat()
        self.save()

    def mark_step_failed(self, step: str):
        if step not in self.failed_steps:
            self.failed_steps.append(step)
        self.updated_at = datetime.now().isoformat()
        self.save()

    def is_step_done(self, step: str) -> bool:
        return step in self.completed_steps

    def next_pending_step(self) -> str | None:
        for step in STEPS:
            if step not in self.completed_steps:
                return step
        return None  # All steps done

    def save(self):
        os.makedirs(SESSIONS_DIR, exist_ok=True)
        path = os.path.join(SESSIONS_DIR, f"{self.session_id}.json")
        with open(path, "w") as f:
            json.dump(self.__dict__, f, indent=2)

    @classmethod
    def load(cls, session_id: str) -> "AgentState":
        path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"No session found: {session_id}")
        with open(path) as f:
            data = json.load(f)
        state = cls.__new__(cls)
        state.__dict__.update(data)
        return state

    @classmethod
    def list_sessions(cls) -> list[dict]:
        os.makedirs(SESSIONS_DIR, exist_ok=True)
        sessions = []
        for fname in os.listdir(SESSIONS_DIR):
            if fname.endswith(".json"):
                with open(os.path.join(SESSIONS_DIR, fname)) as f:
                    data = json.load(f)
                sessions.append({
                    "session_id": data["session_id"],
                    "topic": data["topic"],
                    "created_at": data["created_at"],
                    "completed_steps": data["completed_steps"],
                })
        return sessions