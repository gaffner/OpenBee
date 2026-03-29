"""Parse Linux `ip neigh` output into structured ARP-like entries."""

import re


def parse_ip_neigh(output: str) -> list[dict]:
    """
    Returns a list of dicts:
    { "interface_ip" (None for Linux), "ip_address", "mac_address", "entry_type" }

    Typical line:
        192.168.1.1 dev eth0 lladdr aa:bb:cc:dd:ee:ff REACHABLE
        10.0.0.2 dev eth0 lladdr 00:11:22:33:44:55 STALE
        fe80::1 dev eth0 lladdr aa:bb:cc:dd:ee:ff router REACHABLE
    """
    entries = []
    line_re = re.compile(
        r"^([\d.]+)\s+dev\s+(\S+)\s+lladdr\s+([0-9a-fA-F:]{17})\s+(\S+)",
        re.MULTILINE,
    )

    for m in line_re.finditer(output):
        mac = m.group(3).upper()
        # Skip broadcast/multicast
        if mac.startswith("FF:FF:FF") or mac.startswith("01:00:5E"):
            continue
        entries.append({
            "interface_ip": None,
            "ip_address": m.group(1),
            "mac_address": mac,
            "entry_type": m.group(4).lower(),  # REACHABLE, STALE, DELAY, etc.
        })

    return entries
