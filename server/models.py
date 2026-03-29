from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func

from database import Base


class Network(Base):
    __tablename__ = "networks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    network_id = Column(Integer, ForeignKey("networks.id"), nullable=False)
    hostname = Column(String, nullable=False)
    ip = Column(String, nullable=False)
    mac = Column(String, nullable=True)
    device_type = Column(String, nullable=False)
    os_type = Column(String, nullable=False)
    manufacturer = Column(String, nullable=True)
    vendor = Column(String, nullable=True)
    vendor_category = Column(String, nullable=True)
    model = Column(String, nullable=True)
    ram_gb = Column(Integer, nullable=True)
    cpu = Column(String, nullable=True)
    cpu_usage = Column(Float, nullable=True)
    uptime = Column(String, nullable=True)
    status = Column(String, default="online")
    label = Column(String, nullable=True)
    connection_method = Column(String, nullable=True)
    services = Column(JSON, nullable=True)
    open_ports = Column(JSON, nullable=True)
    users_connected = Column(Integer, default=0)
    last_login = Column(String, nullable=True)
    managed = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())


class Connection(Base):
    __tablename__ = "connections"

    id = Column(Integer, primary_key=True, index=True)
    source_device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    target_device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    connection_type = Column(String, default="ethernet")
    port = Column(String, nullable=True)
    bandwidth = Column(String, nullable=True)