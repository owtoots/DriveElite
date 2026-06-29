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
def main():

# --- IMPORT SHARED TOOLS ---
from database_utils import get_connection, init_db, patch_database, send_sms_alert, send_alert_email

# --- AUTHENTICATION & PAGE CONFIG ---
st.set_page_config(page_title="DriveElite Admin Portal", layout="wide")

# ==========================================
# 💎 2. THE "CRYSTAL ELITE" CSS ENGINE
# ==========================================
st.markdown("""
<style>
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stImage"] img {
        height: 200px !important;
        width: 100% !important;
        object-fit: cover !important;
        border-radius: 8px !important;
    }
    [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #F8FAFC !important;
        color: #0F172A !important;
        font-family: 'Inter', -apple-system, sans-serif !important;
    }
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
        padding-top: 0rem !important;
        margin-top: -1.5rem !important; 
        padding-bottom: 1rem !important;
    }
    [data-testid="stSidebarNav"] {
        order: 2 !important;
        padding-top: 0rem !important; 
    }
    [data-testid="stForm"], .stForm, div[data-testid="stExpander"], div.stMetric {
        background-color: #FFFFFF !important;
        padding: 20px !important;
        border-radius: 16px !important;
        border: 1px solid #E2E8F0 !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
    }
    div.stButton > button, [data-testid="stFormSubmitButton"] > button {
        background-color: #2563EB !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 700 !important;
        border-radius: 10px !important;
        padding: 10px 24px !important;
        text-transform: uppercase !important;
        transition: all 0.2s ease !important;
    }
    div.stButton > button p, [data-testid="stFormSubmitButton"] > button p {
        color: #FFFFFF !important;
    }
    div.stButton > button:hover {
        background-color: #1D4ED8  !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
        transform: translateY(-1px) !important;
    }
    div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 8px !important;
    }
    input { color: #1E293B !important; }
    h1, h2, h3 { color: #0F172A !important; font-weight: 800 !important; }
    label { color: #475569 !important; font-weight: 600 !important; }
</style>
""", unsafe_allow_html=True)

try:
    st.sidebar.image("logo.png", use_container_width=True)
except:
    pass

# ==========================================
# 2. DIRECTORY VISIBILITY & VAULT SETUP
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

UPLOAD_DIR = "/data/uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR, exist_ok=True)

# ==========================================
# 3. MODULE VALIDATION
# ==========================================
required_modules = ['database_utils', 'tiered_discounts', 'finance']
missing = [mod for mod in required_modules if importlib.util.find_spec(mod) is None]

if missing:
    st.error(f"🚨 Critical System Error: Missing required modules: {', '.join(missing)}")
    st.stop()

from tiered_discounts import init_discount_db, render_admin_discount_table, render_platform_settings
from finance import get_days_before_pickup, calculate_moa_cancellation_40_60

# ==========================================
# 4. GLOBAL CONSTANTS & CONFIGURATION
# ==========================================
def get_secret(key, default_val=None):
    val = os.environ.get(key)
    if val: 
        return val
    try:
        return st.secrets.get(key, default_val)
    except:
        return default_val

ADMIN_USERNAME = get_secret("admin_username", "masterom")
ADMIN_PASSWORD = get_secret("admin_password")

TAX_RATE = 0.02  
DEFAULT_RENTER_MARKUP = 0.07
DEFAULT_AFFILIATE_SHARE = 0.80

# ==========================================
# 5. INITIALIZE DATABASE
# ==========================================
conn = get_connection()
init_db()
patch_database()
init_discount_db(conn)

try: 
    conn.execute("ALTER TABLE platform_users ADD COLUMN penalty_balance REAL DEFAULT 0.0")
    conn.commit()
except: 
    pass

try:
    conn.execute("ALTER TABLE platform_settings ADD COLUMN payment_mode TEXT DEFAULT 'MANUAL_QR'")
    conn.commit()
except:
    pass

# ==========================================
# 6. UTILITY FUNCTIONS (CACHE & POS)
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
    """Generates a text-based POS receipt for the master ledger"""
    receipt = f"""
    ====================================
           DRIVEELITE PLATFORM
           POS SETTLEMENT SLIP
    ====================================
    Ref: {b_data['Ref']}
    Date: {str(b_data['Date'])[:10]}
    Days Rented: {b_data['Total_Days']}
    
    Renter: {b_data['Renter']}
    Affiliate: {b_data['Affiliate']}
    ------------------------------------
    Gross Payment:   PHP {b_data['Total_Paid_By_Renter']:,.2f}
    Gateway Fee:     PHP {b_data['gateway_fee']:,.2f}
    EWT Deduction:   PHP {b_data['EWT_Deduction']:,.2f}
    
    Platform Cut:    PHP {b_data['Platform_Net_Profit']:,.2f}
    Affiliate Net:   PHP {b_data['Affiliate_Net_Payout']:,.2f}
    ====================================
    Status: {b_data['Payout_Status']}
    """
    return receipt

def send_admin_email_with_attachment(to_email, subject, body, attachment_path, attachment_name):
    """Safely handles emailing contracts with PDF attachments via Corporate Server"""
    sender_email = "contact@driveelite.ph"
    sender_password = os.environ.get("EMAIL_PASSWORD") 
    
    if not sender_password: 
        return False
        
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
        
        # CONNECT TO DOTPH CORPORATE SERVER
        with smtplib.SMTP_SSL('mail.driveelite.ph', 465) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.send_message(msg)
        return True
    except Exception as e:
        print(f"Attachment Email Error: {e}")
        return False

# --- NEW: MAGIC LINK APPROVAL EMAIL FUNCTION ---

# --- NEW: MAGIC LINK APPROVAL EMAIL FUNCTION (SPAM-SAFE) ---
def send_approval_email(recipient_email, full_name, role):
    if not recipient_email:
        return False, "No email address on file."
        
    msg = EmailMessage()
    msg['Subject'] = f"DriveElite: Notice of {role.title()} Account Approval"
    
    sender_email = "contact@driveelite.ph"
    msg['From'] = f"DriveElite Administration <{sender_email}>"
    msg['To'] = recipient_email
    
    # THE CORRECT MAGIC LINK FORMAT (Using query parameters)
    magic_link = f"https://www.driveelite.ph/?portal={role.upper()}"
    
    body = f"""Dear {full_name},
    
Your registration for a DriveElite {role.title()} account has been successfully reviewed and approved by our administration team.

You may now access your platform features. Please click or copy-paste the exact link below to log in securely to your dashboard:

{magic_link}

If you have any questions regarding your account activation, please contact our support team.

Best regards,
The DriveElite Administration Team
Pasig City, Metro Manila, Philippines
"""
    
    msg.set_content(body)

    try:
        # Using your working app password
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
    try:
        return pd.read_sql_query(q_all_reviews, _conn)
    except Exception as e:
        st.warning(f"Failed to fetch reviews: {e}")
        return pd.DataFrame()

