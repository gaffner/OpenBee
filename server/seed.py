import random
import json
from database import get_driver, init_db
from mac_vendor import lookup_vendor, lookup_vendor_category

random.seed(42)

VENDOR_MACS = {
    "cisco": ["00:00:0C", "00:16:C7"], "hp": ["00:17:5A", "00:22:64"],
    "dell": ["14:2B:2F", "18:66:DA"], "lenovo": ["48:64:C9", "70:F1:A1"],
    "apple": ["3C:07:54", "A8:60:B6"], "fortinet": ["00:09:24", "70:48:1C"],
    "ubiquiti": ["24:A4:3C", "78:8A:20"], "aruba": ["00:0B:86"],
    "netgear": ["00:14:6C", "A0:21:B7"],
}
ROUTER_MODELS = ["ISR 4321", "FortiGate 60F", "USG Pro 4", "ISR 4431"]
SWITCH_MODELS = ["Catalyst 2960", "ProCurve 2530", "Catalyst 9300", "EX3400"]
SERVER_MODELS = ["PowerEdge R740", "ProLiant DL380", "PowerEdge R640"]
PC_MODELS_WIN = ["ThinkPad T14", "OptiPlex 7090", "EliteDesk 800", "Latitude 5520", "Surface Pro 9", "ThinkCentre M90"]
PC_MODELS_MAC = ["MacBook Air M4", "MacBook Pro 16", "iMac 24"]


def _mac(vendor, idx):
    prefixes = VENDOR_MACS.get(vendor, VENDOR_MACS["dell"])
    prefix = prefixes[idx % len(prefixes)]
    return f"{prefix}:{(idx >> 8) & 0xFF:02X}:{idx & 0xFF:02X}:{random.randint(0,255):02X}"


def _randip(subnet, host):
    return f"{subnet}.{host}"


