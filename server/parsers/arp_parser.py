"""Parse the output of `arp -a` into structured entries."""

import re


def parse_arp(output: str) -> list[dict]:
    """
    Returns a list of dicts:
    { "interface_ip", "ip_address", "mac_address", "entry_type" }
    """
    entries = []
    current_interface = None

    # Interface header: "Interface: 10.0.0.5 --- 0x4"
    iface_re = re.compile(r"Interface:\s+([\d.]+)\s+---")
    # Entry line:  "  10.0.0.1            00-1a-2b-3c-4d-5e     dynamic"
    entry_re = re.compile(
        r"^\s+([\d.]+)\s+([0-9a-fA-F-]{17})\s+(\S+)", re.MULTILINE
    )

    for line in output.splitlines():
        m_iface = iface_re.search(line)
        if m_iface:
            current_interface = m_iface.group(1)
            continue

        m_entry = entry_re.match(line)
        if m_entry:
            mac = m_entry.group(2).replace("-", ":").upper()
            # Skip broadcast / multicast MACs
            if mac.startswith("FF:FF:FF") or mac.startswith("01:00:5E"):
                continue
            entries.append({
                "interface_ip": current_interface,
                "ip_address": m_entry.group(1),
                "mac_address": mac,
                "entry_type": m_entry.group(3).lower(),
            })

    return entries
