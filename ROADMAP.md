# 🔮 OpenBee Roadmap

Planned features and improvements for OpenBee. Contributions and ideas are welcome!

---

## 🔌 More Protocols

Support for RDP, Telnet, and WMI connections — expanding beyond SSH and WinRM to cover more device types and legacy systems.

## 🌐 Web API Management

Connect to devices that only offer management through web interfaces (routers, switches, firewalls, appliances). The bees will interact with web-based admin panels just like a human would.

## 📦 Agent Installation from Web Console

Install the OpenBee agent directly from the UI onto any machine. No need to manually deploy — just click and the bee lands on the target.

## 🐝 Custom Bee Agent

A lightweight agent for non-standard machines and devices behind strict firewalls. Supports **backconnect mode** — the bee calls home to the Hive Mind instead of the other way around, busting through firewalls and NAT without opening inbound ports.

## 🔄 Continuous Monitoring

Bees that keep watching for changes in your hive — new devices appearing, services going down, configuration drift, and more. Get notified when something changes.

## ⏰ Automation

Schedule recurring tasks to run on any device at set intervals. Examples:
- Clean temp files every night
- Pull latest code every hour
- Restart a service weekly
- Run compliance checks daily

## 🔍 Passive & Active Scanning Modes

Choose between **passive** and **active** scan modes when discovering your network:
- **Passive** — collect data from ARP tables, routing tables, and neighbor caches without generating any traffic. Silent and safe.
- **Active** — verify if discovered hosts are actually alive using ICMP ping or TCP SYN probes. Optionally scan hosts for live services with SYN checks to build a real-time port/service map.

## 🔬 Deep Service Analysis

Go beyond basic `netstat` and `tasklist`. When a listening service is detected, the bees will:
- Read the service's logs and configuration files
- Identify the service version, health, and recent errors
- Provide deeper insight about what the service is doing, not just that it exists

Turn a raw port number into an actionable service report.

## 🔐 Permission Scopes & Ask-Before-Act

Inspired by how modern coding agents work — the AI will **ask for confirmation before executing risky actions**. You define permission scopes per device or device group:
- **Read-only** — the AI can inspect but not modify
- **File access** — allow reading/editing specific files
- **Command execution** — restrict to specific commands or services
- **Full access** — the AI operates freely within the device

Group devices into **categories** (e.g. "Production Servers", "Dev Machines", "Network Gear") and assign different permission levels to each group. Fine-grained control over what the bees can touch.

**🤠 YOLO Mode** — remove all guardrails. Full permissions on every device. For brave souls and lab environments.

## ⏪ Auto-Revert on Connection Loss

When the AI performs operations on a device, things can go wrong — a bad config change, a killed service, or a dropped connection. OpenBee will implement a **safety net**:

- Before every risky operation, the Hive Mind generates a **revert command** and pushes it to the local agent.
- If the agent loses communication with the Hive Mind for a configurable timeout (e.g. 30 seconds), it automatically executes the revert — rolling back the last change without human intervention.
- The local agent maintains a lightweight state of recent actions, so it can undo them independently.

This means the bee on each device isn't just a dumb command executor — it's a safety-aware agent that can protect the device even when the hive goes dark.

---

# 🔧 Technical Improvements

## 🕸️ Graph Database (Neo4j)

Replace the current relational storage with a proper graph database like **Neo4j** for network topology. Networks are graphs — devices are nodes, connections are edges. A graph DB lets us run powerful queries like "find all paths between two devices", "which devices are one hop from the internet?", and "show me every device that depends on this DNS server" — natively and fast.