# ==========================================
# 7. AUTHENTICATION & HEADER
# ==========================================
is_authenticated = (
    st.session_state.get('logged_in') and 
    st.session_state.get('role') == 'ADMIN' and
    st.session_state.get('username')
)

if not is_authenticated:
    st.title("🛡️ ADMIN AUTHORIZATION")
    with st.form("login"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("LOG IN"):
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

head_col1, head_col2 = st.columns([5, 1])
with head_col1:
    st.title("🛡️ MASTER COMMAND CENTER")
with head_col2:
    st.info(f"👨‍💼 {st.session_state.username.upper()}")
    if st.button("🔒 LOGOUT", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ==========================================
# 7.5. SYSTEM ALERTS (PENDINGS & PAYMENTS)
# ==========================================
try:
    pending_renters = conn.execute("SELECT COUNT(*) FROM platform_users WHERE (admin_status = 'PENDING' OR admin_status IS NULL) AND role = 'RENTER'").fetchone()[0]
    pending_affiliates = conn.execute("SELECT COUNT(*) FROM platform_users WHERE (admin_status = 'PENDING' OR admin_status IS NULL) AND role = 'AFFILIATE'").fetchone()[0]
    pending_drivers = conn.execute("SELECT COUNT(*) FROM drivers WHERE admin_status = 'PENDING'").fetchone()[0]
    pending_payments = conn.execute("SELECT COUNT(*) FROM bookings WHERE status = 'PENDING'").fetchone()[0]

    total_pendings = pending_renters + pending_affiliates + pending_drivers + pending_payments

    if total_pendings > 0:
        st.warning(" **ACTION REQUIRED: You have pending items awaiting your review!**")
        alert_cols = st.columns(4)
        if pending_renters > 0: alert_cols[0].error(f"👤 {pending_renters} Renters")
        if pending_affiliates > 0: alert_cols[1].error(f"💼 {pending_affiliates} Affiliates")
        if pending_drivers > 0: alert_cols[2].error(f"🧑‍✈️ {pending_drivers} Drivers")
        if pending_payments > 0: alert_cols[3].error(f"💳 {pending_payments} Payments")
        
        st.toast(f"Master, you have {total_pendings} pending items to clear.", icon="🚨")
except Exception as e:
    pass

# ==========================================
# 8. MAIN INTERFACE TABS
# ==========================================
tabs = st.tabs(["📋 APPROVALS", "🚙 ASSETS", "🚚 LOGISTICS", "🏦 FINANCIALS", "🗄️ FILING CABINET", "📢 PROMOS & DB", "⭐ REVIEWS", "❌ CANCELLATIONS", "⚖️ DISPUTES", "⚙️ SETTINGS"])

# --- TAB 0: PENDING APPROVALS ---
with tabs[0]:
    st.markdown("<h3 style='text-align: center;'>📋 PENDING APPROVALS</h3>", unsafe_allow_html=True)
    
    p_tabs = st.tabs(["🚙 PENDING RENTERS", "💼 PENDING AFFILIATES", "👨‍✈️ PENDING DRIVERS"])
    
    with p_tabs[0]:
        try:
            renters = pd.read_sql_query("SELECT * FROM platform_users WHERE (admin_status = 'PENDING' OR admin_status IS NULL) AND role = 'RENTER'", conn)
            if renters.empty: st.info("No pending renters.")
            for i, r in renters.iterrows():
                with st.expander(f"{r['full_name']} (@{r['username']})"):
                    st.write(f"Age: {r['age']} | Nat: {r.get('nationality', 'Filipino')} | Contact: {r['contact_number']}")
                    c_img1, c_img2 = st.columns(2)
                    
                    gov = r.get('gov_id') if pd.notna(r.get('gov_id')) else r.get('govt_id_img')
                    lic = r.get('lic_id') if pd.notna(r.get('lic_id')) else r.get('license_img')
                    
                    if pd.notna(gov) and gov:
                        if isinstance(gov, str): c_img1.image(gov, caption="Passport / Govt ID")
                        else: c_img1.image(bytes(gov), caption="Passport / Govt ID")
                    if pd.notna(lic) and lic:
                        if isinstance(lic, str): c_img2.image(lic, caption="Driver's License")
                        else: c_img2.image(bytes(lic), caption="Driver's License")
                    
                    if st.button("APPROVE RENTER", key=f"ra_{r['id']}", type="primary", use_container_width=True):
                        conn.execute("UPDATE platform_users SET admin_status = 'APPROVED' WHERE id = ?", (r['id'],))
                        conn.commit()
                        
                        # --- TRIGGER RENTER MAGIC LINK EMAIL ---
                        with st.spinner("Sending approval email with Magic Link..."):
                            success, error_msg = send_approval_email(r.get('email', ''), r['full_name'], 'RENTER')
                            
                            if success:
                                st.success(f"Renter approved! Magic link sent to {r.get('email', '')}.")
                                time.sleep(1.5)
                                st.rerun() 
                            else:
                                st.error(f"⚠️ Email Failed! The system says: {error_msg}")
                                st.stop() 
        except Exception as e:
            st.warning(f"Could not load Renter database: {e}")

    with p_tabs[1]:
        try:
            affiliates = pd.read_sql_query("SELECT * FROM platform_users WHERE (admin_status = 'PENDING' OR admin_status IS NULL) AND role = 'AFFILIATE'", conn)
            if affiliates.empty: st.info("No pending affiliates.")
            for i, r in affiliates.iterrows():
                with st.expander(f"{r['full_name']} (@{r['username']})"):
                    st.write(f"Age: {r['age']} | Nat: {r.get('nationality', 'Filipino')} | Contact: {r['contact_number']}")
                    c_img1, c_img2 = st.columns(2)
                    
                    gov = r.get('gov_id') if pd.notna(r.get('gov_id')) else r.get('govt_id_img')
                    lic = r.get('lic_id') if pd.notna(r.get('lic_id')) else r.get('license_img')
                    sig = r.get('signature') if pd.notna(r.get('signature')) else r.get('signature_img')
                    
                    if pd.notna(gov) and gov:
                        if isinstance(gov, str): c_img1.image(gov, caption="Passport / Govt ID")
                        else: c_img1.image(bytes(gov), caption="Passport / Govt ID")
                    if pd.notna(lic) and lic:
                        if isinstance(lic, str): c_img2.image(lic, caption="Driver's License")
                        else: c_img2.image(bytes(lic), caption="Driver's License")
                    if pd.notna(sig) and sig:
                        if isinstance(sig, str): st.image(sig, caption="Digitally Signed MOA", width=300)
                        else: st.image(bytes(sig), caption="Digitally Signed MOA", width=300)
                    
                    if st.button("APPROVE AFFILIATE", key=f"aa_{r['id']}", type="primary", use_container_width=True):
                        conn.execute("UPDATE platform_users SET admin_status = 'APPROVED' WHERE id = ?", (r['id'],))
                        conn.commit()
                        
                        # --- TRIGGER AFFILIATE MAGIC LINK EMAIL ---
                        with st.spinner("Sending approval email with Magic Link..."):
                            success, error_msg = send_approval_email(r.get('email', ''), r['full_name'], 'AFFILIATE')
                            
                            if success:
                                st.success(f"Affiliate approved! Magic link sent to {r.get('email', '')}.")
                                time.sleep(1.5)
                                st.rerun() 
                            else:
                                st.error(f"⚠️ Email Failed! The system says: {error_msg}")
                                st.stop() 
        except Exception as e:
            st.warning(f"Could not load Affiliate database: {e}")

    with p_tabs[2]:
        try:
            drivers = pd.read_sql_query("SELECT * FROM drivers WHERE admin_status = 'PENDING'", conn)
            if drivers.empty: st.info("No pending drivers.")
            for i, d in drivers.iterrows():
                with st.expander(f"{d['first_name']} {d['last_name']} (Affiliate: @{d['owner_username']})"):
                    st.write(f"Age: {d['age']} | Contact: {d['contact_number']}")
                    c_img1, c_img2 = st.columns(2)
                    
                    gov = d.get('gov_id') if pd.notna(d.get('gov_id')) else d.get('govt_id_img')
                    lic = d.get('lic_id') if pd.notna(d.get('lic_id')) else d.get('license_img')
                    
                    if pd.notna(gov) and gov:
                        if isinstance(gov, str): c_img1.image(gov, caption="Govt ID")
                        else: c_img1.image(bytes(gov), caption="Govt ID")
                    if pd.notna(lic) and lic:
                        if isinstance(lic, str): c_img2.image(lic, caption="Professional License")
                        else: c_img2.image(bytes(lic), caption="Professional License")
                    
                    if st.button("APPROVE DRIVER", key=f"da_{d['id']}", type="primary", use_container_width=True):
                        conn.execute("UPDATE drivers SET admin_status = 'APPROVED' WHERE id = ?", (d['id'],))
                        conn.commit()
                        st.success("Driver approved.")
                        time.sleep(1)
                        st.rerun()
        except Exception as e:
            st.warning(f"Could not load Driver database: {e}")

# --- TAB 1: ASSETS ---
with tabs[1]:
    try:
        pv = pd.read_sql_query("SELECT * FROM vehicles WHERE admin_status = 'PENDING'", conn)
        if pv.empty: 
            st.info("No vehicles currently pending approval.")
        else:
            for i, r in pv.iterrows():
                with st.expander(f" {r['make']} {r['model']} ({r['plate']})"):
                    st.write("### Vehicle Documents")
                    c_doc1, c_doc2, c_doc3 = st.columns(3)
                    with c_doc1: display_document(r.get('or_img'), "Official Receipt (OR)")
                    with c_doc2: display_document(r.get('cr_img'), "Certificate of Reg (CR)")
                    with c_doc3: display_document(r.get('insurance_img'), "Insurance Policy")
                    st.divider()
                    if st.button("✅ APPROVE & ACTIVATE", key=f"v_app_{r['id']}", type="primary", use_container_width=True):
                        conn.execute("UPDATE vehicles SET admin_status = 'APPROVED', booking_status = 'AVAILABLE' WHERE id = ?", (r['id'],))
                        conn.commit()
                        st.success(f"Success! {r['plate']} is now visible in the Showroom.")
                        time.sleep(1); st.rerun()
    except Exception as e:
        st.warning(f"Could not load Vehicles database: {e}")

# --- TAB 2: LOGISTICS ---
with tabs[2]:
    st.subheader("Active Logistics & Payment Status")
    try:
        query = """
            SELECT b.*, u_renter.full_name as renter_name, u_owner.full_name as affiliate_name 
            FROM bookings b 
            JOIN platform_users u_renter ON b.renter_username = u_renter.username 
            JOIN vehicles v ON b.vehicle_id = v.id 
            JOIN platform_users u_owner ON v.owner_username = u_owner.username 
            WHERE b.status != 'COMPLETED' AND b.status != 'CANCELLED'
            ORDER BY b.id DESC
        """
        bookings = pd.read_sql_query(query, conn)
        if bookings.empty: st.info("No active logistics.")
        else:
            for i, r in bookings.iterrows():
                status_color = "🔴 AWAITING PAYMENT" if r['status'] == 'PENDING' else f"🟢 {r['status']}"
                
                with st.expander(f"🎫 #{r['booking_ref']} | {status_color} | RENTER: {r['renter_name']}"):
                    st.write(f"**Amount:** ₱{r['amount']:,.2f} | **Destination:** {r.get('destination')}")
                    st.write(f"**Affiliate:** {r['affiliate_name']}")
                    
                    if r['status'] == 'PENDING':
                        st.warning("⏳ This renter is currently at the PayMongo checkout screen. If they paid via manual GCash transfer instead, you can override and confirm the booking below.")
                        if st.button("Verify Payment & Confirm Booking", key=f"force_conf_{r['id']}"):
                            conn.execute("UPDATE bookings SET status = 'CONFIRMED' WHERE id = ?", (r['id'],))
                            conn.commit()
                            st.success("Booking Confirmed!")
                            time.sleep(1); st.rerun()
    except Exception as e: st.error(f"Error loading logistics data: {e}")

# --- TAB 3: FINANCIALS ---
with tabs[3]:
    st.markdown("<h2 style='text-align: center;'>🏦 MASTER FINANCIAL LEDGER</h2>", unsafe_allow_html=True)
    try:
        settings_df = pd.read_sql_query("SELECT renter_markup_pct, affiliate_share_pct FROM platform_settings WHERE id = 1", conn)
        if not settings_df.empty:
            r_markup = float(settings_df.iloc[0]['renter_markup_pct'])
            a_share = float(settings_df.iloc[0]['affiliate_share_pct'])
        else:
            r_markup, a_share = 0.07, 0.85 

        f_tabs = st.tabs(["💸 BPI VERIFICATION", "📑 MASTER LEDGER", "📤 PROCESS PAYOUTS", "🎫 ISSUE RECEIPTS"])

        # --- SUB-TAB 0: BPI VERIFICATION ---
        with f_tabs[0]:
            st.markdown("#### 🔍 Awaiting BPI Confirmation")
            pending_bpi = pd.read_sql_query("""
                SELECT b.*, u.full_name as Renter, v.make, v.model
                FROM bookings b 
                JOIN platform_users u ON b.renter_username = u.username 
                JOIN vehicles v ON b.vehicle_id = v.id
                WHERE b.status IN ('PENDING', 'VERIFYING')
                ORDER BY b.id DESC
            """, conn)
            
            if pending_bpi.empty:
                st.info("No bookings currently awaiting payment verification.")
            else:
                for _, row in pending_bpi.iterrows():
                    with st.container(border=True):
                        c_info, c_acts = st.columns([2, 1])
                        with c_info:
                            st.write(f"**Ref:** #{row['booking_ref']} | **Renter:** {row['Renter']}")
                            st.write(f"**Vehicle:** {row['make']} {row['model']}")
                            st.write(f"**Amount to Verify:** :green[₱{row['amount']:,.2f}]")
                            st.caption(f"Pickup: {row['pickup_time']} | Destination: {row['destination']}")
                        with st.expander("👁️ View Chat & Receipts"):
                            msgs = pd.read_sql_query("SELECT * FROM chat_messages WHERE booking_ref = ? ORDER BY timestamp ASC", conn, params=(row['booking_ref'],))
                            if msgs.empty:
                                st.info("No messages or receipts uploaded yet.")
                            else:
                                for _, m in msgs.iterrows():
                                    st.write(f"**{m['sender_username']}:** {m['message_text']}")
                                    if m.get('image_path') and os.path.exists(m['image_path']):
                                        st.image(m['image_path'], width=200)
                        
                        # FIXED: Re-aligned Button Logic
                        with c_acts:
                            if st.button("✅ CONFIRM PAYMENT", key=f"verify_{row['booking_ref']}", type="primary", use_container_width=True):
                                conn.execute("UPDATE bookings SET status = 'CONFIRMED' WHERE booking_ref = ?", (row['booking_ref'],))
                                conn.commit()
                                
                                try:
                                    aff_data = conn.execute("""
                                        SELECT u.contact_number, v.make, v.model, u.full_name
                                        FROM bookings b
                                        JOIN vehicles v ON b.vehicle_id = v.id
                                        JOIN platform_users u ON v.owner_username = u.username
                                        WHERE b.booking_ref = ?
                                    """, (row['booking_ref'],)).fetchone()
                                    
                                    if aff_data and aff_data[0]:
                                        aff_phone = str(aff_data[0])
                                        car_name = f"{aff_data[1]} {aff_data[2]}"
                                        aff_name = aff_data[3].split()[0]
                                        
                                        message = f"DriveElite: Hi {aff_name}, payment for your {car_name} (Ref: #{row['booking_ref']}) is VERIFIED! Please prepare the vehicle."
                                        send_sms_alert(aff_phone, message)
                                except Exception:
                                    pass

                                st.success(f"Verified! Booking #{row['booking_ref']} moved to Ledger.")
                                time.sleep(1)
                                st.rerun()
                            
                            if st.button("❌ REJECT / CANCEL", key=f"reject_{row['booking_ref']}", use_container_width=True):
                                conn.execute("UPDATE bookings SET status = 'CANCELLED' WHERE booking_ref = ?", (row['booking_ref'],))
                                conn.commit()
                                st.warning(f"Booking #{row['booking_ref']} has been manually cancelled.")
                                time.sleep(1)
                                st.rerun()

        # --- SUB-TAB 1: MASTER LEDGER & ANALYTICS ---
        query = """
        SELECT b.id, b.booking_ref, b.pickup_time as Date, b.return_time, u_renter.full_name as Renter, u_owner.full_name as Affiliate,
               b.amount as Total_Paid_By_Renter, b.status as Trip_Status, b.payout_status as Payout_Status,
               b.gateway_fee, v.bank_name, v.account_no
        FROM bookings b
        JOIN vehicles v ON b.vehicle_id = v.id
        JOIN platform_users u_renter ON b.renter_username = u_renter.username
        JOIN platform_users u_owner ON v.owner_username = u_owner.username
        WHERE b.status != 'PENDING' AND b.status != 'CANCELLED' 
        ORDER BY b.id DESC
        """
        df = pd.read_sql_query(query, conn)

        with f_tabs[1]:
            if df.empty:
                st.info("No completed financial transactions recorded yet.")
            else:
                # 0. CALCULATE LEDGER METRICS
                df['gateway_fee'] = df['gateway_fee'].fillna(0)
                df['pickup_dt'] = pd.to_datetime(df['Date'], errors='coerce')
                df['return_dt'] = pd.to_datetime(df['return_time'], errors='coerce')
                
                # Affiliate & Platform Gross Splits
                df['Affiliate_Gross_Share'] = df['Total_Paid_By_Renter'] * a_share
                df['Platform_Gross_Cut'] = df['Total_Paid_By_Renter'] - df['Affiliate_Gross_Share']
                
                # Affiliate Net Payout (Absorbs the payment gateway fee)
                df['Affiliate_Net_Payout'] = df['Affiliate_Gross_Share'] - df['gateway_fee']
                
                # Platform EWT & Net Income (Calculates 2% tax provision on the platform's share)
                PLATFORM_TAX_RATE = 0.02
                df['Platform_EWT'] = df['Platform_Gross_Cut'] * PLATFORM_TAX_RATE
                df['Platform_Net_Income'] = df['Platform_Gross_Cut'] - df['Platform_EWT']
                
                df['Ref'] = df.apply(lambda x: f"#{x['booking_ref']}" if pd.notnull(x.get('booking_ref')) else f"DRV-{x['id']:05d}", axis=1)

                # 1. DISPLAY EXISTING MASTER LEDGER & EXPORT BUTTON
                st.subheader("📑 Master Ledger")
                st.caption(f"Calculated based on MOA: Owner Share ({a_share*100}%) | Platform Share ({100 - a_share*100}%) minus {PLATFORM_TAX_RATE*100}% EWT")
                
                # --- CSV EXPORT FEATURE ---
                export_cols = ['Ref', 'Date', 'Renter', 'Affiliate', 'Total_Paid_By_Renter', 'gateway_fee', 'Affiliate_Net_Payout', 'Platform_Gross_Cut', 'Platform_EWT', 'Platform_Net_Income', 'Payout_Status']
                csv_data = df[export_cols].to_csv(index=False).encode('utf-8')
                
                st.download_button(
                    label="📥 Download Monthly Bookkeeper Export (CSV)",
                    data=csv_data,
                    file_name=f"DriveElite_Financial_Export_{datetime.date.today().strftime('%Y_%m')}.csv",
                    mime="text/csv",
                    type="primary"
                )
                st.write("") 
                # --------------------------
                
                display_cols = ['Ref', 'Date', 'Affiliate', 'Total_Paid_By_Renter', 'Affiliate_Net_Payout', 'Platform_Gross_Cut', 'Platform_EWT', 'Platform_Net_Income', 'Payout_Status']
                
                styled_ledger = df[display_cols].style.format({
                    'Total_Paid_By_Renter': '₱{:,.2f}', 'Affiliate_Net_Payout': '₱{:,.2f}', 
                    'Platform_Gross_Cut': '₱{:,.2f}', 'Platform_EWT': '₱{:,.2f}', 'Platform_Net_Income': '₱{:,.2f}'
                })
                st.dataframe(styled_ledger, use_container_width=True, hide_index=True)
                
                st.divider()
                st.subheader("📊 Platform Revenue Analytics")
                
                # 2. PERFORM TIME-BASED GROUPING
                df['Date'] = pd.to_datetime(df['Date'])
                
                monthly_data = df.groupby(pd.Grouper(key='Date', freq='ME'))[['Platform_Gross_Cut', 'Platform_EWT', 'Platform_Net_Income']].sum()
                quarterly_data = df.groupby(pd.Grouper(key='Date', freq='QE'))[['Platform_Gross_Cut', 'Platform_EWT', 'Platform_Net_Income']].sum()
                yearly_data = df.groupby(pd.Grouper(key='Date', freq='YE'))[['Platform_Gross_Cut', 'Platform_EWT', 'Platform_Net_Income']].sum()

                # 3. DISPLAY PERFORMANCE METRICS
                col1, col2, col3 = st.columns(3)
                col1.metric("Monthly Platform Net", f"₱{monthly_data['Platform_Net_Income'].iloc[-1]:,.2f}", f"Gross: ₱{monthly_data['Platform_Gross_Cut'].iloc[-1]:,.2f}")
                col2.metric("Quarterly Platform Net", f"₱{quarterly_data['Platform_Net_Income'].iloc[-1]:,.2f}", f"Gross: ₱{quarterly_data['Platform_Gross_Cut'].iloc[-1]:,.2f}")
                col3.metric("Yearly Platform Net", f"₱{yearly_data['Platform_Net_Income'].iloc[-1]:,.2f}", f"Gross: ₱{yearly_data['Platform_Gross_Cut'].iloc[-1]:,.2f}")

                st.divider()
                
                # 4. PLATFORM EWT MONTHLY REPORT
                st.markdown("### 🧾 Platform Tax Provision Summary")
                st.write("This tracks the estimated EWT/Percentage Tax on your platform's revenue to set aside for BIR filing.")
                
                ewt_report = monthly_data[['Platform_Gross_Cut', 'Platform_EWT', 'Platform_Net_Income']]
                ewt_report.index = ewt_report.index.strftime('%B %Y') 
                
                st.dataframe(ewt_report.style.format('₱{:,.2f}'), use_container_width=True)

        # --- SUB-TAB 2: PROCESS PAYOUTS ---
        with f_tabs[2]:
            if not df.empty:
                pending_p = df[(df['Trip_Status'] == 'COMPLETED') & (df['Payout_Status'] == 'PENDING')]
                if pending_p.empty: st.info("No pending payouts at this time.")
                for _, p in pending_p.iterrows():
                    with st.expander(f"{p['Ref']} | {p['Affiliate']} | Trip Net: ₱{p['Affiliate_Net_Payout']:,.2f}"):
                        
                        # 1. Look up the affiliate's username and current penalty balance
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
                        except:
                            aff_username, current_penalty = "", 0.0
                        
                        final_payout = p['Affiliate_Net_Payout']
                        penalty_to_deduct = 0.0
                        
                        # 2. Automatically calculate deductions if they owe the platform money
                        if current_penalty > 0:
                            st.warning(f"⚠️ {p['Affiliate']} has an outstanding penalty balance of ₱{current_penalty:,.2f}.")
                            
                            # We can only deduct up to what they actually earned on this trip
                            penalty_to_deduct = min(final_payout, current_penalty)
                            final_payout -= penalty_to_deduct
                            
                            st.error(f"➖ Automatically Deducting Penalty: ₱{penalty_to_deduct:,.2f}")
                        
                        st.write(f"### **Final Remittance:** ₱{final_payout:,.2f}")
                        st.caption(f"Bank: {p.get('bank_name', 'N/A')} | Acct: {p.get('account_no', 'N/A')}")
                        
                        # 3. Process the payout and update the ledger
                        if st.button("MARK AS PAID", key=f"p_{p['id']}", type="primary", use_container_width=True):
                            # Mark the trip as paid
                            conn.execute("UPDATE bookings SET payout_status = 'PAID' WHERE id = ?", (p['id'],))
                            
                            # Reduce their penalty balance in the database
                            if penalty_to_deduct > 0:
                                conn.execute("UPDATE platform_users SET penalty_balance = penalty_balance - ? WHERE username = ?", (penalty_to_deduct, aff_username))
                            
                            conn.commit()
                            st.success("✅ Payout Recorded and Ledger Updated!")
                            time.sleep(1.5)
                            st.rerun()

        # --- SUB-TAB 3: ISSUE RECEIPTS ---
        with f_tabs[3]:
            if not df.empty:
                st.markdown("#### Manual POS Issuance")
                target_ref = st.selectbox("Select Transaction Reference", df['Ref'].tolist())
                if st.button("Generate POS Receipt", type="primary"):
                    b_data = df[df['Ref'] == target_ref].iloc[0]
                    st.code(generate_pos_receipt(b_data), language='text')
    
    except Exception as e:
        st.error(f"Financial Error: {e}")

# --- TAB 4: FILING CABINET ---
with tabs[4]: 
    st.header("🗄️ Master Digital Filing Cabinet")
    st.write("View legally binding contracts, download them, instantly email a copy, or delete test documents.")
    
    if os.path.exists(UPLOAD_DIR):
        all_files = os.listdir(UPLOAD_DIR)
        pdf_files = [f for f in all_files if f.endswith('.pdf')]
        
        if len(pdf_files) > 0:
            st.divider()
            # ADDED: A specific filter for Handovers and Settlements
            role_filter = st.radio("Filter Contracts:", ["All", "💼 Affiliates (MOA)", "🚙 Renters (Agreements)", "🤝 Handovers & Settlements"], horizontal=True)
            st.divider()
            
            if role_filter == "💼 Affiliates (MOA)": filtered_files = [f for f in pdf_files if f.startswith("MOA_")]
            elif role_filter == "🚙 Renters (Agreements)": filtered_files = [f for f in pdf_files if f.startswith("RENTER_")]
            elif role_filter == "🤝 Handovers & Settlements": filtered_files = [f for f in pdf_files if f.startswith("Handover_") or f.startswith("Settlement_")]
            else: filtered_files = pdf_files
            
            if not filtered_files: st.info(f"No documents found matching the filter.")
            else:
                cols = st.columns(4)
                for i, file_name in enumerate(filtered_files):
                    file_path = os.path.join(UPLOAD_DIR, file_name)
                    display_card_text = file_name 
                    uname, target_email = "", ""
                    
                    if file_name.startswith("MOA_") or file_name.startswith("RENTER_"):
                        uname = file_name.replace("MOA_", "").replace("RENTER_", "").replace(".pdf", "")
                        try:
                            user_df = pd.read_sql_query("SELECT full_name, email FROM platform_users WHERE username=?", conn, params=(uname,))
                            if not user_df.empty:
                                target_email, full_name = user_df.iloc[0]['email'], user_df.iloc[0]['full_name']
                                display_card_text = f"{full_name} / {uname}" if full_name else f"(@{uname})"
                        except: pass 
                    
                    with cols[i % 4]:
                        with st.container(border=True):
                            st.write(f"📄 **{display_card_text}**")
                            
                            # UPDATED: 3-Column layout for the buttons
                            c_dl, c_email, c_del = st.columns([2, 2, 1])
                            
                            with c_dl:
                                with open(file_path, "rb") as pdf_file:
                                    st.download_button(label="⬇️ DL", data=pdf_file.read(), file_name=file_name, mime="application/pdf", key=f"dl_{file_name}", use_container_width=True)
                            
                            with c_email:
                                if st.button("📧 Email", key=f"em_{file_name}", use_container_width=True):
                                    if not target_email: 
                                        st.toast(f"❌ No email found for this document.", icon="⚠️")
                                    else:
                                        with st.spinner("Sending..."):
                                            success = send_admin_email_with_attachment(
                                                to_email=target_email, 
                                                subject=f"Document Copy: {file_name}", 
                                                body="Please find your document attached to this email.", 
                                                attachment_path=file_path, 
                                                attachment_name=file_name
                                            )
                                        if success: st.toast(f"✅ Sent to {target_email}", icon="🚀")
                                        else: st.error("Failed to send email.")
                            
                            with c_del:
                                # NEW: Delete Button
                                if st.button("🗑️", key=f"del_{file_name}", use_container_width=True, type="primary"):
                                    try:
                                        os.remove(file_path)
                                        st.toast(f"✅ Deleted {file_name}")
                                        time.sleep(0.5)
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error: {e}")
        else: st.info("No contracts have been signed yet.")
    else: st.warning("The uploads folder does not exist yet. It will be created when the first user registers.")
                                            
# --- ACTIVE AFFILIATE DIRECTORY ---
    st.divider()
    st.markdown("### 💼 Approved Affiliates Directory")
    st.write("View active partners and their submitted legal documents.")
    
    try:
        # Fetch only approved affiliates
        app_affiliates = pd.read_sql_query("SELECT * FROM platform_users WHERE admin_status = 'APPROVED' AND role = 'AFFILIATE'", conn)
        
        if app_affiliates.empty: 
            st.info("No approved affiliates in the system yet.")
        else:
            for i, r in app_affiliates.iterrows():
                with st.expander(f"✅ {r['full_name']} (@{r['username']}) - {r['contact_number']}"):
                    c_img1, c_img2, c_img3 = st.columns(3)
                    
                    # Fetching the images safely
                    gov = r.get('gov_id') if pd.notna(r.get('gov_id')) else r.get('govt_id_img')
                    lic = r.get('lic_id') if pd.notna(r.get('lic_id')) else r.get('license_img')
                    sig = r.get('signature') if pd.notna(r.get('signature')) else r.get('signature_img')
                    
                    # Displaying Govt ID
                    if pd.notna(gov) and gov:
                        if isinstance(gov, str): c_img1.image(gov, caption="Passport / Govt ID")
                        else: c_img1.image(bytes(gov), caption="Passport / Govt ID")
                    
                    # Displaying License
                    if pd.notna(lic) and lic:
                        if isinstance(lic, str): c_img2.image(lic, caption="Driver's License")
                        else: c_img2.image(bytes(lic), caption="Driver's License")
                        
                    # Displaying MOA Signature
                    if pd.notna(sig) and sig:
                        if isinstance(sig, str): c_img3.image(sig, caption="Digitally Signed MOA")
                        else: c_img3.image(bytes(sig), caption="Digitally Signed MOA")
                        
                    # Optional: A button to revoke approval if they violate terms
                    if st.button("Revoke Approval / Suspend", key=f"suspend_{r['id']}"):
                        conn.execute("UPDATE platform_users SET admin_status = 'SUSPENDED' WHERE id = ?", (r['id'],))
                        conn.commit()
                        st.rerun()
                        
    except Exception as e:
        st.warning(f"Could not load Affiliate directory: {e}")

# --- TAB 5: PROMOS & DB ---
with tabs[5]:
    render_platform_settings(conn)
    st.divider()

    render_admin_discount_table(conn)
    st.divider()

    col_promo, col_cat = st.columns(2)
    with col_promo:
        st.subheader("📢 Broadcast Manager")
        try:
            current_active = pd.read_sql_query("SELECT id FROM admin_promos WHERE active = 1", conn)
            banner_is_on = not current_active.empty
            turn_on = st.toggle("📡 Master Broadcast Switch (Turn ON / OFF)", value=banner_is_on)
            if turn_on != banner_is_on:
                if turn_on: conn.execute("UPDATE admin_promos SET active = 1 WHERE id = (SELECT MAX(id) FROM admin_promos)")
                else: conn.execute("UPDATE admin_promos SET active = 0")
                conn.commit(); st.rerun()
        except Exception as e:
            st.warning(f"Could not load broadcast system: {e}")
            
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
                    except: 
                        pass
                    
                    target_map = {
                        "RENTERS": "RENTER", 
                        "AFFILIATES": "AFFILIATE", 
                        "ALL USERS": "ALL USERS"
                    }
                    db_target = target_map[target]
                    
                    conn.execute("UPDATE admin_promos SET active = 0")
                    conn.execute(
                        "INSERT INTO admin_promos (title, message, target, active) VALUES (?, ?, ?, 1)", 
                        (t, m, db_target)
                    )
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
                    try: conn.execute("INSERT INTO vehicle_categories (name, default_price) VALUES (?, ?)", (n.title(), p)); conn.commit()
                    except Exception as e: st.error(f"Error adding category: {e}")

    # =========================================================
    #  PASTE THE PENALTY MANAGER RIGHT HERE! 
    # =========================================================
    st.divider()
    st.markdown("<h3 style='text-align: center;'>⚖️ AFFILIATE PENALTY MANAGER</h3>", unsafe_allow_html=True)
    st.write("Apply No-Show or Cancellation fines. These will be automatically tracked against their ledger.")
    
    try:
        affiliates_df = pd.read_sql_query("SELECT id, username, full_name, penalty_balance FROM platform_users WHERE role = 'AFFILIATE'", conn)
        
        if not affiliates_df.empty:
            with st.form("apply_penalty_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    aff_options = affiliates_df.apply(lambda x: f"{x['full_name']} (@{x['username']}) | Owes: ₱{x['penalty_balance']:,.2f}", axis=1).tolist()
                    selected_aff = st.selectbox("Select Affiliate to Penalize:", aff_options)
                    target_username = selected_aff.split("(@")[1].split(")")[0]
                
                with col2:
                    penalty_amount = st.number_input("Penalty Amount (₱)", min_value=0.0, step=500.0)
                    penalty_reason = st.text_input("Reason (e.g., No-Show Ref #12345)")
                
                submit_penalty = st.form_submit_button("APPLY PENALTY TO LEDGER", type="primary")
                
                if submit_penalty and penalty_amount > 0:
                    conn.execute("UPDATE platform_users SET penalty_balance = penalty_balance + ? WHERE username = ?", (penalty_amount, target_username))
                    conn.commit()
                    st.success(f"✅ ₱{penalty_amount:,.2f} penalty applied to {target_username} for: {penalty_reason}")
                    time.sleep(1.5)
                    st.rerun()
    except Exception as e:
        st.error(f"Error loading penalty manager: {e}")
    # =========================================================

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
    except Exception as e: 
        st.warning(f"Could not load master user lists: {e}")
        
    st.divider()
    st.markdown("<h3 style='text-align: center; color: #e74c3c;'>⚠️ DANGER ZONE</h3>", unsafe_allow_html=True)
    
    # --- NEW: SELECTIVE DELETION TOOL ---
    with st.expander("🗑️ SELECTIVE DELETION (Remove Specific Users or Bookings)"):
        st.write("Use this to silently clean up test accounts, dummy vehicles, and fake bookings without wiping your real data.")
        
        col_del1, col_del2 = st.columns(2)
        
        with col_del1:
            st.markdown("#### 1. Delete a User")
            st.caption("Warning: Deleting an Affiliate will also delete their registered vehicles and drivers.")
            all_users = pd.read_sql_query("SELECT username, full_name, role FROM platform_users", conn)
            
            if not all_users.empty:
                user_opts = ["-- Select User --"] + all_users.apply(lambda x: f"{x['full_name']} (@{x['username']}) - {x['role']}", axis=1).tolist()
                user_to_del = st.selectbox("Select Dummy User to Delete:", user_opts)
                
                if st.button("🗑️ DELETE USER", type="primary"):
                    if user_to_del != "-- Select User --":
                        del_username = user_to_del.split("(@")[1].split(")")[0]
                        
                        # Execute deep deletion to prevent orphaned data
                        conn.execute("DELETE FROM platform_users WHERE username = ?", (del_username,))
                        conn.execute("DELETE FROM vehicles WHERE owner_username = ?", (del_username,))
                        conn.execute("DELETE FROM drivers WHERE owner_username = ?", (del_username,))
                        conn.commit()
                        
                        st.success(f"✅ Erased user @{del_username} and their assets from the database.")
                        time.sleep(1.5)
                        st.rerun()

        with col_del2:
            st.markdown("#### 2. Delete a Booking")
            st.caption("Warning: This completely erases the transaction and its chat history from the ledger.")
            all_bks = pd.read_sql_query("SELECT booking_ref, status FROM bookings", conn)
            
            if not all_bks.empty:
                bk_opts = ["-- Select Booking --"] + all_bks.apply(lambda x: f"#{x['booking_ref']} - {x['status']}", axis=1).tolist()
                bk_to_del = st.selectbox("Select Dummy Booking to Delete:", bk_opts)
                
                if st.button("🗑️ DELETE BOOKING", type="primary"):
                    if bk_to_del != "-- Select Booking --":
                        del_ref = bk_to_del.split(" - ")[0].replace("#", "")
                        
                        # Erase booking and associated chat history
                        conn.execute("DELETE FROM bookings WHERE booking_ref = ?", (del_ref,))
                        conn.execute("DELETE FROM chat_messages WHERE booking_ref = ?", (del_ref,))
                        conn.commit()
                        
                        st.success(f"✅ Erased booking #{del_ref} from the financial ledger.")
                        time.sleep(1.5)
                        st.rerun()

    # --- EXISTING: CLOUD FACTORY RESET ---
    with st.expander("🧨 CLOUD FACTORY RESET (Wipe All Data)"):
        st.warning("WARNING: This will permanently delete the live database and all uploaded files. DO NOT USE IF YOU HAVE REAL AFFILIATES.")
        confirm_text = st.text_input("Type 'DELETE EVERYTHING' to confirm:")
        if st.button("🔥 INITIATE FACTORY RESET", type="primary", use_container_width=True):
            if confirm_text == "DELETE EVERYTHING":
                import glob
                with st.spinner("Disconnecting and Nuking database..."):
                    try: conn.close() 
                    except: pass
                    st.cache_resource.clear() 
                    st.cache_data.clear() 
                    if os.path.exists("/data/driveelite_v2.db"): os.remove("/data/driveelite_v2.db")
                    elif os.path.exists("driveelite_v2.db"): os.remove("driveelite_v2.db")
                    if os.path.exists(UPLOAD_DIR):
                        for f in glob.glob(f"{UPLOAD_DIR}/*"):
                            try: os.remove(f)
                            except: pass
                    st.success("✅ FACTORY RESET COMPLETE! Rebooting system...")
                    time.sleep(3); st.rerun()
            else: st.error("You must type exactly 'DELETE EVERYTHING' to unlock the reset button.")

# --- TAB 6: GLOBAL REVIEWS ---
with tabs[6]:
    st.markdown("<h3 style='text-align: center;'>⭐ MASTER PLATFORM REVIEWS</h3>", unsafe_allow_html=True)
    all_rev_df = get_all_reviews(conn)
    
    if all_rev_df.empty: 
        st.info("No reviews yet or unable to fetch reviews.")
    else:
        st.metric("Platform Average Rating", f"{all_rev_df['rating'].mean():.1f} ⭐")
        for _, rev in all_rev_df.iterrows():
            with st.expander(f"{'⭐'*int(rev['rating'])} | {rev['make']} {rev['model']}"):
                st.write(f"Renter: {rev['renter_name']} | Affiliate: {rev['affiliate_name']}")
                if rev['review']: st.info(rev['review'])

# --- TAB 7: PROCESS CANCELLATIONS ---
with tabs[7]:
    st.header("Process Cancellations")
    st.write("Select an active booking to calculate cancellation penalties and process refunds.")
    try:
        query = "SELECT id, booking_ref, renter_username, amount, pickup_time, status FROM bookings WHERE status NOT IN ('COMPLETED', 'CANCELLED')"
        active_bookings = pd.read_sql_query(query, conn)

        if active_bookings.empty: st.info("There are currently no active bookings eligible for cancellation.")
        else:
            booking_options = ["-- Select a Booking --"] + active_bookings['booking_ref'].astype(str).tolist()
            selected_ref = st.selectbox("Search Active Bookings:", booking_options)

            if selected_ref != "-- Select a Booking --":
                b_data = active_bookings[active_bookings['booking_ref'].astype(str) == selected_ref].iloc[0]
                booking_to_cancel, gross_paid, pickup_date = b_data['booking_ref'], float(b_data['amount']), str(b_data['pickup_time']) 

                st.divider()
                st.subheader(f"Review Details for #{booking_to_cancel}")
                st.write(f"**Renter:** @{b_data['renter_username']} | **Gross Rental Paid:** ₱{gross_paid:,.2f} | **Pickup:** {pickup_date}")

                st.write("### Extra Fee Verification")
                col_in1, col_in2 = st.columns(2)
                with col_in1: logistics = st.number_input("Logistics/Delivery Fee Paid (₱)", value=0.0, step=100.0)
                with col_in2: gateway_fee = st.number_input("Exact PayMongo Surcharge to Absorb (₱)", value=0.0, step=10.0)
                st.divider()

                try:
                    if len(pickup_date) == 16: pickup_date += ":00"
                    days_left = get_days_before_pickup(pickup_date)
                    settlement = calculate_moa_cancellation_40_60(gross_rental_paid=gross_paid, logistics_paid=logistics, exact_gateway_fee=gateway_fee, days_before_pickup=days_left)

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

                    if st.button(" Finalize Cancellation & Update Database", type="primary"):
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
                        target_email = aff_data.iloc[0]['email'] if not aff_data.empty else "contact@driveelite.ph"

                        email_success = send_alert_email(target_email, f"DriveElite Cancellation Notice: #{booking_to_cancel}", sample_receipt_text)
                        
                        if email_success:
                            st.success(f"✅ Cancelled! Compensation email sent to {target_email}.")
                        else:
                            st.warning("⚠️ Database updated, but the email failed to send.")
                            
                        time.sleep(1.5)
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
                st.write("*Admin Note: If a penalty or deduction is required from the security deposit, please contact both parties directly using the phone numbers provided above to finalize mediation.*")
    except Exception as e:
        st.warning(f"Error loading evidence center: {e}")

# --- TAB 9: SYSTEM SETTINGS (The Master Switch) ---
with tabs[9]:
    st.markdown("<h2 style='text-align: center;'>⚙️ SYSTEM SETTINGS</h2>", unsafe_allow_html=True)
    
    st.markdown("### 💳 Payment Gateway Control")
    st.info("Toggle the payment system between automated PayMongo and manual BPI QR. This updates the Renter checkout experience instantly.")
    
    # Fetch current settings to see what is currently active
    try:
        settings_df = pd.read_sql_query("SELECT payment_mode FROM platform_settings WHERE id = 1", conn)
        current_mode = settings_df.iloc[0]['payment_mode'] if not settings_df.empty else "MANUAL_QR"
    except Exception:
        current_mode = "MANUAL_QR"

    new_mode = st.radio("Active Payment System:", 
                        ["MANUAL_QR", "PAYMONGO"], 
                        index=0 if current_mode == "MANUAL_QR" else 1)

    if st.button("Save Payment Settings", type="primary"):
        try:
            conn.execute("UPDATE platform_settings SET payment_mode = ? WHERE id = 1", (new_mode,))
            conn.commit()
            st.success(f"✅ System successfully updated to use {new_mode}!")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Database error: {e}")
