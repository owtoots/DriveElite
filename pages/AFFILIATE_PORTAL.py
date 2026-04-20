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

# --- DATABASE CONNECTION ---
conn = get_connection()

# --- DB PATCHES (Ensuring V2 Compliance & Dispute Features) ---
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

# Ensure admin_promos table exists so it doesn't crash before Admin creates it
try:
    conn.execute("CREATE TABLE IF NOT EXISTS admin_promos (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, message TEXT, target TEXT DEFAULT 'ALL USERS', active INTEGER DEFAULT 1)")
    conn.commit()
except: pass

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

# Get Affiliate Full Name
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
# 📢 NEW: BLINKING SYSTEM BROADCAST BANNER
# ==========================================
try:
    # Look for active promos targeting 'ALL USERS', 'ALL', or 'AFFILIATE'
    query = "SELECT title, message FROM admin_promos WHERE active = 1 AND target IN ('ALL USERS', 'ALL', 'AFFILIATE', 'AFFILIATES')"
    broadcasts = pd.read_sql_query(query, conn)
    
    if not broadcasts.empty:
        # Get the most recent active broadcast
        latest_b = broadcasts.iloc[-1]
        
        # CSS to create a pulsing "siren" effect
        blink_css = """
        <style>
        @keyframes pulse_glow {
            0% { box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.7); border-color: #e74c3c; }
            70% { box-shadow: 0 0 15px 15px rgba(220, 53, 69, 0); border-color: #ff9ff3; }
            100% { box-shadow: 0 0 0 0 rgba(220, 53, 69, 0); border-color: #e74c3c; }
        }
        .broadcast-banner {
            background: linear-gradient(135deg, #c0392b 0%, #e74c3c 100%);
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            border: 2px solid #e74c3c;
            text-align: center;
            margin-bottom: 25px;
            animation: pulse_glow 2s infinite;
        }
        .broadcast-title { font-size: 1.3em; font-weight: 900; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 1px;}
        .broadcast-msg { font-size: 1.1em; font-weight: 500; }
        </style>
        """
        
        # Render the banner
        st.markdown(blink_css + f"""
        <div class="broadcast-banner">
            <div class="broadcast-title">🚨 ADMIN ALERT: {latest_b['title']} 🚨</div>
            <div class="broadcast-msg">{latest_b['message']}</div>
        </div>
        """, unsafe_allow_html=True)
except Exception as e:
    pass # Fails silently if the admin hasn't sent anything yet
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
                    
                    # --- TRIP DETAILS ---
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
                    
                    # --- CHAT INTERFACE ---
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
                            conn.execute("INSERT INTO chat_messages (booking_ref, sender_username, receiver_username, message_text, image_path) VALUES (?, ?, ?, ?, ?)", (b['booking_ref'], st.session_state.username, b['renter_username'], text, path))
                            conn.commit()
                            st.rerun()
                                
                    st.divider()

                    # --- PHASE 1: TRIPLE-LOCK HANDOVER LOGIC ---
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

                    # --- PHASE 2: RETURN & SETTLEMENT LOGIC ---
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
                            
                            # 1. Late Fee
                            l_ok = st.checkbox("Returned on Time", value=True, key=f"l_{b['id']}")
                            late_fee = st.number_input("Hours Late (Php 300/hr)", min_value=1, step=1, key=f"l_hrs_{b['id']}") * 300.0 if not l_ok else 0.0
                            
                            # 2. Fuel Fee
                            f_ok = st.checkbox("Fuel Full", value=True, key=f"f_{b['id']}")
                            fuel_fee = (st.number_input("Refuel Receipt (Php)", step=100.0, key=f"f_cost_{b['id']}") + 200.0) if not f_ok else 0.0
                            
                            # 3. NEW: Cleaning & Smoking Fine
                            c_ok = st.checkbox("Interior Clean & Odor-Free", value=True, key=f"c_{b['id']}")
                            if not c_ok:
                                st.caption("Industry standard smoking/deep-clean fine is ₱2,500.")
                            cleaning_fee = st.number_input("Cleaning/Smoking Fine (Php)", value=2500.0, step=500.0, key=f"c_fine_{b['id']}") if not c_ok else 0.0
                            
                            # 4. Damage Fee
                            d_ok = st.checkbox("No Damage Found", value=True, key=f"d_{b['id']}")
                            damage_fee = 0.0
                            img_damage = None
                            if not d_ok:
                                img_damage = st.file_uploader("Upload Damage Photos", type=['jpg','png'], accept_multiple_files=True, key=f"p_dam_{b['id']}")
                                damage_fee = st.number_input("Estimated Damage Amount", step=500.0, key=f"d_est_{b['id']}")
                                
                            total_deduct = late_fee + fuel_fee + cleaning_fee + damage_fee
                            refund_amount = max(0, 5000.0 - total_deduct)
                            
                            st.write(f"**Total Deductions:** -Php {total_deduct:,.2f}")
                            if (5000.0 - total_deduct) < 0: 
                                st.error(f"RENTER OWES EXTRA: Php {abs(5000.0 - total_deduct):,.2f}")
                            else: 
                                st.success(f"REFUND CASH TO RENTER: Php {refund_amount:,.2f}")

                        with c2:
                            st.write("#### 🖊️ Final Sign-off")
                            if f"clr_sret_{b['id']}" not in st.session_state: st.session_state[f"clr_sret_{b['id']}"] = 0
                            s_ret = st_canvas(stroke_width=2, stroke_color="#000", background_color="#eee", height=150, width=200, key=f"sret_{b['id']}_{st.session_state[f'clr_sret_{b['id']}']}")
                            if st.button("Clear Pad", key=f"btn_sret_{b['id']}"): 
                                st.session_state[f"clr_sret_{b['id']}"] += 1
                                st.rerun()
                                
                            if st.button("✅ COMPLETE JOURNEY & SEND TO ADMIN", type="primary", use_container_width=True):
                                has_sig = s_ret.image_data is not None and len(s_ret.json_data.get("objects", [])) > 0
                                if not has_sig:
                                    st.error("Renter signature is required to close the trip.")
                                elif not d_ok and not img_damage:
                                    st.error("Upload a damage photo to proceed.")
                                else:
                                    d_img_path = ",".join([save_file(img) for img in img_damage]) if img_damage else None
                                    conn.execute("UPDATE bookings SET status = 'COMPLETED', payout_status = 'PENDING', damage_img = ? WHERE id = ?", (d_img_path, b['id']))
                                    conn.execute("UPDATE vehicles SET booking_status = 'AVAILABLE' WHERE id = ?", (b['vehicle_id'],))
                                    conn.commit()
                                    
                                    st.success("Car returned! Payout request sent to Admin.")
                                    time.sleep(2)
                                    st.rerun()
                                    
    except Exception as e:
        st.error(f"System Error loading bookings: {e}")

