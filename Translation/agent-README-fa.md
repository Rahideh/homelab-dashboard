**[English](../agent/agent-README-en.md) | فارسی**

# MikroTik Agent — فاز ۲

اسکریپت پایتونی که از MikroTik (از طریق RouterOS API) اطلاعات CPU، دما (در صورت وجود سنسور)، آپتایم، و ترافیک رو می‌خونه و به داشبورد (`ingest.php`) می‌فرسته.

## ✅ چی تست شده؟

- تبدیل فرمت uptime روتراس (`4w3d12h30m45s` و مشابه) به ثانیه — با ۷ سناریوی مختلف تست شد.
- خوندن دما از `/system/health` با فرمت RouterOS 7؛ اگه دستگاه سنسور دما نداشته باشه، بدون کرش `None` برمی‌گردونه.
- کل مسیر ارسال (`send_to_dashboard`) با دیتای شبیه‌سازی‌شده روی یه نسخه‌ی واقعی از `ingest.php` تست شد و داده درست توی داشبورد نشست.

⚠️ نکته: چون به یه دستگاه MikroTik واقعی دسترسی نداشتم، خود اتصال API (`get_mikrotik_metrics`) رو نمی‌تونستم مستقیماً تست کنم. منطق بر اساس مستندات و رفتار استاندارد کتابخونه‌ی `routeros_api` نوشته شده، ولی اولین اجرای واقعی روی روتر خودت رو با دقت چک کن (لاگ `agent.log` رو ببین).

## 📦 نصب روی ویندوز

