import { useState, useEffect } from "react";
import axios from "axios";
import ChatWindow from "./components/ChatWindow";
import SessionSelector from "./components/SessionSelector";
import NewResearchModal from "./components/NewResearchModal";
import { API, streamSSE } from "./api";

export default function App() {
  const [sessions, setSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("");

  // New-research modal state
  const [showNewResearch, setShowNewResearch] = useState(false);
  const [researching, setResearching] = useState(false);
  const [researchProgress, setResearchProgress] = useState([]);

  const refreshSessions = () =>
    axios.get(`${API}/sessions`).then((res) => {
      setSessions(res.data);
      return res.data;
    });

  useEffect(() => {
    refreshSessions();
  }, []);

  const handleSelectSession = (session) => {
    setSelectedSession(session);
    setHistory([]);
  };

  const handleSend = async (message) => {
    if (!selectedSession) return;

    const priorHistory = history;
    setHistory((h) => [
      ...h,
      { role: "user", content: message },
      { role: "assistant", content: "", sources: [], streaming: true },
    ]);
    setLoading(true);
    setStatus("");

    let answer = "";
    let sources = [];

    // Replace the last (assistant) message as tokens arrive.
    const updateLast = (patch) =>
      setHistory((h) => {
        const copy = [...h];
        copy[copy.length - 1] = { ...copy[copy.length - 1], ...patch };
        return copy;
      });

    try {
      await streamSSE(
        "/chat/stream",
        {
          session_id: selectedSession.session_id,
          message,
          history: priorHistory,
        },
        (evt) => {
          if (evt.type === "status") {
            setStatus(evt.message);
          } else if (evt.type === "sources") {
            sources = evt.sources;
          } else if (evt.type === "token") {
            answer += evt.content;
            updateLast({ content: answer, sources });
          } else if (evt.type === "done") {
            updateLast({ content: answer, sources, streaming: false });
          } else if (evt.type === "error") {
            updateLast({
              content: `⚠️ Error: ${evt.message}`,
              streaming: false,
            });
          }
        }
      );
    } catch (err) {
      updateLast({
        content: "Error getting response. Please try again.",
        streaming: false,
      });
    } finally {
      setLoading(false);
      setStatus("");
    }
  };

  const handleStartResearch = async (topic, maxPapers) => {
    setResearching(true);
    setResearchProgress([]);
    let newSessionId = null;

    try {
      await streamSSE(
        "/research/stream",
        { topic, max_papers: maxPapers },
        (evt) => {
          if (evt.type === "status") {
            setResearchProgress((p) => [...p, evt.message]);
          } else if (evt.type === "session") {
            newSessionId = evt.session_id;
          } else if (evt.type === "done") {
            newSessionId = evt.session_id;
            setResearchProgress((p) => [...p, "🎉 Research complete!"]);
          } else if (evt.type === "error") {
            setResearchProgress((p) => [...p, `❌ Error: ${evt.message}`]);
          }
        }
      );

      // Refresh the sidebar and jump into the new session.
      const updated = await refreshSessions();
      const created = updated.find((s) => s.session_id === newSessionId);
      if (created) handleSelectSession(created);
    } catch (err) {
      setResearchProgress((p) => [...p, `❌ Error: ${err.message}`]);
    } finally {
      setResearching(false);
    }
  };

  const closeModal = () => {
    if (researching) return;
    setShowNewResearch(false);
    setResearchProgress([]);
  };

  return (
    <div style={styles.app}>
      {showNewResearch && (
        <NewResearchModal
          onClose={closeModal}
          onStart={handleStartResearch}
          researching={researching}
          progress={researchProgress}
        />
      )}
      <div style={styles.sidebar}>
        <h2 style={styles.sidebarTitle}>Research Sessions</h2>
        <button
          style={styles.newBtn}
          onClick={() => setShowNewResearch(true)}
        >
          + New Research
        </button>
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
              status={status}
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
  newBtn: {
    width: "100%",
    marginBottom: "16px",
    background: "#7c83ff",
    color: "#fff",
    border: "none",
    borderRadius: "8px",
    padding: "10px",
    fontSize: "13px",
    fontWeight: 600,
    cursor: "pointer",
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
