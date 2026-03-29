"""Parse Linux `ip addr` output into structured interface data."""

import re


def parse_ip_addr(output: str) -> list[dict]:
    """
    Returns a list of dicts, one per interface:
    {
        "name", "mac_address", "ip_address", "subnet_mask",
        "ipv6_address", "media_state", "description"
    }
    """
    interfaces = []

    # Split on interface headers: "2: eth0: <BROADCAST,..."
    iface_re = re.compile(r"^\d+:\s+(\S+?)(?:@\S+)?:\s+<(.+?)>", re.MULTILINE)
    blocks = iface_re.split(output)

    # blocks: [preamble, name1, flags1, block1, name2, flags2, block2, ...]
    for i in range(1, len(blocks), 3):
        name = blocks[i]
        flags = blocks[i + 1] if i + 1 < len(blocks) else ""
        block = blocks[i + 2] if i + 2 < len(blocks) else ""

        # Skip loopback
        if name == "lo":
            continue

        mac = None
        m = re.search(r"link/ether\s+([0-9a-fA-F:]{17})", block)
        if m:
            mac = m.group(1).upper()

        ipv4 = None
        subnet = None
        m = re.search(r"inet\s+([\d.]+)/(\d+)", block)
        if m:
            ipv4 = m.group(1)
            prefix = int(m.group(2))
            # Convert CIDR prefix to dotted mask
            mask_int = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
            subnet = f"{(mask_int >> 24) & 0xFF}.{(mask_int >> 16) & 0xFF}.{(mask_int >> 8) & 0xFF}.{mask_int & 0xFF}"

        ipv6 = None
        m = re.search(r"inet6\s+([0-9a-fA-F:]+)/\d+\s+scope\s+(?:global|link)", block)
        if m:
            ipv6 = m.group(1)

        # State from flags
        state = None
        if "NO-CARRIER" in flags or "DOWN" in flags:
            state = "DOWN"
        elif "UP" in flags and "LOWER_UP" in flags:
            state = "UP"

        interfaces.append({
            "name": name,
            "description": name,
            "mac_address": mac,
            "ip_address": ipv4,
            "subnet_mask": subnet,
            "ipv6_address": ipv6,
            "media_state": state,
            "dhcp_enabled": None,
            "default_gateway": None,
            "dns_servers": None,
            "dhcp_server": None,
            "lease_obtained": None,
            "lease_expires": None,
            "connection_dns_suffix": None,
        })

    return interfaces
