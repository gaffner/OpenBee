"""Parse Linux `ip route` and `/etc/resolv.conf` for gateway and DNS info."""

import re


def parse_ip_route(output: str) -> str | None:
    """Extract the default gateway IP from `ip route` output.
    Typical line: default via 10.0.0.1 dev eth0
    """
    m = re.search(r"^default\s+via\s+([\d.]+)", output, re.MULTILINE)
    return m.group(1) if m else None


def parse_resolv_conf(output: str) -> list[str]:
    """Extract nameserver IPs from /etc/resolv.conf.
    Typical line: nameserver 8.8.8.8
    """
    return re.findall(r"^nameserver\s+([\d.]+)", output, re.MULTILINE)
