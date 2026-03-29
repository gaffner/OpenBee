import { useEffect, useRef, useCallback, useState } from "react";
import cytoscape, { type Core } from "cytoscape";
import cytoscapeDagre from "cytoscape-dagre";
import type { Device, Connection } from "../types";
import { getDeviceIcon, getDeviceColor, getOsLabel } from "../assets/icons";
import "./GraphView.css";

cytoscape.use(cytoscapeDagre);

interface Props {
  devices: Device[];
  connections: Connection[];
  selectedDeviceId: number | null;
  onSelectDevice: (device: Device | null) => void;
}

export default function GraphView({ devices, connections, selectedDeviceId, onSelectDevice }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const [search, setSearch] = useState("");
  const [searchResults, setSearchResults] = useState<Device[]>([]);
  const [showResults, setShowResults] = useState(false);
  const isLarge = devices.length > 100;

  const buildElements = useCallback(() => {
    const nodes = devices.map((d) => {
      const os = getOsLabel(d.os_type, d.vendor_category);
      return { data: { id: String(d.id), label: os ? `${d.hostname}\n${os}` : d.hostname, managed: d.managed, icon: getDeviceIcon(d.device_type, d.os_type, d.vendor_category, d.model), color: getDeviceColor(d.device_type, d.os_type, d.vendor_category), status: d.status } };
    });
    const edges = connections.map((c) => ({ data: { id: `e${c.id}`, source: String(c.source_device_id), target: String(c.target_device_id), connType: c.connection_type } }));
    return [...nodes, ...edges];
  }, [devices, connections]);

  useEffect(() => {
    if (!search.trim()) { setSearchResults([]); setShowResults(false); return; }
    const q = search.toLowerCase();
    setSearchResults(devices.filter(d => d.hostname.toLowerCase().includes(q) || d.ip.includes(q) || (d.mac??"").toLowerCase().includes(q) || (d.vendor??"").toLowerCase().includes(q) || (d.model??"").toLowerCase().includes(q) || d.os_type.includes(q)).slice(0, 12));
    setShowResults(true);
  }, [search, devices]);

  const zoomToDevice = (device: Device) => {
    onSelectDevice(device); setSearch(""); setShowResults(false);
    const cy = cyRef.current; if (!cy) return;
    const node = cy.$(`#${device.id}`);
    if (node.length) { cy.animate({ center: { eles: node }, zoom: 1.5 } as any, { duration: 400 } as any); cy.nodes().unselect(); node.select(); }
  };

  useEffect(() => {
    if (!containerRef.current || devices.length === 0) return;
    const cy = cytoscape({
      container: containerRef.current, elements: buildElements(),
      textureOnViewport: isLarge, hideEdgesOnViewport: isLarge, pixelRatio: isLarge ? 1 : undefined,
      style: [
        { selector: "node", style: { width: 68, height: 68, shape: "ellipse", "background-color": "#ffffff", "background-image": "data(icon)" as any, "background-fit": "contain", "background-width": "65%", "background-height": "65%", "background-image-smoothing": "yes", "border-width": 2.5, "border-color": "data(color)" as any, label: "data(label)", "text-valign": "bottom", "text-margin-y": 6, "font-size": isLarge ? 9 : 11, "font-weight": "600", color: "#1a1a2e", "text-wrap": "wrap", "text-max-width": "110px", "text-outline-color": "#f5f0e8", "text-outline-width": 2, "overlay-padding": 6, "min-zoomed-font-size": isLarge ? 8 : 0 } as any },
        { selector: "node[managed = 0]", style: { "background-color": "#f0ece4", "border-color": "#c5bfb5", "border-style": "dashed", opacity: 0.5, color: "#9ca3af" } as any },
        { selector: "node:selected", style: { "border-width": 3.5, "border-color": "#00a67d", "background-color": "#f0faf6" } as any },
        { selector: 'node[status="offline"]', style: { opacity: 0.3, "border-color": "#ef4444" } as any },
        { selector: "edge", style: { width: 1.5, "line-color": "#c5bfb5", "curve-style": isLarge ? "haystack" : "bezier", "target-arrow-shape": isLarge ? "none" : "triangle", "target-arrow-color": "#c5bfb5", "arrow-scale": 0.7 } as any },
        { selector: 'edge[connType="wifi"]', style: { "line-style": "dashed", "line-dash-pattern": [6, 4], "line-color": "#d4cfc6" } as any },
      ],
      layout: { name: "dagre", rankDir: "TB", nodeSep: isLarge ? 30 : 60, rankSep: isLarge ? 50 : 100, animate: !isLarge, animationDuration: 400 } as any,
      userZoomingEnabled: true, userPanningEnabled: true, boxSelectionEnabled: false, minZoom: 0.1, maxZoom: 4,
    });
    cy.on("tap", "node", (evt: any) => { onSelectDevice(devices.find(d => d.id === Number(evt.target.id())) || null); });
    cy.on("tap", (evt: any) => { if (evt.target === cy) onSelectDevice(null); });
    if (!isLarge) cy.nodes().forEach((node, i) => { node.style("opacity", 0); setTimeout(() => { node.animate({ style: { opacity: node.data("managed") ? 1 : 0.5 } }, { duration: 300, easing: "ease-out-cubic" }); }, Math.min(i * 40, 2000)); });
    cyRef.current = cy;
    return () => { cy.destroy(); };
  }, [devices, connections, buildElements, onSelectDevice, isLarge]);

  useEffect(() => { const cy = cyRef.current; if (!cy) return; cy.nodes().unselect(); if (selectedDeviceId != null) cy.$(`#${selectedDeviceId}`).select(); }, [selectedDeviceId]);

  return (
    <div className="graph-view">
      <div className="graph-topbar">
        <span className="graph-title">Network Topology</span>
        <div className="graph-search-wrap">
          <div className="graph-search-box">
            <input className="graph-search-input" placeholder="Search by hostname, IP, MAC, vendor..." value={search} onChange={e => setSearch(e.target.value)} onFocus={() => search && setShowResults(true)} onBlur={() => setTimeout(() => setShowResults(false), 200)} />
            {search && <button className="search-clear" onClick={() => { setSearch(""); setShowResults(false); }}>x</button>}
          </div>
          {showResults && searchResults.length > 0 && <div className="search-dropdown">{searchResults.map(d => <button key={d.id} className="search-result" onMouseDown={() => zoomToDevice(d)}><div className="sr-main"><span className="sr-hostname">{d.hostname}</span><span className="sr-type">{d.device_type}</span></div><div className="sr-detail">{d.ip} {d.mac ? `· ${d.mac}` : ""} {d.vendor ? `· ${d.vendor}` : ""}</div></button>)}</div>}
          {showResults && search && searchResults.length === 0 && <div className="search-dropdown"><div className="search-empty">No devices found</div></div>}
        </div>
        <div className="graph-legend">
          <span className="legend-item"><span className="legend-dot" style={{background:"#00a67d"}} />Managed</span>
          <span className="legend-item"><span className="legend-dot" style={{background:"#c5bfb5",border:"1px dashed #9ca3af"}} />Discovered</span>
          {isLarge && <span className="legend-count">{devices.length} devices</span>}
        </div>
      </div>
      <div className="graph-canvas-wrap"><div className="graph-container" ref={containerRef} /></div>
    </div>
  );
}