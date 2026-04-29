import sys
import os
import smtplib
import sqlite3
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import streamlit as st
import pandas as pd
import datetime
import numpy as np
import time
import random
import math
from PIL import Image

# ==========================================
# 1. PAGE CONFIG
# ==========================================
st.set_page_config(page_title="DriveElite Admin", layout="wide")

# ==========================================
# 2. DIRECTORY VISIBILITY
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# ==========================================
# 3. MODULE VALIDATION & IMPORTS
# ==========================================
try:
    from database_utils import get_connection, init_db, patch_database
    from tiered_discounts import (
        init_discount_db, 
        render_admin_discount_table, 
        render_platform_settings
    )
    from finance import (
        send_email, 
        generate_pos_receipt, 
        send_dual_receipts, 
        get_days_before_pickup, 
        calculate_moa_cancellation_40_60
    )
except ImportError:
    sys.path.insert(0, parent_dir)
    from database_utils import get_connection, init_db, patch_database
    from tiered_discounts import init_discount_db, render_admin_discount_table, render_platform_settings
    from finance import send_email, generate_pos_receipt, send_dual_receipts, get_days_before_pickup, calculate_moa_cancellation_40_60

# ==========================================
# 4. GLOBAL CONSTANTS & CONFIGURATION
# ==========================================
ADMIN_USERNAME = st.secrets.get("admin_username", "masterom")
ADMIN_PASSWORD = st.secrets.get("admin_password")
SENDER_EMAIL = st.secrets.get("email_sender")
EMAIL_APP_PASSWORD = st.secrets.get("email_app_password")

TAX_RATE = 0.02
DEFAULT_RENTER_MARKUP = 0.07
DEFAULT_AFFILIATE_SHARE = 0.82

# ==========================================
# 5. INITIALIZE DATABASE
# ==========================================
conn = get_connection()
init_db()
patch_database()
init_discount_db(conn)

# ==========================================
# 6. UTILITY FUNCTIONS
# ==========================================
def display_document(file_path, title):
    if file_path and str(file_path).strip() and os.path.exists(file_path):
        if str(file_path).lower().endswith('.pdf'):
            with open(file_path, "rb") as f:
                safe_key = f"dl_{str(file_path).replace('/', '_').replace('.', '_')}"
                st.download_button(f"📄 Download {title}", f.read(), file_name=os.path.basename(file_path), mime="application/pdf", key=safe_key)
        else:
            st.image(file_path, caption=title, use_container_width=True)
    else:
        st.warning(f"No {title} provided.")

