#!/usr/bin/env python3
"""
MikroTik Agent — Homelab Dashboard (فاز ۲)

این اسکریپت یه‌بار اجرا می‌شه: به MikroTik وصل می‌شه، CPU/دما/آپتایم/ترافیک
رو می‌خونه، و به ingest.php روی هاست می‌فرسته. تکرار دوره‌ای (هر ۱-۲ دقیقه)
با Task Scheduler ویندوز انجام می‌شه — نه با یه حلقه‌ی داخلی توی خود اسکریپت.

نصب پیش‌نیازها:
    pip install routeros_api requests

نحوه‌ی استفاده:
    1. از config.example.json یه کپی به اسم config.json بساز و پرش کن
    2. python mikrotik_agent.py
"""

import re
import sys
from pathlib import Path
from typing import Optional

import routeros_api

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import setup_logging, load_config, send_to_dashboard

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.json"
LOG_PATH = SCRIPT_DIR / "agent.log"

log = setup_logging("mikrotik-agent", LOG_PATH)


def parse_uptime_to_seconds(uptime_str: Optional[str]) -> int:
    """
    تبدیل فرمت uptime روتراس (مثلاً '4w3d12h30m45s') به ثانیه.
    هر بخش (هفته/روز/ساعت/دقیقه/ثانیه) اختیاریه.
    """
    if not uptime_str:
        return 0
    pattern = r"(?:(\d+)w)?(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?"
    match = re.match(pattern, uptime_str)
    if not match:
        return 0
    parts = [int(x) if x else 0 for x in match.groups()]
    weeks, days, hours, minutes, seconds = parts
    return weeks * 7 * 86400 + days * 86400 + hours * 3600 + minutes * 60 + seconds


def extract_temperature(health_data) -> Optional[float]:
    """
    /system/health بسته به نسخه‌ی RouterOS فرمت متفاوتی برمی‌گردونه:
      - RouterOS 7.x: لیستی از دیکشنری‌ها مثل {'name': 'temperature', 'value': '45'}
      - بعضی مدل‌های قدیمی‌تر: ممکنه اصلاً همچین سنسوری نداشته باشن
    اگه دما پیدا نشه (سنسور نداشته باشه)، None برمی‌گردونه — این طبیعیه و خطا نیست.
    """
    if not health_data:
        return None
    if isinstance(health_data, list):
        for entry in health_data:
            name = entry.get("name", "")
            if name in ("temperature", "cpu-temperature", "board-temperature"):
                try:
                    return float(entry.get("value"))
                except (TypeError, ValueError):
                    continue
    return None


def get_mikrotik_metrics(cfg: dict) -> dict:
    mt_cfg = cfg["mikrotik"]
    connection = routeros_api.RouterOsApiPool(
        mt_cfg["host"],
        username=mt_cfg["username"],
        password=mt_cfg["password"],
        port=mt_cfg.get("api_port", 8728),
        use_ssl=mt_cfg.get("use_ssl", False),
        plaintext_login=True,
    )
    try:
        api = connection.get_api()

        # --- CPU و Uptime و مدل بورد ---
        resource = api.get_resource("/system/resource").get()[0]
        cpu_load = float(resource.get("cpu-load", 0))
        uptime_seconds = parse_uptime_to_seconds(resource.get("uptime"))
        board_name = resource.get("board-name", "")

        # --- دما (اگه مدل روتر سنسور داشته باشه) ---
        temperature = None
        try:
            health_data = api.get_resource("/system/health").get()
            temperature = extract_temperature(health_data)
        except Exception as e:
            log.warning(f"نتونستیم /system/health رو بخونیم (شاید این مدل سنسور دما نداره): {e}")

        # --- ترافیک ---
        # پیش‌فرض: جمع رفت‌وآمد همه‌ی اینترفیس‌ها (به‌جز loopback)
        # اگه توی config یه interface خاص (مثلاً "ether1") مشخص کرده باشی، فقط همون حساب می‌شه
        traffic_interface = cfg.get("options", {}).get("traffic_interface")
        interfaces = api.get_resource("/interface").get()
        rx_total = 0
        tx_total = 0
        for iface in interfaces:
            if traffic_interface:
                if iface.get("name") != traffic_interface:
                    continue
            elif iface.get("type") == "loopback":
                continue
            try:
                rx_total += int(iface.get("rx-byte", 0))
                tx_total += int(iface.get("tx-byte", 0))
            except (TypeError, ValueError):
                continue

        return {
            "cpu_percent": cpu_load,
            "temperature_c": temperature,
            "uptime_seconds": uptime_seconds,
            "traffic_rx_bytes": rx_total,
            "traffic_tx_bytes": tx_total,
            "extra": {"board_name": board_name},
        }
    finally:
        connection.disconnect()


def main():
    cfg = load_config(CONFIG_PATH, log)
    log.info("شروع جمع‌آوری اطلاعات از MikroTik...")

    try:
        metrics = get_mikrotik_metrics(cfg)
    except Exception as e:
        log.error(f"خطا در اتصال به MikroTik: {e}")
        sys.exit(1)

    log.info(
        f"CPU: {metrics['cpu_percent']}% | "
        f"دما: {metrics['temperature_c']} | "
        f"Uptime: {metrics['uptime_seconds']} ثانیه | "
        f"RX: {metrics['traffic_rx_bytes']} | TX: {metrics['traffic_tx_bytes']}"
    )

    success = send_to_dashboard(cfg, metrics, log)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
