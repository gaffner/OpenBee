"""
Integrated scanner — connects to a remote host, runs discovery commands,
parses the output, and creates/updates a Device in the main DB.
Yields SSE events for live progress streaming.
"""

import json
import re
from connectors.winrm_connector import WinRMConnector
from connectors.ssh_connector import SSHConnector
from parsers.ipconfig_parser import parse_ipconfig
from parsers.arp_parser import parse_arp
from parsers.netbios_parser import parse_nbtstat
from parsers.systeminfo_parser import parse_systeminfo
from parsers.ip_addr_parser import parse_ip_addr
from parsers.ip_neigh_parser import parse_ip_neigh
from parsers.linux_info_parser import parse_linux_info
from parsers.linux_network_parser import parse_ip_route, parse_resolv_conf
from parsers.netstat_parser import parse_netstat_with_tasklist
from parsers.ss_parser import parse_ss
import cred_store

_IPV4_RE = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")


def _is_valid_ipv4(s: str | None) -> bool:
    """Check if a string is a valid IPv4 address (not IPv6, not junk)."""
    return bool(s and _IPV4_RE.match(s.strip()))

WINRM_COMMANDS = [
    ("cmd", "ipconfig /all"),
    ("cmd", "arp -a"),
    ("cmd", "nbtstat -n"),
    ("cmd", "systeminfo"),
    ("cmd", "netstat -ano"),
    ("cmd", "tasklist /FO CSV"),
]

SSH_COMMANDS = [
    ("sh", "ip addr"),
    ("sh", "ip neigh"),
    ("sh", "ip route"),
    ("sh", "cat /etc/resolv.conf"),
    ("sh", "hostnamectl"),
    ("sh", "cat /proc/meminfo"),
    ("sh", "ss -tlnp"),
]


def _evt(step: str, status: str, output: str = "", error: str = "", **extra) -> str:
    payload = {"step": step, "status": status, **extra}
    if output:
        payload["output"] = output
    if error:
        payload["error"] = error
    return f"data: {json.dumps(payload)}\n\n"


