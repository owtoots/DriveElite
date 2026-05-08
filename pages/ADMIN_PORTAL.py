import sys
import os
import smtplib
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
from fpdf import FPDF  # Added for PDF Receipt Generation

# --- AUTHENTICATION & PAGE CONFIG ---
st.set_page_config(page_title="DriveElite Admin", layout="wide")

# ==========================================
# 🚨 "CRYSTAL ELITE" CSS ENGINE 🚨
# ==========================================
st.sidebar.image("logo.png", use_container_width=True)

st.markdown("""
<style>
    /* --- GLOBAL THEME --- */
    [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #F8FAFC !important;
        color: #0F172A !important;
        font-family: 'Inter', -apple-system, sans-serif !important;
    }
    
    /* --- SIDEBAR & LOGO REORDER HACK --- */
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

    /* --- CARDS & BUTTONS --- */
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
        background-color: #1D4ED8 !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
        transform: translateY(-1px) !important;
    }

    /* --- TYPOGRAPHY & INPUTS --- */
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
import importlib.util

required_modules = ['database_utils', 'tiered_discounts', 'finance']
missing = [mod for mod in required_modules if importlib.util.find_spec(mod) is None]

if missing:
    st.error(f"🚨 Critical System Error: Missing required modules: {', '.join(missing)}")
    st.stop()

from database_utils import get_connection, init_db, patch_database
from tiered_discounts import init_discount_db, render_admin_discount_table, render_platform_settings
from finance import get_days_before_pickup, calculate_moa_cancellation_40_60

# ==========================================
# 4. GLOBAL CONSTANTS & CONFIGURATION
# ==========================================
ADMIN_USERNAME = st.secrets.get("admin_username", "masterom")
ADMIN_PASSWORD = st.secrets.get("admin_password")
SENDER_EMAIL = st.secrets.get("email_sender")
EMAIL_APP_PASSWORD = st.secrets.get("email_app_password")

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
    conn.execute("ALTER TABLE platform_settings ADD COLUMN payment_mode TEXT DEFAULT 'MANUAL_QR'")
    conn.commit()
except:
    pass

# ==========================================
# 6. UTILITY FUNCTIONS (UNIFIED EMAILS, CACHE & POS)
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

def send_email(to_email, subject, body, attachment_path=None, attachment_name=None):
    try:
        if not SENDER_EMAIL or not EMAIL_APP_PASSWORD:
            return False, "Email credentials missing in Streamlit secrets."
            
        if attachment_path and os.path.exists(attachment_path):
            msg = MIMEMultipart()
            msg['From'] = f"DriveElite Admin <{SENDER_EMAIL}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            with open(attachment_path, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename= {attachment_name}")
            msg.attach(part)
        else:
            msg = EmailMessage()
            msg.set_content(body)
            msg['Subject'] = subject
            msg['From'] = f"DriveElite Admin <{SENDER_EMAIL}>"
            msg['To'] = to_email
            
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, EMAIL_APP_PASSWORD)
            smtp.send_message(msg)
        return True, "Email sent successfully!"
    except Exception as e:
        return False, f"Failed to send email: {str(e)}"

def send_pdf_email(to_email, subject, body, pdf_bytes, filename):
    try:
        if not SENDER_EMAIL or not EMAIL_APP_PASSWORD: return False
        msg = MIMEMultipart()
        msg['From'] = f"DriveElite Admin <{SENDER_EMAIL}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(pdf_bytes)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {filename}")
        msg.attach(part)
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, EMAIL_APP_PASSWORD)
            server.send_message(msg)
        return True
    except: 
        return False

def generate_booking_receipt(ref_no, renter_name, vehicle, plate, travel_dates, amount, pickup_loc, return_loc):
    pdf = FPDF(orientation='L', unit='mm', format='A5')
    pdf.add_page()
    try: pdf.image("logo.png", x=15, y=12, w=25)
    except: pass
        
    pdf.set_y(15)
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 6, "DRIVEELITE PLATFORM", ln=True, align='R')
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(0, 5, "Official Booking Receipt", ln=True, align='R')
    pdf.cell(0, 5, f"Date: {datetime.date.today()}", ln=True, align='R')
    pdf.cell(0, 5, f"Receipt No: {ref_no}", ln=True, align='R')
    
    pdf.ln(8)
    pdf.set_line_width(0.5)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(8)
    
    pdf.set_font("Helvetica", '', 12)
    pdf.cell(35, 8, "Received From:", ln=0)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 8, f"{renter_name}", ln=1)
    
    pdf.set_font("Helvetica", '', 12)
    pdf.cell(35, 8, "The Sum Of:", ln=0)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 8, f"Php {amount:,.2f}", ln=1)
    
    pdf.ln(5)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(0, 6, "IN FULL PAYMENT FOR RESERVATION:", ln=1)
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(30, 6, "Vehicle:", ln=0)
    pdf.cell(0, 6, f"{vehicle} ({plate})", ln=1)
    pdf.cell(30, 6, "Travel Dates:", ln=0)
    pdf.cell(0, 6, f"{travel_dates}", ln=1)
    pdf.cell(30, 6, "Pickup Loc:", ln=0)
    pdf.cell(0, 6, f"{pickup_loc}", ln=1)
    pdf.cell(30, 6, "Return Loc:", ln=0)
    pdf.cell(0, 6, f"{return_loc}", ln=1)
    
    pdf.ln(5)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(5)
    
    pdf.set_font("Helvetica", 'I', 8)
    pdf.cell(0, 4, "This is a system-generated Official Booking Receipt.", align='C', ln=1)
    pdf.cell(0, 4, "Valid for corporate reimbursement and proof of reservation payment. No physical signature required.", align='C', ln=1)
    
    return pdf.output(dest="S").encode("latin-1")

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
                    if pd.notna(r.get('govt_id_img')) and r.get('govt_id_img'): c_img1.image(r['govt_id_img'], caption="Passport / Govt ID")
                    if pd.notna(r.get('license_img')) and r.get('license_img'): c_img2.image(r['license_img'], caption="Driver's License")
                    if st.button("APPROVE RENTER", key=f"ra_{r['id']}", type="primary", use_container_width=True):
                        conn.execute("UPDATE platform_users SET admin_status = 'APPROVED' WHERE id = ?", (r['id'],))
                        conn.commit(); st.rerun()
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
                    if pd.notna(r.get('govt_id_img')) and r.get('govt_id_img'): c_img1.image(r['govt_id_img'], caption="Passport / Govt ID")
                    if pd.notna(r.get('license_img')) and r.get('license_img'): c_img2.image(r['license_img'], caption="Driver's License") 
                    if pd.notna(r.get('signature_img')) and r.get('signature_img'): st.image(r['signature_img'], caption=f"Digitally Signed MOA", width=300)
                    if st.button("APPROVE AFFILIATE", key=f"aa_{r['id']}", type="primary", use_container_width=True):
                        conn.execute("UPDATE platform_users SET admin_status = 'APPROVED' WHERE id = ?", (r['id'],))
                        conn.commit(); st.rerun()
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
                    if pd.notna(d.get('govt_id_img')) and d.get('govt_id_img'): c_img1.image(d['govt_id_img'], caption="Govt ID")
                    if pd.notna(d.get('license_img')) and d.get('license_img'): c_img2.image(d['license_img'], caption="Professional License")
                    if st.button("APPROVE DRIVER", key=f"da_{d['id']}", type="primary", use_container_width=True):
                        conn.execute("UPDATE drivers SET admin_status = 'APPROVED' WHERE id = ?", (d['id'],))
                        conn.commit(); st.rerun()
        except Exception as e:
            st.warning(f"Could not load Driver database: {e}")

# --- TAB: ASSETS (Vehicle Approvals) ---
with tabs[1]: # (Make sure this matches your tab index for Assets)
    st.subheader("🚗 Vehicle Onboarding Queue")
    
    # Fetch all vehicles waiting for Admin approval
    pending_cars = pd.read_sql_query("SELECT * FROM vehicles WHERE admin_status = 'PENDING'", conn)
    
    if pending_cars.empty:
        st.info("No vehicles currently waiting for approval.")
    else:
        for _, v in pending_cars.iterrows():
            with st.expander(f"Review: {v['make']} {v['model']} ({v['plate']}) - Owner: @{v['owner_username']}"):
                
                # -----------------------------------------
                # 1. SHOW THE ACTUAL CAR PHOTO
                # -----------------------------------------
                st.markdown("#### 📸 Vehicle Photo")
                if v.get('vehicle_img') and os.path.exists(v['vehicle_img']):
                    # Display the car photo slightly smaller so it doesn't take up the whole screen
                    st.image(v['vehicle_img'], width=400)
                else:
                    st.warning("No vehicle photo uploaded.")
                
                st.divider()
                
                # -----------------------------------------
                # 2. SMART DOCUMENT VIEWER (Handles PDFs & Images)
                # -----------------------------------------
                st.markdown("#### 📄 Legal Documents")
                c_or, c_cr, c_ins = st.columns(3)
                
                def render_document(col, title, file_path):
                    with col:
                        st.write(f"**{title}**")
                        # Check if the file exists in the database and in the folder
                        if file_path and os.path.exists(file_path):
                            # If it's a PDF, create a Download/View Button
                            if file_path.lower().endswith('.pdf'):
                                with open(file_path, "rb") as f:
                                    st.download_button(
                                        label=f"📄 Download {title} (PDF)", 
                                        data=f, 
                                        file_name=os.path.basename(file_path), 
                                        key=f"dl_{title}_{v['id']}", 
                                        use_container_width=True
                                    )
                            # If it's an Image (JPG/PNG), display it normally
                            else:
                                st.image(file_path, use_container_width=True)
                        else:
                            st.error("Missing File")

                # Render all three documents safely
                render_document(c_or, "Official Receipt (OR)", v.get('or_img'))
                render_document(c_cr, "Certificate of Reg (CR)", v.get('cr_img'))
                render_document(c_ins, "Insurance Policy", v.get('insurance_img'))
                
                st.divider()
                
                # -----------------------------------------
                # 3. APPROVAL CONTROLS
                # -----------------------------------------
                c_app, c_rej = st.columns(2)
                if c_app.button("✅ APPROVE & LIST VEHICLE", key=f"app_{v['id']}", type="primary", use_container_width=True):
                    conn.execute("UPDATE vehicles SET admin_status = 'APPROVED', booking_status = 'AVAILABLE' WHERE id = ?", (v['id'],))
                    conn.commit()
                    st.success(f"{v['make']} {v['model']} Approved! It is now live in the Renter Showroom.")
                    time.sleep(2)
                    st.rerun()
                    
                if c_rej.button("❌ REJECT VEHICLE", key=f"rej_{v['id']}", use_container_width=True):
                    conn.execute("UPDATE vehicles SET admin_status = 'REJECTED' WHERE id = ?", (v['id'],))
                    conn.commit()
                    st.warning("Vehicle Rejected. It will not appear in the showroom.")
                    time.sleep(2)
                    st.rerun()

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
                        st.warning("⏳ This renter is currently at the checkout screen.")
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
            r_markup = 0.07 
            a_share = 0.85  

        f_tabs = st.tabs(["💸 BPI VERIFICATION", "📑 MASTER LEDGER", "📤 PROCESS PAYOUTS", "🎫 ISSUE RECEIPTS"])

        # --- SUB-TAB 0: BPI VERIFICATION ---
        with f_tabs[0]:
            st.markdown("### 🔍 Awaiting Payment Verification")
            
            query = """
                SELECT b.*, u.full_name as renter_name, u.email as renter_email, 
                       v.make, v.model, v.plate 
                FROM bookings b 
                JOIN platform_users u ON b.renter_username = u.username 
                JOIN vehicles v ON b.vehicle_id = v.id
                WHERE b.status = 'PENDING' OR b.status = 'VERIFYING'
                ORDER BY b.id DESC
            """
            pending_pay = pd.read_sql_query(query, conn)
            
            if pending_pay.empty: 
                st.info("No payments currently awaiting verification.")
            else:
                for _, row in pending_pay.iterrows():
                    with st.container(border=True):
                        st.write(f"**Ref:** #{row['booking_ref']} | **Renter:** {row['renter_name']}")
                        st.write(f"**Vehicle:** {row['make']} {row['model']} ({row['plate']})")
                        st.write(f"**Amount to Verify:** :blue[₱{row['amount']:,.2f}]")
                        
                        if row.get('receipt_img'):
                            with st.expander("👁️ View Uploaded Payment Receipt"):
                                st.image(row['receipt_img'], caption="Renter's Uploaded Proof of Payment")
                        else:
                            st.warning("⏳ Renter has not uploaded a receipt yet.")

                        c1, c2 = st.columns(2)
                        
                        if c1.button("✅ CONFIRM & SEND RECEIPT", key=f"vpay_{row['id']}", type="primary", use_container_width=True):
                            with st.spinner("Confirming payment and generating PDF receipt..."):
                                conn.execute("UPDATE bookings SET status = 'CONFIRMED' WHERE id = ?", (row['id'],))
                                conn.commit()
                                
                                travel_dates = f"{str(row['pickup_time'])[:10]} to {str(row['return_time'])[:10]}"
                                vehicle_str = f"{row['make']} {row['model']}"
                                
                                pdf_bytes = generate_booking_receipt(
                                    ref_no=row['booking_ref'], 
                                    renter_name=row['renter_name'], 
                                    vehicle=vehicle_str, 
                                    plate=row['plate'], 
                                    travel_dates=travel_dates, 
                                    amount=row['amount'], 
                                    pickup_loc=row.get('pickup_loc', 'N/A'), 
                                    return_loc=row.get('return_loc', 'N/A')
                                )
                                
                                if row['renter_email']:
                                    subject = f"DriveElite: Payment Confirmed - Official Receipt (#{row['booking_ref']})"
                                    body = f"Hello {row['renter_name']},\n\nYour payment has been successfully verified! Your booking for the {vehicle_str} is now CONFIRMED.\n\nPlease find your Official Booking Receipt attached to this email.\n\nThank you for choosing DriveElite!"
                                    send_pdf_email(row['renter_email'], subject, body, pdf_bytes, f"Receipt_{row['booking_ref']}.pdf")
                                
                                st.success("✅ Payment Confirmed and Receipt emailed to the Renter!")
                                time.sleep(2)
                                st.rerun()
                        
                        if c2.button("❌ REJECT & FREE CAR", key=f"rej_{row['id']}", use_container_width=True):
                            conn.execute("UPDATE bookings SET status = 'CANCELLED' WHERE id = ?", (row['id'],))
                            conn.commit()
                            st.error(f"Booking #{row['booking_ref']} cancelled. The vehicle calendar is now free.")
                            time.sleep(2)
                            st.rerun()

        # --- PREPARE DATA FOR LEDGER (Excluding Pending) ---
        query = """
        SELECT b.id, b.booking_ref, b.pickup_time as Date, b.return_time, u_renter.full_name as Renter, u_owner.full_name as Affiliate,
               b.amount as Total_Paid_By_Renter, b.status as Trip_Status, b.payout_status as Payout_Status,
               b.gateway_fee, v.bank_name, v.account_no
        FROM bookings b
        JOIN vehicles v ON b.vehicle_id = v.id
        JOIN platform_users u_renter ON b.renter_username = u_renter.username
        JOIN platform_users u_owner ON v.owner_username = u_owner.username
        WHERE b.status != 'PENDING' AND b.status != 'CANCELLED' AND b.status != 'VERIFYING'
        ORDER BY b.id DESC
        """
        df = pd.read_sql_query(query, conn)

        # --- SUB-TAB 1: MASTER LEDGER ---
        with f_tabs[1]:
            if df.empty:
                st.info("No completed financial transactions recorded yet.")
            else:
                df['gateway_fee'] = df['gateway_fee'].fillna(0)
                df['pickup_dt'] = pd.to_datetime(df['Date'], errors='coerce')
                df['return_dt'] = pd.to_datetime(df['return_time'], errors='coerce')
                df['Total_Days'] = (df['return_dt'] - df['pickup_dt']).dt.ceil('D').dt.days
                df['Total_Days'] = df['Total_Days'].fillna(1).clip(lower=1)
                
                df['Applied_Markup'] = np.where(df['Total_Days'] >= 4, r_markup, 0.0)

                df['Platform_Gross_Cut'] = df['Total_Paid_By_Renter'] * (1 - (a_share / (1 + df['Applied_Markup'])))
                TAX_RATE_L = 0.01 
                df['Platform_Net_Profit'] = df['Platform_Gross_Cut'] - df['gateway_fee'] - (df['Total_Paid_By_Renter'] * TAX_RATE_L * 0.18)
                df['Affiliate_Gross_Share'] = df['Total_Paid_By_Renter'] - df['Platform_Gross_Cut']
                df['EWT_Deduction'] = df['Affiliate_Gross_Share'] * TAX_RATE_L
                df['Affiliate_Net_Payout'] = df['Affiliate_Gross_Share'] - df['EWT_Deduction']
                df['Ref'] = df.apply(lambda x: f"#{x['booking_ref']}" if pd.notnull(x.get('booking_ref')) else f"DRV-{x['id']:05d}", axis=1)

                st.caption(f"Calculated based on Admin Margins: Renter Fee ({r_markup*100}% - Waived for <4 days) | Owner Share ({a_share*100}%)")
                display_cols = ['Ref', 'Date', 'Total_Days', 'Affiliate', 'Total_Paid_By_Renter', 'gateway_fee', 'EWT_Deduction', 'Affiliate_Net_Payout', 'Platform_Net_Profit', 'Payout_Status']
                styled_ledger = df[display_cols].style.format({
                    'Total_Paid_By_Renter': '{:,.2f}', 'gateway_fee': '{:,.2f}', 'EWT_Deduction': '{:,.2f}', 
                    'Affiliate_Net_Payout': '{:,.2f}', 'Platform_Net_Profit': '{:,.2f}'
                })
                st.dataframe(styled_ledger, use_container_width=True, hide_index=True)

        # --- SUB-TAB 2: PROCESS PAYOUTS ---
        with f_tabs[2]:
            if not df.empty:
                pending_p = df[(df['Trip_Status'] == 'COMPLETED') & (df['Payout_Status'] == 'PENDING')]
                if pending_p.empty: st.info("No pending payouts at this time.")
                for _, p in pending_p.iterrows():
                    with st.expander(f"{p['Ref']} | {p['Affiliate']} | Net: ₱{p['Affiliate_Net_Payout']:,.2f}"):
                        st.write(f"**Final Remittance:** ₱{p['Affiliate_Net_Payout']:,.2f}")
                        if st.button("MARK AS PAID", key=f"p_{p['id']}", type="primary", use_container_width=True):
                            conn.execute("UPDATE bookings SET payout_status = 'PAID' WHERE id = ?", (p['id'],))
                            conn.commit()
                            st.success("Marked as Paid!")
                            time.sleep(1); st.rerun()

        # --- SUB-TAB 3: ISSUE RECEIPTS ---
        with f_tabs[3]:
            if not df.empty:
                st.markdown("#### Manual POS Issuance")
                st.info("Download text receipt for bookkeeping.")
    
    except Exception as e:
        st.error(f"Financial Error: {e}")

# --- TAB 4: FILING CABINET ---
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
            
            if role_filter == "💼 Affiliates (MOA)": filtered_files = [f for f in pdf_files if f.startswith("MOA_")]
            elif role_filter == "🚙 Renters (Agreements)": filtered_files = [f for f in pdf_files if f.startswith("RENTER_")]
            else: filtered_files = pdf_files
            
            if not filtered_files: st.info(f"No documents found matching the filter.")
            else:
                cols = st.columns(4)
                for i, file_name in enumerate(filtered_files):
                    file_path = os.path.join("uploads", file_name)
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
                            btn_col1, btn_col2 = st.columns(2)
                            with btn_col1:
                                with open(file_path, "rb") as pdf_file:
                                    st.download_button(label="⬇️ DL", data=pdf_file.read(), file_name=file_name, mime="application/pdf", key=f"dl_{file_name}", use_container_width=True)
                            with btn_col2:
                                if st.button("📧 Email", key=f"em_{file_name}", use_container_width=True):
                                    if not target_email: st.toast(f"❌ No email found for @{uname}", icon="⚠️")
                                    else:
                                        with st.spinner("Sending..."):
                                            success, msg = send_email(
                                                to_email=target_email, 
                                                subject=f"Contract Copy: {file_name}", 
                                                body="Please find your signed contract attached to this email.", 
                                                attachment_path=file_path, 
                                                attachment_name=file_name
                                            )
                                            if success: st.toast(f"✅ Contract sent to {target_email}", icon="🚀")
                                            else: st.error(f"Failed: {msg}")
        else: st.info("No contracts have been signed yet.")
    else: st.warning("The uploads folder does not exist yet. It will be created when the first user registers.")

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
                    try: conn.execute("ALTER TABLE admin_promos ADD COLUMN target TEXT DEFAULT 'ALL USERS'"); conn.commit()
                    except: pass
                    conn.execute("UPDATE admin_promos SET active = 0")
                    conn.execute("INSERT INTO admin_promos (title, message, target) VALUES (?, ?, ?)", (t, m, target))
                    conn.commit()
                    st.success(f"Live! Broadcast successfully published to {target}.")
                    time.sleep(1); st.rerun()
                    
    with col_cat:
        st.subheader("📈 Category Manager")
        with st.form("add_cat", clear_on_submit=True):
            n = st.text_input("New Category (e.g., Pickup, Luxury)")
            p = st.number_input("Daily Rate (₱)", min_value=500.0, step=100.0, value=2500.0)
            if st.form_submit_button("ADD NEW CATEGORY"):
                if n:
                    try: conn.execute("INSERT INTO vehicle_categories (name, default_price) VALUES (?, ?)", (n.title(), p)); conn.commit()
                    except Exception as e: st.error(f"Error adding category: {e}")

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
    with st.expander("🧨 CLOUD FACTORY RESET (Wipe All Data)"):
        st.warning("WARNING: This will permanently delete the live database and all uploaded files.")
        confirm_text = st.text_input("Type 'DELETE EVERYTHING' to confirm:")
        if st.button("🔥 INITIATE FACTORY RESET", type="primary", use_container_width=True):
            if confirm_text == "DELETE EVERYTHING":
                import glob
                with st.spinner("Disconnecting and Nuking database..."):
                    try: conn.close() 
                    except: pass
                    st.cache_resource.clear() 
                    st.cache_data.clear() 
                    if os.path.exists("driveelite_v2.db"): os.remove("driveelite_v2.db")
                    if os.path.exists("uploads"):
                        for f in glob.glob("uploads/*"):
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

                        email_success, _ = send_email(target_email, f"DriveElite Cancellation Notice: #{booking_to_cancel}", sample_receipt_text)
                        
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
            check = pd.read_sql_query("SELECT id FROM platform_settings WHERE id = 1", conn)
            
            if check.empty:
                conn.execute("INSERT INTO platform_settings (id, payment_mode) VALUES (1, ?)", (new_mode,))
            else:
                conn.execute("UPDATE platform_settings SET payment_mode = ? WHERE id = 1", (new_mode,))
                
            conn.commit()
            st.success(f"✅ System successfully updated to use {new_mode}!")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Database error: {e}")
