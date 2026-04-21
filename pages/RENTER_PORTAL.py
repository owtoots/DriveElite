import streamlit as st
import pandas as pd
import datetime
import time
import random
import os
import smtplib
import math
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from database_utils import get_connection

# --- DATABASE CONNECTION & SELF-REPAIR ---
conn = get_connection()

# --- CHAT INPUT RESET LOGIC ---
if "temp_msg_renter" not in st.session_state:
    st.session_state.temp_msg_renter = ""

def trigger_send(b_ref):
    # Create the unique key name for this specific booking's chat box
    unique_key = f"chat_{b_ref}"
    if unique_key in st.session_state:
        st.session_state.temp_msg_renter = st.session_state[unique_key]
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

def send_booking_confirmation_email(to_email, renter_name, car_display, b_ref, p_dt, r_dt, html_bill):
    sender_email = "rdalbaojr@gmail.com" 
    try:
        app_password = st.secrets["email_app_password"]
    except KeyError:
        return False
        
    msg = MIMEMultipart("alternative")
    msg['Subject'] = f"DriveElite: Booking Confirmed (#{b_ref})"
    msg['From'] = f"DriveElite Reservations <{sender_email}>"
    msg['To'] = to_email
    
    html_body = f"""
    <html>
    <body style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #333; line-height: 1.6;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
            <h2 style="color: #2c8c80; text-align: center;">Booking Confirmed! 🚗</h2>
            <p>Hi <b>{renter_name}</b>,</p>
            <p>Your reservation for the <strong>{car_display}</strong> is officially locked in.</p>
            
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p style="margin: 5px 0;"><strong>Reference Number:</strong> #{b_ref}</p>
                <p style="margin: 5px 0;"><strong>Pickup:</strong> {p_dt}</p>
                <p style="margin: 5px 0;"><strong>Return:</strong> {r_dt}</p>
            </div>
            
            <h3 style="border-bottom: 2px solid #eee; padding-bottom: 5px;">Payment Summary</h3>
            {html_bill}
            
            <p style="margin-top: 30px; font-size: 0.9em; color: #555;">
                <i>Please prepare your payment and the refundable security deposit. The vehicle owner will contact you shortly via the DriveElite messenger to coordinate the handover.</i>
            </p>
        </div>
    </body>
    </html>
    """
    msg.attach(MIMEText(html_body, 'html'))
    
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, app_password)
            smtp.send_message(msg)
        return True
    except Exception:
        return False

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
    logo_col1, logo_col2, logo_col3 = st.columns([1, 2, 1])
    with logo_col2:
        try: st.image("logo.png", use_container_width=True)
        except: pass
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

# --- BROADCAST BANNER ---
try:
    query = "SELECT title, message, target FROM admin_promos WHERE active = 1 AND target IN ('ALL USERS', 'ALL', 'RENTER', 'RENTERS')"
    broadcasts = pd.read_sql_query(query, conn)
    
    if not broadcasts.empty:
        latest_b = broadcasts.iloc[-1]
        target_group = str(latest_b['target']).upper()
        
        if target_group in ['ALL USERS', 'ALL']:
            primary_color, gradient, glow_color = "#27ae60", "linear-gradient(135deg, #2ecc71 0%, #27ae60 100%)", "rgba(39, 174, 96, 0.7)"
        else:
            primary_color, gradient, glow_color = "#2980b9", "linear-gradient(135deg, #3498db 0%, #2980b9 100%)", "rgba(41, 128, 185, 0.7)"
            
        blink_css = f"""
        <style>
        @keyframes pulse_glow_renter {{
            0% {{ box-shadow: 0 0 0 0 {glow_color}; border-color: {primary_color}; }}
            70% {{ box-shadow: 0 0 15px 15px rgba(0,0,0,0); border-color: #ffffff; }}
            100% {{ box-shadow: 0 0 0 0 rgba(0,0,0,0); border-color: {primary_color}; }}
        }}
        .broadcast-banner-renter {{
            background: {gradient}; color: white; padding: 15px 20px; border-radius: 8px;
            border: 2px solid {primary_color}; text-align: center; margin-bottom: 25px;
            animation: pulse_glow_renter 2s infinite;
        }}
        .broadcast-title-renter {{ font-size: 1.3em; font-weight: 900; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 1px;}}
        .broadcast-msg-renter {{ font-size: 1.1em; font-weight: 500; }}
        </style>
        """
        st.markdown(blink_css + f"""<div class="broadcast-banner-renter"><div class="broadcast-title-renter">📢 ADMIN BROADCAST: {latest_b['title']} 📢</div><div class="broadcast-msg-renter">{latest_b['message']}</div></div>""", unsafe_allow_html=True)
