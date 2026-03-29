"""Parse the output of `nbtstat -n` into structured NetBIOS names."""

import re


def parse_nbtstat(output: str) -> list[dict]:
    """
    Returns a list of dicts:
    { "name", "nb_type", "status" }
    """
    entries = []

    # Typical line:
    #   MYCOMPUTER     <00>  UNIQUE      Registered
    #   WORKGROUP      <00>  GROUP       Registered
    line_re = re.compile(
        r"^\s+(\S+)\s+(<[0-9A-Fa-f]{2}>)\s+(\S+)\s+(\S+)", re.MULTILINE
    )

    for m in line_re.finditer(output):
        nb_type_code = m.group(2)
        kind = m.group(3)  # UNIQUE or GROUP
        entries.append({
            "name": m.group(1),
            "nb_type": f"{nb_type_code} {kind}",
            "status": m.group(4),
        })

    return entries
