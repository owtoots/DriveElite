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
            # COORDINATED: Changed 'users' to 'platform_users'
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

    query = "SELECT * FROM vehicles WHERE admin_status = 'APPROVED' AND booking_status = 'AVAILABLE'"
    cars = pd.read_sql_query(query, conn)

    if cat_filter != "All": 
        cars = cars[cars['category'].str.strip() == cat_filter]
    if search_query: 
        cars = cars[cars['make'].str.contains(search_query, case=False) | cars['model'].str.contains(search_query, case=False)]

    if cars.empty:
        st.info("No vehicles currently matching your search.")
    else:
        grid_cols = st.columns(2)
        for i, car in cars.reset_index(drop=True).iterrows():
            with grid_cols[i % 2]:
                with st.container(border=True):
                    col1, col2 = st.columns([1, 1.3])
                    with col1:
                        img_col = car.get('vehicle_img') or car.get('vehicle_photo')
                        img_path = img_col if pd.notnull(img_col) and str(img_col).strip() else "https://placehold.co/600x400?text=No+Image"
                        
                        if img_path and os.path.exists(img_path):
                            st.image(img_path, use_container_width=True)
                        else:
                            st.warning("🚗 Image unavailable")

                    with col2:
                        st.write(f"### {car['make']} {car['model']} ({car['year']})")
                        base_rate = car.get('approved_price') or 2000.0

                        with st.popover(f"⚡ BOOK {car['model'].upper()} NOW", use_container_width=True):
                            st.markdown("#### 📅 1. Trip Dates")
                            c_date1, c_time1 = st.columns(2)
                            d1 = c_date1.date_input("Pickup Date", min_value=datetime.date.today(), key=f"d1_{car['id']}")
                            t1 = c_time1.time_input("Pickup Time", value=datetime.time(8, 0), key=f"t1_{car['id']}")

                            c_date2, c_time2 = st.columns(2)
                            d2 = c_date2.date_input("Return Date", min_value=d1, value=d1, key=f"d2_{car['id']}")
                            t2 = c_time2.time_input("Return Time", value=datetime.time(18, 0), key=f"t2_{car['id']}")

                            st.divider()
                            st.markdown("#### 📍 2. Trip Details")
                            drive_mode = st.radio("Mode", ["Self-Drive", "With Driver (+₱1k/day)"], key=f"dm_{car['id']}")
                            is_driver = 1 if "Driver" in drive_mode else 0
                            dest = st.text_input("Destination", key=f"dest_{car['id']}")
                            luzon_agree = st.checkbox("I agree to LUZON ONLY.", key=f"luzon_{car['id']}")

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
                            
                            delivery_fee = DELIVERY_ZONES[p_zone]
                            return_fee = DELIVERY_ZONES[r_zone]

                            st.markdown("#### 🧾 4. Cost Breakdown")
                            days = (d2 - d1).days + 1
                            subtotal = days * base_rate
                            driver_fee = (days * 1000.0) if is_driver else 0.0
                            
                            discount_pct = 0.15 if days >= 15 else (0.10 if days >= 7 else (0.05 if days >= 3 else 0.0))
                            savings = subtotal * discount_pct
                            grand_total = (subtotal - savings) + driver_fee + delivery_fee + return_fee

                            st.write(f"Total: **₱{grand_total:,.2f}**")
                            st.divider()
                            
                            ref_num = st.text_input("GCash Reference Number *", key=f"ref_{car['id']}")

                            if st.button("CONFIRM BOOKING", key=f"conf_{car['id']}", type="primary", use_container_width=True):
                                if not (dest and ref_num and luzon_agree and p_exact and r_exact):
                                    st.warning("Please complete all required fields.")
                                else:
                                    booking_ref = str(random.randint(100000, 999999))
                                    pickup_dt = f"{d1} {t1.strftime('%H:%M')}"
                                    return_dt = f"{d2} {t2.strftime('%H:%M')}"
                                    
                                    conn.execute("""
                                        INSERT INTO bookings (renter_username, vehicle_id, pickup_time, return_time, amount, status, destination, pickup_loc, return_loc, with_driver, booking_ref) 
                                        VALUES (?, ?, ?, ?, ?, 'CONFIRMED', ?, ?, ?, ?, ?)
                                    """, (renter_user, car['id'], pickup_dt, return_dt, grand_total, dest, f"{p_zone}: {p_exact}", f"{r_zone}: {r_exact}", is_driver, booking_ref))
                                    conn.commit()
                                    st.success(f"✅ Booking Confirmed! Ref: #{booking_ref}")
                                    time.sleep(2)
                                    st.rerun()

# --- TAB 1: MY BOOKINGS ---
with tabs[1]:
    my_trips = pd.read_sql_query("""
        SELECT b.*, v.make, v.model, v.plate, v.owner_username 
        FROM bookings b JOIN vehicles v ON b.vehicle_id = v.id 
        WHERE b.renter_username = ? ORDER BY b.id DESC
    """, conn, params=(renter_user,))

    if my_trips.empty:
        st.info("No bookings found.")
    else:
        for _, t in my_trips.iterrows():
            with st.expander(f"Booking #{t['booking_ref']} | {t['make']} {t['model']} | {t['status']}"):
                st.write(f"**Dest:** {t['destination']} | **Total:** ₱{t['amount']:,.2f}")
                
                # CHAT SECTION
                st.divider()
                st.write("💬 **Chat with Host**")
                b_ref = t['booking_ref']
                host = t['owner_username']
                
                chat_box = st.container(height=200, border=True)
                with chat_box:
                    history = pd.read_sql_query("SELECT * FROM chat_messages WHERE booking_ref = ? ORDER BY timestamp ASC", conn, params=(b_ref,))
                    for _, msg in history.iterrows():
                        align = "user" if msg['sender_username'] == renter_user else "assistant"
                        with st.chat_message(align):
                            st.write(msg['message_text'])
                
                msg_in = st.text_input("Send message...", key=f"chat_{b_ref}")
                if st.button("Send", key=f"btn_{b_ref}"):
                    if msg_in:
                        conn.execute("INSERT INTO chat_messages (booking_ref, sender_username, receiver_username, message_text) VALUES (?, ?, ?, ?)", (b_ref, renter_user, host, msg_in))
                        conn.commit()
                        st.rerun()
