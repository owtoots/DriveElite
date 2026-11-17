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
        div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stImage"] img {
            height: 200px !important;
            width: 100% !important;
            object-fit: cover !important;
            border-radius: 8px !important;
        }
        
        [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: #F8FAFC !important;
            color: #0F172A !important;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
        }
        
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
            padding-top: 2rem !important;
            padding-bottom: 1.5rem !important;
            margin-top: 0 !important;
        }
        [data-testid="stSidebarNav"] {
            order: 2 !important;
            padding-top: 1rem !important;
        }

        [data-testid="stForm"], .stForm, div[data-testid="stExpander"], div.stMetric {
            background-color: #FFFFFF !important;
            padding: 20px !important;
            border-radius: 16px !important;
            border: 1px solid #E2E8F0 !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
        }

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

        div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
            background-color: #FFFFFF !important;
            border: 1px solid #CBD5E1 !important;
            border-radius: 8px !important;
        }
        input { color: #1E293B !important; }
        h1, h2, h3 { color: #0F172A !important; font-weight: 800 !important; }
        label { color: #475569 !important; font-weight: 600 !important; }
        
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
         # ======================================
         #   📸 UNIFORM CAR IMAGES (PERFECT ALIGNMENT)
         # ==========================================
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
        st.header("🚘 Available Fleet Across Regions")

        available_cars = pd.read_sql_query("""
            SELECT v.*, u.full_name as owner_name 
            FROM vehicles v 
            JOIN platform_users u ON v.owner_username = u.username 
            WHERE v.admin_status = 'APPROVED' AND v.booking_status = 'AVAILABLE'
        """, conn)

        if available_cars.empty:
            st.info("Our fleet is currently fully booked. Please check back later!")
        else:
            # 🌍 DYNAMIC CITY EXTRACTION
            if 'location' in available_cars.columns:
                available_cars['clean_city'] = available_cars['location'].apply(lambda x: str(x).split(',')[-1].strip() if pd.notnull(x) else "Metro Manila")
                cities = ["All Cities"] + sorted(available_cars['clean_city'].unique().tolist())
            else:
                cities = ["All Cities", "Metro Manila"]
                available_cars['clean_city'] = "Metro Manila"
            
            # Render Top-Level City Folders (Tabs)
            city_tabs = st.tabs([f"🏙️ {c}" for c in cities])
            
            for tab_index, city_name in enumerate(cities):
                with city_tabs[tab_index]:
                    
                    # Filter cars by the selected city folder
                    if city_name == "All Cities":
                        city_cars = available_cars.copy()
                    else:
                        city_cars = available_cars[available_cars['clean_city'] == city_name].copy()
                        
                    if city_cars.empty:
                        st.info(f"No vehicles currently available in {city_name}. Check back soon as we expand!")
                    else:
                        # 🏷️ CATEGORY TABS INSIDE EACH CITY FOLDER
                        if 'category' in city_cars.columns:
                            categories = ["All"] + sorted(city_cars['category'].dropna().unique().tolist())
                        elif 'type' in city_cars.columns:
                            categories = ["All"] + sorted(city_cars['type'].dropna().unique().tolist())
                        else:
                            categories = ["All"]
                            
                        category_tabs = st.tabs(categories)
                        
                        for cat_idx, cat in enumerate(categories):
                            with category_tabs[cat_idx]:
                                if cat == "All":
                                    category_cars = city_cars.copy()
                                else:
                                    filter_col = 'category' if 'category' in city_cars.columns else 'type'
                                    category_cars = city_cars[city_cars[filter_col] == cat].copy()
                                
                                if category_cars.empty:
                                    st.info(f"No {cat} vehicles available in {city_name} right now.")
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
                                                        filename = os.path.basename(str(img_p))
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
                                                
                                                st.markdown(f"<h5 style='color: #2563EB;'>₱{base_rate:,.2f} / day</h5>", unsafe_allow_html=True)
                                                # --- BOTTOM: POPOVER CHECKOUT MANAGER ---
                                                with st.popover(f"⚡ BOOK {car['model'].upper()} NOW", use_container_width=True):
                                                    stage_key = f"chk_stage_{car['id']}_{cat}"
                                                    ref_key = f"pend_ref_{car['id']}_{cat}"
                                                    if stage_key not in st.session_state: 
                                                        st.session_state[stage_key] = 0
                                                    
                                                    unavailable_dates = get_booked_dates(car['id'], conn)
                                                    
                                                    # --- STAGE 0: SELECT DATES & LOCATIONS ---
                                                    if st.session_state[stage_key] == 0:
                                                        today = datetime.date.today()
                                                        d1 = st.date_input("Pickup Date", min_value=today, key=f"d1_{car['id']}_{cat}")
                                                        t1 = st.time_input("Pickup Time", value=datetime.time(9, 0), key=f"t1_{car['id']}_{cat}")
                                                        d2 = st.date_input("Return Date", min_value=d1, value=d1, key=f"d2_{car['id']}_{cat}")
                                                        t2 = st.time_input("Return Time", value=datetime.time(9, 0), key=f"t2_{car['id']}_{cat}")
                                                        
                                                        pickup_loc = st.text_input("Pickup Location / Delivery Address", value=parking_location, key=f"ploc_{car['id']}_{cat}")
                                                        return_loc = st.text_input("Return Location / Drop-off Address", value=parking_location, key=f"rloc_{car['id']}_{cat}")
                                                        destination = st.text_input("Declared Trip Route / Destination", placeholder="e.g., Tagaytay or Subic", key=f"dest_{car['id']}_{cat}")
                                                        
                                                        if st.button("PROCEED TO SUMMARY", key=f"btn_s0_{car['id']}_{cat}", use_container_width=True):
                                                            if not destination.strip():
                                                                st.error("Please specify your trip route or destination.")
                                                            else:
                                                                st.session_state[stage_key] = 1
                                                                st.rerun()

                                                    # --- STAGE 1: CONFIRMATION & DISTANCE APPROVAL ---
                                                    elif st.session_state[stage_key] == 1:
                                                        st.write("### 📋 Booking Summary")
                                                        st.write(f"🚗 **Vehicle:** {car['make']} {car['model']}")
                                                        st.write(f"📅 **Pickup:** {st.session_state.get(f'd1_{car['id']}_{cat}')} at {st.session_state.get(f't1_{car['id']}_{cat}')}")
                                                        st.write(f"📅 **Return:** {st.session_state.get(f'd2_{car['id']}_{cat}')} at {st.session_state.get(f't2_{car['id']}_{cat}')}")
                                                        st.write(f"🛣️ **Destination:** {st.session_state.get(f'dest_{car['id']}_{cat}')}")
                                                        
                                                        if st.button("SUBMIT FOR HOST DISTANCE APPROVAL", key=f"btn_s1_{car['id']}_{cat}", type="primary", use_container_width=True):
                                                            booking_ref = str(random.randint(100000, 999999))
                                                            
                                                            s_d1 = st.session_state.get(f"d1_{car['id']}_{cat}", datetime.date.today())
                                                            s_t1 = st.session_state.get(f"t1_{car['id']}_{cat}", datetime.time(9,0))
                                                            s_d2 = st.session_state.get(f"d2_{car['id']}_{cat}", s_d1)
                                                            s_t2 = st.session_state.get(f"t2_{car['id']}_{cat}", datetime.time(9,0))
                                                            
                                                            pickup_dt = datetime.datetime.combine(s_d1, s_t1)
                                                            return_dt = datetime.datetime.combine(s_d2, s_t2)
                                                            days_calc = max(1, (return_dt - pickup_dt).days)
                                                            total_amount = base_rate * days_calc
                                                            
                                                            conn.execute("""
                                                                INSERT INTO bookings (
                                                                    booking_ref, vehicle_id, renter_username, pickup_time, return_time,
                                                                    pickup_loc, return_loc, destination, amount, status
                                                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING_APPROVAL')
                                                            """, (booking_ref, car['id'], st.session_state.username, str(pickup_dt), str(return_dt), 
                                                                  st.session_state.get(f"ploc_{car['id']}_{cat}", ""), 
                                                                  st.session_state.get(f"rloc_{car['id']}_{cat}", ""), 
                                                                  st.session_state.get(f"dest_{car['id']}_{cat}", ""), 
                                                                  total_amount))
                                                            conn.commit()
                                                            
                                                            st.success(f"Booking request submitted! Ref #{booking_ref}. Awaiting host distance review.")
                                                            st.session_state[stage_key] = 0
                                                            time.sleep(1.5)
                                                            st.rerun()

                                                    # --- STAGE 2: XENDIT GATEWAY & RECEIPT UPLOAD ---
                                                    elif st.session_state[stage_key] == 2:
                                                        b_ref = st.session_state.get(ref_key)
                                                        pay_url = st.session_state.get(f"pay_url_{car['id']}")

                                                        amt_df = pd.read_sql_query("SELECT amount FROM bookings WHERE booking_ref = ?", conn, params=(b_ref,))
                                                        owed_amount = float(amt_df.iloc[0]['amount']) if not amt_df.empty else 0.0

                                                        st.markdown(f"""
                                                        <div style="background-color: #EFF6FF; border: 1px solid #BFDBFE; padding: 20px; border-radius: 12px; border-left: 6px solid #2563EB; margin-bottom: 20px;">
                                                            <h4 style="color: #1E3A8A; margin-top: 0; margin-bottom: 8px;">💳 Secure Payment (Ref: #{b_ref})</h4>
                                                            <p style="color: #1D4ED8; font-size: 15px; margin-bottom: 0;">
                                                                Total Amount Due: <b>₱{owed_amount:,.2f}</b><br>
                                                                Please complete your payment via Xendit, then take a screenshot of your payment confirmation (showing the reference number) and upload it below for Admin verification.
                                                            </p>
                                                        </div>
                                                        """, unsafe_allow_html=True)

                                                        if pay_url:
                                                            st.link_button("👉 CLICK HERE TO PAY VIA XENDIT", pay_url, type="primary", use_container_width=True)

                                                        st.divider()
                                                        st.write("#### 📤 Upload Xendit Payment Screenshot")
                                                        st.caption("Upload your payment success screenshot containing the transaction reference number.")
                                                        xendit_receipt = st.file_uploader("Upload Xendit Receipt", type=['jpg', 'png', 'jpeg'], key=f"x_rec_{car['id']}_{cat}")

                                                        c_back, c_sub = st.columns([1, 1])
                                                        if c_back.button("Cancel Booking", key=f"canc_x_{car['id']}_{cat}", use_container_width=True):
                                                            conn.execute("DELETE FROM bookings WHERE booking_ref = ?", (b_ref,))
                                                            conn.commit()
                                                            st.session_state[stage_key] = 0
                                                            if ref_key in st.session_state: del st.session_state[ref_key]
                                                            st.rerun()

                                                        if c_sub.button("SUBMIT PAYMENT PROOF TO ADMIN", type="primary", use_container_width=True, key=f"sub_x_{car['id']}_{cat}"):
                                                            if xendit_receipt:
                                                                receipt_bytes = xendit_receipt.read()
                                                                conn.execute("UPDATE bookings SET receipt_img = ?, status = 'VERIFYING' WHERE booking_ref = ?", (receipt_bytes, b_ref))
                                                                receipt_path = f"/data/uploads/chat_images/receipt_{b_ref}.jpg"
                                                                with open(receipt_path, "wb") as f: f.write(receipt_bytes)

                                                                owner_username = car['owner_username']
                                                                conn.execute("INSERT INTO chat_messages (booking_ref, sender_username, receiver_username, message_text, image_path) VALUES (?, ?, ?, ?, ?)", 
                                                                             (b_ref, renter_user, owner_username, "Xendit Payment Proof Uploaded for Admin Verification.", receipt_path))
                                                                conn.commit()

                                                                # Alert Admin and Affiliate
                                                                try:
                                                                    aff_data = pd.read_sql_query("SELECT email, full_name FROM platform_users WHERE username=?", conn, params=(owner_username,))
                                                                    if not aff_data.empty:
                                                                        send_alert_email(
                                                                            to_email="contact@driveelite.ph",
                                                                            subject=f"CNF: Xendit Proof Verification Needed for #{b_ref}",
                                                                            body=f"Renter @{renter_user} uploaded Xendit payment proof for booking #{b_ref}. Please verify."
                                                                        )
                                                                        send_alert_email(
                                                                            to_email=aff_data.iloc[0]['email'],
                                                                            subject=f"🚗 DriveElite: Payment Proof Uploaded (#{b_ref})",
                                                                            body=f"Hello {aff_data.iloc[0]['full_name']},\n\nRenter uploaded payment proof for booking #{b_ref}. Admin is verifying."
                                                                        )
                                                                except: pass

                                                                st.success("✅ Payment proof submitted to Admin for verification!")
                                                                st.session_state[stage_key] = 0
                                                                if ref_key in st.session_state: del st.session_state[ref_key]
                                                                st.rerun()
                                                            else:
                                                                st.error("Please upload your payment screenshot.")

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

                    # ==========================================================
                    # 💳 PASTE THE PAYMENT BLOCK HERE:
                    # ==========================================================
                    if b['status'] == 'APPROVED_BY_HOST':
                        st.divider()
                        st.markdown("### 💳 Secure Payment Required")
                        st.success("🎉 Your host has approved your pickup and return locations! Please complete your payment below to secure your reservation.")
                        
                        owed_amount = float(b['amount'])
                        st.write(f"**Total Amount Due:** :green[**₱{owed_amount:,.2f}**]")
                        
                        with st.container(border=True):
                            st.markdown("#### 🏦 Manual Bank Transfer")
                            st.write("**Bank:** BPI")
                            st.write("**Account Name:** Romeo Albao Jr.")
                            st.write("**Account Number:** 0180 0206 08")
                            
                            s1, c_img, s2 = st.columns([1, 1, 1])
                            with c_img:
                                try: st.image("bpi_qr.png", use_container_width=True)
                                except: st.info("[BPI QR IMAGE GOES HERE]")
                            
                            st.divider()
                            st.write("#### 📤 Upload Proof of Payment (Showing Reference No.)")
                            receipt_file = st.file_uploader("Upload Receipt", type=['jpg', 'png', 'jpeg'], key=f"my_rec_{b['id']}")
                            
                            if st.button("SUBMIT PAYMENT RECEIPT TO ADMIN", type="primary", use_container_width=True, key=f"my_val_{b['id']}"):
                                if receipt_file:
                                    receipt_bytes = receipt_file.read()
                                    conn.execute("UPDATE bookings SET receipt_img = ?, status = 'VERIFYING' WHERE id = ?", (receipt_bytes, b['id']))
                                    receipt_path = f"/data/uploads/chat_images/receipt_{b['booking_ref']}.jpg"
                                    with open(receipt_path, "wb") as f: f.write(receipt_bytes)
                                    
                                    conn.execute("INSERT INTO chat_messages (booking_ref, sender_username, receiver_username, message_text, image_path) VALUES (?, ?, ?, ?, ?)", 
                                                 (str(b['booking_ref']), renter_user, b['owner_username'], "Payment Receipt Uploaded for Admin Verification.", receipt_path))
                                    conn.commit()
                                    st.success("✅ Receipt submitted! Status updated to VERIFYING. Waiting for Admin confirmation.")
                                    time.sleep(1.5)
                                    st.rerun()
                                else:
                                    st.error("Please upload a screenshot of your payment receipt.")
                  

                   
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
