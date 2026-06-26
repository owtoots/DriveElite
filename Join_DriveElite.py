import streamlit as st
import pandas as pd
import datetime, random, os, io
import smtplib
import sqlite3
from email.message import EmailMessage
import numpy as np
from PIL import Image
from fpdf import FPDF
from streamlit_drawable_canvas import st_canvas
from database_utils import get_connection, send_otp, send_sms_alert, send_alert_email

# ==========================================
# 1. PAGE CONFIG & LOGO (Must be first)
# ==========================================
st.set_page_config(page_title="DriveElite", layout="wide")

try:
    st.sidebar.image("logo.png", use_container_width=True)
except:
    pass

# ==========================================
# 2. THE UNIVERSAL "CRYSTAL ELITE" CSS ENGINE
# ==========================================
st.markdown("""
<style>
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stImage"] img {
        height: 200px !important;
        width: 100% !important;
        object-fit: cover !important;
        border-radius: 8px !important;
    }
    [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #F8FAFC !important;
        color: #0F172A !important;
        font-family: 'Inter', -apple-system, sans-serif !important;
    }
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E2E8F0 !important;
    }
    [data-testid="stSidebarContent"] {
        display: flex !important;
        flex-direction: column !important;
    }
    [data-testid="stSidebarUserContent"] {
        order: 1 !important;
        padding-top: 0rem !important;
        margin-top: -1.5rem !important; 
        padding-bottom: 1rem !important;
    }
    [data-testid="stSidebarNav"] {
        order: 2 !important;
        padding-top: 0rem !important; 
    }
    [data-testid="stForm"], .stForm, div[data-testid="stExpander"], div.stMetric {
        background-color: #FFFFFF !important;
        padding: 20px !important;
        border-radius: 16px !important;
        border: 1px solid #E2E8F0 !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
    }
    div.stButton > button, [data-testid="stFormSubmitButton"] > button {
        background-color: #2563EB !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 700 !important;
        border-radius: 10px !important;
        padding: 10px 24px !important;
        text-transform: uppercase !important;
        transition: all 0.2s ease !important;
    }
    div.stButton > button p, [data-testid="stFormSubmitButton"] > button p {
        color: #FFFFFF !important;
    }
    div.stButton > button:hover {
        background-color: #1D4ED8 !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
        transform: translateY(-1px) !important;
    }
    div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 8px !important;
    }
    input { color: #1E293B !important; }
    h1, h2, h3 { color: #0F172A !important; font-weight: 800 !important; }
    label { color: #475569 !important; font-weight: 600 !important; }
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

for col_name, col_type in [("area_code", "TEXT DEFAULT '+63'"), ("admin_status", "TEXT DEFAULT 'PENDING'")]:
    try:
        conn.execute(f"ALTER TABLE platform_users ADD COLUMN {col_name} {col_type}")
        conn.commit()
    except: pass

if not os.path.exists("/data/uploads"):
    os.makedirs("/data/uploads", exist_ok=True)

# ==========================================
# 4. UTILITY & PDF FUNCTIONS
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

def get_secret(key, default_val=None):
    return os.environ.get(key) or st.secrets.get(key, default_val)

def generate_signed_agreement_pdf(data, role, sig_bytes, db_conn):
    """Generates a secure, signed PDF directly using FPDF."""
    prefix = "MOA" if role.upper() == "AFFILIATE" else "RENTER"
    output_filename = f"/data/uploads/{prefix}_{data['username']}.pdf"
    
    # Fetch platform settings
    try:
        settings_df = pd.read_sql_query("SELECT renter_markup_pct, affiliate_share_pct, operator_name FROM platform_settings WHERE id = 1", db_conn)
        if not settings_df.empty:
            legal_entity = settings_df.iloc[0]['operator_name']
            owner_share_val = int(float(settings_df.iloc[0]['affiliate_share_pct']) * 100)
            agency_share_val = 100 - owner_share_val
            renter_fee_val = int(float(settings_df.iloc[0]['renter_markup_pct']) * 100)
        else:
            legal_entity, owner_share_val, agency_share_val, renter_fee_val = "DriveElite Platform", 82, 18, 7
    except:
        legal_entity, owner_share_val, agency_share_val, renter_fee_val = "DriveElite Platform", 82, 18, 7

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # --- HEADER ---
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, f"OFFICIAL DRIVEELITE {prefix} AGREEMENT", ln=True, align='C')
    pdf.ln(5)
    
    # --- BASIC DETAILS ---
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(0, 6, f"Platform: {legal_entity}", ln=True)
    pdf.cell(0, 6, f"Date: {datetime.date.today().strftime('%B %d, %Y')}", ln=True)
    pdf.cell(0, 6, f"User: {data['full_name'].upper()}", ln=True)
    pdf.cell(0, 6, f"Address: {data['address']}", ln=True)
    pdf.ln(10)
    
    # --- LEGAL TEXT GENERATOR ---
    pdf.set_font("Helvetica", '', 10)
    if role.upper() == "AFFILIATE":
        contract_text = f"""This Memorandum of Agreement (MOA) is entered into by and between {legal_entity} ("Platform") and {data['full_name'].upper()} ("Affiliate/Host").

1. REVENUE SHARING: The Affiliate agrees to a revenue sharing model where the Affiliate receives {owner_share_val}% of the base rental rate, and the Platform retains {agency_share_val}% as an administrative fee.

2. VEHICLE STANDARDS: The Affiliate is solely responsible for ensuring that all listed vehicles are fully insured, legally registered, and maintained in safe, roadworthy condition prior to any handover.

3. LIABILITIES: {legal_entity} acts strictly as an intermediary and marketplace. The Affiliate agrees to hold the Platform harmless against damages, traffic violations, or liabilities incurred by renters during active bookings.

4. PLATFORM COMPLIANCE: The Affiliate agrees to utilize the Platform's Digital Handover and Return features to officially log the start and end of all trips."""
    else:
        contract_text = f"""This Master Renter Agreement is entered into by and between {legal_entity} ("Platform") and {data['full_name'].upper()} ("Renter").

1. PLATFORM FEES & CHARGES: The Renter acknowledges and agrees to a {renter_fee_val}% platform fee applied to base rental transactions, as well as maintaining a standard security deposit of Php 5,000 for incidental charges.

2. DRIVING RESPONSIBILITY: The Renter agrees to operate the vehicle safely, strictly adhering to all Philippine traffic laws. The Renter assumes full financial responsibility for any fines, NCAP camera citations, toll liabilities, or damages incurred during the rental period.

3. USE RESTRICTIONS: The vehicle shall not be used for illegal activities, motorsport events, or off-road driving. Unless explicitly agreed upon, travel is restricted to the regions designated during checkout.

4. DIGITAL HANDOVER: The Renter agrees to physically inspect the vehicle and co-sign the Digital Handover Record alongside the Affiliate prior to departure."""

    pdf.multi_cell(0, 6, contract_text)
    pdf.ln(15)
    
    # --- SIGNATURE BLOCK ---
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, "AGREED AND DIGITALLY SIGNED:", ln=True)
    
    # Stamp the signature bytes
    sig_y = pdf.get_y()
    
    # --- NEW FIX: Save to a temp file so FPDF can read the extension ---
    temp_sig_path = f"/data/uploads/temp_sig_{data['username']}.png"
    with open(temp_sig_path, "wb") as f:
        f.write(sig_bytes)
        
    # Inject the physical file into the PDF
    pdf.image(temp_sig_path, x=10, y=sig_y, w=50)
    
    # Clean up the temp file so it doesn't clutter your server
    try:
        os.remove(temp_sig_path)
    except:
        pass
    # -------------------------------------------------------------------
    
    pdf.set_y(sig_y + 25)
    pdf.set_font("Helvetica", 'U', 10)
    pdf.cell(50, 6, data['full_name'].upper(), align='C', ln=True)
    pdf.set_font("Helvetica", '', 9)
    pdf.cell(50, 4, f"Official {role.capitalize()}", align='C')
    
    pdf.output(output_filename)
    return output_filename

