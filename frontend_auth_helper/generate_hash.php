<?php
/**
 * ابزار موقت برای ساخت هش پسورد جهت .htpasswd
 *
 * نحوه‌ی استفاده:
 *   ۱. این فایل رو موقتاً کنار frontend/ (یا هرجای دیگه‌ی هاست) آپلود کن
 *   ۲. توی مرورگر برو به: https://yourdomain.com/.../generate_hash.php?pw=پسورد-دلخواهت
 *   ۳. خروجی رو کپی کن، بذار توی فایل .htpasswd (توضیحش تو راهنما هست)
 *   ۴. ⚠️ خیلی مهم: بعد از استفاده، همین فایل رو از روی هاست پاک کن!
 *      چون هرکسی که آدرسش رو حدس بزنه می‌تونه هش پسورد بسازه.
 */

if (!isset($_GET['pw']) || $_GET['pw'] === '') {
    die('استفاده: این آدرس رو با ?pw=پسورد-دلخواهت باز کن');
}

$password = $_GET['pw'];
$saltChars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
$salt = '$1$' . substr(str_shuffle($saltChars), 0, 8) . '$';
$hash = crypt($password, $salt);

header('Content-Type: text/plain; charset=utf-8');
echo "این خط رو کامل کپی کن و بذار توی فایل .htpasswd:\n\n";
echo "rahi:{$hash}\n\n";
echo "⚠️ یادت نره بعد از این‌که هش رو کپی کردی، همین فایل (generate_hash.php) رو از روی هاست پاک کنی.\n";
