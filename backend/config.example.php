<?php
/**
 * Homelab Dashboard - Configuration
 * این فایل رو بعد از آپلود روی هاست حتماً ویرایش کن و کلید API رو عوض کن
 */

// کلید امنیتی که Agent باید موقع ارسال داده استفاده کنه
// یه رشته‌ی طولانی و تصادفی بذار (مثلاً با: php -r "echo bin2hex(random_bytes(32));")
define('API_KEY', 'CHANGE_THIS_TO_A_LONG_RANDOM_STRING');

// مسیر فایل دیتابیس SQLite (بهتره خارج از public_html باشه اگه امکانش هست)
define('DB_PATH', __DIR__ . '/database.sqlite');

// بعد از چند ثانیه بدون دریافت داده، دستگاه "آفلاین" در نظر گرفته بشه
define('OFFLINE_THRESHOLD_SECONDS', 120);

// آستانه‌ی هشدار دما (سانتی‌گراد) - قابل تغییر بعداً به ازای هر دستگاه
define('DEFAULT_TEMP_WARNING_THRESHOLD', 70);

// تنظیمات ntfy برای هشدارها (اختیاری - می‌تونی بعداً پر کنی)
define('NTFY_ENABLED', false);
define('NTFY_URL', 'https://ntfy.sh/YOUR_TOPIC_HERE');

// منطقه‌ی زمانی
date_default_timezone_set('Asia/Tehran');

// نمایش خطاها - موقع دیباگ true کن، موقع پروداکشن false کن
define('DEBUG_MODE', true);
if (DEBUG_MODE) {
    error_reporting(E_ALL);
    ini_set('display_errors', 1);
} else {
    error_reporting(0);
    ini_set('display_errors', 0);
}
