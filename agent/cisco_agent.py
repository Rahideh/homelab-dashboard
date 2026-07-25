#!/usr/bin/env python3
"""
Cisco Agent — Homelab Dashboard (فاز ۳)

از طریق SNMP (نسخه‌ی v2c) به سوییچ/روتر سیسکو وصل می‌شه و CPU، دما (اگه
سنسور محیطی داشته باشه)، آپتایم، و ترافیک اینترفیس‌ها رو می‌خونه، بعد به
ingest.php می‌فرسته. مثل mikrotik_agent.py، این اسکریپت یه‌بار اجرا می‌شه
و تکرارش رو Task Scheduler انجام می‌ده.

نصب پیش‌نیاز:
    pip install pysnmp requests

نحوه‌ی استفاده:
    1. از config.example.json یه کپی به اسم config.json بساز و پرش کن
    2. python cisco_agent.py

OID های استفاده‌شده (استاندارد سیسکو):
    - CPU (CISCO-PROCESS-MIB, cpmCPUTotal5secRev): 1.3.6.1.4.1.9.9.109.1.1.1.1.3
    - دما (CISCO-ENVMON-MIB, ciscoEnvMonTemperatureStatusValue): 1.3.6.1.4.1.9.9.13.1.3.1.3
    - آپتایم (SNMPv2-MIB, sysUpTime): 1.3.6.1.2.1.1.3.0
    - ترافیک ورودی (IF-MIB, ifInOctets): 1.3.6.1.2.1.2.2.1.10
    - ترافیک خروجی (IF-MIB, ifOutOctets): 1.3.6.1.2.1.2.2.1.16

⚠️ نکته: این OID ها روی اکثر سوییچ/روترهای سیسکو (از جمله سری Catalyst) استانداردن،
ولی بعضی مدل‌های خیلی قدیمی یا ورودی ممکنه CISCO-ENVMON-MIB (دما) رو نداشته باشن؛
در این صورت temperature_c برابر None می‌مونه که طبیعیه.
"""

import sys
from pathlib import Path
from typing import Optional

from pysnmp.hlapi.v3arch.asyncio import (
    SnmpEngine,
    CommunityData,
    UdpTransportTarget,
    ContextData,
    ObjectType,
    ObjectIdentity,
    get_cmd,
    walk_cmd,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import setup_logging, load_config, send_to_dashboard

import asyncio

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "cisco_config.json"
LOG_PATH = SCRIPT_DIR / "cisco_agent.log"

log = setup_logging("cisco-agent", LOG_PATH)

OID_UPTIME = "1.3.6.1.2.1.1.3.0"
OID_CPU_5SEC = "1.3.6.1.4.1.9.9.109.1.1.1.1.3"
OID_TEMPERATURE = "1.3.6.1.4.1.9.9.13.1.3.1.3"
OID_IF_IN_OCTETS = "1.3.6.1.2.1.2.2.1.10"
OID_IF_OUT_OCTETS = "1.3.6.1.2.1.2.2.1.16"


async def snmp_get(engine, community, target, oid: str):
    error_indication, error_status, error_index, var_binds = await get_cmd(
        engine, community, target, ContextData(), ObjectType(ObjectIdentity(oid))
    )
    if error_indication:
        raise RuntimeError(str(error_indication))
    if error_status:
        raise RuntimeError(f"{error_status.prettyPrint()} در ایندکس {error_index}")
    return var_binds[0]


async def snmp_walk(engine, community, target, oid: str) -> list:
    """
    Walk کردن یه زیردرخت OID (مثلاً کل جدول CPU یا دما یا اینترفیس‌ها).
    اگه دستگاه اصلاً این OID رو نداشته باشه (مثلاً سنسور دما نداره)، لیست خالی برمی‌گرده.
    """
    results = []
    try:
        async for (error_indication, error_status, error_index, var_binds) in walk_cmd(
            engine, community, target, ContextData(),
            ObjectType(ObjectIdentity(oid)),
            lexicographicMode=False,
        ):
            if error_indication:
                raise RuntimeError(str(error_indication))
            if error_status:
                raise RuntimeError(f"{error_status.prettyPrint()} در ایندکس {error_index}")
            results.extend(var_binds)
    except RuntimeError:
        raise
    return results


def parse_uptime_ticks_to_seconds(ticks) -> int:
    """sysUpTime بر حسب centisecond (صدم ثانیه) هست، نه ثانیه."""
    try:
        return int(ticks) // 100
    except (TypeError, ValueError):
        return 0


async def get_cisco_metrics_async(cfg: dict) -> dict:
    cisco_cfg = cfg["cisco"]
    engine = SnmpEngine()
    community = CommunityData(cisco_cfg["community"], mpModel=1)  # mpModel=1 یعنی SNMPv2c
    target = await UdpTransportTarget.create(
        (cisco_cfg["host"], cisco_cfg.get("port", 161)),
        timeout=cisco_cfg.get("timeout", 5),
        retries=cisco_cfg.get("retries", 2),
    )

    # --- Uptime ---
    uptime_varbind = await snmp_get(engine, community, target, OID_UPTIME)
    _, uptime_ticks = uptime_varbind
    uptime_seconds = parse_uptime_ticks_to_seconds(uptime_ticks)

    # --- CPU (میانگین بین همه‌ی هسته‌ها/پردازنده‌ها، اگه چند تا باشه) ---
    cpu_results = await snmp_walk(engine, community, target, OID_CPU_5SEC)
    cpu_values = [int(val) for _, val in cpu_results]
    cpu_percent = (sum(cpu_values) / len(cpu_values)) if cpu_values else None

    # --- دما (بیشترین مقدار بین همه‌ی سنسورها - برای هشدار محافظه‌کارانه‌تره) ---
    temperature = None
    try:
        temp_results = await snmp_walk(engine, community, target, OID_TEMPERATURE)
        temp_values = [int(val) for _, val in temp_results]
        if temp_values:
            temperature = float(max(temp_values))
    except Exception as e:
        log.warning(f"نتونستیم دما رو بخونیم (شاید این مدل CISCO-ENVMON-MIB نداره): {e}")

    # --- ترافیک (جمع کل اینترفیس‌ها) ---
    in_results = await snmp_walk(engine, community, target, OID_IF_IN_OCTETS)
    out_results = await snmp_walk(engine, community, target, OID_IF_OUT_OCTETS)
    rx_total = sum(int(val) for _, val in in_results)
    tx_total = sum(int(val) for _, val in out_results)

    return {
        "cpu_percent": cpu_percent,
        "temperature_c": temperature,
        "uptime_seconds": uptime_seconds,
        "traffic_rx_bytes": rx_total,
        "traffic_tx_bytes": tx_total,
        "extra": {"interface_count": len(in_results)},
    }


def get_cisco_metrics(cfg: dict) -> dict:
    return asyncio.run(get_cisco_metrics_async(cfg))


def main():
    cfg = load_config(CONFIG_PATH, log)
    log.info("شروع جمع‌آوری اطلاعات از سوییچ/روتر سیسکو (SNMP)...")

    try:
        metrics = get_cisco_metrics(cfg)
    except Exception as e:
        log.error(f"خطا در اتصال SNMP به سیسکو: {e}")
        log.error(
            "چک کن: ۱) community string درسته ۲) آی‌پی/پورت درسته "
            "۳) روی سیسکو دستور 'snmp-server community <string> RO' زده شده "
            "۴) فایروال بین ویندوز و سیسکو پورت UDP 161 رو بلاک نکرده"
        )
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
