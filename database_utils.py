import sqlite3
import os

# --- 1. GLOBAL CONNECTION ---
# Establishing one persistent connection for the session
conn = sqlite3.connect("driveelite_v2.db", check_same_thread=False)
conn.row_factory = sqlite3.Row

def get_connection():
    """Returns the globally defined connection."""
    return conn

# --- 2. TABLE INITIALIZATION ---
def init_db():
    """Initializes all required tables for DriveElite."""
    
    # CHAT MESSAGES (The Room for Renters & Affiliates)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_ref TEXT,
            sender_username TEXT,
            receiver_username TEXT,
            message_text TEXT,
            image_path TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # USERS TABLE
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT,
                    full_name TEXT, email TEXT, age INTEGER, nationality TEXT, address TEXT,
                    contact_number TEXT, role TEXT, admin_status TEXT DEFAULT 'PENDING',
                    govt_id_img TEXT, license_img TEXT, document_url TEXT)''')

    # VEHICLES TABLE
    conn.execute('''CREATE TABLE IF NOT EXISTS vehicles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, owner_username TEXT, make TEXT, model TEXT,
                    year TEXT, plate TEXT, bank_name TEXT, account_no TEXT, vehicle_img TEXT,
                    or_cr_img TEXT, insurance_img TEXT, category TEXT, approved_price REAL, 
                    daily_rate REAL, admin_status TEXT DEFAULT 'PENDING', 
                    booking_status TEXT DEFAULT 'AVAILABLE', ref_no TEXT)''')

    # BOOKINGS TABLE (Added gateway_fee for CC Surcharges)
    conn.execute('''CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, vehicle_id INTEGER, renter_username TEXT,
                    status TEXT, pickup_loc TEXT, return_loc TEXT, destination TEXT, pickup_time TEXT,
                    return_time TEXT, amount REAL, payment_method TEXT, front_img TEXT, back_img TEXT, 
                    left_img TEXT, right_img TEXT, odometer_img TEXT, dseat_img TEXT, pseat_img TEXT, 
                    tire_img TEXT, trunk_img TEXT, actual_dl_img TEXT, damage_img TEXT, 
                    payout_status TEXT DEFAULT 'PENDING', with_driver INTEGER DEFAULT 0, 
                    assigned_driver TEXT, rating INTEGER, review TEXT, gateway_fee REAL DEFAULT 0.0,
                    delivery_fee REAL DEFAULT 0, return_fee REAL DEFAULT 0, 
                    deposit_collected INTEGER DEFAULT 0, penalties REAL DEFAULT 0.0, booking_ref TEXT)''')

    # DRIVERS TABLE
    conn.execute('''CREATE TABLE IF NOT EXISTS drivers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, owner_username TEXT, first_name TEXT, 
                    middle_name TEXT, last_name TEXT, age INTEGER, address TEXT, contact_number TEXT, 
                    is_owner INTEGER DEFAULT 0, govt_id_img TEXT, license_img TEXT, admin_status TEXT DEFAULT 'PENDING')''')

    # CATEGORIES, PROMOS, ETC.
    conn.execute('CREATE TABLE IF NOT EXISTS vehicle_categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, default_price REAL)')
    conn.execute('CREATE TABLE IF NOT EXISTS admin_promos (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, message TEXT, target TEXT DEFAULT "ALL USERS", active INTEGER DEFAULT 1)')

    conn.commit()

# --- ADD THIS TO THE BOTTOM OF database_utils.py ---

def patch_database():
    """Safely injects missing columns into the database without losing data."""
    conn = sqlite3.connect("driveelite.db", check_same_thread=False)
    
    # 1. Patch for Financials (The Gateway Fee / CC Surcharge)
    try:
        conn.execute("ALTER TABLE bookings ADD COLUMN gateway_fee REAL DEFAULT 0.0")
        print("✅ Patch Applied: gateway_fee added to bookings")
    except sqlite3.OperationalError:
        # This means the column is already there, so we do nothing
        pass
    
    # 2. Patch for Chat (Ensure table exists for messenger)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_ref TEXT,
            sender_username TEXT,
            receiver_username TEXT,
            message_text TEXT,
            image_path TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

# Run the patcher every time the utility is loaded
patch_database()

# --- 4. EXECUTION ON LOAD ---
init_db()
patch_database()
