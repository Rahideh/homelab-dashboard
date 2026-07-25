<?php
/**
 * Homelab Dashboard - API تاریخچه‌ی متریک‌های یک دستگاه
 * برای رسم گراف CPU/دما/ترافیک استفاده می‌شه
 *
 * پارامترها:
 *   device_id (الزامی) - شناسه‌ی دستگاه
 *   limit (اختیاری، پیش‌فرض ۵۰) - حداکثر تعداد رکورد
 */

require_once __DIR__ . '/config.php';

header('Content-Type: application/json; charset=utf-8');

$deviceId = isset($_GET['device_id']) ? (int) $_GET['device_id'] : 0;
$limit = isset($_GET['limit']) ? min(500, max(1, (int) $_GET['limit'])) : 50;

if ($deviceId <= 0) {
    http_response_code(400);
    echo json_encode(['error' => 'device_id is required']);
    exit;
}

try {
    $pdo = new PDO('sqlite:' . DB_PATH);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);

    // آخرین N رکورد رو می‌گیریم (نزولی)، بعد برای نمایش درست روی گراف
    // (چپ = قدیمی، راست = جدید) دوباره به ترتیب صعودی برمی‌گردونیمش
    $stmt = $pdo->prepare("
        SELECT cpu_percent, temperature_c, uptime_seconds,
               traffic_rx_bytes, traffic_tx_bytes, recorded_at
        FROM metrics_history
        WHERE device_id = :device_id
        ORDER BY recorded_at DESC
        LIMIT :limit
    ");
    $stmt->bindValue(':device_id', $deviceId, PDO::PARAM_INT);
    $stmt->bindValue(':limit', $limit, PDO::PARAM_INT);
    $stmt->execute();
    $rows = array_reverse($stmt->fetchAll());

    $history = array_map(function ($row) {
        return [
            'cpu_percent' => $row['cpu_percent'] !== null ? (float) $row['cpu_percent'] : null,
            'temperature_c' => $row['temperature_c'] !== null ? (float) $row['temperature_c'] : null,
            'traffic_rx_bytes' => $row['traffic_rx_bytes'] !== null ? (int) $row['traffic_rx_bytes'] : null,
            'traffic_tx_bytes' => $row['traffic_tx_bytes'] !== null ? (int) $row['traffic_tx_bytes'] : null,
            'recorded_at' => $row['recorded_at'],
        ];
    }, $rows);

    echo json_encode(['device_id' => $deviceId, 'history' => $history], JSON_UNESCAPED_UNICODE);

} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['error' => 'Database error', 'detail' => DEBUG_MODE ? $e->getMessage() : null]);
}
