import { useEffect, useState, useCallback } from "react";
import type { Device, Connection, Network, Neo4jConfig } from "./types";
import { fetchTopology, fetchNetworks, fetchNeo4jConfig } from "./api";
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
  const [refreshKey, setRefreshKey] = useState(0);
  const [showDemo, setShowDemo] = useState(false);
  const [neo4jConfig, setNeo4jConfig] = useState<Neo4jConfig | null>(null);
  const [showUnmanaged, setShowUnmanaged] = useState(true);

  useEffect(() => {
    fetchNeo4jConfig().then(setNeo4jConfig).catch(console.error);
    fetchNetworks().then((n) => { setNetworks(n); if (n.length > 0) setCurrentNetworkId(n[0].id); }).catch(console.error);
  }, []);

  useEffect(() => {
    setLoading(true); setSelectedDevice(null);
    fetchTopology(currentNetworkId).then((t) => { setDevices(t.devices); setConnections(t.connections); }).catch(console.error).finally(() => setLoading(false));
  }, [currentNetworkId, refreshKey]);

  const handleSelectDevice = useCallback((d: Device | null) => setSelectedDevice(d), []);
  const openAI = useCallback((d: Device) => { setSelectedDevice(d); setPage("ai-console"); }, []);
  const isYourNetwork = networks.length > 0 && currentNetworkId === networks[0].id;

  // Auto-refresh after adding a device (background scan creates neighbors)
  useEffect(() => {
    if (!isYourNetwork || page !== "graph") return;
    const prevCount = devices.length;
    const interval = setInterval(() => {
      fetchTopology(currentNetworkId).then((t) => {
        if (t.devices.length !== prevCount) {
          setDevices(t.devices);
          setConnections(t.connections);
        }
      }).catch(() => {});
    }, 3000);
    // Stop polling after 30s
    const timeout = setTimeout(() => clearInterval(interval), 30000);
    return () => { clearInterval(interval); clearTimeout(timeout); };
  }, [currentNetworkId, refreshKey, isYourNetwork, page]);

  // Demo networks = all networks except the first one ("Your Network")
  const demoNetworks = networks.filter((_, i) => i > 0);
  const nextDemo = () => { if (demoNetworks.length === 0) return; const i = demoNetworks.findIndex(n => n.id === currentNetworkId); setCurrentNetworkId(demoNetworks[(i+1) % demoNetworks.length].id); };
  const prevDemo = () => { if (demoNetworks.length === 0) return; const i = demoNetworks.findIndex(n => n.id === currentNetworkId); setCurrentNetworkId(demoNetworks[(i-1+demoNetworks.length) % demoNetworks.length].id); };
  const currentNetwork = networks.find(n => n.id === currentNetworkId);

  if (loading) return <div className="app-loading"><div className="loader" /><p>Loading...</p></div>;
  if (page === "add-device") return <AddDeviceWizard networkId={networks.length > 0 ? networks[0].id : 1} onClose={() => setPage("graph")} onAdded={() => { setCurrentNetworkId(networks[0].id); setShowDemo(false); setRefreshKey(k => k + 1); setPage("graph"); }} />;
  if (page === "ai-console" && selectedDevice) return <AIConsole device={selectedDevice} totalDevices={devices.length} onBack={() => setPage("graph")} />;

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-left">
          <h1 className="topbar-title">Discovery <span className="topbar-amp">&amp;</span> Manage</h1>
        </div>
        <div className="topbar-right">
          {/* Your Network / Demo toggle */}
          <div className="network-switcher">
            <button className={`net-tab ${isYourNetwork && !showDemo ? "active" : ""}`} onClick={() => { setShowDemo(false); setCurrentNetworkId(networks[0].id); }}>Your Network</button>
            <button className={`net-tab ${showDemo ? "active" : ""}`} onClick={() => { setShowDemo(true); if (demoNetworks.length > 0) setCurrentNetworkId(demoNetworks[0].id); }}>Demo</button>
          </div>
          {showDemo && demoNetworks.length > 1 && (
            <div className="demo-nav">
              <button className="net-nav-btn" onClick={prevDemo}>&lt;</button>
              <span className="net-name">{currentNetwork?.name}</span>
              <span className="net-idx">{demoNetworks.findIndex(n=>n.id===currentNetworkId)+1}/{demoNetworks.length}</span>
              <button className="net-nav-btn" onClick={nextDemo}>&gt;</button>
            </div>
          )}
          <div className="topbar-stats">
            <span className="stat-item"><span className="stat-dot online" />{devices.filter(d=>d.status==="online").length} online</span>
            <span className="stat-item"><span className="stat-dot managed" />{devices.filter(d=>d.managed).length} managed</span>
          </div>
          <label className="unmanaged-toggle">
            <input type="checkbox" checked={showUnmanaged} onChange={e => setShowUnmanaged(e.target.checked)} />
            <span>Unmanaged</span>
          </label>
          <button className="add-btn" onClick={() => setPage("add-device")}>+ Add Device</button>
        </div>
      </header>
      <main className="main-layout">
        <InfoPanel device={selectedDevice} onOpenAI={() => selectedDevice && openAI(selectedDevice)} />
        <GraphView devices={devices} selectedDeviceId={selectedDevice?.id ?? null} onSelectDevice={handleSelectDevice} networkId={currentNetworkId} neo4jConfig={neo4jConfig} showUnmanaged={showUnmanaged} />
      </main>
    </div>
  );
}