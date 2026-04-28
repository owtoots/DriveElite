import sys
import os
import smtplib
from email.message import EmailMessage
import streamlit as st
import pandas as pd
import datetime
import numpy as np
import time
import random
from PIL import Image

# ==========================================
# 1. PAGE CONFIG (MUST BE THE VERY FIRST ST COMMAND)
# ==========================================
st.set_page_config(page_title="DriveElite Admin", layout="wide")

# ==========================================
# 2. FORCE ROOT DIRECTORY VISIBILITY (THE PERISCOPE)
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# ==========================================
# 3. IMPORT CUSTOM MODULES
# ==========================================
from database_utils import get_connection, init_db, patch_database
from tiered_discounts import init_discount_db, render_admin_discount_table

try:
    from finance import get_days_before_pickup, calculate_moa_cancellation_40_60
except ImportError:
    st.error("Missing finance.py! Please ensure the finance script is in your root folder.")

# ==========================================
# 4. INITIALIZE DATABASE
# ==========================================
conn = get_connection()
init_db()
patch_database()
init_discount_db(conn)

# ==========================================
# 5. ADMIN UI STARTS HERE
# ==========================================
st.title("👑 DriveElite Admin Portal")

st.divider()

# --- 3. UTILITY FUNCTIONS ---
def display_document(file_path, title):
    import os
    import streamlit as st
    if file_path and str(file_path).strip() and os.path.exists(file_path):
        if str(file_path).lower().endswith('.pdf'):
            with open(file_path, "rb") as f:
                safe_key = f"dl_{str(file_path).replace('/', '_').replace('.', '_')}_{title.replace(' ', '')}"
                st.download_button(f"📄 Download {title} (PDF)", f.read(), file_name=os.path.basename(file_path), mime="application/pdf", key=safe_key)
        else:
            st.image(file_path, caption=title, use_container_width=True)
    else:
        st.warning(f"No {title} provided.")

def email_receipt_to_affiliate(affiliate_email, receipt_text, transaction_ref):
    sender_email = "rdalbaojr@gmail.com"
    try:
        # Securely fetch the app password from your Streamlit Cloud vault
        app_password = st.secrets["email_app_password"]
        
        msg = EmailMessage()
        msg.set_content(receipt_text)
        msg['Subject'] = f"DriveElite Payout Receipt - Ref: {transaction_ref}"
        msg['From'] = sender_email
        msg['To'] = affiliate_email

        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender_email, app_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Email failed to send: {e}")
        return False

# ==========================================
# 6. MAIN ADMIN DASHBOARD TABS
# ==========================================
tabs = st.tabs(["🚀 Active Bookings", "👥 Approvals", "💰 Finance & Commissions"])

# --- TAB 1: ACTIVE BOOKINGS ---
with tabs[0]:
    st.header("Live Fleet Monitor")
    
    # Fetch all bookings that are not cancelled
    bookings_df = pd.read_sql_query("""
        SELECT b.id, b.booking_ref, b.renter_username, v.make, v.model, v.owner_username, 
               b.pickup_time, b.return_time, b.amount, b.status 
        FROM bookings b 
        JOIN vehicles v ON b.vehicle_id = v.id 
        ORDER BY b.pickup_time DESC
    """, conn)
    
    if bookings_df.empty:
        st.info("No active bookings in the system right now.")
    else:
        # Highlight PENDING bookings (ones waiting for PayMongo confirmation)
        pending_count = len(bookings_df[bookings_df['status'] == 'PENDING'])
        if pending_count > 0:
            st.warning(f"⚠️ You have {pending_count} PENDING bookings awaiting payment confirmation.")
            
        st.dataframe(bookings_df, use_container_width=True, hide_index=True)
        
        st.divider()
        st.subheader("Manual Booking Override")
        col1, col2 = st.columns(2)
        with col1:
            ref_to_update = st.selectbox("Select Booking Reference", bookings_df['booking_ref'].tolist())
        with col2:
            new_status = st.selectbox("Update Status To:", ["CONFIRMED", "ONGOING", "COMPLETED", "CANCELLED"])
            
        if st.button("Update Booking Status", type="primary"):
            conn.execute("UPDATE bookings SET status = ? WHERE booking_ref = ?", (new_status, ref_to_update))
            conn.commit()
            st.success(f"Booking #{ref_to_update} successfully marked as {new_status}!")
            time.sleep(1)
            st.rerun()

