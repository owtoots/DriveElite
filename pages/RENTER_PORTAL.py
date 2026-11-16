import streamlit as st
import pandas as pd
import datetime
import time
import random
import os
import sys
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
from streamlit_autorefresh import st_autorefresh
from database_utils import get_connection, init_db, patch_database

def main():
    # ==========================================
    # 1. PAGE CONFIG & LOGO
    # ==========================================
    st.set_page_config(page_title="DriveElite Renter", layout="wide", initial_sidebar_state="expanded")
    
    # 🚨 SMART LOGO PATH: Automatically finds the logo even from inside the pages/ folder
    logo_path = "logo.png"
    if not os.path.exists(logo_path):
        logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logo.png")
        
    try:
        st.sidebar.image(logo_path, width=140)
    except:
        st.sidebar.markdown("## DriveElite")

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
        
        /* --- GLOBAL THEME & TYPOGRAPHY --- */
        [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: #F8FAFC !important;
            color: #0F172A !important;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
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
            order: 1 !important; /* Forces Logo to the Top */
            padding-top: 2rem !important;
            padding-bottom: 1.5rem !important; /* Gap below logo */
            margin-top: 0 !important;
        }
        [data-testid="stSidebarNav"] {
            order: 2 !important; /* Forces Menu below Logo */
            padding-top: 1rem !important; /* Gap above menu */
        }

        /* --- CARDS & PANELS --- */
        [data-testid="stForm"], .stForm, div[data-testid="stExpander"], div.stMetric {
            background-color: #FFFFFF !important;
            padding: 20px !important;
            border-radius: 16px !important;
            border: 1px solid #E2E8F0 !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
        }

        /* 🚨 FRESH GREEN DASHBOARD BUTTONS (Aggressive form selector) */
        div.stButton > button, 
        [data-testid="stFormSubmitButton"] button,
        [data-testid="stPopover"] button {
            background-color: #22C55E !important;
            color: #FFFFFF !important;
            border: none !important;
            font-family: 'Segoe UI', Arial, sans-serif !important;
            font-size: 14px !important;  
            font-weight: 500 !important; 
            border-radius: 8px !important;
            padding: 10px 20px !important; 
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
            transition: all 0.2s ease !important;
            box-shadow: 0 4px 6px rgba(34, 197, 94, 0.2) !important;
            -webkit-text-fill-color: #FFFFFF !important;
        }
        
        div.stButton > button p, 
        [data-testid="stFormSubmitButton"] button p,
        [data-testid="stPopover"] button p {
            color: #FFFFFF !important;
            font-family: 'Segoe UI', Arial, sans-serif !important;
            font-size: 14px !important;  
            font-weight: 500 !important; 
            -webkit-text-fill-color: #FFFFFF !important;
        }

        /* Ensure the little popover dropdown arrow turns white */
        [data-testid="stPopover"] button svg {
            fill: #FFFFFF !important;
            color: #FFFFFF !important;
        }

        div.stButton > button:hover, 
        [data-testid="stFormSubmitButton"] button:hover,
        [data-testid="stPopover"] button:hover {
            background-color: #16A34A !important;
            box-shadow: 0 6px 12px rgba(34, 197, 94, 0.3) !important;
            transform: translateY(-2px) !important;
        }
        
        div.stButton > button:active, 
        [data-testid="stFormSubmitButton"] button:active,
        [data-testid="stPopover"] button:active {
            background-color: #15803D !important;
            transform: translateY(0px) !important;
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
        
        /* 🚨 MAKE MOBILE MENU ARROW MASSIVE AND GREEN */
        [data-testid="collapsedControl"] {
            position: fixed !important;  
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            background-color: #22C55E !important;
            border-radius: 50% !important;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3) !important;
            top: 15px !important;
            left: 15px !important;
            padding: 8px !important;
            z-index: 999999 !important;
            transition: transform 0.2s ease !important;
        }
        
        [data-testid="collapsedControl"] svg {
            fill: #FFFFFF !important;
            color: #FFFFFF !important;
            width: 24px !important;
            height: 24px !important;
        }
    </style>
    """, unsafe_allow_html=True)
   
    # ==========================================
    # 3. DATABASE CONNECTION & SETUP
    # ==========================================
    conn = get_connection()

    def patch_database_tables():
        try: conn.execute("CREATE TABLE IF NOT EXISTS admin_promos (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, message TEXT, target TEXT DEFAULT 'ALL USERS', active INTEGER DEFAULT 1)"); conn.commit()
        except: pass
        try: conn.execute("ALTER TABLE vehicles ADD COLUMN location TEXT DEFAULT 'Metro Manila'"); conn.commit()
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
        query = "SELECT pickup_time, return_time FROM bookings WHERE vehicle_id = ? AND status IN ('CONFIRMED', 'ONGOING', 'PENDING', 'APPROVED_BY_HOST')"
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
        
    def get_dynamic_delivery_fee(total_km):
        """
        Calculates dynamic delivery/return fee based on distance, 
        factoring in fuel/driver effort plus the driver's return taxi/Grab fare + ₱20 buffer.
        """
        try:
            if total_km <= 5.0:
                return 350.0
            
            base_taxi_fare = 150.0
            fuel_and_time_rate = 50.0
            driver_buffer = 20.0
            
            # Estimated return taxi fare back to owner's parking base
            return_taxi_estimate = total_km * 45.0 
            
            calculated_fee = base_taxi_fare + (total_km * fuel_and_time_rate) + return_taxi_estimate + driver_buffer
            return round(calculated_fee, -2) # Round to nearest hundred for clean pricing
        except Exception:
            return 800.0

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
                user = pd.read_sql_query("SELECT * FROM platform_users WHERE username=? AND password=? AND admin_status='APPROVED'", conn, params=(u, p))
                if not user.empty:
                    st.session_state.logged_in, st.session_state.username, st.session_state.role = True, u, 'RENTER'
                    st.rerun()
                else: 
                    st.error("❌ Invalid credentials or account pending Admin approval.")
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

        available_cars = pd.read_sql_query("""
            SELECT v.*, u.full_name as owner_name 
            FROM vehicles v 
            JOIN platform_users u ON v.owner_username = u.username 
            WHERE v.admin_status = 'APPROVED' AND v.booking_status = 'AVAILABLE'
        """, conn)

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
                                    
                                    # --- TOP: Robust Image Resolver ---
                                    img_p = car.get('vehicle_img')
                                    resolved_img_path = None
                                    
                                    if img_p:
                                        if os.path.exists(img_p):
                                            resolved_img_path = img_p
                                        else:
                                            filename = os.path.basename(img_p)
                                            alt_path = os.path.join(os.getcwd(), "data", "uploads", filename)
                                            if os.path.exists(alt_path):
                                                resolved_img_path = alt_path
                                            else:
                                                alt_path2 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "uploads", filename)
                                                if os.path.exists(alt_path2):
                                                    resolved_img_path = alt_path2

                                    if resolved_img_path:
                                        st.image(resolved_img_path, use_container_width=True)
                                    else:
                                        st.image("https://placehold.co/600x400?text=Vehicle+Image", use_container_width=True)
                                    
                                    # --- MIDDLE: Details ---
                                    base_rate = float(car.get('daily_rate') or car.get('approved_price') or 0.0)
                                    st.markdown(f"#### {car['make']} {car['model']}\n**Year:** {car['year']}", unsafe_allow_html=True)
                                    
                                    parking_location = car.get('location', 'Metro Manila')
                                    owner_display = car.get('owner_name', 'Verified Affiliate')
                                    st.caption(f"📍 Parking Base: **{parking_location}** (Host: {owner_display})")
                                    
                                    # --- CLICKABLE REPUTATION CARD ---
                                    rating_data = conn.execute("""
                                        SELECT AVG(rating), COUNT(rating) 
                                        FROM bookings 
                                        WHERE vehicle_id = ? AND rating IS NOT NULL AND status = 'COMPLETED'
                                    """, (car['id'],)).fetchone()
                                    
                                    avg_rating = rating_data[0] if rating_data[0] is not None else 0
                                    review_count = rating_data[1] if rating_data[1] is not None else 0
                                    
                                    if avg_rating > 0:
                                        stars = '⭐' * int(round(avg_rating))
                                        with st.popover(f"{stars} ({avg_rating:.1f}) - {review_count} Reviews", use_container_width=True):
                                            st.write(f"### 📋 Feedback for this {car['make']} {car['model']}")
                                            
                                            reviews = pd.read_sql_query("""
                                                SELECT b.review, b.rating, r.full_name as renter_name 
                                                FROM bookings b 
                                                JOIN platform_users r ON b.renter_username = r.username 
                                                WHERE b.vehicle_id = ? AND b.review IS NOT NULL AND b.review != ''
                                                ORDER BY b.id DESC LIMIT 10
                                            """, conn, params=(car['id'],))
                                            
                                            if not reviews.empty:
                                                for _, rev in reviews.iterrows():
                                                    color = "green" if rev['rating'] >= 4 else "orange"
                                                    st.markdown(f"**{rev['renter_name']}** rated it :{color}[{'⭐'*int(rev['rating'])}]")
                                                    st.caption(f"_{rev['review']}_")
                                                    st.divider()
                                            else:
                                                st.write("No written reviews yet.")
                                    else:
                                        st.markdown("*No ratings yet*")
                                    
                                    st.markdown(f"<h5 style='color: #2563EB;'>₱{base_rate:,.2f} / day</h5>", unsafe_allow_html=True)
                                    
                                    # --- BOTTOM: POPOVER CHECKOUT MANAGER ---
                                    with st.popover(f"⚡ BOOK {car['model'].upper()} NOW", use_container_width=True):
                                        
                                        stage_key = f"chk_stage_{car['id']}_{cat}"
                                        ref_key = f"pend_ref_{car['id']}_{cat}"
                                        if stage_key not in st.session_state: st.session_state[stage_key] = 0
                                        
                                        unavailable_dates = get_booked_dates(car['id'], conn)
                                        
                                        # -------------------------------------------------------------
                                        # CHECKOUT STAGE 0: SELECT DATES & EXACT ADDRESSES
                                        # -------------------------------------------------------------
                                        if st.session_state[stage_key] == 0:
                                            today = datetime.date.today()
                                            
                                            d1 = st.date_input("Pickup Date", min_value=today, key=f"d1_{car['id']}_{cat}")
                                            t1 = st.time_input("Pickup Time", value=datetime.time(9, 0), key=f"t1_{car['id']}_{cat}", step=datetime.timedelta(hours=1))
                                            d2 = st.date_input("Return Date", min_value=d1, value=d1, key=f"d2_{car['id']}_{cat}")
                                            t2 = st.time_input("Return Time", value=datetime.time(9, 0), key=f"t2_{car['id']}_{cat}", step=datetime.timedelta(hours=1))

                                            # BULLETPROOF FLAT HTML CALENDAR
                                            cal_year = d1.year
                                            cal_month = d1.month
                                            month_matrix = calendar.monthcalendar(cal_year, cal_month)
                                            month_name = calendar.month_name[cal_month]

                                            cal_html = f"""
                                            <style>
                                                .booked-date {{ background-color: #FEE2E2; color: #94A3B8; text-decoration: line-through; border-radius: 6px; padding: 6px 0; font-weight: bold; cursor: not-allowed; }}
                                                .available-date {{ background-color: #DCFCE7; color: #16A34A; border-radius: 6px; padding: 6px 0; font-weight: bold; border: 1px solid #BBF7D0; }}
                                                .past-date {{ color: #CBD5E1; padding: 6px 0; }}
                                            </style>
                                            <div style='background-color:#F8FAFC; border:1px solid #E2E8F0; border-radius:12px; padding:15px; margin-bottom:20px; margin-top:15px;'>
                                                <h4 style='text-align:center; color:#0F172A; margin-top:0px; margin-bottom:10px; font-size:16px;'>{month_name} {cal_year} Availability</h4>
                                                <table style='width:100%; border-collapse:separate; border-spacing:4px; text-align:center; font-size:13px;'>
                                                <tr><th style='color:#64748B;'>Mo</th><th style='color:#64748B;'>Tu</th><th style='color:#64748B;'>We</th><th style='color:#64748B;'>Th</th><th style='color:#64748B;'>Fr</th><th style='color:#64748B;'>Sa</th><th style='color:#64748B;'>Su</th></tr>
                                            """

                                            for week in month_matrix:
                                                cal_html += "<tr>"
                                                for day in week:
                                                    if day == 0:
                                                        cal_html += "<td></td>"
                                                    else:
                                                        d_iter = datetime.date(cal_year, cal_month, day)
                                                        if d_iter in unavailable_dates:
                                                            cal_html += f"<td><div class='booked-date'>{day}</div></td>"
                                                        elif d_iter < today:
                                                            cal_html += f"<td><div class='past-date'>{day}</div></td>"
                                                        else:
                                                            cal_html += f"<td><div class='available-date'>{day}</div></td>"
                                                cal_html += "</tr>"
                                            cal_html += "</table></div>"

                                            st.markdown(cal_html, unsafe_allow_html=True)
                                            
                                            # COLLISION DETECTION
                                            can_book = True
                                            requested_days = set([d1 + datetime.timedelta(days=j) for j in range((d2 - d1).days + 1)])
                                            clashes = requested_days.intersection(unavailable_dates)
                                            if clashes:
                                                can_book = False
                                                st.error(f"⚠️ Vehicle booked on: {', '.join([d.strftime('%b %d') for d in sorted(list(clashes))])}")

                                            drive_mode = st.radio("Mode", ["Self-Drive", "With Driver (+₱1k/day)"], key=f"dm_{car['id']}_{cat}")
                                            dest = st.text_input("Destination", key=f"dest_{car['id']}_{cat}")
                                            luzon_agree = st.checkbox("I agree to regional & nationwide travel rules.", key=f"luzon_{car['id']}_{cat}")
                                            
                                            # 📍 Specific Address Input Fields with Unique Keys per Car & Category Tab
                                            car_id = car.get('id', 'car')
                                            st.caption(f"🚗 Logistics calculated starting from host parking: **{parking_location}**")
                                            
                                            p_exact = st.text_input(
                                                "Specific Pickup Address", 
                                                placeholder="e.g., Silay Airport, Bacolod or Session Road, Baguio",
                                                key=f"pickup_addr_{car_id}_{cat}"
                                            )
                                            r_exact = st.text_input(
                                                "Specific Return Address", 
                                                placeholder="e.g., BGC High Street, Taguig or Downtown Bacolod",
                                                key=f"return_addr_{car_id}_{cat}"
                                            )

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
                                                    
                                                    # 🚚 SMART ZONAL DISTANCE CALCULATOR (Landmark & City Aware)
                                                    def get_zone_distance(address):
                                                        """Intelligently recognizes specific landmarks, malls, and terminals and maps them to accurate distances."""
                                                        addr = str(address).lower() if address else ""
                                                        
                                                        if any(k in addr for k in ["estancia", "capitol commons", "kapitolyo", "ortigas", "megamall", "shang", "tiendesitas", "pasig"]):
                                                            return 3.0
                                                        elif any(k in addr for k in ["terminal 3", "t3", "terminal 1", "t1", "terminal 2", "t2", "terminal 4", "t4", "naia", "airport", "pasay", "moa", "mall of asia", "solaire", "okada", "bay area", "villamor", "silay"]):
                                                            return 12.5
                                                        elif any(k in addr for k in ["bgc", "bonifacio", "taguig", "market market", "high street"]):
                                                            return 6.0
                                                        elif any(k in addr for k in ["makati", "ayala", "rockwell", "legaspi", "salcedo"]):
                                                            return 8.0
                                                        elif any(k in addr for k in ["quezon city", "qc", "cubao", "timog", "trinoma", "sm north", "greenhills"]):
                                                            return 15.0
                                                        elif any(k in addr for k in ["antipolo", "rizal", "cainta", "taytay", "baguio", "session road"]):
                                                            return 18.0
                                                        elif any(k in addr for k in ["bulacan", "malolos", "meycauayan", "marilao", "san jose del monte", "sjdm", "bacolod"]):
                                                            return 25.0
                                                        elif any(k in addr for k in ["cavite", "tagaytay", "laguna", "nuvali", "batangas", "pampanga", "clark", "cebu", "davao"]):
                                                            return 55.0
                                                        return 15.0 # Default fallback distance
        
                                                    # Leg 1: Owner Parking to Pickup
                                                    outbound_km = get_zone_distance(p_exact)
                                                    delivery_fee = get_dynamic_delivery_fee(outbound_km)
        
                                                    # Leg 2: Return to Owner Parking
                                                    return_km = get_zone_distance(r_exact)
                                                    return_fee = get_dynamic_delivery_fee(return_km)
                                                    
                                                    total_logistics_fee = delivery_fee + return_fee
                                                    grand_total = discounted_subtotal + platform_fee + driver_fee + total_logistics_fee
        
                                                    st.markdown("#### 🧾 Cost Breakdown (Estimated)")
                                                    plural = "day" if full_days == 1 else "days"
                                                    
                                                    rows = [f"<tr><td class='bill-label'>Base Rental (₱{base_rate:,.2f} x {full_days} {plural})</td><td style='text-align:right; font-weight:bold;'>₱{base_cost:,.2f}</td></tr>"]
                                                    
                                                    if billed_hrs > 0: 
                                                        rows.append(f"<tr><td style='color:#d35400;'>Hourly Extension</td><td style='text-align:right; color:#d35400;'>+₱{ext_fee:,.2f}</td></tr>")
                                                    
                                                    if savings > 0: 
                                                        rows.append(f"<tr><td style='color:#cc0000;'>Duration Discount ({int(discount_pct * 100)}%)</td><td style='text-align:right; color:#cc0000;'>-₱{savings:,.2f}</td></tr>")
                                                    
                                                    rows.append(f"<tr><td style='padding: 8px; color: #16A34A;'>{operator_name} Fee ({int(applied_renter_fee * 100)}%)</td><td style='text-align:right; color:#27ae60;'>+₱{platform_fee:,.2f}</td></tr>")
                                                    
                                                    if "Driver" in drive_mode: 
                                                        rows.append(f"<tr><td style='color:#003399;'>Driver Fee</td><td style='text-align:right; color:#003399;'>+₱{driver_fee:,.2f}</td></tr>")
                                                        
                                                    rows.append(f"<tr><td style='color:#555;'>Delivery Fee (From Base: {outbound_km} km)</td><td style='text-align:right; color:#555;'>+₱{delivery_fee:,.2f}</td></tr>")
                                                    rows.append(f"<tr><td style='color:#555;'>Return Fee (To Base: {return_km} km)</td><td style='text-align:right; color:#555;'>+₱{return_fee:,.2f}</td></tr>")
                                                    
                                                    bill_html = f"<div class='bill-box'><table class='table-bill' style='width:100%;'>{''.join(rows)}<tr style='border-top:2px solid #000;'><td class='bill-label' style='font-weight:900;'>ESTIMATED TOTAL</td><td style='text-align:right; font-weight:900; font-size:1.1em;'>₱{grand_total:,.2f}</td></tr></table></div>"
                                                    
                                                    st.markdown(bill_html, unsafe_allow_html=True)
                                                    st.divider()
        
                                                except Exception as e:
                                                    st.error(f"Error calculating rate: {e}")
                                                    can_book = False
        
                                            st.warning("💳 **RFID POLICY:** You must load your own toll funds. Excess load is **not refunded**. Empty RFID penalty: **₱100 fine** + toll costs.")
                                            
                                            agree_to_rfid = st.checkbox("I agree to the RFID rules and ₱100 penalty.", key=f"rfid_agree_{car['id']}_{cat}")
                                            is_disabled = (not can_book) or (not agree_to_rfid)

                                            if st.button("1. REQUEST BOOKING & SUBMIT FOR HOST APPROVAL", key=f"conf_{car['id']}_{cat}", type="primary", use_container_width=True, disabled=is_disabled):
                                                p_dt_str = p_dt_obj.strftime("%Y-%m-%d %H:%M")
                                                r_dt_str = r_dt_obj.strftime("%Y-%m-%d %H:%M")
                                                
                                                overlap_check = pd.read_sql_query("""
                                                    SELECT booking_ref FROM bookings 
                                                    WHERE vehicle_id = ? 
                                                    AND status NOT IN ('CANCELLED', 'REJECTED', 'COMPLETED')
                                                    AND pickup_time < ? 
                                                    AND return_time > ?
                                                """, conn, params=(car['id'], r_dt_str, p_dt_str))

                                                if not overlap_check.empty:
                                                    st.error("⚠️ Sorry! This vehicle was just booked by someone else for these dates. Please select different dates.")
                                                    st.stop()

                                                if dest and p_exact and r_exact and luzon_agree:
                                                    if car['owner_username'] == renter_user:
                                                        st.error("⚠️ You cannot rent your own registered vehicle.")
                                                    else:
                                                        with st.spinner("Submitting request to host..."):
                                                            b_ref = str(random.randint(100000, 999999))
                                                            is_drvr_int = 1 if "Driver" in drive_mode else 0
                                                            
                                                            # Insert booking with PENDING_APPROVAL status so host can review distance before payment
                                                            conn.execute("""
                                                                INSERT INTO bookings (renter_username, vehicle_id, pickup_time, return_time, amount, status, destination, pickup_loc, return_loc, with_driver, booking_ref) 
                                                                VALUES (?, ?, ?, ?, ?, 'PENDING_APPROVAL', ?, ?, ?, ?, ?)
                                                            """, (renter_user, car['id'], p_dt_str, r_dt_str, grand_total, dest, f"Pickup: {p_exact}", f"Return: {r_exact}", is_drvr_int, b_ref))
                                                            conn.commit()

                                                            st.session_state[ref_key] = b_ref
                                                            st.session_state[stage_key] = 1 # Move to Host Review / Negotiation stage
                                                            st.rerun()
                                                else:
                                                    st.error("⚠️ ACTION REQUIRED: Please fill in your Destination, Specific Pickup/Return Addresses, and check the travel agreement box before confirming.")

                                        # -------------------------------------------------------------
                                        # CHECKOUT STAGE 1: WAITING FOR HOST DISTANCE APPROVAL & CHAT
                                        # -------------------------------------------------------------
                                        elif st.session_state[stage_key] == 1:
                                            b_ref = st.session_state.get(ref_key)
                                            
                                            st.markdown(f"""
                                                <div style="background-color: #FEF3C7; border: 1px solid #F59E0B; padding: 20px; border-radius: 12px; border-left: 6px solid #D97706; margin-bottom: 20px;">
                                                    <h4 style="color: #92400E; margin-top: 0; margin-bottom: 8px;">⏳ Awaiting Host Distance Review (Ref: #{b_ref})</h4>
                                                    <p style="color: #78350F; font-size: 15px; margin-bottom: 0;">
                                                        Your booking request has been sent to the car owner. The owner is reviewing your pickup and return locations from their parking base ({parking_location}). <b>Please use your My Bookings chat to coordinate or negotiate distance before making any payment.</b>
                                                    </p>
                                                </div>
                                            """, unsafe_allow_html=True)

                                            # Check current status from DB in case host approved it
                                            status_df = pd.read_sql_query("SELECT status FROM bookings WHERE booking_ref = ?", conn, params=(b_ref,))
                                            current_db_status = status_df.iloc[0]['status'] if not status_df.empty else 'PENDING_APPROVAL'

                                            if current_db_status in ['APPROVED_BY_HOST', 'CONFIRMED']:
                                                st.success("🎉 **Host Accepted Distance!** You may now proceed with your payment.")
                                                if gateway_mode == "XENDIT":
                                                    if st.button("PROCEED TO XENDIT PAYMENT", type="primary", use_container_width=True, key=f"pay_xendit_{car['id']}"):
                                                        st.session_state[stage_key] = 2
                                                        st.rerun()
                                                else:
                                                    if st.button("PROCEED TO MANUAL PAYMENT", type="primary", use_container_width=True, key=f"pay_manual_{car['id']}"):
                                                        st.session_state[stage_key] = 2
                                                        st.rerun()

                                            c_back, c_refresh = st.columns([1, 1])
                                            if c_back.button("Cancel Request", key=f"canc_req_{car['id']}_{cat}", use_container_width=True):
                                                conn.execute("DELETE FROM bookings WHERE booking_ref = ?", (b_ref,))
                                                conn.commit()
                                                st.session_state[stage_key] = 0
                                                if ref_key in st.session_state: del st.session_state[ref_key]
                                                st.rerun()
                                            if c_refresh.button("🔄 Refresh Status", key=f"ref_status_{car['id']}_{cat}", use_container_width=True):
                                                st.rerun()

                                        # -------------------------------------------------------------
                                        # CHECKOUT STAGE 2: PAYMENT GATEWAY (XENDIT OR BPI MANUAL)
                                        # -------------------------------------------------------------
                                        elif st.session_state[stage_key] == 2:
                                            b_ref = st.session_state.get(ref_key)
                                            
                                            if gateway_mode == "XENDIT":
                                                try:
                                                    SECRET_KEY = os.environ.get("xendit_active_key")
                                                    if not SECRET_KEY:
                                                        try: SECRET_KEY = st.secrets.get("xendit_active_key")
                                                        except: pass 
                                                    
                                                    amt_df = pd.read_sql_query("SELECT amount FROM bookings WHERE booking_ref = ?", conn, params=(b_ref,))
                                                    owed_amt = float(amt_df.iloc[0]['amount']) if not amt_df.empty else 0.0

                                                    owner_data = pd.read_sql_query("SELECT xendit_sub_id FROM platform_users WHERE username=?", conn, params=(car['owner_username'],))
                                                    sub_id = owner_data.iloc[0]['xendit_sub_id'] if not owner_data.empty else None
                                                    
                                                    auth_string = f"{SECRET_KEY}:"
                                                    base64_auth = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
                                                    url = "https://api.xendit.co/v2/invoices"
                                                    
                                                    payload = {
                                                        "external_id": str(b_ref),
                                                        "amount": int(owed_amt),
                                                        "currency": "PHP",
                                                        "description": f"DriveElite - {car['make']} {car['model']} (Ref: {b_ref})",
                                                    }
                                                    
                                                    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'))
                                                    req.add_header('accept', 'application/json')
                                                    req.add_header('content-type', 'application/json')
                                                    req.add_header('authorization', f'Basic {base64_auth}')
                                                    if sub_id: req.add_header('for-user-id', sub_id)
                                                    
                                                    response = urllib.request.urlopen(req)
                                                    checkout_url = json.loads(response.read().decode('utf-8'))['invoice_url']
                                                    
                                                    st.link_button("💳 PROCEED TO XENDIT SECURE CHECKOUT", checkout_url, type="primary", use_container_width=True)
                                                except Exception as e:
                                                    st.error(f"Error generating Xendit invoice: {e}")
                                            else:
                                                with st.container(border=True):
                                                    st.markdown("### 🏦 Manual Bank Transfer")
                                                    st.write("**Bank:** BPI")
                                                    st.write("**Account Name:** Romeo Albao Jr.")
                                                    st.write("**Account Number:** 0180 0206 08")
                                                    
                                                    amt_df = pd.read_sql_query("SELECT amount FROM bookings WHERE booking_ref = ?", conn, params=(b_ref,))
                                                    owed_amount = float(amt_df.iloc[0]['amount']) if not amt_df.empty else 0.0
                                                    st.write(f"**Amount to Transfer:** :green[**₱{owed_amount:,.2f}**]")
                                                    
                                                    s1, c_img, s2 = st.columns([1, 1, 1])
                                                    with c_img:
                                                        try: st.image("bpi_qr.png", use_container_width=True)
                                                        except: st.info("[BPI QR IMAGE GOES HERE]")
                                                    
                                                    st.divider()
                                                    st.write("#### 📤 Upload Proof of Payment")
                                                    receipt_file = st.file_uploader("Upload Receipt", type=['jpg', 'png', 'jpeg'], key=f"rec_{car['id']}_{cat}")
                                                    
                                                    if st.button("2. VALIDATE PAYMENT SENT", type="primary", use_container_width=True, key=f"val_{car['id']}_{cat}"):
                                                        if receipt_file:
                                                            receipt_bytes = receipt_file.read()
                                                            conn.execute("UPDATE bookings SET receipt_img = ?, status = 'VERIFYING' WHERE booking_ref = ?", (receipt_bytes, b_ref))
                                                            receipt_path = f"/data/uploads/chat_images/receipt_{b_ref}.jpg"
                                                            with open(receipt_path, "wb") as f: f.write(receipt_bytes)
                                                            
                                                            owner_username = car['owner_username']
                                                            conn.execute("INSERT INTO chat_messages (booking_ref, sender_username, receiver_username, message_text, image_path) VALUES (?, ?, ?, ?, ?)", 
                                                                         (b_ref, renter_user, owner_username, "Payment Receipt Uploaded for Verification.", receipt_path))
                                                            conn.commit()
                                                            st.success("✅ Receipt sent to host for verification!")
                                                            st.session_state[stage_key] = 0
                                                            del st.session_state[ref_key]
                                                            st.rerun()
                                                        else:
                                                            st.error("Please upload your receipt.")

                                            if st.button("Cancel Booking", key=f"canc_final_{car['id']}_{cat}", use_container_width=True):
                                                conn.execute("DELETE FROM bookings WHERE booking_ref = ?", (b_ref,))
                                                conn.commit()
                                                st.session_state[stage_key] = 0
                                                if ref_key in st.session_state: del st.session_state[ref_key]
                                                st.rerun()

    # ==========================================
    # 📅 MY BOOKINGS (MAIN TAB 1)
    # ==========================================
    with main_tabs[1]:
        st.header("📅 My Booking History")
        
        try:
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
                            st.info(b['status'])

                    # --- CHAT SYSTEM (For Active Trips & Approvals) ---
                    if b['status'] in ['PENDING_APPROVAL', 'PENDING', 'VERIFYING', 'APPROVED_BY_HOST', 'CONFIRMED', 'ONGOING']:
                        st.divider()
                        st.markdown(f"#### 💬 Coordinate with Host (Ref: #{b['booking_ref']})")
                        b_ref_str = str(b['booking_ref'])
                        
                        st_autorefresh(interval=10000, key=f"chat_ping_{b_ref_str}")
                        
                        chat_win = st.container(height=250, border=True)
                        with chat_win:
                            try:
                                msgs = pd.read_sql_query("SELECT * FROM chat_messages WHERE booking_ref = ? ORDER BY timestamp ASC", conn, params=(b_ref_str,))
                                if msgs.empty:
                                    st.info("👋 Chat is empty. Discuss pickup/return distance or delivery terms with your host here!")
                                else:
                                    for _, m in msgs.iterrows():
                                        if m['sender_username'] == renter_user:
                                            st.markdown(f"""
                                            <div style="display: flex; justify-content: flex-end; margin-bottom: 5px;">
                                                <div style="background-color: #2563EB; color: white; padding: 10px 14px; border-radius: 16px 16px 4px 16px; max-width: 75%;">
                                                    {m['message_text']}
                                                </div>
                                            </div>
                                            """, unsafe_allow_html=True)
                                        else:
                                            st.markdown(f"""
                                            <div style="display: flex; justify-content: flex-start; margin-bottom: 5px;">
                                                <div style="background-color: #334155; color: white; padding: 10px 14px; border-radius: 16px 16px 16px 4px; max-width: 75%;">
                                                    <div style="color: #cbd5e1; font-size: 0.75em; margin-bottom: 2px;">@{m['sender_username']} (Host)</div>
                                                    {m['message_text']}
                                                </div>
                                            </div>
                                            """, unsafe_allow_html=True)
                            except Exception:
                                st.error("Could not load chat.")

                        input_key = f"chat_input_{b_ref_str}"
                        if input_key not in st.session_state: st.session_state[input_key] = ""
                        
                        c_msg, c_btn = st.columns([4, 1])
                        with c_msg: 
                            chat_val = st.text_input("Reply", key=input_key, label_visibility="collapsed", placeholder="Negotiate distance or parking handover...")
                        with c_btn:
                            if st.button("Send", type="primary", use_container_width=True, key=f"send_btn_{b_ref_str}"):
                                if chat_val.strip():
                                    message_body = chat_val.strip()
                                    conn.execute("INSERT INTO chat_messages (booking_ref, sender_username, receiver_username, message_text) VALUES (?, ?, ?, ?)",
                                                 (b_ref_str, renter_user, b['owner_username'], message_body))
                                    conn.commit()
                                    
                                    # 🚨 INSTANT EMAIL POPUP TO AFFILIATE ON CHAT
                                    try:
                                        host_data = pd.read_sql_query("SELECT email, full_name FROM platform_users WHERE username=?", conn, params=(b['owner_username'],))
                                        if not host_data.empty:
                                            host_email = host_data.iloc[0]['email']
                                            host_name = host_data.iloc[0]['full_name']
                                            send_alert_email(
                                                to_email=host_email,
                                                subject=f"💬 DriveElite: New Message Regarding Booking #{b_ref_str}",
                                                body=f"Hello {host_name},\n\nRenter @{renter_user} sent a message regarding booking #{b_ref_str}:\n\n\"{message_body}\"\n\nLog in to your DriveElite dashboard to reply and coordinate handover."
                                            )
                                    except Exception:
                                        pass

                                    st.session_state[input_key] = ""
                                    st.rerun()

                        st.caption("ℹ️ **Logistics & Security Deposit Policy:** If pickup or return locations are modified after payment to a further distance, the incremental logistics fee will be automatically **deducted from your ₱5,000 security deposit** upon trip completion.")

                    # --- THE REVIEW SYSTEM ---
                    if b['status'] == 'COMPLETED':
                        st.divider()
                        if pd.isna(b['rating']) or b['rating'] == "" or b['rating'] == 0:
                            with st.expander("⭐ Leave a Review for this Trip!", expanded=True):
                                st.write("**Rate your experience:**")
                                star_click = st.feedback("stars", key=f"stars_{b['id']}")
                                new_review = st.text_area("Share your thoughts about the vehicle and host...", key=f"rev_text_{b['id']}")
                                
                                if st.button("Submit Review", type="primary", key=f"sub_rev_{b['id']}"):
                                    if star_click is None:
                                        st.error("Please click on the stars to leave a rating!")
                                    else:
                                        final_rating = star_click + 1 
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

if __name__ == "__main__":
    main()
