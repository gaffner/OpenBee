"""Parse the output of `ipconfig /all` into structured interface data."""

import re


def parse_ipconfig(output: str) -> list[dict]:
    """
    Returns a list of dicts, one per adapter:
    {
        "name", "description", "mac_address", "dhcp_enabled",
        "ip_address", "subnet_mask", "default_gateway",
        "dns_servers", "dhcp_server", "lease_obtained", "lease_expires",
        "ipv6_address", "connection_dns_suffix", "media_state"
    }
    """
    interfaces = []

    # Split into adapter blocks.  Each starts with a line like:
    #   "Ethernet adapter Ethernet0:" or "Wireless LAN adapter Wi-Fi:"
    adapter_pattern = re.compile(
        r"^(\S.*adapter\s+.+):\s*$", re.MULTILINE | re.IGNORECASE
    )
    splits = adapter_pattern.split(output)

    # splits[0] is the header (Windows IP Configuration…), then pairs of (name, block)
    for i in range(1, len(splits), 2):
        adapter_name = splits[i].strip()
        block = splits[i + 1] if i + 1 < len(splits) else ""

        iface = _parse_block(block)
        iface["name"] = adapter_name
        interfaces.append(iface)

    return interfaces


def _val(block: str, key: str) -> str | None:
    """Extract a single value line like '   Key . . . : Value'."""
    m = re.search(
        rf"^\s+{re.escape(key)}\s*[\.\s]*:\s*(.+)$", block, re.MULTILINE | re.IGNORECASE
    )
    return m.group(1).strip() if m else None


def _parse_block(block: str) -> dict:
    media_state = _val(block, "Media State")
    description = _val(block, "Description")
    mac = _val(block, "Physical Address")
    dhcp_str = _val(block, "DHCP Enabled")
    dns_suffix = _val(block, "Connection-specific DNS Suffix")

    # IPv4 address may have "(Preferred)" appended
    ipv4_raw = _val(block, "IPv4 Address") or _val(block, "IP Address")
    ipv4 = re.sub(r"\(.*\)", "", ipv4_raw).strip() if ipv4_raw else None

    subnet = _val(block, "Subnet Mask")
    gateway = _val(block, "Default Gateway")
    dhcp_server = _val(block, "DHCP Server")
    lease_obtained = _val(block, "Lease Obtained")
    lease_expires = _val(block, "Lease Expires")

    # DNS servers can span multiple lines
    dns_servers = _parse_multiline(block, "DNS Servers")

    # IPv6
    ipv6_raw = _val(block, "Link-local IPv6 Address")
    ipv6 = re.sub(r"%.*", "", ipv6_raw).strip() if ipv6_raw else None

    # Normalize MAC from XX-XX-XX-XX-XX-XX to XX:XX:XX:XX:XX:XX
    if mac:
        mac = mac.replace("-", ":").upper()

    return {
        "description": description,
        "mac_address": mac,
        "dhcp_enabled": dhcp_str.lower().startswith("y") if dhcp_str else None,
        "ip_address": ipv4,
        "subnet_mask": subnet,
        "default_gateway": gateway,
        "dns_servers": dns_servers,
        "dhcp_server": dhcp_server,
        "lease_obtained": lease_obtained,
        "lease_expires": lease_expires,
        "ipv6_address": ipv6,
        "connection_dns_suffix": dns_suffix,
        "media_state": media_state,
    }


def _parse_multiline(block: str, key: str) -> str | None:
    """Parse a key whose value may continue on subsequent indented lines."""
    pattern = re.compile(
        rf"^\s+{re.escape(key)}\s*[\.\s]*:\s*(.+)$", re.MULTILINE | re.IGNORECASE
    )
    m = pattern.search(block)
    if not m:
        return None

    values = [m.group(1).strip()]
    # Grab continuation lines (lines that are more-indented with just an IP/value)
    rest = block[m.end():]
    for line in rest.splitlines():
        # Continuation lines are indented and contain just a value (no dots/colon key)
        if re.match(r"^\s{30,}[\d\w]", line) and ":" not in line and "." not in line.strip()[:3]:
            values.append(line.strip())
        elif re.match(r"^\s{30,}\d", line):
            values.append(line.strip())
        else:
            break

    return ", ".join(values)