# --- TAB 2: USER & VEHICLE APPROVALS ---
with tabs[1]:
    st.header("Pending Approvals")
    u_col, v_col = st.columns(2)
    
    with u_col:
        st.subheader("Pending Users")
        users_df = pd.read_sql_query("SELECT id, username, role, first_name, last_name FROM platform_users WHERE admin_status = 'PENDING'", conn)
        if users_df.empty:
            st.success("All users approved!")
        else:
            for _, u in users_df.iterrows():
                with st.expander(f"{u['role']}: {u['first_name']} {u['last_name']} (@{u['username']})"):
                    if st.button("Approve User", key=f"app_u_{u['id']}"):
                        conn.execute("UPDATE platform_users SET admin_status = 'APPROVED' WHERE id = ?", (u['id'],))
                        conn.commit()
                        st.success("Approved!")
                        time.sleep(1)
                        st.rerun()
                        
    with v_col:
        st.subheader("Pending Vehicles")
        veh_df = pd.read_sql_query("SELECT id, make, model, year, owner_username, requested_price FROM vehicles WHERE admin_status = 'PENDING'", conn)
        if veh_df.empty:
            st.success("All vehicles approved!")
        else:
            for _, v in veh_df.iterrows():
                with st.expander(f"{v['make']} {v['model']} ({v['year']}) - @{v['owner_username']}"):
                    st.write(f"Requested Daily Rate: ₱{v['requested_price']:,.2f}")
                    if st.button("Approve Vehicle", key=f"app_v_{v['id']}"):
                        conn.execute("UPDATE vehicles SET admin_status = 'APPROVED', booking_status = 'AVAILABLE', approved_price = ? WHERE id = ?", (v['requested_price'], v['id']))
                        conn.commit()
                        st.success("Vehicle Live!")
                        time.sleep(1)
                        st.rerun()

# --- TAB 3: FINANCE & COMMISSIONS ---
with tabs[2]:
    st.header("DriveElite Financial Ledger")
    
    # We only calculate payouts for trips that are officially confirmed or completed
    finance_df = pd.read_sql_query("""
        SELECT b.booking_ref, b.pickup_time, b.amount, b.status, v.owner_username 
        FROM bookings b 
        JOIN vehicles v ON b.vehicle_id = v.id 
        WHERE b.status IN ('CONFIRMED', 'COMPLETED')
    """, conn)
    
    if finance_df.empty:
        st.info("No completed or confirmed paid transactions yet.")
    else:
        # --- THE 20/80 SPLIT ENGINE ---
        finance_df['DriveElite_Cut_20'] = finance_df['amount'] * 0.20
        finance_df['Affiliate_Payout_80'] = finance_df['amount'] * 0.80
        
        total_revenue = finance_df['amount'].sum()
        total_platform_profit = finance_df['DriveElite_Cut_20'].sum()
        total_owed_to_owners = finance_df['Affiliate_Payout_80'].sum()
        
        # Top-level metric cards
        m1, m2, m3 = st.columns(3)
        m1.metric("Gross Platform Volume", f"₱{total_revenue:,.2f}")
        m2.metric("DriveElite Net Profit (20%)", f"₱{total_platform_profit:,.2f}", delta="Platform Retained")
        m3.metric("Pending Affiliate Payouts (80%)", f"₱{total_owed_to_owners:,.2f}", delta="-Owed", delta_color="inverse")
        
        st.divider()
        st.subheader("Detailed Affiliate Payout Log")
        
        # Clean up the table for the admin view
        display_df = finance_df[['booking_ref', 'owner_username', 'amount', 'DriveElite_Cut_20', 'Affiliate_Payout_80', 'status']]
        display_df.columns = ['Ref #', 'Car Owner', 'Gross Paid', 'Platform Cut (20%)', 'Owner Payout (80%)', 'Status']
        
        # Format as currency
        for col in ['Gross Paid', 'Platform Cut (20%)', 'Owner Payout (80%)']:
            display_df[col] = display_df[col].apply(lambda x: f"₱{x:,.2f}")
            
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        st.info("💡 When PayMongo clears a customer's transaction, use the 'Active Bookings' tab to mark the trip as CONFIRMED. It will automatically route to this ledger and calculate the exact 20/80 split.")

