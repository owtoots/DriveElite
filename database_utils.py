import sqlite3
import os
import urllib.parse
import urllib.request
import smtplib
import streamlit as st
from email.message import EmailMessage

DB_PATH = "/data/driveelite_v2.db"

def get_connection():
    """Creates a connection to the SQLite database."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False, timeout=15.0)

# --- 1. SMS UTILITY ---
def send_sms_alert(number, message):
    """Sends an SMS via Semaphore API."""
    try:
        apikey = st.secrets.get("semaphore_api_key", os.environ.get("semaphore_api_key"))
        if not apikey: return False
        
        url = "https://api.semaphore.co/api/v4/messages"
        payload = {'apikey': apikey, 'number': number, 'message': message, 'sendername': 'SEMAPHORE'}
        data = urllib.parse.urlencode(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req)
        return True
    except Exception as e:
        print(f"SMS Failed: {e}")
        return False

# --- 2. ADMIN EMAIL UTILITY ---
def send_alert_email(to_email, subject, body):
    """Sends general notifications and Admin alerts with UTF-8 armor."""
    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = 'contact@driveelite.ph'
        msg['To'] = to_email
        msg.set_content(body, charset='utf-8')
        
        # Connect to Brevo and send
        app_password = os.environ.get("EMAIL_PASSWORD")
        with smtplib.SMTP('smtp-relay.brevo.com', 587) as smtp:
            smtp.starttls()
            # 👇 REPLACE THE EMAIL BELOW WITH YOUR GMAIL ACCOUNT 👇
            smtp.login('YOUR_BREVO_LOGIN_EMAIL@gmail.com', app_password)
            smtp.send_message(msg)
        return True
    except Exception as e:
        print(f"Alert Email Error: {e}")
        return False

# --- 3. CENTRALIZED OTP DISPATCHER ---
def send_otp(contact_number, email_address, otp_code, method="EMAIL"):
    """Sends a clean, utf-8 armored OTP email or SMS."""
    if method == "SMS":
        message = f"Your DriveElite OTP is: {otp_code}. Do not share this with anyone."
        return send_sms_alert(contact_number, message)
        
    try:
        msg = EmailMessage()
        msg['Subject'] = "DriveElite: Your Verification Code"
        msg['From'] = 'contact@driveelite.ph'
        msg['To'] = email_address

        body = f"""Hello,

Your DriveElite registration verification code is: 
{otp_code}

Please enter this 6-digit code on the registration screen to verify your account.

