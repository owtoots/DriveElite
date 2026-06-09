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
from database_utils import get_connection, send_sms_alert, send_alert_email
import calendar
from datetime import timedelta

# ==========================================
# 1. PAGE CONFIG & LOGO (Must be first!)
# ==========================================
st.set_page_config(page_title="DriveElite Renter", layout="wide")
try:
    st.sidebar.image("logo.png", use_container_width=True)
except:
    pass

# ==========================================
# 💎 2. THE "CRYSTAL ELITE" CSS ENGINE
# ==========================================
st.markdown("""
<style>
/* =========================================
       📸 UNIFORM CAR IMAGES (PERFECT ALIGNMENT)
       ========================================= */
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stImage"] img {
        height: 200px !important;
        width: 100% !important;
        object-fit: cover !important;
        border-radius: 8px !important;
    }
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
        background-color: #1D4ED8  !important;
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
os.makedirs("/data/uploads/chat_images", exist_ok=True)

# --- FETCH DYNAMIC PLATFORM SETTINGS ---
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

def calculate_24h_rental(p_dt, r_dt, base_rate, hourly_penalty=300.0, grace_mins=59):
    delta = r_dt - p_dt
    total_hours = delta.total_seconds() / 3600.0
    full_days = int(total_hours // 24)
    remainder_hours = total_hours % 24
    billed_hrs = 0
    if remainder_hours > (grace_mins / 60.0):
        billed_hrs = math.ceil(remainder_hours)
    if full_days == 0 and billed_hrs > 0:
        full_days, billed_hrs = 1, 0
    base_cost = full_days * base_rate
    ext_fee = billed_hrs * hourly_penalty
    return full_days, billed_hrs, base_cost, ext_fee, base_cost + ext_fee

def clear_renter_chat(b_ref):
    """Clears the chat input box and stages the message to be sent."""
    if f"chat_{b_ref}" in st.session_state:
        st.session_state.temp_msg_renter = st.session_state[f"chat_{b_ref}"]
        st.session_state[f"chat_{b_ref}"] = ""
        st.session_state[f"trigger_send_{b_ref}"] = True

def save_chat_image(img_file, b_ref):
    """Saves an uploaded image from the chat to the server."""
    if img_file:
        path = f"/data/uploads/chat_images/{b_ref}_{img_file.name}"
        with open(path, "wb") as f:
            f.write(img_file.getbuffer())
        return path
    return ""

def send_alert_email(to_email, subject, body):
    """Sends system alerts using the Corporate DriveElite server."""
    sender_email = "contact@driveelite.ph" 
    sender_password = os.environ.get("EMAIL_PASSWORD") 
    
    if not sender_password: 
        return False
        
    try:
        msg = MIMEMultipart()
        msg['From'] = f"DriveElite Platform <{sender_email}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        # CONNECT TO DOTPH CORPORATE SERVER
        with smtplib.SMTP_SSL('mail.driveelite.ph', 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False
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
        st.session_state.clear()
        st.rerun()
st.divider()

# ==========================================
# 📢 STATIC BROADCAST BANNER
# ==========================================
try:
    promo_df = pd.read_sql_query("SELECT title, message FROM admin_promos WHERE active = 1 AND target IN ('RENTER', 'ALL USERS') LIMIT 1", conn)
    
    if not promo_df.empty:
        title = promo_df.iloc[0]['title']
        msg = promo_df.iloc[0]['message']
        
        st.markdown(f"""
            <style>
            .broadcast-box {{ 
                padding: 25px 20px; 
                background-color: #2563EB;
                color: white; 
                border-radius: 12px; 
                margin-bottom: 25px; 
                text-align: center; 
                font-size: 22px; 
                display: flex; 
                flex-direction: row;
                justify-content: center;
                align-items: center;
                flex-wrap: wrap; 
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.15);
            }}
            .broadcast-title {{
                font-weight: 900;
                margin-right: 12px;
                letter-spacing: 0.5px;
            }}
            </style>
            <div class="broadcast-box">
                <span class="broadcast-title">📢 {title}:</span> 
                <span>{msg}</span>
            </div>
        """, unsafe_allow_html=True)
except Exception: pass 

main_tabs = st.tabs(["🌟 VEHICLE SHOWROOM", "📅 MY BOOKINGS"])

# ==========================================
# 🚘 RENTER SHOWROOM (MAIN TAB 0)
# ==========================================
with main_tabs[0]:
    st.header("🚘 Available Fleet")

    available_cars = pd.read_sql_query("SELECT * FROM vehicles WHERE admin_status = 'APPROVED' AND booking_status = 'AVAILABLE'", conn)

    if available_cars.empty:
        st.info("Our fleet is currently fully booked. Please check back later!")
    else:
        if 'category' in available_cars.columns:
            categories = ["All"] + sorted(available_cars['category'].dropna().unique().tolist())
        elif 'type' in available_cars.columns:
            categories = ["All"] + sorted(available_cars['type'].dropna().unique().tolist())
        else:
            categories = ["All"]
            
        category_tabs = st.tabs(categories)
        
        for tab_index, cat in enumerate(categories):
            with category_tabs[tab_index]:
                
                if cat == "All":
                    category_cars = available_cars.copy()
                else:
                    filter_col = 'category' if 'category' in available_cars.columns else 'type'
                    category_cars = available_cars[available_cars[filter_col] == cat].copy()
                
                if category_cars.empty:
                    st.info("No vehicles available in this category right now.")
                else:
                    display_cars = category_cars.head(8).reset_index(drop=True)
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
                                
                                # --- MIDDLE: Details ---
                                base_rate = float(car.get('daily_rate') or car.get('approved_price') or 0.0)
                                st.markdown(f"#### {car['make']} {car['model']}\n**Year:** {car['year']}\n\n<h5 style='color: #2563EB;'>₱{base_rate:,.2f} / day</h5>", unsafe_allow_html=True)
                                
                                # --- BOTTOM: POPOVER CHECKOUT MANAGER ---
                                with st.popover(f"⚡ BOOK {car['model'].upper()} NOW", use_container_width=True):
                                    
                                    stage_key = f"chk_stage_{car['id']}_{cat}"
                                    ref_key = f"pend_ref_{car['id']}_{cat}"
                                    if stage_key not in st.session_state: st.session_state[stage_key] = 0
                                    
                                    unavailable_dates = get_booked_dates(car['id'], conn)
                                    
                                    # -------------------------------------------------------------
                                    # CHECKOUT STAGE 0: SELECT DATES & CONFIRM SOFT LOCK
                                    # -------------------------------------------------------------
                                    if st.session_state[stage_key] == 0:
                                        today = datetime.date.today()
                                        
                                        # 1. MOVED DATE PICKERS TO TOP
                                        d1 = st.date_input("Pickup Date", min_value=today, key=f"d1_{car['id']}_{cat}")
                                        t1 = st.time_input("Pickup Time", value=datetime.time(9, 0), key=f"t1_{car['id']}_{cat}", step=datetime.timedelta(hours=1))
                                        d2 = st.date_input("Return Date", min_value=d1, value=d1, key=f"d2_{car['id']}_{cat}")
                                        t2 = st.time_input("Return Time", value=datetime.time(9, 0), key=f"t2_{car['id']}_{cat}", step=datetime.timedelta(hours=1))

                                        # 2. BULLETPROOF FLAT HTML CALENDAR
                                        cal_year = d1.year
                                        cal_month = d1.month
                                        month_matrix = calendar.monthcalendar(cal_year, cal_month)
                                        month_name = calendar.month_name[cal_month]
                                        
                                        cal_html = f"<div style='background-color:#F8FAFC; border:1px solid #E2E8F0; border-radius:12px; padding:15px; margin-bottom:20px; margin-top:15px;'><h4 style='text-align:center; color:#0F172A; margin-top:0px; margin-bottom:10px; font-size:16px;'>{month_name} {cal_year} Availability</h4><table style='width:100%; border-collapse:separate; border-spacing:4px; text-align:center; font-size:13px;'><tr><th style='color:#64748B;'>Mo</th><th style='color:#64748B;'>Tu</th><th style='color:#64748B;'>We</th><th style='color:#64748B;'>Th</th><th style='color:#64748B;'>Fr</th><th style='color:#64748B;'>Sa</th><th style='color:#64748B;'>Su</th></tr>"
                                        
                                        for week in month_matrix:
                                            cal_html += "<tr>"
                                            for day in week:
                                                if day == 0:
                                                    cal_html += "<td></td>"
                                                else:
                                                    d_iter = datetime.date(cal_year, cal_month, day)
                                                    if d_iter in unavailable_dates:
                                                        cal_html += f"<td><div style='background-color:#FEE2E2; color:#EF4444; text-decoration:line-through; border-radius:6px; padding:6px 0; font-weight:bold;'>{day}</div></td>"
                                                    elif d_iter < today:
                                                        cal_html += f"<td><div style='color:#CBD5E1; padding:6px 0;'>{day}</div></td>"
                                                    else:
                                                        cal_html += f"<td><div style='background-color:#DCFCE7; color:#16A34A; border-radius:6px; padding:6px 0; font-weight:bold; border:1px solid #BBF7D0;'>{day}</div></td>"
                                            cal_html += "</tr>"
                                        cal_html += "</table></div>"
                                        
                                        st.markdown(cal_html, unsafe_allow_html=True)
                                        
                                        # 3. COLLISION DETECTION
                                        can_book = True
                                        requested_days = set([d1 + datetime.timedelta(days=j) for j in range((d2 - d1).days + 1)])
                                        clashes = requested_days.intersection(unavailable_dates)
                                        if clashes:
                                            can_book = False
                                            st.error(f"🚨 Vehicle booked on: {', '.join([d.strftime('%b %d') for d in sorted(list(clashes))])}")

                                        drive_mode = st.radio("Mode", ["Self-Drive", "With Driver (+₱1k/day)"], key=f"dm_{car['id']}_{cat}")
                                        dest = st.text_input("Destination", key=f"dest_{car['id']}_{cat}")
                                        luzon_agree = st.checkbox("I agree to LUZON ONLY travel.", key=f"luzon_{car['id']}_{cat}")
                                        ZONES = {"HQ: Pasig/Ortigas/BGC (Free)": 0.0, "Zone 1: Cubao/Sta. Mesa/Makati": 500.0, "Zone 2: Manila/QC/MOA": 1000.0, "Zone 3: Alabang/LP": 1500.0}
                                        p_zone = st.selectbox("Pickup Zone", list(ZONES.keys()), key=f"pz_{car['id']}_{cat}")
                                        p_exact = st.text_input("Pickup Address", key=f"pa_{car['id']}_{cat}")
                                        r_zone = st.selectbox("Return Zone", list(ZONES.keys()), key=f"rz_{car['id']}_{cat}")
                                        r_exact = st.text_input("Return Address", key=f"ra_{car['id']}_{cat}")

                                        p_dt_obj, r_dt_obj = datetime.datetime.combine(d1, t1), datetime.datetime.combine(d2, t2)
                                        if r_dt_obj <= p_dt_obj: 
                                            st.error("⚠️ Return time must be after pickup.")
                                            can_book = False
                                        else:
                                            try:
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

                                                st.markdown("#### 🧾 Cost Breakdown")
                                                plural = "day" if full_days == 1 else "days"
                                                
                                                rows = [f"<tr><td class='bill-label'>Base Rental (₱{base_rate:,.2f} x {full_days} {plural})</td><td style='text-align:right; font-weight:bold;'>₱{base_cost:,.2f}</td></tr>"]
                                                
                                                if billed_hrs > 0: 
                                                    rows.append(f"<tr><td style='color:#d35400;'>Hourly Extension</td><td style='text-align:right; color:#d35400;'>+₱{ext_fee:,.2f}</td></tr>")
                                                
                                                if savings > 0: 
                                                    rows.append(f"<tr><td style='color:#cc0000;'>Duration Discount ({int(discount_pct * 100)}%)</td><td style='text-align:right; color:#cc0000;'>-₱{savings:,.2f}</td></tr>")
                                                
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

                                            except Exception as e:
                                                st.error("Error calculating rate. Please verify your functions.")
                                                can_book = False

                                        st.warning("💳 **RFID POLICY:** You must load your own toll funds. Excess load is **not refunded**. Empty RFID penalty: **₱100 fine** + toll costs.")
                                        
                                        agree_to_rfid = st.checkbox("I agree to the RFID rules and ₱100 penalty.", key=f"rfid_agree_{car['id']}_{cat}")
                                        is_disabled = (not can_book) or (not agree_to_rfid)

                                        if st.button("1. CONFIRM BOOKING (SOFT LOCK)", key=f"conf_{car['id']}_{cat}", type="primary", use_container_width=True, disabled=is_disabled):
                                            if dest and p_exact and r_exact and luzon_agree:
                                                with st.spinner("Securing your dates..."):
                                                    b_ref = str(random.randint(100000, 999999))
                                                    p_dt_str, r_dt_str = p_dt_obj.strftime("%Y-%m-%d %H:%M"), r_dt_obj.strftime("%Y-%m-%d %H:%M")
                                                    is_drvr_int = 1 if "Driver" in drive_mode else 0
                                                    
                                                    if gateway_mode == "PAYMONGO":
                                                        conn.execute("INSERT INTO bookings (renter_username, vehicle_id, pickup_time, return_time, amount, status, destination, pickup_loc, return_loc, with_driver, booking_ref) VALUES (?, ?, ?, ?, ?, 'PENDING', ?, ?, ?, ?, ?)", 
                                                                     (renter_user, car['id'], p_dt_str, r_dt_str, grand_total, dest, f"{p_zone}: {p_exact}", f"{r_zone}: {r_exact}", is_drvr_int, b_ref))
                                                        conn.commit()
                                                        
                                                        try:
                                                            SECRET_KEY = os.environ.get("paymongo_active_key")
                                                            if not SECRET_KEY:
                                                                try:
                                                                    SECRET_KEY = st.secrets.get("paymongo_active_key")
                                                                except Exception:
                                                                    pass 
                                                            
                                                            if not SECRET_KEY:
                                                                st.error("🚨 Missing API Key: Please add 'paymongo_active_key' to your Render Environment Variables.")
                                                            else:
                                                                pay_amount = int(grand_total * 100)
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
                                                                
                                                        except urllib.error.HTTPError as e:
                                                            error_info = e.read().decode()
                                                            st.error(f"PayMongo Rejected the Request: {error_info}")
                                                        except Exception as e:
                                                            st.error(f"System Error generating link: {e}")
                                                    
                                                    else:
                                                        conn.execute("INSERT INTO bookings (renter_username, vehicle_id, pickup_time, return_time, amount, status, destination, pickup_loc, return_loc, with_driver, booking_ref) VALUES (?, ?, ?, ?, ?, 'PENDING', ?, ?, ?, ?, ?)", 
                                                                     (renter_user, car['id'], p_dt_str, r_dt_str, grand_total, dest, f"{p_zone}: {p_exact}", f"{r_zone}: {r_exact}", is_drvr_int, b_ref))
                                                        conn.commit()
                                                        st.session_state[stage_key] = 1
                                                        st.session_state[ref_key] = b_ref
                                                        st.rerun()

                                    # -------------------------------------------------------------
                                    # CHECKOUT STAGE 1: VALIDATE BPI PAYMENT 
                                    # -------------------------------------------------------------
                                    elif st.session_state[stage_key] == 1:
                                        b_ref = st.session_state[ref_key]
                                        st.success(f"✅ Dates Reserved! Your Reference Number is: **#{b_ref}**")
                                        
                                        with st.container(border=True):
                                            st.markdown("### 🏦 Manual Bank Transfer")
                                            st.write("**Bank:** BPI")
                                            st.write("**Account Name:** Romeo Albao Jr.")
                                            st.write("**Account Number:** 1234-5678-90")
                                            
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
                                            receipt_file = st.file_uploader("Upload Receipt", type=['jpg', 'png', 'jpeg'], key=f"rec_{car['id']}_{cat}")
                                            
                                            c_back, c_val = st.columns([1, 2])
                                            if c_back.button("Cancel Booking", key=f"canc_{car['id']}_{cat}", use_container_width=True):
                                                conn.execute("DELETE FROM bookings WHERE booking_ref = ?", (b_ref,)); conn.commit()
                                                st.session_state[stage_key] = 0
                                                del st.session_state[ref_key]
                                                st.rerun()
                                            
                                            if c_val.button("2. VALIDATE PAYMENT SENT", type="primary", use_container_width=True, key=f"val_{car['id']}_{cat}"):
                                                if receipt_file:
                                                    receipt_bytes = receipt_file.read()
                                                    with st.spinner("Transmitting to Admin..."):
                                                        conn.execute("UPDATE bookings SET receipt_img = ?, status = 'VERIFYING' WHERE booking_ref = ?", (receipt_bytes, b_ref))
                                                        
                                                        receipt_path = f"/data/uploads/chat_images/receipt_{b_ref}.jpg"
                                                        with open(receipt_path, "wb") as f: f.write(receipt_bytes)
                                                        
                                                        owner_username = pd.read_sql_query("SELECT owner_username FROM vehicles WHERE id=?", conn, params=(car['id'],)).iloc[0]['owner_username']
                                                        conn.execute("INSERT INTO chat_messages (booking_ref, sender_username, receiver_username, message_text, image_path) VALUES (?, ?, ?, ?, ?)", 
                                                                     (b_ref, renter_user, owner_username, "Payment Receipt Uploaded for Admin Verification.", receipt_path))
                                                        conn.commit()
                                                        
                                                        # ==========================================
                                                        # 🚨 SEND AUTOMATED EMAIL ALERTS
                                                        # ==========================================
                                                        try:
                                                            aff_data = pd.read_sql_query("SELECT email, full_name FROM platform_users WHERE username=?", conn, params=(owner_username,))
                                                            if not aff_data.empty:
                                                                affiliate_email = aff_data.iloc[0]['email']
                                                                affiliate_name = aff_data.iloc[0]['full_name']
                                                                
                                                                # 1. Email to Admin
                                                                admin_email = "contact@driveelite.ph" 
                                                                send_alert_email(
                                                                    to_email=admin_email,
                                                                    subject=f"💳 ACTION REQUIRED: Payment Verification for #{b_ref}",
                                                                    body=f"Renter @{renter_user} has booked a {car['make']} {car['model']} and uploaded a manual payment receipt.\n\nPlease log into the Admin Command Center to verify the BPI payment and confirm the booking."
                                                                )
                                                                
                                                                # 2. Email to Affiliate
                                                                send_alert_email(
                                                                    to_email=affiliate_email,
                                                                    subject=f"🚗 DriveElite: New Booking Verifying (#{b_ref})",
                                                                    body=f"Hello {affiliate_name},\n\nA renter has booked your {car['make']} {car['model']} and submitted their payment.\n\nAdmin is currently verifying the receipt. Once confirmed, this will appear in your Logistics tab!"
                                                                )
                                                        except Exception as e:
                                                            pass
                                                        
                                                        st.toast("✅ Receipt Sent to Admin!")
                                                        st.session_state[stage_key] = 0
                                                        del st.session_state[ref_key]
                                                        time.sleep(2)
                                                        st.rerun()
                                                else:
                                                    st.error("🚨 Please upload a screenshot of your receipt.")

# ==========================================
# 📅 MY BOOKINGS (MAIN TAB 1)
# ==========================================
with main_tabs[1]:
    st.header("📅 My Booking History")
    
    try:
        # Fetch all bookings for this specific renter
        my_bookings = pd.read_sql_query("""
            SELECT b.*, v.make, v.model, v.plate, v.owner_username
            FROM bookings b
            JOIN vehicles v ON b.vehicle_id = v.id
            WHERE b.renter_username = ?
            ORDER BY b.id DESC
        """, conn, params=(renter_user,))
        
        if my_bookings.empty:
            st.info("You haven't made any bookings yet. Head over to the Vehicle Showroom to start your journey!")
        else:
            for _, b in my_bookings.iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"#### {b['make']} {b['model']} ({b['plate']})")
                        b_ref = b.get('booking_ref') if pd.notnull(b.get('booking_ref')) else f"DRV-{b['id']:05d}"
                        st.caption(f"Ref: #{b_ref} | Dates: {str(b['pickup_time'])[:10]} to {str(b['return_time'])[:10]}")
                    
                    with c2:
                        if b['status'] == 'COMPLETED': st.success("COMPLETED")
                        elif b['status'] == 'ONGOING': st.warning("ONGOING")
                        elif b['status'] == 'VERIFYING': st.info("VERIFYING PAYMENT")
                        else: st.info(b['status'])

                    # --- CHAT SYSTEM (For Active Trips) ---
                    if b['status'] in ['PENDING', 'VERIFYING', 'CONFIRMED', 'ONGOING']:
                        st.divider()
                        st.markdown("#### 💬 Message the Host")
                        b_ref_str = str(b['booking_ref'])
                        
                        chat_win = st.container(height=300, border=True)
                        with chat_win:
                            try:
                                msgs = pd.read_sql_query("SELECT * FROM chat_messages WHERE booking_ref = ? ORDER BY timestamp ASC", conn, params=(b_ref_str,))
                                if msgs.empty:
                                    st.info("👋 Chat is empty. Say hello to your host to coordinate the handover!")
                                else:
                                    for _, m in msgs.iterrows():
                                        if m['sender_username'] == renter_user:
                                            st.markdown(f"""
                                            <div style="display: flex; justify-content: flex-end; margin-bottom: 5px;">
                                                <div style="background-color: #2563EB; color: white; padding: 12px 16px; border-radius: 20px 20px 4px 20px; max-width: 75%; box-shadow: 1px 2px 5px rgba(0,0,0,0.2);">
                                                    {m['message_text']}
                                                </div>
                                            </div>
                                            """, unsafe_allow_html=True)
                                            if m.get('image_path') and os.path.exists(m['image_path']): 
                                                c_space, c_img = st.columns([2, 1])
                                                with c_img: st.image(m['image_path'], use_container_width=True)
                                        else:
                                            st.markdown(f"""
                                            <div style="display: flex; justify-content: flex-start; margin-bottom: 5px;">
                                                <div style="background-color: #2b2b2b; color: white; padding: 12px 16px; border-radius: 20px 20px 20px 4px; max-width: 75%; border: 1px solid #444; box-shadow: 1px 2px 5px rgba(0,0,0,0.2);">
                                                    <div class="sender-tag" style="color: #cbd5e1; font-size: 0.8em; margin-bottom: 4px;">@{m['sender_username']} (Host)</div>
                                                    {m['message_text']}
                                                </div>
                                            </div>
                                            """, unsafe_allow_html=True)
                                            if m.get('image_path') and os.path.exists(m['image_path']): 
                                                c_img, c_space = st.columns([1, 2])
                                                with c_img: st.image(m['image_path'], use_container_width=True)
                            except Exception as e:
                                st.error("Could not load chat.")

                        c_img, c_msg = st.columns([1, 4])
                        with c_img: 
                            r_img = st.file_uploader("📷", type=['jpg','png','jpeg'], key=f"r_img_{b_ref_str}", label_visibility="collapsed")
                        with c_msg: 
                            st.text_input("Reply...", key=f"chat_{b_ref_str}", on_change=clear_renter_chat, args=(b_ref_str,), placeholder="Type message and press Enter...")

                        btn_clicked = st.button("Send", key=f"r_btn_{b_ref_str}", use_container_width=True)
                        enter_pressed = st.session_state.get(f"trigger_send_{b_ref_str}", False)

                        if btn_clicked or enter_pressed:
                            box_val = st.session_state.get(f"chat_{b_ref_str}", "")
                            final_text = st.session_state.temp_msg_renter if enter_pressed else box_val
                            
                            has_text = bool(final_text.strip())
                            has_img = bool(r_img)
                            
                            if has_text or has_img:
                                img_path = save_chat_image(r_img, b_ref_str) if has_img else ""
                                text_to_save = final_text if has_text else "📸 Sent a photo."
                                
                                conn.execute("INSERT INTO chat_messages (booking_ref, sender_username, receiver_username, message_text, image_path) VALUES (?, ?, ?, ?, ?)", 
                                            (b_ref_str, renter_user, b['owner_username'], text_to_save, img_path))
                                conn.commit()
                                st.session_state.temp_msg_renter = ""
                                st.session_state[f"chat_{b_ref_str}"] = ""
                                st.session_state[f"trigger_send_{b_ref_str}"] = False
                                st.rerun()

                    # --- THE REVIEW SYSTEM ---
                    if b['status'] == 'COMPLETED':
                        st.divider()
                        if pd.isna(b['rating']) or b['rating'] == "" or b['rating'] == 0:
                            with st.expander("⭐ Leave a Review for this Trip!", expanded=True):
                                
                                st.write("**Rate your experience:**")
                                # Native interactive stars (returns 0 for 1 star, 4 for 5 stars)
                                star_click = st.feedback("stars", key=f"stars_{b['id']}")
                                
                                new_review = st.text_area("Share your thoughts about the vehicle and host...", key=f"rev_text_{b['id']}")
                                
                                if st.button("Submit Review", type="primary", key=f"sub_rev_{b['id']}"):
                                    if star_click is None:
                                        st.error("🚨 Please click on the stars to leave a rating!")
                                    else:
                                        final_rating = star_click + 1  # Converts 0-4 math to a 1-5 scale
                                        conn.execute("UPDATE bookings SET rating = ?, review = ? WHERE id = ?", (final_rating, new_review, b['id']))
                                        conn.commit()
                                        st.success("Thank you! Your review has been published.")
                                        time.sleep(1.5)
                                        st.rerun()
                        else:
                            stars = int(float(b['rating'])) * '⭐'
                            st.markdown(f"**Your Rating:** {stars}")
                            if pd.notna(b['review']) and str(b['review']).strip():
                                st.info(f"💬 \"{b['review']}\"")
                                
    except Exception as e:
        st.error(f"Could not load bookings: {e}")
