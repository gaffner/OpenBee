"""
In-memory credential store — keeps scan credentials so AI chat can
reconnect to machines after the scan is done.
"""


_creds: dict[int, dict] = {}


def store(session_id: int, host: str, username: str, password: str, protocol: str, use_ssl: bool = False):
    _creds[session_id] = {
        "host": host,
        "username": username,
        "password": password,
        "protocol": protocol,
        "use_ssl": use_ssl,
    }


def get(session_id: int) -> dict | None:
    return _creds.get(session_id)
