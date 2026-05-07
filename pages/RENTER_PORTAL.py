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

# --- AUTHENTICATION & PAGE CONFIG ---
st.set_page_config(page_title="DriveElite Renter Portal", layout="wide")

# ==========================================
# ☀️ LIGHT THEME & VISIBILITY ENGINE ☀️
# ==========================================
st.markdown("""
<style>
    /* 1. Main Backgrounds */
    [data-testid="stAppViewContainer"] { 
        background-color: #f8f9fa !important; 
        color: #212529 !important; 
    }
    [data-testid="stHeader"] { background-color: #f8f9fa !important; }
    [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #dee2e6; }

    /* 2. Fix Buttons & Popovers */
    div.stButton > button, 
    [data-testid="stFormSubmitButton"] > button,
    [data-testid="stPopover"] > button {
        background-color: #2c8c80 !important; 
        color: #ffffff !important;
        border: none !important;
        padding: 10px 20px !important;
        font-weight: bold !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
    }
    
    div.stButton > button:hover, 
    [data-testid="stFormSubmitButton"] > button:hover,
    [data-testid="stPopover"] > button:hover {
        background-color: #20685e !important;
        color: #ffffff !important;
    }
    
    div.stButton > button p, 
    [data-testid="stFormSubmitButton"] > button p,
    [data-testid="stPopover"] > button p {
        color: #ffffff !important;
    }

    /* 3. Global Typography */
    h1, h2, h3, h4, label { color: #212529 !important; font-weight: 700 !important; }
    p, .stMarkdown { color: #495057 !important; }
    
    /* Input field colors */
    div[data-baseweb="input"] > div, div[data-baseweb="select"] > div { 
        background-color: #ffffff !important; 
        border: 1px solid #ced4da !important; 
    }
    input { color: #212529 !important; }

    /* 4. The Receipt / Cost Breakdown Table */
    .bill-box { 
        background-color: #ffffff; 
        padding: 20px; 
        border-radius: 8px; 
        border: 1px solid #dee2e6; 
        margin-top: 10px; 
        color: #212529; 
    }
    .table-bill { width:100%; font-family: sans-serif; font-size: 1em; border-collapse: collapse; color: #212529; }
    .table-bill td { padding: 8px 0; border-bottom: 1px solid #f1f3f5; }
    .bill-label { font-weight: 600; color: #6c757d; }
</style>
""", unsafe_allow_html=True)

def render_availability_calendar(year, month, booked_dates_set):
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]
    
    html = f"""
    <style>
        .cal-table {{ width: 100%; text-align: center; border-collapse: collapse; margin-bottom: 15px; font-family: sans-serif; }}
        .cal-table th {{ background-color: #f1f3f5; padding: 8px; color: #2c8c80; font-size: 14px; border: 1px solid #dee2e6; }}
        .cal-table td {{ padding: 10px; border: 1px solid #dee2e6; font-size: 14px; width: 14.28%; }}
        .available-day {{ background-color: #ffffff; color: #212529; font-weight: bold; }}
        .booked-day {{ background-color: #ffe3e3; color: #e03131; text-decoration: line-through; opacity: 0.7; }}
        .empty-day {{ background-color: #f8f9fa; border: 1px solid #f8f9fa; }}
    </style>
    <table class="cal-table">
        <tr><th colspan="7" style="font-size: 16px; color: #212529;">📅 {month_name} {year} Availability</th></tr>
        <tr><th>Mon</th><th>Tue</th><th>Wed</th><th>Thu</th><th>Fri</th><th>Sat</th><th>Sun</th></tr>
    """
    for week in cal:
        html += "<tr>"
        for day in week:
            if day == 0:
                html += "<td class='empty-day'></td>"
            else:
                date_str = f"{year}-{month:02d}-{day:02d}"
                if date_str in booked_dates_set:
                    html += f"<td class='booked-day'>{day}</td>"
                else:
                    html += f"<td class='available-day'>{day}</td>"
        html += "</tr>"
    html += "</table>"
    return html

# --- DATABASE CONNECTION ---
conn = get_connection()

# --- CHAT INPUT RESET LOGIC ---
if "temp_msg_renter" not in st.session_state:
    st.session_state.temp_msg_renter = ""

def get_booked_dates(vehicle_id, conn):
    query = "SELECT pickup_time, return_time FROM bookings WHERE vehicle_id = ? AND status IN ('CONFIRMED', 'ONGOING', 'PENDING')"
    df = pd.read_sql_query(query, conn, params=(vehicle_id,))
    booked_days = set()
    for _, row in df.iterrows():
        try:
            start = pd.to_datetime(row['pickup_time']).date()
            end = pd.to_datetime(row['return_time']).date()
            delta = end - start
            for i in range(delta.days + 1):
                booked_days.add(start + datetime.timedelta(days=i))
        except Exception: pass
    return booked_days

