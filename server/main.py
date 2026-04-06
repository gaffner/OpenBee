from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
import json

from database import get_driver, init_db, next_id, neo4j_config
from models import node_to_device, node_to_network
from schemas import DeviceOut, DeviceCreate, ConnectionOut, TopologyOut, NetworkOut
from mac_vendor import lookup_vendor, lookup_vendor_category
from ai_agent import AIAgent
from connectors.ssh_connector import SSHConnector
from connectors.winrm_connector import WinRMConnector
import cred_store

app = FastAPI(title="Discovery & Manage", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/api/neo4j-config")
def get_neo4j_config():
    """Return Neo4j connection details for neovis.js frontend."""
    return neo4j_config()


@app.get("/api/networks", response_model=list[NetworkOut])
def list_networks():
    with get_driver().session() as session:
        result = session.run("MATCH (n:Network) RETURN n ORDER BY n.id")
        return [node_to_network(record["n"]) for record in result]


@app.get("/api/devices", response_model=list[DeviceOut])
def list_devices():
    with get_driver().session() as session:
        result = session.run("MATCH (d:Device) RETURN d ORDER BY d.id")
        return [node_to_device(record["d"]) for record in result]


@app.get("/api/devices/{device_id}", response_model=DeviceOut)
def get_device(device_id: int):
    with get_driver().session() as session:
        result = session.run(
            "MATCH (d:Device {id: $id}) RETURN d", id=device_id
        )
        record = result.single()
        if not record:
            raise HTTPException(status_code=404, detail="Device not found")
        return node_to_device(record["d"])


@app.post("/api/devices", response_model=DeviceOut)
def create_device(payload: DeviceCreate):
    data = payload.model_dump(exclude={"cred_username", "cred_password"})
    mac = data.get("mac")
    if mac and not data.get("vendor") and data.get("managed") == 0:
        vendor = lookup_vendor(mac)
        if vendor:
            data["vendor"] = vendor
            data["vendor_category"] = lookup_vendor_category(vendor)
    # Serialize complex types for Neo4j storage
    if data.get("services") is not None:
        data["services"] = json.dumps(data["services"])
    if data.get("open_ports") is not None:
        data["open_ports"] = json.dumps(data["open_ports"])

    def _create(tx):
        device_id = next_id(tx, "device")
        data["id"] = device_id
        tx.run(
            "MATCH (n:Network {id: $nid}) "
            "CREATE (d:Device $props)-[:BELONGS_TO]->(n)",
            props=data,
            nid=data["network_id"],
        )
        return device_id

    with get_driver().session() as session:
        device_id = session.execute_write(_create)

    if payload.cred_username and payload.cred_password:
        protocol = data.get(
            "connection_method",
            "winrm" if data.get("os_type") == "windows" else "ssh",
        )
        cred_store.store(
            device_id, data["ip"],
            payload.cred_username, payload.cred_password, protocol,
        )

    return get_device(device_id)


@app.get("/api/connections", response_model=list[ConnectionOut])
def list_connections():
    with get_driver().session() as session:
        result = session.run(
            "MATCH (s:Device)-[r:CONNECTS_TO]->(t:Device) "
            "RETURN r.id AS id, s.id AS source_device_id, "
            "t.id AS target_device_id, r.connection_type AS connection_type, "
            "r.port AS port, r.bandwidth AS bandwidth "
            "ORDER BY r.id"
        )
        return [dict(record) for record in result]


@app.get("/api/topology", response_model=TopologyOut)
def get_topology(network_id: int = 1):
    with get_driver().session() as session:
        dev_result = session.run(
            "MATCH (d:Device {network_id: $nid}) RETURN d ORDER BY d.id",
            nid=network_id,
        )
        devices = [node_to_device(r["d"]) for r in dev_result]

        conn_result = session.run(
            "MATCH (s:Device {network_id: $nid})-[r:CONNECTS_TO]->(t:Device) "
            "RETURN r.id AS id, s.id AS source_device_id, "
            "t.id AS target_device_id, r.connection_type AS connection_type, "
            "r.port AS port, r.bandwidth AS bandwidth "
            "ORDER BY r.id",
            nid=network_id,
        )
        connections = [dict(r) for r in conn_result]

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
):
    """Store credentials for a device so AI chat can connect to it."""
    with get_driver().session() as session:
        result = session.run(
            "MATCH (d:Device {id: $id}) RETURN d.ip AS ip", id=device_id
        )
        record = result.single()
        if not record:
            raise HTTPException(status_code=404, detail="Device not found")
        cred_store.store(device_id, record["ip"], username, password, protocol, use_ssl)
    return {"status": "ok", "device_id": device_id}


@app.get("/api/devices/{device_id}/has-credentials")
def has_credentials(device_id: int):
    """Check if credentials are stored for a device."""
    return {"has_credentials": cred_store.get(device_id) is not None}


# ── AI Chat (SSE) ────────────────────────────────────────────────────────

ai_agent = AIAgent()


@app.get("/api/devices/{device_id}/chat")
def ai_chat_stream(
    device_id: int,
    prompt: str = Query(...),
):
    """SSE endpoint — streams AI agent steps for a device."""
    with get_driver().session() as session:
        result = session.run(
            "MATCH (d:Device {id: $id}) RETURN d", id=device_id
        )
        record = result.single()

    if not record:
        def _err():
            yield f"data: {json.dumps({'type': 'error', 'text': 'Device not found'})}\n\n"
        return StreamingResponse(_err(), media_type="text/event-stream")

    device = node_to_device(record["d"])
    creds = cred_store.get(device_id)
    if not creds:
        def _err():
            yield f"data: {json.dumps({'type': 'error', 'text': 'No credentials stored for this device. Please provide credentials first.'})}\n\n"
        return StreamingResponse(_err(), media_type="text/event-stream")

    host_info = {
        "hostname": device["hostname"],
        "os_name": device["os_type"],
        "protocol": creds["protocol"],
    }

    def _stream():
        connector = None
        try:
            if creds["protocol"] == "ssh":
                connector = SSHConnector(creds["host"], creds["username"], creds["password"])
            else:
                connector = WinRMConnector(
                    creds["host"], creds["username"], creds["password"],
                    use_ssl=creds.get("use_ssl", False),
                )

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