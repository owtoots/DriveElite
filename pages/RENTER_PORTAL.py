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

# --- DATABASE CONNECTION ---
conn = get_connection()

# --- CHAT INPUT RESET LOGIC ---
if "temp_msg_renter" not in st.session_state:
    st.session_state.temp_msg_renter = ""

def get_booked_dates(vehicle_id, conn):
    """Finds all dates a specific vehicle is already booked."""
    # We only care about active trips, pending trips, or confirmed trips. 
    query = "SELECT pickup_time, return_time FROM bookings WHERE vehicle_id = ? AND status IN ('CONFIRMED', 'ONGOING', 'PENDING')"
    df = pd.read_sql_query(query, conn, params=(vehicle_id,))
    
    booked_days = set()
    for _, row in df.iterrows():
        try:
            # FIXED: Corrected column names and pd.to_datetime syntax
            start = pd.to_datetime(row['pickup_time']).date()
            end = pd.to_datetime(row['return_time']).date()
            
            # Add every single day of that trip to our 'booked' list
            delta = end - start
            for i in range(delta.days + 1):
                booked_days.add(start + datetime.timedelta(days=i))
        except Exception:
            pass
            
    return booked_days

def clear_renter_chat(b_ref):
    b_ref_str = str(b_ref)
    unique_key = f"chat_{b_ref_str}"
    if unique_key in st.session_state:
        if st.session_state[unique_key].strip():
            st.session_state.temp_msg_renter = st.session_state[unique_key]
            st.session_state[f"trigger_send_{b_ref_str}"] = True 
        st.session_state[unique_key] = ""

def patch_chat_table():
    """Forces the database to add missing chat columns if they don't exist."""
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

patch_chat_table()

# Ensure admin_promos table exists
try:
    conn.execute("CREATE TABLE IF NOT EXISTS admin_promos (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, message TEXT, target TEXT DEFAULT 'ALL USERS', active INTEGER DEFAULT 1)")
    conn.commit()
except: pass

# --- UTILITIES & HELPERS ---
def save_chat_image(uploaded_file, booking_ref):
    if uploaded_file:
        if not os.path.exists("uploads/chat_images"):
            os.makedirs("uploads/chat_images")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"CHAT_RENTER_{booking_ref}_{timestamp}_{uploaded_file.name}"
        path = os.path.join("uploads/chat_images", filename)
        with open(path, "wb") as f: 
            f.write(uploaded_file.getbuffer())
        return path
    return None

