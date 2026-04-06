import { useEffect, useRef, useState } from "react";
import NeoVis from "neovis.js";
import type { Device, Neo4jConfig } from "../types";
import "./GraphView.css";

interface Props {
  devices: Device[];
  selectedDeviceId: number | null;
  onSelectDevice: (device: Device | null) => void;
  networkId: number;
  neo4jConfig: Neo4jConfig | null;
}

export default function GraphView({
  devices,
  selectedDeviceId,
  onSelectDevice,
  networkId,
  neo4jConfig,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const visRef = useRef<any>(null);
  const [search, setSearch] = useState("");
  const [searchResults, setSearchResults] = useState<Device[]>([]);
  const [showResults, setShowResults] = useState(false);

  useEffect(() => {
    if (!search.trim()) {
      setSearchResults([]);
      setShowResults(false);
      return;
    }
    const q = search.toLowerCase();
    setSearchResults(
      devices
        .filter(
          (d) =>
            d.hostname.toLowerCase().includes(q) ||
            d.ip.includes(q) ||
            (d.mac ?? "").toLowerCase().includes(q) ||
            (d.vendor ?? "").toLowerCase().includes(q) ||
            (d.model ?? "").toLowerCase().includes(q) ||
            d.os_type.includes(q)
        )
        .slice(0, 12)
    );
    setShowResults(true);
  }, [search, devices]);

  const zoomToDevice = (device: Device) => {
    onSelectDevice(device);
    setSearch("");
    setShowResults(false);
    const viz = visRef.current;
    if (viz?.network && viz?.nodes) {
      const allNodes = viz.nodes.get();
      const target = allNodes.find(
        (n: any) => n.raw?.properties?.id === device.id
      );
      if (target) {
        viz.network.focus(target.id, {
          scale: 1.5,
          animation: { duration: 400, easingFunction: "easeInOutQuad" },
        });
        viz.network.selectNodes([target.id]);
      }
    }
  };

  // Render neovis graph
  useEffect(() => {
    if (!containerRef.current || !neo4jConfig) return;

    const cypher = [
      `MATCH (d:Device {network_id: ${networkId}})`,
      `OPTIONAL MATCH (d)-[r:CONNECTS_TO]-(d2:Device {network_id: ${networkId}})`,
      `RETURN d, r, d2`,
    ].join(" ");

    const config = {
      containerId: "neovis-container",
      neo4j: {
        serverUrl: neo4jConfig.uri,
        serverUser: neo4jConfig.user,
        serverPassword: neo4jConfig.password,
      },
      visConfig: {
        nodes: {
          font: {
            size: 13,
            color: "#1a1a2e",
            face: "Inter, system-ui, sans-serif",
            strokeWidth: 3,
            strokeColor: "#f5f0e8",
          },
          borderWidth: 2.5,
          shadow: {
            enabled: true,
            size: 10,
            x: 2,
            y: 2,
            color: "rgba(0,0,0,0.08)",
          },
        },
        edges: {
          color: {
            color: "#d4cfc6",
            highlight: "#00a67d",
            hover: "#00a67d",
          },
          width: 1.5,
          smooth: { type: "continuous", roundness: 0.3 },
          arrows: { to: { enabled: true, scaleFactor: 0.4 } },
        },
        physics: {
          enabled: true,
          barnesHut: {
            gravitationalConstant: -4000,
            centralGravity: 0.15,
            springLength: 160,
            springConstant: 0.035,
            damping: 0.15,
            avoidOverlap: 0.3,
          },
          stabilization: { iterations: 150, updateInterval: 25 },
        },
        interaction: {
          hover: true,
          tooltipDelay: 200,
          zoomView: true,
          dragView: true,
          zoomSpeed: 0.08,
        },
      },
      labels: {
        Device: {
          label: "hostname",
          [NeoVis.NEOVIS_ADVANCED_CONFIG]: {
            function: {
              color: (node: any) => {
                const p = node.properties;
                if (p.status === "offline")
                  return {
                    background: "#fef2f2",
                    border: "#ef4444",
                    highlight: {
                      background: "#fee2e2",
                      border: "#dc2626",
                    },
                    hover: { background: "#fee2e2", border: "#dc2626" },
                  };
                if (p.managed === 0)
                  return {
                    background: "#f8f6f2",
                    border: "#c5bfb5",
                    highlight: {
                      background: "#f0ece4",
                      border: "#a3a097",
                    },
                    hover: { background: "#f0ece4", border: "#a3a097" },
                  };
                const palette: Record<string, any> = {
                  router: {
                    background: "#fffbeb",
                    border: "#f59e0b",
                    highlight: {
                      background: "#fef3c7",
                      border: "#d97706",
                    },
                    hover: { background: "#fef3c7", border: "#d97706" },
                  },
                  switch: {
                    background: "#ecfdf5",
                    border: "#10b981",
                    highlight: {
                      background: "#d1fae5",
                      border: "#059669",
                    },
                    hover: { background: "#d1fae5", border: "#059669" },
                  },
                  server: {
                    background: "#eff6ff",
                    border: "#3b82f6",
                    highlight: {
                      background: "#dbeafe",
                      border: "#2563eb",
                    },
                    hover: { background: "#dbeafe", border: "#2563eb" },
                  },
                  dc: {
                    background: "#f5f3ff",
                    border: "#8b5cf6",
                    highlight: {
                      background: "#ede9fe",
                      border: "#7c3aed",
                    },
                    hover: { background: "#ede9fe", border: "#7c3aed" },
                  },
                  pc: {
                    background: "#f8fafc",
                    border: "#64748b",
                    highlight: {
                      background: "#f1f5f9",
                      border: "#475569",
                    },
                    hover: { background: "#f1f5f9", border: "#475569" },
                  },
                };
                return (
                  palette[p.device_type] || {
                    background: "#ffffff",
                    border: "#00a67d",
                    highlight: {
                      background: "#f0faf6",
                      border: "#00a67d",
                    },
                    hover: { background: "#f0faf6", border: "#00a67d" },
                  }
                );
              },
              size: (node: any) => {
                const t = node.properties.device_type;
                if (t === "router") return 35;
                if (t === "switch") return 28;
                if (t === "server" || t === "dc") return 30;
                return 20;
              },
              shape: (node: any) => {
                if (node.properties.managed === 0) return "diamond";
                const t = node.properties.device_type;
                if (t === "router") return "triangle";
                if (t === "switch") return "square";
                if (t === "server") return "hexagon";
                if (t === "dc") return "star";
                return "dot";
              },
              borderWidth: (node: any) =>
                node.properties.managed === 0 ? 1.5 : 2.5,
              borderDashes: (node: any) =>
                node.properties.managed === 0 ? [4, 4] : false,
            },
          },
        },
      },
      relationships: {
        CONNECTS_TO: {
          [NeoVis.NEOVIS_ADVANCED_CONFIG]: {
            function: {
              width: (rel: any) =>
                rel.properties.connection_type === "wifi" ? 1 : 2,
              dashes: (rel: any) =>
                rel.properties.connection_type === "wifi" ? [6, 4] : false,
            },
          },
        },
      },
      initialCypher: cypher,
    };

    const viz = new NeoVis(config as any);

    viz.registerOnEvent("completed", () => {
      if (viz.network) {
        viz.network.on("click", (params: any) => {
          if (!params.nodes || params.nodes.length === 0) {
            onSelectDevice(null);
            return;
          }
          const nodeId = params.nodes[0];
          const nodeData = (viz as any).nodes?.get(nodeId);
          if (nodeData?.raw?.properties) {
            const device = devices.find(
              (d) => d.id === nodeData.raw.properties.id
            );
            if (device) onSelectDevice(device);
          }
        });
      }
    });

    viz.render();
    visRef.current = viz;

    return () => {
      viz.clearNetwork();
    };
  }, [networkId, neo4jConfig, devices.length]);

  // Sync selection highlight
  useEffect(() => {
    const viz = visRef.current;
    if (!viz?.network || !(viz as any).nodes) return;
    if (selectedDeviceId == null) {
      viz.network.unselectAll();
      return;
    }
    const allNodes = (viz as any).nodes.get();
    const target = allNodes.find(
      (n: any) => n.raw?.properties?.id === selectedDeviceId
    );
    if (target) viz.network.selectNodes([target.id]);
  }, [selectedDeviceId]);

  if (!neo4jConfig) {
    return (
      <div className="graph-view">
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            height: "100%",
            flexDirection: "column",
            gap: 12,
          }}
        >
          <div className="loader" />
          <p>Connecting to Neo4j...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="graph-view">
      <div className="graph-topbar">
        <span className="graph-title">Network Topology</span>
        <div className="graph-search-wrap">
          <div className="graph-search-box">
            <input
              className="graph-search-input"
              placeholder="Search by hostname, IP, MAC, vendor..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onFocus={() => search && setShowResults(true)}
              onBlur={() => setTimeout(() => setShowResults(false), 200)}
            />
            {search && (
              <button
                className="search-clear"
                onClick={() => {
                  setSearch("");
                  setShowResults(false);
                }}
              >
                x
              </button>
            )}
          </div>
          {showResults && searchResults.length > 0 && (
            <div className="search-dropdown">
              {searchResults.map((d) => (
                <button
                  key={d.id}
                  className="search-result"
                  onMouseDown={() => zoomToDevice(d)}
                >
                  <div className="sr-main">
                    <span className="sr-hostname">{d.hostname}</span>
                    <span className="sr-type">{d.device_type}</span>
                  </div>
                  <div className="sr-detail">
                    {d.ip} {d.mac ? `· ${d.mac}` : ""}{" "}
                    {d.vendor ? `· ${d.vendor}` : ""}
                  </div>
                </button>
              ))}
            </div>
          )}
          {showResults && search && searchResults.length === 0 && (
            <div className="search-dropdown">
              <div className="search-empty">No devices found</div>
            </div>
          )}
        </div>
        <div className="graph-legend">
          <span className="legend-item">
            <span className="legend-dot" style={{ background: "#f59e0b" }} />
            Router
          </span>
          <span className="legend-item">
            <span className="legend-dot" style={{ background: "#10b981" }} />
            Switch
          </span>
          <span className="legend-item">
            <span className="legend-dot" style={{ background: "#3b82f6" }} />
            Server
          </span>
          <span className="legend-item">
            <span className="legend-dot" style={{ background: "#8b5cf6" }} />
            DC
          </span>
          <span className="legend-item">
            <span className="legend-dot" style={{ background: "#64748b" }} />
            Endpoint
          </span>
          <span className="legend-item">
            <span
              className="legend-dot"
              style={{
                background: "#f8f6f2",
                border: "1.5px dashed #c5bfb5",
              }}
            />
            Discovered
          </span>
        </div>
      </div>
      <div className="graph-canvas-wrap">
        <div
          className="graph-container"
          id="neovis-container"
          ref={containerRef}
        />
      </div>
    </div>
  );
}