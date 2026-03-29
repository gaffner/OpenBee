import { useState } from "react";
import { createDevice } from "../api";
import "./AddDeviceWizard.css";

interface Props { networkId: number; onClose: () => void; onAdded: () => void; }
type Step = "type" | "connect" | "ip" | "creds" | "label" | "installing";
const PROTOCOLS: Record<string, string[]> = { Windows:["WinRM","RDP","Automatic"], Linux:["SSH","Automatic"], MacOS:["SSH","Automatic"], Router:["SSH","Telnet","SNMP","REST API","Automatic"], Other:["WinRM","SSH","Telnet","SNMP","REST API","Automatic"] };
const OS_MAP: Record<string, string> = { Windows:"windows", Linux:"linux", MacOS:"macos", Router:"ios", Other:"other" };

export default function AddDeviceWizard({ networkId, onClose, onAdded }: Props) {
  const [step, setStep] = useState<Step>("type");
  const [dir, setDir] = useState<"forward"|"back">("forward");
  const [deviceType, setDeviceType] = useState("");
  const [connectionMethod, setConnectionMethod] = useState("");
  const [ip, setIp] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [label, setLabel] = useState("");
  const [progress, setProgress] = useState<string[]>([]);
  const [error, setError] = useState("");
  const goTo = (s: Step, d: "forward"|"back" = "forward") => { setDir(d); setStep(s); };

  const doInstall = async () => {
    goTo("installing");
    const steps = ["Connecting...", "Authenticating...", "Discovering device...", "Saving..."];
    for (let i = 0; i < steps.length; i++) {
      await new Promise(r => setTimeout(r, 500));
      setProgress(p => [...p, steps[i]]);
    }
    try {
      const protocol = connectionMethod === "WinRM" ? "winrm" : connectionMethod === "SSH" ? "ssh" : connectionMethod.toLowerCase();
      await createDevice({
        network_id: networkId,
        hostname: label || ip,
        ip,
        mac: null,
        device_type: deviceType === "Router" ? "router" : deviceType === "Other" ? "pc" : "pc",
        os_type: OS_MAP[deviceType] || "other",
        manufacturer: null, vendor: null, vendor_category: null,
        model: null, ram_gb: null, cpu: null, cpu_usage: null, uptime: null,
        status: "online",
        label: label || null,
        connection_method: protocol,
        services: null, open_ports: null,
        users_connected: 0, last_login: null,
        managed: 1,
        cred_username: username || undefined,
        cred_password: password || undefined,
      } as any);
      setProgress(p => [...p, "Done!"]);
      setTimeout(() => onAdded(), 800);
    } catch (e: any) {
      setError(e.message);
      setProgress(p => [...p, `Error: ${e.message}`]);
    }
  };

  const sn = step==="type"?1:step==="connect"?2:step==="ip"?3:step==="creds"?4:step==="label"?5:6;
  const totalSteps = 5;

  return (
    <div className="wizard-page">
      <header className="wizard-header">
        <button className="wizard-back-btn" onClick={onClose}>&larr; Cancel</button>
        <div className="wizard-title">Add New Device</div>
        <div className="wizard-progress-bar"><div className="wizard-progress-fill" style={{width:`${sn/totalSteps*100}%`}} /></div>
      </header>
      <div className="wizard-body"><div className={`wizard-step-container ${dir}`} key={step}>
        {step==="type" && <div className="wizard-step"><div className="wizard-step-number">Step 1 of {totalSteps}</div><h2>What type of device?</h2>
          <div className="wizard-grid">{["Windows","Linux","MacOS","Router","Other"].map(t=><button key={t} className={`wizard-card ${deviceType===t?"selected":""}`} onClick={()=>{setDeviceType(t);setConnectionMethod((PROTOCOLS[t]||PROTOCOLS.Other)[0]);}}>{t}</button>)}</div>
          <div className="wizard-actions"><div/><button className="wizard-next-btn" disabled={!deviceType} onClick={()=>goTo("connect")}>Continue</button></div>
        </div>}
        {step==="connect" && <div className="wizard-step"><div className="wizard-step-number">Step 2 of {totalSteps}</div><h2>Connection protocol</h2>
          <div className="wizard-protocol-list">{(PROTOCOLS[deviceType]||PROTOCOLS.Other).map(m=><button key={m} className={`wizard-protocol ${connectionMethod===m?"selected":""}`} onClick={()=>setConnectionMethod(m)}><span className="wizard-protocol-name">{m}</span>{m==="Automatic"&&<span className="wizard-protocol-badge">Recommended</span>}</button>)}</div>
          <div className="wizard-actions"><button className="wizard-back-action" onClick={()=>goTo("type","back")}>Back</button><button className="wizard-next-btn" disabled={!connectionMethod} onClick={()=>goTo("ip")}>Continue</button></div>
        </div>}
        {step==="ip" && <div className="wizard-step"><div className="wizard-step-number">Step 3 of {totalSteps}</div><h2>Device address</h2>
          <input className="wizard-text-input" placeholder="e.g. 192.168.1.100" value={ip} onChange={e=>setIp(e.target.value)} autoFocus />
          <div className="wizard-actions"><button className="wizard-back-action" onClick={()=>goTo("connect","back")}>Back</button><button className="wizard-next-btn" disabled={!ip.trim()} onClick={()=>goTo("creds")}>Continue</button></div>
        </div>}
        {step==="creds" && <div className="wizard-step"><div className="wizard-step-number">Step 4 of {totalSteps}</div><h2>Credentials</h2>
          <p style={{fontSize:14,color:"var(--text-secondary)",marginBottom:24}}>Enter credentials for remote access. These will be used by the AI console to manage this device.</p>
          <input className="wizard-text-input" placeholder="Username (e.g. admin)" value={username} onChange={e=>setUsername(e.target.value)} autoFocus style={{marginBottom:12}} />
          <input className="wizard-text-input" type="password" placeholder="Password" value={password} onChange={e=>setPassword(e.target.value)} />
          <div className="wizard-actions"><button className="wizard-back-action" onClick={()=>goTo("ip","back")}>Back</button><button className="wizard-next-btn" onClick={()=>goTo("label")}>Continue</button></div>
        </div>}
        {step==="label" && <div className="wizard-step"><div className="wizard-step-number">Step 5 of {totalSteps}</div><h2>Give it a name</h2>
          <input className="wizard-text-input" placeholder="e.g. Web Server" value={label} onChange={e=>setLabel(e.target.value)} autoFocus />
          <div className="wizard-actions"><button className="wizard-back-action" onClick={()=>goTo("creds","back")}>Back</button><button className="wizard-connect-btn" onClick={doInstall}>Connect Device</button></div>
        </div>}
        {step==="installing" && <div className="wizard-step wizard-step-installing"><div className="wizard-install-spinner" /><h2>Connecting to {ip}</h2>
          <div className="wizard-install-log">{progress.map((p,i)=><div key={i} className={`install-line ${p==="Done!"?"done":p.startsWith("Error")?"err":""}`}>{p}</div>)}</div>
          {error && <button className="wizard-back-action" onClick={onClose} style={{marginTop:20}}>Close</button>}
        </div>}
      </div></div>
    </div>
  );
}