# --- TAB 4: FILING CABINET (MAILROOM LOGIC) ---
with tabs[4]: 
    st.header("🗄️ Master Digital Filing Cabinet")
    st.write("View legally binding contracts, download them, or instantly email a copy to the user.")
    
    doc_type = st.radio("Select Document Type to View:", ["💼 Legal Contracts (PDFs)", "🧾 Service Booking Receipts"], horizontal=True)
    st.divider()

    # ==========================================
    # ROUTE A: LEGAL CONTRACTS (MOAs & Agreements)
    # ==========================================
    if doc_type == "💼 Legal Contracts (PDFs)":
        if os.path.exists("uploads"):
            all_files = os.listdir("uploads")
            pdf_files = [f for f in all_files if f.endswith('.pdf')]
            
            if len(pdf_files) > 0:
                role_filter = st.radio("Filter Contracts:", ["All", "💼 Affiliates (MOA)", "🚙 Renters (Agreements)"], horizontal=True)
                st.divider()
                
                if role_filter == "💼 Affiliates (MOA)":
                    filtered_files = [f for f in pdf_files if f.startswith("MOA_")]
                elif role_filter == "🚙 Renters (Agreements)":
                    filtered_files = [f for f in pdf_files if f.startswith("RENTER_")]
                else:
                    filtered_files = pdf_files
                
                if not filtered_files:
                    st.info(f"No documents found matching the filter: {role_filter}")
                else:
                    cols = st.columns(4)
                    for i, file_name in enumerate(filtered_files):
                        file_path = os.path.join("uploads", file_name)
                        
                        display_card_text = file_name 
                        uname = ""
                        target_email = ""
                        
                        if file_name.startswith("MOA_") or file_name.startswith("RENTER_"):
                            uname = file_name.replace("MOA_", "").replace("RENTER_", "").replace(".pdf", "")
                            try:
                                user_df = pd.read_sql_query("SELECT full_name, email FROM platform_users WHERE username=?", conn, params=(uname,))
                                if not user_df.empty:
                                    target_email = user_df.iloc[0]['email']
                                    full_name = user_df.iloc[0]['full_name']
                                    display_card_text = f"{full_name} / {uname}" if full_name else f"(@{uname})"
                            except: pass 
                        
                        with cols[i % 4]:
                            with st.container(border=True):
                                st.write(f"📄 **{display_card_text}**")
                                
                                btn_col1, btn_col2 = st.columns(2)
                                with btn_col1:
                                    with open(file_path, "rb") as pdf_file:
                                        st.download_button(label="⬇️ DL", data=pdf_file.read(), file_name=file_name, mime="application/pdf", key=f"dl_{file_name}", use_container_width=True)
                                        
                                with btn_col2:
                                    if st.button("📧 Email", key=f"em_{file_name}", use_container_width=True):
                                        if not target_email:
                                            st.toast(f"❌ No email found in DB for @{uname}", icon="⚠️")
                                        else:
                                            with st.spinner("Sending..."):
                                                success, msg = send_pdf_copy(target_email, file_path, file_name)
                                                if success: st.toast(f"✅ Contract sent to {target_email}", icon="🚀")
                                                else: st.error(f"Failed: {msg}")
            else:
                st.info("No contracts have been signed yet.")
        else:
            st.warning("The uploads folder does not exist yet. It will be created when the first user registers.")

    # ==========================================
    # ROUTE B: ON-DEMAND BOOKING RECEIPTS
    # ==========================================
    elif doc_type == "🧾 Service Booking Receipts":
        st.subheader("🧾 On-Demand Receipt Generator")
        
        try:
            settings_df = pd.read_sql_query("SELECT renter_markup_pct, affiliate_share_pct FROM platform_settings WHERE id = 1", conn)
            r_markup = float(settings_df.iloc[0]['renter_markup_pct']) if not settings_df.empty else 0.00
            a_share = float(settings_df.iloc[0]['affiliate_share_pct']) if not settings_df.empty else 0.82
        except:
            r_markup, a_share = 0.00, 0.82

        receipt_query = """
            SELECT b.booking_ref, b.pickup_time, b.return_time, b.amount, b.status, 
                   r.full_name as renter_name, r.email as renter_email, r.username as renter_user,
                   v.make, v.model, v.plate,
                   a.full_name as affiliate_name, a.email as affiliate_email
            FROM bookings b
            JOIN vehicles v ON b.vehicle_id = v.id
            JOIN platform_users r ON b.renter_username = r.username
            JOIN platform_users a ON v.owner_username = a.username
            WHERE b.status != 'PENDING'
            ORDER BY b.id DESC
        """
        try:
            receipt_df = pd.read_sql_query(receipt_query, conn)
            if receipt_df.empty:
                st.info("No paid bookings exist in the database yet.")
            else:
                opts = ["-- Select a Booking Reference --"] + receipt_df['booking_ref'].astype(str).tolist()
                selected_ref = st.selectbox("Search paid bookings:", opts)

                if selected_ref != "-- Select a Booking Reference --":
                    b_data = receipt_df[receipt_df['booking_ref'].astype(str) == selected_ref].iloc[0]
                    
                    # DYNAMIC MATH CALCULATIONS
                    gross_paid = float(b_data['amount'])
                    base_rate = gross_paid / (1 + r_markup)
                    platform_fee_renter = gross_paid - base_rate
                    
                    affiliate_payout = base_rate * a_share
                    platform_commission_owner = base_rate * (1 - a_share)
                    
                    # --- RENTER RECEIPT TEXT ---
                    renter_receipt_text = f"""======================================
DRIVEELITE OFFICIAL RECEIPT
======================================
Booking Reference: #{b_data['booking_ref']}
Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}

RENTER DETAILS:
Name: {b_data['renter_name']} (@{b_data['renter_user']})

VEHICLE DETAILS:
Unit: {b_data['make']} {b_data['model']} ({b_data['plate']})

FINANCIAL BREAKDOWN:
Base Rental Rate:        PHP {base_rate:,.2f}
Platform Fee ({int(r_markup*100)}%):       PHP {platform_fee_renter:,.2f}
--------------------------------------
TOTAL AMOUNT PAID:       PHP {gross_paid:,.2f}
======================================"""

                    # --- AFFILIATE RECEIPT TEXT ---
                    affiliate_receipt_text = f"""======================================
DRIVEELITE PARTNER PAYOUT SUMMARY
======================================
Booking Reference: #{b_data['booking_ref']}
Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}

AFFILIATE DETAILS:
Name: {b_data['affiliate_name']}
Unit: {b_data['make']} {b_data['model']} ({b_data['plate']})

FINANCIAL BREAKDOWN:
Base Rental Assessed:    PHP {base_rate:,.2f}
Platform Comm. ({int((1-a_share)*100)}%):   -PHP {platform_commission_owner:,.2f}
--------------------------------------
NET PAYOUT DUE:          PHP {affiliate_payout:,.2f}
======================================"""

                    st.divider()
                    col_receipt, col_actions = st.columns([2, 1])
                    
                    with col_receipt:
                        st.write("👀 **Preview (Renter View)**")
                        st.code(renter_receipt_text, language='text')
                        
                    with col_actions:
                        st.write("### 🛠️ Transmit Receipts")
                        
                        if st.button("📧 Email to Renter", type="primary", use_container_width=True):
                            with st.spinner("Transmitting to Renter..."):
                                try:
                                    msg = EmailMessage()
                                    msg['Subject'] = f'DriveElite: Official Receipt #{b_data["booking_ref"]}'
                                    msg['From'] = 'rdalbaojr@gmail.com'
                                    msg['To'] = b_data['renter_email']
                                    msg.set_content(renter_receipt_text)
                                    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                                        smtp.login('rdalbaojr@gmail.com', st.secrets["email_app_password"])
                                        smtp.send_message(msg)
                                    st.success(f"✅ Sent to Renter!")
                                except Exception as e:
                                    st.error(f"❌ Failed: {e}")
                                    
                        if st.button("📧 Email to Affiliate", use_container_width=True):
                            with st.spinner("Transmitting to Affiliate..."):
                                try:
                                    msg = EmailMessage()
                                    msg['Subject'] = f'DriveElite: Partner Payout #{b_data["booking_ref"]}'
                                    msg['From'] = 'rdalbaojr@gmail.com'
                                    msg['To'] = b_data['affiliate_email']
                                    msg.set_content(affiliate_receipt_text)
                                    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                                        smtp.login('rdalbaojr@gmail.com', st.secrets["email_app_password"])
                                        smtp.send_message(msg)
                                    st.success(f"✅ Sent to Affiliate!")
                                except Exception as e:
                                    st.error(f"❌ Failed: {e}")
        except Exception as e:
            st.error(f"Error querying database: {e}")


