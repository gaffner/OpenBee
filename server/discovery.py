"""
Network discovery — connects to a device and discovers neighboring
devices via ARP tables, routing tables, DNS/DHCP config, and system info.
Returns lists of discovered neighbor dicts ready for Neo4j insertion.
"""

import re
import logging

logger = logging.getLogger(__name__)

# ── Discovery commands per OS ────────────────────────────────────────────

LINUX_COMMANDS = {
    "arp": "ip neigh show 2>/dev/null || arp -an 2>/dev/null",
    "routes": "ip route show 2>/dev/null || route -n 2>/dev/null",
    "dns": "cat /etc/resolv.conf 2>/dev/null",
    "sysinfo": (
        "echo HOSTNAME=$(hostname);"
        "echo OS=$(uname -s);"
        "echo KERNEL=$(uname -r);"
        "echo ARCH=$(uname -m);"
        "echo RAM_KB=$(grep MemTotal /proc/meminfo 2>/dev/null | awk '{print $2}');"
        "echo CPU=$(grep -m1 'model name' /proc/cpuinfo 2>/dev/null | cut -d: -f2 | xargs);"
        "echo UPTIME=$(uptime -p 2>/dev/null || uptime)"
    ),
    "interfaces": "ip -o addr show 2>/dev/null || ifconfig 2>/dev/null",
    "listening": "ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null",
}

MACOS_COMMANDS = {
    "arp": "arp -an 2>/dev/null",
    "routes": "netstat -rn 2>/dev/null",
    "dns": "cat /etc/resolv.conf 2>/dev/null",
    "sysinfo": (
        "echo HOSTNAME=$(hostname);"
        "echo OS=$(uname -s);"
        "echo KERNEL=$(uname -r);"
        "echo ARCH=$(uname -m);"
        "echo RAM_KB=$(sysctl -n hw.memsize 2>/dev/null | awk '{print int($1/1024)}');"
        "echo CPU=$(sysctl -n machdep.cpu.brand_string 2>/dev/null);"
        "echo UPTIME=$(uptime)"
    ),
    "interfaces": "ifconfig 2>/dev/null",
    "listening": "lsof -iTCP -sTCP:LISTEN -nP 2>/dev/null",
}

WINDOWS_COMMANDS = {
    "arp": "arp -a",
    "routes": "route print",
    "dns": "ipconfig /all",
    "sysinfo": (
        'powershell -Command "'
        "Write-Output HOSTNAME=$env:COMPUTERNAME;"
        "Write-Output OS=$((Get-CimInstance Win32_OperatingSystem).Caption);"
        "Write-Output RAM_KB=$([math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1024));"
        "Write-Output CPU=$((Get-CimInstance Win32_Processor).Name);"
        "Write-Output UPTIME=$((Get-CimInstance Win32_OperatingSystem).LastBootUpTime);"
        "Write-Output DOMAIN=$((Get-CimInstance Win32_ComputerSystem).Domain)"
        '"'
    ),
    "interfaces": 'powershell -Command "Get-NetIPAddress | Format-List"',
    "listening": "netstat -ano | findstr LISTENING",
}


def _get_commands(os_type: str) -> dict:
    if os_type in ("linux",):
        return LINUX_COMMANDS
    if os_type in ("macos",):
        return MACOS_COMMANDS
    if os_type in ("windows",):
        return WINDOWS_COMMANDS
    return LINUX_COMMANDS


# ── Parsers ──────────────────────────────────────────────────────────────