except: pass

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
                            d1 = st.date_input("Pickup Date", min_value=datetime.date.today(), key=f"d1_{car['id']}")
                            t1 = st.time_input("Pickup Time", value=datetime.time(8, 0), key=f"t1_{car['id']}")
                            d2 = st.date_input("Return Date", min_value=d1, value=d1, key=f"d2_{car['id']}")
                            t2 = st.time_input("Return Time", value=datetime.time(18, 0), key=f"t2_{car['id']}")
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
                            if r_dt_obj <= p_dt_obj: st.error("⚠️ Return time must be after pickup.")
                            else:
                                full_days, billed_hrs, base_cost, ext_fee, subtotal = calculate_24h_rental(p_dt_obj, r_dt_obj, base_rate, 300.0, 59)
                                driver_days = full_days + (1 if billed_hrs > 0 else 0)
                                driver_fee = (driver_days * 1000.0) if is_driver else 0.0
                                d_fee, c_fee = ZONES[p_zone], ZONES[r_zone]
                                discount_pct = 0.15 if full_days >= 15 else (0.10 if full_days >= 7 else (0.05 if full_days >= 3 else 0.0))
                                savings = subtotal * discount_pct
                                grand_total = (subtotal - savings) + driver_fee + d_fee + c_fee

                                st.markdown("#### 🧾 Cost Breakdown")
                                plural_days = "day" if full_days == 1 else "days"
                                rows = [f'<tr><td class="bill-label">Base Rental (₱{base_rate:,.2f} x {full_days} {plural_days})</td><td style="text-align:right; font-weight:bold;">₱{base_cost:,.2f}</td></tr>']
                                if billed_hrs > 0: rows.append(f'<tr><td style="color:#d35400; font-style:italic;">Hourly Extension ({billed_hrs} hrs @ ₱300/hr)</td><td style="text-align:right; color:#d35400;">+₱{ext_fee:,.2f}</td></tr>')
                                if savings > 0: rows.append(f'<tr><td style="color:#cc0000; font-style:italic;">Discount ({int(discount_pct*100)}%)</td><td style="text-align:right; color:#cc0000;">-₱{savings:,.2f}</td></tr>')
                                if is_driver: rows.append(f'<tr><td style="color:#003399;">Driver Fee</td><td style="text-align:right; color:#003399;">+₱{driver_fee:,.2f}</td></tr>')
                                bill_html = f'<div class="bill-box"><table class="table-bill">{"".join(rows)}<tr style="border-top:2px solid #000;"><td class="bill-label">GRAND TOTAL</td><td style="text-align:right; font-weight:900;">₱{grand_total:,.2f}</td></tr></table></div>'
                                st.markdown(bill_html, unsafe_allow_html=True)
                                
                                st.divider()
                                qr_p = "gcash_qr.jpg" 
                                if os.path.exists(qr_p): st.image(qr_p, caption=f"Scan to Pay: ₱{grand_total:,.2f}", width=300)
                                ref_num = st.text_input("GCash Reference Number *", key=f"ref_{car['id']}")

                                if st.button("CONFIRM BOOKING", key=f"conf_{car['id']}", type="primary", use_container_width=True):
                                    if dest and ref_num and p_exact and r_exact and luzon_agree:
                                        b_ref = str(random.randint(100000, 999999))
                                        p_dt_str, r_dt_str = f"{d1} {t1.strftime('%H:%M')}", f"{d2} {t2.strftime('%H:%M')}"
                                        conn.execute("INSERT INTO bookings (renter_username, vehicle_id, pickup_time, return_time, amount, status, destination, pickup_loc, return_loc, with_driver, booking_ref) VALUES (?, ?, ?, ?, ?, 'CONFIRMED', ?, ?, ?, ?, ?)", (renter_user, car['id'], p_dt_str, r_dt_str, grand_total, dest, f"{p_zone}: {p_exact}", f"{r_zone}: {r_exact}", is_driver, b_ref))
                                        conn.commit()
                                        st.success(f"✅ Confirmed! Ref: #{b_ref}"); time.sleep(2); st.rerun()
                                    else: st.warning("⚠️ Fill all fields.")

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
                b_ref = t['booking_ref']
                chat_win = st.container(height=200, border=True)
                with chat_win:
                    try:
                        msgs = pd.read_sql_query("SELECT * FROM chat_messages WHERE booking_ref = ? ORDER BY timestamp ASC", conn, params=(b_ref,))
                        for _, m in msgs.iterrows():
                            role = "user" if m['sender_username'] == renter_user else "assistant"
                            with st.chat_message(role):
                                st.write(m['message_text'])
                                if m.get('image_path') and os.path.exists(m['image_path']): st.image(m['image_path'], width=200)
                    except: st.caption("No messages.")

               c_i, c_t = st.columns([1, 4])
                with c_i: 
                    r_img = st.file_uploader("📷", type=['jpg','png'], key=f"img_{b_ref}", label_visibility="collapsed")
                
                with c_t: 
                    st.text_input("Reply...", key=f"chat_{b_ref}", on_change=clear_renter_chat, args=(b_ref,), placeholder="Type and press Enter...")

                # COMBINE BOTH ACTIONS: Did they click the button, OR did the Enter key set off the trigger?
                btn_clicked = st.button("Send Message", key=f"btn_{b_ref}", use_container_width=True)
                enter_pressed = st.session_state.get(f"trigger_send_{b_ref}", False)

                if btn_clicked or enter_pressed:
                    # Get the message from either the Enter key memory OR the active text box
                    box_val = st.session_state.get(f"chat_{b_ref}", "")
                    final_msg = st.session_state.temp_msg_renter if enter_pressed else box_val
                    
                    if final_msg or r_img:
                        path = save_chat_image(r_img, b_ref) if r_img else ""
                        text_to_save = final_msg if final_msg else "📸 Sent a photo."
                        
                        # --- ANTI-LOCK SENDER BLOCK ---
                        success = False
                        error_msg = ""
                        for attempt in range(3):
                            try:
                                conn.execute("INSERT INTO chat_messages (booking_ref, sender_username, receiver_username, message_text, image_path) VALUES (?, ?, ?, ?, ?)", 
                                            (b_ref, renter_user, t['owner_username'], text_to_save, path))
                                conn.commit()
                                success = True
                                
                                # Wipe ALL memories and reset the trigger after successful save
                                st.session_state.temp_msg_renter = ""
                                st.session_state[f"chat_{b_ref}"] = ""
                                st.session_state[f"trigger_send_{b_ref}"] = False
                                break
                            except Exception as e:
                                error_msg = str(e)
                                if "locked" in error_msg.lower():
                                    time.sleep(0.5) 
                                else:
                                    break
                                    
                        if success:
                            st.rerun()
                        else:
                            st.warning(f"🚨 **DATABASE ERROR:** {error_msg}")
                            st.info("Please screenshot this yellow box so we can see the exact cause!")
                        # -------------------------------------

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
                                actual_stars = raw_stars + 1
                                conn.execute("UPDATE bookings SET rating = ?, review = ? WHERE id = ?", (actual_stars, r, t['id']))
                                conn.commit(); st.success("Submitted!"); time.sleep(1); st.rerun()
                else: st.success(f"**Rating:** {'⭐' * int(float(t['rating']))}")
