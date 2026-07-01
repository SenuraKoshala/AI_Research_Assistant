import { useState, useRef, useEffect } from "react";
import MessageBubble from "./MessageBubble";

export default function ChatWindow({ history, loading, status, onSend }) {
  const [input, setInput] = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history, loading, status]);

  const handleSubmit = () => {
    if (!input.trim() || loading) return;
    onSend(input.trim());
    setInput("");
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // Show the "thinking" indicator only while we're loading and the answer
  // hasn't started streaming into the last bubble yet.
  const lastMsg = history[history.length - 1];
  const answerStarted =
    lastMsg && lastMsg.role === "assistant" && lastMsg.content.length > 0;
  const showThinking = loading && !answerStarted;

  return (
    <div style={styles.container}>
      <div style={styles.messages}>
        {history.length === 0 && (
          <div style={styles.empty}>
            Ask anything about the research papers in this session.
          </div>
        )}
        {history.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}
        {showThinking && (
          <div style={styles.thinking}>
            <div style={styles.dots}>
              <span style={styles.dot} /> <span style={styles.dot} />{" "}
              <span style={styles.dot} />
            </div>
            {status && <span style={styles.statusText}>{status}</span>}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div style={styles.inputArea}>
        <textarea
          style={styles.textarea}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about the research papers... (Enter to send)"
          rows={2}
        />
        <button
          onClick={handleSubmit}
          disabled={loading || !input.trim()}
          style={{
            ...styles.button,
            ...(loading || !input.trim() ? styles.buttonDisabled : {}),
          }}
        >
          Send
        </button>
      </div>
    </div>
  );
}

const styles = {
  container: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  },
  messages: {
    flex: 1,
    overflowY: "auto",
    padding: "24px",
    display: "flex",
    flexDirection: "column",
    gap: "16px",
  },
  empty: {
    textAlign: "center",
    color: "#555",
    marginTop: "40px",
    fontSize: "14px",
  },
  thinking: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    padding: "8px 4px",
    alignSelf: "flex-start",
  },
  dots: {
    display: "flex",
    gap: "6px",
  },
  statusText: {
    fontSize: "13px",
    color: "#7c83ff",
    fontStyle: "italic",
  },
  dot: {
    width: "8px",
    height: "8px",
    background: "#7c83ff",
    borderRadius: "50%",
    display: "inline-block",
    animation: "bounce 1s infinite",
  },
  inputArea: {
    display: "flex",
    gap: "12px",
    padding: "16px 24px",
    borderTop: "1px solid #2d2f3e",
    background: "#1a1d27",
  },
  textarea: {
    flex: 1,
    background: "#0f1117",
    border: "1px solid #2d2f3e",
    borderRadius: "8px",
    color: "#e0e0e0",
    padding: "10px 14px",
    fontSize: "14px",
    resize: "none",
    outline: "none",
    fontFamily: "inherit",
  },
  button: {
    background: "#7c83ff",
    color: "#fff",
    border: "none",
    borderRadius: "8px",
    padding: "0 24px",
    fontSize: "14px",
    fontWeight: 600,
    cursor: "pointer",
  },
  buttonDisabled: {
    opacity: 0.4,
    cursor: "not-allowed",
  },
};