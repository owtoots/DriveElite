import streamlit as st
import pandas as pd
import datetime
import time
import random  
import os  
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

# --- PAGE CONFIG ---
st.set_page_config(page_title="DriveElite Showroom", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); }
    /* DARKER FONT STYLING FOR THE BILL */
    .bill-box { 
        background-color: #ffffff; 
        padding: 20px; 
        border-radius: 10px; 
        border: 2px solid #333333; 
        margin-top: 10px; 
        box-shadow: 4px 4px 10px rgba(0,0,0,0.1); 
        color: #1a1a1a; /* High contrast dark font */
    }
    .table-bill { 
        width:100%; 
        font-family: 'Courier New', Courier, monospace; 
        font-size: 1.05em; 
        border-collapse: collapse; 
        color: #1a1a1a; /* Ensuring all text inside is dark */
    }
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
        st.info("No vehicles currently approved and available.")
    else:
        grid_cols = st.columns(2)
        for i, car in cars.reset_index(drop=True).iterrows():
            with grid_cols[i % 2]:
                with st.container(border=True):
                    col1, col2 = st.columns([1, 1.3])
                    with col1:
                        img_path = car.get('vehicle_img')
                        if img_path and os.path.exists(img_path):
                            st.image(img_path, use_container_width=True)
                        else:
                            st.image("https://placehold.co/600x400?text=No+Image", use_container_width=True)

                    with col2:
                        st.write(f"### {car['make']} {car['model']} ({car['year']})")
                        base_rate = car.get('approved_price', 2000.0)
                        st.write(f"**Standard Rate:** ₱{base_rate:,.2f} / day")

                        with st.popover(f"⚡ BOOK {car['model'].upper()} NOW", use_container_width=True):
                            st.markdown("#### 📅 1. Choose Trip Dates")
                            c_d1, c_t1 = st.columns(2)
                            d1 = c_d1.date_input("Pickup Date", min_value=datetime.date.today(), key=f"d1_{car['id']}")
                            t1 = c_t1.time_input("Pickup Time", value=datetime.time(8, 0), key=f"t1_{car['id']}")
                            
                            c_d2, c_t2 = st.columns(2)
                            d2 = c_d2.date_input("Return Date", min_value=d1, value=d1, key=f"d2_{car['id']}")
                            t2 = c_t2.time_input("Return Time", value=datetime.time(18, 0), key=f"t2_{car['id']}")

                            st.divider()
                            st.markdown("#### 📍 2. Trip Details")
                            drive_mode = st.radio("Mode", ["Self-Drive", "With Driver (+₱1k/day)"], key=f"dm_{car['id']}")
                            is_driver = 1 if "Driver" in drive_mode else 0
                            dest = st.text_input("Destination", key=f"dest_{car['id']}")
                            luzon_agree = st.checkbox("I agree to LUZON ONLY travel.", key=f"luzon_{car['id']}")

                            st.markdown("#### 🚚 3. Logistics")
                            DELIVERY_ZONES = {
                                "HQ: Kapitolyo, Pasig (Free)": 0.0,
                                "Zone 1: Greenhills / Ortigas / BGC": 500.0,
                                "Zone 2: Manila / QC / Pasay": 1000.0,
                                "Zone 3: Alabang / Las Piñas / Parañaque": 1500.0
                            }
                            c_loc1, c_loc2 = st.columns(2)
                            p_zone = c_loc1.selectbox("Pickup Zone", list(DELIVERY_ZONES.keys()), key=f"pz_{car['id']}")
                            p_exact = c_loc1.text_input("Exact Pickup Address", key=f"pa_{car['id']}")
                            r_zone = c_loc2.selectbox("Return Zone", list(DELIVERY_ZONES.keys()), key=f"rz_{car['id']}")
                            r_exact = c_loc2.text_input("Exact Return Address", key=f"ra_{car['id']}")

                            # --- EXCEL-STYLE MATH ENGINE ---
                            days = max(1, (d2 - d1).days + 1)
                            subtotal = days * base_rate
                            driver_fee = (days * 1000.0) if is_driver else 0.0
                            d_fee = DELIVERY_ZONES[p_zone]
                            c_fee = DELIVERY_ZONES[r_zone]
                            
                            discount_pct = 0.0
                            if days >= 15: discount_pct = 0.15
                            elif days >= 7: discount_pct = 0.10
                            elif days >= 3: discount_pct = 0.05
                            savings = subtotal * discount_pct
                            
                            grand_total = (subtotal - savings) + driver_fee + d_fee + c_fee

                            # --- THE DARK-FONT EXCEL BILL ---
                            st.markdown("#### 🧾 4. Cost Breakdown")
                            bill_html = f'''
                            <div class="bill-box">
                                <table class="table-bill">
                                    <tr><td class="bill-label">Base Rental (₱{base_rate:,.2f} x {days} days)</td><td style="text-align:right; font-weight:bold;">₱{subtotal:,.2f}</td></tr>
                                    {f'<tr><td style="color:#cc0000; font-style:italic;">Tiered Discount ({int(discount_pct*100)}%)</td><td style="text-align:right; color:#cc0000;">-₱{savings:,.2f}</td></tr>' if savings > 0 else ""}
                                    {f'<tr><td style="color:#003399;">Professional Driver Fee</td><td style="text-align:right; color:#003399;">+₱{driver_fee:,.2f}</td></tr>' if is_driver else ""}
                                    {f'<tr><td style="color:#e67e22;">Delivery Fee ({p_zone.split(":")[0]})</td><td style="text-align:right; color:#e67e22;">+₱{d_fee:,.2f}</td></tr>' if d_fee > 0 else ""}
                                    {f'<tr><td style="color:#e67e22;">Collection Fee ({r_zone.split(":")[0]})</td><td style="text-align:right; color:#e67e22;">+₱{c_fee:,.2f}</td></tr>' if c_fee > 0 else ""}
                                    <tr style="border-top:2px solid #000; font-size:1.15em;"><td class="bill-label" style="padding-top:10px;">GRAND TOTAL (TO PAY)</td><td style="text-align:right; padding-top:10px; font-weight:900; color:#000000;">₱{grand_total:,.2f}</td></tr>
                                    <tr style="color:#006600; font-size:0.9em; font-style:italic;"><td>Refundable Cash Deposit (Pay on Handover)</td><td style="text-align:right;">₱5,000.00</td></tr>
                                </table>
                            </div>
                            '''
                            st.markdown(bill_html, unsafe_allow_html=True)
                            
                            # --- 💳 5. PAYMENT & QR CODE ---
                            st.divider()
                            st.markdown("#### 💳 5. Payment")
                            qr_path = "gcash_qr.jpg" 
                            if os.path.exists(qr_path):
                                st.image(qr_path, caption=f"Scan to Pay: ₱{grand_total:,.2f}", width=300)
                            else:
                                st.warning("⚠️ **QR Code Missing:** Upload 'gcash_qr.jpg' to GitHub.")
                            
                            st.divider()
                            ref_num = st.text_input("GCash Reference Number *", key=f"ref_{car['id']}")

                            if st.button("CONFIRM BOOKING", key=f"conf_{car['id']}", type="primary", use_container_width=True):
                                if dest and ref_num and p_exact and r_exact and luzon_agree:
                                    b_ref = str(random.randint(100000, 999999))
                                    p_dt = f"{d1} {t1.strftime('%H:%M')}"
                                    r_dt = f"{d2} {t2.strftime('%H:%M')}"
                                    p_full = f"{p_zone}: {p_exact}"
                                    r_full = f"{r_zone}: {r_exact}"
                                    
                                    conn.execute("""
                                        INSERT INTO bookings (renter_username, vehicle_id, pickup_time, return_time, amount, status, destination, pickup_loc, return_loc, with_driver, booking_ref) 
                                        VALUES (?, ?, ?, ?, ?, 'CONFIRMED', ?, ?, ?, ?, ?)
                                    """, (renter_user, car['id'], p_dt, r_dt, grand_total, dest, p_full, r_full, is_driver, b_ref))
                                    conn.commit()
                                    st.success(f"✅ Booking Confirmed! Reference: #{b_ref}")
                                    time.sleep(2)
                                    st.rerun()
                                else:
                                    st.warning("⚠️ Please fill all required fields and check the agreement.")

