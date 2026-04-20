import streamlit as st
import pandas as pd
import datetime
import time
import random
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from database_utils import get_connection

# --- DATABASE CONNECTION ---
conn = get_connection()

# --- UTILITIES ---
def save_chat_image(uploaded_file, booking_ref):
    """Saves chat images to a dedicated directory."""
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

def send_booking_confirmation_email(to_email, renter_name, car_display, b_ref, p_dt, r_dt, html_bill):
    """Sends a professional HTML receipt to the renter."""
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

# --- 3. MAIN TABS ---
tabs = st.tabs(["🌟 VEHICLE SHOWROOM", "📅 MY BOOKINGS"])

# --- TAB 0: VEHICLE SHOWROOM ---
with tabs[0]:
    try:
        cat_df = pd.read_sql_query("SELECT name FROM vehicle_categories", conn)
        cat_list = ["All"] + [str(n).strip() for n in cat_df['name'].tolist()]
    except: 
        cat_list = ["All", "Sedan", "SUV", "Van"]
    
    c_f1, c_f2 = st.columns([2, 1])
    cat_filter = c_f1.selectbox("Filter by Category", cat_list)
    search_query = c_f2.text_input("Search Brand/Model", placeholder="e.g. Nissan")

    query = "SELECT * FROM vehicles WHERE admin_status = 'APPROVED' AND booking_status = 'AVAILABLE'"
    cars = pd.read_sql_query(query, conn)

    if cat_filter != "All": 
        cars = cars[cars['category'].str.strip() == cat_filter]
    if search_query: 
        cars = cars[cars['make'].str.contains(search_query, case=False) | cars['model'].str.contains(search_query, case=False)]

    if cars.empty:
        st.info("No vehicles currently live.")
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
                            # --- 1. TRIP DATES ---
                            st.markdown("#### 📅 1. Choose Trip Dates")
                            c_d1, c_t1 = st.columns(2)
                            d1 = c_d1.date_input("Pickup Date", min_value=datetime.date.today(), key=f"d1_{car['id']}")
                            t1 = c_t1.time_input("Pickup Time", value=datetime.time(8, 0), key=f"t1_{car['id']}")
                            c_d2, c_t2 = st.columns(2)
                            d2 = c_d2.date_input("Return Date", min_value=d1, value=d1, key=f"d2_{car['id']}")
                            t2 = c_t2.time_input("Return Time", value=datetime.time(18, 0), key=f"t2_{car['id']}")

                            st.divider()
                            # --- 2. DETAILS ---
                            st.markdown("#### 📍 2. Trip Details")
                            drive_mode = st.radio("Mode", ["Self-Drive", "With Driver (+₱1k/day)"], key=f"dm_{car['id']}")
                            is_driver = 1 if "Driver" in drive_mode else 0
                            dest = st.text_input("Destination", key=f"dest_{car['id']}")
                            luzon_agree = st.checkbox("I agree to LUZON ONLY travel.", key=f"luzon_{car['id']}")

                            # --- 3. LOGISTICS ---
                            st.markdown("#### 🚚 3. Logistics")
                            ZONES = {"HQ: Pasig (Free)": 0.0, "Zone 1: Ortigas/BGC": 500.0, "Zone 2: Manila/QC": 1000.0, "Zone 3: Alabang/LP": 1500.0}
                            c_loc1, c_loc2 = st.columns(2)
                            p_zone = c_loc1.selectbox("Pickup Zone", list(ZONES.keys()), key=f"pz_{car['id']}")
                            p_exact = c_loc1.text_input("Pickup Address", key=f"pa_{car['id']}")
                            r_zone = c_loc2.selectbox("Return Zone", list(ZONES.keys()), key=f"rz_{car['id']}")
                            r_exact = c_loc2.text_input("Return Address", key=f"ra_{car['id']}")

                           # --- 4. PRO 24-HOUR CALCULATION ENGINE ---
                            # Combine the separate dates and times into exact datetime objects
                            p_dt_obj = datetime.datetime.combine(d1, t1)
                            r_dt_obj = datetime.datetime.combine(d2, t2)
                            
                            if r_dt_obj <= p_dt_obj:
                                st.error("⚠️ Return time must be strictly after the pickup time.")
                            else:
                                # Run the 24-hour math! (Defaults to Php 300/hr late fee)
                                full_days, billed_hrs, base_cost, ext_fee, subtotal = calculate_24h_rental(p_dt_obj, r_dt_obj, base_rate, 300.0, 59)
                                
                                # Driver is paid per day touching the road
                                driver_days = full_days + (1 if billed_hrs > 0 else 0)
                                driver_fee = (driver_days * 1000.0) if is_driver else 0.0
                                
                                d_fee = ZONES[p_zone]
                                c_fee = ZONES[r_zone]
                                
                                discount_pct = 0.15 if full_days >= 15 else (0.10 if full_days >= 7 else (0.05 if full_days >= 3 else 0.0))
                                savings = subtotal * discount_pct
                                grand_total = (subtotal - savings) + driver_fee + d_fee + c_fee

                                st.markdown("#### 🧾 4. Cost Breakdown")
                                # Build HTML rows (Now includes Hourly Extensions!)
                                plural_days = "day" if full_days == 1 else "days"
                                rows = [f'<tr><td class="bill-label">Base Rental (₱{base_rate:,.2f} x {full_days} {plural_days})</td><td style="text-align:right; font-weight:bold;">₱{base_cost:,.2f}</td></tr>']
                                
                                if billed_hrs > 0: 
                                    rows.append(f'<tr><td style="color:#d35400; font-style:italic;">Hourly Extension ({billed_hrs} hrs @ ₱300/hr)</td><td style="text-align:right; color:#d35400;">+₱{ext_fee:,.2f}</td></tr>')
                                if savings > 0: 
                                    rows.append(f'<tr><td style="color:#cc0000; font-style:italic;">Tiered Discount ({int(discount_pct*100)}%)</td><td style="text-align:right; color:#cc0000;">-₱{savings:,.2f}</td></tr>')
                                if is_driver: 
                                    rows.append(f'<tr><td style="color:#003399;">Driver Fee ({driver_days} days)</td><td style="text-align:right; color:#003399;">+₱{driver_fee:,.2f}</td></tr>')
                                if d_fee > 0: 
                                    rows.append(f'<tr><td style="color:#e67e22;">Delivery Fee</td><td style="text-align:right; color:#e67e22;">+₱{d_fee:,.2f}</td></tr>')
                                if c_fee > 0: 
                                    rows.append(f'<tr><td style="color:#e67e22;">Collection Fee</td><td style="text-align:right; color:#e67e22;">+₱{c_fee:,.2f}</td></tr>')
                                
                                bill_content = "".join(rows)
                                bill_html = f'<div class="bill-box"><table class="table-bill">{bill_content}<tr style="border-top:2px solid #000; font-size:1.1em;"><td class="bill-label">GRAND TOTAL</td><td style="text-align:right; font-weight:900;">₱{grand_total:,.2f}</td></tr><tr><td style="color:#006600; font-size:0.9em; font-style:italic;">Security Deposit (Cash)</td><td style="text-align:right;">₱5,000.00</td></tr></table></div>'
                                st.markdown(bill_html, unsafe_allow_html=True)
                                
                                # ... Keep your existing Payment and "Confirm Booking" button below this ...
                            
                            # --- 5. PAYMENT & EMAIL FIRING ---
                            st.divider()
                            st.markdown("#### 💳 5. Payment")
                            qr_p = "gcash_qr.jpg" 
                            if os.path.exists(qr_p): st.image(qr_p, caption=f"Scan to Pay: ₱{grand_total:,.2f}", width=300)
                            
                            ref_num = st.text_input("GCash Reference Number *", key=f"ref_{car['id']}")

                            if st.button("CONFIRM BOOKING", key=f"conf_{car['id']}", type="primary", use_container_width=True):
                                if dest and ref_num and p_exact and r_exact and luzon_agree:
                                    b_ref = str(random.randint(100000, 999999))
                                    p_dt_str = f"{d1} {t1.strftime('%H:%M')}"
                                    r_dt_str = f"{d2} {t2.strftime('%H:%M')}"
                                    
                                    conn.execute("INSERT INTO bookings (renter_username, vehicle_id, pickup_time, return_time, amount, status, destination, pickup_loc, return_loc, with_driver, booking_ref) VALUES (?, ?, ?, ?, ?, 'CONFIRMED', ?, ?, ?, ?, ?)", 
                                                 (renter_user, car['id'], p_dt_str, r_dt_str, grand_total, dest, f"{p_zone}: {p_exact}", f"{r_zone}: {r_exact}", is_driver, b_ref))
                                    conn.commit()
                                    
                                    # FETCH EMAIL & SEND RECEIPT
                                    r_info = pd.read_sql_query("SELECT email, full_name FROM platform_users WHERE username=?", conn, params=(renter_user,))
                                    if not r_info.empty and r_info.iloc[0]['email']:
                                        r_email = r_info.iloc[0]['email']
                                        r_name = r_info.iloc[0]['full_name']
                                        car_display = f"{car['make']} {car['model']} ({car['plate']})"
                                        
                                        send_booking_confirmation_email(r_email, r_name, car_display, b_ref, p_dt_str, r_dt_str, bill_html)
                                        st.toast("📧 Official receipt sent to your email!", icon="✅")
                                    
                                    st.success(f"✅ Confirmed! Ref: #{b_ref}")
                                    time.sleep(2)
                                    st.rerun()
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
                st.write(f"**Booking Ref:** #{t['booking_ref']} | **Total:** ₱{t['amount']:,.2f}")
                st.write(f"**Pickup:** {t['pickup_time']} | **Return:** {t['return_time']}")
                
                # --- CHAT ---
                st.divider()
                st.markdown("#### 💬 Message the Owner")
                b_ref = t['booking_ref']
                chat_box = st.container(height=200, border=True)
                with chat_box:
                    try:
                        msgs = pd.read_sql_query("SELECT * FROM chat_messages WHERE booking_ref = ? ORDER BY timestamp ASC", conn, params=(b_ref,))
                        for _, m in msgs.iterrows():
                            role = "user" if m['sender_username'] == st.session_state.username else "assistant"
                            with st.chat_message(role):
                                st.write(m['message_text'])
                                if m['image_path'] and os.path.exists(m['image_path']): st.image(m['image_path'], width=200)
                    except: st.caption("No messages yet.")

                c_i, c_t = st.columns([1, 4])
                with c_i: r_img = st.file_uploader("📷", type=['jpg','png'], key=f"img_{b_ref}", label_visibility="collapsed")
                with c_t: r_txt = st.text_input("Reply...", key=f"txt_{b_ref}")

                if st.button("Send Message", key=f"btn_{b_ref}", use_container_width=True):
                    if r_txt or r_img:
                        path = save_chat_image(r_img, b_ref) if r_img else ""
                        conn.execute("INSERT INTO chat_messages (booking_ref, sender_username, receiver_username, message_text, image_path) VALUES (?, ?, ?, ?, ?)", (b_ref, st.session_state.username, t['owner_username'], r_txt or "📸 Photo", path))
                        conn.commit()
                        st.rerun()

    with trip_tabs[1]:
        history = my_trips[my_trips['status'] == 'COMPLETED']
        if history.empty: st.info("No completed trips.")
        for _, t in history.iterrows():
            with st.expander(f"✅ COMPLETED: {t['make']} {t['model']} | {str(t['pickup_time'])[:10]}"):
                st.write(f"**Final Cost:** ₱{t['amount']:,.2f}")
                if not t.get('rating'):
                    with st.form(f"rev_{t['id']}"):
                        s = st.slider("Rating", 1, 5, 5, key=f"s_{t['id']}")
                        r = st.text_area("Review", key=f"r_{t['id']}")
                        if st.form_submit_button("Submit Review"):
                            conn.execute("UPDATE bookings SET rating = ?, review = ? WHERE id = ?", (s, r, t['id']))
                            conn.commit()
                            st.rerun()
                else:
                    st.success(f"**Rating:** {'⭐' * int(t['rating'])}")
