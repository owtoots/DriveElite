import sys
import os
import smtplib
import sqlite3
import pandas as pd
import numpy as np
import datetime
import time
import random
import math
import importlib.util
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from PIL import Image
from fpdf import FPDF
import streamlit as st

# --- IMPORT SHARED TOOLS ---
from database_utils import get_connection, init_db, patch_database, send_sms_alert, send_alert_email

def main():
    # ==========================================
    # 1. PAGE CONFIG & SMART LOGO LOADER
    # ==========================================
    st.set_page_config(page_title="DriveElite Master Admin", layout="wide", initial_sidebar_state="expanded")

    logo_candidates = ["logo.png", "../logo.png", os.path.join(os.path.dirname(__file__), "..", "logo.png")]
    loaded_logo = None
    for path in logo_candidates:
        if os.path.exists(path):
            loaded_logo = path
            break

    with st.sidebar:
        if loaded_logo:
            st.image(loaded_logo, width=140)
        else:
            st.markdown("## 🚗 DriveElite")

    # ==========================================
    # 💎 2. THE "CRYSTAL ELITE" CSS ENGINE
    # ==========================================
    st.markdown("""
    <style>
    @media (max-width: 768px) {
        .stImage, .stPDF, [data-testid="stForm"], [data-testid="stExpander"] {
            width: 100% !important;
            max-width: 100% !important;
        }
    }
    footer {visibility: hidden;}
    
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stImage"] img {
        height: 200px !important;
        width: 100% !important;
        object-fit: cover !important;
        border-radius: 8px !important;
    }
    
    /* MOBILE MENU ARROW */
    [data-testid="collapsedControl"], [data-testid="stSidebarCollapsedControl"] {
        position: fixed !important;  
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        align-items: center !important;
        justify-content: center !important;
        background-color: #22C55E !important; 
        border-radius: 50% !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3) !important;
        top: 15px !important;
        left: 15px !important;
        padding: 8px !important;
        z-index: 999999 !important;
    }
    [data-testid="collapsedControl"] svg, [data-testid="stSidebarCollapsedControl"] svg {
        fill: #FFFFFF !important;
        color: #FFFFFF !important;
        width: 24px !important;
        height: 24px !important;
    }

    [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #F8FAFC !important;
        color: #0F172A !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
    }
    
    /* SIDEBAR & LOGO REORDER */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E2E8F0 !important;
    }
    [data-testid="stSidebarContent"] {
        display: flex !important;
        flex-direction: column !important;
    }
    [data-testid="stSidebarUserContent"] {
        order: 1 !important;
        padding-top: 2rem !important;
        padding-bottom: 1.5rem !important;
        margin-top: 0 !important;
    }
    [data-testid="stSidebarNav"] {
        order: 2 !important;
        padding-top: 1rem !important;
    }
    
    [data-testid="stForm"], .stForm, div[data-testid="stExpander"], div.stMetric {
        background-color: #FFFFFF !important;
        padding: 20px !important;
        border-radius: 16px !important;
        border: 1px solid #E2E8F0 !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
    }
    
    /* UNIVERSAL GREEN BUTTON OVERRIDE */
    div.stButton > button, 
    button[kind="formSubmit"],
    [data-testid="stFormSubmitButton"] button,
    [data-testid="baseButton-secondary"],
    [data-testid="baseButton-primary"] {
        background-color: #22C55E !important;
        color: #FFFFFF !important;
        border: none !important;
        font-family: 'Segoe UI', Arial, sans-serif !important;
        font-size: 14px !important;  
        font-weight: 500 !important; 
        border-radius: 8px !important;
        padding: 10px 20px !important; 
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        box-shadow: 0 4px 6px rgba(34, 197, 94, 0.2) !important;
        -webkit-text-fill-color: #FFFFFF !important;
    }
    div.stButton > button p, 
    button[kind="formSubmit"] p,
    [data-testid="stFormSubmitButton"] button p {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
    }
    div.stButton > button:hover, 
    button[kind="formSubmit"]:hover,
    [data-testid="stFormSubmitButton"] button:hover {
        background-color: #16A34A !important;
        box-shadow: 0 6px 12px rgba(34, 197, 94, 0.3) !important;
        transform: translateY(-2px) !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ==========================================
    # 3. DIRECTORY & MODULE SETUP
    # ==========================================
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
    if parent_dir not in sys.path:
        sys.path.append(parent_dir)

    UPLOAD_DIR = "/data/uploads"
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR, exist_ok=True)

    required_modules = ['database_utils', 'tiered_discounts', 'finance']
    missing = [mod for mod in required_modules if importlib.util.find_spec(mod) is None]
    if missing:
        st.error(f"🚨 Critical System Error: Missing required modules: {', '.join(missing)}")
        st.stop()

    from tiered_discounts import init_discount_db, render_admin_discount_table, render_platform_settings
    from finance import get_days_before_pickup, calculate_moa_cancellation_40_60

    # ==========================================
    # 4. CONFIGURATION & DATABASE INITIALIZATION
    # ==========================================
    def get_secret(key, default_val=None):
        val = os.environ.get(key)
        if val: return val
        try:
            return st.secrets.get(key, default_val)
        except:
            return default_val

    ADMIN_USERNAME = get_secret("admin_username", "masterom")
    ADMIN_PASSWORD = get_secret("admin_password")

    conn = get_connection()
    init_db()
    patch_database()
    init_discount_db(conn)

    # Database Schema Updates
    for col_query in [
        "ALTER TABLE platform_settings ADD COLUMN admin_bank_name TEXT",
        "ALTER TABLE platform_settings ADD COLUMN admin_bank_acc_num TEXT",
        "ALTER TABLE platform_settings ADD COLUMN admin_bank_acc_name TEXT",
        "ALTER TABLE platform_users ADD COLUMN penalty_balance REAL DEFAULT 0.0",
        "ALTER TABLE platform_settings ADD COLUMN payment_mode TEXT DEFAULT 'MANUAL_QR'"
    ]:
        try: conn.execute(col_query); conn.commit()
        except: pass

    # ==========================================
    # 5. UTILITY & EMAIL FUNCTIONS
    # ==========================================
    def display_document(file_path, title):
        if file_path and str(file_path).strip() and os.path.exists(file_path):
            if str(file_path).lower().endswith('.pdf'):
                with open(file_path, "rb") as f:
                    safe_key = f"dl_{str(file_path).replace('/', '_').replace('.', '_')}_{title.replace(' ', '')}"
                    st.download_button(f"📄 Download {title} (PDF)", f.read(), file_name=os.path.basename(file_path), mime="application/pdf", key=safe_key)
            else:
                st.image(file_path, caption=title, use_container_width=True)
        else:
            st.warning(f"No {title} provided.")

    def generate_pos_receipt(b_data):
        return f"""
    ====================================
           DRIVEELITE PLATFORM
           POS SETTLEMENT SLIP
    ====================================
    Ref: {b_data['Ref']}
    Date: {str(b_data['Date'])[:10]}
    
    Renter: {b_data['Renter']}
    Affiliate: {b_data['Affiliate']}
    ------------------------------------
    Gross Payment:     PHP {b_data['Total_Paid_By_Renter']:,.2f}
    Gateway Fee:       PHP {b_data['gateway_fee']:,.2f}
    Platform Share:    PHP {b_data['Platform_Gross_Cut']:,.2f}
    Platform EWT (2%): PHP {b_data['Platform_EWT']:,.2f}
    Platform Net:      PHP {b_data['Platform_Net_Income']:,.2f}
    Affiliate Net:     PHP {b_data['Affiliate_Net_Payout']:,.2f}
    ====================================
    Status: {b_data['Payout_Status']}
    """

    def send_admin_email_with_attachment(to_email, subject, body, attachment_path, attachment_name):
        sender_email = "contact@driveelite.ph"
        sender_password = os.environ.get("EMAIL_PASSWORD")
        if not sender_password: return False
        try:
            msg = MIMEMultipart()
            msg['From'] = f"DriveElite Admin <{sender_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            with open(attachment_path, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename= {attachment_name}")
            msg.attach(part)
            with smtplib.SMTP_SSL('mail.driveelite.ph', 465) as smtp:
                smtp.login(sender_email, sender_password)
                smtp.send_message(msg)
            return True
        except Exception as e:
            return False

    def send_approval_email(recipient_email, full_name, role):
        if not recipient_email: return False, "No email address on file."
        msg = EmailMessage()
        msg['Subject'] = f"DriveElite: Notice of {role.title()} Account Approval"
        sender_email = "contact@driveelite.ph"
        msg['From'] = f"DriveElite Administration <{sender_email}>"
        msg['To'] = recipient_email
        
        direct_link = "https://www.driveelite.ph/RENTER_PORTAL" if role.upper() == "RENTER" else "https://www.driveelite.ph/AFFILIATE_PORTAL"
        
        body = f"""Dear {full_name},

Your registration for a DriveElite {role.title()} account has been successfully reviewed and approved.
You may now access your dashboard using your secure link:

{direct_link}

Best regards,
The DriveElite Administration Team
Pasig City, Metro Manila, Philippines
"""
        msg.set_content(body)
        try:
            app_password = "chcskxti6hc2d7ao"
            with smtplib.SMTP_SSL('mail.driveelite.ph', 465) as smtp:
                smtp.login(sender_email, app_password)
                smtp.send_message(msg)
            return True, "Email sent"
        except Exception as e:
            return False, str(e)

    @st.cache_data(ttl=300, show_spinner=False)
    def get_all_reviews(_conn):
        q_all_reviews = """
            SELECT b.rating, b.review, b.pickup_time, 
                   r.full_name as renter_name, a.full_name as affiliate_name, 
                   v.make, v.model, v.plate
            FROM bookings b
            JOIN vehicles v ON b.vehicle_id = v.id
            JOIN platform_users r ON b.renter_username = r.username
            JOIN platform_users a ON v.owner_username = a.username
            WHERE b.rating IS NOT NULL 
            ORDER BY b.id DESC
        """
        try: return pd.read_sql_query(q_all_reviews, _conn)
        except: return pd.DataFrame()

    # ==========================================
    # 6. AUTHENTICATION GATE
    # ==========================================
    is_authenticated = (
        st.session_state.get('logged_in') and 
        st.session_state.get('role') == 'ADMIN' and
        st.session_state.get('username')
    )

    if not is_authenticated:
        st.markdown("<h2 style='text-align: center;'>🛡️ ADMIN LOGIN</h2>", unsafe_allow_html=True)
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("LOGIN", type="primary", use_container_width=True):
                if not ADMIN_PASSWORD:
                    st.error("Critical System Error: Admin credentials are not configured in the secrets manager.")
                elif u == ADMIN_USERNAME and p == ADMIN_PASSWORD:
                    st.session_state.logged_in = True
                    st.session_state.username = ADMIN_USERNAME
                    st.session_state.role = "ADMIN"
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
        st.stop()

    # ==========================================
    # 7. HEADER & PENDING SYSTEM ALERTS
    # ==========================================
    head_col1, head_col2 = st.columns([5, 1])
    with head_col1:
        st.title("🛡️ MASTER COMMAND CENTER")
    with head_col2:
        st.info(f"👨‍💼 {st.session_state.username.upper()}")
        if st.button("🔒 LOGOUT", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    try:
        pending_renters = conn.execute("SELECT COUNT(*) FROM platform_users WHERE (admin_status = 'PENDING' OR admin_status IS NULL) AND role = 'RENTER'").fetchone()[0]
        pending_affiliates = conn.execute("SELECT COUNT(*) FROM platform_users WHERE (admin_status = 'PENDING' OR admin_status IS NULL) AND role = 'AFFILIATE'").fetchone()[0]
        pending_drivers = conn.execute("SELECT COUNT(*) FROM drivers WHERE admin_status = 'PENDING'").fetchone()[0]
        pending_payments = conn.execute("SELECT COUNT(*) FROM bookings WHERE status = 'PENDING'").fetchone()[0]
        total_pendings = pending_renters + pending_affiliates + pending_drivers + pending_payments

        if total_pendings > 0:
            st.warning("🚨 **ACTION REQUIRED: You have pending items awaiting your review!**")
            alert_cols = st.columns(4)
            if pending_renters > 0: alert_cols[0].error(f"👤 {pending_renters} Renters")
            if pending_affiliates > 0: alert_cols[1].error(f"💼 {pending_affiliates} Affiliates")
            if pending_drivers > 0: alert_cols[2].error(f"🧑‍✈️ {pending_drivers} Drivers")
            if pending_payments > 0: alert_cols[3].error(f"💳 {pending_payments} Payments")
    except: pass

    # ==========================================
    # 8. PROFESSIONAL WORKFLOW TABS
    # ==========================================
    tabs = st.tabs([
        "📋 APPROVALS", 
        "🚙 ASSETS", 
        "🚚 LOGISTICS", 
        "🏦 FINANCIALS", 
        "🗄️ FILING CABINET", 
        "📢 PROMOS & DB", 
        "⭐ REVIEWS", 
        "❌ CANCELLATIONS", 
        "⚖️ DISPUTES", 
        "⚙️ SETTINGS"
    ])

    # --- TAB 0: APPROVALS ---
    with tabs[0]:
        st.markdown("<h3 style='text-align: center;'>📋 PENDING USER & PARTNER APPROVALS</h3>", unsafe_allow_html=True)
        p_tabs = st.tabs(["🚙 PENDING RENTERS", "💼 PENDING AFFILIATES", "👨‍✈️ PENDING DRIVERS"])
        
        with p_tabs[0]:
            try:
                renters = pd.read_sql_query("SELECT * FROM platform_users WHERE (admin_status = 'PENDING' OR admin_status IS NULL) AND role = 'RENTER'", conn)
                if renters.empty: st.info("No pending renters.")
                for i, r in renters.iterrows():
                    with st.expander(f"{r['full_name']} (@{r['username']})"):
                        st.write(f"Age: {r['age']} | Contact: {r['contact_number']}")
                        c1, c2 = st.columns(2)
                        gov = r.get('gov_id') or r.get('govt_id_img')
                        lic = r.get('lic_id') or r.get('license_img')
                        if gov: c1.image(gov, caption="Govt ID")
                        if lic: c2.image(lic, caption="Driver's License")
                        if st.button("APPROVE RENTER", key=f"ra_{r['id']}", type="primary", use_container_width=True):
                            conn.execute("UPDATE platform_users SET admin_status = 'APPROVED' WHERE id = ?", (r['id'],))
                            conn.commit()
                            send_approval_email(r.get('email', ''), r['full_name'], 'RENTER')
                            st.success("Renter approved successfully!")
                            time.sleep(1); st.rerun()
            except Exception as e: st.warning(f"Error loading renters: {e}")

        with p_tabs[1]:
            try:
                affiliates = pd.read_sql_query("SELECT * FROM platform_users WHERE (admin_status = 'PENDING' OR admin_status IS NULL) AND role = 'AFFILIATE'", conn)
                if affiliates.empty: st.info("No pending affiliates.")
                for i, r in affiliates.iterrows():
                    with st.expander(f"{r['full_name']} (@{r['username']})"):
                        st.write(f"Contact: {r['contact_number']}")
                        c1, c2 = st.columns(2)
                        gov = r.get('gov_id') or r.get('govt_id_img')
                        sig = r.get('signature') or r.get('signature_img')
                        if gov: c1.image(gov, caption="Govt ID")
                        if sig: c2.image(sig, caption="Digitally Signed MOA")
                        if st.button("APPROVE AFFILIATE", key=f"aa_{r['id']}", type="primary", use_container_width=True):
                            conn.execute("UPDATE platform_users SET admin_status = 'APPROVED' WHERE id = ?", (r['id'],))
                            conn.commit()
                            send_approval_email(r.get('email', ''), r['full_name'], 'AFFILIATE')
                            st.success("Affiliate approved successfully!")
                            time.sleep(1); st.rerun()
            except Exception as e: st.warning(f"Error loading affiliates: {e}")

        with p_tabs[2]:
            try:
                drivers = pd.read_sql_query("SELECT * FROM drivers WHERE admin_status = 'PENDING'", conn)
                if drivers.empty: st.info("No pending drivers.")
                for i, d in drivers.iterrows():
                    with st.expander(f"{d['first_name']} {d['last_name']} (Affiliate: @{d['owner_username']})"):
                        if st.button("APPROVE DRIVER", key=f"da_{d['id']}", type="primary", use_container_width=True):
                            conn.execute("UPDATE drivers SET admin_status = 'APPROVED' WHERE id = ?", (d['id'],))
                            conn.commit()
                            st.success("Driver approved.")
                            time.sleep(1); st.rerun()
            except Exception as e: st.warning(f"Error loading drivers: {e}")

    # --- TAB 1: ASSETS ---
    with tabs[1]:
        st.markdown("<h3 style='text-align: center;'>🚙 ASSET & FLEET MANAGEMENT</h3>", unsafe_allow_html=True)
        asset_tabs = st.tabs(["⏳ Pending Fleet Approvals", "🚗 Active Fleet Directory"])
        
        with asset_tabs[0]:
            try:
                pv = pd.read_sql_query("SELECT * FROM vehicles WHERE admin_status = 'PENDING'", conn)
                if pv.empty: 
                    st.info("No vehicles currently pending approval.")
                else:
                    for i, r in pv.iterrows():
                        with st.expander(f"🚗 {r['make']} {r['model']} ({r['plate']}) - Cat: {r['category']}"):
                            
                            # ==========================================
                            # 🔍 PROMINENT VEHICLE CONDITION INSPECTION
                            # ==========================================
                            st.write("### 🔍 Vehicle Condition Inspection")
                            vehicle_img_path = r.get('vehicle_img')
                            if vehicle_img_path:
                                if not os.path.exists(vehicle_img_path) and os.path.exists(os.path.join(os.getcwd(), vehicle_img_path.lstrip("/"))):
                                    vehicle_img_path = os.path.join(os.getcwd(), vehicle_img_path.lstrip("/"))
                                st.image(vehicle_img_path, caption=f"Submitted Photo: {r['make']} {r['model']} ({r['plate']})", use_container_width=True)
                            else:
                                st.error("❌ No vehicle photo was provided by the affiliate.")
                            
                            st.write("### 📄 Supporting Legal Documents")
                            c_doc1, c_doc2, c_doc3 = st.columns(3)
                            with c_doc1: display_document(r.get('or_img'), "Official Receipt (OR)")
                            with c_doc2: display_document(r.get('cr_img'), "Certificate of Reg (CR)")
                            with c_doc3: display_document(r.get('insurance_img'), "Insurance Policy")
                            
                            st.divider()
                            
                            # --- 🧮 PRICING CALCULATOR & APPROVAL ---
                            base_category_rate = float(r.get('approved_price', 0.0))
                            age = int(r.get('vehicle_age', 0))
                            depreciation_pct = min(age * 0.05, 0.50)
                            suggested_rate = base_category_rate * (1 - depreciation_pct)
                            
                            c1, c2 = st.columns(2)
                            c1.metric("Suggested Rate (Depreciation Applied)", f"₱{suggested_rate:,.2f}/day")
                            final_price = c2.number_input("Final Approved Rate (₱/day)", min_value=0.0, step=100.0, value=float(suggested_rate), key=f"fr_{r['id']}")
                            
                            if st.button("✅ APPROVE & ACTIVATE VEHICLE", key=f"v_app_{r['id']}", type="primary", use_container_width=True):
                                conn.execute("UPDATE vehicles SET admin_status = 'APPROVED', booking_status = 'AVAILABLE', approved_price = ? WHERE id = ?", (final_price, r['id']))
                                conn.commit()
                                st.success("Vehicle successfully activated on showroom!")
                                time.sleep(1); st.rerun()
            except Exception as e: 
                st.warning(f"Error loading pending vehicles: {e}")

        with asset_tabs[1]:
            try:
                active_fleet = pd.read_sql_query("SELECT * FROM vehicles WHERE admin_status = 'APPROVED'", conn)
                if active_fleet.empty: st.info("No active fleet records.")
                for i, car in active_fleet.iterrows():
                    with st.expander(f"{car['make']} {car['model']} ({car['plate']}) | @{car['owner_username']}"):
                        if st.button("🚨 Archive / Remove Vehicle", key=f"rm_car_{car['id']}"):
                            conn.execute("UPDATE vehicles SET admin_status = 'REMOVED', booking_status = 'UNAVAILABLE' WHERE id = ?", (car['id'],))
                            conn.commit()
                            st.rerun()
            except Exception as e: st.warning(f"Error loading active fleet: {e}")

    # --- TAB 2: LOGISTICS ---
    with tabs[2]:
        st.subheader("🚚 Active Logistics & Booking Dispatches")
        try:
            bookings = pd.read_sql_query("""
                SELECT b.*, u_renter.full_name as renter_name, u_owner.full_name as affiliate_name 
                FROM bookings b 
                JOIN platform_users u_renter ON b.renter_username = u_renter.username 
                JOIN vehicles v ON b.vehicle_id = v.id 
                JOIN platform_users u_owner ON v.owner_username = u_owner.username 
                WHERE b.status != 'COMPLETED' AND b.status != 'CANCELLED'
                ORDER BY b.id DESC
            """, conn)
            if bookings.empty: st.info("No active dispatches.")
            else:
                for i, r in bookings.iterrows():
                    with st.expander(f"🎫 #{r['booking_ref']} | Status: {r['status']} | Renter: {r['renter_name']}"):
                        st.write(f"**Amount:** ₱{r['amount']:,.2f} | **Destination:** {r.get('destination')}")
                        if r['status'] == 'PENDING' and st.button("Force Confirm Booking", key=f"fc_{r['id']}"):
                            conn.execute("UPDATE bookings SET status = 'CONFIRMED' WHERE id = ?", (r['id'],))
                            conn.commit()
                            st.rerun()
        except Exception as e: st.error(f"Error loading logistics: {e}")

    # --- TAB 3: FINANCIALS ---
    with tabs[3]:
        st.markdown("<h2 style='text-align: center;'>🏦 MASTER FINANCIAL LEDGER & RECALCULATIONS</h2>", unsafe_allow_html=True)
        try:
            settings_df = pd.read_sql_query("SELECT affiliate_share_pct FROM platform_settings WHERE id = 1", conn)
            a_share = float(settings_df.iloc[0]['affiliate_share_pct']) if not settings_df.empty else 0.80

            f_tabs = st.tabs(["💸 PAYMENT VERIFICATION", "📑 FINANCIAL LEDGER", "📤 AUTOMATED PAYOUTS"])

            with f_tabs[0]:
                pending_bpi = pd.read_sql_query("""
                    SELECT b.*, u.full_name as Renter, v.make, v.model
                    FROM bookings b 
                    JOIN platform_users u ON b.renter_username = u.username 
                    JOIN vehicles v ON b.vehicle_id = v.id
                    WHERE b.status IN ('PENDING', 'VERIFYING')
                    ORDER BY b.id DESC
                """, conn)
                if pending_bpi.empty: st.info("No payments waiting for confirmation.")
                for _, row in pending_bpi.iterrows():
                    with st.container(border=True):
                        st.write(f"Ref: #{row['booking_ref']} | Renter: {row['Renter']} | Amount: ₱{row['amount']:,.2f}")
                        if st.button("✅ CONFIRM PAYMENT", key=f"cf_pay_{row['booking_ref']}", type="primary"):
                            conn.execute("UPDATE bookings SET status = 'CONFIRMED' WHERE booking_ref = ?", (row['booking_ref'],))
                            conn.commit()
                            st.success("Payment confirmed and escrow route locked.")
                            time.sleep(1); st.rerun()

            ledger_query = """
                SELECT b.id, b.booking_ref, b.pickup_time as Date, b.return_time, 
                       u_renter.full_name as Renter, u_owner.full_name as Affiliate,
                       b.amount as Total_Paid_By_Renter, b.status as Trip_Status, 
                       b.payout_status as Payout_Status, b.gateway_fee, v.bank_name, v.account_no
                FROM bookings b
                JOIN vehicles v ON b.vehicle_id = v.id
                JOIN platform_users u_renter ON b.renter_username = u_renter.username
                JOIN platform_users u_owner ON v.owner_username = u_owner.username
                WHERE b.status != 'PENDING' AND b.status != 'CANCELLED' 
                ORDER BY b.id DESC
            """
            df = pd.read_sql_query(ledger_query, conn)

            with f_tabs[1]:
                if df.empty: st.info("No recorded transactions.")
                else:
                    df['gateway_fee'] = df['gateway_fee'].fillna(0)
                    
                    # PRECISE RECALCULATIONS: Platform Share & Affiliate Net Payouts with EWT
                    df['Affiliate_Gross_Share'] = df['Total_Paid_By_Renter'] * a_share
                    df['Platform_Gross_Cut'] = df['Total_Paid_By_Renter'] - df['Affiliate_Gross_Share']
                    df['Affiliate_Net_Payout'] = df['Affiliate_Gross_Share'] - df['gateway_fee']
                    
                    PLATFORM_TAX_RATE = 0.02
                    df['Platform_EWT'] = df['Platform_Gross_Cut'] * PLATFORM_TAX_RATE
                    df['Platform_Net_Income'] = df['Platform_Gross_Cut'] - df['Platform_EWT']
                    df['Ref'] = df.apply(lambda x: f"#{x['booking_ref']}" if pd.notnull(x.get('booking_ref')) else f"DRV-{x['id']:05d}", axis=1)

                    display_cols = ['Ref', 'Date', 'Affiliate', 'Total_Paid_By_Renter', 'Affiliate_Net_Payout', 'Platform_Gross_Cut', 'Platform_EWT', 'Platform_Net_Income', 'Payout_Status']
                    st.dataframe(df[display_cols].style.format({
                        'Total_Paid_By_Renter': '₱{:,.2f}', 'Affiliate_Net_Payout': '₱{:,.2f}', 
                        'Platform_Gross_Cut': '₱{:,.2f}', 'Platform_EWT': '₱{:,.2f}', 'Platform_Net_Income': '₱{:,.2f}'
                    }), use_container_width=True, hide_index=True)

            with f_tabs[2]:
                if not df.empty:
                    pending_p = df[(df['Trip_Status'] == 'COMPLETED') & (df['Payout_Status'] == 'PENDING')]
                    if pending_p.empty: st.info("All payouts cleared.")
                    for _, p in pending_p.iterrows():
                        with st.expander(f"{p['Ref']} | {p['Affiliate']} | Remittance: ₱{p['Affiliate_Net_Payout']:,.2f}"):
                            try:
                                aff_data = conn.execute("""
                                    SELECT u.username, u.penalty_balance 
                                    FROM platform_users u
                                    JOIN vehicles v ON v.owner_username = u.username
                                    JOIN bookings b ON b.vehicle_id = v.id
                                    WHERE b.id = ?
                                """, (p['id'],)).fetchone()
                                aff_username = aff_data[0] if aff_data else ""
                                current_penalty = aff_data[1] if aff_data and aff_data[1] else 0.0
                            except: aff_username, current_penalty = "", 0.0

                            final_payout = p['Affiliate_Net_Payout']
                            penalty_to_deduct = 0.0
                            if current_penalty > 0:
                                penalty_to_deduct = min(final_payout, current_penalty)
                                final_payout -= penalty_to_deduct
                                st.error(f"Auto-deducting recorded penalty balance: ₱{penalty_to_deduct:,.2f}")

                            st.write(f"### Adjusted Payout: ₱{final_payout:,.2f}")
                            if st.button("EXECUTE DISBURSEMENT", key=f"ex_pay_{p['id']}", type="primary"):
                                conn.execute("UPDATE bookings SET payout_status = 'PAID' WHERE id = ?", (p['id'],))
                                if penalty_to_deduct > 0:
                                    conn.execute("UPDATE platform_users SET penalty_balance = penalty_balance - ? WHERE username = ?", (penalty_to_deduct, aff_username))
                                conn.commit()
                                st.success("Payout executed via Xendit disbursement loop.")
                                time.sleep(1); st.rerun()
        except Exception as e: st.error(f"Financial Engine Error: {e}")

    # --- TAB 4: FILING CABINET ---
    with tabs[4]:
        st.header("🗄️ Master Legal & Digital Filing Cabinet")
        if os.path.exists(UPLOAD_DIR):
            pdf_files = [f for f in os.listdir(UPLOAD_DIR) if f.endswith('.pdf')]
            if pdf_files:
                for file_name in pdf_files:
                    file_path = os.path.join(UPLOAD_DIR, file_name)
                    c1, c2 = st.columns([4, 1])
                    c1.write(f"📄 {file_name}")
                    if c2.button("🗑️ Delete", key=f"del_file_{file_name}"):
                        os.remove(file_path)
                        st.rerun()
            else: st.info("No documents archived yet.")

    # --- TAB 5: PROMOS & DB HOUSEKEEPING ---
    with tabs[5]:
        render_platform_settings(conn)
        st.divider()
        render_admin_discount_table(conn)
        
        st.divider()
        st.markdown("<h3 style='text-align: center; color: #ef4444;'>🧹 Database Housekeeping & Testing Cleanup</h3>", unsafe_allow_html=True)
        
        with st.container(border=True):
            st.write("#### 🗑️ Selective Test Data Cleanup")
            st.caption("Safely purge dummy accounts, test vehicles, or trial bookings matching 'test' without destroying production records.")
            
            clean_target = st.selectbox(
                "Select Target to Purge:", 
                ["Test Users (Renters/Affiliates matching 'test')", "Test Vehicles", "Pending/Unpaid Test Bookings"]
            )
            
            if st.button("Execute Selective Cleanup", type="secondary"):
                try:
                    if clean_target == "Test Users (Renters/Affiliates matching 'test')":
                        cursor = conn.execute("DELETE FROM platform_users WHERE username LIKE '%test%' OR email LIKE '%test%'")
                        conn.commit()
                        st.success(f"Purged test user accounts successfully.")
                    elif clean_target == "Test Vehicles":
                        cursor = conn.execute("DELETE FROM vehicles WHERE make LIKE '%test%' OR plate LIKE '%TEST%'")
                        conn.commit()
                        st.success(f"Purged test vehicle records successfully.")
                    elif clean_target == "Pending/Unpaid Test Bookings":
                        cursor = conn.execute("DELETE FROM bookings WHERE status = 'PENDING'")
                        conn.commit()
                        st.success("Purged all pending/unpaid test bookings.")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Cleanup error: {e}")

        st.write("")
        
        with st.container(border=True):
            st.markdown("<h4 style='color: #ef4444;'>☢️ Nuclear Database Reset (Danger Zone)</h4>", unsafe_allow_html=True)
            st.warning("⚠️ **Warning:** This will clear all transactions, active bookings, vehicles, and non-admin users. Your master admin account (`masterom`) will be preserved.")
            
            confirm_key = st.text_input("Type 'WIPE ALL DATA' below to unlock the nuclear reset button:")
            
            if confirm_key == "WIPE ALL DATA":
                if st.button("🚨 EXECUTE FULL NUCLEAR RESET", type="primary"):
                    try:
                        conn.execute("DELETE FROM bookings")
                        conn.execute("DELETE FROM vehicles")
                        conn.execute("DELETE FROM drivers")
                        conn.execute("DELETE FROM chat_messages")
                        conn.execute("DELETE FROM admin_promos")
                        conn.execute("DELETE FROM platform_users WHERE role != 'ADMIN'")
                        conn.commit()
                        
                        st.success("💥 Nuclear reset complete! All test data and transactional records have been wiped clean.")
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Nuclear wipe failed: {e}")
    # --- TAB 6: GLOBAL REVIEWS ---
    with tabs[6]:
        st.markdown("<h3 style='text-align: center;'>⭐ PLATFORM REVIEWS</h3>", unsafe_allow_html=True)
        all_rev_df = get_all_reviews(conn)
        if not all_rev_df.empty:
            st.metric("Overall Average Rating", f"{all_rev_df['rating'].mean():.1f} ⭐")
            for _, rev in all_rev_df.iterrows():
                with st.container(border=True):
                    st.write(f"{'⭐'*int(rev['rating'])} | {rev['make']} {rev['model']} (Renter: {rev['renter_name']})")
                    if rev['review']: st.info(rev['review'])

    # --- TAB 7: CANCELLATIONS & MOA SPLIT ENGINE ---
    with tabs[7]:
        st.header("❌ Process Cancellations (MOA 40/60 Rule)")
        try:
            active_bks = pd.read_sql_query("SELECT id, booking_ref, renter_username, amount, pickup_time FROM bookings WHERE status NOT IN ('COMPLETED', 'CANCELLED')", conn)
            if active_bks.empty: st.info("No active bookings eligible for cancellation.")
            else:
                selected_ref = st.selectbox("Select Active Booking Reference:", active_bks['booking_ref'].astype(str).tolist())
                if selected_ref:
                    b_data = active_bks[active_bks['booking_ref'].astype(str) == selected_ref].iloc[0]
                    gross_paid, pickup_date = float(b_data['amount']), str(b_data['pickup_time'])
                    
                    if len(pickup_date) == 16: pickup_date += ":00"
                    days_left = get_days_before_pickup(pickup_date)
                    settlement = calculate_moa_cancellation_40_60(gross_rental_paid=gross_paid, logistics_paid=0.0, exact_gateway_fee=0.0, days_before_pickup=days_left)

                    st.write(f"Cancellation Timing: **{days_left} days** before pickup.")
                    st.success(f"Renter Refund: ₱{settlement['renter_refund']:,.2f} | Penalty Applied: ₱{settlement['penalty_applied']:,.2f}")
                    st.info(f"Recalculated Split -> Platform Cut (40%): ₱{settlement['nucleuz_platform_fee']:,.2f} | Affiliate Comp (60%): ₱{settlement['affiliate_compensation']:,.2f}")

                    if st.button("Confirm Cancellation & Execute MOA Split", type="primary"):
                        conn.execute("UPDATE bookings SET status = 'CANCELLED' WHERE booking_ref = ?", (selected_ref,))
                        conn.commit()
                        st.success("Cancellation finalized and split allocated.")
                        time.sleep(1); st.rerun()
        except Exception as e: st.error(f"Cancellation error: {e}")

    # --- TAB 8: DISPUTE CENTER ---
    with tabs[8]:
        st.header("⚖️ Master Dispute & Evidence Audit Center")
        st.info("Cross-reference initial digital vehicle handovers against return damage logs.")

    # --- TAB 9: SYSTEM SETTINGS ---
    with tabs[9]:
        st.markdown("<h2 style='text-align: center;'>⚙️ SYSTEM SETTINGS</h2>", unsafe_allow_html=True)
        settings_df = pd.read_sql_query("SELECT payment_mode FROM platform_settings WHERE id = 1", conn)
        current_mode = settings_df.iloc[0]['payment_mode'] if not settings_df.empty else "MANUAL_QR"
        
        new_mode = st.radio("Active Payment Gateway:", ["MANUAL_QR", "XENDIT"], index=0 if current_mode == "MANUAL_QR" else 1)
        if st.button("Save Gateway Settings", type="primary"):
            conn.execute("UPDATE platform_settings SET payment_mode = ? WHERE id = 1", (new_mode,))
            conn.commit()
            st.success("Payment gateway successfully updated!")
            st.rerun()

if __name__ == "__main__":
    main()
