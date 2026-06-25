import { useState, useEffect } from "react";
import axios from "axios";
import ChatWindow from "./components/ChatWindow";
import SessionSelector from "./components/SessionSelector";

const API = "http://127.0.0.1:8000";

export default function App() {
  const [sessions, setSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    axios.get(`${API}/sessions`).then((res) => setSessions(res.data));
  }, []);

  const handleSelectSession = (session) => {
    setSelectedSession(session);
    setHistory([]);
  };

  const handleSend = async (message) => {
    if (!selectedSession) return;

    const userMsg = { role: "user", content: message };
    const updatedHistory = [...history, userMsg];
    setHistory(updatedHistory);
    setLoading(true);

    try {
      const res = await axios.post(`${API}/chat`, {
        session_id: selectedSession.session_id,
        message,
        history: history,
      });

      const assistantMsg = {
        role: "assistant",
        content: res.data.reply,
        sources: res.data.sources,
      };
      setHistory([...updatedHistory, assistantMsg]);
    } catch (err) {
      setHistory([
        ...updatedHistory,
        {
          role: "assistant",
          content: "Error getting response. Please try again.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.app}>
      <div style={styles.sidebar}>
        <h2 style={styles.sidebarTitle}>Research Sessions</h2>
        <SessionSelector
          sessions={sessions}
          selected={selectedSession}
          onSelect={handleSelectSession}
        />
      </div>
      <div style={styles.main}>
        {selectedSession ? (
          <>
            <div style={styles.topBar}>
              <span style={styles.topicLabel}>Topic:</span>
              <span style={styles.topicText}>{selectedSession.topic}</span>
              <span style={styles.paperCount}>
                {selectedSession.paper_count} papers
              </span>
            </div>
            <ChatWindow
              history={history}
              loading={loading}
              onSend={handleSend}
            />
          </>
        ) : (
          <div style={styles.placeholder}>
            <h2>Select a research session to start chatting</h2>
            <p>Your past research sessions appear in the sidebar.</p>
          </div>
        )}
      </div>
    </div>
  );
}

const styles = {
  app: {
    display: "flex",
    height: "100vh",
    fontFamily: "'Segoe UI', sans-serif",
    background: "#0f1117",
    color: "#e0e0e0",
  },
  sidebar: {
    width: "280px",
    background: "#1a1d27",
    borderRight: "1px solid #2d2f3e",
    padding: "20px",
    overflowY: "auto",
  },
  sidebarTitle: {
    fontSize: "14px",
    fontWeight: 600,
    color: "#7c83ff",
    textTransform: "uppercase",
    letterSpacing: "1px",
    marginBottom: "16px",
  },
  main: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
  },
  topBar: {
    padding: "14px 24px",
    background: "#1a1d27",
    borderBottom: "1px solid #2d2f3e",
    display: "flex",
    alignItems: "center",
    gap: "10px",
  },
  topicLabel: {
    fontSize: "12px",
    color: "#7c83ff",
    fontWeight: 600,
    textTransform: "uppercase",
  },
  topicText: {
    fontSize: "14px",
    color: "#e0e0e0",
    flex: 1,
  },
  paperCount: {
    fontSize: "12px",
    color: "#666",
    background: "#2d2f3e",
    padding: "3px 10px",
    borderRadius: "12px",
  },
  placeholder: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    color: "#555",
    textAlign: "center",
  },
};
