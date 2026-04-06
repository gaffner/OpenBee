"""
Helper functions for converting Neo4j records to dicts
matching the Pydantic schema shapes.
"""

import json
from typing import Any


def node_to_device(node) -> dict[str, Any]:
    """Convert a Neo4j Device node to a dict matching DeviceOut."""
    props = dict(node)
    if isinstance(props.get("services"), str):
        props["services"] = json.loads(props["services"])
    if isinstance(props.get("open_ports"), str):
        props["open_ports"] = json.loads(props["open_ports"])
    return props


def node_to_network(node) -> dict[str, Any]:
    """Convert a Neo4j Network node to a dict matching NetworkOut."""
    return dict(node)