# --- TAB 1: MY ASSETS ---
with tabs[1]:
    st.markdown("<h3 style='text-align: center;'>MY FLEET CONTROLS</h3>", unsafe_allow_html=True)
    fleet = pd.read_sql_query("SELECT id, make, model, plate, booking_status, admin_status, ref_no FROM vehicles WHERE owner_username = ?", conn, params=(st.session_state.username,))
    if fleet.empty: st.info("You haven't added any vehicles yet.")
    for _, c in fleet.iterrows():
        v_ref = c.get('ref_no') if pd.notnull(c.get('ref_no')) else 'PENDING'
        with st.expander(f"🚗 #{v_ref} | {c['make']} {c['model']} ({c['plate']}) - Status: {c['booking_status']} (Admin: {c['admin_status']})"):
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
    try:
        cat_df = pd.read_sql_query("SELECT name, default_price FROM vehicle_categories", conn)
        FIXED_RATES = dict(zip(cat_df['name'], cat_df['default_price']))
    except Exception: 
        FIXED_RATES = {"Sedan": 1500.0} 
        
    with st.form("add_v"):
        cat = st.selectbox("CATEGORY", list(FIXED_RATES.keys()))
        c1, c2 = st.columns(2)
        ma = c1.text_input("MAKE (e.g., Nissan)")
        mo = c2.text_input("MODEL (e.g., Terra VE)")
        ye = c1.text_input("YEAR")
        pl = c2.text_input("PLATE")
        bn = c1.text_input("PAYOUT BANK")
        an = c2.text_input("ACCOUNT NUMBER")
        vi = st.file_uploader("Vehicle Photo", type=['jpg','png'])
        orc = st.file_uploader("OR/CR Doc", type=['jpg','png'])
        ins = st.file_uploader("Comprehensive Insurance", type=['jpg','png'])
        
        if st.form_submit_button("SUBMIT FOR APPROVAL", type="primary"):
            if ma and mo and pl and bn and an and vi and orc and ins:
                new_ref_no = str(random.randint(100000, 999999))
                conn.execute("""
                    INSERT INTO vehicles (owner_username, make, model, year, plate, bank_name, account_no, vehicle_img, or_cr_img, insurance_img, category, approved_price, ref_no, admin_status, booking_status) 
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'PENDING','UNAVAILABLE')
                """, (st.session_state.username, ma.title(), mo.title(), ye, pl.upper(), bn, an, save_file(vi), save_file(orc), save_file(ins), cat, FIXED_RATES.get(cat,0), new_ref_no))
                conn.commit()
                st.success(f"SUCCESS: Vehicle Submitted! Ref #{new_ref_no}.")
            else: 
                st.error("Please fill all required fields.")

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
                conn.execute("INSERT INTO drivers (owner_username, first_name, middle_name, last_name, age, address, contact_number, is_owner, govt_id_img, license_img, admin_status) VALUES (?,?,?,?,?,?,?,?,?,?, 'PENDING')", (st.session_state.username, df_first, df_mid, df_last, d_age, d_address, d_contact, 1 if is_owner else 0, save_file(d_lic), save_file(d_gov)))
                conn.commit()
                st.success("SUCCESS: Driver Submitted!")
            else: 
                st.error("Please fill required fields.")
    
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
        if reviews_df.empty: st.info("No reviews yet!")
        else:
            for _, rev in reviews_df.iterrows():
                with st.container(border=True):
                    st.markdown(f"#### {'⭐'*int(rev['rating'])} - {rev['make']} {rev['model']} ({rev['plate']})")
                    st.caption(f"🕵️‍♂️ Renter: {rev['renter_name']} | 📅 Date: {str(rev['pickup_time'])[:10]}")
                    if pd.notna(rev['review']) and str(rev['review']).strip(): st.info(f"💬 \"{rev['review']}\"")
    except: pass

# --- SIDEBAR ---
with st.sidebar:
    st.write(f"### 👤 Affiliate Profile")
    st.write(f"**Name:** {affiliate_full_name}")
    st.write(f"**Username:** @{st.session_state.username}")
    moa_path = f"uploads/MOA_{st.session_state.username}.pdf"
    if os.path.exists(moa_path):
        st.success("Partner Verified ✅")
        with open(moa_path, "rb") as pdf_file:
            st.download_button("📄 Download Signed MOA", data=pdf_file.read(), file_name=f"Signed_MOA_{st.session_state.username}.pdf", mime="application/pdf", use_container_width=True)
    else: 
        st.warning("⚠️ No signed MOA found.")
    st.divider()
    st.caption("DriveElite 2026")
