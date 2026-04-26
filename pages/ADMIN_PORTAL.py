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
# 3. IMPORT CUSTOM MODULES (NOW IT CAN FIND THEM)
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
    """Smart viewer: shows images natively, but gives a download button for PDFs."""
    import os
    import streamlit as st
    
    if file_path and str(file_path).strip() and os.path.exists(file_path):
        if str(file_path).lower().endswith('.pdf'):
            with open(file_path, "rb") as f:
                # Give every download button a unique key to prevent Streamlit errors
                safe_key = f"dl_{str(file_path).replace('/', '_').replace('.', '_')}_{title.replace(' ', '')}"
                st.download_button(f"📄 Download {title} (PDF)", f.read(), file_name=os.path.basename(file_path), mime="application/pdf", key=safe_key)
        else:
            st.image(file_path, caption=title, use_container_width=True)
    else:
        st.warning(f"No {title} provided.")

def email_receipt_to_affiliate(affiliate_email, receipt_text, transaction_ref):
    """Sends a cancellation compensation summary to the Affiliate."""
    sender_email = "rdalbaojr@gmail.com" 
    try:
        app_password = st.secrets["email_app_password"]
    except KeyError:
        st.error("Secret 'email_app_password' not found in Streamlit Cloud Settings!")
        return False
        
    msg = EmailMessage()
    msg.set_content(receipt_text)
    msg['Subject'] = f"Cancellation Compensation: {transaction_ref}"
    msg['From'] = f"DriveElite Finance <{sender_email}>"
    msg['To'] = affiliate_email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, app_password)
            smtp.send_message(msg)
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False

def send_pdf_copy(to_email, file_path, file_name):
    """Attaches a PDF from the uploads folder and emails it to the user."""
    from email.mime.multipart import MIMEMultipart
    from email.mime.base import MIMEBase
    from email.mime.text import MIMEText
    from email import encoders
    import smtplib
    
    sender_email = "rdalbaojrh@gmail.com" 
    try:
        app_password = st.secrets["email_app_password"]
    except KeyError:
        return False, "Missing email_app_password in Streamlit Secrets."
        
    msg = MIMEMultipart()
    msg['From'] = f"DriveElite Admin <{sender_email}>"
    msg['To'] = to_email
    msg['Subject'] = f"Your DriveElite Contract Copy: {file_name}"
    msg.attach(MIMEText("Hello,\n\nPer your request or an Admin action, please find attached a secure copy of your signed DriveElite contract.\n\nBest regards,\nThe DriveElite Team", 'plain'))
    
    try:
        with open(file_path, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {file_name}")
        msg.attach(part)
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, app_password)
            server.send_message(msg)
        return True, "Email sent successfully!"
    except Exception as e:
        return False, str(e)


# --- 4. DATABASE PATCH (Auto-Heal) ---
try:
    conn.execute("ALTER TABLE platform_users ADD COLUMN admin_status TEXT")
    conn.commit()
except:
    pass 

# --- 5. AUTHENTICATION ---
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

# --- 6. TOP NAVIGATION BAR ---
head_col1, head_col2 = st.columns([5, 1])
with head_col1:
    st.title("🛡️ MASTER COMMAND CENTER")