Drive safely,
The DriveElite Team"""
        
        # UTF-8 ARMOR PREVENTS LATIN-1 CRASHES
        msg.set_content(body, charset='utf-8')

        # Connect to Brevo and send
        app_password = os.environ.get("EMAIL_PASSWORD") 
        with smtplib.SMTP('smtp-relay.brevo.com', 587) as smtp:
            smtp.starttls()
            # 👇 REPLACE THE EMAIL BELOW WITH YOUR GMAIL ACCOUNT 👇
            smtp.login('YOUR_BREVO_LOGIN_EMAIL@gmail.com', app_password)
            smtp.send_message(msg)
            
        return True
        
    except Exception as e:
        # THIS FORCES THE TRUE ERROR TO SHOW ON YOUR WEBSITE
        st.error(f"🔍 DETAILED SYSTEM ERROR: {e}")
        return False

# --- 4. DATABASE STRUCTURE ---
def init_db():
    """Initializes all required tables for DriveElite V2."""
    conn = get_connection()
    tables = [
        """CREATE TABLE IF NOT EXISTS support_chats (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, receiver TEXT, message TEXT, ts DATETIME DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS platform_users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT, full_name TEXT, email TEXT, age TEXT, nationality TEXT, address TEXT, contact_number TEXT, admin_status TEXT DEFAULT 'PENDING', govt_id_img BLOB, license_img BLOB, signature_img BLOB, area_code TEXT DEFAULT '+63')""",
        """CREATE TABLE IF NOT EXISTS vehicles (id INTEGER PRIMARY KEY AUTOINCREMENT, owner_username TEXT, make TEXT, model TEXT, year TEXT, plate TEXT, bank_name TEXT, account_no TEXT, vehicle_img TEXT, or_cr_img TEXT, or_img TEXT, cr_img TEXT, insurance_img TEXT, category TEXT, approved_price REAL, daily_rate REAL, admin_status TEXT DEFAULT 'PENDING', booking_status TEXT DEFAULT 'AVAILABLE', ref_no TEXT)""",
        """CREATE TABLE IF NOT EXISTS bookings (id INTEGER PRIMARY KEY AUTOINCREMENT, vehicle_id INTEGER, renter_username TEXT, status TEXT, pickup_loc TEXT, return_loc TEXT, destination TEXT, pickup_time TEXT, return_time TEXT, amount REAL, payment_method TEXT, front_img TEXT, back_img TEXT, left_img TEXT, right_img TEXT, odometer_img TEXT, dseat_img TEXT, pseat_img TEXT, tire_img TEXT, trunk_img TEXT, actual_dl_img TEXT, damage_img TEXT, payout_status TEXT DEFAULT 'PENDING', with_driver INTEGER DEFAULT 0, assigned_driver TEXT, rating INTEGER, review TEXT, gateway_fee REAL DEFAULT 0.0, delivery_fee REAL DEFAULT 0, return_fee REAL DEFAULT 0, deposit_collected INTEGER DEFAULT 0, penalties REAL DEFAULT 0.0, damage_fee REAL DEFAULT 0.0, late_fee REAL DEFAULT 0.0, fuel_fee REAL DEFAULT 0.0, cleaning_fee REAL DEFAULT 0.0, rfid_fee REAL DEFAULT 0.0, dispute_status TEXT DEFAULT 'CLEAN', booking_ref TEXT, receipt_img BLOB, handover_photos TEXT)""",
        """CREATE TABLE IF NOT EXISTS drivers (id INTEGER PRIMARY KEY AUTOINCREMENT, owner_username TEXT, first_name TEXT, middle_name TEXT, last_name TEXT, age INTEGER, address TEXT, contact_number TEXT, is_owner INTEGER DEFAULT 0, govt_id_img TEXT, license_img TEXT, admin_status TEXT DEFAULT 'PENDING')""",
        """CREATE TABLE IF NOT EXISTS vehicle_categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, default_price REAL)""",
        """CREATE TABLE IF NOT EXISTS admin_promos (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, message TEXT, target TEXT DEFAULT "ALL USERS", active INTEGER DEFAULT 1)"""
    ]
    for table in tables: 
        conn.execute(table)
    conn.commit()
    conn.close()

def patch_database():
    """Applies structural updates to existing tables."""
    conn = get_connection()
    patches = [
        "ALTER TABLE platform_users ADD COLUMN area_code TEXT DEFAULT '+63'",
        "ALTER TABLE bookings ADD COLUMN gateway_fee REAL DEFAULT 0.0",
        "ALTER TABLE bookings ADD COLUMN receipt_img BLOB",
        "ALTER TABLE bookings ADD COLUMN handover_photos TEXT",
        "ALTER TABLE bookings ADD COLUMN damage_img TEXT",
        "ALTER TABLE vehicles ADD COLUMN or_img TEXT",
        "ALTER TABLE vehicles ADD COLUMN cr_img TEXT",
        "ALTER TABLE bookings ADD COLUMN damage_fee REAL DEFAULT 0.0",
        "ALTER TABLE bookings ADD COLUMN late_fee REAL DEFAULT 0.0",
        "ALTER TABLE bookings ADD COLUMN fuel_fee REAL DEFAULT 0.0",
        "ALTER TABLE bookings ADD COLUMN cleaning_fee REAL DEFAULT 0.0",
        "ALTER TABLE bookings ADD COLUMN rfid_fee REAL DEFAULT 0.0",
        "ALTER TABLE bookings ADD COLUMN dispute_status TEXT DEFAULT 'CLEAN'"
    ]
    for patch in patches:
        try: 
            conn.execute(patch)
        except: 
            pass
    conn.commit()
    conn.close()

# --- 5. EXECUTION GUARD ---
if __name__ == "__main__":
    init_db()
    patch_database()
