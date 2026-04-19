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

# --- TAB 5: PROMOS & DB ---
with tabs[5]:
    st.subheader("📢 Broadcast Manager")
    with st.form("promo"):
        t = st.text_input("Title"); m = st.text_area("Message")
        target = st.radio("Target", ["RENTERS", "AFFILIATES", "ALL"], horizontal=True)
        if st.form_submit_button("PUBLISH"):
            conn.execute("INSERT INTO admin_promos (title, message, target) VALUES (?, ?, ?)", (t, m, target))
            conn.commit(); st.success("Broadcast Live!")

# --- TAB 6: REVIEWS ---
with tabs[6]:
    st.header("⭐ Master Reviews")
    try:
        revs = pd.read_sql_query("SELECT b.rating, b.review, u.full_name FROM bookings b JOIN platform_users u ON b.renter_username = u.username WHERE rating IS NOT NULL", conn)
        st.dataframe(revs, use_container_width=True)
    except: st.info("No reviews yet.")

# --- TAB 7: CANCELLATIONS ---
with tabs[7]:
    st.header("❌ Process Cancellations")
    try:
        active_q = "SELECT id, booking_ref, renter_username, amount, pickup_time FROM bookings WHERE status NOT IN ('COMPLETED', 'CANCELLED')"
        active_bookings = pd.read_sql_query(active_q, conn)

        if active_bookings.empty: st.info("No active bookings eligible for cancellation.")
        else:
            selected_ref = st.selectbox("Select Booking:", ["-- Select --"] + active_bookings['booking_ref'].tolist())
            if selected_ref != "-- Select --":
                b = active_bookings[active_bookings['booking_ref'] == selected_ref].iloc[0]
                pickup_dt = str(b['pickup_time'])
                if len(pickup_dt) == 16: pickup_dt += ":00" # Add seconds if missing

                logistics = st.number_input("Logistics/Delivery Paid (₱)", value=0.0)
                gateway = st.number_input("PayMongo Fee (₱)", value=0.0)

                days_left = get_days_before_pickup(pickup_dt)
                settlement = calculate_moa_cancellation_40_60(b['amount'], logistics, gateway, days_left)

                st.info(f"Cancellation Timing: {days_left} days before pickup.")
                c1, c2 = st.columns(2)
                with c1:
                    st.write("💸 **To Renter**")
                    st.success(f"Refund: ₱{settlement['renter_refund']:,.2f}")
                with c2:
                    st.write("🏢 **To Platform & Affiliate**")
                    st.write(f"Affiliate Payout (60%): ₱{settlement['affiliate_compensation']:,.2f}")

                if st.button("🚨 FINALIZE CANCELLATION", type="primary", use_container_width=True):
                    conn.execute("UPDATE bookings SET status = 'CANCELLED' WHERE booking_ref = ?", (selected_ref,))
                    conn.commit()
                    
                    # Email Logic
                    aff_email_q = "SELECT u.email FROM platform_users u JOIN vehicles v ON v.owner_username = u.username JOIN bookings b ON b.vehicle_id = v.id WHERE b.booking_ref = ?"
                    email_res = pd.read_sql_query(aff_email_q, conn, params=(selected_ref,))
                    target_email = email_res.iloc[0]['email'] if not email_res.empty else "rdalbaojrh@gmail.com"
                    
                    receipt_txt = f"Notice: Booking {selected_ref} cancelled. Affiliate Compensation: ₱{settlement['affiliate_compensation']:,.2f}."
                    email_receipt_to_affiliate(target_email, receipt_txt, selected_ref)
                    
                    st.success("Database Updated and Email Sent!"); st.rerun()
    except Exception as e: st.error(f"Cancellation Error: {e}")
