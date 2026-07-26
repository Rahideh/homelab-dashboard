**[English](../agent/README.md) | فارسی**

# MikroTik Agent — فاز ۲

این اسکریپت پایتونی از MikroTik با RouterOS API اطلاعات CPU، دما (اگر سنسور داشته باشد)، uptime و ترافیک را می‌خواند و به داشبورد (`ingest.php`) می‌فرستد.

## تست‌ها

* تبدیل uptime روتراس مثل `4w3d12h30m45s` به ثانیه، با ۷ سناریو
* خواندن دما از `/system/health` در RouterOS 7
* اگر دستگاه سنسور دما نداشته باشد، `None` برمی‌گرداند و کرش نمی‌کند
* مسیر کامل `send_to_dashboard` با دیتای شبیه‌سازی‌شده روی `ingest.php` واقعی تست شد

⚠️ نکته: به دستگاه MikroTik واقعی دسترسی نداشتم، پس خود اتصال API (`get_mikrotik_metrics`) مستقیم تست نشد. منطق بر اساس رفتار استاندارد `routeros_api` نوشته شده، ولی اولین اجرای واقعی را حتماً با دقت چک کن و `agent.log` را ببین.

## نصب روی ویندوز

### ۱) Python

اگر Python نداری، از [python.org](https://www.python.org/downloads/) نصب کن. موقع نصب تیک **Add python.exe to PATH** را بزن.

```powershell
python --version
```

### ۲) کتابخانه‌ها

داخل پوشه‌ی `agent`:

```powershell
pip install -r requirements.txt
```

### ۳) config

از `config.example.json` یک کپی بگیر و `config.json` بساز:

```powershell
Copy-Item config.example.json config.json
notepad config.json
```

مقادیر لازم:

* `mikrotik.host` → آی‌پی روتر
* `mikrotik.username` / `mikrotik.password` → اطلاعات ورود
* `dashboard.ingest_url` → آدرس `ingest.php`
* `dashboard.api_key` → همان کلید `backend/config.php`

### ۴) تست دستی

```powershell
python mikrotik_agent.py
```

اگر درست باشد، در ترمینال و `agent.log` چیزی شبیه این می‌بینی: `send successful: {'success': True, ...}`

بعد `api_devices.php` را در مرورگر باز کن؛ باید `mikrotik-main` را با داده‌ی واقعی ببینی.

### خطاهای رایج

| خطا                             | دلیل احتمالی                                                      |
| ------------------------------- | ----------------------------------------------------------------- |
| `Connection refused` یا timeout | API روتر فعال نیست یا فایروال MikroTik آی‌پی ویندوزت را بلاک کرده |
| `Invalid user name or password` | یوزر/پسورد اشتباه است یا دسترسی `api` ندارد                       |
| `temperature_c: null`           | طبیعی است؛ خیلی از RouterBoard های ساده سنسور دما ندارند          |
| خطای اتصال به `ingest_url`      | آدرس اشتباه است یا `https` را `http` زده‌ای                       |

## Task Scheduler

1. **Task Scheduler** را از Start Menu باز کن
2. **Create Task** را بزن
3. در تب **General**:

   * Name: `MikroTik Dashboard Agent`
   * گزینه‌ی **Run whether user is logged on or not** را فعال کن
4. در تب **Triggers** → **New**:

   * Begin the task: **On a schedule**
   * Repeat task every: **1 minute** (یا ۲ تا ۵ دقیقه)
   * For a duration of: **Indefinitely**
5. در تب **Actions** → **New**:

   * Action: **Start a program**
   * Program/script: مسیر کامل `python.exe`
   * Add arguments: مسیر کامل فایل، مثلاً:

```text
"C:\Users\Rahi\homelab-dashboard\agent\mikrotik_agent.py"
```

* Start in: مسیر پوشه‌ی `agent`:

```text
C:\Users\Rahi\homelab-dashboard\agent
```

6. در تب **Conditions**، اگر لپ‌تاپ است تیک **Start the task only if the computer is on AC power** را بردار
7. ذخیره کن و رمز ویندوز را وارد کن

### تست Task Scheduler

روی تسک راست‌کلیک کن و **Run** را بزن. بعد `agent.log` را چک کن.

## قدم بعدی

اضافه کردن Cisco، بعد HPE، و بعد فرانت‌اند داشبورد.

---

# Cisco Agent — فاز ۳

اسکریپت `cisco_agent.py` از طریق **SNMP v2c** به سوییچ/روتر سیسکو وصل می‌شود و CPU، دما (اگر سنسور محیطی داشته باشد)، uptime و مجموع ترافیک اینترفیس‌ها را می‌گیرد.

## تست‌ها

* خود SNMP get/walk با یک agent واقعی (`net-snmp`) تست شد
* OID های مشابه Cisco برای CPU، دما و ترافیک شبیه‌سازی و درست parse شدند
* مسیر کامل `get_cisco_metrics` → `send_to_dashboard` → `ingest.php` → `api_devices.php` یک‌بار end to end اجرا شد

⚠️ نکته: به سوییچ سیسکوی واقعی دسترسی نداشتم، پس تست نهایی روی `net-snmp` شبیه‌سازی‌شده انجام شد، نه سخت‌افزار واقعی. منطق و OID ها استاندارد هستند (`CISCO-PROCESS-MIB` و `CISCO-ENVMON-MIB`)، ولی اولین اجرای واقعی را با دقت چک کن.

## نصب و راه‌اندازی

### ۱) کتابخانه‌ها

```powershell
pip install -r requirements.txt
```

### ۲) فعال کردن SNMP روی Cisco

از طریق SSH یا کنسول:

```text
enable
configure terminal
snmp-server community YOUR_COMMUNITY_STRING RO
end
write memory
```

`YOUR_COMMUNITY_STRING` را چیز قابل‌حدس نگذار.

### ۳) config

```powershell
Copy-Item cisco_config.example.json cisco_config.json
notepad cisco_config.json
```

مقادیر لازم:

* `cisco.host` → آی‌پی سوییچ
* `cisco.community` → community string
* `dashboard.ingest_url` و `dashboard.api_key` → مثل قبل

### ۴) تست دستی

```powershell
python cisco_agent.py
```

اگر موفق بود، `cisco_agent.log` را چک کن و `api_devices.php` را باز کن.

### خطاهای رایج

| خطا                   | دلیل احتمالی                               |
| --------------------- | ------------------------------------------ |
| Timeout / no response | SNMP فعال نیست یا UDP 161 در مسیر بلاک شده |
| `temperature_c: null` | مدل شما `CISCO-ENVMON-MIB` ندارد           |
| community error       | community string اشتباه است یا RO نیست     |

## Task Scheduler

مثل MikroTik است؛ فقط به‌جای `mikrotik_agent.py`، فایل `cisco_agent.py` را اجرا کن.
می‌توانی همان پوشه‌ی `agent` را برای **Start in** بگذاری؛ چون فایل config اسم جدا دارد و تداخلی نیست.

## قدم بعدی

اضافه کردن HPE با Redfish / iLO، بعد فرانت‌اند.

---

# HPE Agent — فاز ۴

اسکریپت `hpe_agent.py` از طریق **Redfish API** به سرور HPE و iLO وصل می‌شود.

## نکته مهم

iLO out-of-band است و مثل سیستم‌عامل سرور همه‌چیز را نمی‌دهد.

**داده‌های در دسترس:**

* دما از همه‌ی سنسورها
* توان مصرفی لحظه‌ای، اگر مدل پشتیبانی کند
* وضعیت و تعداد فن‌ها
* مدل و سریال سرور

**داده‌های در دسترس نیست:**

* درصد CPU
* uptime سیستم‌عامل
* ترافیک NIC ها

اگر بعداً این‌ها را بخواهی، باید یک Agent داخل خود سرور اجرا شود؛ این نسخه فقط داده‌های hardware / iLO را می‌گیرد.

## تست‌ها

* مسیر کامل HTTP روی یک Redfish server شبیه‌سازی‌شده تست شد
* انتخاب بالاترین دما بین چند سنسور درست کار کرد
* خطای 401 درست هندل شد
* مسیر نهایی تا داشبورد، با `power_watts`، `model` و `fan_count` در `extra` تست شد

⚠️ چون به HPE واقعی دسترسی نداشتم، تست روی شبیه‌ساز انجام شد، نه iLO واقعی.

## نصب و راه‌اندازی

### ۱) آدرس و اطلاعات iLO

iLO معمولاً یک IP جداست، مثل `https://10.0.0.5`.
یوزر و پسورد همان اطلاعات ورود به وب‌اینترفیس iLO هستند.

### ۲) config

```powershell
Copy-Item hpe_config.example.json hpe_config.json
notepad hpe_config.json
```

مقادیر لازم:

* `hpe.ilo_url` → آدرس iLO با `https://`
* `hpe.username` / `hpe.password` → اطلاعات ورود iLO
* `dashboard.ingest_url` و `dashboard.api_key` → مثل قبل

### ۳) `verify_ssl`

iLO معمولاً self-signed است، برای همین پیش‌فرض روی `false` گذاشته شده.
اگر certificate معتبر داری، می‌توانی `true` کنی.

### ۴) تست دستی

```powershell
python hpe_agent.py
```

اگر موفق بود، `hpe_agent.log` را چک کن و `api_devices.php` را باز کن.

### خطاهای رایج

| خطا                        | دلیل احتمالی                                        |
| -------------------------- | --------------------------------------------------- |
| `401 Unauthorized`         | یوزر/پسورد iLO اشتباه است                           |
| Timeout / connection error | آدرس iLO اشتباه است یا شبکه‌ی مدیریتی در دسترس نیست |
| `temperature_c: null`      | هیچ سنسور `Enabled` پیدا نشده                       |
| `power_watts` خالی است     | بعضی مدل‌های پایه‌ی HPE این قابلیت را ندارند        |

## Task Scheduler

مثل دو Agent قبلی؛ فقط `hpe_agent.py` را اجرا کن.
فایل `hpe_config.json` هم با بقیه تداخل ندارد.

## قدم بعدی

هر سه Agent آماده‌اند. قدم بعدی فرانت‌اند است؛ یک صفحه برای دیدن وضعیت هر سه دستگاه با کارت‌های رنگی و نمودار تاریخچه.
