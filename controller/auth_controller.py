import sys
from .base_controller import BaseController
from utils.security_utils import verify_password

class AuthController(BaseController):
    def handle_admin_login(self, username, password):
        admin_data = self.repo.get_admin_data(username)
        if admin_data:
            stored_hash, salt = admin_data
            if verify_password(password, stored_hash, salt):
                self.log_action("LOGIN_SUCCESS", f"ورود موفق ادمین: {username}")
                self.view.switch_to_main()
                self.refresh_dashboard_data()
                return

        self.log_action("LOGIN_FAILED", f"تلاش ناموفق برای ورود با نام کاربری: {username}", "WARNING")
        self.view.show_message("خطای ورود", "نام کاربری یا رمز عبور اشتباه است.", is_error=True)

    def handle_logout(self):
        self.log_action("LOGOUT", "خروج ادمین از سیستم.")
        self.view.switch_to_login()

    def handle_exit(self):
        self.log_action("SYSTEM", "بسته شدن کامل نرم‌افزار.")
        self.view.destroy()
        sys.exit(0)