<?php
/**
 * Homelab Dashboard - API خواندن وضعیت دستگاه‌ها
 * فرانت‌اند از این آدرس داده‌ها رو می‌خونه (بدون نیاز به API key چون فقط خواندنیه)
 * اگه می‌خوای داشبورد خصوصی بمونه، بعداً یه لایه‌ی لاگین اضافه می‌کنیم
 */

require_once __DIR__ . '/config.php';

header('Content-Type: application/json; charset=utf-8');

try {
    $pdo = new PDO('sqlite:' . DB_PATH);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);

    // آخرین متریک هر دستگاه رو می‌گیریم
    $devices = $pdo->query("SELECT * FROM devices WHERE is_active = 1 ORDER BY display_name")->fetchAll();

    $result = [];
    foreach ($devices as $device) {
        $stmt = $pdo->prepare("
            SELECT * FROM metrics_history
            WHERE device_id = :id
            ORDER BY recorded_at DESC
            LIMIT 1
        ");
        $stmt->execute(['id' => $device['id']]);
        $lastMetric = $stmt->fetch();

        $isOnline = false;
        $secondsSinceLastSeen = null;

        if ($lastMetric) {
            // نکته‌ی مهم: SQLite همیشه CURRENT_TIMESTAMP رو به وقت UTC ذخیره می‌کنه،
            // صرف‌نظر از date_default_timezone_set() که بالای config.php تنظیم شده.
            // پس اینجا باید صریحاً به strtotime بگیم که این رشته UTC هست، وگرنه
            // با توجه به تایم‌زون ایران (UTC+3:30) نتیجه‌ی غلط می‌ده.
            $lastSeenTs = strtotime($lastMetric['recorded_at'] . ' UTC');
            $secondsSinceLastSeen = time() - $lastSeenTs;
            $isOnline = $secondsSinceLastSeen <= OFFLINE_THRESHOLD_SECONDS;
        }

        $result[] = [
            'id' => (int) $device['id'],
            'device_key' => $device['device_key'],
            'display_name' => $device['display_name'],
            'device_type' => $device['device_type'],
            'ip_address' => $device['ip_address'],
            'is_online' => $isOnline,
            'seconds_since_last_seen' => $secondsSinceLastSeen,
            'temp_warning_threshold' => (float) $device['temp_warning_threshold'],
            'last_metric' => $lastMetric ? [
                'cpu_percent' => $lastMetric['cpu_percent'] !== null ? (float) $lastMetric['cpu_percent'] : null,
                'temperature_c' => $lastMetric['temperature_c'] !== null ? (float) $lastMetric['temperature_c'] : null,
                'uptime_seconds' => $lastMetric['uptime_seconds'] !== null ? (int) $lastMetric['uptime_seconds'] : null,
                'traffic_rx_bytes' => $lastMetric['traffic_rx_bytes'] !== null ? (int) $lastMetric['traffic_rx_bytes'] : null,
                'traffic_tx_bytes' => $lastMetric['traffic_tx_bytes'] !== null ? (int) $lastMetric['traffic_tx_bytes'] : null,
                'recorded_at' => $lastMetric['recorded_at'],
            ] : null,
        ];
    }

    echo json_encode(['devices' => $result], JSON_UNESCAPED_UNICODE);

} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['error' => 'Database error', 'detail' => DEBUG_MODE ? $e->getMessage() : null]);
}