# --- TAB 5: PROMOS & DB ---
with tabs[5]:
    render_admin_discount_table(conn)
    st.divider()

    col_promo, col_cat = st.columns(2)
    with col_promo:
        st.subheader("📢 Broadcast Manager")
        
        current_active = pd.read_sql_query("SELECT id FROM admin_promos WHERE active = 1", conn)
        banner_is_on = not current_active.empty
        turn_on = st.toggle("📡 Master Broadcast Switch (Turn ON / OFF)", value=banner_is_on)
        
        if turn_on != banner_is_on:
            if turn_on:
                conn.execute("UPDATE admin_promos SET active = 1 WHERE id = (SELECT MAX(id) FROM admin_promos)")
                conn.commit()
            else:
                conn.execute("UPDATE admin_promos SET active = 0")
                conn.commit()
            st.rerun()
        st.divider()

        with st.form("promo"):
            t = st.text_input("Broadcast Title")
            m = st.text_area("Broadcast Message")
            target = st.radio("Target Audience:", ["RENTERS", "AFFILIATES", "ALL USERS"], horizontal=True)
            
            if st.form_submit_button("PUBLISH NEW BROADCAST"):
                if t and m:
                    try:
                        conn.execute("ALTER TABLE admin_promos ADD COLUMN target TEXT DEFAULT 'ALL USERS'")
                        conn.commit()
                    except: pass
                    
                    conn.execute("UPDATE admin_promos SET active = 0")
                    conn.execute("INSERT INTO admin_promos (title, message, target) VALUES (?, ?, ?)", (t, m, target))
                    conn.commit()
                    st.success(f"Live! Broadcast successfully published to {target}.")
                    time.sleep(1)
                    st.rerun()
                    
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
    u_df = pd.read_sql_query("SELECT full_name, role, govt_id_img, license_img FROM platform_users WHERE admin_status = 'APPROVED'", conn)
    try:
        d_df = pd.read_sql_query("SELECT first_name || ' ' || last_name AS full_name, 'DRIVER' AS role, id_img AS govt_id_img, license_img FROM drivers WHERE admin_status = 'APPROVED'", conn)
        all_profiles = pd.concat([u_df, d_df], ignore_index=True)
    except:
        all_profiles = u_df 

    if not all_profiles.empty:
        all_profiles['display_name'] = all_profiles['full_name']
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
        
        q_renters = "SELECT full_name as 'FULLNAME', address as 'ADDRESS', contact_number as 'CONTACT NO.', admin_status as 'STATUS' FROM platform_users WHERE role='RENTER'"
        with db_tabs[0]: st.dataframe(pd.read_sql_query(q_renters, conn), hide_index=True, use_container_width=True)
        
        q_affiliates = "SELECT full_name as 'FULLNAME', address as 'ADDRESS', contact_number as 'CONTACT NO.', admin_status as 'STATUS' FROM platform_users WHERE role='AFFILIATE'"
        with db_tabs[1]: st.dataframe(pd.read_sql_query(q_affiliates, conn), hide_index=True, use_container_width=True)
        
        q_drivers = "SELECT first_name || ' ' || last_name as 'FULLNAME', owner_username as 'BELONGS TO AFFILIATE', contact_number as 'CONTACT NO.', admin_status as 'STATUS' FROM drivers"
        with db_tabs[2]: st.dataframe(pd.read_sql_query(q_drivers, conn), hide_index=True, use_container_width=True)
    except: 
        pass
        
    st.divider()
    st.markdown("<h3 style='text-align: center; color: #e74c3c;'>⚠️ DANGER ZONE</h3>", unsafe_allow_html=True)
    
    with st.expander("🧨 CLOUD FACTORY RESET (Wipe All Data)"):
        st.warning("WARNING: This will permanently delete the live database and all uploaded files (photos, PDFs, signatures). The platform will revert to Day 1.")
        confirm_text = st.text_input("Type 'DELETE EVERYTHING' to confirm:")
        
        if st.button("🔥 INITIATE FACTORY RESET", type="primary", use_container_width=True):
            if confirm_text == "DELETE EVERYTHING":
                import os, glob
                import time
                
                with st.spinner("Disconnecting and Nuking database..."):
                    try: conn.close() 
                    except: pass
                    st.cache_resource.clear() 
                    st.cache_data.clear() 

                    if os.path.exists("driveelite_v2.db"): 
                        os.remove("driveelite_v2.db")
                    
                    if os.path.exists("uploads"):
                        files = glob.glob("uploads/*")
                        for f in files:
                            try: os.remove(f)
                            except: pass
                    
                    st.success("✅ FACTORY RESET COMPLETE! Rebooting system...")
                    time.sleep(3)
                    st.rerun()
            else:
                st.error("You must type exactly 'DELETE EVERYTHING' to unlock the reset button.")

