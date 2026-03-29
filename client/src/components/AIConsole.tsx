import { useState, useRef, useEffect } from "react";
import type { Device } from "../types";
import "./AIConsole.css";

interface Props { device: Device; totalDevices: number; onBack: () => void; }
type MsgBlock =
  | { type: "user"; text: string }
  | { type: "thinking" }
  | { type: "command"; command: string; output: string; exitCode?: number }
  | { type: "answer"; text: string }
  | { type: "error"; text: string };

export default function AIConsole({ device, totalDevices, onBack }: Props) {
  const [blocks, setBlocks] = useState<MsgBlock[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [connected, setConnected] = useState(false);
  const [checkingCreds, setCheckingCreds] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [protocol, setProtocol] = useState(device.connection_method ?? (device.os_type === "windows" ? "winrm" : "ssh"));
  const [credError, setCredError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  // Check if credentials already exist on mount
  useEffect(() => {
    fetch(`/api/devices/${device.id}/has-credentials`)
      .then(r => r.json())
      .then(data => {
        if (data.has_credentials) setConnected(true);
        setCheckingCreds(false);
      })
      .catch(() => setCheckingCreds(false));
  }, [device.id]);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [blocks, busy]);

  const saveCreds = async () => {
    if (!username || !password) { setCredError("Username and password required"); return; }
    setCredError("");
    try {
      const res = await fetch(`/api/devices/${device.id}/credentials?username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}&protocol=${protocol}`, { method: "POST" });
      if (!res.ok) throw new Error("Failed to store credentials");
      setConnected(true);
    } catch (e: any) {
      setCredError(e.message);
    }
  };

  const send = () => {
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    setBusy(true);
    setBlocks(prev => [...prev, { type: "user", text }]);

    const url = `/api/devices/${device.id}/chat?prompt=${encodeURIComponent(text)}`;
    const es = new EventSource(url);

    let currentCmdIdx = -1;

    es.onmessage = (ev) => {
      const data = JSON.parse(ev.data);
      setBlocks(prev => {
        const next = [...prev];
        switch (data.type) {
          case "thinking":
            // Remove previous thinking if exists
            if (next.length > 0 && next[next.length - 1].type === "thinking") break;
            next.push({ type: "thinking" });
            break;
          case "command":
            // Remove thinking
            if (next.length > 0 && next[next.length - 1].type === "thinking") next.pop();
            next.push({ type: "command", command: data.command, output: "" });
            currentCmdIdx = next.length - 1;
            break;
          case "command_output": {
            if (currentCmdIdx >= 0 && currentCmdIdx < next.length) {
              const cmd = next[currentCmdIdx] as Extract<MsgBlock, { type: "command" }>;
              next[currentCmdIdx] = { ...cmd, output: cmd.output + data.text };
            }
            break;
          }
          case "command_done": {
            if (currentCmdIdx >= 0 && currentCmdIdx < next.length) {
              const cmd = next[currentCmdIdx] as Extract<MsgBlock, { type: "command" }>;
              next[currentCmdIdx] = { ...cmd, exitCode: data.exit_code };
            }
            break;
          }
          case "answer":
            // Remove thinking
            if (next.length > 0 && next[next.length - 1].type === "thinking") next.pop();
            next.push({ type: "answer", text: data.text });
            es.close();
            setBusy(false);
            break;
          case "error":
            if (next.length > 0 && next[next.length - 1].type === "thinking") next.pop();
            next.push({ type: "error", text: data.text });
            es.close();
            setBusy(false);
            break;
        }
        return next;
      });
    };

    es.onerror = () => {
      es.close();
      setBusy(false);
      setBlocks(prev => [...prev, { type: "error", text: "Connection to AI agent lost." }]);
    };
  };

  // Credentials form
  if (checkingCreds) {
    return (
      <div className="ai-page">
        <header className="ai-page-header">
          <button className="ai-back" onClick={onBack}>&larr; Back to Graph</button>
          <div className="ai-page-title"><span className="ai-title-dot" />AI Console</div>
        </header>
        <div className="ai-cred-wrap"><div className="loader" /></div>
      </div>
    );
  }

  if (!connected) {
    return (
      <div className="ai-page">
        <header className="ai-page-header">
          <button className="ai-back" onClick={onBack}>&larr; Back to Graph</button>
          <div className="ai-page-title"><span className="ai-title-dot" />AI Console</div>
        </header>
        <div className="ai-cred-wrap">
          <div className="ai-cred-card">
            <h2>Connect to {device.hostname}</h2>
            <p className="ai-cred-sub">Provide credentials to access <strong>{device.ip}</strong> via remote management.</p>
            <div className="ai-cred-field">
              <label>Protocol</label>
              <div className="ai-cred-protocols">
                {(device.os_type === "windows" ? ["winrm", "ssh"] : ["ssh", "winrm"]).map(p => (
                  <button key={p} className={`ai-cred-proto ${protocol === p ? "active" : ""}`} onClick={() => setProtocol(p)}>{p.toUpperCase()}</button>
                ))}
              </div>
            </div>
            <div className="ai-cred-field">
              <label>Username</label>
              <input value={username} onChange={e => setUsername(e.target.value)} placeholder="admin" autoFocus />
            </div>
            <div className="ai-cred-field">
              <label>Password</label>
              <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="********" onKeyDown={e => e.key === "Enter" && saveCreds()} />
            </div>
            {credError && <p className="ai-cred-error">{credError}</p>}
            <button className="ai-cred-connect" onClick={saveCreds}>Connect</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="ai-page">
      <header className="ai-page-header">
        <button className="ai-back" onClick={onBack}>&larr; Back to Graph</button>
        <div className="ai-page-title"><span className="ai-title-dot" />AI Console</div>
        <div className="ai-page-meta"><span>Target: <strong>{device.hostname}</strong></span><span>{protocol.toUpperCase()} &middot; {totalDevices} devices</span></div>
      </header>
      <div className="ai-page-body">
        <aside className="ai-sidebar">
          <div className="ai-sidebar-card"><h3>{device.hostname}</h3><p className="ai-sidebar-ip">{device.ip}</p>
            <div className="ai-sidebar-grid"><span>OS</span><span>{device.os_type}</span><span>Protocol</span><span>{protocol.toUpperCase()}</span><span>User</span><span>{username}</span></div>
          </div>
          <div className="ai-sidebar-examples"><h4>Try asking:</h4>
            {["What services are running?", "Show recent event logs", "List all users", "Check disk space", "Install IIS and configure it"].map((ex, i) => <button key={i} className="ai-example-btn" onClick={() => setInput(ex)}>{ex}</button>)}
          </div>
        </aside>
        <div className="ai-chat">
          <div className="ai-messages">
            {blocks.length === 0 && !busy && <div className="ai-welcome"><h2>You write, I'll do the IT for you.</h2><p>Ask anything about <strong>{device.hostname}</strong>. I'll run commands on the device and give you answers.</p></div>}
            {blocks.map((b, i) => {
              if (b.type === "user") return <div key={i} className="ai-msg ai-msg-user"><div className="ai-msg-content">{b.text}</div></div>;
              if (b.type === "thinking") return <div key={i} className="ai-msg ai-msg-assistant"><div className="ai-typing"><span /><span /><span /></div></div>;
              if (b.type === "command") return (
                <div key={i} className="ai-msg ai-msg-cmd">
                  <div className="ai-cmd-header"><span className="ai-cmd-icon">$</span> {b.command} {b.exitCode !== undefined && <span className={`ai-cmd-exit ${b.exitCode === 0 ? "ok" : "err"}`}>exit {b.exitCode}</span>}</div>
                  {b.output && <pre className="ai-cmd-output">{b.output}</pre>}
                </div>
              );
              if (b.type === "answer") return <div key={i} className="ai-msg ai-msg-assistant"><div className="ai-msg-content">{b.text}</div></div>;
              if (b.type === "error") return <div key={i} className="ai-msg ai-msg-error"><div className="ai-msg-content">{b.text}</div></div>;
              return null;
            })}
            <div ref={bottomRef} />
          </div>
          <div className="ai-input-area"><div className="ai-input-wrapper">
            <input className="ai-input" placeholder={`Ask about ${device.hostname}...`} value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === "Enter" && send()} disabled={busy} autoFocus />
            <button className="ai-send" onClick={send} disabled={!input.trim() || busy}>{busy ? "..." : "Send"}</button>
          </div></div>
        </div>
      </div>
    </div>
  );
}