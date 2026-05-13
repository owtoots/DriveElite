import streamlit as st
import pandas as pd
import datetime
import time
import random
import os
import smtplib
import math
import urllib.request
import urllib.error
import json
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from database_utils import get_connection
import calendar
from datetime import timedelta


# ==========================================
# 1. PAGE CONFIG & LOGO (Must be first!)
# ==========================================
st.set_page_config(page_title="DriveElite Renter", layout="wide")
st.sidebar.image("logo.png", use_container_width=True)

# ==========================================
# 💎 2. THE "CRYSTAL ELITE" CSS ENGINE
# ==========================================
st.markdown("""
<style>
    /* --- GLOBAL THEME --- */
    [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #F8FAFC !important;
        color: #0F172A !important;
        font-family: 'Inter', -apple-system, sans-serif !important;
    }
    
    /* --- SIDEBAR & LOGO REORDER HACK --- */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E2E8F0 !important;
    }
    
    [data-testid="stSidebarContent"] {
        display: flex !important;
        flex-direction: column !important;
    }
    
    [data-testid="stSidebarUserContent"] {
        order: 1 !important;
        padding-top: 0rem !important;
        margin-top: -1.5rem !important; 
        padding-bottom: 1rem !important;
    }

    [data-testid="stSidebarNav"] {
        order: 2 !important;
        padding-top: 0rem !important; 
    }

    /* --- CARDS & BUTTONS --- */
    [data-testid="stForm"], .stForm, div[data-testid="stExpander"], div.stMetric {
        background-color: #FFFFFF !important;
        padding: 20px !important;
        border-radius: 16px !important;
        border: 1px solid #E2E8F0 !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
    }

    div.stButton > button, [data-testid="stFormSubmitButton"] > button {
        background-color: #2563EB !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 700 !important;
        border-radius: 10px !important;
        padding: 10px 24px !important;
        text-transform: uppercase !important;
        transition: all 0.2s ease !important;
    }
    
    div.stButton > button p, [data-testid="stFormSubmitButton"] > button p {
        color: #FFFFFF !important;
    }

    div.stButton > button:hover {
        background-color: #1D4ED8 !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
        transform: translateY(-1px) !important;
    }

    /* --- TYPOGRAPHY & INPUTS --- */
    div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 8px !important;
    }
    input { color: #1E293B !important; }
    h1, h2, h3 { color: #0F172A !important; font-weight: 800 !important; }
    label { color: #475569 !important; font-weight: 600 !important; }
    
    /* --- BILL BOX (RECEIPT) --- */
    .bill-box { 
        background-color: #ffffff; 
        padding: 20px; 
        border-radius: 10px; 
        border: 2px solid #E2E8F0; 
        margin-top: 10px; 
        box-shadow: 4px 4px 10px rgba(0,0,0,0.05); 
        color: #1E293B; 
    }
    .table-bill { width:100%; font-family: monospace; font-size: 1.05em; border-collapse: collapse; color: #1E293B; }
    .table-bill td { padding: 6px 0; }
    .bill-label { font-weight: 700; color: #0F172A; }

    /* 🚨 KILL THE STREAMLIT FADE/BLINK EFFECT 🚨 */
    [data-testid="stAppViewContainer"] > .main { transition: none !important; }
    .element-container, .stMarkdown, .stText { transition: none !important; animation: none !important; opacity: 1 !important; }
    div[data-testid="stStaleElement"] { opacity: 1 !important; transition: none !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. DATABASE CONNECTION & SETUP
# ==========================================
conn = get_connection()

# --- DATABASE REPAIR PROTOCOLS ---
def patch_database_tables():
    try: conn.execute("CREATE TABLE IF NOT EXISTS admin_promos (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, message TEXT, target TEXT DEFAULT 'ALL USERS', active INTEGER DEFAULT 1)"); conn.commit()
    except: pass
    try: conn.execute("ALTER TABLE bookings ADD COLUMN receipt_img BLOB"); conn.commit()
    except: pass
    try:
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
    except: pass

patch_database_tables()
if not os.path.exists("uploads/chat_images"): os.makedirs("uploads/chat_images")

# --- FETCH DYNAMIC PLATFORM SETTINGS (MASTER FETCH) ---
try:
    settings_df = pd.read_sql_query("SELECT payment_mode, renter_markup_pct, operator_name FROM platform_settings WHERE id = 1", conn)

    if not settings_df.empty:
        gateway_mode = settings_df.iloc[0]['payment_mode']
        raw_fee = settings_df.iloc[0]['renter_markup_pct']
        dynamic_renter_fee = float(raw_fee) if pd.notnull(raw_fee) else 0.07
        raw_op = settings_df.iloc[0]['operator_name']
        operator_name = str(raw_op) if pd.notnull(raw_op) else "Platform"
    else:
        gateway_mode, dynamic_renter_fee, operator_name = "MANUAL_QR", 0.07, "Platform"
except Exception:
    gateway_mode, dynamic_renter_fee, operator_name = "MANUAL_QR", 0.07, "Platform"

# ==========================================
# 4. UTILITIES & HELPERS
# ==========================================
if "temp_msg_renter" not in st.session_state: st.session_state.temp_msg_renter = ""

def get_booked_dates(vehicle_id, conn):
    """Finds all dates a specific vehicle is already booked."""
    query = "SELECT pickup_time, return_time FROM bookings WHERE vehicle_id = ? AND status IN ('CONFIRMED', 'ONGOING', 'PENDING')"
    df = pd.read_sql_query(query, conn, params=(vehicle_id,))
    booked_days = set()
    for _, row in df.iterrows():
        try:
            start_date = pd.to_datetime(row['pickup_time']).date()
            end_date = pd.to_datetime(row['return_time']).date()
            delta = end_date - start_date
            for i in range(delta.days + 1):
                day = start_date + timedelta(days=i)
                booked_days.add(day)
        except Exception:
            pass
    return booked_days

# ==========================================
# 5. AUTHENTICATION FLOW
# ==========================================
if not st.session_state.get('logged_in') or st.session_state.get('role') != 'RENTER':
    st.markdown("<h2 style='text-align: center;'>🚙 RENTER LOGIN</h2>", unsafe_allow_html=True)
    with st.form("login_renter"):
        u, p = st.text_input("Username"), st.text_input("Password", type="password")
        if st.form_submit_button("LOGIN TO SHOWROOM", use_container_width=True):
            user = pd.read_sql_query("SELECT * FROM platform_users WHERE username=? AND password=? AND role='RENTER'", conn, params=(u, p))
            if not user.empty:
                if user.iloc[0]['admin_status'] == 'APPROVED':
                    st.session_state.logged_in, st.session_state.username, st.session_state.role = True, u, 'RENTER'
                    st.rerun()
                else: st.warning("⏳ Your account is pending Admin approval.")
            else: st.error("❌ Invalid credentials.")
    st.stop()

renter_user = st.session_state.username

# ==========================================
# 6. HEADER & MAIN INTERFACE
# ==========================================
st.markdown("<h1 style='text-align: center;'>🚙 RENTER COMMAND CENTER</h1>", unsafe_allow_html=True)
col_l, col_m, col_r = st.columns([1, 4, 1])
with col_r:
    if st.button("🔒 LOGOUT", use_container_width=True):
        st.session_state.clear(); st.rerun()
st.divider()

tabs = st.tabs(["🌟 VEHICLE SHOWROOM", "📅 MY BOOKINGS"])

# ==========================================
    # 🚘 RENTER SHOWROOM
    # ==========================================
    st.header("🚘 Available Fleet")

    # 1. Fetch all approved and available cars
    available_cars = pd.read_sql_query("SELECT * FROM vehicles WHERE admin_status = 'APPROVED' AND booking_status = 'AVAILABLE'", conn)

    if available_cars.empty:
        st.info("Our fleet is currently fully booked. Please check back later!")
    else:
        # 2. Get unique car categories for the tabs
        # Assuming your database has a 'type' column (SUV, Sedan, Van). Adjust if named differently!
        if 'type' in available_cars.columns:
            categories = ["All"] + sorted(available_cars['type'].dropna().unique().tolist())
        else:
            categories = ["All"]
            
        tabs = st.tabs(categories)
        
        # 3. Loop through each tab and display the filtered cars
        for tab_index, cat in enumerate(categories):
            with tabs[tab_index]:
                
                # Filter cars for this specific tab
                if cat == "All":
                    category_cars = available_cars.copy()
                else:
                    category_cars = available_cars[available_cars['type'] == cat].copy()
                
                # --- YOUR INTEGRATED SHOWROOM LAYOUT ---
                if category_cars.empty:
                    st.info("No vehicles available in this category right now.")
                else:
                    # Limit to 8 cars (4 columns x 2 rows)
                    display_cars = category_cars.head(8)
                    
                    # 🛠️ CRITICAL FIX: Reset index so the (idx % 4) math works perfectly 0, 1, 2, 3...
                    display_cars = display_cars.reset_index(drop=True)
                    
                    # Create the 4-column grid
                    grid_cols = st.columns(4)
                    
                    for idx, car in display_cars.iterrows():
                        with grid_cols[idx % 4]: 
                            with st.container(border=True):
                                
                                # --- TOP: Image ---
                                img_p = car.get('vehicle_img')
                                if img_p and os.path.exists(img_p): 
                                    st.image(img_p, use_container_width=True)
                                else: 
                                    st.image("https://placehold.co/600x400?text=Vehicle+Image", use_container_width=True)
                                
                                # --- MIDDLE: Details (WITH Price) ---
                                st.markdown(f"#### {car['make']} {car['model']}\n**Year:** {car['year']}\n\n<h5 style='color: #2563EB;'>₱{car.get('daily_rate', 0):,.2f} / day</h5>", unsafe_allow_html=True)
                                
                                # --- BOTTOM: Button ---
                                # Added _{cat} to the key to prevent Duplicate Widget ID errors between tabs
                                if st.button("⚡ BOOK NOW", key=f"book_btn_{car['id']}_{cat}", type="primary", use_container_width=True):
                                    st.session_state.selected_car_id = car['id']
                                    st.session_state.booking_step = "checkout"
                                    st.rerun()
                        
                        # --- POPOVER CHECKOUT MANAGER ---
                        with st.popover(f"⚡ BOOK {car['model'].upper()} NOW", use_container_width=True):
                            
                            # State Tracking for 2-Step Process
                            stage_key = f"chk_stage_{car['id']}"
                            ref_key = f"pend_ref_{car['id']}"
                            if stage_key not in st.session_state: st.session_state[stage_key] = 0
                            
                            unavailable_dates = get_booked_dates(car['id'], conn)
                            
                            # -------------------------------------------------------------
                            # CHECKOUT STAGE 0: SELECT DATES & CONFIRM SOFT LOCK
                            # -------------------------------------------------------------
                            if st.session_state[stage_key] == 0:
                                # Visual Calendar
                                existing_bookings = pd.read_sql_query("SELECT pickup_time, return_time FROM bookings WHERE vehicle_id = ? AND status NOT IN ('CANCELLED', 'REJECTED')", conn, params=(car['id'],))
                                booked_dates = set()
                                for _, row in existing_bookings.iterrows():
                                    try:
                                        s_dt, e_dt = pd.to_datetime(row['pickup_time']).date(), pd.to_datetime(row['return_time']).date()
                                        for idx in range((e_dt - s_dt).days + 1): booked_dates.add((s_dt + datetime.timedelta(days=idx)).strftime("%Y-%m-%d"))
                                    except: pass

                                today = datetime.date.today()
                                st.markdown(render_availability_calendar(today.year, today.month, booked_dates), unsafe_allow_html=True)
                                
                                d1 = st.date_input("Pickup Date", min_value=datetime.date.today(), key=f"d1_{car['id']}")
                                t1 = st.time_input("Pickup Time", value=datetime.time(9, 0), key=f"t1_{car['id']}", step=datetime.timedelta(hours=1))
                                d2 = st.date_input("Return Date", min_value=d1, value=d1, key=f"d2_{car['id']}")
                                t2 = st.time_input("Return Time", value=datetime.time(9, 0), key=f"t2_{car['id']}", step=datetime.timedelta(hours=1))
                                
                                can_book = True
                                requested_days = set([d1 + datetime.timedelta(days=j) for j in range((d2 - d1).days + 1)])
                                clashes = requested_days.intersection(unavailable_dates)
                                if clashes:
                                    can_book = False
                                    st.error(f"🚨 Vehicle booked on: {', '.join([d.strftime('%b %d') for d in sorted(list(clashes))])}")

                                drive_mode = st.radio("Mode", ["Self-Drive", "With Driver (+₱1k/day)"], key=f"dm_{car['id']}")
                                dest = st.text_input("Destination", key=f"dest_{car['id']}")
                                luzon_agree = st.checkbox("I agree to LUZON ONLY travel.", key=f"luzon_{car['id']}")
                                ZONES = {"HQ: Pasig/Ortigas/BGC (Free)": 0.0, "Zone 1: Cubao/Sta. Mesa/Makati": 500.0, "Zone 2: Manila/QC/MOA": 1000.0, "Zone 3: Alabang/LP": 1500.0}
                                p_zone = st.selectbox("Pickup Zone", list(ZONES.keys()), key=f"pz_{car['id']}")
                                p_exact = st.text_input("Pickup Address", key=f"pa_{car['id']}")
                                r_zone = st.selectbox("Return Zone", list(ZONES.keys()), key=f"rz_{car['id']}")
                                r_exact = st.text_input("Return Address", key=f"ra_{car['id']}")

                                p_dt_obj, r_dt_obj = datetime.datetime.combine(d1, t1), datetime.datetime.combine(d2, t2)
                                if r_dt_obj <= p_dt_obj: 
                                    st.error("⚠️ Return time must be after pickup.")
                                    can_book = False
                                else:
                                    full_days, billed_hrs, base_cost, ext_fee, subtotal = calculate_24h_rental(p_dt_obj, r_dt_obj, base_rate, 300.0, 59)
                                    driver_fee = (full_days + (1 if billed_hrs > 0 else 0)) * 1000.0 if "Driver" in drive_mode else 0.0
                                    
                                    try:
                                        tiers_df = pd.read_sql_query("SELECT min_days, discount_pct FROM discount_tiers ORDER BY min_days DESC", conn)
                                        discount_pct = next((float(r['discount_pct']) for _, r in tiers_df.iterrows() if full_days >= r['min_days']), 0.0)
                                    except: discount_pct = 0.0

                                    savings = subtotal * discount_pct
                                    discounted_subtotal = subtotal - savings
                                    
                                    applied_renter_fee = dynamic_renter_fee if full_days >= 4 else 0.0
                                    platform_fee = discounted_subtotal * applied_renter_fee
                                    p_fee, r_fee = ZONES.get(p_zone, 0.0), ZONES.get(r_zone, 0.0)
                                    grand_total = discounted_subtotal + platform_fee + driver_fee + p_fee + r_fee

                                    # Cost Breakdown Receipt
                                    st.markdown("#### 🧾 Cost Breakdown")
                                    plural = "day" if full_days == 1 else "days"
                                    
                                    # We use safe double-quotes outside, and single-quotes inside to prevent Syntax Errors!
                                    rows = [f"<tr><td class='bill-label'>Base Rental (₱{base_rate:,.2f} x {full_days} {plural})</td><td style='text-align:right; font-weight:bold;'>₱{base_cost:,.2f}</td></tr>"]
                                    
                                    if billed_hrs > 0: 
                                        rows.append(f"<tr><td style='color:#d35400;'>Hourly Extension</td><td style='text-align:right; color:#d35400;'>+₱{ext_fee:,.2f}</td></tr>")
                                    
                                    if savings > 0: 
                                        rows.append(f"<tr><td style='color:#cc0000;'>Duration Discount ({int(discount_pct * 100)}%)</td><td style='text-align:right; color:#cc0000;'>-₱{savings:,.2f}</td></tr>")
                                    
                                    # Here is the dynamic Nucluez / Platform Fee line working perfectly!
                                    rows.append(f"<tr><td style='padding: 8px; color: #16A34A;'>{operator_name} Fee ({int(applied_renter_fee * 100)}%)</td><td style='text-align:right; color:#27ae60;'>+₱{platform_fee:,.2f}</td></tr>")
                                    
                                    if "Driver" in drive_mode: 
                                        rows.append(f"<tr><td style='color:#003399;'>Driver Fee</td><td style='text-align:right; color:#003399;'>+₱{driver_fee:,.2f}</td></tr>")
                                    if p_fee > 0: 
                                        rows.append(f"<tr><td style='color:#555;'>Pickup Fee</td><td style='text-align:right; color:#555;'>+₱{p_fee:,.2f}</td></tr>")
                                    if r_fee > 0: 
                                        rows.append(f"<tr><td style='color:#555;'>Return Fee</td><td style='text-align:right; color:#555;'>+₱{r_fee:,.2f}</td></tr>")
                                    
                                    bill_html = f"<div class='bill-box'><table class='table-bill' style='width:100%;'>{''.join(rows)}<tr style='border-top:2px solid #000;'><td class='bill-label' style='font-weight:900;'>GRAND TOTAL</td><td style='text-align:right; font-weight:900; font-size:1.1em;'>₱{grand_total:,.2f}</td></tr></table></div>"
                                    
                                    st.markdown(bill_html, unsafe_allow_html=True)
                                    st.divider()

                                    # Overlap Security Check
                                    is_overlapping = False
                                    for _, row in pd.read_sql_query("SELECT pickup_time, return_time FROM bookings WHERE vehicle_id = ? AND status NOT IN ('CANCELLED', 'REJECTED')", conn, params=(car['id'],)).iterrows():
                                        if p_dt_obj < pd.to_datetime(row['return_time']) and r_dt_obj > pd.to_datetime(row['pickup_time']):
                                            is_overlapping = True; break
                                    
                                    if is_overlapping:
                                        st.error("🚨 **DATE UNAVAILABLE:** Your exact times overlap with an existing reservation.")
                                        can_book = False 

                                    if st.button("1. CONFIRM BOOKING (SOFT LOCK)", key=f"conf_{car['id']}", type="primary", use_container_width=True, disabled=not can_book):
                                        if dest and p_exact and r_exact and luzon_agree:
                                            with st.spinner("Securing your dates..."):
                                                b_ref = str(random.randint(100000, 999999))
                                                p_dt_str, r_dt_str = p_dt_obj.strftime("%Y-%m-%d %H:%M"), r_dt_obj.strftime("%Y-%m-%d %H:%M")
                                                is_drvr_int = 1 if "Driver" in drive_mode else 0
                                                
                                                # ==========================================
                                                # 🔀 THE SMART PAYMENT TOGGLE
                                                # ==========================================
                                                if gateway_mode == "PAYMONGO":
                                                    # --- DOOR A: AUTOMATED PAYMONGO ---
                                                    conn.execute("INSERT INTO bookings (renter_username, vehicle_id, pickup_time, return_time, amount, status, destination, pickup_loc, return_loc, with_driver, booking_ref) VALUES (?, ?, ?, ?, ?, 'PENDING', ?, ?, ?, ?, ?)", 
                                                                 (renter_user, car['id'], p_dt_str, r_dt_str, grand_total, dest, f"{p_zone}: {p_exact}", f"{r_zone}: {r_exact}", is_drvr_int, b_ref))
                                                    conn.commit()
                                                    
                                                    try:
                                                        SECRET_KEY = st.secrets["paymongo_active_key"]
                                                        pay_amount = int(grand_total * 100) # Centavos
                                                        auth_string = f"{SECRET_KEY}:"
                                                        base64_auth = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
                                                        
                                                        url = "https://api.paymongo.com/v1/links"
                                                        payload = {"data": {"attributes": {"amount": pay_amount, "description": f"DriveElite - {car['make']} {car['model']} (Ref: {b_ref})", "remarks": f"Renter: {renter_user}"}}}
                                                        
                                                        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'))
                                                        req.add_header('accept', 'application/json')
                                                        req.add_header('content-type', 'application/json')
                                                        req.add_header('authorization', f'Basic {base64_auth}')
                                                        
                                                        response = urllib.request.urlopen(req)
                                                        checkout_url = json.loads(response.read().decode('utf-8'))['data']['attributes']['checkout_url']
                                                        
                                                        st.success(f"✅ Booking Saved (Ref: #{b_ref})")
                                                        st.markdown(f"### 💳 [👉 CLICK HERE TO PAY ₱{grand_total:,.2f} VIA PAYMONGO]({checkout_url})")
                                                        st.info("Complete your payment using the link above. Our system will auto-verify shortly.")
                                                    except Exception as e:
                                                        st.error("Failed to generate payment link. Please try again or contact support.")
                                                
                                                else:
                                                    # --- DOOR B: MANUAL BPI FLOW (Moves to Stage 1) ---
                                                    conn.execute("INSERT INTO bookings (renter_username, vehicle_id, pickup_time, return_time, amount, status, destination, pickup_loc, return_loc, with_driver, booking_ref) VALUES (?, ?, ?, ?, ?, 'PENDING', ?, ?, ?, ?, ?)", 
                                                                 (renter_user, car['id'], p_dt_str, r_dt_str, grand_total, dest, f"{p_zone}: {p_exact}", f"{r_zone}: {r_exact}", is_drvr_int, b_ref))
                                                    conn.commit()
                                                    st.session_state[stage_key] = 1
                                                    st.session_state[ref_key] = b_ref
                                                    st.rerun()
                                        else: 
                                            st.warning("⚠️ Please fill all required fields (Destination, Address, and Luzon Agreement).")

                            # -------------------------------------------------------------
                            # CHECKOUT STAGE 1: VALIDATE BPI PAYMENT (HARD LOCK TRIGGER)
                            # -------------------------------------------------------------
                            elif st.session_state[stage_key] == 1:
                                b_ref = st.session_state[ref_key]
                                st.success(f"✅ Dates Reserved! Your Reference Number is: **#{b_ref}**")
                                
                                with st.container(border=True):
                                    st.markdown("### 🏦 Manual Bank Transfer")
                                    st.write("**Bank:** BPI")
                                    st.write("**Account Name:** Romeo Albao Jr.")
                                    st.write("**Account Number:** 1234-5678-90")
                                    
                                    # Fetch total amount for display
                                    amt_df = pd.read_sql_query("SELECT amount FROM bookings WHERE booking_ref = ?", conn, params=(b_ref,))
                                    owed_amount = float(amt_df.iloc[0]['amount']) if not amt_df.empty else 0.0
                                    st.write(f"**Amount to Transfer:** :green[**₱{owed_amount:,.2f}**]")
                                    
                                    s1, c_img, s2 = st.columns([1, 1, 1])
                                    with c_img:
                                        try: st.image("bpi_qr.png", use_container_width=True)
                                        except: st.info("[BPI QR IMAGE GOES HERE]")
                                    
                                    st.divider()
                                    st.write("#### 📤 Upload Proof of Payment")
                                    st.caption("Upload a screenshot of your transfer. Admin will lock your schedule upon validation.")
                                    receipt_file = st.file_uploader("Upload Receipt", type=['jpg', 'png', 'jpeg'], key=f"rec_{car['id']}")
                                    
                                    c_back, c_val = st.columns([1, 2])
                                    if c_back.button("Cancel Booking", key=f"canc_{car['id']}", use_container_width=True):
                                        conn.execute("DELETE FROM bookings WHERE booking_ref = ?", (b_ref,)); conn.commit()
                                        st.session_state[stage_key] = 0
                                        del st.session_state[ref_key]
                                        st.rerun()
                                        
                                    if c_val.button("2. VALIDATE PAYMENT SENT", type="primary", use_container_width=True, key=f"val_{car['id']}"):
                                        if receipt_file:
                                            receipt_bytes = receipt_file.read()
                                            with st.spinner("Transmitting to Admin..."):
                                                # Save the receipt directly to the database
                                                conn.execute("UPDATE bookings SET receipt_img = ?, status = 'VERIFYING' WHERE booking_ref = ?", (receipt_bytes, b_ref))
                                                
                                                receipt_path = f"uploads/chat_images/receipt_{b_ref}.jpg"
                                                with open(receipt_path, "wb") as f: f.write(receipt_bytes)
                                                
                                                owner_username = pd.read_sql_query("SELECT owner_username FROM vehicles WHERE id=?", conn, params=(car['id'],)).iloc[0]['owner_username']
                                                conn.execute("INSERT INTO chat_messages (booking_ref, sender_username, receiver_username, message_text, image_path) VALUES (?, ?, ?, ?, ?)", 
                                                             (b_ref, renter_user, owner_username, "Payment Receipt Uploaded for Admin Verification.", receipt_path))
                                                conn.commit()
                                                
                                          
                                            st.toast("✅ Receipt Sent to Admin!")
                                            st.session_state[stage_key] = 0
                                            del st.session_state[ref_key]
                                            time.sleep(2)
                                            st.rerun()
                                        else:
                                            st.error("🚨 Please upload a screenshot of your receipt.")

# --- TAB 1: MY BOOKINGS ---
with tabs[1]:
    trip_tabs = st.tabs(["🚀 Active Trips", "📜 History"])
    my_trips = pd.read_sql_query("SELECT b.*, v.make, v.model, v.plate, v.owner_username FROM bookings b JOIN vehicles v ON b.vehicle_id = v.id WHERE b.renter_username = ? ORDER BY b.pickup_time DESC", conn, params=(renter_user,))
    
    with trip_tabs[0]:
        active = my_trips[my_trips['status'].isin(['CONFIRMED', 'ONGOING', 'PENDING', 'VERIFYING'])]
        if active.empty: st.info("No active trips.")
        for _, t in active.iterrows():
            status_icon = "⏳" if t['status'] in ['PENDING', 'VERIFYING'] else "✅"
            with st.expander(f"{status_icon} {t['make']} {t['model']} ({t['plate']})"):
                st.write(f"**Ref:** #{t['booking_ref']} | **Status:** {t['status']}")
                st.write(f"**Pickup:** {t['pickup_time']}")
                if t['status'] in ['PENDING', 'VERIFYING']: st.warning("Admin is verifying your payment receipt.")
                
                # CHAT LOGIC
                st.divider()
                st.markdown("#### 💬 Chat with Owner / Admin")
                b_ref_str = str(t['booking_ref'])
                chat_win = st.container(height=300, border=True)
                with chat_win:
                    msgs = pd.read_sql_query("SELECT * FROM chat_messages WHERE booking_ref = ? ORDER BY timestamp ASC", conn, params=(b_ref_str,))
                    for _, m in msgs.iterrows():
                        align = "right" if m['sender_username'] == renter_user else "left"
                        bg_col = "#2563EB" if m['sender_username'] == renter_user else "#F1F5F9"
                        txt_col = "#FFFFFF" if m['sender_username'] == renter_user else "#0F172A"
                        st.markdown(f'''
                        <div style="display:flex; justify-content:{"flex-end" if align=="right" else "flex-start"}; margin-bottom:5px;">
                            <div style="background-color:{bg_col}; color:{txt_col}; padding:10px 15px; border-radius:10px; max-width:80%;">
                                <b>{m["sender_username"]}:</b><br>{m["message_text"]}
                            </div>
                        </div>
                        ''', unsafe_allow_html=True)
                        if m.get('image_path') and os.path.exists(m['image_path']):
                            c_s1, c_img, c_s2 = st.columns([1,2,1] if align=="right" else [0.1,2,2])
                            with c_img: st.image(m['image_path'])
                
                c_img, c_msg = st.columns([1, 4])
                with c_img: 
                    r_img = st.file_uploader("📷", type=['jpg','png','jpeg'], accept_multiple_files=True, key=f"r_img_{b_ref_str}", label_visibility="collapsed")
                with c_msg: 
                    st.text_input("Reply...", key=f"chat_{b_ref_str}", on_change=clear_renter_chat, args=(b_ref_str,), placeholder="Type a message...")

                st.button("Send", key=f"btn_{b_ref_str}", on_click=clear_renter_chat, args=(b_ref_str,), use_container_width=True)
                enter_pressed = st.session_state.get(f"trigger_send_{b_ref_str}", False)

                if enter_pressed:
                    final_msg = st.session_state.temp_msg_renter
                    has_text = bool(final_msg.strip())
                    has_imgs = bool(r_img and len(r_img) > 0)
                    
                    if has_text or has_imgs:
                        if has_imgs:
                            for idx, img_file in enumerate(r_img):
                                path = save_chat_image(img_file, b_ref_str)
                                text_to_save = final_msg if idx == 0 else ""
                                if idx == 0 and not has_text: text_to_save = "📸 Uploaded Photo."
                                conn.execute("INSERT INTO chat_messages (booking_ref, sender_username, receiver_username, message_text, image_path) VALUES (?, ?, ?, ?, ?)", 
                                             (b_ref_str, renter_user, t['owner_username'], text_to_save, path))
                        else:
                            conn.execute("INSERT INTO chat_messages (booking_ref, sender_username, receiver_username, message_text, image_path) VALUES (?, ?, ?, ?, ?)", 
                                         (b_ref_str, renter_user, t['owner_username'], final_msg, ""))
                        conn.commit()
                        st.session_state.temp_msg_renter = ""
                        st.session_state[f"trigger_send_{b_ref_str}"] = False
                        st.rerun()

    with trip_tabs[1]:
        history = my_trips[my_trips['status'] == 'COMPLETED']
        if history.empty: st.info("No completed trips.")
        for _, t in history.iterrows():
            with st.expander(f"✅ COMPLETED: {t['make']} {t['model']} | {str(t['pickup_time'])[:10]}"):
                st.write(f"**Final Cost:** ₱{t['amount']:,.2f}")
                if pd.isna(t.get('rating')) or t.get('rating') == "":
                    with st.container(border=True):
                        st.markdown("#### ⭐ Rate Your Experience")
                        raw_stars = st.feedback("stars", key=f"s_{t['id']}")
                        r = st.text_area("Review", key=f"r_{t['id']}")
                        if st.button("Submit", type="primary", use_container_width=True, key=f"btn_sub_{t['id']}"):
                            if raw_stars is not None:
                                conn.execute("UPDATE bookings SET rating = ?, review = ? WHERE id = ?", (raw_stars + 1, r, t['id']))
                                conn.commit(); st.success("Submitted!"); time.sleep(1); st.rerun()
                else: st.success(f"**Rating:** {'⭐' * int(float(t['rating']))}")