# --- TAB 6: GLOBAL REVIEWS ---
with tabs[6]:
    st.markdown("<h3 style='text-align: center;'>⭐ MASTER PLATFORM REVIEWS</h3>", unsafe_allow_html=True)
    q_all_reviews = """
        SELECT b.rating, b.review, b.pickup_time, r.full_name as renter_name, a.full_name as affiliate_name, v.make, v.model, v.plate
        FROM bookings b
        JOIN vehicles v ON b.vehicle_id = v.id
        JOIN platform_users r ON b.renter_username = r.username
        JOIN platform_users a ON v.owner_username = a.username
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

# --- TAB 7: PROCESS CANCELLATIONS ---
with tabs[7]:
    st.header("Process Cancellations")
    st.write("Select an active booking to calculate cancellation penalties and process refunds.")

    try:
        query = """
        SELECT id, booking_ref, renter_username, amount, pickup_time, status 
        FROM bookings 
        WHERE status NOT IN ('COMPLETED', 'CANCELLED', 'PENDING')
        """
        active_bookings = pd.read_sql_query(query, conn)

        if active_bookings.empty:
            st.info("There are currently no active bookings eligible for cancellation.")
        else:
            booking_options = ["-- Select a Booking --"] + active_bookings['booking_ref'].astype(str).tolist()
            selected_ref = st.selectbox("Search Active Bookings:", booking_options)

            if selected_ref != "-- Select a Booking --":
                b_data = active_bookings[active_bookings['booking_ref'].astype(str) == selected_ref].iloc[0]
                
                booking_to_cancel = b_data['booking_ref']
                gross_paid = float(b_data['amount'])
                pickup_date = str(b_data['pickup_time']) 

                st.divider()
                st.subheader(f"Review Details for #{booking_to_cancel}")
                st.write(f"**Renter:** @{b_data['renter_username']} | **Gross Rental Paid:** ₱{gross_paid:,.2f} | **Pickup:** {pickup_date}")

                st.write("### Extra Fee Verification")
                col_in1, col_in2 = st.columns(2)
                with col_in1:
                    logistics = st.number_input("Logistics/Delivery Fee Paid (₱)", value=0.0, step=100.0)
                with col_in2:
                    gateway_fee = st.number_input("Exact PayMongo Surcharge to Absorb (₱)", value=0.0, step=10.0)

                st.divider()

                try:
                    if len(pickup_date) == 16:
                        pickup_date += ":00"

                    days_left = get_days_before_pickup(pickup_date)
                    settlement = calculate_moa_cancellation_40_60(
                        gross_rental_paid=gross_paid, 
                        logistics_paid=logistics, 
                        exact_gateway_fee=gateway_fee, 
                        days_before_pickup=days_left
                    )

                    st.info(f"⏳ The Renter is canceling **{days_left} days** before pick-up.")

                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("### 💸 To Renter")
                        st.write(f"Penalty Applied: ₱{settlement['penalty_applied']:,.2f}")
                        st.success(f"Refund Amount: ₱{settlement['renter_refund']:,.2f}")

                    with col2:
                        st.write("### 🏢 To Platform & Affiliate")
                        st.write(f"Platform Cut (40%): ₱{settlement['nucleuz_platform_fee']:,.2f}")
                        st.write(f"Affiliate Payout (60%): ₱{settlement['affiliate_compensation']:,.2f}")

                    if st.button("🚨 Finalize Cancellation & Update Database", type="primary"):
                        
                        conn.execute("UPDATE bookings SET status = 'CANCELLED' WHERE booking_ref = ?", (booking_to_cancel,))
                        conn.commit()
                        
                        sample_receipt_text = (
                            f"DriveElite Cancellation Notice\n"
                            f"Booking Ref: {booking_to_cancel}\n"
                            f"Status: CANCELLED\n\n"
                            f"Financial Breakdown:\n"
                            f"Penalty Collected from Renter: ₱{settlement['penalty_applied']:,.2f}\n"
                            f"Your Compensation (60%): ₱{settlement['affiliate_compensation']:,.2f}\n\n"
                            f"This will be included in your next payout cycle."
                        )
                        
                        aff_q = """
                            SELECT u.email FROM platform_users u 
                            JOIN vehicles v ON v.owner_username = u.username 
                            JOIN bookings b ON b.vehicle_id = v.id 
                            WHERE b.booking_ref = ?
                        """
                        aff_data = pd.read_sql_query(aff_q, conn, params=(booking_to_cancel,))
                        target_email = aff_data.iloc[0]['email'] if not aff_data.empty else "rdalbaojrh@gmail.com"

                        email_success = email_receipt_to_affiliate(target_email, sample_receipt_text, booking_to_cancel)
                        
                        if email_success:
                            st.success(f"✅ Cancelled! Compensation email sent to {target_email}.")
                        else:
                            st.warning("⚠️ Database updated, but the email failed to send.")
                            
                        st.rerun()

                except ValueError as ve:
                    st.error(f"Date Error: {ve}. Ensure date format is YYYY-MM-DD HH:MM:SS")

    except Exception as e:
        st.error(f"Database connection error: {e}")

# --- TAB 8: DISPUTE CENTER & EVIDENCE VIEWER ---
with tabs[8]:
    st.header("⚖️ Master Dispute & Evidence Center")
    st.write("Review Before & After photos for completed trips to mediate disputes.")
    
    try:
        q_completed = """
            SELECT b.id, b.booking_ref, b.handover_photos, b.damage_img, 
                   r.full_name as renter_name, r.contact_number as r_phone, r.email as r_email,
                   a.full_name as affiliate_name, a.contact_number as a_phone, a.email as a_email,
                   v.make, v.model, v.plate
            FROM bookings b
            JOIN vehicles v ON b.vehicle_id = v.id
            JOIN platform_users r ON b.renter_username = r.username
            JOIN platform_users a ON v.owner_username = a.username
            WHERE b.status = 'COMPLETED'
            ORDER BY b.id DESC
        """
        completed_trips = pd.read_sql_query(q_completed, conn)
        
        if completed_trips.empty:
            st.info("No completed trips available for review.")
        else:
            dispute_opts = ["-- Select a Trip to Audit --"] + completed_trips['booking_ref'].astype(str).tolist()
            selected_trip = st.selectbox("Select Trip Ref:", dispute_opts)
            
            if selected_trip != "-- Select a Trip to Audit --":
                d_data = completed_trips[completed_trips['booking_ref'].astype(str) == selected_trip].iloc[0]
                
                st.divider()
                st.markdown(f"### 📋 Audit File: #{d_data['booking_ref']} | {d_data['make']} {d_data['model']} ({d_data['plate']})")
                c_rent, c_aff = st.columns(2)
                with c_rent:
                    st.info(f"**Renter:** {d_data['renter_name']}\n\n📞 {d_data['r_phone']}\n\n✉️ {d_data['r_email']}")
                with c_aff:
                    st.info(f"**Affiliate:** {d_data['affiliate_name']}\n\n📞 {d_data['a_phone']}\n\n✉️ {d_data['a_email']}")
                
                st.divider()
                st.markdown("<h3 style='text-align: center;'>📸 Visual Evidence Comparison</h3>", unsafe_allow_html=True)
                
                col_before, col_after = st.columns(2)
                
                with col_before:
                    st.markdown("#### 🟢 BEFORE (Handover Photos)")
                    if pd.notna(d_data.get('handover_photos')) and str(d_data['handover_photos']).strip():
                        h_photos = str(d_data['handover_photos']).split(',')
                        for img_path in h_photos:
                            if os.path.exists(img_path.strip()):
                                st.image(img_path.strip(), use_container_width=True)
                    else:
                        st.warning("No handover photos were logged for this trip.")
                
                with col_after:
                    st.markdown("#### 🔴 AFTER (Reported Damage)")
                    if pd.notna(d_data.get('damage_img')) and str(d_data['damage_img']).strip():
                        d_photos = str(d_data['damage_img']).split(',')
                        for img_path in d_photos:
                            if os.path.exists(img_path.strip()):
                                st.image(img_path.strip(), use_container_width=True)
                    else:
                        st.success("✅ No damage was reported upon return.")
                        
                st.divider()
                st.write("*Admin Note: If a penalty or deduction is required from the security deposit, please contact both parties directly using the phone numbers provided above to finalize mediation.*")
                
    except Exception as e:
        st.error(f"Error loading evidence center: {e}")
