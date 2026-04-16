import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import streamlit as st
import pandas as pd
import datetime
import os
import numpy as np
import time
import random 
from PIL import Image
from fpdf import FPDF
from database_utils import get_connection
from email.message import EmailMessage




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
            else:
                st.error("Invalid credentials.")
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

tabs = st.tabs(["PENDING APPROVALS", "ASSETS", "LOGISTICS", "FINANCIALS", "🗄️ FILING CABINET", "PROMOS & DB", "⭐ REVIEWS", "❌ CANCELLATIONS"])

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
                if pd.notna(r.get('govt_id_img')) and r.get('govt_id_img'): c_img1.image(r['govt_id_img'], caption="Passport / Govt ID")
                if pd.notna(r.get('license_img')) and r.get('license_img'): c_img2.image(r['license_img'], caption="Driver's License")
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
                if pd.notna(r.get('govt_id_img')) and r.get('govt_id_img'): c_img1.image(r['govt_id_img'], caption="Passport / Govt ID")
                if pd.notna(r.get('license_img')) and r.get('license_img'): c_img2.image(r['license_img'], caption="Driver's License") 
                if pd.notna(r.get('signature_img')) and r.get('signature_img'):
                    st.image(r['signature_img'], caption=f"Digitally Signed MOA", width=300)
                if st.button("APPROVE AFFILIATE", key=f"aa_{r['id']}", type="primary", use_container_width=True):
                    conn.execute("UPDATE users SET admin_status = 'APPROVED' WHERE id = ?", (r['id'],))
                    conn.commit()
                    st.rerun()

    with p_tabs[2]:
        drivers = pd.read_sql_query("SELECT * FROM drivers WHERE admin_status = 'PENDING'", conn)
        if drivers.empty: st.info("No pending drivers.")
        for i, d in drivers.iterrows():
            with st.expander(f"{d['first_name']} {d['last_name']} (Affiliate: @{d['owner_username']})"):
                st.write(f"Age: {d['age']} | Contact: {d['contact_number']}")
                c_img1, c_img2 = st.columns(2)
                if pd.notna(d.get('govt_id_img')) and d.get('govt_id_img'): c_img1.image(d['govt_id_img'], caption="Govt ID")
                if pd.notna(d.get('license_img')) and d.get('license_img'): c_img2.image(d['license_img'], caption="Professional License")
                if st.button("APPROVE DRIVER", key=f"da_{d['id']}", type="primary", use_container_width=True):
                    conn.execute("UPDATE drivers SET admin_status = 'APPROVED' WHERE id = ?", (d['id'],))
                    conn.commit()
                    st.rerun()

# --- TAB 1: ASSETS ---
with tabs[1]:
    pv = pd.read_sql_query("SELECT * FROM vehicles WHERE admin_status = 'PENDING'", conn)
    if pv.empty: st.info("No pending vehicles.")
    for i, r in pv.iterrows():
        v_ref = r.get('ref_no') if pd.notnull(r.get('ref_no')) else 'PENDING'
        with st.expander(f"🚗 #{v_ref} | {r['make']} {r['model']} ({r['plate']})"):
            col_img1, col_img2, col_img3 = st.columns(3)
            if r.get('vehicle_img'): col_img1.image(r['vehicle_img'], caption="Vehicle")
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
        query = """
            SELECT b.*, u_renter.full_name as renter_name, u_owner.full_name as affiliate_name 
            FROM bookings b 
            JOIN users u_renter ON b.renter_username = u_renter.username 
            JOIN vehicles v ON b.vehicle_id = v.id 
            JOIN users u_owner ON v.owner_username = u_owner.username 
            WHERE b.status != 'COMPLETED'
        """
        bookings = pd.read_sql_query(query, conn)
        if bookings.empty: st.info("No active logistics.")
        else:
            for i, r in bookings.iterrows():
                with st.expander(f"🎫 #{r['id']} | {r['status']} | RENTER: {r['renter_name']} | AFFILIATE: {r['affiliate_name']}"):
                    st.write(f"Amount: ₱{r['amount']:,.2f} | Destination: {r.get('destination')}")
    except Exception as e: st.error(str(e))