def _create_network(session, counters, name, desc, n_routers, n_switches,
                    n_pcs, n_servers, n_dcs, n_laptops=0, n_macs=0,
                    managed_ratio=0.7):
    counters["network"] += 1
    net_id = counters["network"]
    session.run(
        "CREATE (n:Network {id: $id, name: $name, description: $desc})",
        id=net_id, name=name, desc=desc,
    )

    devices = []
    subnet = f"10.{random.randint(0,254)}.{random.randint(0,254)}"
    dev_idx = 0

    def _add_device(props):
        nonlocal dev_idx
        counters["device"] += 1
        props["id"] = counters["device"]
        props["network_id"] = net_id
        if props.get("services") is not None:
            props["services"] = json.dumps(props["services"])
        if props.get("open_ports") is not None:
            props["open_ports"] = json.dumps(props["open_ports"])
        session.run(
            "MATCH (n:Network {id: $nid}) "
            "CREATE (d:Device $props)-[:BELONGS_TO]->(n)",
            props=props, nid=net_id,
        )
        devices.append(props)
        dev_idx += 1
        return props

    routers = []
    for i in range(n_routers):
        vk = random.choice(["cisco", "fortinet", "ubiquiti"])
        mac = _mac(vk, dev_idx)
        v = lookup_vendor(mac)
        vc = lookup_vendor_category(v) if v else vk
        d = _add_device(dict(
            hostname=f"RTR-{i+1:02d}", ip=_randip(subnet, i+1), mac=mac,
            device_type="router", os_type="ios",
            manufacturer=v or vk.capitalize(), vendor=v, vendor_category=vc,
            model=random.choice(ROUTER_MODELS), ram_gb=4, cpu="Dual-Core",
            cpu_usage=round(random.uniform(5, 40), 1),
            uptime=f"{random.randint(10,365)} days", status="online",
            managed=1, connection_method="ssh",
            services=[{"name": "NAT", "status": "running"}],
            open_ports=[22, 443], label=None,
            users_connected=0, last_login=None,
        ))
        routers.append(d)

    switches = []
    for i in range(n_switches):
        vk = random.choice(["cisco", "hp", "aruba", "netgear"])
        mac = _mac(vk, dev_idx)
        v = lookup_vendor(mac)
        vc = lookup_vendor_category(v) if v else vk
        managed = 1 if random.random() < managed_ratio else 0
        d = _add_device(dict(
            hostname=f"SW-{i+1:02d}", ip=_randip(subnet, 20 + i), mac=mac,
            device_type="switch", os_type="ios",
            manufacturer=v or vk.capitalize(),
            vendor=v if not managed else None,
            vendor_category=vc if not managed else None,
            model=random.choice(SWITCH_MODELS), ram_gb=2, cpu="ARM 800MHz",
            cpu_usage=round(random.uniform(5, 25), 1),
            uptime=f"{random.randint(10,200)} days", status="online",
            managed=managed, connection_method="ssh",
            services=[{"name": "STP", "status": "running"}],
            open_ports=[22], label=None,
            users_connected=0, last_login=None,
        ))
        switches.append(d)

    dcs = []
    for i in range(n_dcs):
        mac = _mac("dell", dev_idx)
        d = _add_device(dict(
            hostname=f"DC-{i+1:02d}", ip=_randip(subnet, 100 + i), mac=mac,
            device_type="dc", os_type="windows", manufacturer="Dell",
            vendor=None, vendor_category=None,
            model=random.choice(SERVER_MODELS), ram_gb=32, cpu="Intel Xeon",
            cpu_usage=round(random.uniform(10, 45), 1),
            uptime=f"{random.randint(30,365)} days", status="online",
            managed=1, connection_method="winrm",
            services=[{"name": "NTDS", "displayName": "Active Directory", "status": "running"}],
            open_ports=[53, 88, 389, 3389], label=None,
            users_connected=0, last_login=None,
        ))
        dcs.append(d)

    servers = []
    for i in range(n_servers):
        vk = random.choice(["dell", "hp"])
        mac = _mac(vk, dev_idx)
        d = _add_device(dict(
            hostname=f"SRV-{i+1:02d}", ip=_randip(subnet, 110 + i), mac=mac,
            device_type="server",
            os_type=random.choice(["windows", "linux"]),
            manufacturer=vk.upper(), vendor=None, vendor_category=None,
            model=random.choice(SERVER_MODELS),
            ram_gb=random.choice([32, 64, 128]), cpu="Intel Xeon",
            cpu_usage=round(random.uniform(10, 85), 1),
            uptime=f"{random.randint(5,180)} days", status="online",
            managed=1,
            connection_method=random.choice(["winrm", "ssh"]),
            services=[{"name": "HTTP", "displayName": "Web Server", "status": "running"}],
            open_ports=[80, 443, 3389], label=None,
            users_connected=0, last_login=None,
        ))
        servers.append(d)

    pcs = []
    for i in range(n_pcs):
        vk = random.choice(["dell", "hp", "lenovo"])
        mac = _mac(vk, dev_idx)
        managed = 1 if random.random() < managed_ratio else 0
        v = lookup_vendor(mac)
        vc = lookup_vendor_category(v) if v else vk
        d = _add_device(dict(
            hostname=f"PC-{i+1:03d}", ip=_randip(subnet, 150 + i % 100),
            mac=mac, device_type="pc", os_type="windows",
            manufacturer=v or vk.capitalize(),
            vendor=v if not managed else None,
            vendor_category=vc if not managed else None,
            model=random.choice(PC_MODELS_WIN),
            ram_gb=random.choice([8, 16]), cpu="Intel Core i5",
            cpu_usage=round(random.uniform(5, 80), 1),
            uptime=f"{random.randint(0,30)} days",
            status=random.choice(["online"] * 9 + ["offline"]),
            managed=managed, connection_method="winrm",
            users_connected=random.randint(0, 2),
            open_ports=[3389, 5985], label=None, last_login=None,
        ))
        pcs.append(d)

    laptops = []
    for i in range(n_laptops):
        vk = random.choice(["lenovo", "dell", "hp"])
        mac = _mac(vk, dev_idx)
        managed = 1 if random.random() < managed_ratio else 0
        v = lookup_vendor(mac)
        vc = lookup_vendor_category(v) if v else vk
        d = _add_device(dict(
            hostname=f"LT-{i+1:03d}", ip=_randip(subnet, 200 + i % 50),
            mac=mac, device_type="pc", os_type="windows",
            manufacturer=v or vk.capitalize(),
            vendor=v if not managed else None,
            vendor_category=vc if not managed else None,
            model=random.choice(["ThinkPad T14", "Latitude 5520", "EliteBook 840", "Surface Laptop 5"]),
            ram_gb=16, cpu="Intel Core i7",
            cpu_usage=round(random.uniform(10, 65), 1),
            status="online", managed=managed, connection_method="winrm",
            users_connected=1, open_ports=[3389, 5985],
            label=None, last_login=None, uptime=None,
        ))
        laptops.append(d)

    mac_devices = []
    for i in range(n_macs):
        mac = _mac("apple", dev_idx)
        d = _add_device(dict(
            hostname=f"MAC-{i+1:02d}", ip=_randip(subnet, 230 + i), mac=mac,
            device_type="pc", os_type="macos", manufacturer="Apple",
            vendor=None, vendor_category=None,
            model=random.choice(PC_MODELS_MAC),
            ram_gb=random.choice([16, 32, 64]), cpu="Apple M4",
            cpu_usage=round(random.uniform(10, 60), 1),
            status="online", managed=1, connection_method="ssh",
            users_connected=1, open_ports=[22],
            label=None, last_login=None, uptime=None,
        ))
        mac_devices.append(d)

    # Create CONNECTS_TO relationships
    for i, sw in enumerate(switches):
        counters["connection"] += 1
        session.run(
            "MATCH (s:Device {id: $sid}), (t:Device {id: $tid}) "
            "CREATE (s)-[:CONNECTS_TO {id: $cid, connection_type: 'ethernet', "
            "port: $port, bandwidth: '1Gbps'}]->(t)",
            sid=routers[i % len(routers)]["id"], tid=sw["id"],
            cid=counters["connection"], port=f"Gi0/{i+1}",
        )

    for dc in dcs:
        counters["connection"] += 1
        parent = switches[0] if switches else routers[0]
        session.run(
            "MATCH (s:Device {id: $sid}), (t:Device {id: $tid}) "
            "CREATE (s)-[:CONNECTS_TO {id: $cid, connection_type: 'ethernet', "
            "port: null, bandwidth: '1Gbps'}]->(t)",
            sid=parent["id"], tid=dc["id"], cid=counters["connection"],
        )

    for i, srv in enumerate(servers):
        counters["connection"] += 1
        parent = switches[i % max(len(switches), 1)] if switches else routers[0]
        session.run(
            "MATCH (s:Device {id: $sid}), (t:Device {id: $tid}) "
            "CREATE (s)-[:CONNECTS_TO {id: $cid, connection_type: 'ethernet', "
            "port: null, bandwidth: '1Gbps'}]->(t)",
            sid=parent["id"], tid=srv["id"], cid=counters["connection"],
        )

    targets = switches if switches else routers
    for i, ep in enumerate(pcs + laptops + mac_devices):
        counters["connection"] += 1
        ct = "wifi" if random.random() < 0.15 else "ethernet"
        bw = "1Gbps" if ct == "ethernet" else "WiFi 6"
        session.run(
            "MATCH (s:Device {id: $sid}), (t:Device {id: $tid}) "
            "CREATE (s)-[:CONNECTS_TO {id: $cid, connection_type: $ct, "
            "port: null, bandwidth: $bw}]->(t)",
            sid=targets[i % len(targets)]["id"], tid=ep["id"],
            cid=counters["connection"], ct=ct, bw=bw,
        )

    return len(devices)


