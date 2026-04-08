import sqlite3

def get_connection():
    # Connect to the SQLite database
    conn = sqlite3.connect("driveelite.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    
    # --- 1. USERS TABLE ---
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT,
                    full_name TEXT,
                    email TEXT,
                    age INTEGER,
                    nationality TEXT,
                    address TEXT,
                    contact_number TEXT,
                    role TEXT,
                    admin_status TEXT DEFAULT 'PENDING',
                    govt_id_img TEXT,
                    license_img TEXT)''')
                    
    # --- 2. VEHICLES TABLE (Assets) ---
    conn.execute('''CREATE TABLE IF NOT EXISTS vehicles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, owner_username TEXT, make TEXT, model TEXT,
                    year TEXT, plate TEXT, bank_name TEXT, account_no TEXT, vehicle_img TEXT,
                    or_cr_img TEXT, insurance_img TEXT, category TEXT, approved_price REAL, daily_rate REAL,
                    admin_status TEXT DEFAULT 'PENDING', booking_status TEXT DEFAULT 'AVAILABLE', 
                    ref_no TEXT)''')

    # --- 3. BOOKINGS TABLE (The Finance & Logistics Engine) ---
    conn.execute('''CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, vehicle_id INTEGER, renter_username TEXT,
                    status TEXT, pickup_loc TEXT, return_loc TEXT, destination TEXT, pickup_time TEXT,
                    return_time TEXT, amount REAL, payment_method TEXT, front_img TEXT, back_img TEXT, 
                    left_img TEXT, right_img TEXT, odometer_img TEXT, dseat_img TEXT, pseat_img TEXT, 
                    tire_img TEXT, trunk_img TEXT, actual_dl_img TEXT, damage_img TEXT, payout_status TEXT DEFAULT 'PENDING',
                    with_driver INTEGER DEFAULT 0, assigned_driver TEXT, rating INTEGER, review_comment TEXT,
                    delivery_fee REAL DEFAULT 0, return_fee REAL DEFAULT 0, 
                    deposit_collected INTEGER DEFAULT 0, penalties REAL DEFAULT 0.0, booking_ref TEXT)''')

    # --- 4. DRIVERS TABLE ---
    conn.execute('''CREATE TABLE IF NOT EXISTS drivers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, owner_username TEXT, first_name TEXT, 
                    cursor.execute('''INSERT INTO users 
                              (username, password, role, full_name, email, age, nationality, address, contact_number, govt_id_img, license_img, signature_img) 
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', payload)
                    is_owner INTEGER DEFAULT 0, govt_id_img TEXT, license_img TEXT, admin_status TEXT DEFAULT 'PENDING')''')

    # --- 5. CATEGORIES TABLE ---
    conn.execute('''CREATE TABLE IF NOT EXISTS vehicle_categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, default_price REAL)''')

    # --- 6. PROMOS TABLE ---
    conn.execute('''CREATE TABLE IF NOT EXISTS admin_promos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, message TEXT, 
                    target TEXT DEFAULT 'ALL USERS', active INTEGER DEFAULT 1)''')

    conn.commit()
    return conn

def patch_database():
    """Safely injects missing columns into older database versions."""
    conn = get_connection()
    
    # 1. Patch for Vehicles (Pricing Tiers)
    try: conn.execute("ALTER TABLE vehicles ADD COLUMN category TEXT")
    except: pass
    try: conn.execute("ALTER TABLE vehicles ADD COLUMN daily_rate REAL")
    except: pass
    
    # 2. Patch for Bookings (Reviews & Ratings)
    try: conn.execute("ALTER TABLE bookings ADD COLUMN rating INTEGER")
    except: pass
    try: conn.execute("ALTER TABLE bookings ADD COLUMN review TEXT")
    except: pass
    
    # 3. Patch for Users (Emails)
    try: conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
    except: pass

    conn.commit()
    conn.close()

# This automatically runs the patcher every time the app loads!
patch_database()
