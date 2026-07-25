<?php
/**
 * این فایل رو موقتاً توی پوشه‌ی frontend آپلود کن، یه‌بار بازش کن تا مسیر دقیق
 * سرور رو بهت بده، بعد پاکش کن.
 */
header('Content-Type: text/plain; charset=utf-8');
echo "مسیر کامل این پوشه روی سرور:\n\n";
echo __DIR__ . "\n\n";
echo "پس مقدار AuthUserFile توی .htaccess باید این باشه:\n\n";
echo __DIR__ . "/.htpasswd\n";
