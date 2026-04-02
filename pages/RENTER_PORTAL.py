import streamlit as st
import pandas as pd
import datetime
import time
from database_utils import get_connection

st.set_page_config(page_title="DriveElite Showroom", layout="wide")

st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); }
    .promo-banner { background: linear-gradient(90deg, #3244c4, #2c8c80); color: white; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 25px; }
    .bill-box { background-color: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #e0e0e0; margin-top: 10px; }
    .savings-badge { background-color: #d4edda; color: #155724; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .star-rating { color: #FFD700; font-size: 18px; }
</style>
""", unsafe_allow_html=True)

conn = get_connection()

# --- RENTER LOGIN FLOW WITH LOGO ---
if not st.session_state.get('logged_in') or st.session_state.get('role') != 'RENTER':
    # Logo placement centered
    logo_col1, logo_col2, logo_col3 = st.columns([1, 2, 1])
    with logo_col2:
        try: st.image("logo.png", use_container_width=True)
        except: pass
    st.markdown("<h2 style='text-align: center;'>🚙 RENTER ACCESS</h2>", unsafe_allow_html=True)
    with st.form("login_renter"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("LOGIN TO SHOWROOM", use_container_width=True):
            user = pd.read_sql_query("SELECT * FROM users WHERE username=? AND password=? AND role='RENTER'", conn, params=(u, p))
            if not user.empty:
                if user.iloc[0]['admin_status'] == 'APPROVED':
                    st.session_state.logged_in, st.session_state.username, st.session_state.role = True, u, 'RENTER'
                    st.rerun()
                else: st.warning("⏳ Account pending Admin approval.")
            else: st.error("❌ Invalid credentials.")
    st.stop()
# ------------------------------------

renter_user = st.session_state.username

# --- LOGO & TOP NAV COLUMN LAYOUT (SIDEBAR-LESS) ---
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
# ------------------------------------

tabs = st.tabs(["🌟 VEHICLE SHOWROOM", "📅 MY BOOKINGS"])

with tabs[0]:
    # Promo display
    try:
        promo = pd.read_sql_query("SELECT title, message FROM admin_promos WHERE active = 1 ORDER BY id DESC LIMIT 1", conn)
        if not promo.empty:
            st.markdown(f'<div class="promo-banner"><h2 style="margin:0;">🔥 {promo.iloc[0]["title"]} 🔥</h2><p style="margin:5px 0 0 0; font-size:18px;">{promo.iloc[0]["message"]}</p></div>', unsafe_allow_html=True)
    except: pass

    # Filters
    try:
        cat_df = pd.read_sql_query("SELECT name FROM vehicle_categories", conn)
        cat_list = ["All"] + [str(n).strip() for n in cat_df['name'].tolist()]
    except: cat_list = ["All", "Sedan", "SUV", "Van"]
    
    c_f1, c_f2 = st.columns([2, 1])
    cat_filter = c_f1.selectbox("Filter by Category", cat_list)
    search_query = c_f2.text_input("Search Brand/Model", placeholder="e.g. Nissan")

    query = "SELECT * FROM vehicles WHERE admin_status = 'APPROVED' AND booking_status = 'AVAILABLE'"
    cars = pd.read_sql_query(query, conn)

    if cat_filter != "All": cars = cars[cars['category'].str.strip() == cat_filter]
    if search_query: cars = cars[cars['make'].str.contains(search_query, case=False) | cars['model'].str.contains(search_query, case=False)]

    if cars.empty: st.info("No vehicles currently matching your search. Check back soon!")
    else:
        for i, car in cars.iterrows():
            with st.container(border=True):
                col1, col2 = st.columns([1, 2])
                with col1:
                    if car.get('vehicle_img'): st.image(car['vehicle_img'], use_container_width=True)
                with col2:
                    st.write(f"### {car['make']} {car['model']} ({car['year']})")
                    
                    # Car Rating Display
                    try:
                        rat_df = pd.read_sql_query("SELECT AVG(rating) as avg, COUNT(rating) as cnt FROM bookings WHERE vehicle_id=? AND rating IS NOT NULL", conn, params=(car['id'],))
                        if not rat_df.empty and pd.notnull(rat_df.iloc[0]['avg']):
                            real_rating = float(rat_df.iloc[0]['avg'])
                            rev_count = int(rat_df.iloc[0]['cnt'])
                            stars = int(round(real_rating))
                            st.markdown(f"<span class='star-rating'>{'⭐' * stars}</span> *{real_rating:.1f}* ({rev_count} Reviews)", unsafe_allow_html=True)
                        else: st.markdown("✨ *New on DriveElite* (No reviews yet)", unsafe_allow_html=True)
                    except: st.markdown("✨ *New on DriveElite* (No reviews yet)", unsafe_allow_html=True)
                    
                    st.write(f"*Category:* {car['category']} | *Plate:* {car['plate']}")
                    st.write(f"#### ₱{car['approved_price']:,.2f} / Day")
                    
                    # BOOKING POPOVER
                    with st.popover(f"⚡ BOOK {car['model'].upper()} NOW"):
                        st.write("### 📍 Trip Details")
                        
                        drive_mode = st.radio("Driving Mode", ["Self-Drive", "With Professional Driver (+₱1,000/day)"], key=f"dm_{car['id']}")
                        is_with_driver = 1 if "Driver" in drive_mode else 0
                        
                        if is_with_driver:
                            st.info("👨‍✈️ Duty: 10 hrs/day. OT ₱200/hr. Renter provides driver meals (or ₱300/day) & lodging outside Manila.")
                        
                        dest = st.text_input("Destination", key=f"dest_{car['id']}")
                        
                        # --- STRICT LUZON-ONLY BAN ---
                        st.error("🚨 *GEOGRAPHIC RESTRICTION*")
                        luzon_agree = st.checkbox("I agree that this vehicle will be driven within LUZON ONLY. RoRo travel is forbidden.", key=f"luzon_{car['id']}")
                        
                        # --- LOGISTICS DELIVERY ZONES ---
                        st.write("### 🚚 Logistics & Delivery")
                        st.info("HQ: Kapitolyo, Pasig. Select zone for delivery pricing.")
                        
                        DELIVERY_ZONES = {
                            "HQ: Kapitolyo, Pasig (Free)": 0.0,
                            "Zone 1: Greenhills / Ortigas / Mandaluyong / BGC": 500.0,
                            "Zone 2: Sampaloc / Manila / Pasay / QC": 1000.0
                        }
                        
                        c_loc1, c_loc2 = st.columns(2)
                        p_zone = c_loc1.selectbox("Pickup Zone", list(DELIVERY_ZONES.keys()), key=f"pzone_{car['id']}")
                        p_exact = c_loc1.text_input("Exact Pickup Address", key=f"pexact_{car['id']}")
                        
                        r_zone = c_loc2.selectbox("Return Zone", list(DELIVERY_ZONES.keys()), key=f"rzone_{car['id']}")
                        r_exact = c_loc2.text_input("Exact Return Address", key=f"rexact_{car['id']}")
                        
                        delivery_fee = DELIVERY_ZONES[p_zone]
                        return_fee = DELIVERY_ZONES[r_zone]
                        
                        final_pickup_str = f"{p_zone} ({p_exact})" if p_exact else p_zone
                        final_return_str = f"{r_zone} ({r_exact})" if r_exact else r_zone
                        
                        c_date1, c_date2 = st.columns(2)
                        p_date = c_date1.date_input("Pickup Date", datetime.date.today(), key=f"pdate_{car['id']}")
                        p_time = c_date1.time_input("Pickup Time", datetime.time(9, 0), key=f"ptime_{car['id']}")
                        
                        r_date = c_date2.date_input("Return Date", datetime.date.today() + datetime.timedelta(days=1), key=f"rdate_{car['id']}")
                        r_time = c_date2.time_input("Return Time", datetime.time(9, 0), key=f"rtime_{car['id']}")
                        
                        p_datetime = f"{p_date} {p_time.strftime('%I:%M %p')}"
                        r_datetime = f"{r_date} {r_time.strftime('%I:%M %p')}"
                        
                        days = (r_date - p_date).days if (r_date - p_date).days > 0 else 1
                        subtotal = days * car['approved_price']
                        
                        driver_fee = days * 1000.0 if is_with_driver else 0.0
                        
                        discount_pct = 0
                        if days >= 30: discount_pct = 0.20
                        elif days >= 14: discount_pct = 0.10
                        elif days >= 7: discount_pct = 0.05
                        
                        savings = subtotal * discount_pct
                        total_rent = (subtotal - savings) + driver_fee
                        deposit = 5000.00
                        
                        # Add logistics to grand total
                        grand_total = total_rent + deposit + delivery_fee + return_fee
                        
                        if savings > 0:
                            st.markdown(f'<div class="savings-badge">🎉 You saved ₱{savings:,.2f}!</div>', unsafe_allow_html=True)
                        
                        # Billing calculation box
                        bill_html = '<div class="bill-box"><table style="width:100%">'
                        bill_html += f'<tr><td>Rental ({days} Days)</td><td style="text-align:right">₱{subtotal:,.2f}</td></tr>'
                        if is_with_driver: bill_html += f'<tr><td style="color:#0056b3">Driver Fee</td><td style="text-align:right; color:#0056b3">+ ₱{driver_fee:,.2f}</td></tr>'
                        if delivery_fee > 0: bill_html += f'<tr><td style="color:#e67e22">Delivery Fee</td><td style="text-align:right; color:#e67e22">+ ₱{delivery_fee:,.2f}</td></tr>'
                        if return_fee > 0: bill_html += f'<tr><td style="color:#e67e22">Collection Fee</td><td style="text-align:right; color:#e67e22">+ ₱{return_fee:,.2f}</td></tr>'
                        bill_html += f'<tr><td style="color:red">Discount</td><td style="text-align:right; color:red">- ₱{savings:,.2f}</td></tr>'
                        bill_html += f'<tr><td style="color:green">Deposit</td><td style="text-align:right; color:green">+ ₱{deposit:,.2f}</td></tr>'
                        bill_html += f'<tr style="border-top:2px solid #000"><td><b>GRAND TOTAL</b></td><td style="text-align:right"><b>₱{grand_total:,.2f}</b></td></tr>'
                        bill_html += '</table></div>'
                        st.markdown(bill_html, unsafe_allow_html=True)
                        
                        st.divider()
                        pay_method = st.radio("Payment", ["GCash / Maya"], key=f"pay_{car['id']}") # CC offline
                        
                        # GCash flow
                        try: st.image("gcash_qr.jpg", caption=f"Scan to Pay: ₱{grand_total:,.2f}", width=250)
                        except: st.warning("⚠️ Admin: Upload 'gcash_qr.jpg' to main folder.")
                        
                        ref_num = st.text_input("Enter Reference Number *", key=f"ref_{car['id']}")
                        
                        # Final confirm button
                        if st.button("CONFIRM BOOKING & PAYMENT", type="primary", use_container_width=True, key=f"btn_{car['id']}"):
                            if not luzon_agree: st.error("❌ You must agree to the LUZON-ONLY policy.")
                            elif not dest or (delivery_fee > 0 and not p_exact) or (return_fee > 0 and not r_exact): st.error("Please fill required address details.")
                            elif not ref_num: st.error("GCash Reference Number required.")
                            else:
                                with st.spinner("Verifying Payment Reference..."):
                                    time.sleep(2) # Fake verification delay
                                    final_payment_string = f"GCash (Ref: {ref_num})"
                                    
                                    # Saves with logistics fees separated
                                    conn.execute("""INSERT INTO bookings 
                                        (vehicle_id, renter_username, amount, status, pickup_loc, return_loc, destination, pickup_time, return_time, payment_method, with_driver, delivery_fee, return_fee) 
                                        VALUES (?, ?, ?, 'CONFIRMED', ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                                        (car['id'], renter_user, grand_total, final_pickup_str, final_return_str, dest, p_datetime, r_datetime, final_payment_string, is_with_driver, delivery_fee, return_fee))
                                    conn.execute("UPDATE vehicles SET booking_status = 'BOOKED' WHERE id = ?", (car['id'],))
                                    conn.commit()
                                    st.success("✅ Payment Verified! Booking Confirmed.")
                                    time.sleep(2); st.rerun()

with tabs[1]:
    st.subheader("Manage Your Trips")
    try:
        my_trips = pd.read_sql_query("""
            SELECT b.id, v.make, v.model, b.amount, b.status, b.pickup_time, b.return_time, b.pickup_loc, b.return_loc, b.destination, b.with_driver, b.rating, b.review 
            FROM bookings b JOIN vehicles v ON b.vehicle_id = v.id 
            WHERE b.renter_username = ? ORDER BY b.id DESC""", conn, params=(renter_user,))
        
        if my_trips.empty: st.info("You haven't booked any trips yet.")
        else:
            for i, t in my_trips.iterrows():
                with st.expander(f"DRV-{t['id']:05d} | {t['make']} {t['model']} ({t['status']})"):
                    if t.get('with_driver', 0) == 1: st.markdown("👨‍✈️ *Trip includes Driver*")
                    st.write(f"*Pickup:* {t['pickup_loc']} at {t['pickup_time']}")
                    st.write(f"*Total:* ₱{t['amount']:,.2f}")
                    
                    # My Bookings Interactive Stars Feedback
                    if t['status'] == 'COMPLETED':
                        st.divider()
                        if pd.isnull(t.get('rating')):
                            st.write("### 📣 Rate your experience")
                            star_index = st.feedback("stars", key=f"star_fb_{t['id']}")
                            user_review = st.text_input("Short review (optional)", key=f"rev_text_{t['id']}")
                            if st.button("SUBMIT", type="primary", key=f"btn_rate_{t['id']}"):
                                if star_index is None: st.error("Please click the stars!")
                                else:
                                    conn.execute("UPDATE bookings SET rating=?, review=? WHERE id=?", (star_index+1, user_review, t['id']))
                                    conn.commit(); st.success("Review submitted!"); time.sleep(1); st.rerun()
                        else:
                            st.info(f"Your rating: {'⭐' * int(t['rating'])}")
                            if t.get('review'): st.write(f"{t['review']}")
    except Exception as e: st.error(str(e))
