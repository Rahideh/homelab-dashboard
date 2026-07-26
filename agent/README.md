**English | [فارسی](../Translation/agent-README-fa.md)**

# MikroTik Agent — Phase 2

This is a small Python script that reads CPU, temperature (if the router has a sensor), uptime, and traffic from a MikroTik device through the RouterOS API, then sends everything to the dashboard (`ingest.php`).

## What I tested

* Parsing RouterOS uptime strings like `4w3d12h30m45s` into seconds. I tested this with 7 different cases.
* Reading temperature from `/system/health` in RouterOS 7 format. If the device does not have a temperature sensor, it returns `None` instead of crashing.
* The full send flow (`send_to_dashboard`) was tested with simulated data against a real `ingest.php`, and the data landed correctly in the dashboard.

I did not have access to a real MikroTik device, so I could not test the API connection itself (`get_mikrotik_metrics`) directly. The logic is based on the documented behavior of `routeros_api`, but you should still check the first real run on your own router and look at `agent.log`.

## Installation on Windows

### 1) Install Python

If Python is not installed yet, download the latest version from [python.org](https://www.python.org/downloads/). During setup, make sure **Add python.exe to PATH** is checked.

Verify the install:

```powershell id="k3r8za"
python --version
```

### 2) Install the required libraries

Inside the `agent` folder:

```powershell id="f1m2qn"
pip install -r requirements.txt
```

### 3) Create the config file

Copy `config.example.json` to `config.json` and fill in the values:

```powershell id="n8v5pl"
Copy-Item config.example.json config.json
notepad config.json
```

You need to change these values:

* `mikrotik.host` → your router IP (the same one you use in Winbox)
* `mikrotik.username` / `mikrotik.password` → your login credentials
* `dashboard.ingest_url` → the real URL of `ingest.php` on your host
* `dashboard.api_key` → the same key you set in `backend/config.php`

### 4) Manual test before scheduling

```powershell id="p6c9dt"
python mikrotik_agent.py
```

If it works, you should see `send successful: {'success': True, ...}` in the terminal and in `agent.log`.

Then open `api_devices.php` in your browser — you should see `mikrotik-main` with live data.

### Common issues

| Error                                         | Likely cause                                                                                                    |
| --------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `Connection refused` or timeout to the router | The API service (port 8728) is not enabled, or MikroTik’s firewall is blocking your Windows machine’s IP        |
| `Invalid user name or password`               | Wrong credentials, or the user does not have API access (the user must belong to a group with the `api` policy) |
| It works, but `temperature_c: null`           | That is normal — many simple RouterBoards do not have a temperature sensor                                      |
| Connection error to `ingest_url`              | Wrong URL, or `http` was used instead of `https`                                                                |

## Scheduling with Task Scheduler

1. Open **Task Scheduler** from the Start Menu

2. Choose **Create Task** (not Create Basic Task, since we need more control)

3. In the **General** tab:

   * Name: `MikroTik Dashboard Agent`
   * Check **Run whether user is logged on or not**

4. In the **Triggers** tab, click **New**:

   * Begin the task: **On a schedule**
   * Repeat task every: **1 minute** (or every 2–5 minutes, whichever you prefer)
   * For a duration of: **Indefinitely**

5. In the **Actions** tab, click **New**:

   * Action: **Start a program**

   * Program/script: the full path to `python.exe` (you can find it with `where python` in PowerShell)

   * Add arguments: the full path to the script, for example:

     ```text
     "C:\Users\Rahi\homelab-dashboard\agent\mikrotik_agent.py"
     ```

   * Start in: the path to the `agent` folder. This matters, because the script looks for `config.json` in the same folder:

     ```text
     C:\Users\Rahi\homelab-dashboard\agent
     ```

6. In the **Conditions** tab, uncheck **Start the task only if the computer is on AC power** if this is a laptop

7. Save it. Windows will ask for your password because **Run whether user is logged on or not** is enabled

### Testing Task Scheduler

After creating it, right-click the task and choose **Run**. Then check `agent.log` to see if a new entry was added.

## Next step

Add Cisco support next, then HPE, and after that the dashboard frontend.

---

# Cisco Agent — Phase 3

The `cisco_agent.py` script connects to a Cisco switch/router through **SNMP v2c** and collects CPU, temperature (if there is an environmental sensor), uptime, and total traffic across all interfaces.

## What I tested

* SNMP get/walk itself was tested against a real SNMP agent (`net-snmp`) — not just library import tests.
* Cisco-style OIDs for CPU, temperature, and interface traffic were simulated on that agent and parsed correctly.
* The full path (`get_cisco_metrics` → `send_to_dashboard` → `ingest.php` → `api_devices.php`) ran successfully end to end once.

I did not have a real Cisco switch available, so the final test was done against a simulated SNMP agent (`net-snmp` with manually configured OIDs), not actual Cisco hardware. The OIDs and approach are standard (`CISCO-PROCESS-MIB` and `CISCO-ENVMON-MIB`), but you should still check the first real run carefully.

## Installation and setup

### 1) Libraries

If you already installed `requirements.txt`, then `pysnmp` is already there too:

```powershell id="c7r4lm"
pip install -r requirements.txt
```

### 2) Enable SNMP on the Cisco device

Log in to the switch through console or SSH:

```text id="h9s2ky"
enable
configure terminal
snmp-server community YOUR_COMMUNITY_STRING RO
end
write memory
```

Use a community string that is hard to guess. Do not use `public`.

### 3) Create the config

```powershell id="w4n8vf"
Copy-Item cisco_config.example.json cisco_config.json
notepad cisco_config.json
```

You need to set:

* `cisco.host` → the switch IP
* `cisco.community` → the community string you created above
* `dashboard.ingest_url` and `dashboard.api_key` → same as before, from `backend/config.php`

### 4) Manual test

```powershell id="r1b6dc"
python cisco_agent.py
```

If it works, check `cisco_agent.log` and open `api_devices.php` in your browser.

### Common issues

| Error                 | Likely cause                                                                                                    |
| --------------------- | --------------------------------------------------------------------------------------------------------------- |
| Timeout / no response | The Cisco firewall, another device in between, or the switch itself is blocking UDP 161, or SNMP is not enabled |
| `temperature_c: null` | The model does not expose `CISCO-ENVMON-MIB` — normal for some simpler switches                                 |
| Community error       | Wrong community string, or it does not have read-only access                                                    |

## Scheduling with Task Scheduler

The setup is the same as the MikroTik agent above — create a new task that runs `cisco_agent.py` instead of `mikrotik_agent.py`.

You can keep using the same `agent` folder as the **Start in** path, because `cisco_config.json` has a different name from MikroTik’s `config.json`, so they do not conflict.

## Next step

Add HPE support through the Redfish / iLO API, then move on to the frontend.

---

# HPE Agent — Phase 4

The `hpe_agent.py` script connects to an HPE server through the **Redfish API**, which is the standard supported by iLO.

## The important part: iLO does not expose everything

Unlike MikroTik and Cisco, iLO is an out-of-band controller, separate from the server operating system. That means some data is available, and some is not.

**Available:**

* Temperature from all sensors (CPU, air inlet, DIMM, etc.) — the highest reading is reported
* Instantaneous power draw in watts, if the model supports it
* Fan status and fan count
* Server model and serial number

**Not available in this version:**

* CPU usage percentage — that is OS-level data, not out-of-band hardware data
* OS uptime — iLO can tell whether power is on or off, not how long Windows or Linux has been running
* Network traffic on the NICs — the Redfish standard does not define a byte counter for this

If you want those three later, you would need a lightweight agent running inside the server on Windows or Linux. That is a separate phase.

## What I tested

* The full real HTTP path was tested against a simulated Redfish server: root discovery → Chassis → Thermal → Power
* Picking the highest temperature from multiple sensors worked correctly, and `Absent` sensors were ignored
* A wrong-credentials error (`401`) was handled correctly with a clear message
* The full path to the dashboard worked, including `power_watts`, `model`, and `fan_count` in `extra`

I did not have access to a real HPE server, so the testing was done against a simulated Redfish agent, not actual iLO. The JSON structure follows the Redfish schema, but you should still check the first real run carefully.

## Installation and setup

### 1) Find your iLO address and credentials

The iLO address is usually a separate IP, not the IP of the server’s Windows or Linux OS. You normally open it in a browser, something like `https://10.0.0.5`. The username and password are the same ones you use for the iLO web interface.

### 2) Create the config

```powershell id="q5d2nv"
Copy-Item hpe_config.example.json hpe_config.json
notepad hpe_config.json
```

You need to set:

* `hpe.ilo_url` → the iLO address with `https://`
* `hpe.username` / `hpe.password` → the iLO login credentials
* `dashboard.ingest_url` and `dashboard.api_key` → same as before

### 3) About `verify_ssl`

iLO often uses a self-signed certificate, so this is set to `false` by default to avoid certificate errors. If you have installed a valid certificate on iLO, you can change it to `true`.

### 4) Manual test

```powershell id="x7v1hk"
python hpe_agent.py
```

If it works, check `hpe_agent.log` — you should see temperature, power, and the server model — and open `api_devices.php` in your browser.

### Common issues

| Error                         | Likely cause                                                                       |
| ----------------------------- | ---------------------------------------------------------------------------------- |
| `401 Unauthorized`            | Wrong iLO username/password                                                        |
| Timeout / connection error    | Wrong iLO address, or your Windows machine cannot reach the iLO management network |
| `temperature_c: null`         | Unlikely, but it means no sensor was found in the `Enabled` state                  |
| `power_watts` is always empty | Some entry-level HPE models do not support instantaneous power reporting           |

## Scheduling with Task Scheduler

The setup is the same as the previous two agents — create a new task that runs `hpe_agent.py`.

`hpe_config.json` has its own name, so it does not conflict with the MikroTik or Cisco config files.

## Next step

All three agents — MikroTik, Cisco, and HPE — are ready. The next piece is the frontend: one page that shows all three in a single place, with colored cards and history charts.
