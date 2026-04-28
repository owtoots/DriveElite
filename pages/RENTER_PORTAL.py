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

# --- DATABASE CONNECTION & SELF-REPAIR ---
conn = get_connection()

# --- CHAT INPUT RESET LOGIC ---
if "temp_msg_renter" not in st.session_state:
    st.session_state.temp_msg_renter = ""

def get_booked_dates(vehicle_id, conn):
    """Finds all dates a specific vehicle is already booked."""
    import datetime
    # We only care about active trips, pending trips, or confirmed trips. 
    query = """
        SELECT pickup_time, return_time 
        FROM bookings 
        WHERE vehicle_id = ? AND status NOT IN ('CANCELLED', 'COMPLETED', 'REJECTED')
    """
    df = pd.read_sql_query(query, conn, params=(vehicle_id,))
    
    booked_days = set()
    for _, row in df.iterrows():
        try:
            # Convert database strings to actual Date objects
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
    # Safely lock the reference as a string
    b_ref_str = str(b_ref)
    unique_key = f"chat_{b_ref_str}"
    
    if unique_key in st.session_state:
        # Only trigger if they actually typed something
        if st.session_state[unique_key].strip():
            st.session_state.temp_msg_renter = st.session_state[unique_key]
            st.session_state[f"trigger_send_{b_ref_str}"] = True # THIS TELLS THE APP TO SEND!
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

    try: conn.execute("ALTER TABLE chat_messages ADD COLUMN image_path TEXT"); conn.commit()
    except: pass

    try: conn.execute("ALTER TABLE chat_messages ADD COLUMN receiver_username TEXT"); conn.commit()
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
</style>
""", unsafe_allow_html=True)

# --- 1. AUTHENTICATION FLOW ---
if not st.session_state.get('logged_in') or st.session_state.get('role') != 'RENTER':
    st.markdown("<h2 style='text-align: center;'>🚙 RENTER ACCESS</h2>", unsafe_allow_html=True)
    with st.form("login_renter"):
        st.info("💡 Log in with your DriveElite credentials.")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        
        if st.form_submit_button("LOGIN TO SHOWROOM", use_container_width=True):
            user = pd.read_sql_query("SELECT * FROM platform_users WHERE username=? AND password=? AND role='RENTER'", conn, params=(u, p))
            if not user.empty:
                if user.iloc[0]['admin_status'] == 'APPROVED':
                    st.session_state.logged_in, st.session_state.username, st.session_state.role = True, u, 'RENTER'
                    st.rerun()
                else: 
                    st.warning("⏳ Your account is pending Admin approval.")
            else: 
                st.error("❌ Invalid credentials.")
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
    try:
        cat_df = pd.read_sql_query("SELECT name FROM vehicle_categories", conn)
        cat_list = ["All"] + [str(n).strip() for n in cat_df['name'].tolist()]
    except: cat_list = ["All", "Sedan", "SUV", "Van"]
    
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
                            t1 = st.time_input("Pickup Time", value=datetime.time(8, 0), key=f"t1_{car['id']}")
                            d2 = st.date_input("Return Date", min_value=d1, value=d1, key=f"d2_{car['id']}")
                            t2 = st.time_input("Return Time", value=datetime.time(18, 0), key=f"t2_{car['id']}")
                            
                            can_book = True
                            requested_days = set()
                            delta = d2 - d1
                            for j in range(delta.days + 1):
                                requested_days.add(d1 + datetime.timedelta(days=j))
                                
                            clashes = requested_days.intersection(unavailable_dates)
                            if clashes:
                                can_book = False
                                clash_str = ", ".join([d.strftime('%b %d') for d in sorted(list(clashes))])
                                st.error(f"🚨 This vehicle is booked on: **{clash_str}**")

                            drive_mode = st.radio("Mode", ["Self-Drive", "With Driver (+₱1k/day)"], key=f"dm_{car['id']}")
                            is_driver = 1 if "Driver" in drive_mode else 0
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
                                driver_fee = (driver_days * 1000.0) if is_driver else 0.0
                                d_fee, c_fee = ZONES[p_zone], ZONES[r_zone]
                                
                                tiers_df = pd.read_sql_query("SELECT min_days, discount_pct FROM discount_tiers ORDER BY min_days DESC", conn)
                                discount_pct = 0.0
                                for _, row in tiers_df.iterrows():
                                    if full_days >= row['min_days']:
                                        discount_pct = float(row['discount_pct'])
                                        break
                                        
                                try:
                                    settings_df = pd.read_sql_query("SELECT renter_markup_pct, affiliate_share_pct FROM platform_settings WHERE id = 1", conn)
                                    dynamic_renter_fee = float(settings_df.iloc[0]['renter_markup_pct'])
                                    dynamic_affiliate_share = float(settings_df.iloc[0]['affiliate_share_pct'])
                                except:
                                    dynamic_renter_fee, dynamic_affiliate_share = 0.00, 0.82
                                
                                savings = subtotal * discount_pct
                                discounted_subtotal = subtotal - savings
                                platform_fee = discounted_subtotal * dynamic_renter_fee  
                                grand_total = discounted_subtotal + platform_fee + driver_fee + d_fee + c_fee

                                st.markdown("#### 🧾 Cost Breakdown")
                                plural_days = "day" if full_days == 1 else "days"
                                rows = [f'<tr><td class="bill-label">Base Rental (₱{base_rate:,.2f} x {full_days} {plural_days})</td><td style="text-align:right; font-weight:bold;">₱{base_cost:,.2f}</td></tr>']
                                if billed_hrs > 0: rows.append(f'<tr><td style="color:#d35400;">Hourly Extension</td><td style="text-align:right; color:#d35400;">+₱{ext_fee:,.2f}</td></tr>')
                                if savings > 0: rows.append(f'<tr><td style="color:#cc0000;">Discount</td><td style="text-align:right; color:#cc0000;">-₱{savings:,.2f}</td></tr>')
                                rows.append(f'<tr><td style="color:#27ae60;">DriveElite Fee ({int(dynamic_renter_fee * 100)}%)</td><td style="text-align:right; color:#27ae60;">+₱{platform_fee:,.2f}</td></tr>')
                                if is_driver: rows.append(f'<tr><td style="color:#003399;">Driver Fee</td><td style="text-align:right; color:#003399;">+₱{driver_fee:,.2f}</td></tr>')
                                if d_fee > 0: rows.append(f'<tr><td style="color:#555;">Pickup Fee</td><td style="text-align:right; color:#555;">+₱{d_fee:,.2f}</td></tr>')
                                if c_fee > 0: rows.append(f'<tr><td style="color:#555;">Return Fee</td><td style="text-align:right; color:#555;">+₱{c_fee:,.2f}</td></tr>')

                                bill_html = f'<div class="bill-box"><table class="table-bill" style="width:100%;">{"".join(rows)}<tr style="border-top:2px solid #000;"><td class="bill-label" style="font-weight:900;">GRAND TOTAL</td><td style="text-align:right; font-weight:900; font-size:1.1em;">₱{grand_total:,.2f}</td></tr></table></div>'
                                st.markdown(bill_html, unsafe_allow_html=True)
                                
                                st.divider()

                                # --- NEW SMART BUTTON WITH PAYMONGO ---
                                if st.button("CONFIRM BOOKING & PAY", key=f"conf_{car['id']}", type="primary", use_container_width=True, disabled=not can_book):
                                    if dest and p_exact and r_exact and luzon_agree:
                                        with st.spinner("Generating secure checkout link..."):
                                            b_ref = str(random.randint(100000, 999999))
                                            p_dt_str, r_dt_str = f"{d1} {t1.strftime('%H:%M')}", f"{d2} {t2.strftime('%H:%M')}"
                                            
                                            # Save booking as 'PENDING'
                                            conn.execute("INSERT INTO bookings (renter_username, vehicle_id, pickup_time, return_time, amount, status, destination, pickup_loc, return_loc, with_driver, booking_ref) VALUES (?, ?, ?, ?, ?, 'PENDING', ?, ?, ?, ?, ?)", 
                                                         (renter_user, car['id'], p_dt_str, r_dt_str, grand_total, dest, f"{p_zone}: {p_exact}", f"{r_zone}: {r_exact}", is_driver, b_ref))
                                            conn.commit()
                                            
                                            # PayMongo API Call
                                            SECRET_KEY = 'sk_test_YOUR_ACTUAL_KEY_HERE'
                                            pay_amount = int(grand_total * 100) # Centavos
                                            
                                            auth_string = f"{SECRET_KEY}:"
                                            base64_auth = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
                                            
                                            url = "https://api.paymongo.com/v1/links"
                                            payload = {
                                                "data": {
                                                    "attributes": {
                                                        "amount": pay_amount, 
                                                        "description": f"DriveElite - {car['make']} {car['model']} (Ref: {b_ref})",
                                                        "remarks": f"Renter: {renter_user}"
                                                    }
                                                }
                                            }
                                            data = json.dumps(payload).encode('utf-8')
                                            req = urllib.request.Request(url, data=data)
                                            req.add_header('accept', 'application/json')
                                            req.add_header('content-type', 'application/json')
                                            req.add_header('authorization', f'Basic {base64_auth}')
                                            
                                            try:
                                                response = urllib.request.urlopen(req)
                                                response_data = json.loads(response.read().decode('utf-8'))
                                                checkout_url = response_data['data']['attributes']['checkout_url']
                                                
                                                st.success(f"✅ Booking Saved (Ref: #{b_ref})")
                                                st.markdown(f"### 💳 [👉 CLICK HERE TO PAY ₱{grand_total:,.2f} VIA PAYMONGO]({checkout_url})")
                                                st.info("Complete your payment using the link above to officially confirm your booking.")
                                            except urllib.error.URLError as e:
                                                st.error("Failed to generate payment link. Please contact admin.")
                                    else: 
                                        st.warning("⚠️ Please fill all required fields.")

# --- TAB 1: MY BOOKINGS ---
with tabs[1]:
    trip_tabs = st.tabs(["🚀 Active Trips", "📜 Trip History"])
    my_trips = pd.read_sql_query("SELECT b.*, v.make, v.model, v.plate, v.owner_username FROM bookings b JOIN vehicles v ON b.vehicle_id = v.id WHERE b.renter_username = ? ORDER BY b.pickup_time DESC", conn, params=(renter_user,))
    
    with trip_tabs[0]:
        active = my_trips[my_trips['status'].isin(['CONFIRMED', 'ONGOING', 'PENDING'])]
        if active.empty: st.info("No active trips.")
        for _, t in active.iterrows():
            with st.expander(f"🚗 {t['make']} {t['model']} ({t['plate']}) | {t['status']}"):
                st.write(f"**Ref:** #{t['booking_ref']} | **Total:** ₱{t['amount']:,.2f}")
                st.write(f"**Pickup:** {t['pickup_time']} | **Return:** {t['return_time']}")
                
                st.divider()
                st.markdown("#### 💬 Message the Owner")
                b_ref_str = str(t['booking_ref']) 
                
                chat_win = st.container(height=450, border=True)
                with chat_win:
                    try:
                        msgs = pd.read_sql_query("SELECT * FROM chat_messages WHERE booking_ref = ? ORDER BY timestamp ASC", conn, params=(b_ref_str,))
                        
                        if msgs.empty:
                            st.info("👋 Chat is empty. Say hello to start coordinating your trip!")
                        else:
                            for _, m in msgs.iterrows():
                                if m['sender_username'] == st.session_state.username:
                                    st.markdown(f'<div style="display: flex; justify-content: flex-end; margin-bottom: 5px;"><div style="background-color: #2c8c80; color: white; padding: 12px 16px; border-radius: 20px 20px 4px 20px; max-width: 75%;">{m["message_text"]}</div></div>', unsafe_allow_html=True)
                                else:
                                    st.markdown(f'<div style="display: flex; justify-content: flex-start; margin-bottom: 5px;"><div style="background-color: #2b2b2b; color: white; padding: 12px 16px; border-radius: 20px 20px 20px 4px; max-width: 75%;"><b>@{m["sender_username"]}</b><br>{m["message_text"]}</div></div>', unsafe_allow_html=True)
                    except: pass

                c_i, c_t = st.columns([1, 4])
                with c_i: r_img = st.file_uploader("📷", type=['jpg','png'], key=f"img_{b_ref_str}", label_visibility="collapsed")
                with c_t: st.text_input("Reply...", key=f"chat_{b_ref_str}", on_change=clear_renter_chat, args=(b_ref_str,))
                
                if st.button("Send Message", key=f"btn_{b_ref_str}", use_container_width=True) or st.session_state.get(f"trigger_send_{b_ref_str}", False):
                    box_val = st.session_state.get(f"chat_{b_ref_str}", "")
                    final_msg = st.session_state.temp_msg_renter if st.session_state.get(f"trigger_send_{b_ref_str}", False) else box_val
                    
                    if final_msg or r_img:
                        path = save_chat_image(r_img, b_ref_str) if r_img else ""
                        text_to_save = final_msg if final_msg else "📸 Sent a photo."
                        try:
                            conn.execute("INSERT INTO chat_messages (booking_ref, sender_username, receiver_username, message_text, image_path) VALUES (?, ?, ?, ?, ?)", (b_ref_str, renter_user, t['owner_username'], text_to_save, path))
                            conn.commit()
                            st.session_state.temp_msg_renter = ""
                            st.session_state[f"chat_{b_ref_str}"] = ""
                            st.session_state[f"trigger_send_{b_ref_str}"] = False
                            st.rerun()
                        except: pass

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
