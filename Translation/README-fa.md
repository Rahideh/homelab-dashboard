**[English](../README.md) | فارسی**

# Homelab Monitoring Dashboard 🖥️📡

داشبورد ساده‌ی مانیتورینگ برای هوم‌لب، با اجرا روی **هاست اشتراکی PHP**.
بدون VPS، بدون root access، و بدون نیاز به زیرساخت اضافه.
برای مانیتور کردن **MikroTik**، **Cisco** و سرورهای **HPE** در یک جا.

## Features

* نمایش وضعیت زنده‌ی هر دستگاه
* CPU / دما / ترافیک
* نمودار تاریخچه
* ثبت هشدارها برای قطعی، وصلی و دمای بالا
* هشدار دمای قابل تنظیم برای هر دستگاه
* معماری push-based برای شبکه‌های پشت NAT
* Agent جدا برای:

  * MikroTik با RouterOS API
  * Cisco با SNMP
  * HPE با Redfish API (iLO)
* محافظت داشبورد با HTTP Basic Auth
* رابط کاربری تیره و ساده

## Preview

<!-- اگر خواستی، اسکرین‌شات را اینجا فعال کن:
![Dashboard](./screenshots/dashboard.png)
-->

## Architecture

هاست اشتراکی به شبکه‌ی داخلی هوم‌لب دسترسی مستقیم ندارد، پس جریان کار این‌طوری است:

```text
[MikroTik]  ─┐
[Cisco]      ├─→  Python agents روی یک دستگاه همیشه‌روشن در هوم‌لب
[HPE/iLO]   ─┘
                     │
                     │  POST دوره‌ای
                     ▼
            backend/ingest.php  (PHP + SQLite)
                     │
                     ▼
            backend/api_*.php  ←── frontend/
```

## Structure

```text
homelab-dashboard/
├── backend/
├── agent/
├── frontend/
├── screenshots/
├── frontend_auth_helper/
└── .gitignore
```

## Deploy

### Requirements

* PHP 7.4+ با SQLite (`pdo_sqlite`)
* یک دستگاه همیشه‌روشن برای اجرای Agentها
* Python 3.9+ روی همان دستگاه

### 1) Backend

1. پوشه‌ی `backend/` را آپلود کن
2. `config.example.php` را به `config.php` کپی کن و API key را تنظیم کن
3. `db_init.php` را یک‌بار اجرا کن و بعد حذف/rename کن
4. یک درخواست تست به `ingest.php` بفرست

### 2) Agentها

راهنمای کامل هر سه Agent داخل [`agent/README.md`](../agent/README.md) هست.

### 3) Frontend

1. پوشه‌ی `frontend/` را کنار `backend/` آپلود کن
2. اگر مسیرها فرق دارد، `frontend/config.js` را اصلاح کن
3. داشبورد را باز کن

### Optional: password protection

اگر خواستی داشبورد را با پسورد ببندی:

1. از `frontend_auth_helper/generate_hash.php` برای ساخت hash استفاده کن
2. `show_path.php` را موقتاً برای گرفتن مسیر واقعی سرور آپلود کن
3. `.htaccess` و `.htpasswd` را تنظیم کن
4. فایل‌های کمکی را بعدش حذف کن

## Test `ingest.php`

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

Expected response:

```json
{"success": true, "device_id": 1}
```

## Security

فایل‌های حساس داخل git نمی‌آیند. قبل از push این‌ها را چک کن:

```bash
git status
```

نباید staged شده باشند:

* `backend/config.php`
* `agent/config.json`
* `agent/cisco_config.json`
* `agent/hpe_config.json`
* `frontend/.htaccess`
* `frontend/.htpasswd`
* `backend/database.sqlite`

## Built with

PHP · SQLite · Python (`routeros_api`, `pysnmp`, `requests`) · Chart.js

## License

MIT — برای استفاده‌ی شخصی آزاد است، با attribution.