def calculate_24h_rental(pickup_dt, return_dt, daily_rate, hourly_late_fee=300.0, grace_mins=59):
    diff = return_dt - pickup_dt
    total_seconds = diff.total_seconds()
    if total_seconds <= 86400: return 1, 0, daily_rate, 0.0, daily_rate
    full_days = int(total_seconds // 86400)
    remainder_mins = (total_seconds % 86400) / 60.0
    billed_hours, hourly_fee_total = 0, 0.0
    if remainder_mins > grace_mins:
        billed_hours = math.ceil(remainder_mins / 60.0)
        hourly_fee_total = billed_hours * hourly_late_fee
        if hourly_fee_total >= daily_rate:
            full_days += 1
            billed_hours, hourly_fee_total = 0, 0.0
    base_cost = full_days * daily_rate
    return full_days, billed_hours, base_cost, hourly_fee_total, base_cost + hourly_fee_total

# --- 1. AUTHENTICATION ---
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
    cars = pd.read_sql_query("SELECT * FROM vehicles WHERE admin_status = 'APPROVED' AND booking_status = 'AVAILABLE'", conn)
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
                        st.write(f"### {car['make']} {car['model']}")
                        base_rate = car.get('approved_price', 2000.0)
                        
                        with st.popover(f"⚡ BOOK {car['model'].upper()} NOW", use_container_width=True):
                            unavailable_dates = get_booked_dates(car['id'], conn)
                            existing_bookings = pd.read_sql_query("SELECT pickup_time, return_time FROM bookings WHERE vehicle_id = ? AND status NOT IN ('CANCELLED', 'REJECTED')", conn, params=(car['id'],))
                            booked_dates = set()
                            for _, row in existing_bookings.iterrows():
                                try:
                                    start_dt = pd.to_datetime(row['pickup_time']).date()
                                    end_dt = pd.to_datetime(row['return_time']).date()
                                    delta = end_dt - start_dt
                                    for idx in range(delta.days + 1):
                                        booked_dates.add((start_dt + datetime.timedelta(days=idx)).strftime("%Y-%m-%d"))
                                except: pass

                            today = datetime.date.today()
                            st.markdown(render_availability_calendar(today.year, today.month, booked_dates), unsafe_allow_html=True)
                            
                            d1 = st.date_input("Pickup Date", min_value=datetime.date.today(), key=f"d1_{car['id']}")
                            t1 = st.time_input("Pickup Time", value=datetime.time(9, 0), key=f"t1_{car['id']}")
                            d2 = st.date_input("Return Date", min_value=d1, value=d1, key=f"d2_{car['id']}")
                            t2 = st.time_input("Return Time", value=datetime.time(9, 0), key=f"t2_{car['id']}")
                            
                            can_book = True
                            p_dt_obj, r_dt_obj = datetime.datetime.combine(d1, t1), datetime.datetime.combine(d2, t2)
                            
                            if r_dt_obj <= p_dt_obj: 
                                can_book = False
                                st.error("⚠️ Return must be after pickup.")
                            else:
                                full_days, billed_hrs, base_cost, ext_fee, subtotal = calculate_24h_rental(p_dt_obj, r_dt_obj, base_rate)
                                grand_total = subtotal + (subtotal * 0.07 if full_days >= 4 else 0)

                                if st.button("CONFIRM BOOKING", key=f"conf_{car['id']}", type="primary", use_container_width=True, disabled=not can_book):
                                    b_ref = str(random.randint(100000, 999999))
                                    conn.execute("INSERT INTO bookings (renter_username, vehicle_id, pickup_time, return_time, amount, status, booking_ref) VALUES (?, ?, ?, ?, ?, 'PENDING', ?)", 
                                                 (renter_user, car['id'], p_dt_obj.strftime("%Y-%m-%d %H:%M"), r_dt_obj.strftime("%Y-%m-%d %H:%M"), grand_total, b_ref))
                                    conn.commit()
                                    st.success(f"✅ Booking Saved (Ref: #{b_ref})")

# --- TAB 1: MY BOOKINGS (With RESTORED STAR RATING) ---
with tabs[1]:
    my_trips = pd.read_sql_query("SELECT b.*, v.make, v.model FROM bookings b JOIN vehicles v ON b.vehicle_id = v.id WHERE b.renter_username = ? ORDER BY b.pickup_time DESC", conn, params=(renter_user,))
    
    active_trips = my_trips[my_trips['status'] != 'COMPLETED']
    history_trips = my_trips[my_trips['status'] == 'COMPLETED']

    st.subheader("🚀 Active Trips")
    if active_trips.empty: st.info("No active bookings.")
    for _, t in active_trips.iterrows():
        with st.expander(f"🚗 {t['make']} {t['model']} | {t['status']}"):
            st.write(f"Ref: #{t['booking_ref']} | Pickup: {t['pickup_time']}")

    st.divider()
    st.subheader("📜 Trip History & Reviews")
    if history_trips.empty: st.info("No completed trips.")
    for _, t in history_trips.iterrows():
        with st.expander(f"✅ COMPLETED: {t['make']} {t['model']} | {str(t['pickup_time'])[:10]}"):
            # Check if already rated
            if pd.isna(t.get('rating')) or t.get('rating') == "":
                with st.container(border=True):
                    st.markdown("#### ⭐ Rate Your Experience")
                    # RESTORED STAR RATING SYSTEM
                    stars = st.feedback("stars", key=f"stars_{t['id']}")
                    review_text = st.text_area("Write a short review (optional)", key=f"rev_{t['id']}")
                    
                    if st.button("Submit Review", key=f"sub_rev_{t['id']}", type="primary"):
                        if stars is not None:
                            # st.feedback returns 0-4, so we add 1 to make it 1-5 stars
                            actual_rating = stars + 1
                            conn.execute("UPDATE bookings SET rating = ?, review = ? WHERE id = ?", (actual_rating, review_text, t['id']))
                            conn.commit()
                            st.success("Thank you for your feedback!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Please select a star rating first.")
            else:
                rating_val = int(float(t['rating']))
                st.success(f"You rated this trip: {'⭐' * rating_val}")
                if t.get('review'):
                    st.info(f"Your Review: {t['review']}")
