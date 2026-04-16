import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import streamlit as st
import pandas as pd
import datetime
import os
import numpy as np
import time
import random 
from PIL import Image
from fpdf import FPDF
from database_utils import get_connection
from streamlit_drawable_canvas import st_canvas

# --- DATABASE CONNECTION ---
conn = get_connection()

# --- DB PATCH ---
try: 
    conn.execute("ALTER TABLE users ADD COLUMN document_url TEXT")
    conn.commit()
except Exception: 
    pass

if not os.path.exists("uploads"): 
    os.makedirs("uploads")

# --- UTILITIES ---
def save_file(uploaded_file):
    if uploaded_file:
        path = os.path.join("uploads", uploaded_file.name)
        with open(path, "wb") as f: f.write(uploaded_file.getbuffer())
        return path
    return None

def send_pdf_email(to_email, subject, body, pdf_bytes, filename):
    sender_email = "rdalbaojrh@gmail.com" 
    app_password = "f22c3FF18pr" 
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
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)
        server.quit()
        return True
    except: 
        return False

# --- PDF ENGINES ---
def generate_contract(booking_ref, renter, vehicle, plate, chk_data, sig_r, sig_a, is_with_driver=False, driver_name=""):
    pdf = FPDF()
    pdf.add_page()
    try:
        pdf.image("logo.png", x=80, y=10, w=50)
        pdf.set_y(45) 
    except Exception: 
        pdf.set_y(20)
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, "DRIVEELITE HANDOVER AGREEMENT", ln=True, align='C')
    pdf.set_font("Helvetica", '', 12)
    pdf.cell(0, 10, f"Ref: {booking_ref} | Date: {datetime.date.today()}", ln=True)
    pdf.cell(0, 10, f"Vehicle: {vehicle} ({plate}) | Renter: {renter}", ln=True)
    if is_with_driver and driver_name:
        pdf.cell(0, 10, f"Assigned Driver: {driver_name}", ln=True)
    pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, "VERIFIED HANDOVER CHECKLIST:", ln=True)
    pdf.set_font("Helvetica", '', 11)
    for item in chk_data: 
        pdf.cell(0, 8, f"[ OK ]  {item}", ln=True)
    current_y = pdf.get_y() + 10
    try:
        if sig_r is not None:
            Image.fromarray(sig_r.astype('uint8'), 'RGBA').convert('RGB').save("tr.jpg", "JPEG")
            pdf.image("tr.jpg", x=20, y=current_y, w=50)
        if sig_a is not None:
            Image.fromarray(sig_a.astype('uint8'), 'RGBA').convert('RGB').save("ta.jpg", "JPEG")
            pdf.image("ta.jpg", x=120, y=current_y, w=50)
    except: 
        pass
    pdf.set_xy(20, current_y + 40)
    pdf.cell(50, 5, "Renter Signature", align='C')
    pdf.set_xy(120, current_y + 40)
    pdf.cell(50, 5, "Partner Signature", align='C')
    return pdf.output(dest="S").encode("latin-1")

def generate_return_receipt(booking_ref, renter, vehicle, plate, fuel, clean, damage, late, rfid, ot, total, refund, sig_ret, sig_reta):
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
    pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, "SECURITY DEPOSIT SETTLEMENT:", ln=True)
    pdf.set_font("Helvetica", '', 11)
    pdf.cell(0, 8, f"- Fuel Penalty (Cost + Surcharge): Php {fuel:,.2f}", ln=True)
    pdf.cell(0, 8, f"- Cleaning Penalty: Php {clean:,.2f}", ln=True)
    pdf.cell(0, 8, f"- Damage Assessment: Php {damage:,.2f}", ln=True)
    pdf.cell(0, 8, f"- Late Penalty (Php 300/hr): Php {late:,.2f}", ln=True)
    pdf.cell(0, 8, f"- RFID Usage (Load + Surcharge): Php {rfid:,.2f}", ln=True)
    if ot > 0:
        pdf.cell(0, 8, f"- Driver Overtime (Php 200/hr): Php {ot:,.2f}", ln=True)
    pdf.ln(5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, f"TOTAL DEDUCTIONS: Php {total:,.2f}", ln=True)
    pdf.cell(0, 10, f"NET CASH REFUNDED TO RENTER: Php {refund:,.2f}", ln=True)
    current_y = pdf.get_y() + 15
    try:
        if sig_ret is not None:
            Image.fromarray(sig_ret.astype('uint8'), 'RGBA').convert('RGB').save("tret.jpg", "JPEG")
            pdf.image("tret.jpg", x=20, y=current_y, w=50)
        if sig_reta is not None:
            Image.fromarray(sig_reta.astype('uint8'), 'RGBA').convert('RGB').save("treta.jpg", "JPEG")
            pdf.image("treta.jpg", x=120, y=current_y, w=50)
    except: 
        pass
    pdf.set_xy(20, current_y + 40)
    pdf.cell(50, 5, "Renter Sign-off", align='C')
    pdf.set_xy(120, current_y + 40)
    pdf.cell(50, 5, "Partner Sign-off", align='C')
    return pdf.output(dest="S").encode("latin-1")

