import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import streamlit as st
import pandas as pd
import datetime
import os
import random 
import time
from PIL import Image
import numpy as np
from fpdf import FPDF
from database_utils import get_connection
from streamlit_drawable_canvas import st_canvas

# --- DATABASE CONNECTION & SELF-REPAIR ---
conn = get_connection()

def patch_database():
    """Ensures all new columns and tables exist to prevent operational crashes."""
    try: conn.execute("ALTER TABLE platform_users ADD COLUMN document_url TEXT"); conn.commit()
    except: pass
    try: conn.execute("ALTER TABLE vehicles ADD COLUMN admin_status TEXT DEFAULT 'PENDING'"); conn.commit()
    except: pass
    try:
        conn.execute("ALTER TABLE bookings ADD COLUMN handover_photos TEXT")
        conn.execute("ALTER TABLE bookings ADD COLUMN handover_sig_renter TEXT")
        conn.execute("ALTER TABLE bookings ADD COLUMN handover_sig_affiliate TEXT")
        conn.commit()
    except: pass
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS admin_promos (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, message TEXT, target TEXT DEFAULT 'ALL USERS', active INTEGER DEFAULT 1)")
        conn.commit()
    except: pass
    
    # --- CHAT TABLE PATCH ---
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

if not os.path.exists("uploads"): os.makedirs("uploads")

# --- UTILITIES & HELPERS ---
def save_file(uploaded_file):
    if uploaded_file:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{uploaded_file.name}"
        path = os.path.join("uploads", filename)
        with open(path, "wb") as f: f.write(uploaded_file.getbuffer())
        return path
    return None

def save_chat_image(uploaded_file, booking_ref):
    if uploaded_file:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chat_{booking_ref}_{timestamp}_{uploaded_file.name}"
        path = os.path.join("uploads", filename)
        with open(path, "wb") as f: f.write(uploaded_file.getbuffer())
        return path
    return ""

def save_canvas_image(image_data, prefix):
    if image_data is not None:
        img = Image.fromarray(image_data.astype('uint8'), 'RGBA')
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join("uploads", f"{prefix}_{timestamp}.png")
        background.save(filename)
        return filename
    return None

def generate_handover_pdf(ref_no, car_name, renter_name, travel_dates, checklist, r_sig_path, a_sig_path, affiliate_name):
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
    pdf.ln(10)
    
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, "DIGITAL SIGNATORIES:", ln=True)
    
    y_sig = pdf.get_y()
    if r_sig_path and os.path.exists(r_sig_path):
        pdf.image(r_sig_path, x=30, y=y_sig, w=50)
    if a_sig_path and os.path.exists(a_sig_path):
        pdf.image(a_sig_path, x=120, y=y_sig, w=50)
    
    pdf.set_y(y_sig + 30)
    pdf.set_font("Helvetica", 'U', 11)
    pdf.cell(90, 8, renter_name, align='C')
    pdf.cell(90, 8, affiliate_name, align='C', ln=True)
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(90, 5, "Renter", align='C')
    pdf.cell(90, 5, "Affiliate/Host", align='C', ln=True)
    
    return pdf.output(dest="S").encode("latin-1")

def send_pdf_email(to_email, subject, body, pdf_bytes, filename):
    sender_email = "rdalbaojr@gmail.com" 
    try: app_password = st.secrets["email_app_password"]
    except: return False
        
    msg = MIMEMultipart()
    msg['From'] = f"DriveElite Admin <{sender_email}>"
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    part = MIMEBase('application', 'octet-stream')
    part.set_payload(pdf_bytes)
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f"attachment; filename= {filename}")
    msg.attach(part)
    
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, app_password)
            server.send_message(msg)
        return True
    except: 
        return False

# --- AUTHENTICATION ---
st.set_page_config(page_title="DriveElite Affiliate Portal", layout="wide")

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
top_col_logo, top_col1, top_col2 = st.columns([1, 4, 1])
with top_col_logo:
    try: st.image("logo.png", use_container_width=True)
    except: pass
with top_col2:
    if st.button("🔒 LOGOUT", use_container_width=True):
        st.session_state.clear()
        st.rerun()
st.divider()

