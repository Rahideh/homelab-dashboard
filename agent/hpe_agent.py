#!/usr/bin/env python3
"""
HPE Agent — Homelab Dashboard (فاز ۴)

از طریق Redfish API (استاندارد صنعتی که iLO 4/5/6 ازش پشتیبانی می‌کنه) به
سرور HPE وصل می‌شه و اطلاعات محیطی (دما، توان مصرفی، فن‌ها) رو می‌گیره.

نصب پیش‌نیاز:
    pip install requests

نحوه‌ی استفاده:
    1. از hpe_config.example.json یه کپی به اسم hpe_config.json بساز و پرش کن
    2. python hpe_agent.py

⚠️ نکته‌ی مهم و صادقانه درباره‌ی این‌که Redfish/iLO چی می‌ده و چی نمی‌ده:
    برخلاف MikroTik و Cisco، iLO یه کنترلر جدا از سیستم‌عامل سروره (out-of-band)،
    پس بعضی چیزا که شاید فکرش رو بکنی در دسترسه، در واقع نیست:

    ✅ در دسترس (و این Agent می‌گیرتشون):
        - دما (همه‌ی سنسورهای حرارتی: CPU، اینلت، DIMM و...)
        - توان مصرفی لحظه‌ای (وات) — اگه سرورت این قابلیت رو پشتیبانی کنه
        - وضعیت و تعداد فن‌ها
        - مدل و سریال سرور (برای اطلاعات، نه مانیتورینگ)

    ❌ در دسترس نیست (چون این‌ها اطلاعات سطح سیستم‌عامل هستن، نه سخت‌افزار):
        - درصد مصرف CPU (این‌جا cpu_percent همیشه None می‌مونه مگه بعداً یه
          agent سطح OS جدا بسازیم که از داخل ویندوز/لینوکس سرور خودش گزارش بده)
        - Uptime سیستم‌عامل (iLO فقط از وضعیت پاور روشن/خاموش خبر داره، نه از
          مدت زمانی که OS بالا اومده)
        - ترافیک شبکه‌ی رابط‌های سرور (Redfish استاندارد شمارنده‌ی بایت
          ورودی/خروجی رو برای NIC های host تعریف نکرده)

    این محدودیت مال طراحی Redfish/iLO هست، نه کم‌کاری این Agent. اگه بعداً
    خواستی CPU/uptime/ترافیک واقعی سرور رو هم داشته باشی، باید یه اسکریپت
    کوچیک داخل خود ویندوز/لینوکس سرور اجرا بشه (فاز جداگانه).
"""

import sys
import warnings
from pathlib import Path
from typing import Optional

import requests
from requests.auth import HTTPBasicAuth

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import setup_logging, load_config, send_to_dashboard

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "hpe_config.json"
LOG_PATH = SCRIPT_DIR / "hpe_agent.log"

log = setup_logging("hpe-agent", LOG_PATH)


