"""Parse Linux host info from `hostnamectl` and `uname -a` / `/etc/os-release`."""

import re


def parse_hostnamectl(output: str) -> dict:
    """
    Parse `hostnamectl` output.
    Returns dict matching DiscoveredHost fields.
    """
    def _get(key: str) -> str | None:
        m = re.search(rf"^\s*{re.escape(key)}:\s*(.+)$", output, re.MULTILINE | re.IGNORECASE)
        return m.group(1).strip() if m else None

    hostname = _get("Static hostname") or _get("Hostname") or _get("Transient hostname")
    os_name = _get("Operating System")
    kernel = _get("Kernel")
    chassis = _get("Chassis")
    hw_vendor = _get("Hardware Vendor")
    hw_model = _get("Hardware Model")

    return {
        "hostname": hostname,
        "os_name": os_name,
        "os_version": kernel,
        "os_build": None,
        "system_manufacturer": hw_vendor,
        "system_model": hw_model or chassis,
        "domain": None,
        "total_physical_memory": None,
    }


def parse_linux_info(hostnamectl_out: str, meminfo_out: str) -> dict:
    """
    Combine hostnamectl + /proc/meminfo into a single host info dict.
    """
    info = parse_hostnamectl(hostnamectl_out)

    # Parse total memory from /proc/meminfo
    m = re.search(r"MemTotal:\s+([\d,]+)\s+kB", meminfo_out, re.IGNORECASE)
    if m:
        kb = int(m.group(1).replace(",", ""))
        mb = kb // 1024
        if mb >= 1024:
            info["total_physical_memory"] = f"{mb // 1024} GB"
        else:
            info["total_physical_memory"] = f"{mb} MB"

    return info
