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
from database_utils import init_db, patch_database
import urllib.parse

# ==========================================
# OPENSTREETMAP & OSRM DISTANCE ROUTING
# ==========================================
def _haversine_road_km(coord1, coord2):
    """Estimates driving distance (straight-line km * 1.35 road factor) if OSRM times out."""
    lat1, lon1 = map(math.radians, coord1)
    lat2, lon2 = map(math.radians, coord2)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a)) * 1.35

def get_gps_coordinates(address):
    """Converts a text address into (lat, lon) using Photon, falling back to Nominatim."""
    if not address:
        return None
    query = urllib.parse.quote(f"{address}, Philippines")
    headers = {'User-Agent': 'DriveElite/1.0 (contact@driveelite.ph)'}

    # 1. Photon (handles informal PH mall names)
    try:
        url = f"https://photon.komoot.io/api/?q={query}&limit=1"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
            if data.get('features'):
                lon, lat = data['features'][0]['geometry']['coordinates']
                return float(lat), float(lon)
    except Exception:
        pass

    # 2. Nominatim fallback
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={query}&format=json&limit=1"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
            if data:
                return float(data[0]['lat']), float(data[0]['lon'])
    except Exception:
        pass

    return None

def get_osrm_driving_distance(coord1, coord2):
    """Calculates driving distance in KM using OSRM (HTTPS), with road-factor fallback."""
    if not coord1 or not coord2:
        return None
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    url = f"https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
    req = urllib.request.Request(url, headers={'User-Agent': 'DriveElite/1.0 (contact@driveelite.ph)'})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            if data.get('routes'):
                return data['routes'][0]['distance'] / 1000.0
    except Exception:
        pass
    return _haversine_road_km(coord1, coord2)
def create_xendit_invoice(booking_ref, amount, description, payer_email=None):
    """Generates a Xendit Hosted Checkout URL using Render Env Vars or st.secrets."""
    api_key = None
    for key_name in ["xendit_active_key", "XENDIT_ACTIVE_KEY", "XENDIT_SECRET_KEY", "xendit_secret_key", "XENDIT_API_KEY"]:
        val = os.environ.get(key_name)
        if not val:
            try:
                val = st.secrets.get(key_name)
            except Exception:
                val = None
        if val:
            api_key = str(val).strip()
            break

    if not api_key:
        return None, "Xendit key not found in Render Environment Variables or st.secrets."

    url = "https://api.xendit.co/v2/invoices"
    auth_str = base64.b64encode(f"{api_key}:".encode("utf-8")).decode("utf-8")

    payload = {
        "external_id": f"DRIVEELITE-{booking_ref}",
        "amount": float(amount),
        "currency": "PHP",
        "description": description,
        "invoice_duration": 86400
    }
    if payer_email and "@" in str(payer_email):
        payload["payer_email"] = str(payer_email)

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Basic {auth_str}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("invoice_url"), None
    except urllib.error.HTTPError as e:
        return None, f"Xendit API Error {e.code}: {e.read().decode('utf-8')}"
    except Exception as e:
        return None, str(e)

