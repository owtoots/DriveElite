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

# --- DB PATCH (Ensuring V2 Compliance) ---
try: 
    conn.execute("ALTER TABLE platform_users ADD COLUMN document_url TEXT")
    conn.commit()
except Exception: 
    pass

if not os.path.exists("uploads"): 
    os.makedirs("uploads")

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
    """Saves a chat image and returns the file path."""
    if uploaded_file:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chat_{booking_ref}_{timestamp}_{uploaded_file.name}"
        path = os.path.join("uploads", filename)
        with open(path, "wb") as f: f.write(uploaded_file.getbuffer())
        return path
    return ""

def send_pdf_email(to_email, subject, body, pdf_bytes, filename):
    sender_email = "rdalbaojr@gmail.com" # CORRECTED EMAIL (No 'h')
    try:
        app_password = st.secrets["email_app_password"] 
    except KeyError:
        return False
        
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

def send_handover_receipt(to_email, renter_name, car_name, ref_no, checklist, signature):
    """Generates and emails the simple Handover Checklist receipt."""
    sender_email = "rdalbaojr@gmail.com" # CORRECTED EMAIL (No 'h')
    try:
        app_password = st.secrets["email_app_password"]
    except KeyError:
        return False, "Missing App Password in Secrets."
        
    msg = MIMEMultipart()
    msg['Subject'] = f"DriveElite: Vehicle Handover Receipt (#{ref_no})"
    msg['From'] = f"DriveElite Handover <{sender_email}>"
    msg['To'] = to_email
    
    body = f"""Hello {renter_name},
    
Your vehicle ({car_name}) has been officially handed over and your trip has started!

--- 📋 OFFICIAL HANDOVER CHECKLIST ---
⛽ Fuel Level: {checklist['fuel']}
🚘 Exterior Inspected (No Unreported Damage): {'✅ Yes' if checklist['ext'] else '❌ No'}
✨ Interior Clean & Odor-Free: {'✅ Yes' if checklist['int'] else '❌ No'}
🔧 Spare Tire & Tools Present: {'✅ Yes' if checklist['tools'] else '❌ No'}

🖋️ Electronically Signed By: {signature}
---------------------------------------

Please drive safely. Remember to return the vehicle with the exact same fuel level to avoid penalties.
"""
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, app_password)
            smtp.send_message(msg)
        return True, "Email sent successfully"
    except Exception as e:
        return False, str(e)

# --- PDF ENGINES ---
def generate_booking_itinerary(booking_ref, renter_name, vehicle_info, total_paid, affiliate_name):
    pdf = FPDF()
    pdf.add_page()
    try:
        pdf.image("logo.png", x=80, y=10, w=50)
        pdf.set_y(45) 
    except Exception: 
        pdf.set_y(20)
        
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(0, 10, "DRIVEELITE BOOKING ITINERARY & PAYMENT SUMMARY", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Helvetica", '', 11)
    pdf.cell(0, 8, f"Booking Ref No: {booking_ref}", ln=True)
    pdf.cell(0, 8, f"Customer Name: {renter_name}", ln=True)
    pdf.cell(0, 8, f"Vehicle Info: {vehicle_info}", ln=True)
    pdf.cell(0, 8, f"Date Issued: {datetime.date.today().strftime('%B %d, %Y')}", ln=True)
    pdf.ln(8)
    
    platform_fee = float(total_paid) * 0.18
    rental_fee = float(total_paid) * 0.82
    
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, "PAYMENT BREAKDOWN:", ln=True)
    pdf.set_font("Helvetica", '', 11)
    pdf.cell(140, 8, f"Vehicle Rental (Collected on behalf of {affiliate_name}):")
    pdf.cell(0, 8, f"Php {rental_fee:,.2f}", ln=True, align='R')
    pdf.cell(140, 8, "DriveElite Platform Service Fee:")
    pdf.cell(0, 8, f"Php {platform_fee:,.2f}", ln=True, align='R')
    pdf.line(10, pdf.get_y() + 2, 200, pdf.get_y() + 2)
    pdf.ln(5)
    
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(140, 10, "TOTAL AMOUNT CHARGED:")
    pdf.cell(0, 10, f"Php {float(total_paid):,.2f}", ln=True, align='R')
    pdf.ln(15)
    pdf.set_font("Helvetica", 'I', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 5, f"Disclaimer: DriveElite operates strictly as a marketplace facilitator. Official BIR Receipts for the 'Vehicle Rental' portion must be requested directly from the Vehicle Owner ({affiliate_name}).")
    return pdf.output(dest="S").encode("latin-1")

# (Assuming generate_contract and generate_return_receipt are still in a separate file or you paste them here)

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

