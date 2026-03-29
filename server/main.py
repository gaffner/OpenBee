from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
from sqlalchemy.orm import Session
import json

from database import get_db, engine, Base
from models import Device, Connection, Network
from schemas import DeviceOut, DeviceCreate, ConnectionOut, TopologyOut, NetworkOut
from mac_vendor import lookup_vendor, lookup_vendor_category
from ai_agent import AIAgent
from connectors.ssh_connector import SSHConnector
from connectors.winrm_connector import WinRMConnector
import cred_store

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


# ── Credential Store ─────────────────────────────────────────────────────


@app.post("/api/devices/{device_id}/credentials")
def store_credentials(
    device_id: int,
    username: str = Query(...),
    password: str = Query(...),
    protocol: str = Query(...),
    use_ssl: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Store credentials for a device so AI chat can connect to it."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    cred_store.store(device_id, device.ip, username, password, protocol, use_ssl)
    return {"status": "ok", "device_id": device_id}


# ── AI Chat (SSE) ────────────────────────────────────────────────────────

ai_agent = AIAgent()


@app.get("/api/devices/{device_id}/chat")
def ai_chat_stream(
    device_id: int,
    prompt: str = Query(...),
    db: Session = Depends(get_db),
):
    """SSE endpoint — streams AI agent steps for a device."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        def _err():
            yield f"data: {json.dumps({'type': 'error', 'text': 'Device not found'})}\n\n"
        return StreamingResponse(_err(), media_type="text/event-stream")

    creds = cred_store.get(device_id)
    if not creds:
        def _err():
            yield f"data: {json.dumps({'type': 'error', 'text': 'No credentials stored for this device. Please provide credentials first.'})}\n\n"
        return StreamingResponse(_err(), media_type="text/event-stream")

    host_info = {
        "hostname": device.hostname,
        "os_name": device.os_type,
        "protocol": creds["protocol"],
    }

    def _stream():
        connector = None
        try:
            if creds["protocol"] == "ssh":
                connector = SSHConnector(creds["host"], creds["username"], creds["password"])
            else:
                connector = WinRMConnector(creds["host"], creds["username"], creds["password"], use_ssl=creds.get("use_ssl", False))

            for step in ai_agent.run(prompt, connector, host_info, session_id=device_id):
                yield f"data: {json.dumps(step)}\n\n"

        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'text': str(exc)})}\n\n"
        finally:
            if connector and creds["protocol"] == "ssh":
                connector.close()

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )