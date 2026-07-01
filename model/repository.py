import sqlite3
from datetime import datetime
from contextlib import contextmanager


class BankRepository:
    """لایه ارتباط با پایگاه داده SQLite و تضمین تراکنش‌های اتمیک"""

    def __init__(self, db_name="fund_database.db"):
        self.db_name = db_name
        self._create_tables()
        self._migrate_schema()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
        finally:
            conn.close()

    def _create_tables(self):
        from utils.security_utils import hash_text

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           CREATE TABLE IF NOT EXISTS Users
                           (
                               id
                               INTEGER
                               PRIMARY
                               KEY
                               AUTOINCREMENT,
                               name
                               TEXT
                               NOT
                               NULL,
                               national_id
                               TEXT
                               UNIQUE
                               NOT
                               NULL,
                               phone
                               TEXT,
                               created_at
                               TEXT
                               NOT
                               NULL
                           )
                           ''')
            cursor.execute('''
                           CREATE TABLE IF NOT EXISTS Accounts
                           (
                               account_number
                               TEXT
                               PRIMARY
                               KEY,
                               user_id
                               INTEGER,
                               pin
                               TEXT
                               NOT
                               NULL,
                               salt
                               TEXT
                               NOT
                               NULL,
                               balance
                               INTEGER
                               DEFAULT
                               0,
                               status
                               TEXT
                               DEFAULT
                               "فعال",
                               created_at
                               TEXT
                               NOT
                               NULL,
                               FOREIGN
                               KEY
                           (
                               user_id
                           ) REFERENCES Users
                           (
                               id
                           )
                               )
                           ''')
            cursor.execute('''
                           CREATE TABLE IF NOT EXISTS Transactions
                           (
                               id
                               INTEGER
                               PRIMARY
                               KEY
                               AUTOINCREMENT,
                               account_number
                               TEXT,
                               transaction_type
                               TEXT,
                               amount
                               INTEGER,
                               resulting_balance
                               INTEGER,
                               timestamp
                               TEXT,
                               description
                               TEXT,
                               FOREIGN
                               KEY
                           (
                               account_number
                           ) REFERENCES Accounts
                           (
                               account_number
                           )
                               )
                           ''')
            cursor.execute(
                'CREATE TABLE IF NOT EXISTS Admins (username TEXT PRIMARY KEY, password_hash TEXT, salt TEXT)')

            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_nid ON Users(national_id);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_accounts_num ON Accounts(account_number);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_acc ON Transactions(account_number);')

            cursor.execute("SELECT COUNT(*) FROM Admins")
            if cursor.fetchone()[0] == 0:
                default_hash, default_salt = hash_text("12345")
                cursor.execute("INSERT INTO Admins (username, password_hash, salt) VALUES (?, ?, ?)",
                               ("admin", default_hash, default_salt))

            conn.commit()

    def _migrate_schema(self):
        """اسکریپت نجات: بروزرسانی ساختار جداول قدیمی به معماری جدید بدون حذف اطلاعات"""
        from utils.security_utils import hash_text
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(Admins)")
            columns = [col[1] for col in cursor.fetchall()]

            if 'salt' not in columns:
                cursor.execute("ALTER TABLE Admins ADD COLUMN salt TEXT")
                new_hash, new_salt = hash_text("12345")
                cursor.execute("UPDATE Admins SET password_hash = ?, salt = ? WHERE username = 'admin'",
                               (new_hash, new_salt))
                conn.commit()

    def add_customer(self, name, national_id, phone, created_at=None):
        if not created_at:
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO Users (name, national_id, phone, created_at) VALUES (?, ?, ?, ?)',
                           (name, national_id, phone, created_at))
            conn.commit()
            return cursor.lastrowid

    def get_customer_by_nid(self, national_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM Users WHERE national_id = ?', (national_id,))
            return cursor.fetchone()

    def add_account(self, account_number, user_id, pin_hash, salt, balance=0, status="فعال", created_at=None):
        if not created_at:
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           INSERT INTO Accounts (account_number, user_id, pin, salt, balance, status, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?)
                           ''', (account_number, user_id, pin_hash, salt, balance, status, created_at))
            conn.commit()

    def get_account_data(self, account_number):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM Accounts WHERE account_number = ?', (account_number,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "account_number": row[0],
                "user_id": row[1],
                "pin_hash": row[2],
                "salt": row[3],
                "balance": row[4],
                "status": row[5],
                "created_at": row[6]
            }

    def update_account_status(self, account_number, new_status):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE Accounts SET status = ? WHERE account_number = ?', (new_status, account_number))
            conn.commit()

    def execute_atomic_operation(self, account, transaction_obj):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE Accounts SET balance = ? WHERE account_number = ?',
                           (account.balance, account.account_number))
            cursor.execute('''
                           INSERT INTO Transactions (account_number, transaction_type, amount, resulting_balance,
                                                     timestamp, description)
                           VALUES (?, ?, ?, ?, ?, ?)
                           ''', (account.account_number, transaction_obj.get_type_name(), transaction_obj.amount,
                                 account.balance, now_str, transaction_obj.get_description()))
            conn.commit()

    def execute_atomic_transfer(self, source_acc, destination_acc, transfer_out_obj, transfer_in_obj):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('UPDATE Accounts SET balance = ? WHERE account_number = ?',
                               (source_acc.balance, source_acc.account_number))
                cursor.execute('''
                               INSERT INTO Transactions (account_number, transaction_type, amount, resulting_balance,
                                                         timestamp, description)
                               VALUES (?, ?, ?, ?, ?, ?)
                               ''',
                               (source_acc.account_number, transfer_out_obj.get_type_name(), transfer_out_obj.amount,
                                source_acc.balance, now_str, transfer_out_obj.get_description()))

                cursor.execute('UPDATE Accounts SET balance = ? WHERE account_number = ?',
                               (destination_acc.balance, destination_acc.account_number))
                cursor.execute('''
                               INSERT INTO Transactions (account_number, transaction_type, amount, resulting_balance,
                                                         timestamp, description)
                               VALUES (?, ?, ?, ?, ?, ?)
                               ''',
                               (destination_acc.account_number, transfer_in_obj.get_type_name(), transfer_in_obj.amount,
                                destination_acc.balance, now_str, transfer_in_obj.get_description()))
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e

    def get_dashboard_stats(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM Accounts WHERE status != 'بسته'")
            mem_count = cursor.fetchone()[0] or 0

            cursor.execute("SELECT SUM(balance) FROM Accounts WHERE status != 'بسته'")
            total_assets = cursor.fetchone()[0] or 0

            today_prefix = datetime.now().strftime("%Y-%m-%d")
            cursor.execute("SELECT COUNT(*) FROM Transactions WHERE timestamp LIKE ?", (f"{today_prefix}%",))
            tx_count = cursor.fetchone()[0] or 0

            return {"total_members": mem_count, "total_assets": total_assets, "today_transactions": tx_count}

    def search_customers(self, query=""):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            sql = '''
                  SELECT a.status, a.created_at, a.balance, a.account_number, u.national_id, u.name
                  FROM Accounts a
                           JOIN Users u ON a.user_id = u.id \
                  '''
            params = ()
            if query:
                sql += " WHERE u.name LIKE ? OR u.national_id LIKE ? OR a.account_number LIKE ?"
                q = f"%{query}%"
                params = (q, q, q)

            sql += " ORDER BY a.created_at DESC"
            cursor.execute(sql, params)
            return cursor.fetchall()

    def get_account_history(self, account_number):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           SELECT transaction_type, amount, resulting_balance, timestamp, description
                           FROM Transactions
                           WHERE account_number = ?
                           ORDER BY timestamp DESC
                           ''', (account_number,))
            return cursor.fetchall()

    def get_admin_data(self, username):
        """بازگرداندن هش و نمکِ ذخیره‌شده برای پروسه لاگین امن"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT password_hash, salt FROM Admins WHERE username = ?', (username,))
            return cursor.fetchone()