# ==========================================
# 7. AUTHENTICATION
# ==========================================
if not st.session_state.get('logged_in'):
    st.title("🛡️ ADMIN AUTHORIZATION")
    with st.form("login"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("LOG IN"):
            if u == ADMIN_USERNAME and p == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.session_state.username = u
                st.session_state.role = "ADMIN"
                st.rerun()
            else:
                st.error("Invalid credentials.")
    st.stop()

# Header
head_col1, head_col2 = st.columns([5, 1])
head_col1.title("🛡️ MASTER COMMAND CENTER")
with head_col2:
    if st.button("🔒 LOGOUT", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ==========================================
# 8. MAIN INTERFACE TABS
# ==========================================
tabs = st.tabs(["📋 APPROVALS", "🚙 ASSETS", "🚚 LOGISTICS", "🏦 FINANCIALS", "🗄️ FILING CABINET", "📢 PROMOS & SETTINGS", "⭐ REVIEWS", "❌ CANCELLATIONS", "⚖️ DISPUTES"])

# --- TAB 0: APPROVALS ---
with tabs[0]:
    st.markdown("<h3 style='text-align: center;'>📋 PENDING APPROVALS</h3>", unsafe_allow_html=True)
    p_tabs = st.tabs(["🚙 PENDING RENTERS", "💼 PENDING AFFILIATES", "👨‍✈️ PENDING DRIVERS"])
    
    with p_tabs[0]:
        renters = pd.read_sql_query("SELECT * FROM platform_users WHERE admin_status = 'PENDING' AND role = 'RENTER'", conn)
        if renters.empty: st.info("No pending renters.")
        for i, r in renters.iterrows():
            with st.expander(f"{r['full_name']} (@{r['username']})"):
                st.write(f"Age: {r['age']} | Contact: {r['contact_number']}")
                if r.get('govt_id_img'): st.image(r['govt_id_img'], caption="ID")
                if st.button("APPROVE RENTER", key=f"ra_{r['id']}", type="primary"):
                    conn.execute("UPDATE platform_users SET admin_status = 'APPROVED' WHERE id = ?", (r['id'],))
                    conn.commit(); st.rerun()

    with p_tabs[1]:
        affiliates = pd.read_sql_query("SELECT * FROM platform_users WHERE admin_status = 'PENDING' AND role = 'AFFILIATE'", conn)
        if affiliates.empty: st.info("No pending affiliates.")
        for i, r in affiliates.iterrows():
            with st.expander(f"{r['full_name']} (@{r['username']})"):
                if r.get('signature_img'): st.image(r['signature_img'], caption="MOA Signature")
                if st.button("APPROVE AFFILIATE", key=f"aa_{r['id']}", type="primary"):
                    conn.execute("UPDATE platform_users SET admin_status = 'APPROVED' WHERE id = ?", (r['id'],))
                    conn.commit(); st.rerun()

    with p_tabs[2]:
        drivers = pd.read_sql_query("SELECT * FROM drivers WHERE admin_status = 'PENDING'", conn)
        if drivers.empty: st.info("No pending drivers.")
        for i, d in drivers.iterrows():
            with st.expander(f"{d['first_name']} {d['last_name']}"):
                if st.button("APPROVE DRIVER", key=f"da_{d['id']}", type="primary"):
                    conn.execute("UPDATE drivers SET admin_status = 'APPROVED' WHERE id = ?", (d['id'],))
                    conn.commit(); st.rerun()

# --- TAB 1: ASSETS ---
with tabs[1]:
    pv = pd.read_sql_query("SELECT * FROM vehicles WHERE admin_status = 'PENDING'", conn)
    if pv.empty: st.info("No vehicles pending.")
    else:
        for i, r in pv.iterrows():
            with st.expander(f"🚗 {r['make']} {r['model']} ({r['plate']})"):
                display_document(r.get('or_img'), "OR")
                display_document(r.get('cr_img'), "CR")
                if st.button("✅ APPROVE VEHICLE", key=f"v_app_{r['id']}", type="primary"):
                    conn.execute("UPDATE vehicles SET admin_status = 'APPROVED', booking_status = 'AVAILABLE' WHERE id = ?", (r['id'],))
                    conn.commit(); st.rerun()

# --- TAB 2: LOGISTICS ---
with tabs[2]:
    st.subheader("Active Logistics & Payment Status")
    query = "SELECT b.*, u_renter.full_name as renter_name FROM bookings b JOIN platform_users u_renter ON b.renter_username = u_renter.username WHERE b.status != 'COMPLETED' AND b.status != 'CANCELLED'"
    bookings = pd.read_sql_query(query, conn)
    if bookings.empty: st.info("No active logistics.")
    else:
        for i, r in bookings.iterrows():
            with st.expander(f"🎫 #{r['booking_ref']} | {r['status']}"):
                if r['status'] == 'PENDING':
                    if st.button("Override & Confirm Payment", key=f"conf_{r['id']}"):
                        conn.execute("UPDATE bookings SET status = 'CONFIRMED' WHERE id = ?", (r['id'],))
                        conn.commit(); st.rerun()

# --- TAB 3: FINANCIALS ---
with tabs[3]:
    st.markdown("<h2 style='text-align: center;'>🏦 MASTER FINANCIAL LEDGER</h2>", unsafe_allow_html=True)
    try:
        settings_df = pd.read_sql_query("SELECT renter_markup_pct, affiliate_share_pct FROM platform_settings WHERE id = 1", conn)
        r_markup = float(settings_df.iloc[0][0]) if not settings_df.empty else DEFAULT_RENTER_MARKUP
        a_share = float(settings_df.iloc[0][1]) if not settings_df.empty else DEFAULT_AFFILIATE_SHARE

        df = pd.read_sql_query("SELECT b.*, v.make, v.model FROM bookings b JOIN vehicles v ON b.vehicle_id = v.id WHERE b.status != 'PENDING' AND b.status != 'CANCELLED'", conn)
        if not df.empty:
            df['Platform_Net_Profit'] = df['amount'] * (1 - (a_share / (1 + r_markup)))
            df['Affiliate_Net_Payout'] = (df['amount'] / (1 + r_markup)) * a_share * (1 - TAX_RATE)
            
            c1, c2 = st.columns(2)
            c1.metric("💰 Gross Revenue", f"₱{df['amount'].sum():,.2f}")
            c2.metric("🏢 Platform Profit", f"₱{df['Platform_Net_Profit'].sum():,.2f}")

            f_tabs = st.tabs(["📑 LEDGER", "📤 PAYOUTS", "🎫 POS"])
            with f_tabs[0]: st.dataframe(df[['booking_ref', 'renter_username', 'amount', 'status']], use_container_width=True)
            with f_tabs[2]:
                target_ref = st.selectbox("Select Booking for Receipt:", ["--"] + df['booking_ref'].astype(str).tolist())
                if target_ref != "--":
                    if st.button("SEND POS RECEIPT"):
                        if send_dual_receipts(target_ref, conn): st.success("Receipt Sent!")
    except Exception as e: st.error(f"Finance Error: {e}")

# --- TAB 4: FILING CABINET ---
with tabs[4]:
    st.header("🗄️ Digital Filing Cabinet")
    if os.path.exists("uploads"):
        files = [f for f in os.listdir("uploads") if f.endswith('.pdf')]
        for f in files:
            with st.container(border=True):
                st.write(f"📄 {f}")
                with open(os.path.join("uploads", f), "rb") as pdf:
                    st.download_button("Download", pdf.read(), file_name=f, key=f"dl_{f}")

# --- TAB 5: PROMOS & SETTINGS ---
with tabs[5]:
    render_platform_settings(conn)
    st.divider()
    render_admin_discount_table(conn)

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
        
        if completed_trips.empty: st.info("No completed trips available for review.")
        else:
            dispute_opts = ["-- Select a Trip to Audit --"] + completed_trips['booking_ref'].astype(str).tolist()
            selected_trip = st.selectbox("Select Trip Ref:", dispute_opts)
            
            if selected_trip != "-- Select a Trip to Audit --":
                d_data = completed_trips[completed_trips['booking_ref'].astype(str) == selected_trip].iloc[0]
                st.divider()
                st.markdown(f"### 📋 Audit File: #{d_data['booking_ref']} | {d_data['make']} {d_data['model']} ({d_data['plate']})")
                c_rent, c_aff = st.columns(2)
                with c_rent: st.info(f"**Renter:** {d_data['renter_name']}\n\n📞 {d_data['r_phone']}\n\n✉️ {d_data['r_email']}")
                with c_aff: st.info(f"**Affiliate:** {d_data['affiliate_name']}\n\n📞 {d_data['a_phone']}\n\n✉️ {d_data['a_email']}")
                
                st.divider()
                st.markdown("<h3 style='text-align: center;'>📸 Visual Evidence Comparison</h3>", unsafe_allow_html=True)
                col_before, col_after = st.columns(2)
                
                with col_before:
                    st.markdown("#### 🟢 BEFORE (Handover Photos)")
                    if pd.notna(d_data.get('handover_photos')) and str(d_data['handover_photos']).strip():
                        h_photos = str(d_data['handover_photos']).split(',')
                        for img_path in h_photos:
                            if os.path.exists(img_path.strip()): st.image(img_path.strip(), use_container_width=True)
                    else: st.warning("No handover photos were logged for this trip.")
                
                with col_after:
                    st.markdown("#### 🔴 AFTER (Reported Damage)")
                    if pd.notna(d_data.get('damage_img')) and str(d_data['damage_img']).strip():
                        d_photos = str(d_data['damage_img']).split(',')
                        for img_path in d_photos:
                            if os.path.exists(img_path.strip()): st.image(img_path.strip(), use_container_width=True)
                    else: st.success("✅ No damage was reported upon return.")
                        
                st.divider()
                st.write("*Admin Note: If a penalty or deduction is required from the security deposit, please contact both parties directly using the phone numbers provided above to finalize med[...]
    except Exception as e:
        st.warning(f"Error loading evidence center: {e}")
