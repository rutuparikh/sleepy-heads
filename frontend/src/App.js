import { useState } from "react";

const API_URL = process.env.REACT_APP_API_URL || "/api/chat";

export default function App() {
  const [messages, setMessages] = useState([
    {
      role: "Story Builder",
      content: "Hello!! What's your mood today? Help me with your thoughts and I will create a story for you to read tonight.",
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [stages, setStages] = useState([]);
  const [sessionId, setSessionId] = useState(null);

  async function handleSubmit(event) {
    event.preventDefault();

    const message = input.trim();
    if (!message || isLoading) return;

    setInput("");
    setIsLoading(true);
    setMessages((current) => [...current, { role: "user", content: message }]);
    console.log("[SleepyHeads] Sending chat request", {
      apiUrl: API_URL,
      messageLength: message.length,
      sessionId,
    });

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, session_id: sessionId }),
      });
      console.log("[SleepyHeads] Received chat response", {
        ok: response.ok,
        status: response.status,
        statusText: response.statusText,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        console.warn("[SleepyHeads] Backend returned an error", errorData);
        throw new Error(errorData?.detail || "The backend could not process that request.");
      }

      const data = await response.json();
      console.log("[SleepyHeads] Chat request completed", {
        sessionId: data.session_id,
        responseLength: data.message?.length || 0,
        stages: data.stages?.map((stage) => stage.name) || [],
      });
      setSessionId(data.session_id);
      setStages(data.stages || []);
      setMessages((current) => [...current, { role: "Story Builder", content: data.message }]);
    } catch (error) {
      console.error("[SleepyHeads] Chat request failed", error);
      setMessages((current) => [
        ...current,
        { role: "Story Builder", content: error.message },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="chat-panel" aria-label="Sleepy Heads">
        <header className="chat-header">
          <div>
            <h1>Sleepy Heads</h1>
            {/* <p>FastAPI backend with code-managed prompts and Responses API stages.</p> */}
          </div>
          <div className="status">{isLoading ? "Running" : "Ready"}</div>
        </header>

        <div className="messages">
          {messages.map((message, index) => (
            <article className={`message ${message.role}`} key={`${message.role}-${index}`}>
              <span>{message.role}</span>
              <p>{message.content}</p>
            </article>
          ))}
        </div>

        <div className="stage-list" aria-label="Completed pipeline stages">
          {stages.map((stage) => (
            <span key={stage.name}>{stage.name}</span>
          ))}
        </div>

        <form className="composer" onSubmit={handleSubmit}>
          <textarea
            aria-label="Message"
            placeholder="Ask for a story..."
            value={input}
            onChange={(event) => setInput(event.target.value)}
          />
          <button type="submit" disabled={isLoading || !input.trim()}>
            Send
          </button>
        </form>
      </section>
    </main>
  );
}