def main():
    # ==========================================
    # 1. PAGE CONFIG & LOGO
    # ==========================================
    st.set_page_config(page_title="DriveElite Renter", layout="wide", initial_sidebar_state="expanded")
    
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
        
        try: conn.execute("ALTER TABLE bookings ADD COLUMN pay_url TEXT"); conn.commit()
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

    def generate_booked_calendar_html(unavailable_dates, ref_d1, ref_d2):
        today = datetime.date.today()
        months_to_show = [(ref_d1.year, ref_d1.month)]
        if (ref_d2.year, ref_d2.month) != (ref_d1.year, ref_d1.month):
            months_to_show.append((ref_d2.year, ref_d2.month))

        html = '<div style="display: flex; gap: 12px; flex-wrap: wrap; justify-content: center; margin-top: 6px;">'
        for y, m in months_to_show:
            month_name = calendar.month_name[m]
            html += (
                '<div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 10px; padding: 10px; width: 100%; max-width: 240px;">'
                f'<div style="text-align: center; font-weight: 800; color: #0F172A; margin-bottom: 8px; font-size: 14px;">{month_name} {y}</div>'
                '<div style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 3px; text-align: center; font-size: 11px; font-weight: 700; color: #64748B; margin-bottom: 4px;">'
                '<div>M</div><div>T</div><div>W</div><div>T</div><div>F</div><div>S</div><div>S</div>'
                '</div>'
                '<div style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 3px; text-align: center; font-size: 12px; font-weight: 600;">'
            )
            for week in calendar.monthcalendar(y, m):
                for day in week:
                    if day == 0:
                        html += '<div></div>'
                    else:
                        cur = datetime.date(y, m, day)
                        if cur in unavailable_dates:
                            html += (
                                '<div style="position: relative; background-color: #FEE2E2; color: #DC2626; border: 1px solid #EF4444; border-radius: 5px; padding: 4px 0; font-weight: 800;" title="Booked">'
                                f'<span style="opacity: 0.45;">{day}</span>'
                                '<span style="position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; font-size: 16px; color: #DC2626; font-weight: 900;">&#10005;</span>'
                                '</div>'
                            )
                        elif ref_d1 <= cur <= ref_d2:
                            html += f'<div style="background-color: #DBEAFE; color: #1D4ED8; border: 1px solid #3B82F6; border-radius: 5px; padding: 4px 0; font-weight: 800;" title="Your Selection">{day}</div>'
                        elif cur < today:
                            html += f'<div style="color: #94A3B8; padding: 4px 0;">{day}</div>'
                        else:
                            html += f'<div style="background-color: #DCFCE7; color: #16A34A; border: 1px solid #86EFAC; border-radius: 5px; padding: 4px 0;">{day}</div>'
            html += '</div></div>'

        html += (
            '</div>'
            '<div style="text-align: center; font-size: 11px; color: #475569; margin-top: 8px;">'
            '<span style="color: #DC2626; font-weight: 700;">&#10005; Red</span> = Booked &nbsp;|&nbsp; '
            '<span style="color: #1D4ED8; font-weight: 700;">Blue</span> = Selected &nbsp;|&nbsp; '
            '<span style="color: #16A34A; font-weight: 700;">Green</span> = Available'
            '</div>'
        )
        return html   
    def get_dynamic_delivery_fee(total_km):
        try:
            if total_km <= 5.0:
                return 350.0
            base_taxi_fare = 150.0
            fuel_and_time_rate = 50.0
            driver_buffer = 20.0
            return_taxi_estimate = total_km * 45.0 
            calculated_fee = base_taxi_fare + (total_km * fuel_and_time_rate) + return_taxi_estimate + driver_buffer
            return round(calculated_fee, -2) 
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
        if f"chat_{b_ref}" in st.session_state:
            st.session_state.temp_msg_renter = st.session_state[f"chat_{b_ref}"]
            st.session_state[f"chat_{b_ref}"] = ""
            st.session_state[f"trigger_send_{b_ref}"] = True

    def save_chat_image(img_file, b_ref):
        if img_file:
            path = f"/data/uploads/chat_images/{b_ref}_{img_file.name}"
            with open(path, "wb") as f:
                f.write(img_file.getbuffer())
            return path
        return ""

    def send_alert_email(to_email, subject, body):
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

    try:
        promo_df = pd.read_sql_query(
            "SELECT title, message FROM admin_promos WHERE active = 1 AND UPPER(TRIM(target)) IN ('RENTER', 'RENTERS', 'ALL USERS', 'ALL') ORDER BY id DESC LIMIT 1",
            conn
        )
        if not promo_df.empty:
            title = promo_df.iloc[0]['title']
            msg = promo_df.iloc[0]['message']
            st.markdown(f"""
                <style>
                .broadcast-box {{ padding: 25px 20px; background-color: #2563EB; color: white; border-radius: 12px; margin-bottom: 25px; text-align: center; font-size: 22px; display: flex; flex-direction: row; justify-content: center; align-items: center; flex-wrap: wrap; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); border: 1px solid rgba(255, 255, 255, 0.15); }}
                .broadcast-title {{ font-weight: 900; margin-right: 12px; letter-spacing: 0.5px; }}
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
            if 'location' in available_cars.columns:
                available_cars['clean_city'] = available_cars['location'].apply(lambda x: str(x).split(',')[-1].strip() if pd.notnull(x) else "Metro Manila")
                cities = ["All Cities"] + sorted(available_cars['clean_city'].unique().tolist())
            else:
                cities = ["All Cities", "Metro Manila"]
                available_cars['clean_city'] = "Metro Manila"
            
            city_tabs = st.tabs([f"🏙️ {c}" for c in cities])
            
            for tab_index, city_name in enumerate(cities):
                with city_tabs[tab_index]:
                    
                    if city_name == "All Cities":
                        city_cars = available_cars.copy()
                    else:
                        city_cars = available_cars[available_cars['clean_city'] == city_name].copy()
                        
                    if city_cars.empty:
                        st.info(f"No vehicles currently available in {city_name}. Check back soon as we expand!")
                    else:
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
                                                
                                                img_p = car.get('vehicle_img')
                                                resolved_img_path = None
                                                
                                                if pd.notnull(img_p) and str(img_p).strip():
                                                    img_str = str(img_p).strip()
                                                    filename = os.path.basename(img_str)
                                                    
                                                    # Check persistent Render disk first
                                                    persistent_path = f"/data/uploads/{filename}"
                                                    local_fallback = os.path.join(os.getcwd(), "data", "uploads", filename)
                                                    
                                                    if os.path.exists(persistent_path):
                                                        resolved_img_path = persistent_path
                                                    elif os.path.exists(img_str):
                                                        resolved_img_path = img_str
                                                    elif os.path.exists(local_fallback):
                                                        resolved_img_path = local_fallback
                                                
                                                if resolved_img_path:
                                                    st.image(resolved_img_path, use_container_width=True)
                                                else:
                                                    st.image("https://placehold.co/600x400?text=No+Photo+Found", use_container_width=True)
                                                
                                                base_rate = float(car.get('daily_rate') or car.get('approved_price') or 0.0)
                                                st.markdown(f"#### {car['make']} {car['model']}\n**Year:** {car['year']}", unsafe_allow_html=True)
                                                
                                                parking_location = car.get('location', 'Metro Manila')
                                                plate_no = car.get('plate', 'N/A')
                                                st.caption(f"📍 Parking Base: **{parking_location}** (Plate: {plate_no})")
                                                
                                                st.markdown(f"<h5 style='color: #2563EB;'>₱{base_rate:,.2f} / day</h5>", unsafe_allow_html=True)
                                                
                                                # --- BOTTOM: POPOVER CHECKOUT MANAGER ---
                                                with st.popover(f"⚡ BOOK {car['model'].upper()} NOW", use_container_width=True):
                                                    stage_key = f"chk_stage_{car['id']}_{cat}_{tab_index}"
                                                    ref_key = f"pend_ref_{car['id']}_{cat}_{tab_index}"
                                                    if stage_key not in st.session_state: 
                                                        st.session_state[stage_key] = 0
                                                    
                                                    unavailable_dates = get_booked_dates(car['id'], conn)
                                                    
                                                    if unavailable_dates:
                                                        formatted_dates = ", ".join(sorted([d.strftime('%b %d') for d in unavailable_dates]))
                                                        # Read the renter's currently selected pickup/return dates so the calendar follows them
                                                        sel_d1 = st.session_state.get(f"d1_{car['id']}_{cat}_{tab_index}", datetime.date.today())
                                                        sel_d2 = st.session_state.get(f"d2_{car['id']}_{cat}_{tab_index}", sel_d1)
                                                        with st.expander(f"📅 Currently Booked On: {formatted_dates} (Click for Calendar)", expanded=False):
                                                            st.markdown(generate_booked_calendar_html(unavailable_dates, sel_d1, sel_d2), unsafe_allow_html=True)
                                                    
                                                    # --- STAGE 0: SELECT DATES & LOCATIONS ---
                                                    if st.session_state[stage_key] == 0:
                                                        today = datetime.date.today()
                                                        d1 = st.date_input("Pickup Date", min_value=today, key=f"d1_{car['id']}_{cat}_{tab_index}")
                                                        t1 = st.time_input("Pickup Time", value=datetime.time(9, 0), key=f"t1_{car['id']}_{cat}_{tab_index}")
                                                        d2 = st.date_input("Return Date", min_value=d1, value=d1, key=f"d2_{car['id']}_{cat}_{tab_index}")
                                                        t2 = st.time_input("Return Time", value=datetime.time(9, 0), key=f"t2_{car['id']}_{cat}_{tab_index}")
                                                        
                                                        pickup_loc_input = st.text_input(
                                                            "Pickup Location / Delivery Address (Leave blank for Base Pickup)",
                                                            value="",
                                                            placeholder="e.g., Ayala Malls Capitol Central, Bacolod City, Negros Occidental",
                                                            key=f"ploc_{car['id']}_{cat}_{tab_index}"
                                                        )
                                                        return_loc_input = st.text_input(
                                                            "Return Location / Drop-off Address (Leave blank for Base Return)",
                                                            value="",
                                                            placeholder="e.g., Lopues East, Villamonte, Bacolod City, Negros Occidental",
                                                            key=f"rloc_{car['id']}_{cat}_{tab_index}"
                                                        )
                                                        pickup_loc = pickup_loc_input.strip() if pickup_loc_input.strip() else parking_location
                                                        return_loc = return_loc_input.strip() if return_loc_input.strip() else parking_location
                                                        destination = st.text_input("Declared Trip Route / Destination", placeholder="e.g., Tagaytay or Subic", key=f"dest_{car['id']}_{cat}_{tab_index}")
                                                        
                                                        if st.button("PROCEED TO SUMMARY", key=f"btn_s0_{car['id']}_{cat}_{tab_index}", use_container_width=True):
                                                            requested_days = set()
                                                            delta = d2 - d1
                                                            for i in range(delta.days + 1):
                                                                requested_days.add(d1 + timedelta(days=i))
                                                            
                                                            overlapping = requested_days.intersection(unavailable_dates)
                                                            
                                                            if overlapping:
                                                                st.error("🚨 **Overlapping Schedule Detected!** The vehicle is already booked on your selected dates. Please adjust your schedule or look for an available similar vehicle.")
                                                            elif not destination.strip():
                                                                st.error("Please specify your trip route or destination.")
                                                            else:
                                                                # 🛡️ BULLETPROOF MEMORY: Pack everything into a single safe dictionary
                                                                st.session_state[f"safe_data_{car['id']}"] = {
                                                                    "d1": d1,
                                                                    "t1": t1,
                                                                    "d2": d2,
                                                                    "t2": t2,
                                                                    "ploc": pickup_loc,
                                                                    "rloc": return_loc,
                                                                    "dest": destination
                                                                }
                                                                
                                                                st.session_state[stage_key] = 1
                                                                st.rerun()

                                                    # --- STAGE 1: CONFIRMATION & DISTANCE APPROVAL ---
                                                    elif st.session_state[stage_key] == 1:
                                                        # Read directly from the saved Stage 0 dictionary
                                                        safe_data = st.session_state.get(f"safe_data_{car['id']}", {})
                                                    
                                                        s_d1 = safe_data.get("d1", datetime.date.today())
                                                        s_t1 = safe_data.get("t1", datetime.time(9, 0))
                                                        s_d2 = safe_data.get("d2", s_d1)
                                                        s_t2 = safe_data.get("t2", datetime.time(9, 0))
                                                        dest_val = safe_data.get("dest", "Not Specified")
                                                        pickup_address = safe_data.get("ploc", parking_location)
                                                        return_address = safe_data.get("rloc", parking_location)
                                                    
                                                        pickup_dt = datetime.datetime.combine(s_d1, s_t1)
                                                        return_dt = datetime.datetime.combine(s_d2, s_t2)
                                                        days_calc = max(1, (return_dt - pickup_dt).days)
                                                    
                                                        gross_rental = base_rate * days_calc
                                                        discount_pct = 0.0
                                                    
                                                        try:
                                                            disc_row = conn.execute(
                                                                "SELECT discount_pct FROM discount_tiers WHERE min_days <= ? ORDER BY min_days DESC LIMIT 1",
                                                                (days_calc,)
                                                            ).fetchone()
                                                            if disc_row:
                                                                raw_disc = float(disc_row[0])
                                                                discount_pct = raw_disc / 100.0 if raw_disc > 1.0 else raw_disc
                                                        except Exception:
                                                            discount_pct = 0.0
                                                    
                                                        discount_amount = gross_rental * discount_pct
                                                        net_rental = gross_rental - discount_amount
                                                    
                                                        # --- API ROUTING DELIVERY LEG CALCULATION ---
                                                        def get_leg_fee(addr, base_location):
                                                            if not addr:
                                                                return 0.0, "Base Pickup"
                                                        
                                                            clean_addr = addr.strip().lower()
                                                            clean_base = (base_location or "").strip().lower()
                                                        
                                                            if clean_base and clean_addr == clean_base:
                                                                return 0.0, "0.0 km (Base)"
                                                        
                                                            base_coords = get_gps_coordinates(base_location)
                                                            addr_coords = get_gps_coordinates(addr)
                                                        
                                                            # Fallback 1: If no city was typed and raw lookup failed, try appending garage city
                                                            if not addr_coords and "," not in addr and base_location and "," in base_location:
                                                                city_hint = base_location.split(",")[-1].strip()
                                                                addr_coords = get_gps_coordinates(f"{addr}, {city_hint}")
                                                        
                                                            # Fallback 2: If landmark wasn't found, retry using barangay/city after the first comma
                                                            if not addr_coords and "," in addr:
                                                                addr_coords = get_gps_coordinates(addr.split(",", 1)[1].strip())
                                                        
                                                            if base_coords and addr_coords:
                                                                dist_km = get_osrm_driving_distance(base_coords, addr_coords)
                                                                if dist_km is not None:
                                                                    return get_dynamic_delivery_fee(dist_km), f"{dist_km:.1f} km"
                                                        
                                                            return 350.0, "Est. Flat Rate"
                                                    
                                                        pickup_leg_fee, pickup_dist_lbl = get_leg_fee(pickup_address, parking_location)
                                                        return_leg_fee, return_dist_lbl = get_leg_fee(return_address, parking_location)
                                                        total_delivery_fee = pickup_leg_fee + return_leg_fee
                                                        total_online_bill = net_rental + total_delivery_fee
                                                    
                                                        # --- HTML EXCEL-STYLE TRIP LEDGER ---
                                                        st.write(f"### 📋 Trip Ledger: {car['make']} {car['model']}")
                                                        st.caption(f"📍 **Pickup:** {pickup_address} | 🛬 **Return:** {return_address}")
                                                    
                                                        ledger_html = f"""
                                                        <div style="overflow-x: auto; margin-bottom: 20px;">
                                                            <table style="width: 100%; border-collapse: collapse; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 14px; background-color: #FFFFFF; border: 1px solid #CBD5E1;">
                                                                <thead>
                                                                    <tr style="background-color: #F1F5F9; color: #1E293B; border-bottom: 2px solid #CBD5E1;">
                                                                        <th style="padding: 10px 14px; text-align: left; font-weight: 700; border-right: 1px solid #CBD5E1;">Cost Breakdown Item</th>
                                                                        <th style="padding: 10px 14px; text-align: right; font-weight: 700;">Amount (₱)</th>
                                                                    </tr>
                                                                </thead>
                                                                <tbody>
                                                                    <tr style="border-bottom: 1px solid #E2E8F0;">
                                                                        <td style="padding: 9px 14px; color: #334155; border-right: 1px solid #E2E8F0;"><b>Base Rental</b> (₱{base_rate:,.2f} × {days_calc} days)</td>
                                                                        <td style="padding: 9px 14px; text-align: right; color: #334155;">₱{gross_rental:,.2f}</td>
                                                                    </tr>
                                                                    <tr style="border-bottom: 1px solid #E2E8F0;">
                                                                        <td style="padding: 9px 14px; color: #334155; border-right: 1px solid #E2E8F0;"><b>Multi-Day Discount</b> ({discount_pct*100:.0f}%)</td>
                                                                        <td style="padding: 9px 14px; text-align: right; color: #16A34A;">- ₱{discount_amount:,.2f}</td>
                                                                    </tr>
                                                                    <tr style="border-bottom: 1px solid #E2E8F0;">
                                                                        <td style="padding: 9px 14px; color: #334155; border-right: 1px solid #E2E8F0;"><b>1st Leg (Pickup):</b> {pickup_address} <small style="color:#64748B;">({pickup_dist_lbl})</small></td>
                                                                        <td style="padding: 9px 14px; text-align: right; color: #334155;">₱{pickup_leg_fee:,.2f}</td>
                                                                    </tr>
                                                                    <tr style="border-bottom: 1px solid #E2E8F0;">
                                                                        <td style="padding: 9px 14px; color: #334155; border-right: 1px solid #E2E8F0;"><b>2nd Leg (Return):</b> {return_address} <small style="color:#64748B;">({return_dist_lbl})</small></td>
                                                                        <td style="padding: 9px 14px; text-align: right; color: #334155;">₱{return_leg_fee:,.2f}</td>
                                                                    </tr>
                                                                    <tr style="background-color: #F8FAFC; border-top: 2px solid #CBD5E1;">
                                                                        <td style="padding: 11px 14px; color: #0F172A; font-weight: 800; border-right: 1px solid #CBD5E1;">TOTAL ONLINE PAYMENT DUE</td>
                                                                        <td style="padding: 11px 14px; text-align: right; color: #2563EB; font-weight: 800; font-size: 15px;">₱{total_online_bill:,.2f}</td>
                                                                    </tr>
                                                                </tbody>
                                                            </table>
                                                        </div>
                                                        """
                                                        st.markdown(ledger_html, unsafe_allow_html=True)
                                                    
                                                        st.info("💵 **Security Deposit:** A refundable **₱5,000 cash deposit** is required, but it is **not** included in this online bill. It is paid directly in cash to the car host upon physical vehicle handover.")
                                                    
                                                        st.error(
                                                            "**🚨 STRICT PLATFORM RULES:**\n"
                                                            "- **No RoRo or Inter-island travel allowed.** Vehicles must remain strictly on the mainland.\n"
                                                            "- **RFID is required** if passing through Metro Manila or provincial tollways.\n"
                                                            "- The **₱5,000 security deposit** is mandatory. If your delivery locations change, incremental logistics fees will be deducted from this deposit."
                                                        )
                                                    
                                                        c_back_s1, c_sub_s1 = st.columns([1, 2])
                                                        if c_back_s1.button("⬅️ EDIT", key=f"back_s1_{car['id']}_{cat}_{tab_index}", use_container_width=True):
                                                            st.session_state[stage_key] = 0
                                                            st.rerun()
                                                    
                                                        if c_sub_s1.button("AGREE & SUBMIT FOR HOST APPROVAL", key=f"btn_s1_{car['id']}_{cat}_{tab_index}", type="primary", use_container_width=True):
                                                            booking_ref = str(random.randint(100000, 999999))
                                                    
                                                            conn.execute("""
                                                                INSERT INTO bookings (
                                                                    booking_ref, vehicle_id, renter_username, pickup_time, return_time,
                                                                    pickup_loc, return_loc, destination, delivery_fee, return_fee, amount, status
                                                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING_APPROVAL')
                                                            """, (
                                                                booking_ref,
                                                                car['id'],
                                                                st.session_state.username,
                                                                str(pickup_dt),
                                                                str(return_dt),
                                                                pickup_address,
                                                                return_address,
                                                                dest_val,
                                                                pickup_leg_fee,
                                                                return_leg_fee,
                                                                total_online_bill
                                                            ))
                                                            conn.commit()
                                                    
                                                            st.success(f"Booking request submitted! Ref #{booking_ref}. Awaiting host distance review.")
                                                            st.session_state[stage_key] = 0
                                                            time.sleep(1.5)
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
                # Filter into 3 clean groups
                to_approve_df = my_bookings[my_bookings['status'].isin(['PENDING_APPROVAL'])]
                approved_df   = my_bookings[my_bookings['status'].isin(['APPROVED_BY_HOST', 'PENDING', 'VERIFYING', 'CONFIRMED', 'ONGOING'])]
                completed_df  = my_bookings[my_bookings['status'].isin(['COMPLETED', 'CANCELLED', 'REJECTED'])]

                b_tabs = st.tabs([
                    f"⏳ To Be Approved ({len(to_approve_df)})",
                    f"✅ Approved & Active ({len(approved_df)})",
                    f"🏁 Completed ({len(completed_df)})"
                ])

                def render_renter_booking(b):
                    with st.container(border=True):
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            st.markdown(f"#### {b['make']} {b['model']} ({b['plate']})")
                            b_ref = b.get('booking_ref') if pd.notnull(b.get('booking_ref')) else f"DRV-{b['id']:05d}"
                            st.caption(f"Ref: #{b_ref} | Dates: {str(b['pickup_time'])[:10]} to {str(b['return_time'])[:10]}")
                        with c2:
                            st.info(b['status'])

                    # 🚨 DYNAMIC CHECK: Only show payment gateway when ready for payment
                        if b['status'] in ['APPROVED_BY_HOST', 'PENDING']:
                            st.markdown(f"**Amount Due:** ₱{float(b['amount']):,.2f}")

                            if gateway_mode == "XENDIT":
                                st.info("💳 Xendit Secure Gateway Active.")
                                dynamic_pay_url = b.get('pay_url') if 'pay_url' in b else None

                                if pd.notna(dynamic_pay_url) and str(dynamic_pay_url).strip():
                                    st.link_button("👉 PROCEED TO XENDIT SECURE CHECKOUT", str(dynamic_pay_url), type="primary", use_container_width=True)
                                else:
                                    if st.button("⚡ GENERATE XENDIT PAYMENT LINK", type="primary", use_container_width=True, key=f"gen_xen_{b['id']}"):
                                        with st.spinner("Connecting to Xendit..."):
                                            u_email_df = pd.read_sql_query("SELECT email FROM platform_users WHERE username=?", conn, params=(renter_user,))
                                            r_email = u_email_df.iloc[0]['email'] if not u_email_df.empty else None

                                            desc = f"DriveElite Rental Ref #{b_ref} ({b['make']} {b['model']})"
                                            inv_url, err = create_xendit_invoice(b_ref, float(b['amount']), desc, r_email)

                                            if inv_url:
                                                conn.execute("UPDATE bookings SET pay_url = ? WHERE id = ?", (inv_url, b['id']))
                                                conn.commit()
                                                st.rerun()
                                            else:
                                                st.error(f"Could not generate Xendit link: {err}")

                                st.warning("⚠️ **IMPORTANT:** After completing payment on Xendit, screenshot your confirmation page and upload it below for Admin verification.")
                            else:
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
                                    with open(receipt_path, "wb") as f:
                                        f.write(receipt_bytes)

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
                        
                        c_title, c_call = st.columns([3, 1])
                        with c_title:
                            st.markdown(f"#### 💬 Coordinate with Host (Ref: #{b['booking_ref']})")
                        with c_call:
                            try:
                                host_df = pd.read_sql_query("SELECT contact_number FROM platform_users WHERE username=?", conn, params=(b['owner_username'],))
                                if not host_df.empty and host_df.iloc[0]['contact_number']:
                                    host_phone = host_df.iloc[0]['contact_number']
                                    # ONLY shows the icon and label
                                    st.markdown(f'<a href="tel:{host_phone}"><button style="width:100%; background-color:#10B981; color:white; border:none; padding:8px 12px; border-radius:8px; font-weight:bold; cursor:pointer; margin-top:2px; box-shadow: 0 4px 6px rgba(16, 185, 129, 0.2);">📞 Call Host</button></a>', unsafe_allow_html=True)
                            except: pass
                            
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

                with b_tabs[0]:
                    if to_approve_df.empty:
                        st.info("No booking requests waiting for host approval.")
                    else:
                        for _, b in to_approve_df.iterrows():
                            render_renter_booking(b)

                with b_tabs[1]:
                    if approved_df.empty:
                        st.info("No approved or active trips right now.")
                    else:
                        for _, b in approved_df.iterrows():
                            render_renter_booking(b)

                with b_tabs[2]:
                    if completed_df.empty:
                        st.info("No completed trips yet.")
                    else:
                        for _, b in completed_df.iterrows():
                            render_renter_booking(b)

        except Exception as e:
            st.error(f"Could not load bookings: {e}")

if __name__ == "__main__":
    main()
