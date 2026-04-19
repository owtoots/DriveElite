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
import streamlit.components.v1 as components
import smtplib
from email.message import EmailMessage
from googleapiclient.http import MediaIoBaseUpload
import json

# --- GOOGLE API IMPORTS ---
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ==========================================
# PAGE CONFIG & DATABASE
# ==========================================
st.set_page_config(page_title="Join DriveElite", layout="wide")
conn = get_connection()

# --- NEW: AUTO-BUILD THE DATABASE TABLE ---
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT,
        full_name TEXT,
        email TEXT,
        age TEXT,
        nationality TEXT,
        address TEXT,
        contact_number TEXT,
        govt_id_img BLOB,
        license_img BLOB,
        signature_img BLOB
    )
''')
conn.commit()
# ------------------------------------------

if not os.path.exists("uploads"): 
    os.makedirs("uploads")
# ==========================================
# UNIVERSAL GOOGLE DOC FETCH FUNCTION
# ==========================================
def get_live_google_doc(doc_id):
    """Fetches the Google Doc as HTML so it keeps all bolding, paragraphs, and spacing."""
    url = f"https://docs.google.com/document/d/{doc_id}/export?format=html"
    try:
        response = requests.get(url)
        return response.content.decode('utf-8')
    except Exception as e:
        return f"<p>Agreement terms are temporarily unavailable. Error: {e}</p>"

def generate_legal_doc_from_drive(role, username, full_name, doc_id):
    """Duplicates the Google Doc, replaces tags, and exports a perfect PDF using the VIP Token."""
    from google.oauth2.credentials import Credentials
    
    # --- AUTHENTICATION ---
    token_data = json.loads(st.secrets["google_oauth"]["token"])
    creds = Credentials.from_authorized_user_info(token_data)
    drive_service = build('drive', 'v3', credentials=creds)
    docs_service = build('docs', 'v1', credentials=creds)

    # --- DUPLICATE TEMPLATE ---
    prefix = "MOA" if role == "AFFILIATE" else "RENTER"
    copy_title = f"TEMP_{prefix}_{username}"
    copied_file = drive_service.files().copy(fileId=doc_id, body={'name': copy_title}).execute()
    new_doc_id = copied_file.get('id')

    # --- REPLACE TAGS ---
    today_date = datetime.datetime.now().strftime("%B %d, %Y")
    
    # We include every possible version of the tags found in your screenshots
    requests_payload = [
        requests_payload = [
        # MOA Tags
        {'replaceAllText': {'containsText': {'text': '{{DATE_SIGNED}}', 'matchCase': False}, 'replaceText': today_date}},
        {'replaceAllText': {'containsText': {'text': '{{AFFILIATE_FULLNAME}}', 'matchCase': False}, 'replaceText': full_name.upper()}},
        
        # RENTER Agreement Tags (Matching your new template!)
        {'replaceAllText': {'containsText': {'text': '{{renter_fullname}}', 'matchCase': False}, 'replaceText': full_name.upper()}},
        {'replaceAllText': {'containsText': {'text': '{{renter_nationality}}', 'matchCase': False}, 'replaceText': 'FILIPINO'}},
        {'replaceAllText': {'containsText': {'text': '{{renter_address}}', 'matchCase': False}, 'replaceText': 'METRO MANILA'}},
        {'replaceAllText': {'containsText': {'text': '{{date_signed}}', 'matchCase': False}, 'replaceText': today_date}},
    ]

    docs_service.documents().batchUpdate(documentId=new_doc_id, body={'requests': requests_payload}).execute()

    # --- EXPORT TO PDF ---
    request = drive_service.files().export_media(fileId=new_doc_id, mimeType='application/pdf')
    pdf_bytes = request.execute()

    # --- CLEANUP DRIVE ---
    drive_service.files().delete(fileId=new_doc_id).execute()

    return pdf_bytes

# ==========================================
# DRIVEELITE VAULT & MAILROOM FUNCTIONS
# ==========================================
def upload_to_vault(file_bytes, folder_id, filename):
    """Uploads ID bytes directly to Google Drive Vault using your personal token."""
    token_data = json.loads(st.secrets["google_oauth"]["token"])
    from google.oauth2.credentials import Credentials
    creds = Credentials.from_authorized_user_info(token_data)
    drive_service = build('drive', 'v3', credentials=creds)

    file_metadata = {'name': filename, 'parents': [folder_id]}
    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype='application/octet-stream', resumable=True)
    drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

def send_welcome_email(recipient_email, role, username, pdf_filepath):
    """Emails the generated PDF to the user and your backup inbox."""
    msg = EmailMessage()
    doc_type = "Memorandum of Agreement" if role == "AFFILIATE" else "Master Renter Agreement"
    
    msg['Subject'] = f'DriveElite: Your Official {doc_type}'
    msg['From'] = 'rdalbaojr@gmail.com'
    msg['To'] = recipient_email
    msg['Bcc'] = 'rdalbaojr@gmail.com' # Your permanent backup copy!

    msg.set_content(f'''Hello,
    
Welcome to DriveElite! Please find your official {doc_type} attached to this email.

