**English | [فارسی](./Translation/README-fa.md)**

# Homelab Monitoring Dashboard 🖥️📡

A network and server monitoring dashboard for homelabs — built to run on **shared PHP hosting** (no VPS or root access required), monitoring **MikroTik**, **Cisco**, and **HPE** servers all in one place.

> Built by [Rahideh](https://trustit.ir) for a personal homelab project — with help from [Claude](https://claude.ai) (Anthropic's AI assistant) throughout coding, and testing 🤖

---

## ✨ Features

- 📊 Live web dashboard with per-device status cards (online/offline, CPU, temperature, traffic)
- 📈 CPU/temperature/traffic history charts for each device (click any card)
- 🔔 Automatic alert log (offline, back online, high temperature)
- 🌡️ Configurable temperature warning threshold per device
- 🔌 Push-based architecture — works even though shared hosting can't reach your homelab's internal network
- 🐍 Separate Python agents per device type:
  - **MikroTik** via the RouterOS API
  - **Cisco** via SNMP
  - **HPE** via the Redfish API (iLO)
- 🔒 Dashboard protected with HTTP Basic Auth (no separate login system needed)
- 🎨 Dark terminal-style UI, Vazirmatn + JetBrains Mono fonts, RTL-ready

## 📸 Preview


[Dashboard](./screenshots/dashboard.png)


## 🏗️ Architecture

Since shared hosting can't reach your homelab's internal network (behind NAT), this project uses a **push-based** architecture:

```
[MikroTik]  ─┐
[Cisco]      ├─→  Python agents (running on an always-on device in your homelab)
[HPE/iLO]   ─┘         │
                        │  Periodic POST (every 1-5 min, via Task Scheduler)
                        ▼
              backend/ingest.php  (on shared hosting, PHP + SQLite)
                        │
                        ▼
              backend/api_*.php  ←── frontend/ (web dashboard)
```

## 📁 Project structure

```
homelab-dashboard/
├── backend/              # PHP APIs + SQLite database
│   ├── config.example.php
│   ├── db_init.php
│   ├── ingest.php        # receives data from agents
│   ├── api_devices.php   # current device status
│   ├── api_history.php   # history (for charts)
│   └── api_alerts.php    # alert log
├── agent/                # Python data-collection scripts
│   ├── common.py
│   ├── mikrotik_agent.py + config.example.json
│   ├── cisco_agent.py    + cisco_config.example.json
│   ├── hpe_agent.py      + hpe_config.example.json
│   ├── requirements.txt
│   └── README.md         # full setup guide for each agent
├── frontend/             # web dashboard
│   ├── index.html
│   ├── style.css
│   ├── script.js
│   ├── config.js
│   └── .htaccess.example # password protection (optional)
├── screenshots/           # web dashboard Preview
│   ├── dashboard.png
├── frontend_auth_helper/  # temporary tools for setting the dashboard password
├── Translation/
│   └── README-fa.md       # Persian version of this README
└── .gitignore
```

## 🚀 Deployment guide (shared hosting)

### Requirements
- Shared hosting with PHP 7.4+ and SQLite support (`pdo_sqlite`)
- An always-on device in your homelab (even a Windows PC that's usually on works) to run the agents
- Python 3.9+ on that same device, for the agents

### Phase 1: Backend
1. Upload the `backend/` folder (e.g. to `public_html/dashboard/backend`)
2. Copy `config.example.php` to `config.php` and set the API key to a long random string
3. Run `db_init.php` once from your browser, then delete or rename it
4. Send a test request to `ingest.php` with curl/Postman/PowerShell (examples below)

### Phases 2-4: Agents (MikroTik / Cisco / HPE)
Full setup instructions for all three (installing Python, filling in config, enabling the API/SNMP/Redfish on the device itself, and scheduling with Windows Task Scheduler) are in [`agent/README.md`](./agent/README.md).

### Phase 5: Frontend
1. Upload the `frontend/` folder next to `backend/`
2. If your folder structure differs, update `frontend/config.js` with the correct path to `backend`
3. Go to `https://yourdomain.com/dashboard/frontend/index.html`

### (Optional but recommended) Password-protect the dashboard
1. Temporarily upload `frontend_auth_helper/generate_hash.php` **outside of `frontend/`** (since it won't be reachable once the folder is locked) and use it to generate a password hash
2. Before locking things down, upload `frontend_auth_helper/show_path.php` inside `frontend/` to get the server's full absolute path
3. Copy `frontend/.htaccess.example` to `.htaccess` and fill in the real path for `AuthUserFile`
4. Create a `.htpasswd` file in `frontend/` and paste in the single line the hash generator gave you
5. Delete both helper files (`generate_hash.php`, `show_path.php`) from the host

## 🧪 Testing ingest.php (before setting up a real agent)

**PowerShell:**
```powershell
$body = @{
    api_key = "your-api-key"
    device_key = "mikrotik-main"
    display_name = "MikroTik hEX"
    device_type = "mikrotik"
    cpu_percent = 12.5
    temperature_c = 45.2
    uptime_seconds = 123456
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://yourdomain.com/dashboard/backend/ingest.php" -Method Post -Body $body -ContentType "application/json"
```

Successful response: `{"success": true, "device_id": 1}`

## 🔒 Security — read this before you push

This repo's `.gitignore` is set up so that files containing real secrets (your actual API key, MikroTik/Cisco/iLO passwords, the `.htpasswd` file) never get committed. Only the `*.example.*` version of each is tracked. **Before pushing, always check:**

```bash
git status
```

and make sure none of these show up as staged:
- `backend/config.php`
- `agent/config.json`, `agent/cisco_config.json`, `agent/hpe_config.json`
- `frontend/.htaccess`, `frontend/.htpasswd`
- `backend/database.sqlite`

## 🛠️ Built with

PHP · SQLite · Python (`routeros_api`, `pysnmp`, `requests`) · Chart.js · Vazirmatn & JetBrains Mono


## 📄 License

MIT — use it however you like for your own projects, with attribution.
