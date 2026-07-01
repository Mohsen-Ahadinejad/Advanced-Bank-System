import secrets
import re
from .base_controller import BaseController
from utils.security_utils import hash_pin


class RegisterController(BaseController):
    def _is_valid_national_id(self, nid):
        """اعتبارسنجی دقیق و رسمی کد ملی ایران"""
        if not re.match(r'^\d{10}$', nid): return False
        check = int(nid[9])
        s = sum(int(nid[i]) * (10 - i) for i in range(9)) % 11
        return check == s if s < 2 else check + s == 11

    def _is_valid_phone(self, phone):
        """اعتبارسنجی فرمت شماره موبایل"""
        return bool(re.match(r'^09\d{9}$', phone))

    def handle_register(self, name, nid, phone, pin):
        try:
            if not self._is_valid_national_id(nid):
                raise ValueError("کد ملی وارد شده نامعتبر است.")
            if not self._is_valid_phone(phone):
                raise ValueError("شماره تماس باید با 09 شروع شده و ۱۱ رقم باشد.")
            if len(pin) != 4 or not pin.isdigit():
                raise ValueError("رمز حساب باید دقیقاً ۴ رقم عدد باشد.")

            pin_hash, salt = hash_pin(pin)

            cust = self.repo.get_customer_by_nid(nid)
            user_id = cust[0] if cust else self.repo.add_customer(name, nid, phone)

            # استفاده از secrets برای تولید امن شماره حساب
            acc_num = str(10000000 + secrets.randbelow(90000000))

            self.repo.add_account(acc_num, user_id, pin_hash, salt)

            self.log_action("REGISTER_SUCCESS", f"افتتاح حساب {acc_num} برای کد ملی {nid}")

            # نمایش شماره حساب تولید شده در قالب یک پاپ‌آپ ماندگار
            msg = f"حساب مشتری با موفقیت در سیستم ثبت گردید.\n\nشماره حساب: {acc_num}\n\nلطفاً این شماره را در اختیار مشتری قرار دهید."
            self.view.show_persistent_message("افتتاح حساب موفق", msg)

            self.view.register_tab.clear_form()
            self.refresh_dashboard_data()

        except Exception as e:
            self.handle_error(e)