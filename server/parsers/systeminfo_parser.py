"""Parse the output of `systeminfo` into structured host data."""

import re


def parse_systeminfo(output: str) -> dict:
    """
    Returns a dict with:
    { "hostname", "os_name", "os_version", "os_build", "system_manufacturer",
      "system_model", "domain", "total_physical_memory" }
    """

    def _get(key: str) -> str | None:
        m = re.search(
            rf"^{re.escape(key)}:\s+(.+)$", output, re.MULTILINE | re.IGNORECASE
        )
        return m.group(1).strip() if m else None

    return {
        "hostname": _get("Host Name"),
        "os_name": _get("OS Name"),
        "os_version": _get("OS Version"),
        "os_build": _get("OS Build Type"),
        "system_manufacturer": _get("System Manufacturer"),
        "system_model": _get("System Model"),
        "domain": _get("Domain"),
        "total_physical_memory": _get("Total Physical Memory"),
    }
