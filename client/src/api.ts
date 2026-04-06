import type { Topology, Device, Network, Neo4jConfig } from "./types";

const BASE = "/api";

export async function fetchNeo4jConfig(): Promise<Neo4jConfig> {
  const res = await fetch(`${BASE}/neo4j-config`);
  if (!res.ok) throw new Error("Failed to fetch Neo4j config");
  return res.json();
}

export async function fetchNetworks(): Promise<Network[]> {
  const res = await fetch(`${BASE}/networks`);
  if (!res.ok) throw new Error("Failed to fetch networks");
  return res.json();
}

export async function fetchTopology(networkId: number = 1): Promise<Topology> {
  const res = await fetch(`${BASE}/topology?network_id=${networkId}`);
  if (!res.ok) throw new Error("Failed to fetch topology");
  return res.json();
}

export async function fetchDevice(id: number): Promise<Device> {
  const res = await fetch(`${BASE}/devices/${id}`);
  if (!res.ok) throw new Error("Failed to fetch device");
  return res.json();
}

export async function createDevice(device: Record<string, any>): Promise<Device> {
  const res = await fetch(`${BASE}/devices`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(device),
  });
  if (!res.ok) throw new Error("Failed to create device");
  return res.json();
}

export async function hasCredentials(deviceId: number): Promise<boolean> {
  const res = await fetch(`${BASE}/devices/${deviceId}/has-credentials`);
  if (!res.ok) return false;
  const data = await res.json();
  return data.has_credentials;
}