with head_col2:
    st.info(f"👨‍💼 {st.session_state.username.upper()}")
    if st.button("🔒 LOGOUT", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# NEW TAB ADDED: DISPUTE CENTER
tabs = st.tabs(["PENDING APPROVALS", "ASSETS", "LOGISTICS", "FINANCIALS", "🗄️ FILING CABINET", "PROMOS & DB", "⭐ REVIEWS", "❌ CANCELLATIONS", "⚖️ DISPUTES"])

# --- TAB 0: PENDING APPROVALS ---
with tabs[0]:
    st.markdown("<h3 style='text-align: center;'>📋 PENDING APPROVALS</h3>", unsafe_allow_html=True)
    p_tabs = st.tabs(["🚙 PENDING RENTERS", "💼 PENDING AFFILIATES", "👨‍✈️ PENDING DRIVERS"])
    
    with p_tabs[0]:
        renters = pd.read_sql_query("SELECT * FROM platform_users WHERE (admin_status = 'PENDING' OR admin_status IS NULL) AND role = 'RENTER'", conn)
        if renters.empty: st.info("No pending renters.")
        for i, r in renters.iterrows():
            with st.expander(f"{r['full_name']} (@{r['username']})"):
                st.write(f"Age: {r['age']} | Nat: {r.get('nationality', 'Filipino')} | Contact: {r['contact_number']}")
                c_img1, c_img2 = st.columns(2)
                if pd.notna(r.get('govt_id_img')) and r.get('govt_id_img'): c_img1.image(r['govt_id_img'], caption="Passport / Govt ID")
                if pd.notna(r.get('license_img')) and r.get('license_img'): c_img2.image(r['license_img'], caption="Driver's License")
                if st.button("APPROVE RENTER", key=f"ra_{r['id']}", type="primary", use_container_width=True):
                    conn.execute("UPDATE platform_users SET admin_status = 'APPROVED' WHERE id = ?", (r['id'],))
                    conn.commit()
                    st.rerun()

    with p_tabs[1]:
        affiliates = pd.read_sql_query("SELECT * FROM platform_users WHERE (admin_status = 'PENDING' OR admin_status IS NULL) AND role = 'AFFILIATE'", conn)
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
                    conn.execute("UPDATE platform_users SET admin_status = 'APPROVED' WHERE id = ?", (r['id'],))
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

# --- TAB 1: ASSETS (ADMIN PORTAL) ---
with tabs[1]:
    pv = pd.read_sql_query("SELECT * FROM vehicles WHERE admin_status = 'PENDING'", conn)
    
    if pv.empty: 
        st.info("No vehicles currently pending approval.")
    else:
        for i, r in pv.iterrows():
            with st.expander(f"🚗 {r['make']} {r['model']} ({r['plate']})"):
                
                # --- NEW: SMART DOCUMENT VIEWER ---
                st.write("### Vehicle Documents")
                c_doc1, c_doc2, c_doc3 = st.columns(3)
                with c_doc1: display_document(r.get('or_img'), "Official Receipt (OR)")
                with c_doc2: display_document(r.get('cr_img'), "Certificate of Reg (CR)")
                with c_doc3: display_document(r.get('insurance_img'), "Insurance Policy")
                st.divider()
                # ----------------------------------
                
                if st.button("✅ APPROVE & ACTIVATE", key=f"v_app_{r['id']}", type="primary", use_container_width=True):
                    # ... your existing approval code ...
                    conn.execute("""
                        UPDATE vehicles 
                        SET admin_status = 'APPROVED', 
                            booking_status = 'AVAILABLE' 
                        WHERE id = ?
                    """, (r['id'],))
                    conn.commit()
                    st.success(f"Success! {r['plate']} is now visible in the Renter Showroom.")
                    time.sleep(1)
                    st.rerun()

# --- TAB 2: LOGISTICS ---
with tabs[2]:
    st.subheader("Active Logistics")
    try:
        query = """
            SELECT b.*, u_renter.full_name as renter_name, u_owner.full_name as affiliate_name 
            FROM bookings b 
            JOIN platform_users u_renter ON b.renter_username = u_renter.username 
            JOIN vehicles v ON b.vehicle_id = v.id 
            JOIN platform_users u_owner ON v.owner_username = u_owner.username 
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
        query = """
        SELECT b.id, b.booking_ref, b.pickup_time as Date, u_renter.full_name as Renter, u_owner.full_name as Affiliate,
               b.amount as Gross_Revenue, b.status as Trip_Status, b.payout_status as Payout_Status,
               b.gateway_fee, v.bank_name, v.account_no
        FROM bookings b
        JOIN vehicles v ON b.vehicle_id = v.id
        JOIN platform_users u_renter ON b.renter_username = u_renter.username
        JOIN platform_users u_owner ON v.owner_username = u_owner.username
        ORDER BY b.id DESC
        """
        df = pd.read_sql_query(query, conn)
        
        if df.empty:
            st.info("No financial transactions recorded yet.")
        else:
            TAX_RATE = 0.02
            df['gateway_fee'] = df['gateway_fee'].fillna(0)

            df['Platform_Gross'] = df['Gross_Revenue'] * 0.18
            df['Platform_Net_Profit'] = df['Platform_Gross'] - (df['Gross_Revenue'] * TAX_RATE * 0.18)

            df['Affiliate_Gross_Share'] = df['Gross_Revenue'] * 0.82
            # --- NEW: ISOLATED EWT COLUMN ---
            df['EWT_Deduction'] = df['Gross_Revenue'] * TAX_RATE * 0.82
            df['Affiliate_Net_Payout'] = (df['Affiliate_Gross_Share'] - df['EWT_Deduction']) - df['gateway_fee']

            df['Ref'] = df.apply(lambda x: f"#{x['booking_ref']}" if pd.notnull(x.get('booking_ref')) else f"DRV-{x['id']:05d}", axis=1)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("💰 Total Gross", f"₱{df['Gross_Revenue'].sum():,.2f}")
            c2.metric("🏢 Platform Net", f"₱{df['Platform_Net_Profit'].sum():,.2f}")
            
            payouts_due = df[(df['Payout_Status'] == 'PENDING') & (df['Trip_Status'] == 'COMPLETED')]['Affiliate_Net_Payout'].sum()
            c3.metric("⏳ Payouts Due", f"₱{payouts_due:,.2f}")
            
            f_tabs = st.tabs(["📑 MASTER LEDGER", "📤 PROCESS PAYOUTS"])
            
            with f_tabs[0]: 
                # --- NEW: ADDED EWT TO DISPLAY COLS ---
                display_cols = ['Ref', 'Date', 'Affiliate', 'Gross_Revenue', 'gateway_fee', 'EWT_Deduction', 'Affiliate_Net_Payout', 'Platform_Net_Profit', 'Payout_Status']
                
                styled_ledger = df[display_cols].style.format({
                    'Gross_Revenue': '{:,.2f}',
                    'gateway_fee': '{:,.2f}',
                    'EWT_Deduction': '{:,.2f}',
                    'Affiliate_Net_Payout': '{:,.2f}',
                    'Platform_Net_Profit': '{:,.2f}'
                })
                
                st.dataframe(styled_ledger, use_container_width=True, hide_index=True)
            
            with f_tabs[1]:
                pending_p = df[(df['Trip_Status'] == 'COMPLETED') & (df['Payout_Status'] == 'PENDING')]
                if pending_p.empty:
                    st.info("No pending payouts for completed trips.")
                for _, p in pending_p.iterrows():
                    with st.expander(f"{p['Ref']} | {p['Affiliate']} | Net: ₱{p['Affiliate_Net_Payout']:,.2f}"):
                        st.write(f"**Gross Affiliate Share (82%):** ₱{p['Affiliate_Gross_Share']:,.2f}")
                        st.write(f"**Tax Deduction (EWT):** -₱{p['EWT_Deduction']:,.2f}")
                        st.write(f"**CC Gateway Fee (Owner Absorbed):** -₱{p['gateway_fee']:,.2f}")
                        st.divider()
                        st.write(f"**Final Remittance:** ₱{p['Affiliate_Net_Payout']:,.2f}")
                        st.info(f"🏦 **Bank:** {p['bank_name']} | **Acc:** {p['account_no']}")
                        
                        if st.button("MARK AS PAID", key=f"p_{p['id']}", type="primary", use_container_width=True):
                            conn.execute("UPDATE bookings SET payout_status = 'PAID' WHERE id = ?", (p['id'],))
                            conn.commit()
                            st.rerun()
    except Exception as e:
        st.error(f"Financial Error: {e}")


# --- TAB 4: FILING CABINET (MAILROOM LOGIC) ---
with tabs[4]: 
    st.header("🗄️ Master Digital Filing Cabinet")
    st.write("View legally binding contracts, download them, or instantly email a copy to the user.")
    
    if os.path.exists("uploads"):
        all_files = os.listdir("uploads")
        pdf_files = [f for f in all_files if f.endswith('.pdf')]
        
        if len(pdf_files) > 0:
            st.divider()
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
                        except:
                            pass 
                    
                    with cols[i % 4]:
                        with st.container(border=True):
                            st.write(f"📄 **{display_card_text}**")
                            
                            btn_col1, btn_col2 = st.columns(2)
                            with btn_col1:
                                with open(file_path, "rb") as pdf_file:
                                    st.download_button(
                                        label="⬇️ DL",
                                        data=pdf_file.read(),
                                        file_name=file_name,
                                        mime="application/pdf",
                                        key=f"dl_{file_name}",
                                        use_container_width=True 
                                    )
                            with btn_col2:
                                if st.button("📧 Email", key=f"em_{file_name}", use_container_width=True):
                                    if not target_email:
                                        st.toast(f"❌ No email found in DB for @{uname}", icon="⚠️")
                                    else:
                                        with st.spinner("Sending..."):
                                            success, msg = send_pdf_copy(target_email, file_path, file_name)
                                            if success:
                                                st.toast(f"✅ Contract sent to {target_email}", icon="🚀")
                                            else:
                                                st.error(f"Failed: {msg}")
        else:
            st.info("No contracts have been signed yet.")
    else:
        st.warning("The uploads folder does not exist yet. It will be created when the first user registers.")


# --- TAB 5: PROMOS & DB ---
with tabs[5]:
    # --- 1. DYNAMIC PRICING & DISCOUNTS TABLE ---
    render_admin_discount_table(conn)
    st.divider()

    # --- 2. EXISTING PROMO & CATEGORY MANAGERS ---
    col_promo, col_cat = st.columns(2)
    with col_promo:
        st.subheader("📢 Broadcast Manager")
        
        # --- NEW: MASTER TOGGLE SWITCH ---
        # Check if there is currently an active broadcast
        current_active = pd.read_sql_query("SELECT id FROM admin_promos WHERE active = 1", conn)
        banner_is_on = not current_active.empty
        
        # Display the sleek toggle bullet
        turn_on = st.toggle("📡 Master Broadcast Switch (Turn ON / OFF)", value=banner_is_on)
        
        # If the toggle is clicked, update the database instantly
        if turn_on != banner_is_on:
            if turn_on:
                # Turn back on the most recently created promo
                conn.execute("UPDATE admin_promos SET active = 1 WHERE id = (SELECT MAX(id) FROM admin_promos)")
                conn.commit()
            else:
                # Turn everything off (hide the banner)
                conn.execute("UPDATE admin_promos SET active = 0")
                conn.commit()
            st.rerun()
        st.divider()
        # ---------------------------------

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
        
    # --- DANGER ZONE: FACTORY RESET ---
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
                    # Clear memory lock
                    try: conn.close() 
                    except: pass
                    st.cache_resource.clear() 
                    st.cache_data.clear() 

                    # 1. Delete Database (Corrected to V2)
                    if os.path.exists("driveelite_v2.db"): 
                        os.remove("driveelite_v2.db")
                    
                    # 2. Delete Uploads
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
        WHERE status NOT IN ('COMPLETED', 'CANCELLED')
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
            # Dropdown to select a trip
            dispute_opts = ["-- Select a Trip to Audit --"] + completed_trips['booking_ref'].astype(str).tolist()
            selected_trip = st.selectbox("Select Trip Ref:", dispute_opts)
            
            if selected_trip != "-- Select a Trip to Audit --":
                d_data = completed_trips[completed_trips['booking_ref'].astype(str) == selected_trip].iloc[0]
                
                st.divider()
                # 1. Contact Information Block
                st.markdown(f"### 📋 Audit File: #{d_data['booking_ref']} | {d_data['make']} {d_data['model']} ({d_data['plate']})")
                c_rent, c_aff = st.columns(2)
                with c_rent:
                    st.info(f"**Renter:** {d_data['renter_name']}\n\n📞 {d_data['r_phone']}\n\n✉️ {d_data['r_email']}")
                with c_aff:
                    st.info(f"**Affiliate:** {d_data['affiliate_name']}\n\n📞 {d_data['a_phone']}\n\n✉️ {d_data['a_email']}")
                
                st.divider()
                st.markdown("<h3 style='text-align: center;'>📸 Visual Evidence Comparison</h3>", unsafe_allow_html=True)
                
                # 2. Side-by-Side Photo Comparison
                col_before, col_after = st.columns(2)
                
                with col_before:
                    st.markdown("#### 🟢 BEFORE (Handover Photos)")
                    if pd.notna(d_data.get('handover_photos')) and str(d_data['handover_photos']).strip():
                        # Split the comma-separated string back into a list of file paths
                        h_photos = str(d_data['handover_photos']).split(',')
                        for img_path in h_photos:
                            if os.path.exists(img_path.strip()):
                                st.image(img_path.strip(), use_container_width=True)
                    else:
                        st.warning("No handover photos were logged for this trip.")
                
                with col_after:
                    st.markdown("#### 🔴 AFTER (Reported Damage)")
                    if pd.notna(d_data.get('damage_img')) and str(d_data['damage_img']).strip():
                        # Split the comma-separated string back into a list of file paths
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