# --- TAB 3: FINANCIALS ---
with tabs[3]:
    st.markdown("<h2 style='text-align: center;'>🏦 MASTER FINANCIAL LEDGER</h2>", unsafe_allow_html=True)
    try:
        # 1. Fetch Data (Ensuring gateway_fee is included)
        query = """
        SELECT b.id, b.booking_ref, b.pickup_time as Date, u_renter.full_name as Renter, u_owner.full_name as Affiliate,
               b.amount as Gross_Revenue, b.status as Trip_Status, b.payout_status as Payout_Status,
               b.gateway_fee, v.bank_name, v.account_no
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
            # --- 2. CALCULATIONS (MOA COMPLIANT) ---
            TAX_RATE = 0.02  # 2% EWT
            
            # Fill empty gateway fees with 0 to prevent math errors
            df['gateway_fee'] = df['gateway_fee'].fillna(0)

            # A. Platform Earnings (18% of Gross)
            df['Platform_Gross'] = df['Gross_Revenue'] * 0.18
            df['Platform_Tax_Deduct'] = df['Gross_Revenue'] * TAX_RATE * 0.18
            df['Platform_Net_Profit'] = df['Platform_Gross'] - df['Platform_Tax_Deduct']

            # B. Affiliate Share (82% of Gross)
            df['Affiliate_Gross_Share'] = df['Gross_Revenue'] * 0.82
            df['Affiliate_Tax_Deduct'] = df['Gross_Revenue'] * TAX_RATE * 0.82
            
            # THE MOA RULE: Payout = (82% Share - Tax Share) - CC Surcharge (gateway_fee)
            df['Affiliate_Net_Payout'] = (df['Affiliate_Gross_Share'] - df['Affiliate_Tax_Deduct']) - df['gateway_fee']

            # Create clean reference labels
            df['Ref'] = df.apply(lambda x: f"#{x['booking_ref']}" if pd.notnull(x.get('booking_ref')) else f"DRV-{x['id']:05d}", axis=1)
            
            # --- 3. TOP LEVEL METRICS ---
            c1, c2, c3 = st.columns(3)
            c1.metric("💰 Total Platform Gross", f"₱{df['Gross_Revenue'].sum():,.2f}")
            c2.metric("🏢 DriveElite Net Profit", f"₱{df['Platform_Net_Profit'].sum():,.2f}")
            
            pending_payouts = df[(df['Payout_Status'] == 'PENDING') & (df['Trip_Status'] == 'COMPLETED')]['Affiliate_Net_Payout'].sum()
            c3.metric("⏳ Pending Affiliate Payouts", f"₱{pending_payouts:,.2f}", delta="-Liabilities", delta_color="inverse")
            
            # --- 4. SUB-TABS ---
            f_tabs = st.tabs(["📑 MASTER LEDGER", "📤 PROCESS PAYOUTS"])
            
            with f_tabs[0]: 
                # Master Ledger View
                display_cols = ['Ref', 'Date', 'Affiliate', 'Gross_Revenue', 'gateway_fee', 'Affiliate_Net_Payout', 'Platform_Net_Profit', 'Payout_Status']
                st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
            
            with f_tabs[1]:
                # Individual Payout Processing
                pending_df = df[(df['Trip_Status'] == 'COMPLETED') & (df['Payout_Status'] == 'PENDING')]
                if pending_df.empty:
                    st.info("No pending payouts for completed trips.")
                for _, p in pending_df.iterrows():
                    with st.expander(f"{p['Ref']} | {p['Affiliate']} | Net: ₱{p['Affiliate_Net_Payout']:,.2f}"):
                        st.write(f"**Gross Affiliate Share (82%):** ₱{p['Affiliate_Gross_Share']:,.2f}")
                        st.write(f"**Tax Deduction (EWT):** -₱{p['Affiliate_Tax_Deduct']:,.2f}")
                        st.write(f"**CC Gateway Fee (Owner Absorbed):** -₱{p['gateway_fee']:,.2f}")
                        st.divider()
                        st.write(f"**Final Remittance:** ₱{p['Affiliate_Net_Payout']:,.2f}")
                        st.info(f"🏦 **Bank:** {p['bank_name']} | **Acc:** {p['account_no']}")
                        
                        if st.button("MARK AS PAID", key=f"pay_{p['id']}", type="primary", use_container_width=True):
                            conn.execute("UPDATE bookings SET payout_status = 'PAID' WHERE id = ?", (p['id'],))
                            conn.commit()
                            st.rerun()
                            
    except Exception as e:
        st.error(f"Financial Error: {str(e)}")

# --- TAB 4: FILING CABINET (COMPLETELY REDESIGNED) ---
with tabs[4]: 
    st.header("🗄️ Master Digital Filing Cabinet")
    st.write("View legally binding contracts signed by your users.")
    
    if os.path.exists("uploads"):
        # 1. Look for all PDF files
        all_files = os.listdir("uploads")
        pdf_files = [f for f in all_files if f.endswith('.pdf')]
        
        if len(pdf_files) > 0:
            # 2. Add Filter by Role
            st.divider()
            role_filter = st.radio("Filter Contracts:", ["All", "💼 Affiliates (MOA)", "🚙 Renters (Agreements)"], horizontal=True)
            st.divider()
            
            # 3. Apply Filter to File List
            if role_filter == "💼 Affiliates (MOA)":
                filtered_files = [f for f in pdf_files if f.startswith("MOA_")]
            elif role_filter == "🚙 Renters (Agreements)":
                filtered_files = [f for f in pdf_files if f.startswith("RENTER_")]
            else:
                filtered_files = pdf_files
            
            if not filtered_files:
                st.info(f"No documents found matching the filter: {role_filter}")
            else:
                # 4. Create the condensed 4-column grid (Smaller version)
                cols = st.columns(4)
                for i, file_name in enumerate(filtered_files):
                    file_path = os.path.join("uploads", file_name)
                    
                    # --- Naming Logic: Translate Username to Full Name /username ---
                    display_card_text = file_name # Fallback
                    if file_name.startswith("MOA_") or file_name.startswith("RENTER_"):
                        # Extract the username from filename
                        uname = file_name.replace("MOA_", "").replace("RENTER_", "").replace(".pdf", "")
                        
                        try:
                            name_df = pd.read_sql_query("SELECT full_name FROM users WHERE username=?", conn, params=(uname,))
                            if not name_df.empty and name_df.iloc[0]['full_name']:
                                full_name = name_df.iloc[0]['full_name']
                                display_card_text = f"{full_name} /{uname}"
                            else:
                                # No full name in DB, fallback to username format
                                display_card_text = f"(@{uname})"
                        except:
                            pass # Fallback to original file_name if database fails
                    
                    with cols[i % 4]:
                        # Condensed Card Visuals
                        with st.container(border=True):
                            # Displays the elegant format Romeo /mingoy
                            st.write(f"📄 **{display_card_text}**")
                            with open(file_path, "rb") as pdf_file:
                                # Aligned to the left, condensed button text
                                st.download_button(
                                    label="⬇️ DL",
                                    data=pdf_file.read(),
                                    file_name=file_name,
                                    mime="application/pdf",
                                    key=f"dl_{file_name}",
                                    use_container_width=True # Fills the card width
                                )
        else:
            st.info("No contracts have been signed yet.")
    else:
        st.warning("The uploads folder does not exist yet. It will be created when the first user registers.")

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

# --- TAB 6: GLOBAL REVIEWS ---
with tabs[6]:
    st.markdown("<h3 style='text-align: center;'>⭐ MASTER PLATFORM REVIEWS</h3>", unsafe_allow_html=True)
    q_all_reviews = """
        SELECT b.rating, b.review, b.pickup_time, r.full_name as renter_name, a.full_name as affiliate_name, v.make, v.model, v.plate
        FROM bookings b
        JOIN vehicles v ON b.vehicle_id = v.id
        JOIN users r ON b.renter_username = r.username
        JOIN users a ON v.owner_username = a.username
        WHERE b.rating IS NOT NULL ORDER BY b.id DESC
    """
    try:
        all_rev_df = pd.read_sql_query(q_all_reviews, conn)
        if all_rev_df.empty: st.info("No reviews yet.")
        else:
            st.metric("Platform Average Rating", f"{all_rev_df['rating'].mean():.1f} ⭐")
            for _, rev in all_rev_df.iterrows():
                with st.expander(f"{'⭐'*int(rev['rating'])} | {rev['make']} {rev['model']}"):
                    st.write(f"Renter: {rev['renter_name']} | Affiliate: {rev['affiliate_name']}")
                    if rev['review']: st.info(rev['review'])
    except: pass
# --- TOP NAVIGATION BAR ---
# (Keep your existing header code above this)

# WE ADDED "❌ CANCELLATIONS" AS THE 8TH TAB

# ... (Keep all your existing code for tabs[0] through tabs[6] exactly as it is) ...

# --- TAB 7: PROCESS CANCELLATIONS ---
with tabs[7]:
    st.header("Process Cancellations")
    st.write("Select an active booking to calculate cancellation penalties and process refunds.")

    try:
        # 1. Fetch only bookings that have NOT been completed or cancelled yet
        query = """
        SELECT id, booking_ref, renter_username, amount, pickup_time, status 
        FROM bookings 
        WHERE status NOT IN ('COMPLETED', 'CANCELLED')
        """
        active_bookings = pd.read_sql_query(query, conn)

        if active_bookings.empty:
            st.info("There are currently no active bookings eligible for cancellation.")
        else:
            # 2. Create a dropdown menu for the Admin to select the booking
            booking_options = ["-- Select a Booking --"] + active_bookings['booking_ref'].astype(str).tolist()
            selected_ref = st.selectbox("Search Active Bookings:", booking_options)

            if selected_ref != "-- Select a Booking --":
                # 3. Pull the specific data for the selected booking
                b_data = active_bookings[active_bookings['booking_ref'].astype(str) == selected_ref].iloc[0]
                
                booking_to_cancel = b_data['booking_ref']
                gross_paid = float(b_data['amount'])
                pickup_date = str(b_data['pickup_time']) 

                st.divider()
                st.subheader(f"Review Details for #{booking_to_cancel}")
                st.write(f"**Renter:** @{b_data['renter_username']} | **Gross Rental Paid:** ₱{gross_paid:,.2f} | **Pickup:** {pickup_date}")

                # 4. Admin inputs for variables not stored in the main table
                st.write("### Extra Fee Verification")
                col_in1, col_in2 = st.columns(2)
                with col_in1:
                    logistics = st.number_input("Logistics/Delivery Fee Paid (₱)", value=0.0, step=100.0)
                with col_in2:
                    gateway_fee = st.number_input("Exact PayMongo Surcharge to Absorb (₱)", value=0.0, step=10.0)

                st.divider()

                # 5. Run the background math
                try:
                    days_left = get_days_before_pickup(pickup_date)
                    settlement = calculate_moa_cancellation_40_60(
                        gross_rental_paid=gross_paid, 
                        logistics_paid=logistics, 
                        exact_gateway_fee=gateway_fee, 
                        days_before_pickup=days_left
                    )

                    st.info(f"⏳ The Renter is canceling **{days_left} days** before pick-up.")

                    # Show the breakdown to the Admin
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("### 💸 To Renter")
                        st.write(f"Penalty Applied: ₱{settlement['penalty_applied']:,.2f}")
                        st.success(f"Refund Amount: ₱{settlement['renter_refund']:,.2f}")

                    with col2:
                        st.write("### 🏢 To Platform & Affiliate")
                        st.write(f"Platform Cut (40%): ₱{settlement['nucleuz_platform_fee']:,.2f}")
                        st.write(f"Affiliate Payout (60%): ₱{settlement['affiliate_compensation']:,.2f}")

                    # 6. The Final Execution Button
                    if st.button("🚨 Finalize Cancellation & Update Database", type="primary"):
                        
                        conn.execute("UPDATE bookings SET status = 'CANCELLED' WHERE booking_ref = ?", (booking_to_cancel,))
                        conn.commit()
                        
                        sample_receipt_text = f"Your booking {booking_to_cancel} was cancelled. Your 60% compensation is ₱{settlement['affiliate_compensation']:,.2f}."
                        email_success = email_receipt_to_affiliate(
                            affiliate_email="affiliate@test.com", 
                            receipt_text=sample_receipt_text, 
                            transaction_ref=booking_to_cancel
                        )
                        
                        if email_success:
                            st.success("✅ Database updated and email sent to the Affiliate.")
                        else:
                            st.warning("⚠️ Database updated, but the email receipt failed to send.")
                            
                        st.rerun()

                except ValueError:
                    st.error(f"Date Error: The database date '{pickup_date}' is not in the required 'YYYY-MM-DD HH:MM:SS' format.")

    except Exception as e:
        st.error(f"Database connection error: {e}")
