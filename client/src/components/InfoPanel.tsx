import type { Device } from "../types";
import "./InfoPanel.css";

interface Props { device: Device | null; onOpenAI: () => void; }

export default function InfoPanel({ device, onOpenAI }: Props) {
  if (!device) return <div className="info-panel"><div className="info-panel-header">Info</div><div className="info-empty"><p>Select a device in the graph to view its details.</p></div></div>;
  return (
    <div className="info-panel">
      <div className="info-panel-header">Info
        <div style={{display:"flex",gap:8}}>
          <span className={`managed-badge ${device.managed?"yes":"no"}`}>{device.managed?"Managed":"Discovered"}</span>
          <span className="status-badge" style={{background:device.status==="online"?"#10b981":"#ef4444"}}>{device.status}</span>
        </div>
      </div>
      <div className="info-body">
        <section className="info-section"><h3>{device.hostname}</h3>{device.label && <p className="info-label">{device.label}</p>}
          <div className="info-grid">
            <span className="info-key">IP</span><span className="info-val">{device.ip}</span>
            <span className="info-key">MAC</span><span className="info-val">{device.mac ?? "—"}</span>
            <span className="info-key">Type</span><span className="info-val">{device.device_type.toUpperCase()}</span>
            <span className="info-key">OS</span><span className="info-val">{device.os_type}</span>
            <span className="info-key">Vendor</span><span className="info-val">{device.vendor ?? "—"}</span>
            <span className="info-key">Manufacturer</span><span className="info-val">{device.manufacturer ?? "—"}</span>
            <span className="info-key">Connect</span><span className="info-val">{device.connection_method ?? "—"}</span>
          </div>
        </section>
        <section className="info-section"><h4>Hardware</h4>
          <div className="info-grid">
            <span className="info-key">Model</span><span className="info-val">{device.model ?? "—"}</span>
            <span className="info-key">RAM</span><span className="info-val">{device.ram_gb ? `${device.ram_gb} GB` : "—"}</span>
            <span className="info-key">CPU</span><span className="info-val">{device.cpu ?? "—"}</span>
            <span className="info-key">CPU Usage</span><span className="info-val">{device.cpu_usage != null ? `${device.cpu_usage}%` : "—"}</span>
            <span className="info-key">Uptime</span><span className="info-val">{device.uptime ?? "—"}</span>
          </div>
        </section>
        {device.services && device.services.length > 0 && <section className="info-section"><h4>Services</h4><ul className="service-list">{device.services.map((s,i)=><li key={i} className="service-item"><span className="service-dot" style={{background:s.status==="running"?"#10b981":"#ef4444"}} /><span>{s.displayName??s.name}</span></li>)}</ul></section>}
        {device.open_ports && device.open_ports.length > 0 && <section className="info-section"><h4>Listening Ports</h4><div className="port-tags">{device.open_ports.map((p,i)=><span key={i} className="port-tag">{p}</span>)}</div></section>}
        <button className="ai-btn" onClick={onOpenAI}>Open AI Console</button>
      </div>
    </div>
  );
}