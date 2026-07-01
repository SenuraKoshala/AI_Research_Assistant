import json


def sse(event_type: str, **data) -> str:
    """
    Format a Server-Sent Events (SSE) message.

    Each message is a single line: `data: {json}\n\n`. The blank line
    (the double newline) tells the browser the message is complete.

    Event types used across the app:
      - "status"  → a human-readable progress step ("Searching...")
      - "sources" → the retrieved KB chunks for a chat answer
      - "token"   → one small piece of the streamed answer (live typing)
      - "session" → the id of a newly created research session
      - "done"    → the stream finished successfully
      - "error"   → something failed; `message` holds the reason
    """
    payload = {"type": event_type, **data}
    return f"data: {json.dumps(payload)}\n\n"