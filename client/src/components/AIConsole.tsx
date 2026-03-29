import { useState, useRef, useEffect } from "react";
import type { Device } from "../types";
import "./AIConsole.css";

interface Props { device: Device; totalDevices: number; onBack: () => void; }
interface Message { role: "user" | "assistant"; content: string; }

export default function AIConsole({ device, totalDevices, onBack }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, isTyping]);

  const send = () => {
    const text = input.trim(); if (!text) return;
    setMessages(p => [...p, { role: "user", content: text }]); setInput(""); setIsTyping(true);
    setTimeout(() => { setIsTyping(false); setMessages(p => [...p, { role: "assistant", content: `I would execute that on ${device.hostname} (${device.ip}). AI integration coming soon.` }]); }, 1200);
  };

  return (
    <div className="ai-page">
      <header className="ai-page-header">
        <button className="ai-back" onClick={onBack}>&larr; Back to Graph</button>
        <div className="ai-page-title"><span className="ai-title-dot" />AI Console</div>
        <div className="ai-page-meta"><span>Target: <strong>{device.hostname}</strong></span><span>{totalDevices} devices</span></div>
      </header>
      <div className="ai-page-body">
        <aside className="ai-sidebar">
          <div className="ai-sidebar-card"><h3>{device.hostname}</h3><p className="ai-sidebar-ip">{device.ip}</p></div>
          <div className="ai-sidebar-examples"><h4>Try asking:</h4>
            {["What services are running?","Show recent event logs","Install IIS and configure it","Who logged in today?"].map((ex,i)=><button key={i} className="ai-example-btn" onClick={()=>setInput(ex)}>{ex}</button>)}
          </div>
        </aside>
        <div className="ai-chat">
          <div className="ai-messages">
            {messages.length === 0 && <div className="ai-welcome"><h2>You write, I'll do the IT for you.</h2><p>Ask anything about <strong>{device.hostname}</strong>.</p></div>}
            {messages.map((m,i) => <div key={i} className={`ai-msg ai-msg-${m.role}`}><div className="ai-msg-content">{m.content}</div></div>)}
            {isTyping && <div className="ai-msg ai-msg-assistant"><div className="ai-typing"><span/><span/><span/></div></div>}
            <div ref={bottomRef} />
          </div>
          <div className="ai-input-area"><div className="ai-input-wrapper">
            <input className="ai-input" placeholder={`Ask about ${device.hostname}...`} value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>e.key==="Enter"&&send()} autoFocus />
            <button className="ai-send" onClick={send} disabled={!input.trim()}>Send</button>
          </div></div>
        </div>
      </div>
    </div>
  );
}