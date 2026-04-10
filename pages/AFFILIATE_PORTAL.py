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

conn = get_connection()

# --- DB PATCH ---
try: 
    conn.execute("ALTER TABLE users ADD COLUMN document_url TEXT")
    conn.commit()
except Exception: 
    pass

if not os.path.exists("uploads"): 
    os.makedirs("uploads")

# Utility to save uploaded images locally
def save_file(uploaded_file):
    if uploaded_file:
        path = os.path.join("uploads", uploaded_file.name)
        with open(path, "wb") as f: f.write(uploaded_file.getbuffer())
        return path
    return None

# --- PDF GENERATION ENGINES ---
def generate_contract(booking_ref, renter, vehicle, plate, chk_data, sig_r, sig_a, is_with_driver=False, driver_name=""):
    pdf = FPDF()
    pdf.add_page()
    try:
        pdf.image("logo.png", x=80, y=10, w=50)
        pdf.set_y(45) 
    except Exception: pdf.set_y(20)
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, "DRIVEELITE HANDOVER AGREEMENT", ln=True, align='C')
    pdf.set_font("Helvetica", '', 12)
    pdf.cell(0, 10, f"Ref: {booking_ref} | Date: {datetime.date.today()}", ln=True)
    pdf.cell(0, 10, f"Vehicle: {vehicle} ({plate}) | Renter: {renter}", ln=True)
    pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 12); pdf.cell(0, 10, "VERIFIED HANDOVER CHECKLIST:", ln=True)
    pdf.set_font("Helvetica", '', 11)
    for item in chk_data: pdf.cell(0, 8, f"[ OK ]  {item}", ln=True)
    current_y = pdf.get_y() + 10
    try:
        if sig_r is not None:
            Image.fromarray(sig_r.astype('uint8'), 'RGBA').convert('RGB').save("tr.jpg", "JPEG")
            pdf.image("tr.jpg", x=20, y=current_y, w=50)
        if sig_a is not None:
            Image.fromarray(sig_a.astype('uint8'), 'RGBA').convert('RGB').save("ta.jpg", "JPEG")
            pdf.image("ta.jpg", x=120, y=current_y, w=50)
    except: pass
    pdf.set_xy(20, current_y + 40); pdf.cell(50, 5, "Renter Signature", align='C')
    pdf.set_xy(120, current_y + 40); pdf.cell(50, 5, "Partner Signature", align='C')
    return pdf.output(dest="S").encode("latin-1")

def generate_return_receipt(booking_ref, renter, vehicle, plate, fuel, clean, damage, late, total_deduct, refund, sig_ret, sig_reta):
    pdf = FPDF()
    pdf.add_page()
    try:
        pdf.image("logo.png", x=80, y=10, w=50)
        pdf.set_y(45) 
    except Exception: pdf.set_y(20)
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, "DRIVEELITE RETURN & SETTLEMENT RECEIPT", ln=True, align='C')
    pdf.set_font("Helvetica", '', 12)
    pdf.cell(0, 10, f"Ref: {booking_ref} | Date: {datetime.date.today()}", ln=True)
    pdf.cell(0, 10, f"Vehicle: {vehicle} ({plate}) | Renter: {renter}", ln=True)
    pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 12); pdf.cell(0, 10, "SECURITY DEPOSIT DEDUCTIONS:", ln=True)
    pdf.set_font("Helvetica", '', 11)
    pdf.cell(0, 8, f"Fuel Replacement: Php {fuel:,.2f}", ln=True)
    pdf.cell(0, 8, f"Cleaning Penalty: Php {clean:,.2f}", ln=True)
    pdf.cell(0, 8, f"Damage Penalty: Php {damage:,.2f}", ln=True)
    pdf.cell(0, 8, f"Late Penalty: Php {late:,.2f}", ln=True)
    pdf.ln(5); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(5)
    pdf.cell(0, 8, f"Total Deductions: Php {total_deduct:,.2f}", ln=True)
    pdf.cell(0, 10, f"NET CASH REFUNDED TO RENTER: Php {refund:,.2f}", ln=True)
    current_y = pdf.get_y() + 15
    try:
        if sig_ret is not None:
            Image.fromarray(sig_ret.astype('uint8'), 'RGBA').convert('RGB').save("tret.jpg", "JPEG")
            pdf.image("tret.jpg", x=20, y=current_y, w=50)
        if sig_reta is not None:
            Image.fromarray(sig_reta.astype('uint8'), 'RGBA').convert('RGB').save("treta.jpg", "JPEG")
            pdf.image("treta.jpg", x=120, y=current_y, w=50)
    except: pass
    pdf.set_xy(20, current_y + 40); pdf.cell(50, 5, "Renter Sign-off", align='C')
    pdf.set_xy(120, current_y + 40); pdf.cell(50, 5, "Affiliate Sign-off", align='C')
    return pdf.output(dest="S").encode("latin-1")

