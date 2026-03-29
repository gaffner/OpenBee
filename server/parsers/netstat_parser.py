"""
Parse Windows `netstat -ano` + `tasklist /FO CSV` to get listening services
with their process names.
"""

import csv
import io
import re


def _parse_tasklist_csv(output: str) -> dict[int, str]:
    """Parse `tasklist /FO CSV` into a PID→process_name mapping."""
    pid_map = {}
    reader = csv.reader(io.StringIO(output))
    for row in reader:
        if len(row) >= 2:
            try:
                pid = int(row[1].strip('"'))
                name = row[0].strip('"')
                pid_map[pid] = name
            except (ValueError, IndexError):
                continue
    return pid_map


def parse_netstat_with_tasklist(netstat_output: str, tasklist_output: str) -> list[dict]:
    """
    Combine netstat -ano and tasklist /FO CSV to produce listening services.
    Only returns entries listening on 0.0.0.0 or [::].

    Returns list of dicts:
    { "protocol", "address", "port", "pid", "process_name" }
    """
    pid_map = _parse_tasklist_csv(tasklist_output)

    services = []
    # Typical netstat line:
    #   TCP    0.0.0.0:135           0.0.0.0:0              LISTENING       1044
    #   TCP    [::]:135              [::]:0                  LISTENING       1044
    line_re = re.compile(
        r"^\s*(TCP|UDP)\s+"
        r"(\[?[\d.:a-fA-F]+\]?):(\d+)\s+"   # local address:port
        r"\S+\s+"                            # foreign address
        r"LISTENING\s+"
        r"(\d+)",
        re.MULTILINE | re.IGNORECASE,
    )

    seen = set()
    for m in line_re.finditer(netstat_output):
        proto = m.group(1).lower()
        addr = m.group(2).strip("[]")
        port = int(m.group(3))
        pid = int(m.group(4))

        # Only keep 0.0.0.0 and :: (all-interface listeners)
        if addr not in ("0.0.0.0", "::"):
            continue

        key = (proto, addr, port, pid)
        if key in seen:
            continue
        seen.add(key)

        process_name = pid_map.get(pid, f"PID {pid}")

        services.append({
            "protocol": proto,
            "address": addr,
            "port": port,
            "pid": pid,
            "process_name": process_name,
        })

    services.sort(key=lambda s: s["port"])
    return services
