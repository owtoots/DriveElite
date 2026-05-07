from PIL import Image
import io
import streamlit as st
import pandas as pd
import random
import datetime
import os
import numpy as np
from database_utils import get_connection
from streamlit_drawable_canvas import st_canvas
import smtplib
from email.message import EmailMessage
import subprocess 

# --- THE MAGIC LIBRARY ---
from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm

# ==========================================
# PAGE CONFIG & DATABASE
# ==========================================
st.set_page_config(page_title="Join DriveElite", layout="wide")
conn = get_connection()

# --- AUTO-BUILD THE DATABASE TABLE ---
try:
    conn.execute('''
        CREATE TABLE IF NOT EXISTS platform_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT,
            full_name TEXT,
            email TEXT,
            age TEXT,
            nationality TEXT,
            address TEXT,
            area_code TEXT DEFAULT '+63',
            contact_number TEXT,
            govt_id_img BLOB,
            license_img BLOB,
            signature_img BLOB
        )
    ''')
    conn.commit()
except:
    pass

try:
    conn.execute("ALTER TABLE platform_users ADD COLUMN area_code TEXT DEFAULT '+63'")
    conn.commit()
except:
    pass

# ---> THE CORRECTED SAFE PATCH <---
try:
    conn.execute("ALTER TABLE platform_users ADD COLUMN admin_status TEXT DEFAULT 'PENDING'")
    conn.commit()
except:
    pass

# ---> FOLDER CREATION FIX <---
if not os.path.exists("uploads"):
    os.makedirs("uploads")
# ----------------------------------

# ==========================================
# UTILITY & EMAIL FUNCTIONS
# ==========================================
def crop_signature(image_data):
    """Acts as digital scissors to trim the blank space around the drawn ink."""
    gray = np.dot(image_data[...,:3], [0.2989, 0.5870, 0.1140])
    mask = gray < 200  
    
    coords = np.argwhere(mask)
    if coords.size > 0:
        y0, x0 = coords.min(axis=0)
        y1, x1 = coords.max(axis=0) + 1
        
        y0, x0 = max(0, y0-5), max(0, x0-5)
        y1, x1 = min(image_data.shape[0], y1+5), min(image_data.shape[1], x1+5)
        
        cropped = image_data[y0:y1, x0:x1]
        return Image.fromarray(cropped.astype('uint8'), 'RGBA')
    
    return Image.fromarray(image_data.astype('uint8'), 'RGBA')

