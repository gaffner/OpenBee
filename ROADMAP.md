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
