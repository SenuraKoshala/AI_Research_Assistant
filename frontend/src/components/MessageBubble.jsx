import ReactMarkdown from "react-markdown";

export default function MessageBubble({ message }) {
  const isUser = message.role === "user";

  return (
    <div
      style={{
        ...styles.wrapper,
        justifyContent: isUser ? "flex-end" : "flex-start",
      }}
    >
      <div
        style={{
          ...styles.bubble,
          ...(isUser ? styles.user : styles.assistant),
        }}
      >
        <ReactMarkdown>{message.content}</ReactMarkdown>

        {/* Show sources for assistant messages */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div style={styles.sources}>
            <div style={styles.sourcesTitle}>Sources used:</div>
            {message.sources.slice(0, 3).map((s, i) => (
              <div key={i} style={styles.sourceItem}>
                <span style={styles.sourceScore}>
                  {(s.score * 100).toFixed(0)}% match
                </span>
                <span style={styles.sourceText}>{s.text.slice(0, 120)}...</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

const styles = {
  wrapper: {
    display: "flex",
    width: "100%",
  },
  bubble: {
    maxWidth: "72%",
    padding: "12px 16px",
    borderRadius: "12px",
    fontSize: "14px",
    lineHeight: "1.6",
  },
  user: {
    background: "#7c83ff",
    color: "#fff",
    borderBottomRightRadius: "2px",
  },
  assistant: {
    background: "#1e2130",
    color: "#e0e0e0",
    border: "1px solid #2d2f3e",
    borderBottomLeftRadius: "2px",
  },
  sources: {
    marginTop: "12px",
    paddingTop: "10px",
    borderTop: "1px solid #2d2f3e",
  },
  sourcesTitle: {
    fontSize: "11px",
    color: "#7c83ff",
    fontWeight: 600,
    textTransform: "uppercase",
    marginBottom: "6px",
  },
  sourceItem: {
    display: "flex",
    flexDirection: "column",
    gap: "2px",
    marginBottom: "6px",
  },
  sourceScore: {
    fontSize: "11px",
    color: "#7c83ff",
    fontWeight: 600,
  },
  sourceText: {
    fontSize: "11px",
    color: "#888",
  },
};