def send_welcome_email(recipient_email, role, username, filepath):
    """Emails the generated Document to the user and your backup inbox."""
    msg = EmailMessage()
    doc_type = "Memorandum of Agreement" if role == "AFFILIATE" else "Master Renter Agreement"
    
    msg['Subject'] = f'DriveElite: Your Official {doc_type}'
    msg['From'] = 'rdalbaojr@gmail.com'
    msg['To'] = recipient_email
    msg['Bcc'] = 'rdalbaojr@gmail.com' # <-- This is your automated Backup Vault!

    msg.set_content(f'''Hello,
    
Welcome to DriveElite! Please find your official signed {doc_type} attached to this email.

Best regards,
The DriveElite Team''')

    with open(filepath, 'rb') as f:
        file_data = f.read()
        
    if filepath.endswith('.pdf'):
        msg.add_attachment(file_data, maintype='application', subtype='pdf', filename=f"DriveElite_{doc_type}.pdf")
    else:
        msg.add_attachment(file_data, maintype='application', subtype='vnd.openxmlformats-officedocument.wordprocessingml.document', filename=f"DriveElite_{doc_type}.docx")

    email_password = st.secrets["email_app_password"]
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login('rdalbaojr@gmail.com', email_password)
        smtp.send_message(msg)

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
            
            # 1. SAVE TO DATABASE
            cursor.execute('''INSERT INTO platform_users 
            (username, password, role, full_name, email, age, nationality, address, area_code, contact_number, govt_id_img, license_img, signature_img) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', payload)
            
            conn.commit()
            
            # 2. EMAIL AUTOMATION
            with st.spinner("Securing account and emailing your contract..."):
                try:
                    username = payload[0]
                    role = payload[2]
                    email_addr = payload[4]

                    # Find the generated file (try PDF first, fallback to DOCX)
                    doc_prefix = "MOA" if role == "AFFILIATE" else "RENTER"
                    pdf_path = f"uploads/{doc_prefix}_{username}.pdf"
                    docx_path = f"uploads/{doc_prefix}_{username}.docx"
                    
                    final_path = pdf_path if os.path.exists(pdf_path) else docx_path
                            
                    send_welcome_email(email_addr, role, username, final_path)
                    
                    st.success("✅ Verification successful! Your account is created and your contract has been emailed.")
                    
                    # --- INSTANT DOWNLOAD BUTTON ---
                    with open(final_path, "rb") as file:
                        btn = st.download_button(
                            label="📄 Download Your Signed Contract Now",
                            data=file,
                            file_name=f"DriveElite_{doc_prefix}.{'pdf' if final_path.endswith('.pdf') else 'docx'}",
                            mime="application/pdf" if final_path.endswith('.pdf') else "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            type="primary"
                        )
                            
                    # Cleanup local server memory
                    if os.path.exists(docx_path): os.remove(docx_path)
                    if os.path.exists(pdf_path): os.remove(pdf_path)
                                
                except Exception as e:
                    st.warning(f"Account created, but background email encountered an error: {e}")
            
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
                nationality = c6.text_input("Nat.", max_chars=3, value="PH").upper() 
                
                st.write("Mobile Number *")
                c_area, c_num = st.columns([1, 4])
                with c_area:
                    a_code = st.text_input("Code", value="+63", label_visibility="collapsed")
                with c_num:
                    contact = st.text_input("Number", placeholder="917 123 4567", label_visibility="collapsed")
                
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
                        user_check = pd.read_sql_query("SELECT username FROM platform_users WHERE username=?", conn, params=(username,))
                        if not user_check.empty:
                            st.error("🚨 Username taken.")
                        else:
                            full_name = f"{first_name} {middle_name} {surname}".replace("  ", " ").strip()
                            st.session_state.temp_affiliate_data = {
                                "username": username, "password": password, "full_name": full_name, "email": email,
                                "age": age, "nationality": nationality, "address": address,
                                "area_code": a_code,
                                "contact": contact, "gov_id_bytes": gov_id.read(), "lic_id_bytes": lic_id.read(),
                            }
                            st.session_state.affiliate_step = 2
                            st.rerun()

        elif st.session_state.affiliate_step == 2:
            st.write("### Step 2: Memorandum of Agreement")
            st.info("Please sign below to digitally execute your DriveElite Affiliate Memorandum of Agreement. A signed copy will be emailed to you and made available for instant download.")
            
            st.write("#### Sign to Accept")
            st.caption("Please draw your signature below. This will be saved to your profile for future booking handovers.")
            
            canvas_result = st_canvas(
                stroke_width=3, stroke_color="#000000", background_color="#f0f2f6",
                height=150, width=400, drawing_mode="freedraw", key="a_canvas",
            )
            
            c_back, c_submit = st.columns([1, 4])
            
            if c_back.button("⬅️ Back", key="a_back"):
                st.session_state.affiliate_step = 1
                st.rerun()

            if c_submit.button("Submit Registration & Send OTP", type="primary", key="a_sub"):
                if canvas_result.image_data is not None and len(np.unique(canvas_result.image_data)) > 1:
                    with st.spinner("Generating your digital PDF contract instantly..."):
                        
                        data = st.session_state.temp_affiliate_data
                        current_date = datetime.date.today().strftime("%B %d, %Y")
                        
                        # 1. Save and Crop Signature Image into Memory
                        sig_image = crop_signature(canvas_result.image_data)
                        img_byte_arr = io.BytesIO()
                        sig_image.save(img_byte_arr, format='PNG')
                        signature_bytes = img_byte_arr.getvalue() 
                        
                        # 2. GENERATE LOCAL WORD DOC
                        doc = DocxTemplate("moa_affiliate.docx")
                        
                        context = {
                            'FULL_NAME': data['full_name'].upper(),
                            'DATE_SIGNED': current_date,
                            'ADDRESS': data['address'],
                            'NATIONALITY': data['nationality'].upper(),
                            'SIGNATURE': InlineImage(doc, io.BytesIO(signature_bytes), width=Mm(40))
                        }
                        
                        
                        doc.render(context)
                        
                        # 3. Save DOCX, then CONVERT TO PDF
                        docx_filename = f"uploads/MOA_{data['username']}.docx"
                        doc.save(docx_filename)
                        
                        try:
                            subprocess.run(['libreoffice', '--headless', '--convert-to', 'pdf', docx_filename, '--outdir', 'uploads/'], check=True)
                        except Exception:
                            pass
                        
                        # 4. Set Payload and Move to OTP
                        st.session_state.reg_payload = (
                            data["username"], data["password"], 'AFFILIATE', data["full_name"], data["email"],
                            data["age"], data["nationality"], data["address"], data["area_code"], data["contact"], 
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
                
                st.write("Mobile Number *")
                c_area, c_num = st.columns([1, 4])
                with c_area:
                    a_code = st.text_input("Code", value="+63", label_visibility="collapsed")
                with c_num:
                    contact = st.text_input("Number", placeholder="917 123 4567", label_visibility="collapsed")
                
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
                        user_check = pd.read_sql_query("SELECT username FROM platform_users WHERE username=?", conn, params=(username,))
                        if not user_check.empty:
                            st.error("🚨 Username taken.")
                        else:
                            full_name = f"{first_name} {middle_name} {surname}".replace("  ", " ").strip()
                            st.session_state.temp_renter_data = {
                                "username": username, "password": password, "full_name": full_name, "email": email,
                                "age": age, "nationality": nationality, "address": address,
                                "area_code": a_code,
                                "contact": contact, "gov_id_bytes": gov_id.read(), "lic_id_bytes": lic_id.read(),
                            }
                            st.session_state.renter_step = 2
                            st.rerun()

        elif st.session_state.renter_step == 2:
            st.write("### Step 2: Master Renter Agreement")
            st.info("Please sign below to digitally execute your DriveElite Master Renter Agreement. A signed copy will be emailed to you and made available for instant download.")

            st.write("#### Sign to Accept")
            st.caption("Please draw your signature below. This will be saved to your profile for future bookings.")

            r_canvas = st_canvas(
                stroke_width=3, stroke_color="#000000", background_color="#f0f2f6",
                height=150, width=400, drawing_mode="freedraw", key="r_canvas",
            )

            c_back, c_submit = st.columns([1, 4])
            
            if c_back.button("⬅️ Back", key="r_back"):
                st.session_state.renter_step = 1
                st.rerun()

            if c_submit.button("Submit Registration & Send OTP", type="primary", key="r_sub"):
                if r_canvas.image_data is not None and len(np.unique(r_canvas.image_data)) > 1:
                    with st.spinner("Generating your digital PDF contract instantly..."):
                        
                        data = st.session_state.temp_renter_data
                        current_date = datetime.date.today().strftime("%B %d, %Y")
                        
                        # 1. Save and Crop Signature Image into Memory
                        sig_image = crop_signature(r_canvas.image_data)
                        img_byte_arr = io.BytesIO()
                        sig_image.save(img_byte_arr, format='PNG')
                        signature_bytes = img_byte_arr.getvalue() 
                        
                        # 2. GENERATE LOCAL WORD DOC
                        doc = DocxTemplate("MASTER RENTER AGREEMENT.docx")
                        
                        context = {
                            'FULL_NAME': data['full_name'].upper(),
                            'DATE_SIGNED': current_date,
                            'ADDRESS': data['address'],
                            'NATIONALITY': data['nationality'].upper(),
                            'SIGNATURE': InlineImage(doc, io.BytesIO(signature_bytes), width=Mm(40))
                        }
                        
                        doc.render(context)
                        
                        # 3. Save DOCX, then CONVERT TO PDF
                        docx_filename = f"uploads/RENTER_{data['username']}.docx"
                        doc.save(docx_filename)
                        
                        try:
                            subprocess.run(['libreoffice', '--headless', '--convert-to', 'pdf', docx_filename, '--outdir', 'uploads/'], check=True)
                        except Exception:
                            pass
                        
                        # 4. Set Payload and Move to OTP
                        st.session_state.reg_payload = (
                            data["username"], data["password"], 'RENTER', data["full_name"], data["email"],
                            data["age"], data["nationality"], data["address"], data["area_code"], data["contact"], 
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
