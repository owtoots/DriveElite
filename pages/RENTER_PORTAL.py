import streamlit as st
import pandas as pd
import datetime
import time
import random  
import os  
from database_utils import get_connection

conn = get_connection()

# --- DB PATCH: Add document_url to users table ---
try: 
    conn.execute("ALTER TABLE users ADD COLUMN document_url TEXT")
    conn.commit()
except Exception: 
    pass
# -------------------------------------------------

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

conn = get_connection()

# --- DEV TOOLS: AUTO-HEAL DATABASE & USERS ---
try:
    check_user = pd.read_sql_query("SELECT * FROM users WHERE username='testrenter'", conn)
    if check_user.empty:
        conn.execute("INSERT INTO users (username, password, role, admin_status) VALUES ('testrenter', 'password123', 'RENTER', 'APPROVED')")
        conn.commit()
except Exception: 
    pass

try: conn.execute("ALTER TABLE bookings ADD COLUMN rating INTEGER"); conn.commit()
except Exception: pass

try: conn.execute("ALTER TABLE bookings ADD COLUMN review_comment TEXT"); conn.commit()
except Exception: pass

# Added new columns to track the 5k physical cash and penalties!
try: conn.execute("ALTER TABLE bookings ADD COLUMN deposit_collected INTEGER DEFAULT 0"); conn.commit()
except Exception: pass

try: conn.execute("ALTER TABLE bookings ADD COLUMN penalties REAL DEFAULT 0.0"); conn.commit()
except Exception: pass

# Added reference number columns
try: conn.execute("ALTER TABLE bookings ADD COLUMN booking_ref TEXT"); conn.commit()
except Exception: pass

try: conn.execute("ALTER TABLE vehicles ADD COLUMN ref_no TEXT"); conn.commit()
except Exception: pass
# ---------------------------------------------