### ۱. نصب Python (اگه نداری)
از [python.org](https://www.python.org/downloads/) نسخه‌ی جدید رو دانلود و نصب کن. موقع نصب حتماً تیک **"Add python.exe to PATH"** رو بزن.

بررسی نصب:
```powershell
python --version
```

### ۲. نصب کتابخونه‌های لازم
توی پوشه‌ی `agent`:
```powershell
pip install -r requirements.txt
```

### ۳. ساخت فایل config
از `config.example.json` یه کپی بگیر به اسم `config.json` و مقادیرش رو پر کن:

```powershell
Copy-Item config.example.json config.json
notepad config.json
```

مقادیری که باید عوض کنی:
- `mikrotik.host` → آی‌پی روتر (همون که باهاش وارد Winbox می‌شی)
- `mikrotik.username` / `mikrotik.password` → اطلاعات ورود
- `dashboard.ingest_url` → آدرس واقعی `ingest.php` روی هاستت
- `dashboard.api_key` → همون کلیدی که توی `backend/config.php` گذاشتی

### ۴. تست دستی (قبل از زمان‌بندی کردن)
```powershell
python mikrotik_agent.py
```

- اگه موفق بود، تو ترمینال و توی فایل `agent.log` می‌بینی: `ارسال موفق: {'success': True, ...}`
- برو `api_devices.php` رو توی مرورگر چک کن، باید `mikrotik-main` رو با دیتای واقعی ببینی.

### مشکلات رایج در این مرحله:
| خطا | دلیل احتمالی |
|---|---|
| `Connection refused` یا timeout به روتر | سرویس API (پورت 8728) فعال نیست یا فایروال MikroTik آی‌پی ویندوزت رو بلاک کرده |
| `Invalid user name or password` | یوزر/پس اشتباهه، یا یوزر دسترسی API نداره (توی MikroTik باید تو گروه‌ای باشه که policy `api` داشته باشه) |
| موفق ولی `temperature_c: null` | طبیعیه — مدل روترت سنسور دما نداره (خیلی از RouterBoard های ساده ندارن) |
| خطای اتصال به `ingest_url` | آدرس اشتباهه یا `https` رو اشتباه `http` نوشتی |

## ⏰ زمان‌بندی با Task Scheduler

۱. **Task Scheduler** رو از Start Menu باز کن
۲. **Create Task** (نه Create Basic Task، چون کنترل بیشتری می‌دیم)
۳. تب **General**:
   - Name: `MikroTik Dashboard Agent`
   - **Run whether user is logged on or not** رو انتخاب کن (تا وقتی لاگین نیستی هم اجرا بشه)
4. تب **Triggers** → **New**:
   - Begin the task: **On a schedule**
   - Repeat task every: **1 minute** (یا ۲-۵ دقیقه، هرچقدر می‌خوای)
   - for a duration of: **Indefinitely**
5. تب **Actions** → **New**:
   - Action: **Start a program**
   - Program/script: مسیر کامل `python.exe` (مثلاً با `where python` توی PowerShell پیدا کن)
   - Add arguments: مسیر کامل فایل، مثلاً:
     ```
     "C:\Users\Rahi\homelab-dashboard\agent\mikrotik_agent.py"
     ```
   - Start in: مسیر پوشه‌ی agent (خیلی مهمه، چون اسکریپت دنبال `config.json` توی همون پوشه می‌گرده):
     ```
     C:\Users\Rahi\homelab-dashboard\agent
     ```
6. تب **Conditions**: تیک "Start the task only if the computer is on AC power" رو اگه لپ‌تاپه بردار (وگرنه با باتری اجرا نمی‌شه)
7. ذخیره کن، رمز ویندوزت رو می‌خواد (چون "Run whether logged on or not" انتخاب شده)

### تست Task Scheduler
بعد از ساخت، روی تسک راست‌کلیک کن → **Run**. بعد `agent.log` رو چک کن ببین لاگ جدید اضافه شده یا نه.

## 📌 قدم بعدی

اضافه کردن Cisco به Agent، و بعدش HPE و فرانت‌اند داشبورد.

---

# Cisco Agent — فاز ۳

اسکریپت `cisco_agent.py` از طریق **SNMP (نسخه‌ی v2c)** به سوییچ/روتر سیسکو وصل می‌شه و CPU، دما (اگه سنسور محیطی داشته باشه)، آپتایم، و مجموع ترافیک همه‌ی اینترفیس‌ها رو می‌گیره.

## ✅ چی تست شده؟

- خود پروتکل SNMP (get و walk) با یه SNMP agent واقعی (net-snmp) تست شد — نه فقط import کتابخونه.
- OID های دقیقاً مشابه Cisco (CPU، دما، ترافیک اینترفیس) روی اون agent شبیه‌سازی شدن و parse درست انجام شد.
- کل مسیر (`get_cisco_metrics` → `send_to_dashboard` → `ingest.php` → `api_devices.php`) یک‌بار کامل با موفقیت اجرا شد.

⚠️ نکته: چون به یه سوییچ سیسکوی واقعی دسترسی نداشتم، تست نهایی روی SNMP agent شبیه‌سازی‌شده (net-snmp با OID های دستی) انجام شد، نه خود سیسکو. منطق و OID ها استانداردن (CISCO-PROCESS-MIB و CISCO-ENVMON-MIB)، ولی بازم **اولین اجرای واقعی رو با دقت چک کن**.

## 📦 نصب و راه‌اندازی

### ۱. کتابخونه‌ها (اگه از قبل `requirements.txt` رو نصب کردی، همین الان `pysnmp` هم نصب می‌شه)
```powershell
pip install -r requirements.txt
```

### ۲. فعال کردن SNMP روی سوییچ سیسکو (اگه هنوز نکردی)
از طریق کنسول/SSH وارد سوییچ شو:
```
enable
configure terminal
snmp-server community YOUR_COMMUNITY_STRING RO
end
write memory
```
`YOUR_COMMUNITY_STRING` رو یه چیز غیرقابل‌حدس بذار (نه `public`).

### ۳. ساخت config
```powershell
Copy-Item cisco_config.example.json cisco_config.json
notepad cisco_config.json
```
مقادیر لازم:
- `cisco.host` → آی‌پی سوییچ
- `cisco.community` → همون community string که بالا ساختی
- `dashboard.ingest_url` و `dashboard.api_key` → مثل قبل، از `backend/config.php`

### ۴. تست دستی
```powershell
python cisco_agent.py
```
موفق بود → `cisco_agent.log` رو چک کن و `api_devices.php` رو تو مرورگر ببین.

### مشکلات رایج:
| خطا | دلیل احتمالی |
|---|---|
| Timeout / no response | فایروال سیسکو یا شبکه‌ی بینابین پورت UDP 161 رو بلاک کرده، یا SNMP اصلاً فعال نیست |
| `temperature_c: null` | مدلت CISCO-ENVMON-MIB نداره — طبیعیه، خیلی از سوییچ‌های ساده‌تر این سنسور رو ندارن |
| خطای community | community string اشتباهه یا سطح دسترسی RO رو نداره |

## ⏰ زمان‌بندی با Task Scheduler
دقیقاً مثل MikroTik Agent (بخش بالا) — فقط یه Task جدید بساز که به‌جای `mikrotik_agent.py`، مسیر `cisco_agent.py` رو صدا بزنه. می‌تونی همون پوشه رو Start in بذاری چون `cisco_config.json` اسمش با `config.json` مربوط به MikroTik فرق داره و تداخلی پیش نمیاد.

## 📌 قدم بعدی

اضافه کردن HPE (از طریق Redfish/iLO API)، و بعدش فرانت‌اند داشبورد.

---

# HPE Agent — فاز ۴

اسکریپت `hpe_agent.py` از طریق **Redfish API** (استاندارد صنعتی که iLO ازش پشتیبانی می‌کنه) به سرور HPE وصل می‌شه.

## ⚠️ مهم‌ترین نکته: iLO همه‌چیز رو نمی‌ده

برخلاف MikroTik و Cisco، iLO یه کنترلر جدا از خود سیستم‌عامل سروره (out-of-band). این یعنی:

**✅ در دسترس:**
- دما (همه‌ی سنسورها — CPU، اینلت هوا، DIMM و...) — بیشترین مقدار گزارش می‌شه
- توان مصرفی لحظه‌ای (وات)، اگه مدلت پشتیبانی کنه
- وضعیت و تعداد فن‌ها
- مدل و سریال سرور

**❌ در دسترس نیست (و توی این نسخه `null` می‌مونه):**
- درصد مصرف CPU — چون این اطلاعات سطح سیستم‌عامله، نه سخت‌افزار out-of-band
- Uptime سیستم‌عامل — iLO فقط می‌دونه پاور روشنه یا نه، نه این‌که ویندوز/لینوکس چقدره بالاست
- ترافیک شبکه‌ی NIC های سرور — Redfish استاندارد شمارنده‌ی بایت رو برای این تعریف نکرده

اگه بعداً این سه‌تا رو هم خواستی، باید یه Agent سبک *داخل* خود سرور (روی ویندوز/لینوکسش) اجرا بشه — یه فاز جداست، بگو اگه خواستی بعداً بسازیمش.

## ✅ چی تست شده؟

- کل مسیر HTTP واقعی (نه mock کردن توابع) با یه سرور Redfish شبیه‌سازی‌شده تست شد: root discovery → Chassis → Thermal → Power.
- منطق انتخاب بیشترین دما از بین چند سنسور (و نادیده گرفتن سنسورهای `Absent`) درست کار کرد.
- خطای احراز هویت اشتباه (401) درست مدیریت شد و پیام خطای قابل‌فهم داد.
- مسیر کامل تا نشستن داده توی داشبورد (با `power_watts`, `model`, `fan_count` توی `extra`) با موفقیت اجرا شد.

⚠️ چون به یه سرور HPE واقعی دسترسی نداشتم، تست روی یه Redfish agent شبیه‌سازی‌شده انجام شد نه خود iLO. ساختار JSON دقیقاً مطابق اسکیمای استاندارد Redfish نوشته شده، ولی بازم اولین اجرای واقعی رو با دقت چک کن.

## 📦 نصب و راه‌اندازی

### ۱. پیدا کردن آدرس و اطلاعات ورود iLO
آدرس iLO معمولاً یه آی‌پی جداست (نه آی‌پی خود ویندوز/لینوکس سرور) — از طریق مرورگر بهش وصل می‌شی، چیزی شبیه `https://10.0.0.5`. یوزر/پسورد همونیه که برای ورود به رابط وب iLO استفاده می‌کنی.

### ۲. ساخت config
```powershell
Copy-Item hpe_config.example.json hpe_config.json
notepad hpe_config.json
```
مقادیر لازم:
- `hpe.ilo_url` → آدرس iLO با `https://`
- `hpe.username` / `hpe.password` → اطلاعات ورود iLO
- `dashboard.ingest_url` و `dashboard.api_key` → مثل قبل

### ۳. درباره‌ی `verify_ssl`
iLO معمولاً یه گواهی SSL خودامضا (self-signed) داره، پس پیش‌فرض روی `false` گذاشتیمش تا خطای گواهی نگیری. اگه یه گواهی معتبر روی iLO نصب کردی، می‌تونی `true` بذاریش.

### ۴. تست دستی
```powershell
python hpe_agent.py
```
موفق بود → `hpe_agent.log` رو چک کن (باید دما، توان، و مدل سرور رو ببینی) و `api_devices.php` رو تو مرورگر باز کن.

### مشکلات رایج:
| خطا | دلیل احتمالی |
|---|---|
| `401 Unauthorized` | یوزر/پسورد iLO اشتباهه |
| Timeout / connection error | آدرس iLO اشتباهه، یا ویندوزت به شبکه‌ی مدیریتی iLO دسترسی نداره |
| `temperature_c: null` | بعیده، ولی یعنی هیچ سنسوری در وضعیت `Enabled` پیدا نشد |
| `power_watts` همیشه خالیه | بعضی مدل‌های پایه‌ی HPE گزارش توان لحظه‌ای رو پشتیبانی نمی‌کنن — طبیعیه |

## ⏰ زمان‌بندی با Task Scheduler
دقیقاً مثل دو تای قبلی — یه Task جدید با `hpe_agent.py`. اسم `hpe_config.json` هم با بقیه تداخل نداره.

## 📌 قدم بعدی

هر سه Agent (MikroTik، Cisco، HPE) آماده‌ن. حالا نوبت فرانت‌انده — صفحه‌ای که وضعیت هر سه رو یه‌جا، با کارت‌های رنگی و گراف تاریخچه نشون بده.
