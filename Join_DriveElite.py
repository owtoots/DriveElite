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
# 1. PAGE CONFIG & LOGO (Must be first!)
# ==========================================
st.set_page_config(page_title="Join DriveElite", layout="wide")

# 🟢 THE NEW GUARANTEED LOGO METHOD
st.sidebar.image("logo.png", use_container_width=True)
st.sidebar.markdown("<br>", unsafe_allow_html=True) # Adds a clean gap below the logo

# ==========================================
# 💎 2. THE "CRYSTAL ELITE" CSS ENGINE
# ==========================================
st.markdown("""
<style>
    /* 1. Page Background - Cool Ice White */
    [data-testid="stAppViewContainer"] {
        background-color: #F8FAFC !important;
        color: #0F172A !important;
        font-family: 'Inter', -apple-system, sans-serif !important;
    }
    [data-testid="stHeader"] { background-color: #F8FAFC !important; }
    
    /* Ensure the Sidebar background is clean */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E2E8F0 !important;
    }

    /* 2. Size the Logo and Center it Perfectly */
    [data-testid="stLogo"] {
        height: 6.5rem !important; /* Adjust this number to make it taller/shorter */
        width: auto !important;
        max-width: 80% !important; /* Keeps it from hitting the sidebar edges */
        
        /* The Centering Engine */
        display: block !important;
        margin-top: 2rem !important;
        margin-left: auto !important; 
        margin-right: auto !important; 
        
        object-fit: contain !important; /* Ensures the image doesn't stretch weirdly */
    }

    /* Push the Menu down so it doesn't overlap the new centered logo */
    [data-testid="stSidebarNav"] {
        padding-top: 8.5rem !important; 
    }

    /* 3. Registration Cards - Pure White with Soft Shadow */
    [data-testid="stForm"], .stForm {
        background-color: #FFFFFF !important;
        padding: 40px !important;
        border-radius: 16px !important;
        border: 1px solid #E2E8F0 !important;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05) !important;
    }

    /* 4. Primary Action Buttons - Electric Blue (High Contrast) */
    div.stButton > button, [data-testid="stFormSubmitButton"] > button {
        background-color: #2563EB !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 700 !important;
        border-radius: 10px !important;
        padding: 14px 28px !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        transition: all 0.2s ease !important;
    }
    
    /* Target the text specifically inside the button to prevent "Dark Text" bug */
    div.stButton > button p, [data-testid="stFormSubmitButton"] > button p {
        color: #FFFFFF !important;
    }

    div.stButton > button:hover {
        background-color: #1D4ED8 !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
        transform: translateY(-1px) !important;
    }

    /* 5. Cleaner Input Fields */
    div[data-baseweb="input"] > div {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 10px !important;
    }
    input { color: #1E293B !important; }
    
    /* 6. Typography Fixes */
    h1, h2, h3 { color: #0F172A !important; font-weight: 800 !important; }
    label { color: #475569 !important; font-weight: 600 !important; }
    /* 🚀 THE SIDEBAR REORDER HACK */
    [data-testid="stSidebarContent"] {
        display: flex !important;
        flex-direction: column !important;
    }
    
    /* 1. Force the Logo (User Content) to the TOP */
    [data-testid="stSidebarUserContent"] {
        order: 1 !important;
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }

    /* 2. Force the Navigation Links to the BOTTOM */
    [data-testid="stSidebarNav"] {
        order: 2 !important;
        padding-top: 0rem !important; 
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. DATABASE SETUP
# ==========================================
conn = get_connection()

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
            signature_img BLOB,
            admin_status TEXT DEFAULT 'PENDING'
        )
    ''')
    conn.commit()
except: pass

# Patch for older tables to ensure they have the new columns
for col_name, col_type in [("area_code", "TEXT DEFAULT '+63'"), ("admin_status", "TEXT DEFAULT 'PENDING'")]:
    try:
        conn.execute(f"ALTER TABLE platform_users ADD COLUMN {col_name} {col_type}")
        conn.commit()
    except: pass

if not os.path.exists("uploads"):
    os.makedirs("uploads")

# ==========================================
# 4. UTILITY FUNCTIONS
# ==========================================
def crop_signature(image_data):
    gray = np.dot(image_data[...,:3], [0.2989, 0.5870, 0.1140])
    mask = gray < 200  
    coords = np.argwhere(mask)
    if coords.size > 0:
        y0, x0 = coords.min(axis=0)
        y1, x1 = coords.max(axis=0) + 1
        y0, x0, y1, x1 = max(0, y0-5), max(0, x0-5), min(image_data.shape[0], y1+5), min(image_data.shape[1], x1+5)
        return Image.fromarray(image_data[y0:y1, x0:x1].astype('uint8'), 'RGBA')
    return Image.fromarray(image_data.astype('uint8'), 'RGBA')

def send_welcome_email(recipient_email, role, filepath):
    msg = EmailMessage()
    doc_label = "MOA" if role == "AFFILIATE" else "RENTER"
    msg['Subject'] = f'DriveElite: Your Official {doc_label} Agreement'
    msg['From'] = 'rdalbaojr@gmail.com'
    msg['To'] = recipient_email
    msg['Bcc'] = 'rdalbaojr@gmail.com'

    msg.set_content(f"Hello,\n\nWelcome to DriveElite! Attached is your signed {doc_label} agreement.\n\nBest,\nThe DriveElite Team")

    with open(filepath, 'rb') as f:
        file_data = f.read()
    
    ext = 'pdf' if filepath.endswith('.pdf') else 'docx'
    msg.add_attachment(file_data, maintype='application', subtype=ext, filename=f"DriveElite_{doc_label}.{ext}")

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login('rdalbaojr@gmail.com', st.secrets["email_app_password"])
        smtp.send_message(msg)

# ==========================================
# 5. 🔐 OTP VERIFICATION SCREEN
# ==========================================
if st.session_state.get('otp_pending'):
    st.title("🔐 Account Verification")
    st.divider()
    st.info(f"An OTP has been sent to your mobile number: **{st.session_state.verify_contact}**")
    otp_input = st.text_input("Enter 6-digit OTP", key="otp_verify")
    st.caption(f"(Dev Mode: Your OTP is {st.session_state.generated_otp})")
    
    if st.button("VERIFY & FINALIZE", type="primary"):
        if otp_input == st.session_state.generated_otp:
            payload = st.session_state.reg_payload
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO platform_users 
            (username, password, role, full_name, email, age, nationality, address, area_code, contact_number, govt_id_img, license_img, signature_img) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', payload)
            conn.commit()
            
            with st.spinner("Processing documents and emailing your copy..."):
                try:
                    un, role, email = payload[0], payload[2], payload[4]
                    prefix = "MOA" if role == "AFFILIATE" else "RENTER"
                    pdf_p, docx_p = f"uploads/{prefix}_{un}.pdf", f"uploads/{prefix}_{un}.docx"
                    final_p = pdf_p if os.path.exists(pdf_p) else docx_p
                            
                    send_welcome_email(email, role, final_p)
                    st.success("✅ Account verified and agreement sent to your inbox!")
                    
                    with open(final_p, "rb") as f:
                        st.download_button("📄 DOWNLOAD SIGNED CONTRACT", f, file_name=f"DriveElite_{prefix}.pdf", type="primary")
                            
                    if os.path.exists(docx_p): os.remove(docx_p)
                    if os.path.exists(pdf_p): os.remove(pdf_p)
                                
                except Exception as e:
                    st.error(f"Account saved, but email failed: {e}")
            
            st.session_state.otp_pending = False
            if st.button("GO TO LOGIN"): st.rerun()
        else:
            st.error("🚨 Invalid OTP. Please try again.")

# ==========================================
# 6. 🚗 MAIN REGISTRATION SCREEN
# ==========================================
else:
    st.title("🚗 Join DriveElite")
    st.write("Philippines' Premier Peer-to-Peer Car Sharing Platform")
    
    reg_type = st.radio("I want to register as a:", ["Select...", "Affiliate", "Renter"], horizontal=True)
    st.divider()

    if reg_type in ["Affiliate", "Renter"]:
        step_key = f"{reg_type.lower()}_step"
        if step_key not in st.session_state: st.session_state[step_key] = 1

        # --- STEP 1: PERSONAL DETAILS ---
        if st.session_state[step_key] == 1:
            with st.form(f"reg_{reg_type}"):
                st.subheader(f"Step 1: {reg_type} Profile Details")
                c1, c2, c3 = st.columns(3)
                fn = c1.text_input("First Name").title()
                mn = c2.text_input("Middle Name").title()
                sn = c3.text_input("Surname").title()
                
                c4, c5, c6 = st.columns([3, 1, 1])
                dob = c4.date_input("Date of Birth", min_value=datetime.date(1940, 1, 1))
                age = c5.text_input("Age")
                nat = c6.text_input("Nationality", value="PH").upper()
                
                c_a, c_n = st.columns([1, 4])
                ac = c_a.text_input("Code", value="+63")
                cn = c_n.text_input("Mobile Number", placeholder="917 123 4567")
                
                em = st.text_input("Email Address")
                ad = st.text_area("Complete Physical Address")
                
                un = st.text_input("Choose Username")
                p1, p2 = st.columns(2)
                pwd = p1.text_input("Create Password", type="password")
                cpwd = p2.text_input("Confirm Password", type="password")
                
                g_id = st.file_uploader("Upload Government ID", type=['jpg', 'png', 'jpeg'])
                l_id = st.file_uploader("Upload Driver's License", type=['jpg', 'png', 'jpeg'])
                
                if st.form_submit_button("NEXT: REVIEW & SIGN AGREEMENT"):
                    if pwd != cpwd:
                        st.error("🚨 Passwords do not match.")
                    elif not all([fn, sn, un, pwd, g_id, l_id, cn, em, ad]):
                        st.error("🚨 Please fill all required fields and upload your documents.")
                    else:
                        check = pd.read_sql_query("SELECT username FROM platform_users WHERE username=?", conn, params=(un,))
                        if not check.empty:
                            st.error("🚨 Username already taken.")
                        else:
                            st.session_state[f"temp_{reg_type.lower()}_data"] = {
                                "username": un, "password": pwd, "full_name": f"{fn} {mn} {sn}".strip(), 
                                "email": em, "age": age, "nationality": nat, "address": ad, 
                                "area_code": ac, "contact": cn, "gov_id": g_id.read(), "lic_id": l_id.read()
                            }
                            st.session_state[step_key] = 2
                            st.rerun()

        # --- STEP 2: CONTRACT & SIGNATURE ---
        elif st.session_state[step_key] == 2:
            st.subheader(f"Step 2: Digital {reg_type} Agreement")
            st.info("By signing below, you agree to the DriveElite Terms of Service and Privacy Policy.")
            
            canvas = st_canvas(stroke_width=3, stroke_color="#000000", background_color="#FFFFFF", height=150, width=400, key=f"sig_{reg_type}")
            
            c_back, c_sub = st.columns([1, 4])
            if c_back.button("⬅️ BACK"):
                st.session_state[step_key] = 1
                st.rerun()

            if c_sub.button("SUBMIT REGISTRATION & SEND OTP", type="primary"):
                if canvas.image_data is not None and len(np.unique(canvas.image_data)) > 1:
                    with st.spinner("Generating legal agreement..."):
                        data = st.session_state[f"temp_{reg_type.lower()}_data"]
                        sig_cropped = crop_signature(canvas.image_data)
                        sig_buf = io.BytesIO()
                        sig_cropped.save(sig_buf, format='PNG')
                        sig_bytes = sig_buf.getvalue()
                        
                        tmpl = "moa_affiliate.docx" if reg_type == "Affiliate" else "MASTER RENTER AGREEMENT.docx"
                        doc = DocxTemplate(tmpl)
                        
                        ctx = {
                            'FULL_NAME': data['full_name'].upper(),
                            'DATE_SIGNED': datetime.date.today().strftime("%B %d, %Y"),
                            'ADDRESS': data['address'],
                            'NATIONALITY': data['nationality'].upper(),
                            'SIGNATURE': InlineImage(doc, io.BytesIO(sig_bytes), width=Mm(40))
                        }
                        doc.render(ctx)
                        
                        prefix = "MOA" if reg_type == "Affiliate" else "RENTER"
                        docx_fn = f"uploads/{prefix}_{data['username']}.docx"
                        doc.save(docx_fn)
                        
                        try: subprocess.run(['libreoffice', '--headless', '--convert-to', 'pdf', docx_fn, '--outdir', 'uploads/'], check=True)
                        except: pass
                        
                        st.session_state.reg_payload = (
                            data["username"], data["password"], reg_type.upper(), data["full_name"], 
                            data["email"], data["age"], data["nationality"], data["address"], 
                            data["area_code"], data["contact"], data["gov_id"], data["lic_id"], sig_bytes
                        )
                        st.session_state.verify_contact = data["contact"]
                        st.session_state.generated_otp = str(random.randint(100000, 999999))
                        st.session_state.otp_pending = True
                        st.rerun()
                else:
                    st.error("🚨 Digital signature required to proceed.")
