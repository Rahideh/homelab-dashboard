"""
common.py — کدهای مشترک بین Agent های مختلف (MikroTik, Cisco, HPE, ...)
هر Agent این ماژول رو ایمپورت می‌کنه تا مجبور نباشیم منطق ارسال به داشبورد
رو توی هر فایل از اول بنویسیم.
"""

import json
import logging
import sys
from pathlib import Path

import requests


def setup_logging(logger_name: str, log_file: Path) -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger(logger_name)


def load_config(config_path: Path, log: logging.Logger) -> dict:
    if not config_path.exists():
        log.error(
            f"فایل {config_path.name} پیدا نشد. از {config_path.stem}.example.json "
            "یه کپی بگیر، اسمش رو بذار config.json و مقادیرش رو پر کن."
        )
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def send_to_dashboard(cfg: dict, metrics: dict, log: logging.Logger) -> bool:
    """
    metrics باید شامل این کلیدها باشه (هرکدوم می‌تونه None باشه):
    cpu_percent, temperature_c, uptime_seconds, traffic_rx_bytes, traffic_tx_bytes, extra
    """
    dash_cfg = cfg["dashboard"]
    payload = {
        "api_key": dash_cfg["api_key"],
        "device_key": dash_cfg["device_key"],
        "display_name": dash_cfg.get("display_name"),
        "device_type": dash_cfg.get("device_type"),
        **metrics,
    }
    try:
        resp = requests.post(dash_cfg["ingest_url"], json=payload, timeout=10)
        if resp.status_code == 200:
            log.info(f"ارسال موفق: {resp.json()}")
            return True
        log.error(f"خطا از سرور (کد {resp.status_code}): {resp.text}")
        return False
    except requests.RequestException as e:
        log.error(f"خطا در اتصال به داشبورد: {e}")
        return False