def scan_and_create_device(
    host: str, username: str, password: str,
    protocol: str, device_type: str, label: str,
    network_id: int = 1, use_ssl: bool = False,
):
    """
    Generator that yields SSE events as the scan progresses.
    On success, creates a Device in the main DB and yields device_id.
    """
    is_ssh = protocol == "ssh"
    commands = SSH_COMMANDS if is_ssh else WINRM_COMMANDS
    proto_label = "SSH" if is_ssh else "WinRM"

    # ── Connect ──────────────────────────────────────────────────────
    yield _evt("connect", "running", output=f"Connecting to {host} via {proto_label}...")
    connector = None
    try:
        if is_ssh:
            connector = SSHConnector(host, username, password)
        else:
            connector = WinRMConnector(host, username, password, use_ssl=use_ssl)
        test = connector.run_cmd("hostname")
        if test["exit_code"] != 0:
            raise RuntimeError(test["stderr"] or "hostname command failed")
        yield _evt("connect", "success", output=f"Connected — hostname: {test['stdout'].strip()}")
    except Exception as exc:
        if connector and is_ssh:
            connector.close()
        yield _evt("connect", "error", error=str(exc))
        yield _evt("done", "error")
        return

    # ── Execute commands ─────────────────────────────────────────────
    raw_results = {}
    for shell, cmd in commands:
        step_key = cmd.replace(" ", "_").replace("/", "").replace(".", "")
        yield _evt(step_key, "running", output=f"Executing {cmd}...")
        try:
            result = connector.run_cmd(cmd)
            raw_results[cmd] = result
            if result["exit_code"] != 0:
                yield _evt(step_key, "error", output=result["stdout"],
                           error=result["stderr"] or f"Exit code {result['exit_code']}")
            else:
                yield _evt(step_key, "success", output=result["stdout"])
        except Exception as exc:
            yield _evt(step_key, "error", error=str(exc))

    # ── Parse ────────────────────────────────────────────────────────
    yield _evt("parse", "running", output="Parsing collected data...")
    try:
        if is_ssh:
            info, interfaces, neighbors, services, infra_devices = _parse_ssh(raw_results)
        else:
            info, interfaces, neighbors, services, infra_devices = _parse_winrm(raw_results)

        # Map os_type
        os_type = "linux" if is_ssh else "windows"
        os_name = info.get("os_name") or ""
        if "mac" in os_name.lower() or "darwin" in os_name.lower():
            os_type = "macos"

        # Get active interface info
        active_iface = next((i for i in interfaces if i.get("ip_address")), {})
        mac = active_iface.get("mac_address")
        gateway = active_iface.get("default_gateway")

        # Collect open ports
        open_ports = sorted(set(s["port"] for s in services))

        # Build services list for the Device model
        svc_list = [
            {"name": s["process_name"] or f"port-{s['port']}",
             "displayName": f"{s['process_name'] or '?'} (:{s['port']})",
             "status": "running"}
            for s in services
        ]

        summary = (
            f"Host: {info.get('hostname', '—')}\n"
            f"OS: {os_name or '—'}\n"
            f"Interfaces: {len(interfaces)}\n"
            f"Neighbors: {len(neighbors)}\n"
            f"Services: {len(services)}"
        )
        yield _evt("parse", "success", output=summary)

        # ── Create device in DB ──────────────────────────────────────
        yield _evt("save", "running", output="Saving device to database...")
        from database import SessionLocal
        from models import Device, Connection
        from mac_vendor import lookup_vendor, lookup_vendor_category
        db = SessionLocal()
        try:
            device = Device(
                network_id=network_id,
                hostname=info.get("hostname") or host,
                ip=host,
                mac=mac,
                device_type=device_type,
                os_type=os_type,
                manufacturer=info.get("system_manufacturer"),
                model=info.get("system_model"),
                ram_gb=_parse_ram_gb(info.get("total_physical_memory")),
                status="online",
                label=label or None,
                connection_method=protocol.lower(),
                services=svc_list if svc_list else None,
                open_ports=open_ports if open_ports else None,
                managed=1,
            )
            db.add(device)
            db.commit()
            db.refresh(device)
            device_id = device.id

            # Store creds for AI chat
            cred_store.store(device_id, host, username, password, protocol, use_ssl)

            # ── Create unmanaged neighbor devices from ARP/neighbor scan ──
            neighbor_count = 0

            # Helper: get or create an unmanaged device by IP
            def _get_or_create(ip, mac=None, dev_type="pc", hostname=None, label=None):
                nonlocal neighbor_count
                if not ip or ip == host or not _is_valid_ipv4(ip):
                    return None
                existing = db.query(Device).filter(
                    Device.ip == ip, Device.network_id == network_id
                ).first()
                if existing:
                    # Ensure connection exists
                    if not db.query(Connection).filter(
                        Connection.source_device_id == device_id,
                        Connection.target_device_id == existing.id
                    ).first():
                        db.add(Connection(
                            source_device_id=device_id,
                            target_device_id=existing.id,
                            connection_type="ethernet",
                        ))
                    return existing

                vendor = lookup_vendor(mac) if mac else None
                vendor_cat = lookup_vendor_category(vendor) if vendor else None
                dev = Device(
                    network_id=network_id,
                    hostname=hostname or ip,
                    ip=ip, mac=mac,
                    device_type=dev_type,
                    os_type="other",
                    vendor=vendor, vendor_category=vendor_cat,
                    status="online", managed=0,
                    label=label,
                )
                db.add(dev)
                db.commit()
                db.refresh(dev)
                neighbor_count += 1
                db.add(Connection(
                    source_device_id=device_id,
                    target_device_id=dev.id,
                    connection_type="ethernet",
                ))
                return dev

            # Infrastructure devices (gateways, DNS, DHCP)
            for infra in infra_devices:
                _get_or_create(
                    ip=infra["ip"],
                    dev_type=infra.get("device_type", "router"),
                    hostname=infra.get("hostname"),
                    label=infra.get("label"),
                )

            # ARP / neighbor table
            for neigh in neighbors:
                _get_or_create(
                    ip=neigh.get("ip_address"),
                    mac=neigh.get("mac_address"),
                )

            db.commit()
            db.close()

            save_msg = f"Device saved (ID: {device_id})"
            if neighbor_count > 0:
                save_msg += f", {neighbor_count} neighbors discovered"
            yield _evt("save", "success", output=save_msg)
            yield _evt("done", "success", device_id=device_id)
        except Exception as exc:
            db.close()
            yield _evt("save", "error", error=str(exc))
            yield _evt("done", "error")
    except Exception as exc:
        yield _evt("parse", "error", error=str(exc))
        yield _evt("done", "error")
    finally:
        if connector and is_ssh:
            connector.close()


