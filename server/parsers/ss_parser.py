"""
Parse Linux `ss -tlnp` output to get listening services with process names.
"""

import re


def parse_ss(output: str) -> list[dict]:
    """
    Parse `ss -tlnp` output.
    Only returns entries listening on 0.0.0.0 or [::] / *.

    Returns list of dicts:
    { "protocol", "address", "port", "pid", "process_name" }
    """
    services = []
    seen = set()

    # Typical ss -tlnp lines:
    #   LISTEN  0  128  0.0.0.0:22   0.0.0.0:*  users:(("sshd",pid=1234,fd=3))
    #   LISTEN  0  128     [::]:22      [::]:*  users:(("sshd",pid=1234,fd=3))
    #   LISTEN  0  4096       *:9090       *:*  users:(("prometheus",pid=567,fd=7))
    line_re = re.compile(
        r"LISTEN\s+\d+\s+\d+\s+"
        r"(\[?[\d.:a-fA-F*]+\]?):(\d+)\s+"   # local addr:port
        r"\S+\s*"                              # peer address
        r"(.*)",                               # rest (users:...)
        re.IGNORECASE,
    )

    for m in line_re.finditer(output):
        addr_raw = m.group(1).strip("[]")
        port = int(m.group(2))
        rest = m.group(3)

        # Normalize: * means all interfaces
        if addr_raw == "*":
            addr_raw = "0.0.0.0"

        # Only keep all-interface listeners
        if addr_raw not in ("0.0.0.0", "::"):
            continue

        # Extract process info from users:(("name",pid=N,...))
        pid = None
        process_name = None
        pm = re.search(r'users:\(\("([^"]+)",pid=(\d+)', rest)
        if pm:
            process_name = pm.group(1)
            pid = int(pm.group(2))

        key = ("tcp", addr_raw, port, pid)
        if key in seen:
            continue
        seen.add(key)

        services.append({
            "protocol": "tcp",
            "address": addr_raw,
            "port": port,
            "pid": pid,
            "process_name": process_name or f"PID {pid}" if pid else "unknown",
        })

    services.sort(key=lambda s: s["port"])
    return services