Best regards,
The DriveElite Team''')

    # Read the PDF that your script already saved to the uploads folder
    with open(pdf_filepath, 'rb') as f:
        pdf_data = f.read()
        
    msg.add_attachment(pdf_data, maintype='application', subtype='pdf', filename=f"DriveElite_{doc_type}.pdf")

    # Send the email securely
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
            cursor.execute('''INSERT INTO users 
                              (username, password, role, full_name, email, age, nationality, address, contact_number, govt_id_img, license_img, signature_img) 
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', payload)
            conn.commit()
            
            # 2. THE AUTOMATION INJECTION (Vault + Email)
            with st.spinner("Securing IDs to Vault and emailing your contract..."):
                try:
                    username = payload[0]
                    role = payload[2]
                    email_addr = payload[4]
                    gov_id_bytes = payload[9]
                    lic_id_bytes = payload[10]

                    # Upload IDs to the Vault
                    VAULT_ID = "1Gc21xmpLvKHFB_0ta9vl-osySjLyrPD7"  
                    upload_to_vault(gov_id_bytes, VAULT_ID, f"{username}_GovID.jpg")
                    upload_to_vault(lic_id_bytes, VAULT_ID, f"{username}_License.jpg")

                    # Decide which file to look for based on role
                    pdf_prefix = "MOA" if role == "AFFILIATE" else "RENTER"
                    pdf_path = f"uploads/{pdf_prefix}_{username}.pdf"
                    
                    # SEND THE EMAIL (This uses your email_app_password from Secrets)
                    send_welcome_email(email_addr, role, username, pdf_path)
                    
                    # Cleanup local server memory
                    if os.path.exists(pdf_path):
                        os.remove(pdf_path)
                        
                except Exception as e:
                    st.warning(f"Account created, but background tasks (Vault/Email) encountered an error: {e}")

            st.success("✅ Verification successful! Your account is created and your contract has been emailed.")
            
            # Reset session state for next use
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
            
            affiliate_doc_id = "1CUT_lzsYG0M9RiLuItk8FHKg03QUZ3TXLHT9f6quR5A"
            raw_moa_html = get_live_google_doc(affiliate_doc_id)
            
            current_date = datetime.date.today().strftime("%B %d, %Y")
            affiliate_name = st.session_state.temp_affiliate_data['full_name']
            
            display_moa = raw_moa_html.replace("{{AFFILIATE_FULLNAME}}", affiliate_name.upper())
            display_moa = display_moa.replace("{affiliate_fullname}", affiliate_name.upper()) 
            
            display_moa = display_moa.replace("{{DATE_SIGNED}}", current_date)
            display_moa = display_moa.replace("{date_signed}", current_date) 

            with st.container(border=True):
                components.html(display_moa, height=400, scrolling=True)
                
            st.divider()
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
                    with st.spinner("Connecting to Google Cloud to generate your legal PDF..."):
                        try:
                            # 1. Save Signature Image
                            sig_image = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                            img_byte_arr = io.BytesIO()
                            sig_image.save(img_byte_arr, format='PNG')
                            signature_bytes = img_byte_arr.getvalue() 
                            
                            data = st.session_state.temp_affiliate_data
                            
                            # 2. Call Google Docs API
                            pdf_bytes = generate_legal_doc_from_drive("AFFILIATE", data['username'], data['full_name'], affiliate_doc_id)
                            
                            # 3. Save PDF to uploads folder
                            pdf_filename = f"uploads/MOA_{data['username']}.pdf"
                            with open(pdf_filename, "wb") as f:
                                f.write(pdf_bytes)
                                
                            # 4. Set Payload and Move to OTP
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
                            
                        except Exception as e:
                            st.error(f"Failed to connect to Google Docs API. Ensure credentials are valid. Error: {e}")
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
            
            renter_doc_id = "1bEs6dcwb5OYuerZHeAg7MAF2c1HTsP2Zk67Pg71QYj8" 
            raw_renter_html = get_live_google_doc(renter_doc_id)
            
            data = st.session_state.temp_renter_data
            current_date = datetime.date.today().strftime("%B %d, %Y")
            renter_name = data['full_name']

            display_renter = raw_renter_html.replace("{{RENTER_FULLNAME}}", renter_name.upper())
            display_renter = display_renter.replace("{{DATE_SIGNED}}", current_date)

            with st.container(border=True):
                components.html(display_renter, height=400, scrolling=True)

            st.divider()
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
                    with st.spinner("Connecting to Google Cloud to generate your legal PDF..."):
                        try:
                            # 1. Save Signature Image
                            sig_image = Image.fromarray(r_canvas.image_data.astype('uint8'), 'RGBA')
                            img_byte_arr = io.BytesIO()
                            sig_image.save(img_byte_arr, format='PNG')
                            signature_bytes = img_byte_arr.getvalue() 
                            
                            # 2. Call Google Docs API
                            pdf_bytes = generate_legal_doc_from_drive("RENTER", data['username'], data['full_name'], renter_doc_id)
                            
                            # 3. Save PDF to uploads folder
                            pdf_filename = f"uploads/RENTER_{data['username']}.pdf"
                            with open(pdf_filename, "wb") as f:
                                f.write(pdf_bytes)
                                
                            # 4. Set Payload and Move to OTP
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
                            
                        except Exception as e:
                            st.error(f"Failed to connect to Google Docs API. Ensure credentials are valid. Error: {e}")
                else:
                    st.error("🚨 Digital signature required to proceed.")