def _parse_ram_gb(mem_str: str | None) -> int | None:
    if not mem_str:
        return None
    import re
    m = re.search(r"([\d,]+)", mem_str)
    if not m:
        return None
    val = int(m.group(1).replace(",", ""))
    if "GB" in mem_str.upper():
        return val
    if "MB" in mem_str.upper():
        return max(1, val // 1024)
    return val


def _parse_winrm(raw):
    sysinfo = parse_systeminfo(raw.get("systeminfo", {}).get("stdout", ""))
    interfaces = parse_ipconfig(raw.get("ipconfig /all", {}).get("stdout", ""))
    neighbors = parse_arp(raw.get("arp -a", {}).get("stdout", ""))
    netstat_out = raw.get("netstat -ano", {}).get("stdout", "")
    tasklist_out = raw.get("tasklist /FO CSV", {}).get("stdout", "")
    services = parse_netstat_with_tasklist(netstat_out, tasklist_out)

    # Extract infrastructure devices from ipconfig /all
    infra = []
    seen_ips = set()
    for iface in interfaces:
        gw = (iface.get("default_gateway") or "").strip()
        if _is_valid_ipv4(gw) and gw not in seen_ips:
            seen_ips.add(gw)
            infra.append({"ip": gw, "device_type": "router", "label": "Gateway", "hostname": f"gateway-{gw}"})
        dhcp = (iface.get("dhcp_server") or "").strip()
        if _is_valid_ipv4(dhcp) and dhcp not in seen_ips:
            seen_ips.add(dhcp)
            infra.append({"ip": dhcp, "device_type": "server", "label": "DHCP Server", "hostname": f"dhcp-{dhcp}"})
        dns_str = iface.get("dns_servers") or ""
        for dns_ip in [s.strip() for s in dns_str.split(",") if s.strip()]:
            if _is_valid_ipv4(dns_ip) and dns_ip not in seen_ips:
                seen_ips.add(dns_ip)
                infra.append({"ip": dns_ip, "device_type": "server", "label": "DNS Server", "hostname": f"dns-{dns_ip}"})

    # Parse nbtstat -n for NetBIOS names (enriches the scanned host, not separate devices)
    # nbtstat data is informational — stored on the managed device's label if relevant
    nb_raw = raw.get("nbtstat -n", {}).get("stdout", "")
    nb_names = parse_nbtstat(nb_raw)
    if nb_names:
        # Use the first UNIQUE name as hostname hint
        for nb in nb_names:
            if "UNIQUE" in (nb.get("nb_type") or ""):
                if not sysinfo.get("hostname"):
                    sysinfo["hostname"] = nb["name"]
                break

    return sysinfo, interfaces, neighbors, services, infra


def _parse_ssh(raw):
    from parsers.linux_info_parser import parse_linux_info
    info = parse_linux_info(
        raw.get("hostnamectl", {}).get("stdout", ""),
        raw.get("cat /proc/meminfo", {}).get("stdout", ""),
    )
    interfaces = parse_ip_addr(raw.get("ip addr", {}).get("stdout", ""))
    neighbors = parse_ip_neigh(raw.get("ip neigh", {}).get("stdout", ""))
    services = parse_ss(raw.get("ss -tlnp", {}).get("stdout", ""))

    # Extract infrastructure from ip route + resolv.conf
    infra = []
    seen_ips = set()

    gw = parse_ip_route(raw.get("ip route", {}).get("stdout", ""))
    if gw and gw not in seen_ips:
        seen_ips.add(gw)
        infra.append({"ip": gw, "device_type": "router", "label": "Gateway", "hostname": f"gateway-{gw}"})

    dns_list = parse_resolv_conf(raw.get("cat /etc/resolv.conf", {}).get("stdout", ""))
    for dns_ip in dns_list:
        if dns_ip not in seen_ips:
            seen_ips.add(dns_ip)
            infra.append({"ip": dns_ip, "device_type": "server", "label": "DNS Server", "hostname": f"dns-{dns_ip}"})

    return info, interfaces, neighbors, services, infra
