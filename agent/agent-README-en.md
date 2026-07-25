**English | [فارسی](../Translation/agent-README.md)**

# MikroTik Agent — Phase 2

A Python script that reads CPU, temperature (if a sensor is present), uptime, and traffic from MikroTik (via the RouterOS API) and sends it to the dashboard (`ingest.php`).

## ✅ What's been tested?

- Parsing RouterOS's uptime format (`4w3d12h30m45s` and similar) into seconds — tested with 7 different scenarios.
- Reading temperature from `/system/health` in the RouterOS 7 format; if the device has no temperature sensor, it returns `None` without crashing.
- The full send path (`send_to_dashboard`) was tested with simulated data against a real instance of `ingest.php`, and the data landed correctly in the dashboard.

⚠️ Note: since I didn't have access to a real MikroTik device, I couldn't directly test the API connection itself (`get_mikrotik_metrics`). The logic is written based on the documented, standard behavior of the `routeros_api` library, but you should still carefully check the first real run against your own router (check the `agent.log` file).

## 📦 Installation on Windows

### 1. Install Python (if you don't have it)
Download and install the latest version from [python.org](https://www.python.org/downloads/). Make sure to check **"Add python.exe to PATH"** during installation.

Verify the install:
```powershell
python --version
```

### 2. Install the required libraries
Inside the `agent` folder:
```powershell
pip install -r requirements.txt
```

### 3. Create the config file
Copy `config.example.json` to `config.json` and fill in the values:

```powershell
Copy-Item config.example.json config.json
notepad config.json
```

Values you need to change:
- `mikrotik.host` → your router's IP (the same one you use to log into Winbox)
- `mikrotik.username` / `mikrotik.password` → login credentials
- `dashboard.ingest_url` → the real URL of `ingest.php` on your host
- `dashboard.api_key` → the same key you set in `backend/config.php`

### 4. Manual test (before scheduling it)
```powershell
python mikrotik_agent.py
```

- If it worked, you'll see in the terminal and in `agent.log`: `send successful: {'success': True, ...}`
- Check `api_devices.php` in your browser — you should see `mikrotik-main` with real data.

### Common issues at this stage:
| Error | Likely cause |
|---|---|
| `Connection refused` or timeout to the router | The API service (port 8728) isn't enabled, or MikroTik's firewall is blocking your Windows machine's IP |
| `Invalid user name or password` | Wrong username/password, or the user doesn't have API access (in MikroTik it must belong to a group with the `api` policy) |
| Succeeds but `temperature_c: null` | Normal — your router model has no temperature sensor (many simple RouterBoards don't) |
| Connection error to `ingest_url` | Wrong URL, or you typed `http` instead of `https` |

## ⏰ Scheduling with Task Scheduler

1. Open **Task Scheduler** from the Start Menu
2. **Create Task** (not Create Basic Task, since it gives us more control)
3. **General** tab:
   - Name: `MikroTik Dashboard Agent`
   - Select **Run whether user is logged on or not** (so it runs even when you're not logged in)
4. **Triggers** tab → **New**:
   - Begin the task: **On a schedule**
   - Repeat task every: **1 minute** (or every 2-5 minutes, whatever you prefer)
   - for a duration of: **Indefinitely**
5. **Actions** tab → **New**:
   - Action: **Start a program**
   - Program/script: the full path to `python.exe` (find it with `where python` in PowerShell)
   - Add arguments: the full path to the file, e.g.:
     ```
     "C:\Users\Rahi\homelab-dashboard\agent\mikrotik_agent.py"
     ```
   - Start in: the path to the `agent` folder (this really matters, since the script looks for `config.json` in the same folder):
     ```
     C:\Users\Rahi\homelab-dashboard\agent
     ```
6. **Conditions** tab: uncheck "Start the task only if the computer is on AC power" if it's a laptop (otherwise it won't run on battery)
7. Save it — it'll ask for your Windows password (since "Run whether logged on or not" is selected)

### Testing Task Scheduler
After creating it, right-click the task → **Run**. Then check `agent.log` to see if a new entry was added.

## 📌 Next step

Add Cisco support to the agent, then HPE, then the dashboard frontend.

---

# Cisco Agent — Phase 3

The `cisco_agent.py` script connects to a Cisco switch/router via **SNMP (v2c)** and collects CPU, temperature (if there's an environmental sensor), uptime, and total traffic across all interfaces.

## ✅ What's been tested?

- The SNMP protocol itself (get and walk) was tested against a real SNMP agent (net-snmp) — not just importing the library.
- OIDs identical to Cisco's (CPU, temperature, interface traffic) were simulated on that agent and parsed correctly.
- The full path (`get_cisco_metrics` → `send_to_dashboard` → `ingest.php` → `api_devices.php`) ran successfully end to end once.

⚠️ Note: since I didn't have access to a real Cisco switch, the final test ran against a simulated SNMP agent (net-snmp with manually configured OIDs), not an actual Cisco device. The logic and OIDs are standard (CISCO-PROCESS-MIB and CISCO-ENVMON-MIB), but you should still **carefully check the first real run**.

## 📦 Installation and setup

### 1. Libraries (if you already ran `requirements.txt`, `pysnmp` is installed now too)
```powershell
pip install -r requirements.txt
```

### 2. Enable SNMP on the Cisco switch (if you haven't already)
Log into the switch via console/SSH:
```
enable
configure terminal
snmp-server community YOUR_COMMUNITY_STRING RO
end
write memory
```
Make `YOUR_COMMUNITY_STRING` something hard to guess (not `public`).

### 3. Create the config
```powershell
Copy-Item cisco_config.example.json cisco_config.json
notepad cisco_config.json
```
Values needed:
- `cisco.host` → the switch's IP
- `cisco.community` → the community string you created above
- `dashboard.ingest_url` and `dashboard.api_key` → same as before, from `backend/config.php`

### 4. Manual test
```powershell
python cisco_agent.py
```
If successful → check `cisco_agent.log` and view `api_devices.php` in your browser.

### Common issues:
| Error | Likely cause |
|---|---|
| Timeout / no response | The Cisco device's firewall, or a network in between, is blocking UDP port 161, or SNMP isn't enabled at all |
| `temperature_c: null` | Your model doesn't have CISCO-ENVMON-MIB — normal, many simpler switches lack this sensor |
| Community error | Wrong community string, or it doesn't have RO access |

## ⏰ Scheduling with Task Scheduler
Exactly like the MikroTik Agent (section above) — just create a new Task that calls `cisco_agent.py` instead of `mikrotik_agent.py`. You can use the same folder as "Start in" since `cisco_config.json` has a different name from MikroTik's `config.json`, so there's no conflict.

## 📌 Next step

Add HPE (via the Redfish/iLO API), then the dashboard frontend.

---

# HPE Agent — Phase 4

The `hpe_agent.py` script connects to an HPE server via the **Redfish API** (the industry standard supported by iLO).

## ⚠️ The most important thing to know: iLO doesn't give you everything

Unlike MikroTik and Cisco, iLO is a controller separate from the server's own operating system (out-of-band). This means:

**✅ Available:**
- Temperature (all sensors — CPU, air inlet, DIMM, etc.) — the highest reading is reported
- Instantaneous power draw (watts), if your model supports it
- Fan status and count
- Server model and serial number

**❌ Not available (and stays `null` in this version):**
- CPU usage percentage — this is OS-level information, not out-of-band hardware data
- OS uptime — iLO only knows whether the power is on or off, not how long Windows/Linux has been up
- Network traffic on the server's NICs — the Redfish standard doesn't define a byte counter for this

If you want these three later, you'd need a lightweight agent running *inside* the server itself (on Windows/Linux) — that's a separate phase, let me know if you want it built later.

## ✅ What's been tested?

- The full real HTTP path (not mocked functions) was tested against a simulated Redfish server: root discovery → Chassis → Thermal → Power.
- The logic for picking the highest temperature among multiple sensors (and ignoring `Absent` sensors) worked correctly.
- A wrong-credentials error (401) was handled correctly with a clear error message.
- The full path through to the data landing in the dashboard (with `power_watts`, `model`, `fan_count` in `extra`) ran successfully.

⚠️ Since I didn't have access to a real HPE server, testing ran against a simulated Redfish agent, not actual iLO. The JSON structure follows the standard Redfish schema exactly, but you should still carefully check the first real run.

## 📦 Installation and setup

### 1. Find your iLO address and login credentials
The iLO address is usually a separate IP (not the IP of the server's own Windows/Linux OS) — you connect to it via a browser, something like `https://10.0.0.5`. The username/password are the same ones you use to log into the iLO web interface.

### 2. Create the config
```powershell
Copy-Item hpe_config.example.json hpe_config.json
notepad hpe_config.json
```
Values needed:
- `hpe.ilo_url` → the iLO address with `https://`
- `hpe.username` / `hpe.password` → iLO login credentials
- `dashboard.ingest_url` and `dashboard.api_key` → same as before

### 3. About `verify_ssl`
iLO usually has a self-signed SSL certificate, so we default this to `false` to avoid certificate errors. If you've installed a valid certificate on iLO, you can set it to `true`.

### 4. Manual test
```powershell
python hpe_agent.py
```
If successful → check `hpe_agent.log` (you should see temperature, power, and the server model) and open `api_devices.php` in your browser.

### Common issues:
| Error | Likely cause |
|---|---|
| `401 Unauthorized` | Wrong iLO username/password |
| Timeout / connection error | Wrong iLO address, or your Windows machine can't reach iLO's management network |
| `temperature_c: null` | Unlikely, but means no sensor was found in the `Enabled` state |
| `power_watts` is always empty | Some entry-level HPE models don't support instantaneous power reporting — normal |

## ⏰ Scheduling with Task Scheduler
Exactly like the previous two — a new Task with `hpe_agent.py`. The name `hpe_config.json` doesn't conflict with the others.

## 📌 Next step

All three agents (MikroTik, Cisco, HPE) are ready. Now it's the frontend's turn — a page that shows the status of all three in one place, with colored cards and history charts.