# --- 1. LOGIN FLOW ---
if not st.session_state.get('logged_in') or st.session_state.get('role') != 'RENTER':
    logo_col1, logo_col2, logo_col3 = st.columns([1, 2, 1])
    with logo_col2:
        try: st.image("logo.png", use_container_width=True)
        except: pass
    st.markdown("<h2 style='text-align: center;'>🚙 RENTER ACCESS</h2>", unsafe_allow_html=True)
    with st.form("login_renter"):
        st.info("🔧 **Test Credentials:** Username: `testrenter` | Password: `password123`")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("LOGIN TO SHOWROOM", use_container_width=True):
            user = pd.read_sql_query("SELECT * FROM users WHERE username=? AND password=? AND role='RENTER'", conn, params=(u, p))
            if not user.empty:
                if user.iloc[0]['admin_status'] == 'APPROVED':
                    st.session_state.logged_in, st.session_state.username, st.session_state.role = True, u, 'RENTER'
                    st.rerun()
                else: 
                    st.warning("⏳ Account pending Admin approval.")
            else: 
                st.error("❌ Invalid credentials.")
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
                        
                        # Properly indented checking block
                        if img_path and os.path.exists(img_path):
                            st.image(img_path, use_container_width=True)
                        else:
                            st.warning("🚗 Image temporarily unavailable (Cloud Reset)")

                    with col2:
                        st.write(f"### {car['make']} {car['model']} ({car['year']})")
                        ap = car.get('approved_price')
                        dr = car.get('daily_rate')
                        base_rate = ap if pd.notnull(ap) and ap > 0 else (dr if pd.notnull(dr) and dr > 0 else 2000.0)

                        with st.popover(f"⚡ BOOK {car['model'].upper()} NOW", use_container_width=True):
                            existing_books = pd.read_sql_query(
                                """
                                SELECT pickup_time, return_time, renter_username 
                                FROM bookings 
                                WHERE vehicle_id = ? 
                                AND status IN ('CONFIRMED', 'ONGOING', 'MAINTENANCE')
                                AND return_time >= date('now')
                                """, 
                                conn, params=(car['id'],)
                            )

                            st.markdown("#### 🗓️ Current Availability")
                            if not existing_books.empty:
                                st.warning("⚠️ This vehicle has existing bookings:")
                                for _, row in existing_books.iterrows():
                                    p_date = str(row['pickup_time'])[:10]
                                    r_date = str(row['return_time'])[:10]
                                    st.write(f"🚫 **Booked:** {p_date} to {r_date}")
                            else:
                                st.success("✅ Fully available for your selected dates!")

                            st.divider()

                            st.markdown("#### 📅 1. Choose Your Trip Dates")
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
                            st.info("💡 **Note: Pickup and Return is strictly up to Zone 3 only.**")
                            DELIVERY_ZONES = {
                                "HQ: Kapitolyo, Pasig (Free)": 0.0,
                                "Zone 1: Greenhills / Ortigas / BGC": 500.0,
                                "Zone 2: Manila / QC / Pasay": 1000.0,
                                "Zone 3: Alabang / Las Piñas / Parañaque": 1500.0
                            }
                            c_loc1, c_loc2 = st.columns(2)
                            p_zone = c_loc1.selectbox("Pickup Zone", list(DELIVERY_ZONES.keys()), key=f"pz_{car['id']}")
                            p_exact = c_loc1.text_input("Exact Pickup Address", placeholder="House #, Street", key=f"pa_{car['id']}")
                            
                            r_zone = c_loc2.selectbox("Return Zone", list(DELIVERY_ZONES.keys()), key=f"rz_{car['id']}")
                            r_exact = c_loc2.text_input("Exact Return Address", placeholder="Collection point", key=f"ra_{car['id']}")
                            
                            delivery_fee = DELIVERY_ZONES[p_zone]
                            return_fee = DELIVERY_ZONES[r_zone]
                            final_pickup_str = f"{p_zone}: {p_exact}"
                            final_return_str = f"{r_zone}: {r_exact}"

                            out_of_bounds = False
                            restricted_areas = ["laguna", "cavite", "batangas", "bulacan", "rizal", "pampanga", "tagaytay", "antipolo"]
                            if p_exact and r_exact:
                                if any(area in p_exact.lower() for area in restricted_areas) or any(area in r_exact.lower() for area in restricted_areas):
                                    out_of_bounds = True
                                    st.error("🚨 OUT OF BOUNDS ALARM: You entered an address outside our supported zones. Delivery is strictly limited to Metro Manila.")

                            st.markdown("#### 🧾 4. Cost Breakdown")
                            days = (d2 - d1).days + 1
                            subtotal = days * base_rate
                            driver_fee = (days * 1000.0) if is_driver else 0.0
                                
                            discount_pct = 0.0
                            if days >= 15: discount_pct = 0.15
                            elif days >= 7: discount_pct = 0.10
                            elif days >= 3: discount_pct = 0.05
                            savings = subtotal * discount_pct
                                
                            grand_total = (subtotal - savings) + driver_fee + delivery_fee + return_fee

                            bill_html = '<div class="bill-box"><table style="width:100%; font-family: monospace; font-size: 1.1em;">'
                            bill_html += f'<tr><td style="padding: 5px 0;">Base Rate (₱{base_rate:,.2f} x {days} days)</td><td style="text-align:right">₱{subtotal:,.2f}</td></tr>'
                            if savings > 0: bill_html += f'<tr><td style="padding: 5px 0; color:#d9534f;"><i>Tiered Discount ({int(discount_pct*100)}%)</i></td><td style="text-align:right; color:#d9534f;"><i>- ₱{savings:,.2f}</i></td></tr>'
                            if is_driver: bill_html += f'<tr><td style="padding: 5px 0; color:#0056b3">Professional Driver</td><td style="text-align:right; color:#0056b3">+ ₱{driver_fee:,.2f}</td></tr>'
                            if delivery_fee > 0: bill_html += f'<tr><td style="padding: 5px 0; color:#e67e22">Delivery Fee</td><td style="text-align:right; color:#e67e22">+ ₱{delivery_fee:,.2f}</td></tr>'
                            if return_fee > 0: bill_html += f'<tr><td style="padding: 5px 0; color:#e67e22">Collection Fee</td><td style="text-align:right; color:#e67e22">+ ₱{return_fee:,.2f}</td></tr>'
                            bill_html += f'<tr style="border-top:2px solid #000"><td style="padding: 10px 0;"><b>GRAND TOTAL (Pay Online)</b></td><td style="text-align:right"><b>₱{grand_total:,.2f}</b></td></tr>'
                            bill_html += f'<tr><td style="padding: 5px 0; color:#198754"><i>Cash Deposit (Pay to Driver)</i></td><td style="text-align:right; color:#198754"><i>₱5,000.00</i></td></tr>'
                            bill_html += '</table></div><br>'
                            st.markdown(bill_html, unsafe_allow_html=True)

                            st.divider()
                            st.markdown("#### 💳 5. Payment")
                            try: st.image("gcash_qr.jpg", caption=f"Pay ₱{grand_total:,.2f}", width=250)
                            except: st.warning("Admin: Upload gcash_qr.jpg")
                                
                            ref_num = st.text_input("GCash Reference Number *", key=f"ref_{car['id']}")

                            if st.button("CONFIRM BOOKING", key=f"conf_{car['id']}", type="primary", use_container_width=True):
                                if not (dest and ref_num and luzon_agree and p_exact and r_exact):
                                    st.warning("Please complete all required fields.")
                                elif out_of_bounds:
                                    st.error("❌ Cannot proceed: Please change your delivery/return address to a supported zone.")
                                else:
                                    # GENERATE 6-DIGIT BOOKING REF
                                    booking_ref = str(random.randint(100000, 999999))
                                    
                                    pickup_dt = f"{d1} {t1.strftime('%H:%M')}"
                                    return_dt = f"{d2} {t2.strftime('%H:%M')}"
                                    
                                    # INJECT BOOKING REF INTO DATABASE
                                    conn.execute("""
                                        INSERT INTO bookings (renter_username, vehicle_id, pickup_time, return_time, amount, status, destination, pickup_loc, return_loc, with_driver, booking_ref) 
                                        VALUES (?, ?, ?, ?, ?, 'CONFIRMED', ?, ?, ?, ?, ?)
                                    """, (renter_user, car['id'], pickup_dt, return_dt, grand_total, dest, final_pickup_str, final_return_str, is_driver, booking_ref))
                                    conn.commit()
                                    
                                    # SHOW REFERENCE NUMBER TO RENTER
                                    st.success(f"✅ Booking Confirmed! Your Reference No is: #{booking_ref}")
                                    time.sleep(3)
                                    st.rerun()