# ==========================================
# 📢 SMART COLOR-CHANGING BROADCAST BANNER
# ==========================================
try:
    query = "SELECT title, message, target FROM admin_promos WHERE active = 1 AND target IN ('ALL USERS', 'ALL', 'AFFILIATE', 'AFFILIATES')"
    broadcasts = pd.read_sql_query(query, conn)
    
    if not broadcasts.empty:
        latest_b = broadcasts.iloc[-1]
        target_group = str(latest_b['target']).upper()
        
        if target_group in ['ALL USERS', 'ALL']:
            primary_color = "#27ae60" 
            gradient = "linear-gradient(135deg, #2ecc71 0%, #27ae60 100%)"
            glow_color = "rgba(39, 174, 96, 0.7)"
        else:
            primary_color = "#c0392b" 
            gradient = "linear-gradient(135deg, #e74c3c 0%, #c0392b 100%)"
            glow_color = "rgba(231, 76, 60, 0.7)"
            
        blink_css = f"""
        <style>
        @keyframes pulse_glow_affiliate {{
            0% {{ box-shadow: 0 0 0 0 {glow_color}; border-color: {primary_color}; }}
            70% {{ box-shadow: 0 0 15px 15px rgba(0,0,0,0); border-color: #ffffff; }}
            100% {{ box-shadow: 0 0 0 0 rgba(0,0,0,0); border-color: {primary_color}; }}
        }}
        .broadcast-banner-affiliate {{
            background: {gradient};
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            border: 2px solid {primary_color};
            text-align: center;
            margin-bottom: 25px;
            animation: pulse_glow_affiliate 2s infinite;
        }}
        .broadcast-title-affiliate {{ font-size: 1.3em; font-weight: 900; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 1px;}}
        .broadcast-msg-affiliate {{ font-size: 1.1em; font-weight: 500; }}
        </style>
        """
        
        st.markdown(blink_css + f"""
        <div class="broadcast-banner-affiliate">
            <div class="broadcast-title-affiliate">📢 ADMIN BROADCAST: {latest_b['title']} 📢</div>
            <div class="broadcast-msg-affiliate">{latest_b['message']}</div>
        </div>
        """, unsafe_allow_html=True)
except Exception as e:
    pass 
# ==========================================

