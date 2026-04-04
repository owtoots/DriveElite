import streamlit as st
import pandas as pd
from database_utils import get_connection

st.set_page_config(page_title="DriveElite Admin", layout="wide")
conn = get_connection()

# --- AUTHENTICATION ---
if not st.session_state.get('logged_in') or st.session_state.get('role') != 'ADMIN':
    st.title("ADMIN LOGIN")
    with st.form("login"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("AUTHORIZE"):
            if u == "masterom" and p == "qZ822118qq":
                st.session_state.logged_in, st.session_state.username, st.session_state.role = True, "masterom", "ADMIN"
                st.rerun()
    st.stop()

# --- TOP NAVIGATION BAR ---
head_col1, head_col2 = st.columns([5, 1])
with head_col1:
    st.title("🛡️ MASTER COMMAND CENTER")
with head_col2:
    st.info(f"👨‍💼 {st.session_state.username.upper()}")
    if st.button("🔒 LOGOUT", use_container_width=True):
        st.session_state.clear()
        st.rerun()

tabs = st.tabs(["PENDING APPROVALS", "ASSETS", "LOGISTICS", "FINANCIALS", "🗄️ FILING CABINET", "PROMOS & DB"])

# --- TAB 0: PENDING APPROVALS ---
with tabs[0]:
    st.markdown("<h3 style='text-align: center;'>📋 PENDING APPROVALS</h3>", unsafe_allow_html=True)
    p_tabs = st.tabs(["🚙 PENDING RENTERS", "💼 PENDING AFFILIATES", "👨‍✈️ PENDING DRIVERS"])
    
    with p_tabs[0]:
        renters = pd.read_sql_query("SELECT * FROM users WHERE admin_status = 'PENDING' AND role = 'RENTER'", conn)
        if renters.empty: st.info("No pending renters.")
        for i, r in renters.iterrows():
            with st.expander(f"{r['full_name']} (@{r['username']})"):
                st.write(f"Age: {r['age']} | Nat: {r.get('nationality', 'Filipino')} | Contact: {r['contact_number']}")
                c_img1, c_img2 = st.columns(2)
                if r.get('govt_id_img'): c_img1.image(r['govt_id_img'], caption="Passport / Govt ID")
                if r.get('license_img'): c_img2.image(r['license_img'], caption="Driver's License")
                if st.button("APPROVE RENTER", key=f"ra_{r['id']}", type="primary", use_container_width=True):
                    conn.execute("UPDATE users SET admin_status = 'APPROVED' WHERE id = ?", (r['id'],))
                    conn.commit()
                    st.rerun()

    with p_tabs[1]:
        affiliates = pd.read_sql_query("SELECT * FROM users WHERE admin_status = 'PENDING' AND role = 'AFFILIATE'", conn)
        if affiliates.empty: st.info("No pending affiliates.")
        for i, r in affiliates.iterrows():
            with st.expander(f"{r['full_name']} (@{r['username']})"):
                st.write(f"Age: {r['age']} | Nat: {r.get('nationality', 'Filipino')} | Contact: {r['contact_number']}")
                c_img1, c_img2 = st.columns(2)
                if r.get('govt_id_img'): c_img1.image(r['govt_id_img'], caption="Passport / Govt ID")
                if r.get('license_img'): c_img2.image(r['license_img'], caption="Driver's License") 
                if st.button("APPROVE AFFILIATE", key=f"aa_{r['id']}", type="primary", use_container_width=True):
                    conn.execute("UPDATE users SET admin_status = 'APPROVED' WHERE id = ?", (r['id'],))
                    conn.commit()
                    st.rerun()

    with p_tabs[2]:
        drivers = pd.read_sql_query("SELECT * FROM drivers WHERE admin_status = 'PENDING'", conn)
        if drivers.empty: st.info("No pending drivers.")
        for i, d in drivers.iterrows():
            with st.expander(f"{d['first_name']} {d['last_name']} (Affiliate: @{d['owner_username']})"):
                st.write(f"Age: {d['age']} | Contact: {d['contact_number']} | Address: {d['address']}")
                if d.get('is_owner'): st.info("ℹ️ This driver is also the registered Affiliate Owner.")
                c_img1, c_img2 = st.columns(2)
                if d.get('govt_id_img'): c_img1.image(d['govt_id_img'], caption="Govt ID")
                if d.get('license_img'): c_img2.image(d['license_img'], caption="Professional License")
                if st.button("APPROVE DRIVER", key=f"da_{d['id']}", type="primary", use_container_width=True):
                    conn.execute("UPDATE drivers SET admin_status = 'APPROVED' WHERE id = ?", (d['id'],))
                    conn.commit()
                    st.rerun()

# --- TAB 1: ASSETS ---
with tabs[1]:
    st.subheader("Vehicle Approvals")
    pv = pd.read_sql_query("SELECT * FROM vehicles WHERE admin_status = 'PENDING'", conn)
    if pv.empty: st.info("No pending vehicles.")
    for i, r in pv.iterrows():
        with st.expander(f"{r['make']} {r['model']} ({r['plate']})"):
            col_img1, col_img2, col_img3 = st.columns(3)
            if r.get('vehicle_img'): col_img1.image(r['vehicle_img'], caption="Vehicle Photo")
            if r.get('or_cr_img'): col_img2.image(r['or_cr_img'], caption="OR/CR")
            if r.get('insurance_img'): col_img3.image(r['insurance_img'], caption="Insurance")
            if st.button("APPROVE ASSET", key=f"v_{r['id']}", type="primary"):
                conn.execute("UPDATE vehicles SET admin_status = 'APPROVED' WHERE id = ?", (r['id'],))
                conn.commit()
                st.rerun()

# --- TAB 2: LOGISTICS ---
with tabs[2]:
    st.subheader("Active Logistics")
    try:
        bookings = pd.read_sql_query("SELECT b.*, u.full_name as renter_name FROM bookings b JOIN users u ON b.renter_username = u.username WHERE b.status != 'COMPLETED'", conn)
        if bookings.empty: st.info("No active logistics.")
        for i, r in bookings.iterrows():
            with st.expander(f"Ref #DRV-{r['id']:05d} | STATUS: {r['status']} | RENTER: {r['renter_name']}"):
                if r.get('with_driver', 0) == 1: st.markdown("👨‍✈️ [TRIP INCLUDES PROFESSIONAL DRIVER]")
                st.write(f"Amount Paid: ₱{r['amount']:,.2f} | Dest: {r.get('destination', 'N/A')}")
    except: pass

# --- TAB 3: FINANCIALS ---
with tabs[3]:
    st.markdown("<h2 style='text-align: center;'>🏦 MASTER FINANCIAL LEDGER</h2>", unsafe_allow_html=True)
    try:
        query = """
        SELECT b.id, b.pickup_time as Date, u_renter.full_name as Renter, u_owner.full_name as Affiliate,
               b.amount as Gross_Revenue, b.status as Trip_Status, b.payout_status as Payout_Status,
               v.bank_name, v.account_no
        FROM bookings b
        JOIN vehicles v ON b.vehicle_id = v.id
        JOIN users u_renter ON b.renter_username = u_renter.username
        JOIN users u_owner ON v.owner_username = u_owner.username
        ORDER BY b.id DESC
        """
        df = pd.read_sql_query(query, conn)
        if df.empty:
            st.info("No financial transactions recorded yet.")
        else:
            df['Date_Clean'] = pd.to_datetime(df['Date'].astype(str).str[:10], errors='coerce')
            df['Affiliate_Share (85%)'] = df['Gross_Revenue'] * 0.85
            df['DriveElite_Fee (15%)'] = df['Gross_Revenue'] * 0.15
            df['Ref'] = df['id'].apply(lambda x: f"DRV-{x:05d}")
            
            c1, c2, c3 = st.columns(3)
            c1.metric("💰 Total Platform Gross", f"₱{df['Gross_Revenue'].sum():,.2f}")
            c2.metric("🏢 DriveElite Net Revenue (15%)", f"₱{df['DriveElite_Fee (15%)'].sum():,.2f}")
            pending_payouts = df[(df['Payout_Status'] == 'PENDING') & (df['Trip_Status'] == 'COMPLETED')]['Affiliate_Share (85%)'].sum()
            c3.metric("⏳ Pending Affiliate Payouts", f"₱{pending_payouts:,.2f}", delta="-Liabilities", delta_color="inverse")
            
            f_tabs = st.tabs(["📑 MASTER LEDGER", "📅 DAILY", "📤 PROCESS PAYOUTS"])
            with f_tabs[0]: 
                st.dataframe(df[['Ref', 'Date', 'Renter', 'Affiliate', 'Gross_Revenue', 'Trip_Status', 'Payout_Status']], use_container_width=True, hide_index=True)
            with f_tabs[2]:
                pending_df = df[(df['Trip_Status'] == 'COMPLETED') & (df['Payout_Status'] == 'PENDING')]
                if pending_df.empty: st.info("No pending payouts.")
                for _, p in pending_df.iterrows():
                    with st.expander(f"{p['Ref']} | {p['Affiliate']} | Amount Due: ₱{p['Affiliate_Share (85%)']:,.2f}"):
                        st.write(f"Send To: {p['bank_name']} | Account Number: {p['account_no']}")
                        if st.button("MARK AS PAID", key=f"pay_{p['id']}", type="primary", use_container_width=True):
                            conn.execute("UPDATE bookings SET payout_status = 'PAID' WHERE id = ?", (p['id'],))
                            conn.commit()
                            st.rerun()
    except Exception as e: st.error(f"Financial Error: {str(e)}")

# --- TAB 4: FILING CABINET ---
with tabs[4]: 
    st.header("🗄️ Master Digital Filing Cabinet")
    q_all = "SELECT b.*, v.make, v.model, v.plate, r.full_name as rname, r.username as r_user, u.full_name as owner_name FROM bookings b JOIN vehicles v ON b.vehicle_id = v.id JOIN users r ON b.renter_username = r.username JOIN users u ON v.owner_username = u.username"
    try:
        df_search = pd.read_sql_query(q_all, conn)
        search_mode = st.radio("Search Records By:", ["Booking ID", "Renter Name", "Affiliate Name", "Vehicle Plate"], horizontal=True)
        filtered_df = pd.DataFrame()
        
        c_search, _ = st.columns([1, 1])
        with c_search:
            if search_mode == "Booking ID":
                search_val = st.number_input("Enter exact Booking ID", min_value=1, step=1, value=1)
                if st.button("SEARCH"): filtered_df = df_search[df_search['id'] == search_val]
            elif search_mode == "Renter Name":
                r_list = ["-- Select Renter --"] + df_search['rname'].unique().tolist()
                s_val = st.selectbox("Select a Renter", r_list)
                if s_val != "-- Select Renter --": filtered_df = df_search[df_search['rname'] == s_val]
            elif search_mode == "Affiliate Name":
                a_list = ["-- Select Affiliate --"] + df_search['owner_name'].unique().tolist()
                s_val = st.selectbox("Select an Affiliate", a_list)
                if s_val != "-- Select Affiliate --": filtered_df = df_search[df_search['owner_name'] == s_val]
            elif search_mode == "Vehicle Plate":
                p_list = ["-- Select Plate --"] + df_search['plate'].unique().tolist()
                s_val = st.selectbox("Select Vehicle Plate", p_list)
                if s_val != "-- Select Plate --": filtered_df = df_search[df_search['plate'] == s_val]

        st.divider()

        if not filtered_df.empty:
            if len(filtered_df) > 1:
                st.info(f"Found {len(filtered_df)} records. Please select which specific trip you want to view:")
                b_id = st.selectbox("Select Trip Reference:", filtered_df['id'].apply(lambda x: f"DRV-{x:05d}").tolist())
                r = filtered_df[filtered_df['id'] == int(b_id.replace("DRV-", ""))].iloc[0]
            else:
                r = filtered_df.iloc[0]
            
            st.success(f"Viewing Case File: DRV-{r['id']:05d}")
            st.write(f"Vehicle: {r['make']} {r['model']} ({r['plate']})")
            st.write(f"Renter: {r['rname']} | Affiliate: {r['owner_name']}")
            st.write(f"Trip Status: {r['status']}")
            
            st.write("### 📸 Pre-Dispatch Visual Proof")
            photos = [r.get('actual_dl_img'), r.get('front_img'), r.get('back_img'), r.get('left_img'), r.get('right_img'), r.get('odometer_img'), r.get('dseat_img'), r.get('pseat_img'), r.get('trunk_img'), r.get('tire_img')]
            photo_cols = st.columns(5)
            valid_photos = 0
            for idx, p in enumerate(photos):
                if pd.notna(p) and p:
                    photo_cols[idx % 5].image(p, caption=f"Dispatch Photo {idx+1}")
                    valid_photos += 1
            if valid_photos == 0: st.warning("No pre-dispatch photos were attached to this record.")
            
            if pd.notna(r.get('damage_img')) and r.get('damage_img'):
                st.divider()
                st.error("⚠️ DAMAGE REPORTED ON RETURN")
                st.image(r['damage_img'], caption="Proof of Damage", width=400)
    except:
        st.info("Database is empty or formatting.")

# --- TAB 5: PROMOS & DB ---
with tabs[5]:
    col_promo, col_cat = st.columns(2)
    with col_promo:
        st.subheader("📢 Broadcast Manager")
        with st.form("promo"):
            t = st.text_input("Broadcast Title")
            m = st.text_area("Broadcast Message")
            target = st.radio("Target Audience:", ["RENTERS", "AFFILIATES", "ALL USERS"], horizontal=True)
            
            if st.form_submit_button("PUBLISH BROADCAST"):
                if t and m:
                    try:
                        conn.execute("ALTER TABLE admin_promos ADD COLUMN target TEXT DEFAULT 'ALL USERS'")
                        conn.commit()
                    except: pass
                    
                    conn.execute("UPDATE admin_promos SET active = 0")
                    conn.execute("INSERT INTO admin_promos (title, message, target) VALUES (?, ?, ?)", (t, m, target))
                    conn.commit()
                    st.success(f"Live! Broadcast successfully published to {target}.")
                    
    with col_cat:
        st.subheader("📈 Category Manager")
        with st.form("add_cat", clear_on_submit=True):
            n = st.text_input("New Category (e.g., Pickup, Luxury)")
            p = st.number_input("Daily Rate (₱)", min_value=500.0, step=100.0, value=2500.0)
            if st.form_submit_button("ADD NEW CATEGORY"):
                if n:
                    try:
                        conn.execute("INSERT INTO vehicle_categories (name, default_price) VALUES (?, ?)", (n.title(), p))
                        conn.commit()
                    except: pass

    st.divider()
    st.write("🔍 Quick Profile Viewer (Lookup IDs)*")
    
    u_df = pd.read_sql_query("SELECT full_name, role, govt_id_img, license_img FROM users WHERE admin_status = 'APPROVED'", conn)
    try:
        d_df = pd.read_sql_query("SELECT first_name || ' ' || last_name AS full_name, 'DRIVER' AS role, id_img AS govt_id_img, license_img FROM drivers WHERE admin_status = 'APPROVED'", conn)
        all_profiles = pd.concat([u_df, d_df], ignore_index=True)
    except:
        all_profiles = u_df 

    if not all_profiles.empty:
        all_profiles['display_name'] = all_profiles['full_name'] + " (" + all_profiles['role'] + ")"
        user_list = ["-- Select a Profile --"] + all_profiles['display_name'].tolist()
        selected_user = st.selectbox("Search for an Approved Profile to view their documents:", user_list)
        
        if selected_user != "-- Select a Profile --":
            u_data = all_profiles[all_profiles['display_name'] == selected_user].iloc[0]
            c_id1, c_id2 = st.columns(2)
            
            with c_id1:
                if pd.notna(u_data.get('govt_id_img')) and u_data.get('govt_id_img'): 
                    c_id1.image(u_data['govt_id_img'], caption="Govt ID")
                else: st.info("No Government ID uploaded.")
            
            with c_id2:
                if pd.notna(u_data.get('license_img')) and u_data.get('license_img'): 
                    c_id2.image(u_data['license_img'], caption="Driver's License")
                else: st.info("No Driver's License uploaded.")

    st.divider()
    st.markdown("<h3 style='text-align: center;'>ALL REGISTERED USERS</h3>", unsafe_allow_html=True)
    
    try:
        db_tabs = st.tabs(["🚗 RENTERS", "💼 AFFILIATES", "🧑‍✈️ DRIVERS"])
        
        q_renters = "SELECT full_name as 'FULLNAME', address as 'ADDRESS', contact_number as 'CONTACT NO.', admin_status as 'STATUS' FROM users WHERE role='RENTER'"
        with db_tabs[0]: st.dataframe(pd.read_sql_query(q_renters, conn), hide_index=True, use_container_width=True)
        
        q_affiliates = "SELECT full_name as 'FULLNAME', address as 'ADDRESS', contact_number as 'CONTACT NO.', admin_status as 'STATUS' FROM users WHERE role='AFFILIATE'"
        with db_tabs[1]: st.dataframe(pd.read_sql_query(q_affiliates, conn), hide_index=True, use_container_width=True)
        
        q_drivers = "SELECT first_name || ' ' || last_name as 'FULLNAME', owner_username as 'BELONGS TO AFFILIATE', contact_number as 'CONTACT NO.', admin_status as 'STATUS' FROM drivers"
        with db_tabs[2]: st.dataframe(pd.read_sql_query(q_drivers, conn), hide_index=True, use_container_width=True)
    except: 
        pass