def send_pdf_email(to_email, subject, body, pdf_bytes, filename):
    sender_email = "rdalbaojrh@gmail.com"; app_password = "f22c3FF18pr" 
    msg = MIMEMultipart()
    msg['From'] = f"DriveElite Admin <{sender_email}>"; msg['To'] = to_email; msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    part = MIMEBase('application', 'octet-stream'); part.set_payload(pdf_bytes); encoders.encode_base64(part)
    part.add_header('Content-Disposition', f"attachment; filename= {filename}"); msg.attach(part)
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587); server.starttls(); server.login(sender_email, app_password)
        server.send_message(msg); server.quit()
        return True
    except: return False

# --- PAGE SETUP ---
st.set_page_config(page_title="DriveElite Affiliate Portal", layout="wide")
if not st.session_state.get('logged_in'): st.stop()

# Get Affiliate's Real Name for the UI
aff_info = pd.read_sql_query("SELECT full_name FROM users WHERE username=?", conn, params=(st.session_state.username,))
affiliate_full_name = aff_info.iloc[0]['full_name'] if not aff_info.empty else st.session_state.username

st.markdown("<h1 style='text-align: center;'>💼 AFFILIATE COMMAND CENTER</h1>", unsafe_allow_html=True)
tabs = st.tabs(["BOOKINGS & HANDOVER", "MY ASSETS", "ADD ASSET", "ADD DRIVER", "REVIEWS"])