# --- TABS ---
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
                status_icon = "🟡" if b['status'] in ['PENDING', 'CONFIRMED'] else "🟢"
                b_ref_display = f"#{b['booking_ref']}" if pd.notnull(b.get('booking_ref')) else f"DRV-{b['id']:05d}"
                
                with st.expander(f"{status_icon} {str(b['pickup_time'])[:16]} | {b['make']} {b['model']} ({b['plate']})"):
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Booking Ref:** {b_ref_display}")
                        st.write(f"**Renter:** {b['renter_name']}")
                        st.write(f"**Contact:** {b['renter_contact']}")
                    with col2:
                        st.write(f"**Pickup:** {b.get('pickup_loc', 'Not specified')}")
                        st.write(f"**Return:** {b.get('return_loc', 'Not specified')}")
                        st.write(f"**Total Revenue:** ₱{b['amount']:,.2f}")
                    st.divider()
                    
                    st.markdown("#### 💬 Message the Renter")
                    chat_win = st.container(height=250, border=True)
                    with chat_win:
                        try:
                            history = pd.read_sql_query("SELECT * FROM chat_messages WHERE booking_ref = ? ORDER BY timestamp ASC", conn, params=(b['booking_ref'],))
                            for _, msg in history.iterrows():
                                role = "user" if msg['sender_username'] == st.session_state.username else "assistant"
                                with st.chat_message(role):
                                    st.write(msg['message_text'])
                                    if pd.notna(msg.get('image_path')) and msg['image_path'] and os.path.exists(msg['image_path']):
                                        st.image(msg['image_path'], width=200)
                        except: st.caption("No messages yet.")

                    c_img, c_msg = st.columns([1, 4])
                    with c_img: a_img = st.file_uploader("📷", type=['jpg','png','jpeg'], key=f"a_img_{b['id']}", label_visibility="collapsed")
                    with c_msg: a_input = st.text_input("Reply...", key=f"a_in_{b['id']}")

                    if st.button("Send", key=f"a_btn_{b['id']}", use_container_width=True):
                        if a_input or a_img:
                            path = save_chat_image(a_img, b['booking_ref']) if a_img else ""
                            text = a_input if a_input else "📸 Sent a photo."
                            
                            # --- ANTI-LOCK & ERROR CATCHER ---
                            success = False
                            error_msg = ""
                            for attempt in range(3):
                                try:
                                    conn.execute("INSERT INTO chat_messages (booking_ref, sender_username, receiver_username, message_text, image_path) VALUES (?, ?, ?, ?, ?)", (b['booking_ref'], st.session_state.username, b['renter_username'], text, path))
                                    conn.commit()
                                    success = True
                                    break
                                except Exception as e:
                                    error_msg = str(e)
                                    if "locked" in error_msg.lower():
                                        time.sleep(0.5) # Wait and retry if locked
                                    else:
                                        break
                                        
                            if success:
                                st.rerun()
                            else:
                                st.warning(f"🚨 **DATABASE ERROR:** {error_msg}")
                            # ---------------------------------
                                
                    st.divider()

                    if b['status'] == 'PENDING' or b['status'] == 'CONFIRMED':
                        st.info("🚨 **ACTION REQUIRED:** Complete the Digital Handover with the Renter present.")
                        
                        with st.expander("📋 Official Handover & Photo Evidence", expanded=True):
                            st.write("### 1. Vehicle Checklist")
                            c1, c2 = st.columns(2)
                            with c1:
                                c_fuel = st.selectbox("Current Fuel Level", ["Full", "3/4", "1/2", "1/4", "Empty"], key=f"fuel_{b['id']}")
                                c_deposit = st.checkbox("₱5,000 Cash Deposit Received", value=False, key=f"dep_{b['id']}")
                            with c2:
                                c_ext = st.checkbox("Exterior inspected (No new damage)", value=True, key=f"ext_{b['id']}")
                                c_int = st.checkbox("Interior is clean/odor-free", value=True, key=f"int_{b['id']}")
                                c_tools = st.checkbox("Tools/Spare tire verified", value=True, key=f"tools_{b['id']}")
                            
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
                                s_r = st_canvas(stroke_width=2, stroke_color="#000", background_color="#eee", height=150, width=300, display_toolbar=False, key=f"sr_{b['id']}_{st.session_state[f'clr_sr_{b['id']}']}")
                                if st.button("Clear Renter Pad", key=f"btn_sr_{b['id']}", use_container_width=True): 
                                    st.session_state[f"clr_sr_{b['id']}"] += 1
                                    st.rerun()
                                st.markdown(f"<div style='text-align: center; margin-top: -10px;'><u><b>{b['renter_name']}</b></u><br>Renter</div>", unsafe_allow_html=True)
                            
                            with col_sig2:
                                if f"clr_sa_{b['id']}" not in st.session_state: st.session_state[f"clr_sa_{b['id']}"] = 0
                                s_a = st_canvas(stroke_width=2, stroke_color="#000", background_color="#eee", height=150, width=300, display_toolbar=False, key=f"sa_{b['id']}_{st.session_state[f'clr_sa_{b['id']}']}")
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
                                    st.error("❌ DISPATCH BLOCKED: You must verify receipt of the ₱5,000 Cash Deposit.")
                                elif not (has_sr and has_sa):
                                    st.error("❌ DISPATCH BLOCKED: Both parties must sign on the digital pads.")
                                else:
                                    r_sig_path = save_canvas_image(s_r.image_data, f"sig_r_{b['booking_ref']}")
                                    a_sig_path = save_canvas_image(s_a.image_data, f"sig_a_{b['booking_ref']}")
                                    
                                    chk_data = {'fuel': c_fuel, 'ext': c_ext, 'int': c_int, 'tools': c_tools, 'deposit': c_deposit}
                                    travel_dates = f"{str(b.get('pickup_time'))[:10]} to {str(b.get('return_time'))[:10]}"
                                    pdf_bytes = generate_handover_pdf(b['booking_ref'], f"{b['make']} {b['model']} ({b['plate']})", b['renter_name'], travel_dates, chk_data, r_sig_path, a_sig_path, affiliate_full_name)
                                    
                                    pdf_filepath = f"uploads/Handover_{b['booking_ref']}.pdf"
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
                        
                        pdf_filepath = f"uploads/Handover_{b['booking_ref']}.pdf"
                        if os.path.exists(pdf_filepath):
                            with open(pdf_filepath, "rb") as pdf_file:
                                st.download_button("📄 DOWNLOAD SIGNED HANDOVER PDF", data=pdf_file.read(), file_name=f"Handover_{b['booking_ref']}.pdf", mime="application/pdf", type="secondary", use_container_width=True)
                            st.divider()

                        c1, c2 = st.columns(2)
                        with c1:
                            st.write("#### 🛠️ Agreement Penalties")
                            
                            l_ok = st.checkbox("Returned on Time", value=True, key=f"l_{b['id']}")
                            late_fee = st.number_input("Hours Late (Php 300/hr)", min_value=1, step=1, key=f"l_hrs_{b['id']}") * 300.0 if not l_ok else 0.0
                            
                            f_ok = st.checkbox("Fuel Full", value=True, key=f"f_{b['id']}")
                            fuel_fee = (st.number_input("Refuel Receipt (Php)", step=10
