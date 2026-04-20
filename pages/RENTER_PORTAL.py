import streamlit as st
import pandas as pd
import datetime
import time
import random  
import os  
from database_utils import get_connection

# --- DATABASE CONNECTION ---
conn = get_connection()

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

# --- PAGE CONFIG ---
st.set_page_config(page_title="DriveElite Showroom", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); }
    .promo-banner { background: linear-gradient(90deg, #3244c4, #2c8c80); color: white; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 25px; }
    .bill-box { background-color: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #e0e0e0; margin-top: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .star-rating { color: #FFD700; font-size: 18px; }
</style>
""", unsafe_allow_html=True)

# --- 1. LOGIN FLOW ---
if not st.session_state.get('logged_in') or st.session_state.get('role') != 'RENTER':
    logo_col1, logo_col2, logo_col3 = st.columns([1, 2, 1])
    with logo_col2:
        try: st.image("logo.png", use_container_width=True)
        except: pass
    st.markdown("<h2 style='text-align: center;'>🚙 RENTER ACCESS</h2>", unsafe_allow_html=True)
    
    with st.form("login_renter"):
        st.info("💡 Log in with the Username and Password you created during registration.")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        
        if st.form_submit_button("LOGIN TO SHOWROOM", use_container_width=True):
            user = pd.read_sql_query("SELECT * FROM platform_users WHERE username=? AND password=? AND role='RENTER'", conn, params=(u, p))
            
            if not user.empty:
                if user.iloc[0]['admin_status'] == 'APPROVED':
                    st.session_state.logged_in, st.session_state.username, st.session_state.role = True, u, 'RENTER'
                    st.rerun()
                else: 
                    st.warning("⏳ Your account is still pending Admin approval.")
            else: 
                st.error("❌ Invalid credentials. Please check your username or password.")
    st.stop()

renter_user = st.session_state.username

# --- 2. HEADER ---
st.markdown("<h1 style='text-align: center;'>💼 RENTER COMMAND CENTER</h1>", unsafe_allow_html=True)
top_col_logo, top_col1, top_col2 = st.columns([1, 4, 1])
with top_col_logo:
    try: st.image("logo.png", use_container_width=True)
    except: pass
with top_col2:
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

    # HANDSHAKE QUERY: Must be Admin APPROVED and Affiliate AVAILABLE
    query = "SELECT * FROM vehicles WHERE admin_status = 'APPROVED' AND booking_status = 'AVAILABLE'"
    cars = pd.read_sql_query(query, conn)

    if cat_filter != "All": 
        cars = cars[cars['category'].str.strip() == cat_filter]
    if search_query: 
        cars = cars[cars['make'].str.contains(search_query, case=False) | cars['model'].str.contains(search_query, case=False)]

    if cars.empty:
        st.info("No vehicles currently live. (Wait for Admin to approve uploaded assets).")
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

                        with st.popover(f"⚡ BOOK {car['model'].upper()} NOW", use_container_width=True):
                            st.markdown("#### 📅 1. Choose Your Trip Dates")
                            c_date1, c_time1 = st.columns(2)
                            d1 = c_date1.date_input("Pickup Date", min_value=datetime.date.today(), key=f"d1_{car['id']}")
                            t1 = c_time1.time_input("Pickup Time", value=datetime.time(8, 0), key=f"t1_{car['id']}")

                            c_date2, c_time2 = st.columns(2)
                            d2 = c_date2.date_input("Return Date", min_value=d1, value=d1, key=f"d2_{car['id']}")
                            t2 = c_time2.time_input("Return Time", value=datetime.time(18, 0), key=f"t2_{car['id']}")

                            st.divider()
                            drive_mode = st.radio("Mode", ["Self-Drive", "With Driver (+₱1k/day)"], key=f"dm_{car['id']}")
                            is_driver = 1 if "Driver" in drive_mode else 0
                            dest = st.text_input("Destination", key=f"dest_{car['id']}")
                            luzon_agree = st.checkbox("I agree to LUZON ONLY.", key=f"luzon_{car['id']}")

                            st.markdown("#### 🚚 3. Logistics")
                            DELIVERY_ZONES = {"HQ: Kapitolyo, Pasig (Free)": 0.0, "Zone 1: Greenhills / Ortigas / BGC": 500.0, "Zone 2: Manila / QC / Pasay": 1000.0, "Zone 3: Alabang / Las Piñas / Parañaque": 1500.0}
                            p_zone = st.selectbox("Pickup Zone", list(DELIVERY_ZONES.keys()), key=f"pz_{car['id']}")
                            p_exact = st.text_input("Exact Pickup Address", key=f"pa_{car['id']}")
                            
                            days = (d2 - d1).days + 1
                            grand_total = (days * base_rate) + (days * 1000.0 if is_driver else 0) + DELIVERY_ZONES[p_zone]

                            st.metric("Total Amount", f"₱{grand_total:,.2f}")
                            ref_num = st.text_input("GCash Reference Number *", key=f"ref_{car['id']}")

                            if st.button("CONFIRM BOOKING", key=f"conf_{car['id']}", type="primary"):
                                if dest and ref_num and p_exact and luzon_agree:
                                    booking_ref = str(random.randint(100000, 999999))
                                    pickup_dt = f"{d1} {t1.strftime('%H:%M')}"
                                    return_dt = f"{d2} {t2.strftime('%H:%M')}"
                                    
                                    conn.execute("""
                                        INSERT INTO bookings (renter_username, vehicle_id, pickup_time, return_time, amount, status, destination, pickup_loc, return_loc, with_driver, booking_ref) 
                                        VALUES (?, ?, ?, ?, ?, 'CONFIRMED', ?, ?, ?, ?, ?)
                                    """, (renter_user, car['id'], pickup_dt, return_dt, grand_total, dest, p_exact, p_exact, is_driver, booking_ref))
                                    conn.commit()
                                    st.success(f"✅ Confirmed! Ref: #{booking_ref}")
                                    time.sleep(2)
                                    st.rerun()

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
        if active.empty: st.info("No active trips.")
        for _, t in active.iterrows():
            with st.expander(f"🚗 {t['make']} {t['model']} | {t['status']}"):
                st.write(f"**Ref:** #{t['booking_ref']} | **Total:** ₱{t['amount']:,.2f}")
                
                # --- CHAT SECTION ---
                st.markdown("#### 💬 Chat with Owner")
                b_ref = t['booking_ref']
                chat_win = st.container(height=200, border=True)
                with chat_win:
                    try:
                        history = pd.read_sql_query("SELECT * FROM chat_messages WHERE booking_ref = ? ORDER BY timestamp ASC", conn, params=(b_ref,))
                        for _, msg in history.iterrows():
                            role = "user" if msg['sender_username'] == st.session_state.username else "assistant"
                            with st.chat_message(role):
                                st.write(msg['message_text'])
                    except: st.caption("Starting chat...")

                c_img, c_msg = st.columns([1, 4])
                with c_img: r_img = st.file_uploader("📷", type=['jpg','png'], key=f"img_{b_ref}", label_visibility="collapsed")
                with c_msg: r_input = st.text_input("Message...", key=f"in_{b_ref}")

                if st.button("Send", key=f"btn_{b_ref}"):
                    if r_input or r_img:
                        path = save_chat_image(r_img, b_ref) if r_img else ""
                        conn.execute("INSERT INTO chat_messages (booking_ref, sender_username, receiver_username, message_text, image_path) VALUES (?, ?, ?, ?, ?)", (b_ref, st.session_state.username, t['owner_username'], r_input or "📸 Photo", path))
                        conn.commit()
                        st.rerun()

    with trip_tabs[1]:
        history = my_trips[my_trips['status'] == 'COMPLETED']
        if history.empty: st.info("No completed trips.")
        for _, t in history.iterrows():
            with st.expander(f"✅ {t['make']} {t['model']} | {str(t['pickup_time'])[:10]}"):
                st.write(f"**Final Cost:** ₱{t['amount']:,.2f}")
                
                # --- REVIEWS ---
                if not t.get('rating'):
                    with st.form(f"rev_{t['id']}"):
                        rate = st.slider("Rating", 1, 5, 5, key=f"s_{t['id']}")
                        rev = st.text_area("Review", key=f"t_{t['id']}")
                        if st.form_submit_button("Submit"):
                            conn.execute("UPDATE bookings SET rating = ?, review = ? WHERE id = ?", (rate, rev, t['id']))
                            conn.commit()
                            st.rerun()
                else:
                    st.success(f"Rated: {'⭐' * int(t['rating'])}")
