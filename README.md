<p align="center">
  <img src="screens/openbee-logo.png" alt="OpenBee Logo" width="600"/>
</p>

<p align="center">
  <em>"Buzz Buzz! Let the bees do the hard work for you."</em><br/><br/>
  <strong>AI-Powered Network Management & Discovery</strong>
</p>

<p align="center">
  <a href="#installation--setup">Setup</a> •
  <a href="#getting-started">Getting Started</a> •
  <a href="#how-it-works">How It Works</a> •
  <a href="#ai-console">AI Console</a> •
  <a href="#examples">Examples</a> •
  <a href="#supported-platforms">Platforms</a>
</p>

---

## 🍯 The Hive Philosophy

In a beehive, the Queen doesn't carry pollen. She doesn't build honeycomb. **The bees do all the heavy lifting.**

OpenBee works the same way. **You are the Queen.** Your network is the hive. And the bees, our AI-powered agents, will discover, manage, and configure every device in your infrastructure. You just tell them what you need.

No more clicking through UIs from the year 2000. No more memorizing PowerShell cmdlets. No more SSH-ing into 15 machines to check one thing.

**Just say your words, my Queen. The bees will handle it.**

---

## 📸 The Hive at a Glance

<p align="center">
  <img src="screens/ui-main.png" alt="OpenBee Network Graph" width="800"/>
</p>

*Your entire network, visualized as a hive. Click any device to see its details — IP, MAC, OS, hardware, services, and listening ports. Managed devices glow. Unmanaged devices are discovered automatically. Click "Open AI Console" to start talking to any device.*

---

## �️ Installation & Setup

### Prerequisites

