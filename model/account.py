from model.exceptions import BankError, AccountBlockedError, AccountClosedError


class Account:
    def __init__(self, account_number, user_id, pin_hash, salt, balance=0, status="فعال", created_at=None):
        self.account_number = account_number
        self.user_id = user_id
        self.pin_hash = pin_hash
        self.salt = salt
        self.balance = balance
        self.status = status
        self.created_at = created_at

    def block_account(self):
        if self.status == "بسته":
            raise BankError("حساب بسته شده است و قابل مسدودسازی نیست.")
        self.status = "مسدود"

    def activate_account(self):
        if self.status == "بسته":
            raise BankError("حساب بسته‌شده را نمی‌توان مجدداً فعال کرد.")
        self.status = "فعال"

    def close_account(self):
        if self.status == "بسته":
            raise BankError("حساب از قبل بسته شده است.")
        if self.balance > 0:
            raise BankError(f"امکان بستن حساب وجود ندارد. حساب دارای {self.balance:,} ریال موجودی است.")
        self.status = "بسته"

    def apply_transaction(self, transaction):
        if self.status == "بسته":
            raise AccountClosedError("حساب به طور کامل بسته شده است و امکان تراکنش ندارد.")
        if self.status == "مسدود":
            raise AccountBlockedError("حساب مسدود است و امکان تراکنش ندارد.")

        # اجرای منطق تراکنش در صورت مجاز بودن وضعیت حساب
        transaction.execute(self)