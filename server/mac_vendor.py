import json
import os
import re
from pathlib import Path

_DB_PATH = Path(__file__).parent / "oui_database.json"
_oui_db = None


def _normalize_mac(mac):
    clean = re.sub(r"[:\-\.]", "", mac).upper()
    return clean[:6]


def _load_db():
    global _oui_db
    if _oui_db is not None:
        return _oui_db
    if _DB_PATH.exists():
        with open(_DB_PATH, "r", encoding="utf-8") as f:
            _oui_db = json.load(f)
    else:
        _oui_db = {}
    return _oui_db


def lookup_vendor(mac):
    if not mac:
        return None
    db = _load_db()
    oui = _normalize_mac(mac)
    return db.get(oui)


def lookup_vendor_category(vendor):
    if not vendor:
        return "unknown"
    v = vendor.lower()
    if any(k in v for k in ["cisco", "meraki"]): return "cisco"
    if "fortinet" in v or "forti" in v: return "fortinet"
    if "juniper" in v: return "juniper"
    if "aruba" in v: return "aruba"
    if "ubiquiti" in v: return "ubiquiti"
    if "mikrotik" in v: return "mikrotik"
    if "palo alto" in v: return "paloalto"
    if "sophos" in v: return "sophos"
    if "netgear" in v: return "netgear"
    if "tp-link" in v or "tplink" in v: return "tplink"
    if "arista" in v: return "arista"
    if "huawei" in v: return "huawei"
    if "zyxel" in v: return "zyxel"
    if "dell" in v: return "dell"
    if any(k in v for k in ["hewlett", "hp inc", "hpe"]): return "hp"
    if "lenovo" in v: return "lenovo"
    if "apple" in v: return "apple"
    if "microsoft" in v: return "microsoft"
    if "intel" in v: return "intel"
    if "supermicro" in v: return "supermicro"
    if "asus" in v or "asustek" in v: return "asus"
    if "samsung" in v: return "samsung"
    if "vmware" in v: return "vmware"
    return "other"