from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, List, Any


class NetworkBase(BaseModel):
    name: str
    description: Optional[str] = None

class NetworkCreate(NetworkBase):
    pass

class NetworkOut(NetworkBase):
    id: int
    class Config:
        from_attributes = True


class DeviceBase(BaseModel):
    network_id: int = 1
    hostname: str
    ip: str
    mac: Optional[str] = None
    device_type: str
    os_type: str
    manufacturer: Optional[str] = None
    vendor: Optional[str] = None
    vendor_category: Optional[str] = None
    model: Optional[str] = None
    ram_gb: Optional[int] = None
    cpu: Optional[str] = None
    cpu_usage: Optional[float] = None
    uptime: Optional[str] = None
    status: str = "online"
    label: Optional[str] = None
    connection_method: Optional[str] = None
    services: Optional[List[Any]] = None
    open_ports: Optional[List[Any]] = None
    users_connected: int = 0
    last_login: Optional[str] = None
    managed: int = 1

class DeviceCreate(DeviceBase):
    pass

class DeviceOut(DeviceBase):
    id: int
    class Config:
        from_attributes = True


class ConnectionBase(BaseModel):
    source_device_id: int
    target_device_id: int
    connection_type: str = "ethernet"
    port: Optional[str] = None
    bandwidth: Optional[str] = None

class ConnectionCreate(ConnectionBase):
    pass

class ConnectionOut(ConnectionBase):
    id: int
    class Config:
        from_attributes = True


class TopologyOut(BaseModel):
    devices: List[DeviceOut]
    connections: List[ConnectionOut]