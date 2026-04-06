export interface Neo4jConfig {
  uri: string;
  user: string;
  password: string;
}

export interface DeviceService {
  name: string;
  displayName?: string;
  status: string;
}

export interface Network {
  id: number;
  name: string;
  description: string | null;
}

export interface Device {
  id: number;
  network_id: number;
  hostname: string;
  ip: string;
  mac: string | null;
  device_type: string;
  os_type: string;
  manufacturer: string | null;
  vendor: string | null;
  vendor_category: string | null;
  model: string | null;
  ram_gb: number | null;
  cpu: string | null;
  cpu_usage: number | null;
  uptime: string | null;
  status: string;
  label: string | null;
  connection_method: string | null;
  services: DeviceService[] | null;
  open_ports: number[] | null;
  users_connected: number;
  last_login: string | null;
  managed: number;
}

export interface Connection {
  id: number;
  source_device_id: number;
  target_device_id: number;
  connection_type: string;
  port: string | null;
  bandwidth: string | null;
}

export interface Topology {
  devices: Device[];
  connections: Connection[];
}