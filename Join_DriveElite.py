from PIL import Image
import io
import streamlit as st
import pandas as pd
import random
import datetime
import os
import numpy as np
import requests # Added for Google Doc Call
from database_utils import get_connection
from streamlit_drawable_canvas import st_canvas
from fpdf import FPDF

# Connect to database
conn = get_connection()

# ==========================================
# NEW: GOOGLE DOC FETCH FUNCTION
# ==========================================
def get_live_moa_text():
    # Your specific Google Doc ID
    doc_id = "1CUT_lzsYG0M9RiLuItk8FHKg03QUZ3TXLHT9f6quR5A"
    url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
    try:
        response = requests.get(url)
        # We use 'replace' to handle any hidden characters from Google Docs
        return response.content.decode('utf-8').replace('\ufeff', '')
    except Exception as e:
        return f"Agreement terms are temporarily unavailable. Error: {e}"

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
                
                gov_id = st.file_uploader("Upload Valid Government ID", type=['jpg', 'png', 'jpeg'])
                lic_id = st.file_uploader("Upload Driver's License", type=['jpg', 'png', 'jpeg'])
                
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
            
            # FETCH LIVE CONTENT FROM GOOGLE DOC
            raw_moa_text = get_live_moa_text()
            
            # REPLACE PLACEHOLDERS
            current_date = datetime.date.today().strftime("%B %d, %Y")
            affiliate_name = f"{st.session_state.temp_affiliate_data['first_name']} {st.session_state.temp_affiliate_data['surname']}"
            
            # This makes the MOA personalized on screen
            display_moa = raw_moa_text.replace("{affiliate_fullname}", affiliate_name.upper())
            display_moa = display_moa.replace("{date_signed}", current_date)

            with st.container(height=400):
                st.markdown(display_moa)
                
            st.divider()
            st.write("#### Sign to Accept")
            st.caption("Please draw your signature below to formally execute the agreement.")
            
            canvas_result = st_canvas(
                stroke_width=3, stroke_color="#000000", background_color="#f0f2f6",
                height=150, width=400, drawing_mode="freedraw", key="canvas",
            )
            
            col_sign_a, col_sign_b = st.columns(2)
            col_sign_a.write(f"**OWNER:** {affiliate_name}")
            col_sign_b.write("**AGENCY:** DriveElite Platform")

            c_back, c_submit = st.columns([1, 4])
            
            if c_back.button("⬅️ Back"):
                st.session_state.affiliate_step = 1
                st.rerun()

            if c_submit.button("Submit Registration & Send OTP", type="primary"):
                if canvas_result.image_data is not None and len(np.unique(canvas_result.image_data)) > 1:
                    # 1. Grab the signature from the canvas
                    sig_image = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                    img_byte_arr = io.BytesIO()
                    sig_image.save(img_byte_arr, format='PNG')
                    signature_bytes = img_byte_arr.getvalue() 
                    
                    data = st.session_state.temp_affiliate_data
                    
                    # ==========================================
                    # 🎨 START OF PDF GENERATION
                    # ==========================================
                    if not os.path.exists("uploads"):
                        os.makedirs("uploads") # Create folder if it doesn't exist
                        
                    pdf = FPDF()
                    pdf.add_page()
                    
                    # A. Add the DriveElite Logo
                    try:
                        pdf.image("logo.png", x=10, y=10, w=40) 
                        pdf.set_y(40)
                    except:
                        pdf.set_y(20) # Fallback if logo is missing
                    
                    # B. Main Title (Bold)
                    pdf.set_font("Helvetica", 'B', 16)
                    pdf.cell(0, 10, "MEMORANDUM OF AGREEMENT", ln=True, align='C')
                    pdf.ln(5)
                    
                    # C. The Body Text
                    pdf.set_font("Helvetica", '', 10)
                    
                    # Clean up Google Docs "Smart" characters so FPDF doesn't crash
                    clean_moa = display_moa.replace('\u2014', '-') \
                                           .replace('\u2013', '-') \
                                           .replace('“', '"') \
                                           .replace('”', '"') \
                                           .replace('‘', "'") \
                                           .replace('’', "'") \
                                           .replace('•', '-') \
                                           .replace('₱', 'PhP')
                    
                    # Catch-all: forces remaining weird symbols to a safe format
                    clean_moa = clean_moa.encode('latin-1', 'replace').decode('latin-1')
                    
                    # Print the clean text into the PDF
                    pdf.multi_cell(0, 5, clean_moa)
                    
                    # D. Stamp Signature at the bottom
                    pdf.ln(10)
                    y_sig = pdf.get_y()
                    
                    # Save a quick temp JPG for the PDF to read
                    sig_image.convert('RGB').save("temp_sig.jpg") 
                    pdf.image("temp_sig.jpg", x=20, y=y_sig, w=50)
                    
                    pdf.set_xy(20, y_sig + 35)
                    pdf.set_font("Helvetica", 'B', 10)
                    pdf.cell(0, 10, f"DIGITALLY SIGNED: {affiliate_name.upper()}", ln=True)
                    
                    # E. Save the final PDF
                    pdf_filename = f"uploads/MOA_{data['username']}.pdf"
                    pdf.output(pdf_filename)
                    # ==========================================
                    
                    # 2. Prepare Database Payload
                    st.session_state.reg_payload = (
                        data["username"], data["password"], 'AFFILIATE', data["full_name"], data["email"],
                        data["age"], data["nationality"], data["address"], data["contact"], 
                        data["gov_id_bytes"], data["lic_id_bytes"], signature_bytes 
                    )
                    
                    # 3. Trigger OTP Screen
                    st.session_state.verify_contact = data["contact"]
                    st.session_state.generated_otp = str(random.randint(100000, 999999))
                    st.session_state.otp_pending = True
                    st.session_state.affiliate_step = 1 
                    del st.session_state.temp_affiliate_data
                    st.rerun()
                else:
                    st.error("🚨 Digital signature required to proceed.")

