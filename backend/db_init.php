<?php
/**
 * Homelab Dashboard - Database Initialization
 * این فایل رو فقط یک بار (بعد از آپلود روی هاست) از طریق مرورگر اجرا کن
 * بعد از اجرای موفق، پیشنهاد میشه فایل رو پاک کنی یا نامش رو عوض کنی
 */

require_once __DIR__ . '/config.php';

try {
    $pdo = new PDO('sqlite:' . DB_PATH);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    // جدول دستگاه‌ها - اطلاعات ثابت هر دستگاه
    $pdo->exec("
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_key TEXT UNIQUE NOT NULL,      -- شناسه‌ی یکتا که Agent می‌فرسته (مثلاً 'mikrotik-main')
            display_name TEXT NOT NULL,           -- نام نمایشی (مثلاً 'MikroTik hEX - اتاق سرور')
            device_type TEXT NOT NULL,             -- mikrotik / cisco / hpe_server / vm / other
            ip_address TEXT,
            temp_warning_threshold INTEGER DEFAULT 70,
            is_active INTEGER DEFAULT 1,           -- برای غیرفعال کردن موقت یه دستگاه بدون حذفش
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ");

    // جدول تاریخچه‌ی متریک‌ها - هر بار Agent داده می‌فرسته یه ردیف اضافه میشه
    $pdo->exec("
        CREATE TABLE IF NOT EXISTS metrics_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id INTEGER NOT NULL,
            cpu_percent REAL,
            temperature_c REAL,
            uptime_seconds INTEGER,
            traffic_rx_bytes INTEGER,              -- بایت دریافتی (تجمعی یا نرخ لحظه‌ای - بعداً دقیق‌تر می‌کنیم)
            traffic_tx_bytes INTEGER,
            extra_json TEXT,                        -- برای داده‌های اضافی خاص هر نوع دستگاه (JSON)
            recorded_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (device_id) REFERENCES devices(id)
        )
    ");

    // جدول لاگ هشدارها (قطعی، وصلی، دمای بالا و...)
    $pdo->exec("
        CREATE TABLE IF NOT EXISTS alerts_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id INTEGER NOT NULL,
            alert_type TEXT NOT NULL,              -- offline / online / high_temp / other
            message TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (device_id) REFERENCES devices(id)
        )
    ");

    // ایندکس برای کوئری سریع‌تر تاریخچه بر اساس دستگاه و زمان
    $pdo->exec("CREATE INDEX IF NOT EXISTS idx_metrics_device_time ON metrics_history(device_id, recorded_at)");
    $pdo->exec("CREATE INDEX IF NOT EXISTS idx_alerts_device_time ON alerts_log(device_id, created_at)");

    echo "✅ دیتابیس با موفقیت ساخته شد.\n";
    echo "مسیر: " . DB_PATH . "\n\n";
    echo "⚠️ حالا برو تو config.php کلید API رو عوض کن، بعد این فایل (db_init.php) رو یا پاک کن یا rename کن.\n";

} catch (PDOException $e) {
    http_response_code(500);
    echo "❌ خطا در ساخت دیتابیس: " . $e->getMessage();
}