- **Python 3.11+** — [python.org](https://www.python.org/downloads/)
- **Node.js 20+** — [nodejs.org](https://nodejs.org/)
- **Git** — [git-scm.com](https://git-scm.com/)

### 1. Clone the repository

```bash
git clone https://github.com/galtshuler/Discovery.git
cd Discovery
```

### 2. Set up the backend (Python)

<details>
<summary><strong>Windows (PowerShell)</strong></summary>

```powershell
cd server
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt

# Create .env with your AI config
copy .env.example .env
# Edit .env and add your GITHUB_TOKEN (get one at https://github.com/settings/tokens)

# Seed the database with demo topologies
.\venv\Scripts\python seed.py

# Start the server
.\venv\Scripts\python -m uvicorn main:app --reload --port 8000
```
</details>

<details>
<summary><strong>Linux / macOS (Bash)</strong></summary>

```bash
cd server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env with your AI config
cp .env.example .env
# Edit .env and add your GITHUB_TOKEN (get one at https://github.com/settings/tokens)

# Seed the database with demo topologies
python seed.py

# Start the server
uvicorn main:app --reload --port 8000
```
</details>

The backend runs on **http://localhost:8000**. API docs at **http://localhost:8000/docs**.

### 3. Set up the frontend (React)

Open a **new terminal**:

<details>
<summary><strong>Windows (PowerShell)</strong></summary>

```powershell
cd client
npm install
npm run dev
```
</details>

<details>
<summary><strong>Linux / macOS (Bash)</strong></summary>

```bash
cd client
npm install
npm run dev
```
</details>

The frontend runs on **http://localhost:5173** and proxies API calls to the backend.

### 4. Open in browser

Go to **http://localhost:5173** — you'll see "Your Network" (empty) with a Demo toggle to explore sample topologies.

### Getting an AI token

The AI Console requires a **GitHub Personal Access Token** with Models API access:

1. Go to [github.com/settings/tokens](https://github.com/settings/tokens)
2. Generate a new token (classic) — no special scopes needed, just the default
3. Paste it into `server/.env` as `GITHUB_TOKEN=ghp_your_token_here`

Without a token, everything works except the AI Console chat.

### Enabling WinRM on Windows targets

To manage Windows machines, WinRM must be enabled on the target:

```powershell
# Run on the target Windows machine (as Administrator)
Enable-PSRemoting -Force
winrm set winrm/config/service/auth @{Basic="true"}
winrm set winrm/config/service @{AllowUnencrypted="true"}
```

### Enabling SSH on Linux/macOS targets

SSH is usually enabled by default. If not:

```bash
# Ubuntu/Debian
sudo apt install openssh-server
sudo systemctl enable --now ssh

# macOS
# System Settings → General → Sharing → Remote Login → On
```

---

## �🚀 Getting Started

Getting started with OpenBee is as simple as adding your first device:

1. **Click "Add Device"** in the top bar
2. **Choose the OS type** — Windows, Linux, or macOS
3. **Pick the protocol** — WinRM or SSH
4. **Enter the IP and credentials**
5. **Watch the bees work** — the scanner connects, runs discovery commands, and maps the device live

That's it. The device appears in your hive graph, and OpenBee automatically discovers every other device it can see — gateways, DNS servers, DHCP servers, ARP neighbors — all added to the graph as unmanaged devices. Toggle them on or off with the "Unmanaged" switch.

<p align="center">
  <img src="screens/ui-add-device.png" alt="OpenBee Add Device Wizard" width="800"/>
</p>

**To manage any device, just double-click it on the graph.** You're instantly in a prompt screen where you can query and act. That's the entire workflow. Click and talk.

---

## 🔍 How It Works

### Discovery — The Scout Bees

When you add a device, OpenBee deploys **scout bees** that map the device and everything around it. The bees gather:

🔹 **Network interfaces** — IPs, MACs, subnet masks, connection status
🔹 **ARP neighbors** — every device visible on the local network
🔹 **Routing tables** — default gateways and network routes
🔹 **DNS & DHCP servers** — who's serving names and addresses
🔹 **System information** — OS, hostname, hardware, domain, memory
🔹 **Running services** — every listening port and the process behind it
🔹 **NetBIOS names** — machine identities on Windows networks

From this data, OpenBee builds your hive:

**Managed devices** (devices you scanned) are shown prominently. **Gateways** are detected from routing tables and shown as routers. **DNS & DHCP servers** are detected from network config. **ARP neighbors**, every device seen on the wire, appear as unmanaged nodes.

### AI Console — The Worker Bees

Once a device is in the hive, the AI Console is your command center. The worker bees can:

**Run remote commands** on the device via SSH or WinRM. **Fetch files** from the device for local analysis. **Execute Python scripts in an isolated environment on the Hive Mind** for parsing binary files, crunching data, or processing logs. **Chain actions** across multiple iterations — fetch a file, parse it, run more commands, and synthesize a final answer.

The AI maintains **conversation history per device**, so it remembers what you discussed earlier. Ask a follow-up and it knows the context.

<p align="center">
  <img src="screens/ui-ai-console.png" alt="OpenBee AI Console" width="800"/>
</p>

*The AI Console in action — ask questions, run commands, create users, inspect files, all through natural language.*

### Cross-Device Intelligence — The Hive Mind

The Hive Mind is the central brain of OpenBee. It is where the server code resides, where all API requests are processed, and where remote connection sessions to your devices are established. It is the most crucial asset in the hive.

The Hive Mind maintains a **global context** of your entire network. It understands the relationships between devices — which machine is the router, which is the DNS server, which is the domain controller. This enables **complex multi-device operations from a single prompt**. When a Python script needs to run for parsing files or crunching data, it executes in an isolated environment on the Hive Mind, keeping your managed devices untouched.

---

## 💬 Examples

### Example 1: Set Up a Web Server from Scratch

You want to deploy a web app. IIS on the server, repo from GitHub, and open it to the internet.

**You (on WEB-SRV-01):**
> Set up IIS, clone https://github.com/acme/webapp, and open it to the internet.

**🐝 OpenBee:**
```
$ Install-WindowsFeature -Name Web-Server -IncludeManagementTools
[output] Success: True, Restart Needed: No

$ git clone https://github.com/acme/webapp C:\inetpub\wwwroot\webapp
[output] Cloning into 'C:\inetpub\wwwroot\webapp'... done.

$ New-IISSite -Name "WebApp" -PhysicalPath "C:\inetpub\wwwroot\webapp" -BindingInformation "*:80:"
[output] Site "WebApp" created successfully.

🧠 Thinking... WEB-SRV-01 is behind gateway-10.0.0.1 (Cisco ASA 5506-X).
   To open it to the internet I need to configure port forwarding on the
   router. Activating the Cisco bee... 🐝

$ ssh admin@10.0.0.1 "show running-config | include interface"
[output] interface GigabitEthernet0/0 (outside)
         interface GigabitEthernet0/1 (inside)

$ ssh admin@10.0.0.1 "object network WEB-SRV-01"
$ ssh admin@10.0.0.1 "host 10.0.0.50"
$ ssh admin@10.0.0.1 "nat (inside,outside) static interface service tcp 80 80"
[output] Configuration applied.

✓ All done! IIS is installed, the repo is cloned, and the site is live.
  I also configured port forwarding on your Cisco ASA 5506-X router.
  External port 80 → 10.0.0.50:80 (WEB-SRV-01).
  Your web app is now accessible from the internet.
```

---

### Example 2: Managing Active Directory

**You (on DC-01):**
> Create a Group Policy that installs Google Chrome silently on all domain computers.

**🐝 OpenBee:**
```
$ New-GPO -Name "Install Google Chrome" | New-GPLink -Target "DC=acme,DC=local"
[output] GPO "Install Google Chrome" created and linked to acme.local

$ Invoke-WebRequest -Uri "https://dl.google.com/dl/chrome/install/googlechromestandaloneenterprise64.msi" -OutFile "\\DC-01\NETLOGON\ChromeSetup.msi"
[output] Download complete.

$ Set-GPRegistryValue -Name "Install Google Chrome" -Key "HKLM\SOFTWARE\Policies\Microsoft\Windows\Installer" ...
[output] Software installation policy configured.

✓ Group Policy "Install Google Chrome" is created and linked to the domain.
  Chrome MSI is staged on NETLOGON. All domain computers will install Chrome
  at next Group Policy refresh (or run gpupdate /force to push now).
```

**You:**
> Add a new domain user called John Dubian and add him to the HR group.

**🐝 OpenBee:**
```
$ New-ADUser -Name "John Dubian" -SamAccountName "jdubian" -UserPrincipalName "jdubian@acme.local" -Path "OU=Users,DC=acme,DC=local" -AccountPassword (ConvertTo-SecureString "W3lc0me!2026" -AsPlainText -Force) -Enabled $true
[output] User "John Dubian" created successfully.

$ Add-ADGroupMember -Identity "HR" -Members "jdubian"
[output] User "jdubian" added to group "HR".

✓ Done! User John Dubian (jdubian@acme.local) has been created and added to
  the HR group. Temporary password: W3lc0me!2026 (user will be prompted to
  change on first login).
```

---

### Example 3: Who Logged In via RDP?

**You:**
> Who logged on recently using RDP to FILE-SRV-02?

**🐝 OpenBee:**
```
$ fetch: C:\Windows\System32\winevt\Logs\Microsoft-Windows-TerminalServices-LocalSessionManager%4Operational.evtx
[output] Fetched → C:\Users\...\AppData\Local\Temp\discovery_rdp.evtx (2.4 MB)

$ python (local)
[output] Parsed 847 events. Found 12 RDP logon events in the last 7 days.

✓ Here are the recent RDP logons to FILE-SRV-02:

  | Date                | User              | Source IP      |
  |---------------------|-------------------|----------------|
  | 2026-03-28 14:22:01 | ACME\jsmith       | 10.0.0.105     |
  | 2026-03-28 09:15:44 | ACME\jdubian      | 10.0.0.112     |
  | 2026-03-27 18:30:12 | ACME\admin         | 10.0.0.1       |
  | 2026-03-27 11:05:33 | ACME\jsmith       | 10.0.0.105     |
  | 2026-03-26 16:48:00 | ACME\mwilliams    | 10.0.0.88      |

  The most frequent RDP user is jsmith (4 sessions this week).
  Last RDP login was by jsmith from 10.0.0.105, today at 2:22 PM.
```

The AI fetched the Windows Event Log binary file, ran a Python script in an isolated environment on the Hive Mind to parse the .evtx format, and presented the results, all from a single prompt.

---

### Example 4: Network-Wide Queries

**You:**
> Which devices in the hive are running SSH on a non-standard port?

**🐝 OpenBee:**
```
✓ I've checked all managed devices in the hive. Here are the ones with SSH
  on non-standard ports:

  | Device         | IP          | SSH Port |
  |----------------|-------------|----------|
  | DEV-SRV-03     | 10.0.1.15   | 2222     |
  | BACKUP-01      | 10.0.2.30   | 8022     |

  All other devices with SSH are on the standard port 22.
```

---

## 🖥️ Supported Platforms

OpenBee works with **any Windows or Unix-like machine**. If it has a network interface, OpenBee can discover it. If it supports SSH or WinRM, OpenBee can manage it.

| Platform | Discovery | Management | Protocol |
|----------|-----------|------------|----------|
| Windows Server | ✅ | ✅ | WinRM |
| Windows 10/11 | ✅ | ✅ | WinRM |
| Ubuntu / Debian | ✅ | ✅ | SSH |
| RHEL / CentOS | ✅ | ✅ | SSH |
| macOS | ✅ | ✅ | SSH |
| Routers / Switches | ✅ | ✅ | SSH |
| Any network device | ✅ (passive) | — | ARP discovery |

**The sky is the limit.** If you can SSH or WinRM into it, OpenBee can manage it.

---

## 🔮 Coming Soon

Check out the [Roadmap](ROADMAP.md) for planned features and what's next for OpenBee.

---

## 🐝 Adding Devices to the Hive

There are two ways to bring devices into the hive:

### Option 1: Credentials + Protocol (Current)
Click **Add Device**, enter the IP, username, password, and select WinRM or SSH. OpenBee connects immediately and scans.

### Option 2: Agent Installation (Coming Soon)
From the web console, generate an agent installer. Run it on the target machine. The agent registers itself with the hive automatically — no credentials needed.

---

## 🏗️ Architecture

```
                    🐝 The Hive
                         │
              ┌──────────┼──────────┐
              │          │          │
         ┌────┴────┐ ┌───┴───┐ ┌───┴────┐
         │ Worker  │ │Worker │ │ Worker │
         │ Bee     │ │ Bee   │ │  Bee   │
         │ (SSH)   │ │(WinRM)│ │ (SSH)  │
         └────┬────┘ └───┬───┘ └───┬────┘
              │          │         │
         ┌────┴────┐ ┌───┴───┐ ┌──┴─────┐
         │ Linux   │ │Windows│ │ Router │
         │ Server  │ │  DC   │ │        │
         └─────────┘ └───────┘ └────────┘

    Queen (You) ──prompt──▶ AI Brain ──commands──▶ Worker Bees
                                │
                         ┌──────┤
                         │      │
                    fetch files  run local
                    from hive   python scripts
```

---

## ⚠️ Disclaimer

**OpenBee is provided "as is", without warranty of any kind.** The authors and contributors are **not responsible** for any damage, data loss, security incidents, or any other harm resulting from the use or misuse of this software.

**AI-powered operations can be dangerous.** OpenBee executes real commands on real machines. AI agents may make mistakes, misinterpret instructions, or take unexpected actions. **Human supervision is required at all times**, especially when operating on critical systems, production environments, or sensitive assets.

By using OpenBee, you acknowledge that:
- You are solely responsible for any actions taken by the software on your systems.
- AI-generated commands should be reviewed before execution on production/critical infrastructure.
- The authors bear no liability for any consequences arising from the use of this tool.

**Use responsibly. Always have backups. Always supervise.**

---

## 📄 License

MIT — Free as honey. 🍯

---

<p align="center">
  <strong>🐝 OpenBee</strong><br/>
  <em>Your Network. Your Bees. Their Job.</em><br/><br/>
  Stop doing IT. Let the bees do it for you.
</p>