# --- AUTHENTICATION ---
st.set_page_config(page_title="DriveElite Affiliate Portal", layout="wide")

if not st.session_state.get('logged_in') or st.session_state.get('role') != 'AFFILIATE':
    logo_col1, logo_col2, logo_col3 = st.columns([1, 2, 1])
    with logo_col2:
        try: st.image("logo.png", use_container_width=True)
        except: pass
    st.markdown("<h2 style='text-align: center;'>💼 AFFILIATE LOGIN</h2>", unsafe_allow_html=True)
    with st.form("login", clear_on_submit=True):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("LOGIN", use_container_width=True):
            user = pd.read_sql_query("SELECT * FROM users WHERE username=? AND password=? AND role='AFFILIATE'", conn, params=(u, p))
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
aff_info = pd.read_sql_query("SELECT full_name FROM users WHERE username=?", conn, params=(st.session_state.username,))
affiliate_full_name = aff_info.iloc[0]['full_name'] if not aff_info.empty else st.session_state.username

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

# --- TABS ---
tabs = st.tabs(["BOOKINGS & HANDOVER", "MY ASSETS", "ADD ASSET", "ADD DRIVER", "REVIEWS"])

# --- TAB 0: BOOKINGS, HANDOVER & RETURNS ---
with tabs[0]:
    
    # ----------------------------------------------------
    # 1. PENDING DISPATCH (Handover)
    # ----------------------------------------------------
    st.markdown("<h3 style='text-align: center;'>🟡 PENDING DISPATCH (Vehicle Release)</h3>", unsafe_allow_html=True)
    pending = pd.read_sql_query("""
        SELECT b.id, b.renter_username, b.with_driver, b.pickup_time, b.booking_ref, 
               u.full_name as renter_fullname, u.email as renter_email,
               v.make, v.model, v.plate FROM bookings b 
        JOIN vehicles v ON b.vehicle_id = v.id 
        JOIN users u ON b.renter_username = u.username 
        WHERE v.owner_username = ? AND b.status = 'CONFIRMED'
        ORDER BY b.pickup_time ASC""", conn, params=(st.session_state.username,))
    
    if pending.empty: 
        st.info("No vehicles pending handover.")
    
    for _, t in pending.iterrows():
        b_ref = t.get('booking_ref') if pd.notnull(t.get('booking_ref')) else 'PENDING'
        with st.expander(f"🤝 #{b_ref} | RELEASE: {t['make']} {t['model']} ({t['plate']}) - Renter: {t['renter_fullname']}"):
            
            if f"contract_{t['id']}" in st.session_state:
                st.success("SUCCESS: Contract generated! Download to your phone & share.")
                st.download_button("📥 DOWNLOAD PDF CONTRACT", data=st.session_state[f"contract_{t['id']}"], file_name=f"Handover_{b_ref}.pdf", mime="application/pdf", use_container_width=True)
                if st.button("FINISH & RELEASE VEHICLE (START TRIP)", key=f"fin_{t['id']}", type="primary", use_container_width=True):
                    imgs = st.session_state.get(f"imgs_{t['id']}", [None]*10)
                    ass_driver = st.session_state.get(f"drv_{t['id']}", "")
                    conn.execute("""UPDATE bookings SET status = 'ONGOING', 
                                    front_img=?, back_img=?, left_img=?, right_img=?, odometer_img=?, 
                                    dseat_img=?, pseat_img=?, tire_img=?, trunk_img=?, actual_dl_img=?, 
                                    assigned_driver=? WHERE id = ?""", (*imgs, ass_driver, t['id']))
                    conn.commit()
                    st.rerun()
            else:
                is_with_driver = t.get('with_driver', 0) == 1
                assigned_driver = ""
                can_proceed = True
                
                if is_with_driver:
                    st.warning("👨‍✈️ *DRIVER REQUIRED*")
                    my_drivers = pd.read_sql_query("SELECT first_name || ' ' || last_name as full_name FROM drivers WHERE owner_username = ? AND admin_status = 'APPROVED'", conn, params=(st.session_state.username,))
                    if my_drivers.empty: 
                        st.error("⚠️ No APPROVED drivers registered to your account.")
                        can_proceed = False
                    else: 
                        assigned_driver = st.selectbox("Assign Driver:", my_drivers['full_name'].tolist(), key=f"d_sel_{t['id']}")
                
                if can_proceed:
                    chk_tank = st.checkbox("[ ] Full Tank Verified", key=f"htank_{t['id']}")
                    chk_exterior = st.checkbox("[ ] Exterior & Tires Check OK", key=f"hext_{t['id']}")
                    chk_deposit = st.checkbox("[ ] Php 5k Cash Deposit Received", key=f"hdep_{t['id']}")
                    
                    st.write("**BULK UPLOAD 10 PHOTOS (Required)**")
                    bulk_photos = st.file_uploader("Upload pre-dispatch photos", type=['jpg','png'], accept_multiple_files=True, key=f"bulk_{t['id']}")
                    st.divider()
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        if f"clr_sr_{t['id']}" not in st.session_state: st.session_state[f"clr_sr_{t['id']}"] = 0
                        s_r = st_canvas(stroke_width=2, stroke_color="#000", background_color="#eee", height=150, width=300, display_toolbar=False, key=f"sr_{t['id']}_{st.session_state[f'clr_sr_{t['id']}']}")
                        if st.button("Clear Renter Pad", key=f"btn_sr_{t['id']}", use_container_width=True):
                            st.session_state[f"clr_sr_{t['id']}"] += 1
                            st.rerun()
                        st.write(f"**Renter:** {t['renter_fullname']} /{t['renter_username']}")
                        
                    with c2:
                        if f"clr_sa_{t['id']}" not in st.session_state: st.session_state[f"clr_sa_{t['id']}"] = 0
                        s_a = st_canvas(stroke_width=2, stroke_color="#000", background_color="#eee", height=150, width=300, display_toolbar=False, key=f"sa_{t['id']}_{st.session_state[f'clr_sa_{t['id']}']}")
                        if st.button("Clear Partner Pad", key=f"btn_sa_{t['id']}", use_container_width=True):
                            st.session_state[f"clr_sa_{t['id']}"] += 1
                            st.rerun()
                        st.write(f"**Partner:** {affiliate_full_name} /{st.session_state.username}")
                        
                    if st.button("GENERATE CONTRACT & DISPATCH", key=f"ex_{t['id']}", type="primary", use_container_width=True):
                        has_sr = s_r.image_data is not None and len(s_r.json_data.get("objects", [])) > 0
                        has_sa = s_a.image_data is not None and len(s_a.json_data.get("objects", [])) > 0
                        
                        if not (chk_tank and chk_exterior and chk_deposit): 
                            st.error("Please verify all checklist items.")
                        elif not bulk_photos or len(bulk_photos) < 10: 
                            st.error("10 pre-dispatch photos are required.")
                        elif not (has_sr and has_sa): 
                            st.error("Both signatures are required.")
                        else:
                            chk_items = ["Full Tank", "Exterior check OK", "Php 5k Deposit Confirmed"]
                            b_ref_display = f"#{t['booking_ref']}" if pd.notnull(t.get('booking_ref')) else f"DRV-{t['id']:05d}"
                            
                            pdf_bytes = generate_contract(b_ref_display, t['renter_fullname'], f"{t['make']} {t['model']}", t['plate'], chk_items, s_r.image_data, s_a.image_data, is_with_driver, assigned_driver)
                            st.session_state[f"contract_{t['id']}"] = pdf_bytes
                            st.session_state[f"imgs_{t['id']}"] = [save_file(bulk_photos[i]) for i in range(10)]
                            st.session_state[f"drv_{t['id']}"] = assigned_driver
                            
                            # Email execution
                            affiliate_email_df = pd.read_sql_query("SELECT email FROM users WHERE username=?", conn, params=(st.session_state.username,))
                            affiliate_email = affiliate_email_df.iloc[0]['email'] if not affiliate_email_df.empty else None
                            
                            if t['renter_email']: send_pdf_email(t['renter_email'], f"Handover Contract: {b_ref_display}", "Attached is your binding handover agreement.", pdf_bytes, f"Handover_{b_ref_display}.pdf")
                            if affiliate_email: send_pdf_email(affiliate_email, f"Partner Copy: {b_ref_display}", "Attached is your copy.", pdf_bytes, f"Handover_{b_ref_display}.pdf")
                            
                            st.rerun()
