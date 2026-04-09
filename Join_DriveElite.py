from PIL import Image
import io
import streamlit as st
import pandas as pd
import random
import datetime
import os
import numpy as np
import requests 
from database_utils import get_connection
from streamlit_drawable_canvas import st_canvas
from fpdf import FPDF

# ==========================================
# PAGE CONFIG & DATABASE
# ==========================================
st.set_page_config(page_title="Join DriveElite", layout="wide")
conn = get_connection()

# ==========================================
# UNIVERSAL GOOGLE DOC FETCH FUNCTION
# ==========================================
def get_live_google_doc(doc_id):
    url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
    try:
        response = requests.get(url)
        # We use 'replace' to handle any hidden characters from Google Docs
        return response.content.decode('utf-8').replace('\ufeff', '')
    except Exception as e:
        return f"Agreement terms are temporarily unavailable. Error: {e}"

def clean_text_for_pdf(text):
    """Cleans Google Docs 'smart' punctuation so FPDF doesn't crash."""
    return text.replace('\u2014', '-') \
               .replace('\u2013', '-') \
               .replace('“', '"') \
               .replace('”', '"') \
               .replace('‘', "'") \
               .replace('’', "'") \
               .replace('•', '-') \
               .replace('₱', 'PhP') \
               .encode('latin-1', 'replace').decode('latin-1')