def redfish_get(session: requests.Session, base_url: str, path: str, verify_ssl: bool) -> Optional[dict]:
    url = base_url.rstrip("/") + path
    try:
        resp = session.get(url, verify=verify_ssl, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        log.warning(f"درخواست به {path} با خطا مواجه شد: {e}")
        return None


def get_hpe_metrics(cfg: dict) -> dict:
    hpe_cfg = cfg["hpe"]
    base_url = hpe_cfg["ilo_url"].rstrip("/")  # مثلاً https://10.0.0.5
    verify_ssl = hpe_cfg.get("verify_ssl", False)

    # iLO معمولاً گواهی self-signed داره؛ اگه verify_ssl=False باشه (پیش‌فرض)
    # هشدار InsecureRequestWarning رو خاموش می‌کنیم که لاگ رو شلوغ نکنه
    if not verify_ssl:
        warnings.filterwarnings("ignore", message="Unverified HTTPS request")

    session = requests.Session()
    session.auth = HTTPBasicAuth(hpe_cfg["username"], hpe_cfg["password"])
    session.headers.update({"Accept": "application/json"})

    extra = {}
    temperature_c = None
    power_watts = None

    # --- مرحله ۱: پیدا کردن مسیر Chassis از ریشه‌ی Redfish ---
    root = redfish_get(session, base_url, "/redfish/v1/", verify_ssl)
    if root is None:
        raise RuntimeError("نتونستیم به /redfish/v1/ وصل بشیم — آدرس iLO یا احراز هویت رو چک کن")

    chassis_link = root.get("Chassis", {}).get("@odata.id")
    if not chassis_link:
        raise RuntimeError("مسیر Chassis توی پاسخ Redfish پیدا نشد")

    chassis_collection = redfish_get(session, base_url, chassis_link, verify_ssl)
    if chassis_collection is None:
        raise RuntimeError("نتونستیم لیست Chassis رو بخونیم")

    chassis_members = chassis_collection.get("Members", [])
    if not chassis_members:
        raise RuntimeError("هیچ Chassis ای توی این سرور پیدا نشد")

    # --- مرحله ۲: برای هر Chassis، دما و توان رو می‌خونیم ---
    # (اکثر سرورهای تک‌بدنه فقط یه Chassis دارن، ولی این کد عمومی نوشته شده)
    all_temperatures = []
    for member in chassis_members:
        chassis_path = member.get("@odata.id")
        if not chassis_path:
            continue
        chassis_detail = redfish_get(session, base_url, chassis_path, verify_ssl)
        if chassis_detail is None:
            continue

        if "Model" not in extra and chassis_detail.get("Model"):
            extra["model"] = chassis_detail.get("Model")
        if "serial_number" not in extra and chassis_detail.get("SerialNumber"):
            extra["serial_number"] = chassis_detail.get("SerialNumber")

        # --- دما ---
        thermal_link = chassis_detail.get("Thermal", {}).get("@odata.id")
        if thermal_link:
            thermal = redfish_get(session, base_url, thermal_link, verify_ssl)
            if thermal:
                for sensor in thermal.get("Temperatures", []):
                    reading = sensor.get("ReadingCelsius")
                    status = sensor.get("Status", {}).get("State", "")
                    if reading is not None and status != "Absent":
                        all_temperatures.append(reading)

                fan_states = [
                    fan.get("Status", {}).get("Health", "Unknown")
                    for fan in thermal.get("Fans", [])
                ]
                if fan_states:
                    extra["fan_count"] = len(fan_states)
                    extra["fans_healthy"] = all(s == "OK" for s in fan_states)

        # --- توان مصرفی (اختیاری، بعضی مدل‌ها ندارن) ---
        power_link = chassis_detail.get("Power", {}).get("@odata.id")
        if power_link:
            power = redfish_get(session, base_url, power_link, verify_ssl)
            if power:
                power_controls = power.get("PowerControl", [])
                if power_controls:
                    reading = power_controls[0].get("PowerConsumedWatts")
                    if reading is not None:
                        power_watts = reading

    if all_temperatures:
        # بیشترین دمای بین همه‌ی سنسورها رو گزارش می‌کنیم (محافظه‌کارانه‌تر برای هشدار)
        temperature_c = float(max(all_temperatures))
        extra["sensor_count"] = len(all_temperatures)

    if power_watts is not None:
        extra["power_watts"] = power_watts

    return {
        # این سه مورد از طریق Redfish/iLO در دسترس نیستن (توضیح کامل بالای فایل) —
        # None فرستادنشون عمدیه، باگ نیست
        "cpu_percent": None,
        "uptime_seconds": None,
        "traffic_rx_bytes": None,
        "traffic_tx_bytes": None,
        "temperature_c": temperature_c,
        "extra": extra,
    }


def main():
    cfg = load_config(CONFIG_PATH, log)
    log.info("شروع جمع‌آوری اطلاعات از سرور HPE (Redfish/iLO)...")

    try:
        metrics = get_hpe_metrics(cfg)
    except Exception as e:
        log.error(f"خطا در اتصال Redfish به iLO: {e}")
        log.error(
            "چک کن: ۱) آدرس iLO (https://آی‌پی) درسته ۲) یوزر/پسورد iLO درسته "
            "۳) اکانت iLO دسترسی 'Login' و 'Configure iLO Settings' حداقلی داره "
            "۴) اگه verify_ssl=true گذاشتی و گواهی self-signed داری، بذارش false"
        )
        sys.exit(1)

    log.info(
        f"دما: {metrics['temperature_c']} | "
        f"توان: {metrics['extra'].get('power_watts')} وات | "
        f"مدل: {metrics['extra'].get('model')}"
    )

    success = send_to_dashboard(cfg, metrics, log)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
