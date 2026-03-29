import { useEffect, useState, useCallback } from "react";
import type { Device, Connection, Network } from "./types";
import { fetchTopology, fetchNetworks } from "./api";
import GraphView from "./components/GraphView";
import InfoPanel from "./components/InfoPanel";
import AIConsole from "./components/AIConsole";
import AddDeviceWizard from "./components/AddDeviceWizard";
import "./App.css";

type Page = "graph" | "add-device" | "ai-console";

export default function App() {
  const [networks, setNetworks] = useState<Network[]>([]);
  const [currentNetworkId, setCurrentNetworkId] = useState(1);
  const [devices, setDevices] = useState<Device[]>([]);
  const [connections, setConnections] = useState<Connection[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  const [page, setPage] = useState<Page>("graph");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchNetworks().then((n) => { setNetworks(n); if (n.length > 0) setCurrentNetworkId(n[0].id); }).catch(console.error);
  }, []);

  useEffect(() => {
    setLoading(true); setSelectedDevice(null);
    fetchTopology(currentNetworkId).then((t) => { setDevices(t.devices); setConnections(t.connections); }).catch(console.error).finally(() => setLoading(false));
  }, [currentNetworkId]);

  const handleSelectDevice = useCallback((d: Device | null) => setSelectedDevice(d), []);
  const openAI = useCallback((d: Device) => { setSelectedDevice(d); setPage("ai-console"); }, []);
  const nextNet = () => { const i = networks.findIndex(n => n.id === currentNetworkId); setCurrentNetworkId(networks[(i+1) % networks.length].id); };
  const prevNet = () => { const i = networks.findIndex(n => n.id === currentNetworkId); setCurrentNetworkId(networks[(i-1+networks.length) % networks.length].id); };
  const currentNetwork = networks.find(n => n.id === currentNetworkId);

  if (loading) return <div className="app-loading"><div className="loader" /><p>Loading...</p></div>;
  if (page === "add-device") return <AddDeviceWizard onClose={() => setPage("graph")} onAdd={() => setPage("graph")} />;
  if (page === "ai-console" && selectedDevice) return <AIConsole device={selectedDevice} totalDevices={devices.length} onBack={() => setPage("graph")} />;

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-left">
          <h1 className="topbar-title">Discovery <span className="topbar-amp">&amp;</span> Manage</h1>
        </div>
        <div className="topbar-right">
          {networks.length > 1 && (
            <div className="network-switcher">
              <button className="net-nav-btn" onClick={prevNet}>&lt;</button>
              <span className="net-name">{currentNetwork?.name}</span>
              <span className="net-idx">{networks.findIndex(n=>n.id===currentNetworkId)+1}/{networks.length}</span>
              <button className="net-nav-btn" onClick={nextNet}>&gt;</button>
            </div>
          )}
          <div className="topbar-stats">
            <span className="stat-item"><span className="stat-dot online" />{devices.filter(d=>d.status==="online").length} online</span>
            <span className="stat-item"><span className="stat-dot managed" />{devices.filter(d=>d.managed).length} managed</span>
          </div>
          <button className="add-btn" onClick={() => setPage("add-device")}>+ Add Device</button>
        </div>
      </header>
      <main className="main-layout">
        <InfoPanel device={selectedDevice} onOpenAI={() => selectedDevice && openAI(selectedDevice)} />
        <GraphView devices={devices} connections={connections} selectedDeviceId={selectedDevice?.id ?? null} onSelectDevice={handleSelectDevice} />
      </main>
    </div>
  );
}