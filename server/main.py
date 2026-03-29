from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import get_db, engine, Base
from models import Device, Connection, Network
from schemas import DeviceOut, DeviceCreate, ConnectionOut, TopologyOut, NetworkOut
from mac_vendor import lookup_vendor, lookup_vendor_category

app = FastAPI(title="Discovery & Manage", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/api/networks", response_model=list[NetworkOut])
def list_networks(db: Session = Depends(get_db)):
    return db.query(Network).all()


@app.get("/api/devices", response_model=list[DeviceOut])
def list_devices(db: Session = Depends(get_db)):
    return db.query(Device).all()


@app.get("/api/devices/{device_id}", response_model=DeviceOut)
def get_device(device_id: int, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@app.post("/api/devices", response_model=DeviceOut)
def create_device(payload: DeviceCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    mac = data.get("mac")
    if mac and not data.get("vendor") and data.get("managed") == 0:
        vendor = lookup_vendor(mac)
        if vendor:
            data["vendor"] = vendor
            data["vendor_category"] = lookup_vendor_category(vendor)
    device = Device(**data)
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


@app.get("/api/connections", response_model=list[ConnectionOut])
def list_connections(db: Session = Depends(get_db)):
    return db.query(Connection).all()


@app.get("/api/topology", response_model=TopologyOut)
def get_topology(network_id: int = 1, db: Session = Depends(get_db)):
    device_ids_q = db.query(Device.id).filter(Device.network_id == network_id)
    device_ids = [r[0] for r in device_ids_q.all()]
    devices = db.query(Device).filter(Device.network_id == network_id).all()
    connections = db.query(Connection).filter(
        Connection.source_device_id.in_(device_ids)
    ).all()
    return TopologyOut(devices=devices, connections=connections)


@app.get("/api/mac-lookup/{mac}")
def mac_lookup(mac: str):
    vendor = lookup_vendor(mac)
    category = lookup_vendor_category(vendor) if vendor else "unknown"
    return {"mac": mac, "vendor": vendor, "vendor_category": category}