def seed():
    driver = get_driver()
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")

    init_db()

    counters = {"device": 0, "network": 0, "connection": 0}

    with driver.session() as session:
        # Network 1 is always "Your Network"
        counters["network"] += 1
        session.run(
            "CREATE (n:Network {id: 1, name: 'Your Network', "
            "description: 'Your actual network devices'})"
        )

        configs = [
            ("Small Office", "1 router, 1 switch, 5 desktops", 1, 1, 5, 0, 0, 0, 0),
            ("Home Lab", "Router, 2 servers, 3 PCs, 1 Mac", 1, 1, 3, 2, 0, 0, 1),
            ("Original Demo", "1 router, 2 switches, server, DC, 3 PCs, Mac", 1, 2, 2, 1, 1, 1, 1),
            ("Branch Office", "1 router, 3 switches, 15 PCs, 2 servers", 1, 3, 10, 2, 0, 5, 0),
            ("School Campus", "2 routers, 5 switches, 30 PCs, 3 servers", 2, 5, 20, 3, 0, 8, 2),
            ("Small Enterprise", "2 routers, 8 switches, 50 PCs, 5 servers, 2 DCs", 2, 8, 30, 5, 2, 15, 3),
            ("Multi-Floor Office", "3 routers, 10 switches, 80 endpoints", 3, 10, 40, 4, 1, 25, 5),
            ("Data Center Core", "2 routers, 15 switches, 4 DCs, 20 servers", 2, 15, 10, 20, 4, 5, 0),
            ("Hospital Network", "5 routers, 20 switches, 150 endpoints", 5, 20, 80, 10, 2, 50, 8),
            ("Mega Enterprise", "10 routers, 50 switches, 500 endpoints", 10, 50, 250, 30, 5, 150, 15),
        ]
        for name, desc, r, s, pc, srv, dc, lt, mac_count in configs:
            total = _create_network(
                session, counters, name, desc, r, s, pc, srv, dc, lt, mac_count,
            )
            print(f"  {name:25s} - {total} devices")

        # Sync counter nodes with final values
        for name, value in counters.items():
            session.run(
                "MATCH (c:_Counter {name: $name}) SET c.value = $value",
                name=name, value=value,
            )

    print(f"\nSeeded {len(configs)} networks.")


if __name__ == "__main__":
    seed()