# THIS IS THE CRITICAL LINE THAT CREATES THE VARIABLES
renter_tab, affiliate_tab = st.tabs(["🚙 REGISTER AS RENTER", "🤝 JOIN AS AFFILIATE (CAR OWNER)"])

# ==========================================
# TAB 1: RENTER REGISTRATION
# ==========================================
with renter_tab:
    st.markdown("### 📝 Renter Account Setup")
    
    # ... your existing renter code continues here ...
    
    col1, col2 = st.columns(2)
    with col1:
        r_username = st.text_input("Choose Username *", key="r_user")
        r_password = st.text_input("Choose Password *", type="password", key="r_pass")
        r_name = st.text_input("Full Legal Name *", key="r_name")
    with col2:
        r_address = st.text_input("Complete Home Address *", key="r_add")
        r_citizenship = st.text_input("Citizenship *", value="Filipino", key="r_cit")
        r_license = st.text_input("Driver's License Number *", key="r_lic")

    # Master Agreement for Renters
    renter_agreement_text = f"""
    MASTER RENTER AGREEMENT
    DriveElite Peer-to-Peer Car Rentals
    
    KNOW ALL MEN BY THESE PRESENTS:
    This agreement is made by {r_name.upper()} (the "LESSEE"), a citizen of {r_citizenship}, residing at {r_address}.
    
    1. GENERAL TERMS
    The LESSEE agrees to abide by the rules of the DriveElite platform for all future vehicle bookings. 
    The LESSEE shall use the subject vehicles for personal purposes only and within the Luzon region exclusively.
    
    2. PENALTIES AND MISUSE (ANNEX C)
    - Missing RFID or Keys will result in replacement penalties (PHP 500 to PHP 15,000).
    - Smoking inside any vehicle incurs a strict penalty up to PHP 5,000.
    - Inter-island trips, off-roading, or driving through floods is strictly prohibited (Maximum Penalty: PHP 50,000.00).
    - In case of total loss or theft, the LESSEE is responsible for 30% of the Fair Market Value of the vehicle.
    """

    st.markdown("#### 📄 Master Renter Agreement & Terms")
    with st.expander("Read Master Agreement"):
        st.write(renter_agreement_text)

    st.write("**Draw your signature to accept terms and register:**")
    r_canvas = st_canvas(
        stroke_width=2, stroke_color="#000", background_color="#EEE",
        height=150, width=400, drawing_mode="freedraw", key="r_canvas"
    )

    if st.button("SIGN & REGISTER AS RENTER", type="primary", use_container_width=True):
        if not (r_username and r_password and r_name and r_address):
            st.warning("Please fill out all required fields.")
        elif r_canvas.image_data is None:
            st.warning("Please sign the document before submitting.")
        else:
            with st.spinner("Generating Renter Profile and saving PDF..."):
                # GENERATE PDF
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=11)
                for line in renter_agreement_text.split('\n'):
                    pdf.cell(200, 7, txt=line, ln=True)
                pdf.ln(10)
                pdf.cell(200, 7, txt=f"Digitally Signed by: {r_name} on {datetime.date.today()}", ln=True)
                
                # IN A REAL APP: Upload pdf_bytes to Google Drive here and get the URL
                pdf_bytes = pdf.output(dest='S').encode('latin-1') 
                fake_drive_url = "https://drive.google.com/renter_agreement_placeholder"

                # SAVE TO DATABASE
                try:
                    conn.execute("""
                        INSERT INTO users (username, password, role, full_name, address, document_url, admin_status) 
                        VALUES (?, ?, 'RENTER', ?, ?, ?, 'APPROVED')
                    """, (r_username, r_password, r_name, r_address, fake_drive_url))
                    conn.commit()
                    st.success("✅ Registration Successful! You can now log into the DriveElite Showroom.")
                except Exception as e:
                    st.error("Username might already exist. Please try another.")