# --- TAB 0: BOOKINGS & SETTLEMENTS ---
with tabs[0]:
    # --- ONGOING TRIPS (SETTLEMENT SECTION) ---
    st.markdown("<h3 style='text-align: center;'>🔵 ONGOING TRIPS (Settlement & Returns)</h3>", unsafe_allow_html=True)
    ongoing = pd.read_sql_query("""
        SELECT b.id, b.vehicle_id, b.renter_username, b.booking_ref, u.full_name as renter_fullname, 
               v.make, v.model, v.plate FROM bookings b 
        JOIN vehicles v ON b.vehicle_id = v.id 
        JOIN users u ON b.renter_username = u.username 
        WHERE v.owner_username = ? AND b.status = 'ONGOING'""", conn, params=(st.session_state.username,))
    
    if ongoing.empty: st.info("No vehicles currently on the road.")
    for _, t in ongoing.iterrows():
        b_ref = t.get('booking_ref') or 'PENDING'
        with st.expander(f"🏁 #{b_ref} | RETURN & SETTLE: {t['make']} {t['model']} - {t['renter_fullname']}"):
            if f"ret_receipt_{t['id']}" in st.session_state:
                st.success(f"Settlement Complete! Refund: Php {st.session_state[f'refund_{t['id']}']:,.2f}")
                st.download_button("📥 DOWNLOAD RECEIPT", data=st.session_state[f"ret_receipt_{t['id']}"], file_name=f"Settlement_{b_ref}.pdf", use_container_width=True)
                if st.button("CLOSE BOOKING & RELEASE VEHICLE", key=f"fin_ret_{t['id']}", type="primary", use_container_width=True):
                    conn.execute("UPDATE bookings SET status = 'COMPLETED', damage_img = ? WHERE id = ?", (st.session_state.get(f"dmg_img_{t['id']}"), t['id']))
                    conn.execute("UPDATE vehicles SET booking_status = 'AVAILABLE' WHERE id = ?", (t['vehicle_id'],))
                    conn.commit()
                    st.rerun()
            else:
                col1, col2 = st.columns(2)
                with col1:
                    st.write("#### 🛠️ Assess Penalties")
                    f_ok = st.checkbox("Fuel OK", value=True, key=f"f_ok_{t['id']}")
                    f_deduct = st.number_input("Fuel Deduction (₱)", min_value=0.0, step=100.0) if not f_ok else 0.0
                    c_ok = st.checkbox("Clean OK", value=True, key=f"c_ok_{t['id']}")
                    c_deduct = st.number_input("Cleaning Fee (₱)", min_value=0.0, step=100.0) if not c_ok else 0.0
                    d_ok = st.checkbox("Damage OK", value=True, key=f"d_ok_{t['id']}")
                    d_deduct = st.number_input("Damage Deduction (₱)", min_value=0.0, step=500.0) if not d_ok else 0.0
                    d_img = st.file_uploader("Upload Damage Photos", key=f"dim_{t['id']}") if not d_ok else None
                    l_ok = st.checkbox("Late OK", value=True, key=f"l_ok_{t['id']}")
                    l_deduct = st.number_input("Late Penalty (₱)", min_value=0.0, step=100.0) if not l_ok else 0.0
                    
                    total_penalties = f_deduct + c_deduct + d_deduct + l_deduct
                    refund = max(0, 5000.0 - total_penalties)
                    st.write(f"**Total Deductions:** -₱{total_penalties:,.2f}")
                    st.success(f"**REFUND IN CASH:** ₱{refund:,.2f}")
                
                with col2:
                    st.write("#### 🖊️ Handover Sign-off")
                    sig_col1, sig_col2 = st.columns(2)
                    
                    # RENTER SIGNATURE PAD
                    with sig_col1:
                        if f"clr_sret_{t['id']}" not in st.session_state: st.session_state[f"clr_sret_{t['id']}"] = 0
                        s_ret = st_canvas(stroke_width=2, stroke_color="#000", background_color="#eee", height=150, width=200, display_toolbar=False, key=f"sret_{t['id']}_{st.session_state[f'clr_sret_{t['id']}']}")
                        if st.button("Clear Renter", key=f"btn_sret_{t['id']}", use_container_width=True):
                            st.session_state[f"clr_sret_{t['id']}"] += 1
                            st.rerun()
                        st.write(f"**Renter:** {t['renter_fullname']} / {t['renter_username']}")
                        st.caption("Renter Final Sign-off")

                    # AFFILIATE SIGNATURE PAD
                    with sig_col2:
                        if f"clr_sreta_{t['id']}" not in st.session_state: st.session_state[f"clr_sreta_{t['id']}"] = 0
                        s_reta = st_canvas(stroke_width=2, stroke_color="#000", background_color="#eee", height=150, width=200, display_toolbar=False, key=f"sreta_{t['id']}_{st.session_state[f'clr_sreta_{t['id']}']}")
                        if st.button("Clear Partner", key=f"btn_sreta_{t['id']}", use_container_width=True):
                            st.session_state[f"clr_sreta_{t['id']}"] += 1
                            st.rerun()
                        st.write(f"**Partner:** {affiliate_full_name} / {st.session_state.username}")
                        st.caption("Affiliate Final Sign-off")
                    
                    if st.button("GENERATE SETTLEMENT & COMPLETE JOURNEY", key=f"comp_{t['id']}", type="primary", use_container_width=True):
                        if not d_ok and not d_img: st.error("Damage photo required.")
                        else:
                            pdf_bytes = generate_return_receipt(b_ref, t['renter_fullname'], f"{t['make']} {t['model']}", t['plate'], f_deduct, c_deduct, d_deduct, l_deduct, total_penalties, refund, s_ret.image_data, s_reta.image_data)
                            st.session_state[f"ret_receipt_{t['id']}"] = pdf_bytes
                            st.session_state[f"refund_{t['id']}"] = refund
                            if d_img: st.session_state[f"dmg_img_{t['id']}"] = save_file(d_img)
                            st.rerun()

