import csv
from .base_controller import BaseController
from model.account import Account


class CustomersController(BaseController):
    def handle_customer_search(self, query):
        data = self.repo.search_customers(query)
        self.view.customers_tab.update_tree_data(data)

    def handle_account_status_modify(self, acc_num, new_status):
        try:
            acc_data = self.repo.get_account_data(acc_num)
            if not acc_data:
                raise ValueError("حساب در سیستم یافت نشد.")

            # ساخت شیء دامنه و اعمال قوانین (جلوگیری از فعال‌سازی حساب بسته و غیره)
            acc = Account(**acc_data)
            if new_status == "بسته":
                acc.close_account()
            elif new_status == "مسدود":
                acc.block_account()
            elif new_status == "فعال":
                acc.activate_account()

            self.repo.update_account_status(acc.account_number, acc.status)
            self.log_action("STATUS_CHANGE", f"وضعیت حساب {acc_num} به {acc.status} تغییر یافت")
            self.view.show_message("موفق", f"وضعیت حساب با موفقیت به '{acc.status}' تغییر کرد.")

            self.handle_customer_search(self.view.customers_tab.v_q.get())
            self.refresh_dashboard_data()
        except Exception as e:
            self.handle_error(e)

    def handle_report(self, acc_num):
        records = self.repo.get_account_history(acc_num)
        self.view.show_history_window(acc_num, records)
        self.log_action("REPORT_VIEW", f"مشاهده تاریخچه حساب {acc_num}")

    def handle_export_csv(self, acc_num):
        records = self.repo.get_account_history(acc_num)
        if not records:
            self.view.show_message("خطا", "هیچ تراکنشی برای این حساب ثبت نشده است.", is_error=True)
            return

        filepath = self.view.ask_save_file(
            ext=".csv",
            init=f"BankReport_{acc_num}.csv",
            title="ذخیره گزارش اکسل",
            types=[("CSV files", "*.csv")]
        )

        if not filepath:
            return

        try:
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['نوع تراکنش', 'مبلغ (ریال)', 'موجودی پس از تراکنش', 'زمان', 'توضیحات'])
                for row in records:
                    writer.writerow(row)

            self.log_action("EXPORT_CSV", f"دریافت خروجی اکسل برای حساب {acc_num}")
            self.view.show_message("موفق", "فایل گزارش با موفقیت در سیستم شما ذخیره شد.")
        except Exception as e:
            self.handle_error(e)