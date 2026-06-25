import streamlit as st
import pandas as pd
import datetime
import os
import random 
import time
from PIL import Image
import numpy as np
from fpdf import FPDF
from streamlit_drawable_canvas import st_canvas

# --- Email Imports ---
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

from database_utils import get_connection, send_sms_alert, send_alert_email

# ==========================================
# 1. PAGE CONFIG & LOGO
# ==========================================
st.set_page_config(page_title="DriveElite Affiliate", layout="wide")

try:
    st.sidebar.image("logo.png", use_container_width=True)
except:
    pass

# ==========================================
# 2. THE "CRYSTAL ELITE" CSS ENGINE
# ==========================================
st.markdown("""
<style>
    [data-testid="stSignaturePad"],
    [data-testid="stSignaturePad"] > div > canvas {
        background-color: #FFFFFF !important; 
        border: 2px solid #E2E8F0 !important; 
        border-radius: 12px !important;     
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.03) !important; 
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
        background-color: #1D4ED8 !important;
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
    [data-testid="stAppViewContainer"] > .main { transition: none !important; }
    .element-container, .stMarkdown, .stText { transition: none !important; animation: none !important; opacity: 1 !important; }
    div[data-testid="stStaleElement"] { opacity: 1 !important; transition: none !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. DATABASE CONNECTION & SELF-REPAIR
# ==========================================
conn = get_connection()

def patch_database():
    try: conn.execute("ALTER TABLE vehicles ADD COLUMN or_img TEXT"); conn.commit()
    except: pass
    try: conn.execute("ALTER TABLE vehicles ADD COLUMN cr_img TEXT"); conn.commit()
    except: pass
    try: conn.execute("ALTER TABLE vehicles ADD COLUMN is_with_driver INTEGER DEFAULT 0"); conn.commit()
    except: pass  
    try: conn.execute("ALTER TABLE vehicles ADD COLUMN tire_pressure TEXT DEFAULT 'Standard specs'"); conn.commit()
    except: pass
    try: conn.execute("ALTER TABLE vehicles ADD COLUMN preferred_fuel TEXT DEFAULT 'Standard Unleaded'"); conn.commit()
    except: pass
    try: conn.execute("ALTER TABLE platform_users ADD COLUMN document_url TEXT"); conn.commit()
    except: pass
    try: conn.execute("ALTER TABLE vehicles ADD COLUMN admin_status TEXT DEFAULT 'PENDING'"); conn.commit()
    except: pass
    try: conn.execute("ALTER TABLE bookings ADD COLUMN handover_photos TEXT"); conn.commit()
    except: pass
    try: conn.execute("ALTER TABLE bookings ADD COLUMN handover_sig_renter TEXT"); conn.commit()
    except: pass
    try: conn.execute("ALTER TABLE bookings ADD COLUMN handover_sig_affiliate TEXT"); conn.commit()
    except: pass
    
    # Financial & Dispute Columns
    try: conn.execute("ALTER TABLE bookings ADD COLUMN damage_fee REAL DEFAULT 0.0"); conn.commit()
    except: pass
    try: conn.execute("ALTER TABLE bookings ADD COLUMN late_fee REAL DEFAULT 0.0"); conn.commit()
    except: pass
    try: conn.execute("ALTER TABLE bookings ADD COLUMN fuel_fee REAL DEFAULT 0.0"); conn.commit()
    except: pass
    try: conn.execute("ALTER TABLE bookings ADD COLUMN cleaning_fee REAL DEFAULT 0.0"); conn.commit()
    except: pass
    try: conn.execute("ALTER TABLE bookings ADD COLUMN rfid_fee REAL DEFAULT 0.0"); conn.commit() 
    except: pass
    try: conn.execute("ALTER TABLE bookings ADD COLUMN dispute_status TEXT DEFAULT 'CLEAN'"); conn.commit()
    except: pass
    
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS admin_promos (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, message TEXT, target TEXT DEFAULT 'ALL USERS', active INTEGER DEFAULT 1)")
        conn.commit()
    except: pass
    
    # Chat Table
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_ref TEXT,
                sender_username TEXT,
                receiver_username TEXT,
                message_text TEXT,
                image_path TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    except: pass
    try: conn.execute("ALTER TABLE chat_messages ADD COLUMN image_path TEXT"); conn.commit()
    except: pass
    try: conn.execute("ALTER TABLE chat_messages ADD COLUMN receiver_username TEXT"); conn.commit()
    except: pass

patch_database()

if not os.path.exists("/data/uploads"): os.makedirs("/data/uploads", exist_ok=True)

# --- FETCH DYNAMIC RATES & SETTINGS ---
try:
    settings_df = pd.read_sql_query("SELECT renter_markup_pct, affiliate_share_pct FROM platform_settings WHERE id = 1", conn)
    if not settings_df.empty:
        r_markup = float(settings_df.iloc[0]['renter_markup_pct'])
        a_share_pct = float(settings_df.iloc[0]['affiliate_share_pct'])
    else:
        r_markup, a_share_pct = 0.07, 0.85 
except:
    r_markup, a_share_pct = 0.07, 0.85

try:
    cat_df = pd.read_sql_query("SELECT name, default_price FROM vehicle_categories", conn)
    FIXED_RATES = dict(zip(cat_df['name'], cat_df['default_price']))
except Exception: 
    FIXED_RATES = {"Sedan": 1500.0, "SUV": 2500.0, "Van": 3000.0, "Luxury": 5000.0}

# ==========================================
# 4. UTILITIES & HELPERS
# ==========================================
if "temp_msg_affiliate" not in st.session_state:
    st.session_state.temp_msg_affiliate = ""

def clear_affiliate_chat(b_ref):
    b_ref_str = str(b_ref)
    unique_key = f"chat_{b_ref_str}"
    if unique_key in st.session_state:
        if st.session_state[unique_key].strip():
            st.session_state.temp_msg_affiliate = st.session_state[unique_key]
            st.session_state[f"trigger_send_{b_ref_str}"] = True 
        st.session_state[unique_key] = ""

def save_file(uploaded_file):
    if uploaded_file:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{uploaded_file.name}"
        path = os.path.join("/data/uploads", filename)
        with open(path, "wb") as f: f.write(uploaded_file.getbuffer())
        return path
    return None

def save_chat_image(uploaded_file, booking_ref):
    if uploaded_file:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chat_{booking_ref}_{timestamp}_{uploaded_file.name}"
        path = os.path.join("/data/uploads", filename)
        with open(path, "wb") as f: f.write(uploaded_file.getbuffer())
        return path
    return ""

def save_canvas_image(image_data, prefix):
    if image_data is not None:
        img = Image.fromarray(image_data.astype('uint8'), 'RGBA')
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join("/data/uploads", f"{prefix}_{timestamp}.jpg")
        background.save(filename, "JPEG")
        return filename
    return None

def generate_handover_pdf(ref_no, car_name, renter_name, travel_dates, checklist, r_sig_path, a_sig_path, affiliate_name, tire_pressure="Standard", preferred_fuel="Unleaded"):
    pdf = FPDF()
    pdf.add_page()
    try:
        pdf.image("logo.png", x=80, y=10, w=50)
        pdf.set_y(45) 
    except Exception: 
        pdf.set_y(20)
        
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(0, 10, "DRIVEELITE OFFICIAL HANDOVER RECORD", ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font("Helvetica", '', 11)
    pdf.cell(0, 8, f"Reference No: {ref_no}", ln=True)
    pdf.cell(0, 8, f"Vehicle: {car_name}", ln=True)
    pdf.cell(0, 8, f"Renter Name: {renter_name}", ln=True)
    pdf.cell(0, 8, f"Travel Dates: {travel_dates}", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, "CHECKLIST VERIFICATION:", ln=True)
    pdf.set_font("Helvetica", '', 11)
    pdf.cell(0, 8, f"1. Cash Deposit (Php 5,000): {'YES' if checklist['deposit'] else 'NO'}", ln=True)
    pdf.cell(0, 8, f"2. Fuel Level: {checklist['fuel']}", ln=True)
    pdf.cell(0, 8, f"3. Exterior Inspected: {'YES' if checklist['ext'] else 'NO'}", ln=True)
    pdf.cell(0, 8, f"4. Interior Clean: {'YES' if checklist['int'] else 'NO'}", ln=True)
    pdf.cell(0, 8, f"5. Tools/Spare Tire Verified: {'YES' if checklist['tools'] else 'NO'}", ln=True)
    pdf.ln(5)

    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, "⚠️ IMPORTANT REMINDERS FOR RENTER:", ln=True)
    pdf.set_font("Helvetica", '', 10)
    pdf.multi_cell(0, 6, f"1. Tire Pressure: Please maintain the tire pressure at {tire_pressure} to ensure safety and optimal fuel efficiency.")
    pdf.multi_cell(0, 6, f"2. Preferred Fuel: This vehicle requires {preferred_fuel}. Please ensure the correct fuel type is used to avoid engine damage charges.")
    pdf.multi_cell(0, 6, "3. Speed Limits & Violations: Strictly adhere to all local traffic rules. Any NCAP camera citations, traffic violations, or fines incurred during the rental period will be charged directly to the renter to protect the vehicle's LTO demerit points.")
    pdf.ln(10)
    
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, "DIGITAL SIGNATORIES:", ln=True)
    
    y_sig = pdf.get_y()
    try:
        if r_sig_path and os.path.exists(r_sig_path):
            pdf.image(r_sig_path, x=30, y=y_sig, w=50)
    except Exception:
        pdf.text(30, y_sig + 10, "[Signature Registered]")
        
    try:
        if a_sig_path and os.path.exists(a_sig_path):
            pdf.image(a_sig_path, x=120, y=y_sig, w=50)
    except Exception:
        pdf.text(120, y_sig + 10, "[Signature Registered]")
    
    pdf.set_y(y_sig + 30)
    pdf.set_font("Helvetica", 'U', 11)
    pdf.cell(90, 8, renter_name, align='C')
    pdf.cell(90, 8, affiliate_name, align='C', ln=True)
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(90, 5, "Renter", align='C')
    pdf.cell(90, 5, "Affiliate/Host", align='C', ln=True)
    
    return pdf.output(dest="S").encode("utf-8")

def generate_return_receipt(booking_ref, renter, vehicle, plate, fuel, clean, damage, late, ot_fee, rfid_fee, total_deduct, refund, sig_ret, sig_reta, is_with_driver=False, driver_name=""):
    pdf = FPDF()
    pdf.add_page()
    try:
        pdf.image("logo.png", x=80, y=10, w=50)
        pdf.set_y(45) 
    except Exception: 
        pdf.set_y(20)
        
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, "DRIVEELITE RETURN & SETTLEMENT RECEIPT", ln=True, align='C')
    pdf.set_font("Helvetica", '', 12)
    pdf.cell(0, 10, f"Ref: {booking_ref} | Date: {datetime.date.today()}", ln=True)
    pdf.cell(0, 10, f"Vehicle: {vehicle} ({plate}) | Renter: {renter}", ln=True)
    pdf.ln(10); pdf.set_font("Helvetica", 'B', 12); pdf.cell(0, 10, "SECURITY DEPOSIT DEDUCTIONS:", ln=True)
    pdf.set_font("Helvetica", '', 11)
    pdf.cell(0, 8, f"Fuel Replacement: Php {fuel:,.2f}", ln=True)
    pdf.cell(0, 8, f"Cleaning Penalty: Php {clean:,.2f}", ln=True)
    pdf.cell(0, 8, f"Damage Penalty: Php {damage:,.2f}", ln=True)
    pdf.cell(0, 8, f"Net RFID & Toll Deductions: Php {rfid_fee:,.2f}", ln=True)
    pdf.cell(0, 8, f"Late Penalty: Php {late:,.2f}", ln=True)
    if is_with_driver: pdf.cell(0, 8, f"Driver OT Fee: Php {ot_fee:,.2f}", ln=True)
    pdf.ln(5); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(5)
    pdf.set_font("Helvetica", '', 12)
    pdf.cell(0, 8, f"Total Deductions: Php {total_deduct:,.2f}", ln=True)
    pdf.cell(0, 8, f"Less Initial Deposit: (Php 5,000.00)", ln=True)
    pdf.ln(2) 
    pdf.set_font("Helvetica", 'B', 12)
    
    if total_deduct > 5000.0:
        amount_payable = total_deduct - 5000.0
        pdf.cell(0, 10, f"NET PAYABLE TO AFFILIATE: Php {amount_payable:,.2f}", ln=True)
    else:
        pdf.cell(0, 10, f"NET REFUND TO RENTER: Php {refund:,.2f}", ln=True)
        
    current_y = pdf.get_y() + 15
    
    try:
        if sig_ret is not None:
            r_path = f"/data/uploads/ret_r_{booking_ref}.jpg"
            Image.fromarray(sig_ret.astype('uint8'), 'RGBA').convert('RGB').save(r_path, "JPEG")
            pdf.image(r_path, x=20, y=current_y, w=50)
    except Exception: 
        pass
        
    try:
        if sig_reta is not None:
            a_path = f"/data/uploads/ret_a_{booking_ref}.jpg"
            Image.fromarray(sig_reta.astype('uint8'), 'RGBA').convert('RGB').save(a_path, "JPEG")
            pdf.image(a_path, x=120, y=current_y, w=50)
    except Exception: 
        pass
        
    pdf.set_xy(20, current_y + 40); pdf.cell(50, 5, "Renter Final Sign-off", align='C')
    pdf.set_xy(120, current_y + 40); pdf.cell(50, 5, "Affiliate Final Sign-off", align='C')
    pdf.ln(20); pdf.set_font("Helvetica", 'I', 9); pdf.cell(0, 5, "Legally generated by DriveElite Platform", align='C')
    
    return pdf.output(dest="S").encode("utf-8")

def send_pdf_email(to_email, subject, body, pdf_bytes, filename):
    sender_email = 'contact@driveelite.ph'
    sender_password = os.environ.get("EMAIL_PASSWORD")
    
    if not sender_password: 
        return False
        
    try:
        msg = MIMEMultipart()
        msg['From'] = f"DriveElite Admin <{sender_email}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(pdf_bytes)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {filename}")
        msg.attach(part)
        
        with smtplib.SMTP_SSL('mail.driveelite.ph', 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return True
    except Exception as e: 
        print(f"PDF Email Error: {e}")
        return False

# ==========================================
# 5. LOGIN FLOW
# ==========================================
if not st.session_state.get('logged_in') or st.session_state.get('role') != 'AFFILIATE':
    st.markdown("<h2 style='text-align: center;'>💼 AFFILIATE LOGIN</h2>", unsafe_allow_html=True)
    with st.form("login", clear_on_submit=True):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("LOGIN", use_container_width=True):
            user = pd.read_sql_query("SELECT * FROM platform_users WHERE username=? AND password=? AND role='AFFILIATE'", conn, params=(u, p))
            if not user.empty:
                if user.iloc[0]['admin_status'] == 'APPROVED':
                    st.session_state.logged_in, st.session_state.username, st.session_state.role = True, u, 'AFFILIATE'
                    st.rerun()
                else:
                    st.warning("⏳ Account pending Admin approval.")
            else:
                st.error("❌ Invalid credentials.")
    st.stop()

aff_info = pd.read_sql_query("SELECT full_name FROM platform_users WHERE username=?", conn, params=(st.session_state.username,))
affiliate_full_name = aff_info.iloc[0]['full_name'] if not aff_info.empty else st.session_state.username

# --- HEADER ---
st.markdown("<h1 style='text-align: center;'>💼 AFFILIATE COMMAND CENTER</h1>", unsafe_allow_html=True)
top_col1, top_col2 = st.columns([5, 1])
with top_col2:
    if st.button("🔒 LOGOUT", use_container_width=True):
        st.session_state.clear()
        st.rerun()
st.divider()

# ==========================================
# 📢 STATIC BROADCAST BANNER
# ==========================================
try:
    promo_df = pd.read_sql_query("SELECT title, message FROM admin_promos WHERE active = 1 AND target IN ('AFFILIATE', 'ALL USERS') LIMIT 1", conn)
    
    if not promo_df.empty:
        title = promo_df.iloc[0]['title']
        msg = promo_df.iloc[0]['message']
        
        st.markdown(f"""
            <style>
            .broadcast-box {{ 
                padding: 25px 20px; 
                background-color: #2563EB; 
                color: white; 
                border-radius: 12px; 
                margin-bottom: 25px; 
                text-align: center; 
                font-size: 22px; 
                display: flex; 
                flex-direction: row;
                justify-content: center;
                align-items: center;
                flex-wrap: wrap; 
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.15); 
            }}
            .broadcast-title {{
                font-weight: 900;
                margin-right: 12px;
                letter-spacing: 0.5px;
            }}
            </style>
            <div class="broadcast-box">
                <span class="broadcast-title">📢 {title}:</span> 
                <span>{msg}</span>
            </div>
        """, unsafe_allow_html=True)
except Exception: pass 

# ==========================================
# 6. TABS
# ==========================================
tabs = st.tabs(["BOOKINGS & HANDOVER", "MY ASSETS", "ADD ASSET", "ADD DRIVER", "REVIEWS"])

# --- TAB 0: BOOKINGS & HANDOVER ---
with tabs[0]: 
    st.header("📦 Active Bookings & Handovers")
    st.write("Manage your upcoming deliveries, chat with renters, and log your handovers.")
    
    query = """
        SELECT b.*, v.make, v.model, v.plate, r.full_name as renter_name, r.contact_number as renter_contact, r.email as renter_email
        FROM bookings b
        JOIN vehicles v ON b.vehicle_id = v.id
        JOIN platform_users r ON b.renter_username = r.username
        WHERE v.owner_username = ? AND b.status NOT IN ('COMPLETED', 'CANCELLED')
        ORDER BY b.pickup_time ASC
    """
    
    try:
        my_bookings = pd.read_sql_query(query, conn, params=(st.session_state.username,))
        
        if my_bookings.empty:
            st.info("You have no active bookings right now. Ensure your vehicles are marked 'AVAILABLE'.")
        else:
            for _, b in my_bookings.iterrows():
                b_ref_display = f"#{b['booking_ref']}" if pd.notnull(b.get('booking_ref')) else f"DRV-{b['id']:05d}"
                vehicle_info = f"{str(b['pickup_time'])[:16]} | {b['make']} {b['model']} ({b['plate']})"
                
                if b['status'] in ['PENDING', 'VERIFYING']:
                    with st.container(border=True):
                        c_icon, c_info = st.columns([1, 15])
                        with c_icon: st.markdown("<h2>⏳</h2>", unsafe_allow_html=True)
                        with c_info:
                            st.write(f"**Ref: {b_ref_display}** | {vehicle_info}")
                            
                            if b['status'] == 'PENDING':
                                st.warning("🔒 **AWAITING RENTER PAYMENT.** Renter reserved the dates but hasn't uploaded a receipt yet.")
                            elif b['status'] == 'VERIFYING':
                                st.info("🔒 **VERIFYING RECEIPT.** Renter uploaded proof of payment. Waiting for Admin to confirm the funds.")

                else:
                    if b['status'] == 'CONFIRMED':
                        exp_title = f"✅ [CONFIRMED] Ref: {b_ref_display} | {vehicle_info}"
                    else:
                        exp_title = f"🚙 [ONGOING] Ref: {b_ref_display} | {vehicle_info}"
                        
                    with st.expander(exp_title):
                        if b['status'] == 'CONFIRMED':
                            st.success("✅ **PAYMENT VERIFIED.** You may proceed with the handover.")
                    
                        with st.container(border=True):
                            p_dt = pd.to_datetime(b['pickup_time'])
                            r_dt = pd.to_datetime(b['return_time'])
                            days_count = max(1, (r_dt - p_dt).days) 
                            
                            active_markup = r_markup if days_count >= 7 else 0.0
                            base_est = b['amount'] / (1 + active_markup)
                            affiliate_gross = base_est * a_share_pct
                            ewt_val = affiliate_gross * 0.01
                            net_payout = affiliate_gross - ewt_val
                            
                            c_earn1, c_earn2, c_earn3 = st.columns(3)
                            c_earn1.metric("Total Rental", f"Php{b['amount']:,.2f}")
                            c_earn2.metric("Your Gross", f"Php{affiliate_gross:,.2f}")
                            c_earn3.metric("Net Payout", f"Php{net_payout:,.2f}")
                            
                            if active_markup == 0:
                                st.info("💡 **7-Day Rule:** Platform fee was waived for this short trip.")
                        st.divider()
                        
                        col1, col2 = st.columns(2)
                        
                        st.markdown("#### 💬 Message the Renter")
                        b_ref_str = str(b['booking_ref'])
                        
                        chat_win = st.container(height=450, border=True)
                        with chat_win:
                            try:
                                msgs = pd.read_sql_query("SELECT * FROM chat_messages WHERE booking_ref = ? ORDER BY timestamp ASC", conn, params=(b_ref_str,))
                                
                                if msgs.empty:
                                    st.info("👋 Chat is empty. Say hello to start coordinating your trip!")
                                else:
                                    for _, m in msgs.iterrows():
                                        if m['sender_username'] == st.session_state.username:
                                            st.markdown(f"""
                                            <div style="display: flex; justify-content: flex-end; margin-bottom: 5px;">
                                                <div style="background-color: #2c8c80; color: white; padding: 12px 16px; border-radius: 20px 20px 4px 20px; max-width: 75%; box-shadow: 1px 2px 5px rgba(0,0,0,0.2);">
                                                    {m['message_text']}
                                                </div>
                                            </div>
                                            """, unsafe_allow_html=True)
                                            if m.get('image_path') and os.path.exists(m['image_path']): 
                                                c_space, c_img = st.columns([2, 1])
                                                with c_img: st.image(m['image_path'], use_container_width=True)
                                        else:
                                            st.markdown(f"""
                                            <div style="display: flex; justify-content: flex-start; margin-bottom: 5px;">
                                                <div style="background-color: #2b2b2b; color: white; padding: 12px 16px; border-radius: 20px 20px 20px 4px; max-width: 75%; border: 1px solid #444; box-shadow: 1px 2px 5px rgba(0,0,0,0.2);">
                                                    <div class="sender-tag">@{m['sender_username']}</div>
                                                    {m['message_text']}
                                                </div>
                                            </div>
                                            """, unsafe_allow_html=True)
                                            if m.get('image_path') and os.path.exists(m['image_path']): 
                                                c_img, c_space = st.columns([1, 2])
                                                with c_img: st.image(m['image_path'], use_container_width=True)

                                st.markdown(f'<div id="chat_anchor_{b_ref_str}" style="height: 1px; margin-top: 10px;"></div>', unsafe_allow_html=True)
                                scroll_js = f"""
                                <script>
                                    setTimeout(function() {{
                                        var anchor = window.parent.document.getElementById('chat_anchor_{b_ref_str}');
                                        if (anchor) {{
                                            var parent = anchor.parentElement;
                                            while (parent) {{
                                                var style = window.parent.getComputedStyle(parent);
                                                if (style.overflowY === 'auto' || style.overflowY === 'scroll') {{
                                                    parent.scrollTop = parent.scrollHeight;
                                                    break;
                                                }}
                                                parent = parent.parentElement;
                                            }}
                                        }}
                                    }}, 150);
                                </script>
                                """
                                st.components.v1.html(scroll_js, height=0)
                            except: 
                                st.error("Could not load chat history.")

                        c_img, c_msg = st.columns([1, 4])
                        with c_img: 
                            a_img = st.file_uploader("📷", type=['jpg','png','jpeg'], accept_multiple_files=True, key=f"a_img_{b_ref_str}", label_visibility="collapsed")
                        with c_msg: 
                            st.text_input("Reply...", key=f"chat_{b_ref_str}", on_change=clear_affiliate_chat, args=(b_ref_str,), placeholder="Type message and press Enter...")

                        btn_clicked = st.button("Send", key=f"a_btn_{b_ref_str}", use_container_width=True)
                        enter_pressed = st.session_state.get(f"trigger_send_{b_ref_str}", False)

                        if btn_clicked or enter_pressed:
                            box_val = st.session_state.get(f"chat_{b_ref_str}", "")
                            final_text = st.session_state.temp_msg_affiliate if enter_pressed else box_val
                            
                            has_text = bool(final_text.strip())
                            has_imgs = bool(a_img and len(a_img) > 0)
                            
                            if has_text or has_imgs:
                                success = False
                                error_msg = ""
                                for attempt in range(3):
                                    try:
                                        if has_imgs:
                                            for idx, img_file in enumerate(a_img):
                                                path = save_chat_image(img_file, b_ref_str)
                                                text_to_save = final_text if idx == 0 else ""
                                                if idx == 0 and not has_text: text_to_save = "📸 Sent a photo."
                                                conn.execute("INSERT INTO chat_messages (booking_ref, sender_username, receiver_username, message_text, image_path) VALUES (?, ?, ?, ?, ?)", 
                                                            (b_ref_str, st.session_state.username, b['renter_username'], text_to_save, path))
                                        else:
                                            conn.execute("INSERT INTO chat_messages (booking_ref, sender_username, receiver_username, message_text, image_path) VALUES (?, ?, ?, ?, ?)", 
                                                        (b_ref_str, st.session_state.username, b['renter_username'], final_text, ""))
                                        
                                        conn.commit()
                                        success = True
                                        st.session_state.temp_msg_affiliate = ""
                                        st.session_state[f"chat_{b_ref_str}"] = ""
                                        st.session_state[f"trigger_send_{b_ref_str}"] = False
                                        break
                                    except Exception as e:
                                        error_msg = str(e)
                                        if "locked" in error_msg.lower(): time.sleep(0.5)
                                        else: break
                                if success: st.rerun()
                                else: st.warning(f" **DATABASE ERROR:** {error_msg}")
                                    
                        st.divider()

                        if b['status'] == 'CONFIRMED':
                            st.info(" **ACTION REQUIRED:** Complete the Digital Handover with the Renter present.")
                            with st.expander("📋 Official Handover & Photo Evidence", expanded=True):
                                st.write("### 1. Vehicle Checklist")
                                c1, c2 = st.columns(2)
                                
                                with c1:
                                    c_fuel = st.selectbox("Current Fuel Level", ["Full", "3/4", "1/2", "1/4", "Empty"], key=f"fuel_{b['id']}")
                                    c_deposit = st.checkbox("Php5,000 Cash Deposit Received", value=False, key=f"dep_{b['id']}")
                                    c_aircon = st.checkbox("❄️ Aircon Confirmed (Cold & Working)", value=True, key=f"aircon_{b['id']}")
                                
                                with c2:
                                    c_ext = st.checkbox("Exterior inspected (No new damage)", value=True, key=f"ext_{b['id']}")
                                    c_int = st.checkbox("Interior is clean/odor-free", value=True, key=f"int_{b['id']}")
                                    c_tools = st.checkbox("Tools/Spare tire verified", value=True, key=f"tools_{b['id']}")
                                    c_rfid = st.checkbox("💳 RFID Handover & Reminded to Load", value=True, key=f"rfid_{b['id']}")
                                
                                st.divider()
                                st.write("### 📸 2. Photo Evidence (10 Photos Required)")
                                st.caption("Upload: Front, Back, Left, Right, 4 Tires, Odometer, and Fuel Gauge.")
                                h_photos = st.file_uploader("Dump 10 Photos here", type=['jpg','png','jpeg'], accept_multiple_files=True, key=f"photos_{b['id']}")
                                if h_photos and len(h_photos) < 10:
                                    st.warning(f"⚠️ Uploaded {len(h_photos)}/10 photos. Please upload all 10 to proceed.")

                                st.divider()
                                st.write("### 🖋️ 3. Dual Digital Signatures")
                                col_sig1, col_sig2 = st.columns(2)
                                with col_sig1:
                                    if f"clr_sr_{b['id']}" not in st.session_state: st.session_state[f"clr_sr_{b['id']}"] = 0
                                    s_r = st_canvas(stroke_width=2, stroke_color="#000", background_color="#ffffff", height=150, width=300, display_toolbar=False, key=f"sr_{b['id']}_{st.session_state[f'clr_sr_{b['id']}']}")
                                    if st.button("Clear Renter Pad", key=f"btn_sr_{b['id']}", use_container_width=True): 
                                        st.session_state[f"clr_sr_{b['id']}"] += 1
                                        st.rerun()
                                    st.markdown(f"<div style='text-align: center; margin-top: -10px;'><u><b>{b['renter_name']}</b></u><br>Renter</div>", unsafe_allow_html=True)
                                with col_sig2:
                                    if f"clr_sa_{b['id']}" not in st.session_state: st.session_state[f"clr_sa_{b['id']}"] = 0
                                    s_a = st_canvas(stroke_width=2, stroke_color="#000", background_color="#ffffff", height=150, width=300, display_toolbar=False, key=f"sa_{b['id']}_{st.session_state[f'clr_sa_{b['id']}']}")
                                    if st.button("Clear Host Pad", key=f"btn_sa_{b['id']}", use_container_width=True): 
                                        st.session_state[f"clr_sa_{b['id']}"] += 1
                                        st.rerun()
                                    st.markdown(f"<div style='text-align: center; margin-top: -10px;'><u><b>{affiliate_full_name}</b></u><br>Affiliate/Host</div>", unsafe_allow_html=True)
                                
                                if st.button("🚀 FINAL LOG HANDOVER & DISPATCH", key=f"dispatch_{b['id']}", type="primary", use_container_width=True):
                                    has_sr = s_r.image_data is not None and len(s_r.json_data.get("objects", [])) > 0
                                    has_sa = s_a.image_data is not None and len(s_a.json_data.get("objects", [])) > 0
                                    
                                    if not h_photos or len(h_photos) < 10:
                                        st.error("❌ DISPATCH BLOCKED: You must upload at least 10 photos of the vehicle condition.")
                                    elif not c_deposit:
                                        st.error("❌ DISPATCH BLOCKED: You must verify receipt of the 5,000 Php Cash Deposit.")
                                    elif not (has_sr and has_sa):
                                        st.error("❌ DISPATCH BLOCKED: Both parties must sign on the digital pads.")
                                    else:
                                        r_sig_path = save_canvas_image(s_r.image_data, f"sig_r_{b['booking_ref']}")
                                        a_sig_path = save_canvas_image(s_a.image_data, f"sig_a_{b['booking_ref']}")
                                        
                                        chk_data = {'fuel': c_fuel, 'ext': c_ext, 'int': c_int, 'tools': c_tools, 'deposit': c_deposit}
                                        travel_dates = f"{str(b.get('pickup_time'))[:10]} to {str(b.get('return_time'))[:10]}"
                                        
                                        with st.spinner("Building Handover Record..."):
                                            pdf_bytes = generate_handover_pdf(b['booking_ref'], f"{b['make']} {b['model']} ({b['plate']})", b['renter_name'], travel_dates, chk_data, r_sig_path, a_sig_path, affiliate_full_name)
                                            
                                            pdf_filepath = f"/data/uploads/Handover_{b['booking_ref']}.pdf"
                                            with open(pdf_filepath, "wb") as f: f.write(pdf_bytes)
                                            
                                            photo_paths = [save_file(img) for img in h_photos]
                                            photo_string = ",".join(filter(None, photo_paths))
                                            
                                            conn.execute("""
                                                UPDATE bookings 
                                                SET status = 'ONGOING', handover_photos = ?, handover_sig_renter = ?, handover_sig_affiliate = ? 
                                                WHERE id = ?
                                            """, (photo_string, r_sig_path, a_sig_path, b['id']))
                                            conn.commit()
                                            
                                            if b['renter_email']:
                                                success = send_pdf_email(b['renter_email'], f"DriveElite: Digital Handover Record (#{b['booking_ref']})", "Attached is the official digital handover record with checklists and signatures. Please drive safely!", pdf_bytes, f"Handover_{b['booking_ref']}.pdf")
                                                if success: st.toast("📧 Secure PDF Handover record sent to renter!", icon="✅")
                                                else: st.error("⚠️ Email failed. PDF saved locally.")
                                            
                                            st.success("✅ Handover Secured! PDF Generated and Trip started.")
                                            time.sleep(3)
                                            st.rerun()

                        elif b['status'] == 'ONGOING':
                            st.warning("⏱️ This trip is currently active. Coordinate the return below.")
                            
                            pdf_filepath = f"/data/uploads/Handover_{b['booking_ref']}.pdf"
                            if os.path.exists(pdf_filepath):
                                with open(pdf_filepath, "rb") as pdf_file:
                                    st.download_button("📄 DOWNLOAD SIGNED HANDOVER PDF", data=pdf_file.read(), file_name=f"Handover_{b['booking_ref']}.pdf", mime="application/pdf", type="secondary", use_container_width=True)
                            
                            if b.get('handover_photos'):
                                with st.expander("📸 VIEW ORIGINAL HANDOVER PHOTOS (BEFORE TRIP)", expanded=False):
                                    st.write("Compare these original photos to the current condition of the vehicle.")
                                    h_paths = str(b['handover_photos']).split(",")
                                    h_cols = st.columns(3) 
                                    for idx, img_path in enumerate(h_paths):
                                        clean_path = img_path.strip()
                                        if clean_path and os.path.exists(clean_path):
                                            with h_cols[idx % 3]:
                                                st.image(clean_path, use_container_width=True, caption=f"Original Photo {idx+1}")
                            st.divider()

                            st.write("#### 🛠️ Final Settlement Details")
                            settlement_type = st.radio("Trip Type:", ["Self-Drive", "With Driver"], key=f"type_{b['id']}", horizontal=True)
                            
                            with st.form(f"settlement_form_{b['id']}"):
                                c1, c2 = st.columns(2)
                                
                                with c1:
                                    st.write("##### Renter Expenses")
                                    l_hrs = st.number_input("Vehicle Late Return (Hours)", min_value=0, step=1, key=f"l_hrs_{b['id']}")
                                    st.caption("Standard penalty for the car (Php 300/hr)")
                                    late_fee = l_hrs * 300.0
                                    
                                    fuel_cost = st.number_input("Refuel Receipt (Php)", min_value=0.0, step=100.0, key=f"f_cost_{b['id']}")
                                    cleaning_fee = st.number_input("Cleaning/Smoking Fine (Php)", value=0.0, step=500.0, key=f"c_fine_{b['id']}")
                                    
                                    st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
                                    st.write("##### 🛣️ Tolls & Travel Expenses")
                                    rfid_usage = st.number_input("Tolls Consumed (Php)", min_value=0.0, step=50.0, value=0.0, key=f"r_use_{b['id']}")
                                    rfid_replenished = st.number_input("Tolls Loaded (Php)", min_value=0.0, step=50.0, value=0.0, key=f"r_load_{b['id']}")
                                    rfid_penalty = st.checkbox("Apply 100 Php fine (Failure to load)", key=f"r_pen_{b['id']}")

                                with c2:
                                    st.write("##### Driver/Owner Liabilities")
                                    damage_fee = 0.0
                                    img_damage = None
                                    
                                    if settlement_type == "Self-Drive":
                                        d_ok = st.checkbox("No Damage Found", value=True, key=f"d_{b['id']}")
                                        if not d_ok:
                                            img_damage = st.file_uploader("Upload Damage Photos", type=['jpg','png','jpeg'], accept_multiple_files=True, key=f"p_dam_{b['id']}")
                                            if img_damage:
                                                d_cols = st.columns(3)
                                                for idx, dmg_file in enumerate(img_damage):
                                                    with d_cols[idx % 3]:
                                                        st.image(dmg_file, use_container_width=True)
                                            damage_fee = st.number_input("Estimated Damage Amount (Php)", step=500.0, key=f"d_est_{b['id']}")
                                    else:
                                        st.info("🛡️ **With Driver Mode:** The Driver is responsible for the vehicle. Damage liability is waived for the Renter.")
                                    
                                    driver_extras = 0.0
                                    if settlement_type == "With Driver":
                                        st.write("--- 🧑‍✈️ Driver Allowances & Extras ---")
                                        driver_ot_hrs = st.number_input("Driver Overtime (Hours)", min_value=0, step=1, key=f"ot_hrs_{b['id']}")
                                        st.caption("Extra pay for the driver's labor (Php 200/hr)")
                                        ot_fee = driver_ot_hrs * 200.0
                                        
                                        p_fee = st.number_input("Parking Fees (Php)", min_value=0.0, step=20.0, key=f"park_{b['id']}")
                                        n_diff = st.number_input("Night Differential (Php)", min_value=0.0, step=100.0, key=f"ndiff_{b['id']}")
                                        m_allow = st.number_input("Meal Allowance (Php)", min_value=0.0, step=50.0, key=f"meal_{b['id']}")
                                        l_allow = st.number_input("Lodging Allowance (Php)", min_value=0.0, step=100.0, key=f"lodge_{b['id']}")
                                        
                                        driver_extras = ot_fee + p_fee + n_diff + m_allow + l_allow

                                # Master Calculation
                                fine_amount = 100.0 if rfid_penalty else 0.0
                                rfid_fee = max(0.0, rfid_usage - rfid_replenished) + fine_amount
                                
                                total_deduct = late_fee + fuel_cost + cleaning_fee + damage_fee + rfid_fee + driver_extras
                                refund_amount = max(0, 5000.0 - total_deduct)
                                
                                st.markdown(f"""
                                <div style='background-color: rgba(128, 128, 128, 0.1); padding: 15px; border-radius: 8px; border: 1px solid rgba(128, 128, 128, 0.3); margin-bottom: 10px; margin-top: 15px;'>
                                    <b style='color: #e74c3c;'>Total Deductions:</b> Php{total_deduct:,.2f}<br>
                                    <b style='color: #27ae60;'>Deposit Held:</b> Php5,000.00
                                </div>
                                """, unsafe_allow_html=True)
                                
                                if total_deduct > 5000.0: 
                                    st.error(f" RENTER OWES EXTRA: Php{(total_deduct - 5000.0):,.2f}. (Collect directly from Renter).")
                                else: 
                                    st.success(f"✅ REFUND CASH TO RENTER NOW: Php{refund_amount:,.2f}")

                                st.write("#### 🖊️ Final Sign-off")
                                c_sig1, c_sig2 = st.columns(2)
                                
                                with c_sig1:
                                    if f"clr_sret_{b['id']}" not in st.session_state: st.session_state[f"clr_sret_{b['id']}"] = 0
                                    s_ret = st_canvas(stroke_width=2, stroke_color="#000", background_color="#ffffff", height=150, width=180, display_toolbar=False, key=f"sret_{b['id']}_{st.session_state[f'clr_sret_{b['id']}']}")
                                    if st.form_submit_button("Clear Renter Pad", use_container_width=True): 
                                        st.session_state[f"clr_sret_{b['id']}"] += 1
                                        st.rerun()
                                    st.markdown(f"<div style='text-align: center; margin-top: -10px;'><u><b>{b['renter_name']}</b></u><br>Renter</div>", unsafe_allow_html=True)
                                    
                                with c_sig2:
                                    if f"clr_sreta_{b['id']}" not in st.session_state: st.session_state[f"clr_sreta_{b['id']}"] = 0
                                    s_reta = st_canvas(stroke_width=2, stroke_color="#000", background_color="#ffffff", height=150, width=180, display_toolbar=False, key=f"sreta_{b['id']}_{st.session_state[f'clr_sreta_{b['id']}']}")
                                    if st.form_submit_button("Clear Host Pad", use_container_width=True): 
                                        st.session_state[f"clr_sreta_{b['id']}"] += 1
                                        st.rerun()
                                    st.markdown(f"<div style='text-align: center; margin-top: -10px;'><u><b>{affiliate_full_name}</b></u><br>Affiliate/Host</div>", unsafe_allow_html=True)

                                st.write("")
                                submit = st.form_submit_button("✅ COMPLETE JOURNEY & CLOSE OUT", type="primary", use_container_width=True)

                            # --- FORM SUBMISSION LOGIC ---
                            if submit:
                                has_sig = s_ret.image_data is not None and len(s_ret.json_data.get("objects", [])) > 0
                                has_sig_a = s_reta.image_data is not None and len(s_reta.json_data.get("objects", [])) > 0
                                
                                if not has_sig or not has_sig_a:
                                    st.error("Both Renter and Affiliate signatures are required to close the trip.")
                                elif settlement_type == "Self-Drive" and not d_ok and not img_damage:
                                    st.error("Upload damage photos to proceed.")
                                else:
                                    d_img_path = ",".join([save_file(img) for img in img_damage]) if img_damage else None
                                    
                                    with st.spinner("Generating Settlement PDF and closing trip..."):
                                        try:
                                            pdf_bytes = generate_return_receipt(
                                                b['booking_ref'], b['renter_name'], f"{b['make']} {b['model']}", b['plate'], 
                                                float(fuel_cost), float(cleaning_fee), float(damage_fee), float(late_fee), float(driver_extras), float(rfid_fee), 
                                                float(total_deduct), float(refund_amount), s_ret.image_data, s_reta.image_data
                                            )
                                            
                                            pdf_filepath = f"/data/uploads/Settlement_{b['booking_ref']}.pdf"
                                            with open(pdf_filepath, "wb") as f: f.write(pdf_bytes)
                                            
                                            if b.get('renter_email'):
                                                subject = f"DriveElite: Return Settlement Receipt (#{b['booking_ref']})"
                                                body = f"Thank you for using DriveElite!\n\nAttached is your official settlement receipt and deposit breakdown.\n\nTotal Deductions: Php{total_deduct:,.2f}\nRefund Amount: Php{refund_amount:,.2f}"
                                                send_pdf_email(b['renter_email'], subject, body, pdf_bytes, f"Settlement_{b['booking_ref']}.pdf")
                                            
                                            conn.execute("""
                                                UPDATE bookings 
                                                SET status = 'COMPLETED', payout_status = 'PENDING',
                                                    damage_img = ?, rfid_fee = ?, damage_fee = ?, late_fee = ?, fuel_fee = ?, cleaning_fee = ?, dispute_status = 'CLEAN' 
                                                WHERE id = ?
                                            """, (d_img_path, float(rfid_fee + driver_extras), float(damage_fee), float(late_fee), float(fuel_cost), float(cleaning_fee), b['id']))
                                            
                                            conn.execute("UPDATE vehicles SET booking_status = 'AVAILABLE' WHERE id = ?", (b['vehicle_id'],))
                                            conn.commit()
                                            
                                            st.success("✅ Trip closed & Settlement Receipt emailed to Renter!")
                                            time.sleep(3)
                                            st.rerun()
                                            
                                        except Exception as e:
                                            st.error(f"Error finalizing settlement: {e}")
    except Exception as e:
        st.error(f"System Error loading bookings: {e}")

# --- TAB 1: MY ASSETS ---
with tabs[1]:
    st.markdown("<h3 style='text-align: center;'>MY FLEET CONTROLS</h3>", unsafe_allow_html=True)
    fleet = pd.read_sql_query("SELECT id, make, model, plate, booking_status, admin_status, ref_no FROM vehicles WHERE owner_username = ?", conn, params=(st.session_state.username,))
    if fleet.empty: st.info("You haven't added any vehicles yet.")
    for _, c in fleet.iterrows():
        v_ref = c.get('ref_no') if pd.notnull(c.get('ref_no')) else 'PENDING'
        with st.expander(f" #{v_ref} | {c['make']} {c['model']} ({c['plate']}) - Status: {c['booking_status']} (Admin: {c['admin_status']})"):
            if c['admin_status'] == 'APPROVED':
                if c['booking_status'] == 'AVAILABLE' and st.button("Hide Vehicle", key=f"h_{c['id']}"):
                    conn.execute("UPDATE vehicles SET booking_status = 'UNAVAILABLE' WHERE id = ?", (c['id'],))
                    conn.commit(); st.rerun()
                elif c['booking_status'] == 'UNAVAILABLE' and st.button("Repost Vehicle", key=f"s_{c['id']}"):
                    conn.execute("UPDATE vehicles SET booking_status = 'AVAILABLE' WHERE id = ?", (c['id'],))
                    conn.commit(); st.rerun()

# --- TAB 2: ADD ASSET ---
with tabs[2]:
    st.markdown("<h3 style='text-align: center;'>REGISTER A VEHICLE</h3>", unsafe_allow_html=True)
    
    with st.form("add_v"):
        # ROW 1: Category, Make, Model
        c1, c2, c3 = st.columns(3)
        cat = c1.selectbox("CATEGORY", list(FIXED_RATES.keys()))
        ma = c2.text_input("MAKE")
        mo = c3.text_input("MODEL")
        
        # ROW 2: Year, Plate, Tire Pressure, Preferred Fuel
        c4, c5, c6, c7 = st.columns(4)
        ye = c4.text_input("YEAR")
        pl = c5.text_input("PLATE")
        tp = c6.text_input("TIRE PRESSURE", placeholder="e.g., 32 PSI")
        pf = c7.selectbox("PREF. FUEL", ["Premium Unleaded", "Regular Unleaded", "Diesel", "EV"])
        
        # ROW 3: Banking Info
        c8, c9 = st.columns(2)
        bn = c8.text_input("PAYOUT BANK")
        an = c9.text_input("ACCOUNT NUMBER")
        
        # ROW 4: Uploads
        vi = st.file_uploader("Vehicle Photo", type=['jpg','png'])
        or_cr_files = st.file_uploader("Upload OR & CR (Drop 2 files)", type=['jpg','png','pdf'], accept_multiple_files=True)
        ins = st.file_uploader("Insurance Policy", type=['pdf','jpg','png'])
        
        # Service Type Toggle
        st.divider()
        service_type = st.radio("Service Type", ["Self-Drive Only", "With Driver Included"], horizontal=True)
        is_with_driver = 1 if service_type == "With Driver Included" else 0
        
        if st.form_submit_button("SUBMIT FOR APPROVAL", type="primary"):
            if ma and mo and pl and bn and an and vi and len(or_cr_files) >= 1 and ins:
                new_ref_no = str(random.randint(100000, 999999))
                
                car_img_path = save_file(vi)
                or_path = save_file(or_cr_files[0]) if len(or_cr_files) > 0 else ""
                cr_path = save_file(or_cr_files[1]) if len(or_cr_files) > 1 else or_path
                ins_path = save_file(ins)
                
                conn.execute("""
                    INSERT INTO vehicles (
                        owner_username, make, model, year, plate, bank_name, account_no, 
                        vehicle_img, or_img, cr_img, insurance_img, category, 
                        approved_price, ref_no, admin_status, booking_status, is_with_driver,
                        tire_pressure, preferred_fuel
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', 'UNAVAILABLE', ?, ?, ?)
                """, (st.session_state.username, ma.title(), mo.title(), ye, pl.upper(), bn, an, 
                      car_img_path, or_path, cr_path, ins_path, cat, 
                      FIXED_RATES.get(cat,0), new_ref_no, is_with_driver, tp, pf))
                
                conn.commit()
                st.success(f"SUCCESS: Vehicle Submitted! Ref #{new_ref_no}.")
            else: 
                st.error("Please fill all required fields and upload all documents.")

# --- TAB 3: ADD DRIVER ---
with tabs[3]:
    st.markdown("<h3 style='text-align: center;'>REGISTER A DRIVER</h3>", unsafe_allow_html=True)
    with st.form("add_d"):
        c1, c2, c3 = st.columns(3)
        df_first = c1.text_input("First Name").title()
        df_mid = c2.text_input("Middle Name").title()
        df_last = c3.text_input("Last Name").title()
        c_contact, c_age = st.columns(2)
        d_contact = c_contact.text_input("Contact No.")
        d_age = c_age.number_input("Age", min_value=18, max_value=99, step=1)
        d_address = st.text_area("Full Address")
        is_owner = st.checkbox("I am the driver (Owner driving)")
        d_gov = st.file_uploader("Upload Govt ID", type=['jpg','png'])
        d_lic = st.file_uploader("Upload Professional License", type=['jpg','png'])
        
        if st.form_submit_button("SUBMIT DRIVER FOR APPROVAL", type="primary"):
            if df_first and df_last and d_contact and d_gov and d_lic:
                # 1. Save to Database
                conn.execute("INSERT INTO drivers (owner_username, first_name, middle_name, last_name, age, address, contact_number, is_owner, govt_id_img, license_img, admin_status) VALUES (?,?,?,?,?,?,?,?,?,?, 'PENDING')", 
                             (st.session_state.username, df_first, df_mid, df_last, d_age, d_address, d_contact, 1 if is_owner else 0, save_file(d_lic), save_file(d_gov)))
                conn.commit()
                
                # 2. Alert Admin
                admin_phone = "09688811400"
                admin_email = "contact@driveelite.ph"
                subject = " Action Required: New Driver Pending Approval"
                body = f"Hello Admin,\n\nAffiliate @{st.session_state.username} has just registered a new driver: {df_first} {df_last}.\n\nPlease review documents."
                
                send_sms_alert(admin_phone, f"DriveElite Admin: Affiliate @{st.session_state.username} registered a new driver.")
                send_alert_email(admin_email, subject, body)

                st.success("SUCCESS: Driver Submitted!")
            else: 
                st.error("Please fill required fields.")
    
    # 4. Show Existing Drivers
    my_drivers = pd.read_sql_query("SELECT first_name, last_name, contact_number, admin_status FROM drivers WHERE owner_username = ?", conn, params=(st.session_state.username,))
    if not my_drivers.empty: 
        st.dataframe(my_drivers, hide_index=True, use_container_width=True)

# --- TAB 4: REVIEWS ---
with tabs[4]:
    st.markdown("<h3 style='text-align: center;'>⭐ Guest Reviews</h3>", unsafe_allow_html=True)
    query_reviews = """
        SELECT b.rating, b.review, b.pickup_time, u.full_name as renter_name, v.make, v.model, v.plate
        FROM bookings b JOIN vehicles v ON b.vehicle_id = v.id JOIN platform_users u ON b.renter_username = u.username
        WHERE v.owner_username = ? AND b.rating IS NOT NULL ORDER BY b.id DESC
    """
    try:
        reviews_df = pd.read_sql_query(query_reviews, conn, params=(st.session_state.username,))
        if reviews_df.empty: 
            st.info("No reviews yet!")
        else:
            for _, rev in reviews_df.iterrows():
                with st.container(border=True):
                    if pd.notna(rev['rating']) and rev['rating'] != "":
                        stars = '⭐' * int(float(rev['rating']))
                    else:
                        stars = "No rating provided"
                        
                    st.markdown(f"#### {stars} - {rev['make']} {rev['model']} ({rev['plate']})")
                    st.caption(f"🕵️‍♂️ Renter: {rev['renter_name']} | 📅 Date: {str(rev['pickup_time'])[:10]}")
                    if pd.notna(rev['review']) and str(rev['review']).strip(): 
                        st.info(f"💬 \"{rev['review']}\"")
    except Exception as e: 
        pass
