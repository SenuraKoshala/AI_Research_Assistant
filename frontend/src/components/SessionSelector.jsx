export default function SessionSelector({ sessions, selected, onSelect }) {
  if (sessions.length === 0) {
    return (
      <p style={styles.empty}>
        No sessions found. Run a research session first.
      </p>
    );
  }

  return (
    <div>
      {sessions.map((s) => (
        <div
          key={s.session_id}
          onClick={() => onSelect(s)}
          style={{
            ...styles.card,
            ...(selected?.session_id === s.session_id ? styles.active : {}),
          }}
        >
          <div style={styles.topic}>{s.topic}</div>
          <div style={styles.meta}>
            {s.paper_count} papers · {s.created_at.slice(0, 10)}
          </div>
        </div>
      ))}
    </div>
  );
}

const styles = {
  card: {
    padding: "12px",
    borderRadius: "8px",
    marginBottom: "8px",
    cursor: "pointer",
    border: "1px solid #2d2f3e",
    transition: "all 0.2s",
  },
  active: {
    background: "#2d2f3e",
    borderColor: "#7c83ff",
  },
  topic: {
    fontSize: "13px",
    fontWeight: 500,
    color: "#e0e0e0",
    marginBottom: "4px",
  },
  meta: {
    fontSize: "11px",
    color: "#666",
  },
  empty: {
    fontSize: "12px",
    color: "#555",
  },
};
