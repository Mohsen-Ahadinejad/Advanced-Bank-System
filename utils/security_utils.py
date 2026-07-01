import hashlib
import secrets
import string

def generate_salt(length=32):
    """تولید نمک (Salt) تصادفی امن برای هر کاربر"""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def hash_text(text, salt=None):
    """هش کردن متن با الگوریتم SHA-256 به همراه Salt اختصاصی"""
    if not salt:
        salt = generate_salt()
    salted_text = text + salt
    hashed = hashlib.sha256(salted_text.encode('utf-8')).hexdigest()
    return hashed, salt

def hash_pin(pin, salt=None):
    """تابع کمکی برای حفظ سازگاری نام توابع در کنترلرها"""
    return hash_text(pin, salt)

def verify_password(plain_text, hashed, salt):
    """بررسی صحت رمز عبور با استفاده از Salt ذخیره شده"""
    calculated_hash, _ = hash_text(plain_text, salt)
    return calculated_hash == hashed

def verify_pin(plain_text, hashed, salt):
    """تابع کمکی برای اعتبارسنجی پین‌کد در تراکنش‌ها"""
    return verify_password(plain_text, hashed, salt)