# --- TAB 1: MANAGE YOUR TRIPS & REVIEWS ---
with tabs[1]:
    st.markdown("<h3 style='text-align: center;'>🧳 Manage Your Trips</h3>", unsafe_allow_html=True)
    
    # --- FIXED DB PATCH ---
    # Separated into two blocks! If 'rating' already exists, it will still safely create 'review'.
    try: conn.execute("ALTER TABLE bookings ADD COLUMN rating INTEGER")
    except: pass
    try: conn.execute("ALTER TABLE bookings ADD COLUMN review TEXT")
    except: pass
    conn.commit()
    
    trip_tabs = st.tabs(["🚀 Active Trips", "📜 Trip History & Reviews"])
    
    # Fetch ALL trips belonging to this Renter, sorted by newest first
    my_trips_query = """
        SELECT b.*, v.make, v.model, v.plate 
        FROM bookings b 
        JOIN vehicles v ON b.vehicle_id = v.id 
        WHERE b.renter_username = ? 
        ORDER BY b.pickup_time DESC
    """
    my_trips = pd.read_sql_query(my_trips_query, conn, params=(renter_user,))
    
    if my_trips.empty:
        st.info("You haven't booked any trips yet. Head to the Showroom to get started!")
    else:
        # --- SUB-TAB 1: ACTIVE TRIPS ---
        with trip_tabs[0]:
            active_trips = my_trips[my_trips['status'].isin(['PENDING', 'CONFIRMED', 'ONGOING'])]
            if active_trips.empty:
                st.info("No active trips at the moment.")
            else:
                for _, t in active_trips.iterrows():
                    with st.expander(f"🚗 {t['make']} {t['model']} ({t['plate']}) | STATUS: {t['status']}"):
                        st.write(f"**Schedule:** {str(t['pickup_time'])[:16]} to {str(t['return_time'])[:16]}")
                        st.write(f"**Destination:** {t['destination']}")
                        st.write(f"**Grand Total:** ₱{t['amount']:,.2f}")
                        
                        # Give them a status update so they know what happens next
                        if t['status'] == 'PENDING': st.warning("Waiting for Affiliate to review your booking...")
                        elif t['status'] == 'CONFIRMED': st.success("Booking confirmed! Please proceed to handover on your pickup date.")
                        elif t['status'] == 'ONGOING': st.info("Trip is currently in progress. Drive safely!")

        # --- SUB-TAB 2: TRIP HISTORY & REVIEWS ---
        with trip_tabs[1]:
            history_trips = my_trips[my_trips['status'] == 'COMPLETED']
            if history_trips.empty:
                st.info("No completed trips to review yet.")
            else:
                for _, t in history_trips.iterrows():
                    with st.expander(f"✅ COMPLETED: {t['make']} {t['model']} | {str(t['pickup_time'])[:10]}"):
                        st.write(f"**Trip Cost:** ₱{t['amount']:,.2f} | **Destination:** {t['destination']}")
                        st.divider()
                        
                        # Check if they have already left a review
                        if pd.isna(t.get('rating')) or not t.get('rating'):
                            st.write("### ⭐ Rate Your Experience")
                            with st.form(f"review_form_{t['id']}"):
                                
                                # UPGRADED UI: No more horizontal volume line! It now uses visual star buttons.
                                star_options = ["5 ⭐⭐⭐⭐⭐", "4 ⭐⭐⭐⭐", "3 ⭐⭐⭐", "2 ⭐⭐", "1 ⭐"]
                                star_choice = st.radio("Select Rating:", star_options, horizontal=True, key=f"star_{t['id']}")
                                
                                review_txt = st.text_area("Tell us about your trip!", key=f"txt_{t['id']}")
                                
                                if st.form_submit_button("Submit Review"):
                                    # Extracts the number from the choice (e.g., grabs the "5" from "5 ⭐⭐⭐⭐⭐")
                                    num_stars = int(star_choice[0]) 
                                    
                                    conn.execute("UPDATE bookings SET rating = ?, review = ? WHERE id = ?", (num_stars, review_txt, t['id']))
                                    conn.commit()
                                    st.success("Thank you for your feedback!")
                                    time.sleep(1)
                                    st.rerun()
                        else:
                            # Show the review they left
                            stars = "⭐" * int(t['rating'])
                            st.success(f"**You rated this trip {int(t['rating'])}/5** {stars}")
                            if t.get('review'):
                                st.write(f"*{t['review']}*")

# ==========================================
# 4. SIDEBAR (Placed safely at the bottom)
# ==========================================
with st.sidebar:
    st.write(f"### 👤 Renter Profile")
    st.write(f"**Username:** {st.session_state.username}")
    
    # Fetch their specific contract link from the database
    user_doc = pd.read_sql_query(
        "SELECT document_url FROM users WHERE username=?", 
        conn, 
        params=(st.session_state.username,)
    )
    
    if not user_doc.empty and pd.notnull(user_doc.iloc[0]['document_url']):
        doc_link = user_doc.iloc[0]['document_url']
        st.success("Account Verified ✅")
        st.link_button("📄 View Master Agreement", doc_link, use_container_width=True)
    else:
        st.warning("⚠️ No signed agreement found.")
    
    st.divider()
    st.caption("Need help? Contact DriveElite Admin.")