# --- TAB 1: MY BOOKINGS ---
with tabs[1]:
    trip_tabs = st.tabs(["🚀 Active Trips", "📜 Trip History"])
    
    my_trips = pd.read_sql_query("""
        SELECT b.*, v.make, v.model, v.plate, v.owner_username 
        FROM bookings b 
        JOIN vehicles v ON b.vehicle_id = v.id 
        WHERE b.renter_username = ? ORDER BY b.pickup_time DESC
    """, conn, params=(renter_user,))
    
    with trip_tabs[0]:
        active = my_trips[my_trips['status'].isin(['CONFIRMED', 'ONGOING', 'PENDING'])]
        if active.empty:
            st.info("No active trips. Visit the Showroom to book your next ride!")
        else:
            for _, t in active.iterrows():
                with st.expander(f"🚗 {t['make']} {t['model']} ({t['plate']}) | {t['status']}"):
                    st.write(f"**Booking Ref:** #{t['booking_ref']}")
                    st.write(f"**Total Paid:** ₱{t['amount']:,.2f}")
                    st.write(f"**Schedule:** {t['pickup_time']} to {t['return_time']}")
                    
                    # --- MESSENGER ---
                    st.divider()
                    st.markdown("#### 💬 Message the Owner")
                    b_ref = t['booking_ref']
                    chat_box = st.container(height=200, border=True)
                    with chat_box:
                        try:
                            msgs = pd.read_sql_query("SELECT * FROM chat_messages WHERE booking_ref = ? ORDER BY timestamp ASC", conn, params=(b_ref,))
                            if msgs.empty: 
                                st.caption("No messages yet.")
                            for _, m in msgs.iterrows():
                                role = "user" if m['sender_username'] == st.session_state.username else "assistant"
                                with st.chat_message(role):
                                    st.write(m['message_text'])
                                    if m['image_path'] and os.path.exists(m['image_path']):
                                        st.image(m['image_path'], width=200)
                        except: st.caption("Chat system initializing...")

                    c_img, c_msg = st.columns([1, 4])
                    with c_img: r_img = st.file_uploader("📷", type=['jpg','png'], key=f"img_{b_ref}", label_visibility="collapsed")
                    with c_msg: r_input = st.text_input("Reply...", key=f"txt_{b_ref}")

                    if st.button("Send Message", key=f"btn_{b_ref}", use_container_width=True):
                        if r_input or r_img:
                            path = save_chat_image(r_img, b_ref) if r_img else ""
                            conn.execute("INSERT INTO chat_messages (booking_ref, sender_username, receiver_username, message_text, image_path) VALUES (?, ?, ?, ?, ?)", (b_ref, st.session_state.username, t['owner_username'], r_input or "📸 Photo Attachment", path))
                            conn.commit()
                            st.rerun()

    with trip_tabs[1]:
        history = my_trips[my_trips['status'] == 'COMPLETED']
        if history.empty:
            st.info("Your trip history will appear here once journeys are completed.")
        else:
            for _, t in history.iterrows():
                with st.expander(f"✅ COMPLETED: {t['make']} {t['model']} | {str(t['pickup_time'])[:10]}"):
                    st.write(f"**Final Cost:** ₱{t['amount']:,.2f}")
                    
                    if not t.get('rating'):
                        st.markdown("### ⭐ Rate Your Trip")
                        with st.form(f"rev_{t['id']}"):
                            s = st.slider("Rating", 1, 5, 5, key=f"s_{t['id']}")
                            r = st.text_area("How was the car and service?", key=f"r_{t['id']}")
                            if st.form_submit_button("Submit Review"):
                                conn.execute("UPDATE bookings SET rating = ?, review = ? WHERE id = ?", (s, r, t['id']))
                                conn.commit()
                                st.success("Thank you!")
                                time.sleep(1)
                                st