# ==========================================
# OTP VERIFICATION SCREEN
# ==========================================
if st.session_state.get('otp_pending'):
    st.title("🔐 Verification Required")
    st.divider()
    st.warning(f"📲 An OTP has been sent to your number: **{st.session_state.verify_contact}**")
    otp_input = st.text_input("Enter 6-digit OTP", key="otp_verify")
    st.caption(f"(For Testing: The OTP is {st.session_state.generated_otp})")
    
    if st.button("Verify OTP", type="primary"):
        if otp_input == st.session_state.generated_otp:
            payload = st.session_state.reg_payload
            cursor = conn.cursor()
            
            cursor.execute('''INSERT INTO users 
                              (username, password, role, full_name, email, age, nationality, address, contact_number, govt_id_img, license_img, signature_img) 
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', payload)
            
            conn.commit()
            st.success("✅ Verification successful! Your account is created. Please log in.")
            
            # Clean up session state
            for key in ['reg_payload', 'verify_contact', 'generated_otp']:
                if key in st.session_state: del st.session_state[key]
            st.session_state.otp_pending = False
            
            if st.button("Go to Login Page"):
                st.rerun()
        else:
            st.error("🚨 Invalid OTP. Please try again.")

# ==========================================
# MAIN REGISTRATION SCREEN
# ==========================================
else:
    st.title("🚗 Welcome to DriveElite")
    st.write("Join the premier peer-to-peer car rental network.")

    # The radio button controls what renders below it
    reg_type = st.radio("I want to register as a:", ["Select...", "Affiliate", "Renter"])
    st.divider()

    # ---------------------------------------------------------
    # AFFILIATE REGISTRATION BLOCK 
    # ---------------------------------------------------------
    if reg_type == "Affiliate":
        st.subheader("💼 Affiliate Partner Registration")
        
        if "affiliate_step" not in st.session_state:
            st.session_state.affiliate_step = 1

        if st.session_state.affiliate_step == 1:
            with st.form("affiliate_reg_form"):
                st.write("### Step 1: Personal & Account Details")
                c1, c2, c3 = st.columns(3)
                first_name = c1.text_input("First Name").title()
                middle_name = c2.text_input("Middle Name").title()
                surname = c3.text_input("Surname").title()
                
                c4, c5, c6, c7 = st.columns([3, 1, 1, 3])
                dob = c4.date_input("Date of Birth", min_value=datetime.date(1920, 1, 1), max_value=datetime.date.today())
                age = c5.text_input("Age", max_chars=2) 
                nationality = c6.text_input("Nat.", max_chars=3).upper() 
                contact = c7.text_input("Contact Number")
                
                email = st.text_input("Email Address *")
                address = st.text_area("Complete Home Address")
                
                username = st.text_input("Choose a Username")
                p1, p2 = st.columns(2)
                password = p1.text_input("Password", type="password")
                confirm_password = p2.text_input("Confirm Password", type="password")
                
                gov_id = st.file_uploader("Upload Valid Government ID", type=['jpg', 'png', 'jpeg'], key="a_gov")
                lic_id = st.file_uploader("Upload Driver's License/ORCR", type=['jpg', 'png', 'jpeg'], key="a_lic")
                
                if st.form_submit_button("Next: Review & Sign Contract", type="primary"):
                    if password != confirm_password:
                        st.error("🚨 Passwords do not match.")
                    elif not all([first_name, surname, username, password, gov_id, lic_id, contact, email]):
                        st.error("🚨 Please fill out all required fields.")
                    else:
                        user_check = pd.read_sql_query("SELECT username FROM users WHERE username=?", conn, params=(username,))
                        if not user_check.empty:
                            st.error("🚨 Username taken.")
                        else:
                            full_name = f"{first_name} {middle_name} {surname}".replace("  ", " ").strip()
                            st.session_state.temp_affiliate_data = {
                                "username": username, "password": password, "full_name": full_name, "email": email,
                                "age": age, "nationality": nationality, "address": address, 
                                "contact": contact, "gov_id_bytes": gov_id.read(), "lic_id_bytes": lic_id.read(),
                                "first_name": first_name, "surname": surname 
                            }
                            st.session_state.affiliate_step = 2
                            st.rerun()

        elif st.session_state.affiliate_step == 2:
            st.write("### Step 2: Memorandum of Agreement")
            
            # Fetch Live Affiliate MOA
            affiliate_doc_id = "1CUT_lzsYG0M9RiLuItk8FHKg03QUZ3TXLHT9f6quR5A"
            raw_moa_text = get_live_google_doc(affiliate_doc_id)
            
            current_date = datetime.date.today().strftime("%B %d, %Y")
            affiliate_name = f"{st.session_state.temp_affiliate_data['first_name']} {st.session_state.temp_affiliate_data['surname']}"
            
            display_moa = raw_moa_text.replace("{affiliate_fullname}", affiliate_name.upper())
            display_moa = display_moa.replace("{date_signed}", current_date)

            with st.container(height=400):
                st.markdown(display_moa)
                
            st.divider()
            st.write("#### Sign to Accept")
            st.caption("Please draw your signature below to formally execute the agreement.")
            
            canvas_result = st_canvas(
                stroke_width=3, stroke_color="#000000", background_color="#f0f2f6",
                height=150, width=400, drawing_mode="freedraw", key="a_canvas",
            )
            
            col_sign_a, col_sign_b = st.columns(2)
            col_sign_a.write(f"**OWNER:** {affiliate_name}")
            col_sign_b.write("**AGENCY:** DriveElite Platform")

            c_back, c_submit = st.columns([1, 4])
            
            if c_back.button("⬅️ Back", key="a_back"):
                st.session_state.affiliate_step = 1
                st.rerun()

            if c_submit.button("Submit Registration & Send OTP", type="primary", key="a_sub"):
                if canvas_result.image_data is not None and len(np.unique(canvas_result.image_data)) > 1:
                    sig_image = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                    img_byte_arr = io.BytesIO()
                    sig_image.save(img_byte_arr, format='PNG')
                    signature_bytes = img_byte_arr.getvalue() 
                    
                    data = st.session_state.temp_affiliate_data
                    
                    if not os.path.exists("uploads"):
                        os.makedirs("uploads") 
                        
                    # GENERATE PDF
                    pdf = FPDF()
                    pdf.add_page()
                    
                    try:
                        pdf.image("logo.png", x=10, y=10, w=40) 
                        pdf.set_y(40)
                    except:
                        pdf.set_y(20) 
                    
                    pdf.set_font("Helvetica", 'B', 16)
                    pdf.cell(0, 10, "MEMORANDUM OF AGREEMENT", ln=True, align='C')
                    pdf.ln(5)
                    pdf.set_font("Helvetica", '', 10)
                    
                    clean_moa = clean_text_for_pdf(display_moa)
                    pdf.multi_cell(0, 5, clean_moa)
                    
                    pdf.ln(10)
                    y_sig = pdf.get_y()
                    sig_image.convert('RGB').save("temp_a_sig.jpg") 
                    pdf.image("temp_a_sig.jpg", x=20, y=y_sig, w=50)
                    
                    pdf.set_xy(20, y_sig + 35)
                    pdf.set_font("Helvetica", 'B', 10)
                    pdf.cell(0, 10, f"DIGITALLY SIGNED: {affiliate_name.upper()}", ln=True)
                    
                    pdf_filename = f"uploads/MOA_{data['username']}.pdf"
                    pdf.output(pdf_filename)
                    
                    st.session_state.reg_payload = (
                        data["username"], data["password"], 'AFFILIATE', data["full_name"], data["email"],
                        data["age"], data["nationality"], data["address"], data["contact"], 
                        data["gov_id_bytes"], data["lic_id_bytes"], signature_bytes 
                    )
                    
                    st.session_state.verify_contact = data["contact"]
                    st.session_state.generated_otp = str(random.randint(100000, 999999))
                    st.session_state.otp_pending = True
                    st.session_state.affiliate_step = 1 
                    del st.session_state.temp_affiliate_data
                    st.rerun()
                else:
                    st.error("🚨 Digital signature required to proceed.")

    # ---------------------------------------------------------
    # RENTER REGISTRATION BLOCK
    # ---------------------------------------------------------
    elif reg_type == "Renter":
        st.subheader("🚙 Renter Account Setup")
        
        if "renter_step" not in st.session_state:
            st.session_state.renter_step = 1

        if st.session_state.renter_step == 1:
            with st.form("renter_reg_form"):
                st.write("### Step 1: Personal & Account Details")
                c1, c2, c3 = st.columns(3)
                first_name = c1.text_input("First Name").title()
                middle_name = c2.text_input("Middle Name").title()
                surname = c3.text_input("Surname").title()
                
                c4, c5, c6, c7 = st.columns([3, 1, 1, 3])
                dob = c4.date_input("Date of Birth", min_value=datetime.date(1920, 1, 1), max_value=datetime.date.today())
                age = c5.text_input("Age", max_chars=2) 
                nationality = c6.text_input("Nat.", max_chars=3, value="PH").upper() 
                contact = c7.text_input("Contact Number")
                
                email = st.text_input("Email Address *")
                address = st.text_area("Complete Home Address")
                
                username = st.text_input("Choose a Username")
                p1, p2 = st.columns(2)
                password = p1.text_input("Password", type="password")
                confirm_password = p2.text_input("Confirm Password", type="password")
                
                gov_id = st.file_uploader("Upload Valid Government ID", type=['jpg', 'png', 'jpeg'], key="r_gov")
                lic_id = st.file_uploader("Upload Driver's License", type=['jpg', 'png', 'jpeg'], key="r_lic")
                
                if st.form_submit_button("Next: Review & Sign Master Agreement", type="primary"):
                    if password != confirm_password:
                        st.error("🚨 Passwords do not match.")
                    elif not all([first_name, surname, username, password, gov_id, lic_id, contact, email, address]):
                        st.error("🚨 Please fill out all required fields.")
                    else:
                        user_check = pd.read_sql_query("SELECT username FROM users WHERE username=?", conn, params=(username,))
                        if not user_check.empty:
                            st.error("🚨 Username taken.")
                        else:
                            full_name = f"{first_name} {middle_name} {surname}".replace("  ", " ").strip()
                            st.session_state.temp_renter_data = {
                                "username": username, "password": password, "full_name": full_name, "email": email,
                                "age": age, "nationality": nationality, "address": address, 
                                "contact": contact, "gov_id_bytes": gov_id.read(), "lic_id_bytes": lic_id.read(),
                                "first_name": first_name, "surname": surname 
                            }
                            st.session_state.renter_step = 2
                            st.rerun()

        elif st.session_state.renter_step == 2:
            st.write("### Step 2: Master Renter Agreement")
            
            data = st.session_state.temp_renter_data
            renter_name = data['full_name'].upper()

            # Fetch Live Renter Agreement
            renter_doc_id = "1bEs6dcwb5OYuerZHeAg7MAF2c1HTsP2Zk67Pg71QYj8" 
            raw_renter_text = get_live_google_doc(renter_doc_id)
            
            display_renter = raw_renter_text.replace("{renter_fullname}", renter_name)
            display_renter = display_renter.replace("{renter_nationality}", data['nationality'])
            display_renter = display_renter.replace("{renter_address}", data['address'])

            with st.container(height=400):
                st.markdown(display_renter)

            st.divider()
            st.write("#### Sign to Accept")
            st.caption("Please draw your signature below to formally execute the agreement.")

            r_canvas = st_canvas(
                stroke_width=3, stroke_color="#000000", background_color="#f0f2f6",
                height=150, width=400, drawing_mode="freedraw", key="r_canvas",
            )
            
            col_sign_a, col_sign_b = st.columns(2)
            col_sign_a.write(f"**LESSEE:** {renter_name}")
            col_sign_b.write("**LESSOR:** DriveElite Platform")

            c_back, c_submit = st.columns([1, 4])
            
            if c_back.button("⬅️ Back", key="r_back"):
                st.session_state.renter_step = 1
                st.rerun()

            if c_submit.button("Submit Registration & Send OTP", type="primary", key="r_sub"):
                if r_canvas.image_data is not None and len(np.unique(r_canvas.image_data)) > 1:
                    sig_image = Image.fromarray(r_canvas.image_data.astype('uint8'), 'RGBA')
                    img_byte_arr = io.BytesIO()
                    sig_image.save(img_byte_arr, format='PNG')
                    signature_bytes = img_byte_arr.getvalue() 
                    
                    if not os.path.exists("uploads"):
                        os.makedirs("uploads") 
                        
                    # GENERATE PDF
                    pdf = FPDF()
                    pdf.add_page()
                    
                    try:
                        pdf.image("logo.png", x=10, y=10, w=40) 
                        pdf.set_y(40)
                    except:
                        pdf.set_y(20)
                    
                    pdf.set_font("Helvetica", 'B', 14)
                    pdf.cell(0, 10, "MASTER RENTER AGREEMENT", ln=True, align='C')
                    pdf.ln(5)
                    pdf.set_font("Helvetica", '', 10)
                    
                    clean_renter_moa = clean_text_for_pdf(display_renter)
                    pdf.multi_cell(0, 5, clean_renter_moa)
                    
                    pdf.ln(10)
                    y_sig = pdf.get_y()
                    sig_image.convert('RGB').save("temp_r_sig.jpg") 
                    pdf.image("temp_r_sig.jpg", x=20, y=y_sig, w=50)
                    
                    pdf.set_xy(20, y_sig + 35)
                    pdf.set_font("Helvetica", 'B', 10)
                    pdf.cell(0, 10, f"DIGITALLY SIGNED: {renter_name}", ln=True)
                    
                    pdf_filename = f"uploads/RENTER_{data['username']}.pdf"
                    pdf.output(pdf_filename)
                    
                    st.session_state.reg_payload = (
                        data["username"], data["password"], 'RENTER', data["full_name"], data["email"],
                        data["age"], data["nationality"], data["address"], data["contact"], 
                        data["gov_id_bytes"], data["lic_id_bytes"], signature_bytes 
                    )
                    
                    st.session_state.verify_contact = data["contact"]
                    st.session_state.generated_otp = str(random.randint(100000, 999999))
                    st.session_state.otp_pending = True
                    st.session_state.renter_step = 1 
                    del st.session_state.temp_renter_data
                    st.rerun()
                else:
                    st.error("🚨 Digital signature required to proceed.")
