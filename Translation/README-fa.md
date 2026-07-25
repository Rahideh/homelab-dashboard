**[English](../README.md) | فارسی**

# Homelab Monitoring Dashboard 🖥️📡

داشبورد مانیتورینگ شبکه و سرورهای هوم‌لب — طراحی‌شده برای اجرا روی **هاست اشتراکی PHP** (بدون نیاز به VPS یا دسترسی root)، برای مانیتور کردن دستگاه‌های **MikroTik**، **Cisco**، و سرورهای **HPE** به‌صورت یک‌جا.

> ساخته‌شده توسط [Rahideh](https://trustit.ir) برای پروژه‌ی هوم‌لب شخصی — با کمک [Claude](https://claude.ai) (دستیار هوش مصنوعی Anthropic) در تمام مراحل کدنویسی و تست 🤖

---

## ✨ ویژگی‌ها

- 📊 داشبورد وب زنده با کارت‌های وضعیت هر دستگاه (آنلاین/آفلاین، CPU، دما، ترافیک)
- 📈 گراف تاریخچه‌ی CPU/دما/ترافیک برای هر دستگاه (با کلیک روی کارت)
- 🔔 لاگ خودکار هشدارها (قطعی، وصلی، دمای بالا)
- 🌡️ هشدار دمای قابل‌تنظیم به‌ازای هر دستگاه
- 🔌 معماری push-based — مناسب هاست اشتراکی که به شبکه‌ی داخلی هوم‌لب دسترسی نداره
- 🐍 Agent های پایتونی جدا برای هر نوع دستگاه:
  - **MikroTik** از طریق RouterOS API
  - **Cisco** از طریق SNMP
  - **HPE** از طریق Redfish API (iLO)
- 🔒 محافظت از داشبورد با HTTP Basic Auth (بدون نیاز به سیستم لاگین جداگانه)
- 🎨 ظاهر تیره‌ی ترمینالی، فونت Vazirmatn + JetBrains Mono، راست‌به‌چپ

## 📸 پیش‌نمایش

<!-- اگه اسکرین‌شات‌ها رو کنار همین README گذاشتی، این خط‌ها رو از کامنت دربیار:
![Dashboard](./screenshots/dashboard.png)
![Device history chart](./screenshots/chart-modal.png)
-->

## 🏗️ معماری

چون هاست اشتراکی به شبکه‌ی داخلی هوم‌لب (پشت NAT) دسترسی نداره، این پروژه معماری **push-based** داره:

```
[MikroTik]  ─┐
[Cisco]      ├─→  Agent های پایتونی (روی یه دستگاه همیشه‌روشن توی هوم‌لب)
[HPE/iLO]   ─┘         │
                        │  POST دوره‌ای (هر ۱-۵ دقیقه، با Task Scheduler)
                        ▼
              backend/ingest.php  (روی هاست اشتراکی، PHP + SQLite)
                        │
                        ▼
              backend/api_*.php  ←── frontend/ (داشبورد وب)
```

## 📁 ساختار پروژه

```
homelab-dashboard/
├── backend/              # API های PHP + دیتابیس SQLite
│   ├── config.example.php
│   ├── db_init.php
│   ├── ingest.php        # دریافت داده از Agent ها
│   ├── api_devices.php   # وضعیت فعلی دستگاه‌ها
│   ├── api_history.php   # تاریخچه (برای گراف)
│   └── api_alerts.php    # لاگ هشدارها
├── agent/                # اسکریپت‌های پایتونی جمع‌آوری داده
│   ├── common.py
│   ├── mikrotik_agent.py + config.example.json
│   ├── cisco_agent.py    + cisco_config.example.json
│   ├── hpe_agent.py      + hpe_config.example.json
│   ├── requirements.txt
│   └── README.md         # راهنمای کامل نصب هر Agent
├── frontend/              # داشبورد وب
│   ├── index.html
│   ├── style.css
│   ├── script.js
│   ├── config.js
│   └── .htaccess.example # محافظت با پسورد (اختیاری)
├── frontend_auth_helper/  # ابزارهای موقت ساخت پسورد داشبورد
└── .gitignore
```

## 🚀 راهنمای دیپلوی (هاست اشتراکی)

### پیش‌نیاز
- هاست اشتراکی با PHP 7.4+ و پشتیبانی از SQLite (`pdo_sqlite`)
- یه دستگاه همیشه‌روشن توی هوم‌لب (یا حتی یه PC ویندوزی که بیشتر وقت‌ها روشنه) برای اجرای Agent ها
- پایتون ۳.۹+ روی همون دستگاه، برای Agent ها

### فاز ۱: بک‌اند
۱. پوشه‌ی `backend/` رو آپلود کن (مثلاً به `public_html/dashboard/backend`)
۲. از `config.example.php` یه کپی بگیر به اسم `config.php` و کلید API رو با یه رشته‌ی تصادفی امن پر کن
۳. یک‌بار `db_init.php` رو از مرورگر اجرا کن، بعد پاکش کن یا rename کن
۴. با curl/Postman/PowerShell یه درخواست تست به `ingest.php` بزن (نمونه‌ها توی همین README پایین‌تر)

### فاز ۲-۴: Agent ها (MikroTik / Cisco / HPE)
راهنمای کامل هر سه (نصب پایتون، پر کردن config، فعال‌سازی API/SNMP/Redfish روی خود دستگاه، و زمان‌بندی با Task Scheduler ویندوز) توی [`agent/README.md`](../agent/README.md) هست.

### فاز ۵: فرانت‌اند
۱. پوشه‌ی `frontend/` رو کنار `backend/` آپلود کن
۲. اگه ساختار پوشه‌بندیت فرق داره، `frontend/config.js` رو با آدرس درست `backend` تنظیم کن
۳. برو به `https://yourdomain.com/dashboard/frontend/index.html`

### (اختیاری ولی پیشنهادی) محافظت از داشبورد با پسورد
۱. `frontend_auth_helper/generate_hash.php` رو **در یه مسیر خارج از frontend** (چون بعد از قفل شدن دیگه در دسترس نیست) موقتاً آپلود کن و باهاش هش پسورد بساز
۲. `frontend_auth_helper/show_path.php` رو (قبل از فعال کردن قفل) داخل `frontend/` آپلود کن تا مسیر کامل سرور رو بگیری
۳. از `frontend/.htaccess.example` یه کپی بگیر به اسم `.htaccess`، مسیر `AuthUserFile` رو با مسیر واقعی پر کن
۴. یه فایل `.htpasswd` توی `frontend/` بساز، خروجی مرحله‌ی ۱ رو (کامل، یه خط) توش بذار
۵. هر دو فایل کمکی (`generate_hash.php`, `show_path.php`) رو از روی هاست پاک کن

## 🧪 تست ingest.php (قبل از راه‌اندازی Agent واقعی)

**PowerShell:**
```powershell
$body = @{
    api_key = "کلید-api-ت"
    device_key = "mikrotik-main"
    display_name = "MikroTik hEX"
    device_type = "mikrotik"
    cpu_percent = 12.5
    temperature_c = 45.2
    uptime_seconds = 123456
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://yourdomain.com/dashboard/backend/ingest.php" -Method Post -Body $body -ContentType "application/json"
```

جواب موفق: `{"success": true, "device_id": 1}`

## 🔒 امنیت — قبل از push کردن حتماً بخون

این ریپازیتوری با `.gitignore` طوری تنظیم شده که فایل‌های حاوی اطلاعات حساس (کلید API واقعی، پسورد MikroTik/Cisco/iLO، فایل `.htpasswd`) هیچ‌وقت commit نشن. فقط نسخه‌ی `*.example.*` هرکدوم توی ریپو هست. **قبل از push، حتماً چک کن:**

```bash
git status
```

و مطمئن شو هیچ‌کدوم از این‌ها توی لیست فایل‌های commit‌شونده نیستن:
- `backend/config.php`
- `agent/config.json`, `agent/cisco_config.json`, `agent/hpe_config.json`
- `frontend/.htaccess`, `frontend/.htpasswd`
- `backend/database.sqlite`

## 🛠️ ساخته‌شده با

PHP · SQLite · Python (`routeros_api`, `pysnmp`, `requests`) · Chart.js · Vazirmatn & JetBrains Mono


## 📄 لایسنس

MIT — با رعایت، برای پروژه‌ی شخصی خودت هرجور می‌خوای استفاده کن.
