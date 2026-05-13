import sqlite3
import os

# --- 1. SINGLE SOURCE OF TRUTH ---
# This tells the app to save everything on your permanent Render Disk mount point
DB_PATH = "/data/driveelite_v2.db"

def get_connection():
    """
    Creates a connection to the SQLite database.
    Added timeout=15.0 to prevent 'Database is locked' errors during concurrent writes.
    """
    return sqlite3.connect(DB_PATH, check_same_thread=False, timeout=15.0)

# --- 2. TABLE INITIALIZATION ---
def init_db():
    """Initializes all required tables for DriveElite V2."""
    conn = get_connection()
    
    # SUPPORT CHATS 
    conn.execute("""
        CREATE TABLE IF NOT EXISTS support_chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            receiver TEXT,
            message TEXT,
            ts DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # PLATFORM USERS TABLE
    conn.execute('''
        CREATE TABLE IF NOT EXISTS platform_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            username TEXT UNIQUE, 
            password TEXT,
            role TEXT,
            full_name TEXT, 
            email TEXT, 
            age TEXT, 
            nationality TEXT, 
            address TEXT,
            contact_number TEXT, 
            admin_status TEXT DEFAULT 'PENDING',
            govt_id_img BLOB, 
            license_img BLOB, 
            signature_img BLOB
        )
    ''')

    # VEHICLES TABLE
    conn.execute('''CREATE TABLE IF NOT EXISTS vehicles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, owner_username TEXT, make TEXT, model TEXT,
                    year TEXT, plate TEXT, bank_name TEXT, account_no TEXT, vehicle_img TEXT,
                    or_cr_img TEXT, insurance_img TEXT, category TEXT, approved_price REAL, 
                    daily_rate REAL, admin_status TEXT DEFAULT 'PENDING', 
                    booking_status TEXT DEFAULT 'AVAILABLE', ref_no TEXT)''')

    # BOOKINGS TABLE
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

    # CATEGORIES & PROMOS
    conn.execute('CREATE TABLE IF NOT EXISTS vehicle_categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, default_price REAL)')
    conn.execute('CREATE TABLE IF NOT EXISTS admin_promos (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, message TEXT, target TEXT DEFAULT "ALL USERS", active INTEGER DEFAULT 1)')

    conn.commit()
    conn.close()

# --- 3. PATCHING SYSTEM ---
def patch_database():
    """Safely injects missing columns into the database without losing data."""
    conn = get_connection()
    try: 
        conn.execute("ALTER TABLE bookings ADD COLUMN gateway_fee REAL DEFAULT 0.0")
    except: pass
    
    try: 
        conn.execute("ALTER TABLE bookings ADD COLUMN receipt_img BLOB")
    except: pass
    
    # --- NEW PATCH: Injecting the missing evidence columns ---
    try: 
        conn.execute("ALTER TABLE bookings ADD COLUMN handover_photos TEXT")
    except: pass
    
    try: 
        conn.execute("ALTER TABLE bookings ADD COLUMN damage_img TEXT")
    except: pass
    
    conn.commit()
    conn.close()

# --- 4. EXECUTION ON LOAD ---
# This ensures that whenever database_utils is imported, the DB is ready to go.
if not os.path.exists(os.path.dirname(DB_PATH)):
    try:
        os.makedirs(os.path.dirname(DB_PATH))
    except:
        pass # In case of permissions issues on local dev

init_db()
patch_database()
