import { useState } from "react";

/**
 * Modal for starting a brand-new research session.
 * The user enters a topic; on submit, App runs the streaming pipeline and
 * feeds live progress lines back in via the `progress` prop.
 */
export default function NewResearchModal({ onClose, onStart, researching, progress }) {
  const [topic, setTopic] = useState("");
  const [maxPapers, setMaxPapers] = useState(10);

  const handleStart = () => {
    if (!topic.trim() || researching) return;
    onStart(topic.trim(), Number(maxPapers));
  };

  const done = progress.some((p) => p.startsWith("🎉"));

  return (
    <div style={styles.overlay}>
      <div style={styles.modal}>
        <div style={styles.header}>
          <h2 style={styles.title}>New Research Session</h2>
          <button
            onClick={onClose}
            disabled={researching}
            style={{ ...styles.close, ...(researching ? styles.disabled : {}) }}
          >
            ✕
          </button>
        </div>

        {progress.length === 0 ? (
          <>
            <label style={styles.label}>Research topic</label>
            <input
              autoFocus
              style={styles.input}
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleStart()}
              placeholder="e.g. retrieval-augmented generation for code"
            />

            <label style={styles.label}>Max papers</label>
            <input
              type="number"
              min={1}
              max={20}
              style={styles.input}
              value={maxPapers}
              onChange={(e) => setMaxPapers(e.target.value)}
            />

            <button
              onClick={handleStart}
              disabled={!topic.trim()}
              style={{ ...styles.startBtn, ...(!topic.trim() ? styles.disabled : {}) }}
            >
              Start Research
            </button>
            <p style={styles.hint}>
              This searches, downloads, summarizes and indexes papers. It can take a few minutes.
            </p>
          </>
        ) : (
          <div style={styles.progressBox}>
            {progress.map((line, i) => (
              <div key={i} style={styles.progressLine}>
                {line}
              </div>
            ))}
            {researching && (
              <div style={styles.progressLine}>
                <span style={styles.spinner} /> working…
              </div>
            )}
            {done && (
              <button onClick={onClose} style={styles.startBtn}>
                Open Session
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

const styles = {
  overlay: {
    position: "fixed",
    inset: 0,
    background: "rgba(0,0,0,0.6)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 100,
  },
  modal: {
    width: "460px",
    maxWidth: "90vw",
    background: "#1a1d27",
    border: "1px solid #2d2f3e",
    borderRadius: "12px",
    padding: "24px",
    boxShadow: "0 20px 60px rgba(0,0,0,0.5)",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "20px",
  },
  title: { fontSize: "18px", color: "#e0e0e0", margin: 0 },
  close: {
    background: "none",
    border: "none",
    color: "#888",
    fontSize: "18px",
    cursor: "pointer",
  },
  label: {
    display: "block",
    fontSize: "12px",
    color: "#7c83ff",
    fontWeight: 600,
    textTransform: "uppercase",
    letterSpacing: "0.5px",
    marginBottom: "6px",
    marginTop: "14px",
  },
  input: {
    width: "100%",
    boxSizing: "border-box",
    background: "#0f1117",
    border: "1px solid #2d2f3e",
    borderRadius: "8px",
    color: "#e0e0e0",
    padding: "10px 14px",
    fontSize: "14px",
    outline: "none",
    fontFamily: "inherit",
  },
  startBtn: {
    width: "100%",
    marginTop: "20px",
    background: "#7c83ff",
    color: "#fff",
    border: "none",
    borderRadius: "8px",
    padding: "12px",
    fontSize: "14px",
    fontWeight: 600,
    cursor: "pointer",
  },
  hint: { fontSize: "12px", color: "#666", marginTop: "12px", lineHeight: 1.5 },
  progressBox: {
    display: "flex",
    flexDirection: "column",
    gap: "8px",
    maxHeight: "320px",
    overflowY: "auto",
    fontSize: "13px",
    color: "#cfd2e0",
    fontFamily: "monospace",
  },
  progressLine: { lineHeight: 1.5 },
  spinner: {
    display: "inline-block",
    width: "10px",
    height: "10px",
    marginRight: "6px",
    border: "2px solid #7c83ff",
    borderTopColor: "transparent",
    borderRadius: "50%",
    animation: "spin 0.8s linear infinite",
    verticalAlign: "middle",
  },
  disabled: { opacity: 0.4, cursor: "not-allowed" },
};