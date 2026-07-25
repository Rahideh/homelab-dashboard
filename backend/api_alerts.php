<?php
/**
 * Homelab Dashboard - API لاگ هشدارهای اخیر (همه‌ی دستگاه‌ها)
 *
 * پارامترها:
 *   limit (اختیاری، پیش‌فرض ۳۰) - حداکثر تعداد رکورد
 */

require_once __DIR__ . '/config.php';

header('Content-Type: application/json; charset=utf-8');

$limit = isset($_GET['limit']) ? min(200, max(1, (int) $_GET['limit'])) : 30;

try {
    $pdo = new PDO('sqlite:' . DB_PATH);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);

    $stmt = $pdo->prepare("
        SELECT a.alert_type, a.message, a.created_at, d.display_name, d.device_key
        FROM alerts_log a
        JOIN devices d ON d.id = a.device_id
        ORDER BY a.created_at DESC
        LIMIT :limit
    ");
    $stmt->bindValue(':limit', $limit, PDO::PARAM_INT);
    $stmt->execute();
    $alerts = $stmt->fetchAll();

    echo json_encode(['alerts' => $alerts], JSON_UNESCAPED_UNICODE);

} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['error' => 'Database error', 'detail' => DEBUG_MODE ? $e->getMessage() : null]);
}