def calculate_24h_rental(pickup_dt, return_dt, daily_rate, hourly_late_fee=300.0, grace_mins=59):
    diff = return_dt - pickup_dt
    total_seconds = diff.total_seconds()
    if total_seconds <= 86400:
        return 1, 0, daily_rate, 0.0, daily_rate
    full_days = int(total_seconds // 86400)
    remainder_mins = (total_seconds % 86400) / 60.0
    billed_hours = 0
    hourly_fee_total = 0.0
    if remainder_mins > grace_mins:
        billed_hours = math.ceil(remainder_mins / 60.0)
        hourly_fee_total = billed_hours * hourly_late_fee
        if hourly_fee_total >= daily_rate:
            full_days += 1
            billed_hours = 0
            hourly_fee_total = 0.0
    base_cost = full_days * daily_rate
    total_rental_cost = base_cost + hourly_fee_total
    return full_days, billed_hours, base_cost, hourly_fee_total, total_rental_cost

# --- PAGE CONFIG ---
st.set_page_config(page_title="DriveElite Showroom", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    /* Your existing styles */
    .stApp { background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); }
    .bill-box { 
        background-color: #ffffff; 
        padding: 20px; 
        border-radius: 10px; 
        border: 2px solid #333333; 
        margin-top: 10px; 
        box-shadow: 4px 4px 10px rgba(0,0,0,0.1); 
        color: #1a1a1a; 
    }
    .table-bill { width:100%; font-family: monospace; font-size: 1.05em; border-collapse: collapse; color: #1a1a1a; }
    .table-bill td { padding: 6px 0; }
    .bill-label { font-weight: 700; color: #000000; }

    /* 🚨 NEW: KILL THE STREAMLIT FADE/BLINK EFFECT 🚨 */
    [data-testid="stAppViewContainer"] > .main {
        transition: none !important;
    }
    .element-container, .stMarkdown, .stText {
        transition: none !important;
        animation: none !important;
        opacity: 1 !important;
    }
    div[data-testid="stStaleElement"] {
        opacity: 1 !important;
        transition: none !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 1. AUTHENTICATION FLOW ---
if not st.session_state.get('logged_in') or st.session_state.get('role') != 'RENTER':
    st.markdown("<h2 style='text-align: center;'>🚙 RENTER ACCESS</h2>", unsafe_allow_html=True)
    with st.form("login_renter"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
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

# --- 2. HEADER ---
st.markdown("<h1 style='text-align: center;'>💼 RENTER COMMAND CENTER</h1>", unsafe_allow_html=True)
col_l, col_m, col_r = st.columns([1, 4, 1])
with col_r:
    if st.button("🔒 LOGOUT", use_container_width=True):
        st.session_state.clear()
        st.rerun()
st.divider()

# --- 3. MAIN TABS ---
tabs = st.tabs(["🌟 VEHICLE SHOWROOM", "📅 MY BOOKINGS"])

# --- TAB 0: VEHICLE SHOWROOM ---
with tabs[0]:
    cat_df = pd.read_sql_query("SELECT name FROM vehicle_categories", conn)
    cat_list = ["All"] + [str(n).strip() for n in cat_df['name'].tolist()]
    c_f1, c_f2 = st.columns([2, 1])
    cat_filter = c_f1.selectbox("Filter by Category", cat_list)
    search_query = c_f2.text_input("Search Brand/Model", placeholder="e.g. Nissan")

    cars = pd.read_sql_query("SELECT * FROM vehicles WHERE admin_status = 'APPROVED' AND booking_status = 'AVAILABLE'", conn)
    if cat_filter != "All": cars = cars[cars['category'].str.strip() == cat_filter]
    if search_query: cars = cars[cars['make'].str.contains(search_query, case=False) | cars['model'].str.contains(search_query, case=False)]

    if cars.empty: st.info("No vehicles currently live.")
    else:
        grid_cols = st.columns(2)
        for i, car in cars.reset_index(drop=True).iterrows():
            with grid_cols[i % 2]:
                with st.container(border=True):
                    col1, col2 = st.columns([1, 1.3])
                    with col1:
                        img_p = car.get('vehicle_img')
                        if img_p and os.path.exists(img_p): st.image(img_p, use_container_width=True)
                        else: st.image("https://placehold.co/600x400?text=No+Image", use_container_width=True)
                    with col2:
                        st.write(f"### {car['make']} {car['model']} ({car['year']})")
                        base_rate = car.get('approved_price', 2000.0)
                        with st.popover(f"⚡ BOOK {car['model'].upper()} NOW", use_container_width=True):
                            unavailable_dates = get_booked_dates(car['id'], conn)
                            d1 = st.date_input("Pickup Date", min_value=datetime.date.today(), key=f"d1_{car['id']}")
                            
                            # APPLIED: Hourly step logic
                            t1 = st.time_input("Pickup Time", value=datetime.time(9, 0), key=f"t1_{car['id']}", step=datetime.timedelta(hours=1))
                            d2 = st.date_input("Return Date", min_value=d1, value=d1, key=f"d2_{car['id']}")
                            t2 = st.time_input("Return Time", value=datetime.time(9, 0), key=f"t2_{car['id']}", step=datetime.timedelta(hours=1))
                            
                            can_book = True
                            requested_days = set()
                            delta = d2 - d1
                            for j in range(delta.days + 1):
                                requested_days.add(d1 + datetime.timedelta(days=j))
                            clashes = requested_days.intersection(unavailable_dates)
                            if clashes:
                                can_book = False
                                st.error(f"🚨 Vehicle booked on: {', '.join([d.strftime('%b %d') for d in sorted(list(clashes))])}")

                            drive_mode = st.radio("Mode", ["Self-Drive", "With Driver (+₱1k/day)"], key=f"dm_{car['id']}")
                            dest = st.text_input("Destination", key=f"dest_{car['id']}")
                            luzon_agree = st.checkbox("I agree to LUZON ONLY travel.", key=f"luzon_{car['id']}")
                            ZONES = {"HQ: Pasig (Free)": 0.0, "Zone 1: Ortigas/BGC": 500.0, "Zone 2: Manila/QC": 1000.0, "Zone 3: Alabang/LP": 1500.0}
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
                                driver_days = full_days + (1 if billed_hrs > 0 else 0)
                                
                                # 🚨 Add this exact line right here to fix the NameError!
                                is_driver = 1 if "Driver" in drive_mode else 0
                                
                                driver_fee = (driver_days * 1000.0) if is_driver else 0.0
                                # --- 1. DYNAMIC DURATION DISCOUNTS ---
                                try:
                                    tiers_df = pd.read_sql_query("SELECT min_days, discount_pct FROM discount_tiers ORDER BY min_days DESC", conn)
                                    discount_pct = 0.0
                                    for _, row in tiers_df.iterrows():
                                        if full_days >= row['min_days']:
                                            discount_pct = float(row['discount_pct'])
                                            break
                                except: 
                                    discount_pct = 0.0

                                savings = subtotal * discount_pct
                                discounted_subtotal = subtotal - savings
                                
                                # --- 2. DYNAMIC MARGINS & 4-DAY RULE ---
                                try:
                                    settings_df = pd.read_sql_query("SELECT renter_markup_pct FROM platform_settings WHERE id = 1", conn)
                                    dynamic_renter_fee = float(settings_df.iloc[0]['renter_markup_pct'])
                                except: 
                                    dynamic_renter_fee = 0.07

                                # 🚨 The 4-Day Rule: Waive the fee if booking is less than 4 days
                                applied_renter_fee = dynamic_renter_fee if full_days >= 4 else 0.0

                                platform_fee = discounted_subtotal * applied_renter_fee
                                
                                p_fee = ZONES[p_zone]
                                r_fee = ZONES[r_zone]
                                grand_total = discounted_subtotal + platform_fee + driver_fee + p_fee + r_fee

                                # --- 3. THE COST BREAKDOWN RECEIPT ---
                                st.markdown("#### 🧾 Cost Breakdown")
                                plural_days = "day" if full_days == 1 else "days"
                                
                                rows = [f'<tr><td class="bill-label">Base Rental (₱{base_rate:,.2f} x {full_days} {plural_days})</td><td style="text-align:right; font-weight:bold;">₱{base_cost:,.2f}</td></tr>']
                                
                                if billed_hrs > 0: 
                                    rows.append(f'<tr><td style="color:#d35400;">Hourly Extension</td><td style="text-align:right; color:#d35400;">+₱{ext_fee:,.2f}</td></tr>')
                                
                                if savings > 0: 
                                    rows.append(f'<tr><td style="color:#cc0000;">Duration Discount ({int(discount_pct * 100)}%)</td><td style="text-align:right; color:#cc0000;">-₱{savings:,.2f}</td></tr>')
                                
                                rows.append(f'<tr><td style="color:#27ae60;">DriveElite Fee ({int(applied_renter_fee * 100)}%)</td><td style="text-align:right; color:#27ae60;">+₱{platform_fee:,.2f}</td></tr>')
                                
                                if is_driver: 
                                    rows.append(f'<tr><td style="color:#003399;">Driver Fee</td><td style="text-align:right; color:#003399;">+₱{driver_fee:,.2f}</td></tr>')
                                if p_fee > 0: 
                                    rows.append(f'<tr><td style="color:#555;">Pickup Fee</td><td style="text-align:right; color:#555;">+₱{p_fee:,.2f}</td></tr>')
                                if r_fee > 0: 
                                    rows.append(f'<tr><td style="color:#555;">Return Fee</td><td style="text-align:right; color:#555;">+₱{r_fee:,.2f}</td></tr>')

                                bill_html = f'<div class="bill-box"><table class="table-bill" style="width:100%;">{"".join(rows)}<tr style="border-top:2px solid #000;"><td class="bill-label" style="font-weight:900;">GRAND TOTAL</td><td style="text-align:right; font-weight:900; font-size:1.1em;">₱{grand_total:,.2f}</td></tr></table></div>'
                                st.markdown(bill_html, unsafe_allow_html=True)
                                
                                st.divider()
                                # ... (The "CONFIRM BOOKING & PAY" button comes exactly after this) ...

# --- TAB 1: MY BOOKINGS ---
with tabs[1]:
    trip_tabs = st.tabs(["🚀 Active Trips", "📜 History"])
    my_trips = pd.read_sql_query("SELECT b.*, v.make, v.model, v.plate, v.owner_username FROM bookings b JOIN vehicles v ON b.vehicle_id = v.id WHERE b.renter_username = ? ORDER BY b.pickup_time DESC", conn, params=(renter_user,))
    
    with trip_tabs[0]:
        active = my_trips[my_trips['status'].isin(['CONFIRMED', 'ONGOING', 'PENDING'])]
        if active.empty: st.info("No active trips.")
        for _, t in active.iterrows():
            with st.expander(f"🚗 {t['make']} {t['model']} ({t['plate']})"):
                st.write(f"**Ref:** #{t['booking_ref']} | **Status:** {t['status']}")
                st.write(f"**Pickup:** {t['pickup_time']}")
                
                # CHAT LOGIC
                st.divider()
                st.markdown("#### 💬 Chat with Owner")
                b_ref_str = str(t['booking_ref'])
                chat_win = st.container(height=300, border=True)
                with chat_win:
                    msgs = pd.read_sql_query("SELECT * FROM chat_messages WHERE booking_ref = ? ORDER BY timestamp ASC", conn, params=(b_ref_str,))
                    for _, m in msgs.iterrows():
                        align = "right" if m['sender_username'] == renter_user else "left"
                        st.markdown(f'<div style="text-align: {align};"><b>{m["sender_username"]}:</b> {m["message_text"]}</div>', unsafe_allow_html=True)
                
                c_i, c_t = st.columns([1, 4])
                with c_t: st.text_input("Reply...", key=f"chat_{b_ref_str}", on_change=clear_renter_chat, args=(b_ref_str,))
                if st.button("Send", key=f"btn_{b_ref_str}"):
                    final_msg = st.session_state.get(f"chat_{b_ref_str}", "")
                    if final_msg:
                        conn.execute("INSERT INTO chat_messages (booking_ref, sender_username, receiver_username, message_text) VALUES (?, ?, ?, ?)", (b_ref_str, renter_user, t['owner_username'], final_msg))
                        conn.commit()
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
