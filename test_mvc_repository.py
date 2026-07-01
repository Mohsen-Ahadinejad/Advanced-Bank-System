import os
import pytest
from model.repository import BankRepository
from model.account import Account
from model.exceptions import BankError, AccountBlockedError, AccountClosedError
from utils.security_utils import hash_text


# ================= 1. Fixture Setup =================
@pytest.fixture
def repo():
    """یک دیتابیس تستی ایزوله می‌سازد و بعد از پایان تست آن را پاک می‌کند"""
    test_db = "test_mvc_bank_system.db"
    repository = BankRepository(db_name=test_db)

    yield repository

    if os.path.exists(test_db):
        os.remove(test_db)


# ================= 2. Database Initialization Tests =================
def test_database_initialization_and_admin_creation(repo):
    """بررسی ساخته شدن جداول و ادمین پیش‌فرض در دیتابیس جدید با امنیت Salt"""
    admin_data = repo.get_admin_data("admin")
    assert admin_data is not None, "ادمین پیش‌فرض باید ساخته شود"
    assert len(admin_data) == 2, "خروجی اطلاعات ادمین باید شامل هش و نمک باشد"


# ================= 3. Core CRUD Operations Tests =================
def test_add_customer_and_account(repo):
    """بررسی ثبت صحیح مشتری و متصل شدن حساب به آن"""
    user_id = repo.add_customer("تست کاربر", "0123456789", "09120000000")
    assert user_id > 0

    customer = repo.get_customer_by_nid("0123456789")
    assert customer is not None
    assert customer[1] == "تست کاربر"

    # اصلاح باگ تست: دریافت همزمان هش و نمک از تابع امنیتی
    pin_hash, salt = hash_text("1234")
    repo.add_account("6037990000000000", user_id, pin_hash, salt, 500000, "فعال")

    acc_data = repo.get_account_data("6037990000000000")
    assert acc_data is not None
    assert acc_data["balance"] == 500000
    assert acc_data["status"] == "فعال"


# ================= 4. Regression Test (The 6-Column Bug) =================
def test_search_customers_returns_exactly_6_columns(repo):
    """تضمین خروجی ۶ ستونه برای جدول رابط کاربری"""
    user_id = repo.add_customer("مشتری گزارش", "9998887776", "09129998877")
    repo.add_account("1111222233334444", user_id, "hash", "salt", 1000, "فعال")

    results = repo.search_customers("مشتری گزارش")

    assert len(results) == 1
    assert len(results[0]) == 6

    status, created_at, balance, acc_num, nid, name = results[0]

    assert status == "فعال"
    assert name == "مشتری گزارش"
    assert nid == "9998887776"
    assert acc_num == "1111222233334444"


# ================= 5. Dashboard Stats Tests =================
def test_dashboard_stats_calculation(repo):
    """بررسی محاسبه درست آمارهای داشبورد"""
    u1 = repo.add_customer("کاربر یک", "111", "091")
    repo.add_account("1001", u1, "h", "s", 150000, "فعال")

    u2 = repo.add_customer("کاربر دو", "222", "092")
    repo.add_account("1002", u2, "h", "s", 350000, "فعال")

    u3 = repo.add_customer("کاربر سه", "333", "093")
    repo.add_account("1003", u3, "h", "s", 999999, "بسته")

    stats = repo.get_dashboard_stats()

    assert stats["total_members"] == 2
    assert stats["total_assets"] == 500000


# ================= 6. Account Domain Logic Tests (احیای تست‌های منطقی) =================
def test_account_state_machine_logic():
    """تست قوانین حیاتی کسب‌وکار روی وضعیت حساب‌ها"""
    acc = Account("1234", 1, "hash", "salt", balance=50000, status="فعال")

    # 1. تست مسدود و فعال کردن
    acc.block_account()
    assert acc.status == "مسدود"
    acc.activate_account()
    assert acc.status == "فعال"

    # 2. جلوگیری از بستن حساب دارای موجودی
    with pytest.raises(BankError, match="دارای 50,000 ریال موجودی است"):
        acc.close_account()

    # 3. صفر کردن موجودی و بستن موفق حساب
    acc.balance = 0
    acc.close_account()
    assert acc.status == "بسته"

    # 4. جلوگیری از فعال‌سازی مجدد حساب ابطال‌شده
    with pytest.raises(BankError, match="بسته‌شده را نمی‌توان مجدداً فعال کرد"):
        acc.activate_account()