# ----------------------------------------------------
    # 3. DRIVEELITE MESSENGER (Affiliate View)
    # ----------------------------------------------------
    st.divider()
    st.markdown("<h3 style='text-align: center;'>💬 DRIVEELITE MESSENGER</h3>", unsafe_allow_html=True)
    
    # Get list of active Renters to chat with
    chat_partners = pd.read_sql_query("""
        SELECT DISTINCT b.booking_ref, b.renter_username, u.full_name 
        FROM bookings b 
        JOIN vehicles v ON b.vehicle_id = v.id 
        JOIN users u ON b.renter_username = u.username
        WHERE v.owner_username = ? AND b.status IN ('CONFIRMED', 'ONGOING')
    """, conn, params=(st.session_state.username,))

    if chat_partners.empty:
        st.info("No active bookings to chat with.")
    else:
        # Selection for which renter to talk to
        chat_options = {f"Booking #{r['booking_ref']} - {r['full_name']}": r for _, r in chat_partners.iterrows()}
        selected_label = st.selectbox("Select a conversation:", ["-- Select Renter --"] + list(chat_options.keys()))
        
        if selected_label != "-- Select Renter --":
            target = chat_options[selected_label]
            b_ref = target['booking_ref']
            renter_uname = target['renter_username']
            
            # --- DISPLAY CHAT BOX ---
            chat_container = st.container(height=400, border=True)
            with chat_container:
                history = pd.read_sql_query("""
                    SELECT * FROM chat_messages 
                    WHERE booking_ref = ? 
                    ORDER BY timestamp ASC
                """, conn, params=(b_ref,))
                
                for _, msg in history.iterrows():
                    align = "user" if msg['sender_username'] == st.session_state.username else "assistant"
                    with st.chat_message(align):
                        st.write(msg['message_text'])
                        if msg['image_path']:
                            st.image(msg['image_path'], width=250)

            # --- INPUT AREA ---
            with st.expander("📎 Attach Photo (Turnover/Evidence)"):
                chat_img = st.file_uploader("Upload photo", type=['jpg','png','jpeg'], key=f"chatimg_{b_ref}")
            
            chat_input = st.chat_input("Type a message to the Renter...")
            
            if chat_input or chat_img:
                img_path = save_chat_image(chat_img, b_ref) if chat_img else ""
                msg_text = chat_input if chat_input else "📸 Sent an attachment."
                
                conn.execute("""
                    INSERT INTO chat_messages (booking_ref, sender_username, receiver_username, message_text, image_path)
                    VALUES (?, ?, ?, ?, ?)
                """, (b_ref, st.session_state.username, renter_uname, msg_text, img_path))
                conn.commit()
                st.rerun()
    
    st.divider()

    # ----------------------------------------------------
    # 2. ONGOING TRIPS (Return & Settlement Flow)
    # ----------------------------------------------------
    st.markdown("<h3 style='text-align: center;'>🏁 ONGOING TRIPS (Return & Settlement)</h3>", unsafe_allow_html=True)
    ongoing = pd.read_sql_query("""
        SELECT b.id, b.vehicle_id, b.renter_username, b.with_driver, b.booking_ref, 
               u.full_name as renter_fullname, u.email as renter_email, 
               v.make, v.model, v.plate FROM bookings b 
        JOIN vehicles v ON b.vehicle_id = v.id 
        JOIN users u ON b.renter_username = u.username 
        WHERE v.owner_username = ? AND b.status = 'ONGOING'""", conn, params=(st.session_state.username,))
    
    if ongoing.empty: 
        st.info("No vehicles currently on the road.")
        
    for _, t in ongoing.iterrows():
        b_ref = t.get('booking_ref') if pd.notnull(t.get('booking_ref')) else 'PENDING'
        with st.expander(f"🏁 #{b_ref} | RECEIVE & SETTLE: {t['make']} {t['model']} ({t['plate']}) - Renter: {t['renter_fullname']}"):
            
            if f"ret_receipt_{t['id']}" in st.session_state:
                refund_amt = st.session_state[f"refund_{t['id']}"]
                st.success(f"SUCCESS: Settlement calculated! Refund to handover: Php {refund_amt:,.2f}")
                st.download_button("📥 DOWNLOAD SETTLEMENT PDF", data=st.session_state[f"ret_receipt_{t['id']}"], file_name=f"Settlement_{b_ref}.pdf", mime="application/pdf", use_container_width=True)
                
                if st.button("CLOSE BOOKING & RELEASE VEHICLE", key=f"fin_ret_{t['id']}", type="primary", use_container_width=True):
                    d_img_path = st.session_state.get(f"dmg_img_{t['id']}", None)
                    conn.execute("UPDATE bookings SET status = 'COMPLETED', damage_img = ? WHERE id = ?", (d_img_path, t['id']))
                    conn.execute("UPDATE vehicles SET booking_status = 'AVAILABLE' WHERE id = ?", (t['vehicle_id'],))
                    conn.commit()
                    st.rerun()
            else:
                is_with_driver = t.get('with_driver', 0) == 1
                c1, c2 = st.columns(2)
                
                with c1:
                    st.write("#### 🛠️ Agreement Penalties")
                    # 1. Late Penalty (Php 300/hr)
                    l_ok = st.checkbox("Returned on Time", value=True, key=f"l_{t['id']}")
                    late_hrs = st.number_input("Hours Late (Php 300/hr)", min_value=1, step=1, key=f"l_hrs_{t['id']}") if not l_ok else 0
                    late_fee = late_hrs * 300.0
                    
                    # 2. Fuel Penalty (Cost + Php 200)
                    f_ok = st.checkbox("Fuel Full", value=True, key=f"f_{t['id']}")
                    fuel_cost = st.number_input("Refuel Receipt Amount (Php)", step=100.0, key=f"f_cost_{t['id']}") if not f_ok else 0.0
                    fuel_fee = (fuel_cost + 200.0) if not f_ok else 0.0
                    
                    # 3. Clean Penalty (Up to 500)
                    c_ok = st.checkbox("Vehicle Clean", value=True, key=f"c_{t['id']}")
                    clean_fee = st.slider("Cleaning/Smoking Penalty (Php)", 0.0, 500.0, 0.0, step=100.0, key=f"c_cost_{t['id']}") if not c_ok else 0.0
                    
                    # 4. RFID Penalty (Cost + Php 200)
                    r_ok = st.checkbox("RFID Balance OK", value=True, key=f"r_{t['id']}")
                    rfid_load = st.number_input("RFID Load Used (Php)", step=50.0, key=f"r_cost_{t['id']}") if not r_ok else 0.0
                    rfid_fee = (rfid_load + 200.0) if not r_ok else 0.0
                    
                    # 5. Driver OT (Php 200/hr)
                    ot_fee = 0.0
                    if is_with_driver:
                        ot_ok = st.checkbox("Driver Hours OK", value=True, key=f"ot_chk_{t['id']}")
                        ot_hrs = st.number_input("Overtime Hours (Php 200/hr)", min_value=1, step=1, key=f"ot_hrs_{t['id']}") if not ot_ok else 0
                        ot_fee = ot_hrs * 200.0
                    
                    # 6. Damage Assessment
                    d_ok = st.checkbox("No Damage Found", value=True, key=f"d_{t['id']}")
                    damage_fee = 0.0
                    img_damage = None
                    if not d_ok:
                        img_damage = st.file_uploader("Upload Damage Photos", type=['jpg','png'], accept_multiple_files=True, key=f"p_dam_{t['id']}")
                        dam_type = st.radio("Damage Type", ["Php 4k/panel", "Repair Estimate"], key=f"d_type_{t['id']}")
                        if dam_type == "Php 4k/panel":
                            panels = st.number_input("Damaged Panels", min_value=1, step=1, key=f"d_pan_{t['id']}")
                            damage_fee = panels * 4000.0
                        else: 
                            damage_fee = st.number_input("Estimate Amount", step=500.0, key=f"d_est_{t['id']}")
                    
                    total_deduct = late_fee + fuel_fee + clean_fee + damage_fee + rfid_fee + ot_fee
                    refund_amount = max(0, 5000.0 - total_deduct)
                    
                    st.divider()
                    st.write(f"Total Deductions: -Php {total_deduct:,.2f}")
                    if (5000.0 - total_deduct) < 0: 
                        st.error(f"RENTER OWES EXTRA: Php {abs(5000.0 - total_deduct):,.2f}")
                    else: 
                        st.success(f"REFUND CASH TO RENTER: Php {refund_amount:,.2f}")

                with c2:
                    st.write("#### 🖊️ Final Sign-off")
                    c_ret1, c_ret2 = st.columns(2)
                    
                    with c_ret1:
                        if f"clr_sret_{t['id']}" not in st.session_state: st.session_state[f"clr_sret_{t['id']}"] = 0
                        s_ret = st_canvas(stroke_width=2, stroke_color="#000", background_color="#eee", height=150, width=200, display_toolbar=False, key=f"sret_{t['id']}_{st.session_state[f'clr_sret_{t['id']}']}")
                        if st.button("Clear Renter Pad", key=f"btn_sret_{t['id']}", use_container_width=True): 
                            st.session_state[f"clr_sret_{t['id']}"] += 1
                            st.rerun()
                        st.write(f"**Renter:** {t['renter_fullname']} /{t['renter_username']}")
                        
                    with c_ret2:
                        if f"clr_sreta_{t['id']}" not in st.session_state: st.session_state[f"clr_sreta_{t['id']}"] = 0
                        s_reta = st_canvas(stroke_width=2, stroke_color="#000", background_color="#eee", height=150, width=200, display_toolbar=False, key=f"sreta_{t['id']}_{st.session_state[f'clr_sreta_{t['id']}']}")
                        if st.button("Clear Partner Pad", key=f"btn_sreta_{t['id']}", use_container_width=True): 
                            st.session_state[f"clr_sreta_{t['id']}"] += 1
                            st.rerun()
                        st.write(f"**Partner:** {affiliate_full_name} /{st.session_state.username}")
                        
                    if st.button("GENERATE SETTLEMENT & COMPLETE JOURNEY", key=f"comp_{t['id']}", type="primary", use_container_width=True):
                        has_sret = s_ret.image_data is not None and len(s_ret.json_data.get("objects", [])) > 0
                        has_sreta = s_reta.image_data is not None and len(s_reta.json_data.get("objects", [])) > 0
                        
                        if not d_ok and not img_damage: 
                            st.error("Upload a damage photo to proceed.")
                        elif not (has_sret and has_sreta):
                            st.error("Both signatures are required for settlement.")
                        else:
                            b_ref_display = f"#{t['booking_ref']}" if pd.notnull(t.get('booking_ref')) else f"DRV-{t['id']:05d}"
                            
                            pdf_bytes = generate_return_receipt(b_ref_display, t['renter_fullname'], f"{t['make']} {t['model']}", t['plate'], fuel_fee, clean_fee, damage_fee, late_fee, rfid_fee, ot_fee, total_deduct, refund_amount, s_ret.image_data, s_reta.image_data)
                            
                            st.session_state[f"ret_receipt_{t['id']}"] = pdf_bytes
                            st.session_state[f"refund_{t['id']}"] = refund_amount
                            
                            if img_damage:
                                saved_paths = [save_file(img) for img in img_damage]
                                st.session_state[f"dmg_img_{t['id']}"] = ",".join(filter(None, saved_paths))
                                
                            # Emails
                            affiliate_email_df = pd.read_sql_query("SELECT email FROM users WHERE username=?", conn, params=(st.session_state.username,))
                            affiliate_email = affiliate_email_df.iloc[0]['email'] if not affiliate_email_df.empty else None
                            if t['renter_email']: send_pdf_email(t['renter_email'], f"Return Receipt: {b_ref_display}", "Attached is your settlement receipt.", pdf_bytes, f"Settlement_{b_ref_display}.pdf")
                            if affiliate_email: send_pdf_email(affiliate_email, f"Partner Copy: {b_ref_display}", "Attached is your copy.", pdf_bytes, f"Settlement_{b_ref_display}.pdf")
                            
                            st.rerun()

# --- OTHER TABS ---
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
                    INSERT INTO vehicles (owner_username, make, model, year, plate, bank_name, account_no, vehicle_img, or_cr_img, insurance_img, category, approved_price, ref_no) 
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (st.session_state.username, ma.title(), mo.title(), ye, pl.upper(), bn, an, save_file(vi), save_file(orc), save_file(ins), cat, FIXED_RATES.get(cat,0), new_ref_no))
                conn.commit()
                st.success(f"SUCCESS: Vehicle Submitted! Ref #{new_ref_no}.")
            else: 
                st.error("Please fill all required fields.")

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

with tabs[4]:
    st.markdown("<h3 style='text-align: center;'>⭐ Guest Reviews</h3>", unsafe_allow_html=True)
    query_reviews = """
        SELECT b.rating, b.review, b.pickup_time, u.full_name as renter_name, v.make, v.model, v.plate
        FROM bookings b JOIN vehicles v ON b.vehicle_id = v.id JOIN users u ON b.renter_username = u.username
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
