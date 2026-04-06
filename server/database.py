import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def get_driver():
    return driver


def init_db():
    """Create uniqueness constraints and counter nodes for ID generation."""
    with driver.session() as session:
        session.run(
            "CREATE CONSTRAINT device_id IF NOT EXISTS "
            "FOR (d:Device) REQUIRE d.id IS UNIQUE"
        )
        session.run(
            "CREATE CONSTRAINT network_id IF NOT EXISTS "
            "FOR (n:Network) REQUIRE n.id IS UNIQUE"
        )
        for name in ("device", "network", "connection"):
            session.run(
                "MERGE (c:_Counter {name: $name}) ON CREATE SET c.value = 0",
                name=name,
            )


def next_id(tx, entity_name: str) -> int:
    """Atomically increment and return the next ID for an entity type."""
    result = tx.run(
        "MATCH (c:_Counter {name: $name}) "
        "SET c.value = c.value + 1 "
        "RETURN c.value AS id",
        name=entity_name,
    )
    return result.single()["id"]


def neo4j_config() -> dict:
    """Return Neo4j connection details for the neovis.js frontend."""
    return {
        "uri": NEO4J_URI,
        "user": NEO4J_USER,
        "password": NEO4J_PASSWORD,
    }