def send_corporate_welcome_email(recipient_email, role, filepath):
    """Sends the signed PDF securely using the corporate DriveElite email."""
    msg = EmailMessage()
    doc_label = "MOA" if role == "AFFILIATE" else "RENTER"
    msg['Subject'] = f'DriveElite: Your Official {doc_label} Agreement'
    
    sender_email = "contact@driveelite.ph"
    admin_email = "contact@driveelite.ph"
    
    msg['From'] = f"DriveElite Team <{sender_email}>"
    msg['To'] = recipient_email
    msg['Bcc'] = admin_email

    msg.set_content(f"Hello,\n\nWelcome to DriveElite! Attached is your digitally signed {doc_label} agreement.\n\nBest,\nThe DriveElite Team")

    with open(filepath, 'rb') as f:
        file_data = f.read()
    
    msg.add_attachment(file_data, maintype='application', subtype='pdf', filename=f"DriveElite_{doc_label}.pdf")

    # Aggressively fetch password
    sender_password = None
    for key in ["EMAIL_PASSWORD", "email_password", "email_app_password"]:
        if not sender_password:
            sender_password = os.environ.get(key)
            if not sender_password:
                try: sender_password = st.secrets.get(key)
                except: pass

    if not sender_password:
        print("CRITICAL: Corporate Email password not found.")
        return False

    try:
        with smtplib.SMTP_SSL('mail.driveelite.ph', 465) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.send_message(msg)
        return True
    except Exception as e:
        print(f"Welcome Email failed: {e}")
        return False


