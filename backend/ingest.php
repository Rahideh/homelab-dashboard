<?php
/**
 * Homelab Dashboard - Ingest API
 * Agent محلی داده‌ها رو با POST به این آدرس می‌فرسته
 *
 * فرمت مورد انتظار (JSON):
 * {
 *   "api_key": "...",
 *   "device_key": "mikrotik-main",
 *   "cpu_percent": 12.5,
 *   "temperature_c": 45.0,
 *   "uptime_seconds": 123456,
 *   "traffic_rx_bytes": 102400,
 *   "traffic_tx_bytes": 51200,
 *   "extra": { "any": "extra data" }
 * }
 */

require_once __DIR__ . '/config.php';

header('Content-Type: application/json; charset=utf-8');

// فقط POST قبول می‌کنیم
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Only POST method allowed']);
    exit;
}

// --- خواندن و پارس بدنه‌ی درخواست ---
$rawBody = file_get_contents('php://input');
$data = json_decode($rawBody, true);

if (json_last_error() !== JSON_ERROR_NONE) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid JSON body']);
    exit;
}

// --- بررسی کلید API ---
// این چک رو قبل از rate limiting می‌ذاریم که یه IP نامعتبر نتونه فایل‌های rate-limit بی‌نهایت بسازه
if (!isset($data['api_key']) || !hash_equals(API_KEY, $data['api_key'])) {
    http_response_code(401);
    echo json_encode(['error' => 'Invalid API key']);
    exit;
}

// --- بررسی فیلدهای الزامی ---
if (empty($data['device_key'])) {
    http_response_code(400);
    echo json_encode(['error' => 'device_key is required']);
    exit;
}

// --- Rate limiting بر اساس IP + device_key (فایل موقت) ---
// عمداً بعد از پارس JSON و چک شدن device_key انجام می‌شه.
// کلید بر اساس ترکیب IP و device_key هست، نه فقط IP:
// چون Agent معمولاً چند دستگاه (MikroTik/Cisco/HPE) رو پشت سر هم از یه IP می‌فرسته
// و نباید ارسال داده‌ی دستگاه B به‌خاطر ارسال اخیر داده‌ی دستگاه A رد بشه
$ip = $_SERVER['REMOTE_ADDR'] ?? 'unknown';
$rateLimitFile = sys_get_temp_dir() . '/homelab_ingest_' . md5($ip . '|' . $data['device_key']) . '.txt';
$minIntervalSeconds = 5; // حداقل فاصله بین دو ریکوئست برای همون دستگاه مشخص

if (file_exists($rateLimitFile)) {
    $lastTime = (int) file_get_contents($rateLimitFile);
    if (time() - $lastTime < $minIntervalSeconds) {
        http_response_code(429);
        echo json_encode(['error' => 'Too many requests for this device, slow down']);
        exit;
    }
}
file_put_contents($rateLimitFile, time());

$deviceKey = trim($data['device_key']);
$cpuPercent = isset($data['cpu_percent']) ? (float) $data['cpu_percent'] : null;
$temperatureC = isset($data['temperature_c']) ? (float) $data['temperature_c'] : null;
$uptimeSeconds = isset($data['uptime_seconds']) ? (int) $data['uptime_seconds'] : null;
$trafficRx = isset($data['traffic_rx_bytes']) ? (int) $data['traffic_rx_bytes'] : null;
$trafficTx = isset($data['traffic_tx_bytes']) ? (int) $data['traffic_tx_bytes'] : null;
$extraJson = isset($data['extra']) ? json_encode($data['extra'], JSON_UNESCAPED_UNICODE) : null;

try {
    $pdo = new PDO('sqlite:' . DB_PATH);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    // --- پیدا کردن یا ساختن دستگاه ---
    $stmt = $pdo->prepare("SELECT id, temp_warning_threshold FROM devices WHERE device_key = :device_key");
    $stmt->execute(['device_key' => $deviceKey]);
    $device = $stmt->fetch(PDO::FETCH_ASSOC);

    if (!$device) {
        // اگه دستگاه قبلاً تعریف نشده، خودکار با نام پیش‌فرض بسازش
        // (بعداً می‌تونی از پنل ادمین نامش رو ویرایش کنی)
        $insert = $pdo->prepare("
            INSERT INTO devices (device_key, display_name, device_type, temp_warning_threshold)
            VALUES (:device_key, :display_name, :device_type, :threshold)
        ");
        $insert->execute([
            'device_key' => $deviceKey,
            'display_name' => $data['display_name'] ?? $deviceKey,
            'device_type' => $data['device_type'] ?? 'other',
            'threshold' => DEFAULT_TEMP_WARNING_THRESHOLD,
        ]);
        $deviceId = $pdo->lastInsertId();
        $tempThreshold = DEFAULT_TEMP_WARNING_THRESHOLD;

        logAlert($pdo, $deviceId, 'new_device', "دستگاه جدید ثبت شد: {$deviceKey}");
    } else {
        $deviceId = $device['id'];
        $tempThreshold = $device['temp_warning_threshold'];
    }

    // --- ثبت متریک جدید ---
    $insertMetric = $pdo->prepare("
        INSERT INTO metrics_history
            (device_id, cpu_percent, temperature_c, uptime_seconds, traffic_rx_bytes, traffic_tx_bytes, extra_json)
        VALUES
            (:device_id, :cpu, :temp, :uptime, :rx, :tx, :extra)
    ");
    $insertMetric->execute([
        'device_id' => $deviceId,
        'cpu' => $cpuPercent,
        'temp' => $temperatureC,
        'uptime' => $uptimeSeconds,
        'rx' => $trafficRx,
        'tx' => $trafficTx,
        'extra' => $extraJson,
    ]);

    // --- چک هشدار دما ---
    if ($temperatureC !== null && $temperatureC >= $tempThreshold) {
        logAlert($pdo, $deviceId, 'high_temp', "دمای بالا: {$temperatureC}°C (آستانه: {$tempThreshold}°C)");
        if (NTFY_ENABLED) {
            sendNtfyAlert("🔥 دمای بالا - {$deviceKey}", "دما به {$temperatureC}°C رسیده (آستانه: {$tempThreshold}°C)");
        }
    }

    echo json_encode(['success' => true, 'device_id' => $deviceId]);

} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['error' => 'Database error', 'detail' => DEBUG_MODE ? $e->getMessage() : null]);
}

/**
 * ثبت یه هشدار در جدول alerts_log
 */
function logAlert(PDO $pdo, int $deviceId, string $type, string $message): void
{
    $stmt = $pdo->prepare("INSERT INTO alerts_log (device_id, alert_type, message) VALUES (:device_id, :type, :message)");
    $stmt->execute(['device_id' => $deviceId, 'type' => $type, 'message' => $message]);
}

/**
 * ارسال نوتیفیکیشن به ntfy (مشابه پروژه Ping)
 */
function sendNtfyAlert(string $title, string $message): void
{
    $encodedTitle = '=?UTF-8?B?' . base64_encode($title) . '?=';
    $opts = [
        'http' => [
            'method' => 'POST',
            'header' => "Title: {$encodedTitle}\r\nContent-Type: text/plain; charset=utf-8\r\n",
            'content' => $message,
            'timeout' => 5,
        ],
    ];
    $context = stream_context_create($opts);
    @file_get_contents(NTFY_URL, false, $context);
}