# --- TAB 1: ASSETS --- (Rest of your tabs follow here...)

# --- TAB 1: MY ASSETS ---
with tabs[1]:
    st.markdown("<h3 style='text-align: center;'>MY FLEET CONTROLS</h3>", unsafe_allow_html=True)
    fleet = pd.read_sql_query("SELECT id, make, model, plate, booking_status, admin_status, ref_no FROM vehicles WHERE owner_username = ?", conn, params=(username,))
    if fleet.empty: st.info("No vehicles registered.")
    for _, c in fleet.iterrows():
        v_ref = c.get('ref_no') or 'PENDING'
        with st.expander(f"🚗 #{v_ref} | {c['make']} {c['model']} ({c['plate']}) - Status: {c['booking_status']}"):
            if c['admin_status'] == 'APPROVED':
                new_status = 'UNAVAILABLE' if c['booking_status'] == 'AVAILABLE' else 'AVAILABLE'
                if st.button(f"Switch to {new_status}", key=f"sw_{c['id']}"):
                    conn.execute("UPDATE vehicles SET booking_status = ? WHERE id = ?", (new_status, c['id']))
                    conn.commit()
                    st.rerun()

# --- TAB 2: ADD ASSET ---
with tabs[2]:
    st.markdown("<h3 style='text-align: center;'>REGISTER A VEHICLE</h3>", unsafe_allow_html=True)
    with st.form("add_v"):
        cat = st.selectbox("CATEGORY", ["Sedan", "SUV", "Van", "Pickup"])
        c1, c2 = st.columns(2)
        ma = c1.text_input("MAKE (Nissan)")
        mo = c2.text_input("MODEL (Terra)")
        ye = c1.text_input("YEAR")
        pl = c2.text_input("PLATE")
        bn = c1.text_input("PAYOUT BANK")
        an = c2.text_input("ACCOUNT NUMBER")
        vi = st.file_uploader("Vehicle Photo")
        orc = st.file_uploader("OR/CR")
        ins = st.file_uploader("Insurance")
        if st.form_submit_button("SUBMIT"):
            ref = str(random.randint(100000, 999999))
            conn.execute("INSERT INTO vehicles (owner_username, make, model, year, plate, bank_name, account_no, vehicle_img, or_cr_img, insurance_img, category, ref_no) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (username, ma, mo, ye, pl, bn, an, save_file(vi), save_file(orc), save_file(ins), cat, ref))
            conn.commit()
            st.success("Submitted!")

# --- TAB 3 & 4 (STUBS FOR DRIVERS & REVIEWS) ---
with tabs[3]: st.info("Driver registration portal.")
with tabs[4]: st.info("Guest reviews will appear here.")

# --- SIDEBAR ---
with st.sidebar:
    st.write(f"### 👤 Affiliate Profile")
    st.write(f"**Fleet Owner:** {username}")
    moa_path = f"uploads/MOA_{username}.pdf"
    if os.path.exists(moa_path):
        with open(moa_path, "rb") as f:
            st.download_button("📄 Download MOA", data=f.read(), file_name=f"MOA_{username}.pdf", use_container_width=True)
    else: st.warning("No signed MOA found.")
    st.divider()
    st.caption("DriveElite 2026")
