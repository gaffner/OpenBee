import { useState } from "react";
import "./AddDeviceWizard.css";

interface Props { onClose: () => void; onAdd: (data: any) => void; }
type Step = "type" | "connect" | "ip" | "label" | "installing";
const PROTOCOLS: Record<string, string[]> = { Windows:["WinRM","RDP","Automatic"], Linux:["SSH","Automatic"], MacOS:["SSH","Automatic"], Router:["SSH","Telnet","SNMP","REST API","Automatic"], Other:["WinRM","SSH","Telnet","SNMP","REST API","Automatic"] };

export default function AddDeviceWizard({ onClose, onAdd }: Props) {
  const [step, setStep] = useState<Step>("type");
  const [dir, setDir] = useState<"forward"|"back">("forward");
  const [deviceType, setDeviceType] = useState("");
  const [connectionMethod, setConnectionMethod] = useState("");
  const [ip, setIp] = useState("");
  const [label, setLabel] = useState("");
  const [progress, setProgress] = useState<string[]>([]);
  const goTo = (s: Step, d: "forward"|"back" = "forward") => { setDir(d); setStep(s); };
  const simulate = () => { goTo("installing"); const steps=["Connecting...","Authenticating...","Running: hostname","Running: network discovery","Running: service enumeration","Done!"]; steps.forEach((s,i)=>setTimeout(()=>{setProgress(p=>[...p,s]); if(i===steps.length-1) setTimeout(()=>onAdd({ip,deviceType,connectionMethod,label}),1000);}, (i+1)*600)); };
  const sn = step==="type"?1:step==="connect"?2:step==="ip"?3:step==="label"?4:5;

  return (
    <div className="wizard-page">
      <header className="wizard-header">
        <button className="wizard-back-btn" onClick={onClose}>&larr; Cancel</button>
        <div className="wizard-title">Add New Device</div>
        <div className="wizard-progress-bar"><div className="wizard-progress-fill" style={{width:`${sn/4*100}%`}} /></div>
      </header>
      <div className="wizard-body"><div className={`wizard-step-container ${dir}`} key={step}>
        {step==="type" && <div className="wizard-step"><div className="wizard-step-number">Step 1 of 4</div><h2>What type of device?</h2>
          <div className="wizard-grid">{["Windows","Linux","MacOS","Router","Other"].map(t=><button key={t} className={`wizard-card ${deviceType===t?"selected":""}`} onClick={()=>{setDeviceType(t);setConnectionMethod((PROTOCOLS[t]||PROTOCOLS.Other)[0]);}}>{t}</button>)}</div>
          <div className="wizard-actions"><div/><button className="wizard-next-btn" disabled={!deviceType} onClick={()=>goTo("connect")}>Continue</button></div>
        </div>}
        {step==="connect" && <div className="wizard-step"><div className="wizard-step-number">Step 2 of 4</div><h2>Connection protocol</h2>
          <div className="wizard-protocol-list">{(PROTOCOLS[deviceType]||PROTOCOLS.Other).map(m=><button key={m} className={`wizard-protocol ${connectionMethod===m?"selected":""}`} onClick={()=>setConnectionMethod(m)}><span className="wizard-protocol-name">{m}</span>{m==="Automatic"&&<span className="wizard-protocol-badge">Recommended</span>}</button>)}</div>
          <div className="wizard-actions"><button className="wizard-back-action" onClick={()=>goTo("type","back")}>Back</button><button className="wizard-next-btn" disabled={!connectionMethod} onClick={()=>goTo("ip")}>Continue</button></div>
        </div>}
        {step==="ip" && <div className="wizard-step"><div className="wizard-step-number">Step 3 of 4</div><h2>Device address</h2>
          <input className="wizard-text-input" placeholder="e.g. 192.168.1.100" value={ip} onChange={e=>setIp(e.target.value)} autoFocus />
          <div className="wizard-actions"><button className="wizard-back-action" onClick={()=>goTo("connect","back")}>Back</button><button className="wizard-next-btn" disabled={!ip.trim()} onClick={()=>goTo("label")}>Continue</button></div>
        </div>}
        {step==="label" && <div className="wizard-step"><div className="wizard-step-number">Step 4 of 4</div><h2>Give it a name</h2>
          <input className="wizard-text-input" placeholder="e.g. Web Server" value={label} onChange={e=>setLabel(e.target.value)} autoFocus />
          <div className="wizard-actions"><button className="wizard-back-action" onClick={()=>goTo("ip","back")}>Back</button><button className="wizard-connect-btn" onClick={simulate}>Connect Device</button></div>
        </div>}
        {step==="installing" && <div className="wizard-step wizard-step-installing"><div className="wizard-install-spinner" /><h2>Connecting to {ip}</h2>
          <div className="wizard-install-log">{progress.map((p,i)=><div key={i} className={`install-line ${p==="Done!"?"done":""}`}>{p}</div>)}</div>
        </div>}
      </div></div>
    </div>
  );
}