# ==========================================
# 5. 🔐 OTP VERIFICATION SCREEN
# ==========================================
if st.session_state.get('otp_pending'):
    st.title("🔐 Account Verification")
    st.divider()
    st.info(f"An OTP has been sent to your email: **{st.session_state.reg_payload[4]}**")
    otp_input = st.text_input("Enter 6-digit OTP", key="otp_verify")
    
    if st.button("VERIFY & FINALIZE", type="primary"):
        if otp_input == st.session_state.generated_otp:
            payload = st.session_state.reg_payload
            cursor = conn.cursor()
            
            try:
                cursor.execute('''INSERT INTO platform_users 
                (username, password, role, full_name, email, age, nationality, address, area_code, contact_number, govt_id_img, license_img, signature_img) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', payload)
                
                conn.commit()
                st.success("✅ Registration Successful! You can now log in.")
                
            except sqlite3.IntegrityError:
                st.error("🚨 That Username is already taken! Please refresh and choose a different username.")
            except Exception as e:
                st.error(f"⚠️ Registration failed due to a system error: {e}")
            
            # --- ALERTS & EMAILS ---
            try:
                admin_phone = "09688811400" 
                admin_email = "contact@driveelite.ph"
                new_role = payload[2] 
                new_name = payload[3] 
                
                sms_msg = f"DriveElite Admin: A new {new_role} ({new_name}) just registered! Please review their documents."
                send_sms_alert(admin_phone, sms_msg)
                
                email_sub = f"🚨 New {new_role} Registration: {new_name}"
                email_body = f"Hello Admin,\n\nA new {new_role} named {new_name} has successfully verified their account.\n\nPlease log into the Admin Command Center to review their ID and License."
                send_alert_email(admin_email, email_sub, email_body)
            except Exception: pass
            
            with st.spinner("Processing documents and emailing your copy..."):
                try:
                    un, role, email = payload[0], payload[2], payload[4]
                    prefix = "MOA" if role == "AFFILIATE" else "RENTER"
                    final_pdf_path = f"/data/uploads/{prefix}_{un}.pdf"
                            
                    send_corporate_welcome_email(email, role, final_pdf_path)
                    st.success("✅ Account verified and Signed PDF Agreement sent to your inbox!")
                    
                    with open(final_pdf_path, "rb") as f:
                        file_bytes = f.read()
                        
                    st.download_button(
                        label="📄 DOWNLOAD SIGNED PDF CONTRACT", 
                        data=file_bytes, 
                        file_name=f"DriveElite_{prefix}_{un}.pdf", 
                        type="primary"
                    )
                                
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
    
    st.markdown("### 🚘 Live Fleet Preview")
    st.caption("Browse our exclusive fleet. Create a free Renter account to view rates and lock in your dates!")

    try:
        preview_cars = pd.read_sql_query("SELECT * FROM vehicles WHERE admin_status = 'APPROVED' AND booking_status = 'AVAILABLE'", conn)
        
        if preview_cars.empty:
            st.info("Our fleet is currently fully booked or undergoing maintenance. Check back soon!")
        else:
            preview_cars = preview_cars.head(4).reset_index(drop=True)
            grid_cols = st.columns(4)
            for i, car in preview_cars.iterrows():
                with grid_cols[i % 4]:
                    with st.container(border=True):
                        img_p = car.get('vehicle_img')
                        if img_p and os.path.exists(img_p): 
                            st.image(img_p, use_container_width=True)
                        else: 
                            st.image("https://placehold.co/600x400?text=Vehicle+Image", use_container_width=True)
                        
                        st.markdown(f"#### {car['make']} {car['model']}\n**Year:** {car['year']}")
                        st.write("") 
                        
                        if st.button("🔍 VIEW DETAILS", key=f"preview_btn_{car['id']}", use_container_width=True):
                            st.warning("🔒 Please sign up to book or view full vehicle rates.")
                            
            if len(pd.read_sql_query("SELECT id FROM vehicles WHERE admin_status = 'APPROVED'", conn)) > 4:
                st.markdown("<p style='text-align: center; color: #64748B;'><em>Sign up to explore the full DriveElite fleet...</em></p>", unsafe_allow_html=True)
                
    except Exception as e:
        pass 
        
    st.divider()
        
    # --- REGISTRATION TABS ---
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
                    with st.spinner("Generating secure PDF agreement..."):
                        data = st.session_state[f"temp_{reg_type.lower()}_data"]
                        sig_cropped = crop_signature(canvas.image_data)
                        sig_buf = io.BytesIO()
                        sig_cropped.save(sig_buf, format='PNG')
                        sig_bytes = sig_buf.getvalue()
                        
                        # ==========================================
                        # 📝 TRIGGER DIRECT PDF GENERATION
                        # ==========================================
                        pdf_filepath = generate_signed_agreement_pdf(data, reg_type, sig_bytes, conn)
                        
                        st.session_state.reg_payload = (
                            data["username"], data["password"], reg_type.upper(), data["full_name"], 
                            data["email"], data["age"], data["nationality"], data["address"], 
                            data["area_code"], data["contact"], data["gov_id"], data["lic_id"], sig_bytes
                        )
                        st.session_state.verify_contact = data["contact"]
                        
                        # --- CENTRALIZED OTP LOGIC ---
                        otp_code = str(random.randint(100000, 999999))
                        st.session_state.generated_otp = otp_code
                        
                        success = send_otp(data["contact"], data["email"], otp_code, method="EMAIL")
                        
                        if success:
                            st.session_state.otp_pending = True
                            st.rerun()
                        else:
                            st.error("🚨 Failed to send verification. Please try again.")
                else:
                    st.error("🚨 Digital signature required to proceed.")