# --- TAB 0: BOOKINGS & HANDOVER ---
with tabs[0]: 
    st.header("📦 Active Bookings & Handovers")
    st.write("Manage your upcoming deliveries, chat with renters, and log your handovers.")
    
    affiliate_user = st.session_state.username
    
    # MASTER QUERY: Pulls everything that is NOT completed/cancelled
    query = """
        SELECT b.*, v.make, v.model, v.plate, r.full_name as renter_name, r.contact_number as renter_contact, r.email as renter_email
        FROM bookings b
        JOIN vehicles v ON b.vehicle_id = v.id
        JOIN platform_users r ON b.renter_username = r.username
        WHERE v.owner_username = ? AND b.status NOT IN ('COMPLETED', 'CANCELLED')
        ORDER BY b.pickup_time ASC
    """
    
    try:
        my_bookings = pd.read_sql_query(query, conn, params=(affiliate_user,))
        
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
                        except:
                            st.caption("No messages yet.")

                    c_img, c_msg = st.columns([1, 4])
                    with c_img:
                        a_img = st.file_uploader("📷", type=['jpg','png','jpeg'], key=f"a_img_{b['id']}", label_visibility="collapsed")
                    with c_msg:
                        a_input = st.text_input("Reply...", key=f"a_in_{b['id']}")

                    if st.button("Send", key=f"a_btn_{b['id']}", use_container_width=True):
                        if a_input or a_img:
                            path = save_chat_image(a_img, b['booking_ref']) if a_img else ""
                            text = a_input if a_input else "📸 Sent a photo."
                            try:
                                conn.execute("INSERT INTO chat_messages (booking_ref, sender_username, receiver_username, message_text, image_path) VALUES (?, ?, ?, ?, ?)", (b['booking_ref'], st.session_state.username, b['renter_username'], text, path))
                                conn.commit()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to send message: {e}")
                                
                    st.divider()

                    # --- PHASE 1: HANDOVER LOGIC (PENDING/CONFIRMED) ---
                    if b['status'] == 'PENDING' or b['status'] == 'CONFIRMED':
                        st.info("🚨 **ACTION REQUIRED:** Complete the Handover Checklist to release the vehicle.")
                        
                        with st.expander("📋 Official Handover Checklist", expanded=True):
                            st.write("Ensure both the Affiliate and Renter agree on the vehicle's condition.")
                            c_fuel = st.selectbox("Current Fuel Level", ["Full", "3/4", "1/2", "1/4", "Empty"], key=f"fuel_{b['id']}")
                            c_ext = st.checkbox("Exterior inspected and documented (Photos taken)", value=True, key=f"ext_{b['id']}")
                            c_int = st.checkbox("Interior is clean and odor-free", value=True, key=f"int_{b['id']}")
                            c_tools = st.checkbox("Spare tire, jack, and tools are present", value=True, key=f"tools_{b['id']}")
                            
                            st.divider()
                            r_sig = st.text_input("Renter's Digital Signature (Type Full Name to Agree)", key=f"sig_{b['id']}")
                            
                            if st.button("🔑 LOG HANDOVER & EMAIL RECEIPT", key=f"start_{b['id']}", type="primary", use_container_width=True):
                                if not r_sig:
                                    st.error("⚠️ The Renter must type their name to electronically sign.")
                                else:
                                    conn.execute("UPDATE bookings SET status = 'ONGOING' WHERE id = ?", (b['id'],))
                                    conn.commit()
                                    
                                    if b['renter_email']:
                                        chk_data = {'fuel': c_fuel, 'ext': c_ext, 'int': c_int, 'tools': c_tools}
                                        car_display = f"{b['make']} {b['model']} ({b['plate']})"
                                        success, msg = send_handover_receipt(b['renter_email'], b['renter_name'], car_display, b['booking_ref'], chk_data, r_sig)
                                        if success: st.toast("📧 Handover receipt sent to renter!", icon="✅")
                                        
                                    st.success("✅ Handover complete! Trip officially started. Drive safely.")
                                    time.sleep(2)
                                    st.rerun()

                    # --- PHASE 2: RETURN & SETTLEMENT LOGIC (ONGOING) ---
                    elif b['status'] == 'ONGOING':
                        st.warning("⏱️ This trip is currently active. Use the form below to process the return.")
                        
                        c1, c2 = st.columns(2)
                        with c1:
                            st.write("#### 🛠️ Agreement Penalties")
                            l_ok = st.checkbox("Returned on Time", value=True, key=f"l_{b['id']}")
                            late_fee = st.number_input("Hours Late (Php 300/hr)", min_value=1, step=1, key=f"l_hrs_{b['id']}") * 300.0 if not l_ok else 0.0
                            
                            f_ok = st.checkbox("Fuel Full", value=True, key=f"f_{b['id']}")
                            fuel_fee = (st.number_input("Refuel Receipt (Php)", step=100.0, key=f"f_cost_{b['id']}") + 200.0) if not f_ok else 0.0
                            
                            d_ok = st.checkbox("No Damage Found", value=True, key=f"d_{b['id']}")
                            damage_fee = 0.0
                            img_damage = None
                            if not d_ok:
                                img_damage = st.file_uploader("Upload Damage Photos", type=['jpg','png'], accept_multiple_files=True, key=f"p_dam_{b['id']}")
                                damage_fee = st.number_input("Estimated Damage Amount", step=500.0, key=f"d_est_{b['id']}")
                                
                            total_deduct = late_fee + fuel_fee + damage_fee
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
                                    
                                    # Marks it completed and requests payout!
                                    conn.execute("UPDATE bookings SET status = 'COMPLETED', payout_status = 'PENDING', damage_img = ? WHERE id = ?", (d_img_path, b['id']))
                                    conn.execute("UPDATE vehicles SET booking_status = 'AVAILABLE' WHERE id = ?", (b['vehicle_id'],))
                                    conn.commit()
                                    
                                    st.success("Car returned! Payout request sent to Admin Master Ledger.")
                                    time.sleep(2)
                                    st.rerun()
                                    
    except Exception as e:
        st.error(f"System Error: {e}")

# --- MY ASSETS & OTHER TABS REMAIN UNCHANGED BELOW ---
# (Tabs 1, 2, 3, 4 and Sidebar are working perfectly based on your paste)
