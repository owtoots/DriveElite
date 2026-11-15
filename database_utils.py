import sqlite3
import os
import urllib.parse
import urllib.request
import smtplib
import json 
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
    """Sends general notifications using Brevo's REST API to bypass port blocks."""
    try:
        clean_email = to_email.strip() if to_email else ""
        
        api_key = os.environ.get("BREVO_RENDER", "").strip()

        url = "https://api.brevo.com/v3/smtp/email"
        payload = {
            "sender": {"name": "DriveElite Admin", "email": "contact@driveelite.ph"},
            "to": [{"email": clean_email}],
            "subject": subject,
            "textContent": body
        }
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={
            'api-key': api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        urllib.request.urlopen(req)
        return True
    except Exception as e:
        print(f"Alert Email Error: {e}")
        return False

# --- 2.1 AFFILIATE APPROVAL EMAIL UTILITY ---
def send_approval_email(to_email, subject, body):
    """Sends affiliate approval notifications using Brevo's REST API over HTTPS."""
    try:
        clean_email = to_email.strip() if to_email else ""
        api_key = os.environ.get("BREVO_RENDER", "").strip()

        url = "https://api.brevo.com/v3/smtp/email"
        payload = {
            "sender": {"name": "DriveElite Admin", "email": "contact@driveelite.ph"},
            "to": [{"email": clean_email}],
            "subject": subject,
            "textContent": body
        }
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={
            'api-key': api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        urllib.request.urlopen(req)
        return True
    except Exception as e:
        print(f"Approval Email Error: {e}")
        return False

# --- 3. CENTRALIZED OTP DISPATCHER ---
def send_otp(contact_number, email_address, otp_code, method="EMAIL"):
    """Sends a clean OTP using Brevo's REST API over HTTPS."""
    if method == "SMS":
        message = f"Your DriveElite OTP is: {otp_code}. Do not share this with anyone."
        return send_sms_alert(contact_number, message)
        
    try:
        clean_email = email_address.strip() if email_address else ""
        
        api_key = os.environ.get("BREVO_RENDER", "").strip() 
        
        body = f"Hello,\n\nYour DriveElite registration verification code is:\n{otp_code}\n\nPlease enter this 6-digit code on the registration screen to verify your account.\n\nDrive safely,\nThe DriveElite Team"
        
        url = "https://api.brevo.com/v3/smtp/email"
        payload = {
            "sender": {"name": "DriveElite", "email": "contact@driveelite.ph"},
            "to": [{"email": clean_email}],
            "subject": "DriveElite: Your Verification Code",
            "textContent": body
        }
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={
            'api-key': api_key, 
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        urllib.request.urlopen(req)
        return True
        
    except Exception as e:
        st.error(f"🔍 API SYSTEM ERROR: {e}")
        return False

# --- 4. DATABASE STRUCTURE ---
def init_db():
    """Initializes all required tables for DriveElite V2."""
    conn = get_connection()
    tables = [
        """CREATE TABLE IF NOT EXISTS support_chats (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, receiver TEXT, message TEXT, ts DATETIME DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS platform_users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT, full_name TEXT, email TEXT, age TEXT, nationality TEXT, address TEXT, contact_number TEXT, admin_status TEXT DEFAULT 'PENDING', govt_id_img BLOB, license_img BLOB, signature_img BLOB, area_code TEXT DEFAULT '+63', bank_name TEXT, account_no TEXT, bank_acc_name TEXT)""",
        """CREATE TABLE IF NOT EXISTS vehicles (id INTEGER PRIMARY KEY AUTOINCREMENT, owner_username TEXT, make TEXT, model TEXT, year TEXT, plate TEXT, bank_name TEXT, account_no TEXT, vehicle_img TEXT, or_cr_img TEXT, or_img TEXT, cr_img TEXT, insurance_img TEXT, category TEXT, approved_price REAL, daily_rate REAL, admin_status TEXT DEFAULT 'PENDING', booking_status TEXT DEFAULT 'AVAILABLE', ref_no TEXT, location TEXT DEFAULT 'Metro Manila', is_with_driver INTEGER DEFAULT 0, tire_pressure TEXT DEFAULT 'Standard specs', preferred_fuel TEXT DEFAULT 'Standard Unleaded')""",
        """CREATE TABLE IF NOT EXISTS bookings (id INTEGER PRIMARY KEY AUTOINCREMENT, vehicle_id INTEGER, renter_username TEXT, status TEXT, pickup_loc TEXT, return_loc TEXT, destination TEXT, pickup_time TEXT, return_time TEXT, amount REAL, payment_method TEXT, front_img TEXT, back_img TEXT, left_img TEXT, right_img TEXT, odometer_img TEXT, dseat_img TEXT, pseat_img TEXT, tire_img TEXT, trunk_img TEXT, actual_dl_img TEXT, damage_img TEXT, payout_status TEXT DEFAULT 'PENDING', with_driver INTEGER DEFAULT 0, assigned_driver TEXT, rating INTEGER, review TEXT, gateway_fee REAL DEFAULT 0.0, delivery_fee REAL DEFAULT 0, return_fee REAL DEFAULT 0, deposit_collected INTEGER DEFAULT 0, penalties REAL DEFAULT 0.0, damage_fee REAL DEFAULT 0.0, late_fee REAL DEFAULT 0.0, fuel_fee REAL DEFAULT 0.0, cleaning_fee REAL DEFAULT 0.0, rfid_fee REAL DEFAULT 0.0, dispute_status TEXT DEFAULT 'CLEAN', booking_ref TEXT, receipt_img BLOB, handover_photos TEXT)""",
        """CREATE TABLE IF NOT EXISTS drivers (id INTEGER PRIMARY KEY AUTOINCREMENT, owner_username TEXT, first_name TEXT, middle_name TEXT, last_name TEXT, age INTEGER, address TEXT, contact_number TEXT, is_owner INTEGER DEFAULT 0, govt_id_img TEXT, license_img TEXT, admin_status TEXT DEFAULT 'PENDING')""",
        """CREATE TABLE IF NOT EXISTS vehicle_categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, default_price REAL)""",
        """CREATE TABLE IF NOT EXISTS admin_promos (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, message TEXT, target TEXT DEFAULT 'ALL USERS', active INTEGER DEFAULT 1)""",
        """CREATE TABLE IF NOT EXISTS delivery_tiers (id INTEGER PRIMARY KEY AUTOINCREMENT, max_km REAL UNIQUE, fee REAL)"""
    ]
    for table in tables: 
        conn.execute(table)
    
    # Seed default tiers if the table is empty
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM delivery_tiers")
    if cursor.fetchone()[0] == 0:
        default_tiers = [
            (1.0, 0.0),
            (5.0, 400.0),
            (10.0, 800.0),
            (15.0, 1200.0)
        ]
        cursor.executemany("INSERT INTO delivery_tiers (max_km, fee) VALUES (?, ?)", default_tiers)
        conn.commit()

    conn.commit()
    conn.close()

# --- 5. EXECUTION GUARD ---
if __name__ == "__main__":
    init_db()
    patch_database()