def _parse_arp(output: str, own_ip: str) -> list[dict]:
    """Parse ARP output into list of {ip, mac} dicts."""
    neighbors = []
    seen_ips = set()
    for line in output.splitlines():
        # Linux: 10.0.0.1 dev eth0 lladdr aa:bb:cc:dd:ee:ff REACHABLE
        # macOS/BSD: ? (10.0.0.1) at aa:bb:cc:dd:ee:ff on en0
        # Windows: 10.0.0.1    aa-bb-cc-dd-ee-ff    dynamic
        ip_match = re.findall(
            r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line
        )
        mac_match = re.findall(
            r'([0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}'
            r'[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2})',
            line,
        )
        for ip in ip_match:
            if ip == own_ip or ip in seen_ips:
                continue
            if ip.startswith("255.") or ip == "0.0.0.0" or ip.endswith(".255"):
                continue
            mac = mac_match[0].replace("-", ":").upper() if mac_match else None
            if mac and mac in ("FF:FF:FF:FF:FF:FF", "00:00:00:00:00:00"):
                continue
            neighbors.append({"ip": ip, "mac": mac})
            seen_ips.add(ip)
    return neighbors


def _parse_gateways(output: str) -> list[str]:
    """Extract default gateway IPs from route output."""
    gateways = set()
    for line in output.splitlines():
        lower = line.lower()
        if "default" in lower or "0.0.0.0" in line:
            ips = re.findall(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
            for ip in ips:
                if ip not in ("0.0.0.0", "255.255.255.255", "255.255.255.0"):
                    gateways.add(ip)
    return list(gateways)


def _parse_dns(output: str) -> list[str]:
    """Extract DNS server IPs from config output."""
    dns_servers = set()
    for line in output.splitlines():
        if "nameserver" in line.lower() or "dns" in line.lower():
            ips = re.findall(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
            for ip in ips:
                if ip not in ("0.0.0.0", "127.0.0.1", "255.255.255.255"):
                    dns_servers.add(ip)
    return list(dns_servers)


def _parse_sysinfo(output: str) -> dict:
    """Parse system info key=value output."""
    info = {}
    for line in output.splitlines():
        if "=" in line:
            key, _, val = line.partition("=")
            info[key.strip()] = val.strip()
    return info


def _parse_listening_ports(output: str) -> list[int]:
    """Extract unique listening port numbers."""
    ports = set()
    for line in output.splitlines():
        # Match :PORT patterns
        matches = re.findall(r'[:\s](\d{1,5})\s', line)
        for m in matches:
            port = int(m)
            if 1 <= port <= 65535:
                ports.add(port)
    return sorted(ports)[:20]  # cap at 20


# ── Main discovery function ──────────────────────────────────────────────

def run_discovery(connector, os_type: str, device_ip: str) -> dict:
    """
    Run discovery commands on a remote device.
    Returns:
        {
            "sysinfo": {...},
            "neighbors": [{ip, mac, device_type}, ...],
            "gateways": [ip, ...],
            "dns_servers": [ip, ...],
            "listening_ports": [int, ...],
        }
    """
    commands = _get_commands(os_type)
    results = {}

    for name, cmd in commands.items():
        try:
            result = connector.run_cmd(cmd)
            results[name] = result.get("stdout", "")
        except Exception as e:
            logger.warning(f"Discovery command '{name}' failed: {e}")
            results[name] = ""

    # Parse results
    sysinfo = _parse_sysinfo(results.get("sysinfo", ""))
    arp_neighbors = _parse_arp(results.get("arp", ""), device_ip)
    gateways = _parse_gateways(results.get("routes", ""))
    dns_servers = _parse_dns(results.get("dns", ""))
    listening_ports = _parse_listening_ports(results.get("listening", ""))

    # Classify neighbors
    gateway_ips = set(gateways)
    dns_ips = set(dns_servers)

    for neighbor in arp_neighbors:
        ip = neighbor["ip"]
        if ip in gateway_ips:
            neighbor["device_type"] = "router"
        elif ip in dns_ips:
            neighbor["device_type"] = "server"
        else:
            neighbor["device_type"] = "pc"

    # Update sysinfo with parsed data
    if sysinfo.get("RAM_KB"):
        try:
            sysinfo["ram_gb"] = int(int(sysinfo["RAM_KB"]) / 1024 / 1024)
        except (ValueError, TypeError):
            pass

    return {
        "sysinfo": sysinfo,
        "neighbors": arp_neighbors,
        "gateways": gateways,
        "dns_servers": dns_servers,
        "listening_ports": listening_ports,
    }
