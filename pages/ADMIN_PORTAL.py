import smtplib
from email.message import EmailMessage
import streamlit as st
import pandas as pd
import datetime
import os
import numpy as np
import time
import random 
from PIL import Image
from database_utils import get_connection

# --- 1. FINANCE LOGIC IMPORT ---
# Ensure finance.py is in your main folder!
try:
    from finance import get_days_before_pickup, calculate_moa_cancellation_40_60
except ImportError:
    st.error("Missing finance.py! Please ensure the finance script is in your root folder.")

# --- 2. CONFIG & INITIALIZATION ---
# This MUST be the first Streamlit command
st.set_page_config(page_title="DriveElite Admin", layout="wide")
conn = get_connection()

# --- 3. UTILITY FUNCTIONS ---
def email_receipt_to_affiliate(affiliate_email, receipt_text, transaction_ref):
    """Sends a cancellation compensation summary to the Affiliate."""
    sender_email = "rdalbaojrh@gmail.com" 
    # Grab the password securely from your Streamlit Secrets
    try:
        app_password = st.secrets["email_app_password"]
    except KeyError:
        st.error("Secret 'email_app_password' not found in Streamlit Cloud Settings!")
        return False
    # ... inside email_receipt_to_affiliate ...
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False

  # --- NEW MAILROOM FUNCTION GOES RIGHT HERE (Line 51) ---
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
# ... (the rest of the send_pdf_copy function) ...
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

tabs = st.tabs(["PENDING APPROVALS", "ASSETS", "LOGISTICS", "FINANCIALS", "🗄️ FILING CABINET", "PROMOS & DB", "⭐ REVIEWS", "❌ CANCELLATIONS"])

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
            df['Affiliate_Net_Payout'] = (df['Affiliate_Gross_Share'] - (df['Gross_Revenue'] * TAX_RATE * 0.82)) - df['gateway_fee']
            df['Ref'] = df.apply(lambda x: f"#{x['booking_ref']}" if pd.notnull(x.get('booking_ref')) else f"DRV-{x['id']:05d}", axis=1)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("💰 Total Gross", f"₱{df['Gross_Revenue'].sum():,.2f}")
            c2.metric("🏢 Platform Net", f"₱{df['Platform_Net_Profit'].sum():,.2f}")
            
            payouts_due = df[(df['Payout_Status'] == 'PENDING') & (df['Trip_Status'] == 'COMPLETED')]['Affiliate_Net_Payout'].sum()
            c3.metric("⏳ Payouts Due", f"₱{payouts_due:,.2f}")
            
            f_tabs = st.tabs(["📑 MASTER LEDGER", "📤 PROCESS PAYOUTS"])
            with f_tabs[0]: st.dataframe(df, use_container_width=True, hide_index=True)
            with f_tabs[1]:
                pending_p = df[(df['Trip_Status'] == 'COMPLETED') & (df['Payout_Status'] == 'PENDING')]
                for _, p in pending_p.iterrows():
                    with st.expander(f"{p['Ref']} | {p['Affiliate']} | Net: ₱{p['Affiliate_Net_Payout']:,.2f}"):
                        if st.button("MARK AS PAID", key=f"p_{p['id']}", type="primary", use_container_width=True):
                            conn.execute("UPDATE bookings SET payout_status = 'PAID' WHERE id = ?", (p['id'],))
                            conn.commit(); st.rerun()
    except Exception as e: st.error(f"Financial Error: {e}")

# --- TAB 4: FILING CABINET ---
with tabs[4]:
    st.header("🗄️ Master Filing Cabinet")
    if os.path.exists("uploads"):
        pdf_files = [f for f in os.listdir("uploads") if f.endswith('.pdf')]
        if not pdf_files: st.info("No contracts found.")
        else:
            cols = st.columns(4)
            for i, f_name in enumerate(pdf_files):
                with cols[i % 4]:
                    with st.container(border=True):
                        st.write(f"📄 {f_name}")
                        with open(os.path.join("uploads", f_name), "rb") as f:
                            st.download_button("⬇️ DL", f.read(), file_name=f_name, key=f"dl_{f_name}")
    else: st.warning("Uploads folder not found.")

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
                # 4. Create the condensed 4-column grid
                cols = st.columns(4)
                for i, file_name in enumerate(filtered_files):
                    file_path = os.path.join("uploads", file_name)
                    
                    # --- Naming Logic: Translate Username to Full Name /username ---
                    display_card_text = file_name # Fallback
                    if file_name.startswith("MOA_") or file_name.startswith("RENTER_"):
                        # Extract the username from filename
                        uname = file_name.replace("MOA_", "").replace("RENTER_", "").replace(".pdf", "")
                        
                        try:
                            # COORDINATED: Look up the real name in platform_users
                            name_df = pd.read_sql_query("SELECT full_name FROM platform_users WHERE username=?", conn, params=(uname,))
                            if not name_df.empty and name_df.iloc[0]['full_name']:
                                full_name = name_df.iloc[0]['full_name']
                                display_card_text = f"{full_name} / {uname}"
                            else:
                                # No full name in DB, fallback to username format
                                display_card_text = f"(@{uname})"
                        except:
                            pass # Fallback to original file_name if database fails
                    
                    with cols[i % 4]:
                        # Condensed Card Visuals
                        with st.container(border=True):
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
