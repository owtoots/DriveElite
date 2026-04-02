import sqlite3
import os

def get_connection():
    # Defines the database file
    conn = sqlite3.connect("driveelite_v2.db", check_same_thread=False)
    
    # --- 1. USERS TABLE (Renters & Affiliates) ---
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, password TEXT, role TEXT, full_name TEXT, 
                    age INTEGER, nationality TEXT, address TEXT, contact_number TEXT, id_img TEXT, 
                    license_img TEXT, admin_status TEXT DEFAULT 'PENDING')''')
    
    # --- 2. VEHICLES TABLE (Assets) ---
    conn.execute('''CREATE TABLE IF NOT EXISTS vehicles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, owner_username TEXT, make TEXT, model TEXT, 
                    year TEXT, plate TEXT, bank_name TEXT, account_no TEXT, vehicle_img TEXT, 
                    or_cr_img TEXT, insurance_img TEXT, category TEXT, approved_price REAL, 
                    admin_status TEXT DEFAULT 'PENDING', booking_status TEXT DEFAULT 'AVAILABLE')''')
    
    # --- 3. BOOKINGS TABLE (The Finance & Logistics Engine) ---
    # Preserves all required columns, including logistics fees and reviews
    conn.execute('''CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, vehicle_id INTEGER, renter_username TEXT, amount REAL, 
                    status TEXT, pickup_loc TEXT, return_loc TEXT, destination TEXT, pickup_time TEXT, 
                    return_time TEXT, payment_method TEXT, front_img TEXT, back_img TEXT, left_img TEXT, 
                    right_img TEXT, odometer_img TEXT, dseat_img TEXT, pseat_img TEXT, tire_img TEXT, 
                    trunk_img TEXT, actual_dl_img TEXT, damage_img TEXT, payout_status TEXT DEFAULT 'PENDING', 
                    with_driver INTEGER DEFAULT 0, assigned_driver TEXT, rating INTEGER, review TEXT,
                    delivery_fee REAL DEFAULT 0, return_fee REAL DEFAULT 0)''')
    
    # --- 4. PROMOS TABLE (Admin Marketing) ---
    conn.execute('''CREATE TABLE IF NOT EXISTS admin_promos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, message TEXT, active INTEGER DEFAULT 1)''')
                    
    # --- 5. CATEGORIES TABLE (Pricing control) ---
    conn.execute('''CREATE TABLE IF NOT EXISTS vehicle_categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, default_price REAL)''')
                    
    # --- 6. DRIVERS TABLE (Affiliate Team) ---
    conn.execute('''CREATE TABLE IF NOT EXISTS drivers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, owner_username TEXT, first_name TEXT, middle_name TEXT, 
                    last_name TEXT, age INTEGER, address TEXT, contact_number TEXT, is_owner INTEGER, 
                    license_img TEXT, govt_id_img TEXT, admin_status TEXT DEFAULT 'PENDING')''')
    
    # --- 7. SUPPORT CHATS (Messenger) ---
    conn.execute('''CREATE TABLE IF NOT EXISTS support_chats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, receiver TEXT, message TEXT, 
                    ts DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # --- THE DATABASE UPGRADE PATCH ---
    # Safely adds required columns to existing databases without breaking them.
    try:
        cur = conn.cursor()
        # Add rating/review if missing
        cur.execute("ALTER TABLE bookings ADD COLUMN rating INTEGER")
        cur.execute("ALTER TABLE bookings ADD COLUMN review TEXT")
        # Add delivery tracking if missing
        cur.execute("ALTER TABLE bookings ADD COLUMN delivery_fee REAL DEFAULT 0")
        cur.execute("ALTER TABLE bookings ADD COLUMN return_fee REAL DEFAULT 0")
        conn.commit()
    except Exception: pass # Ignores if columns already exist
                    
    return conn
