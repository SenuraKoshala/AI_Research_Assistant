import logging
from google import genai
from config import GEMINI_API_KEY, GEMINI_MODEL
from tools.knowledge_base import query_kb

client = genai.Client(api_key=GEMINI_API_KEY)
logger = logging.getLogger(__name__)


def _build_system_prompt(topic: str, context_chunks: list[dict]) -> str:
    context_text = ""
    for i, chunk in enumerate(context_chunks, 1):
        context_text += f"\n[Source {i}]\n{chunk['text']}\n"

    return f"""You are a research assistant with deep knowledge about the following research topic:
**{topic}**

You have access to the following relevant excerpts from research papers:
{context_text}

Instructions:
- Answer questions based on the provided research context above
- Be specific and cite which paper or source supports your answer when possible
- If the context doesn't contain enough information to answer, say so clearly
- Keep answers focused and academic in tone
- When comparing papers, use the context provided
"""


def _format_history(history: list[dict]) -> str:
    formatted = ""
    for msg in history:
        role = "User" if msg["role"] == "user" else "Assistant"
        formatted += f"{role}: {msg['content']}\n"
    return formatted


def chat_with_kb(
    session_id: str,
    message: str,
    history: list[dict],
    topic: str,
) -> tuple[str, list[dict]]:
    """
    RAG chat:
    1. Retrieve relevant chunks from ChromaDB for this session
    2. Build prompt with context + history
    3. Call Gemini and return response + sources
    """

    # Step 1 — Retrieve relevant chunks
    sources = query_kb(query=message, session_id=session_id, top_k=5)
    logger.info(f"[Chat] Retrieved {len(sources)} chunks for query: {message[:60]}")

    # Step 2 — Get topic from KB session metadata
    system_prompt = _build_system_prompt(topic, sources)

    # Step 3 — Build full prompt with history
    history_text = _format_history(history)
    full_prompt = f"""{system_prompt}

Conversation so far:
{history_text}
User: {message}
Assistant:"""

    # Step 4 — Call Gemini
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=full_prompt,
    )

    reply = response.text.strip()
    return reply, sources