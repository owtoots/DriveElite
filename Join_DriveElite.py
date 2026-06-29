import streamlit as st
import pandas as pd
import datetime, random, os, io
import smtplib
import sqlite3
from email.message import EmailMessage
import numpy as np
from PIL import Image
from streamlit_drawable_canvas import st_canvas
from database_utils import get_connection
from database_utils import send_otp
from fpdf import FPDF

# ==========================================
# 1. INITIALIZE SESSION STATE (MUST BE FIRST)
# ==========================================
if "current_page" not in st.session_state:
    st.session_state.current_page = "JOIN"

# ==========================================
# 2. CATCH MAGIC LINKS
# ==========================================
query_params = st.query_params
if "portal" in query_params:
    target_page = query_params["portal"].upper()
    if st.session_state.current_page != target_page:
        st.session_state.current_page = target_page

# ==========================================
# 3. PAGE CONFIGURATION & CSS
# ==========================================
st.set_page_config(page_title="DriveElite", layout="wide")

try:
    st.sidebar.image("logo.png", use_container_width=True)
except:
    pass

st.markdown("""
<style>
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stImage"] img {
        height: 200px !important;
        width: 100% !important;
        object-fit: cover !important;
        border-radius: 8px !important;
    }
    /* Force the sidebar toggle to be more visible */
    [data-testid="stSidebarCollapse"] {
        background-color: rgba(255, 255, 255, 0.8) !important;
        border: 2px solid #2563EB !important;
        border-radius: 50% !important;
        padding: 10px !important;
        color: #2563EB !important;
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
# 4. NAVIGATION ROUTER
# ==========================================
# If they are supposed to be somewhere else, redirect them!
if st.session_state.current_page != "JOIN":
    
    if st.session_state.current_page == "AFFILIATE":
        import affiliate 
        affiliate.main() 
        st.stop() # CRITICAL: Stops the Join page from loading underneath
        
    elif st.session_state.current_page == "RENTER":
        import Renter_Portal # <--- Updated to match your exact file name
        Renter_Portal.main() 
        st.stop()
        
    elif st.session_state.current_page == "ADMIN":
        import ADMIN_PORTAL 
        ADMIN_PORTAL.main() 
        st.stop()

# ==========================================
# 5. DATABASE SETUP
# ==========================================
# (The rest of your database code starting with conn = get_connection() stays exactly the same)

# ==========================================
# 2. DATABASE SETUP
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

if not os.path.exists("uploads"):
    os.makedirs("/data/uploads", exist_ok=True)

# ==========================================
# 3. UTILITY FUNCTIONS
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

def send_welcome_email(recipient_email, role, filepath):
    msg = EmailMessage()
    doc_label = "MOA" if role == "AFFILIATE" else "RENTER"
    msg['Subject'] = f'DriveElite: Your Official {doc_label} Agreement'
    
    sender_email = get_secret("email_sender", "contact@driveelite.ph")
    msg['From'] = f"DriveElite Team <{sender_email}>"
    msg['To'] = recipient_email
    msg['Bcc'] = sender_email

    msg.set_content(f"Hello,\n\nWelcome to DriveElite! Attached is your signed {doc_label} agreement.\n\nBest,\nThe DriveElite Team")

    with open(filepath, 'rb') as f:
        file_data = f.read()
    
    msg.add_attachment(file_data, maintype='application', subtype='pdf', filename=f"DriveElite_{doc_label}.pdf")

    try:
        app_password = "chcskxti6hc2d7ao"
            
        with smtplib.SMTP_SSL('mail.driveelite.ph', 465) as smtp:
            smtp.login(sender_email, app_password)
            smtp.send_message(msg)
    except Exception as e:
        raise Exception(f"SMTP Error: {e}")

# ==========================================
# 📄 UNIFIED PDF ENGINE
# ==========================================
def create_legit_pdf_contract(data, role, sig_bytes, conn):
    is_affiliate = role.upper() == "AFFILIATE"
    prefix = "MOA" if is_affiliate else "RENTER"
    pdf_filename = f"/data/uploads/{prefix}_{data['username']}.pdf"
    
    try:
        settings_df = pd.read_sql_query("SELECT renter_markup_pct, affiliate_share_pct, operator_name FROM platform_settings WHERE id = 1", conn)
        if not settings_df.empty:
            legal_entity = settings_df.iloc[0]['operator_name']
            owner_share_val = f"{int(float(settings_df.iloc[0]['affiliate_share_pct']) * 100)}%"
            agency_share_val = f"{100 - int(float(settings_df.iloc[0]['affiliate_share_pct']) * 100)}%"
            renter_fee_val = f"{int(float(settings_df.iloc[0]['renter_markup_pct']) * 100)}%"
        else:
            legal_entity, owner_share_val, agency_share_val, renter_fee_val = "DriveElite Platform", "82%", "18%", "7%"
    except:
        legal_entity, owner_share_val, agency_share_val, renter_fee_val = "DriveElite Platform", "82%", "18%", "7%"

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    date_str = datetime.date.today().strftime("%B %d, %Y")
    
    pdf.set_font("Helvetica", 'B', 14)
    if is_affiliate:
        pdf.cell(0, 10, "MEMORANDUM OF AGREEMENT", ln=True, align='C')
        pdf.set_font("Helvetica", 'B', 10)
        pdf.cell(0, 6, "DriveElite, a Peer-to-Peer Car Rentals", ln=True, align='C')
        pdf.ln(5)
        
        pdf.set_font("Helvetica", '', 8)
        body_text = f"""This Memorandum of Agreement (the "Agreement") is made and entered into this {date_str} upon digital acceptance by and between:

{legal_entity}, a business operating under the laws of the Republic of the Philippines, with its registered address in Pasig City, Metro Manila, hereinafter referred to as the "AGENCY",

-and-

{data['full_name'].upper()}, of legal age, resident of {data['address']}, whose identity and details are provided and verified through the DriveElite platform registration, hereinafter referred to as the "OWNER".

WITNESSETH: That-
WHEREAS, the OWNER is the registered owner of a vehicle or fleet of vehicles intended for leasing services and desires to engage the services of the AGENCY to market and finalize bookings on the DriveElite platform;
WHEREAS, the AGENCY operates strictly as an online marketplace facilitator connecting vehicle owners with renters. The AGENCY is not a party to the physical rental agreement, nor does it own, operate, or maintain any of the listed vehicles;
WHEREAS, the AGENCY has accepted the said engagement subject to the terms and conditions of this Agreement;
NOW, THEREFORE, for and in consideration of the foregoing premises, the parties agree as follows:

1. EXCLUSIVE RIGHT TO MARKET AND NON-COMPETE 
a. Exclusive Right: The OWNER engages the AGENCY as the exclusive marketer for any and all vehicles activated by the OWNER on the DriveElite Affiliate Dashboard. 
b. Non-Compete: The OWNER shall not make any direct bookings with clients referred by the AGENCY or market similar services to said clients. This prohibition lasts for the term of this Agreement plus two (2) years. Violations incur liquidated damages of PHP 200,000 per transaction.

2. OBLIGATIONS OF THE OWNER 
a. Vehicle Quality: Vehicles must be turned over in a clean, sanitized, and roadworthy condition. 
b. Fulfillment: Once a renter confirms a booking, the OWNER is strictly obligated to fulfill it. 
c. Penalties: Failure to fulfill a confirmed booking results in a PHP 3,000 penalty. If the OWNER fails to notify the AGENCY of unavailability in time, an additional PHP 3,000 penalty plus replacement costs shall apply. 
d. Driver Liability: Any driver provided is the sole employee/agent of the OWNER. The AGENCY holds no employer-employee relationship and zero liability for accidents or violations caused by the driver.

3. COMPENSATION, TAXES, AND DELIVERY FEES 
a. Revenue Split: The Gross Rental Revenue (excluding delivery/logistics fees) shall be shared directly as follows:
- OWNER Share: {owner_share_val}
- AGENCY Share: {agency_share_val}
- Tax Independence & EWT: The AGENCY is not a withholding agent for the OWNER. The AGENCY shall only declare and pay taxes on its own {agency_share_val} commission. The OWNER receives their full {owner_share_val} share (less gateway fees) and assumes 100% legal and financial responsibility for filing, declaring, and paying their own taxes-including the 2% Expanded Withholding Tax (EWT) and Personal Income Tax-to the Bureau of Internal Revenue (BIR).
- Delivery Fees: 100% of delivery/pick-up fees are remitted to the OWNER and are exempt from the AGENCY's {agency_share_val} fee.
- Payment Processing Fees: Third-party payment gateway surcharges associated with their gross earnings shall be absorbed by the OWNER and deducted prior to final remittance.

4. CANCELLATION PENALTIES AND COMPENSATION 
In the event that a Renter cancels a confirmed booking and a cancellation penalty is applied, the standard revenue split shall not apply to the penalty amount. Instead, the collected penalty shall be subject to a 60% / 40% distribution. The OWNER shall receive sixty percent (60%) as compensation, and the AGENCY shall retain forty percent (40%) to cover administrative overhead.

5. SECURITY DEPOSIT AND DAMAGE SETTLEMENT
a. Direct Collection: The OWNER is responsible for collecting and returning the PHP 5,000.00 Security Deposit directly to/from the renter. 
b. Damage Assessment & Evidence: The OWNER is strictly required to use the DriveElite platform to upload time-stamped evidence of the vehicle condition.
c. Dispute Resolution: Damage, fuel, or traffic violations shall be settled directly between the OWNER and Renter using the security deposit. 

6. INSURANCE AND LOSS LIABILITY
a. Mandatory Coverage: The OWNER must maintain valid comprehensive insurance.
b. Zero Agency Liability: The OWNER assumes all financial risk. The AGENCY holds zero financial or legal liability for physical damage, total wreck, theft, or insurance denial due to commercial use.
c. Regulatory Compliance & Impoundment: The OWNER is solely responsible for securing any necessary LTO/LTFRB franchises. The AGENCY assumes no liability if the vehicle is impounded for operating as an unregistered 'colorum' rental.

7. TERMINATION & PLATFORM ENFORCEMENT 
The AGENCY reserves the right to suspend accounts of users who fail to settle valid financial obligations.

8. Failure to Deliver and Affiliate Cancellations
1. No-Show Penalty: Failure to deliver the vehicle at the scheduled time incurs a penalty of PHP 2,000.00.
2. Late Cancellation Penalty: Canceling a confirmed booking with 24 to 48 hours notice incurs a penalty of PHP 1,000.00.
3. Account Suspension: Three (3) instances of cancellation or two (2) instances of a No-Show within a twelve (12) month period will result in permanent deactivation.

9. MISCELLANEOUS 
a. Electronic Consent: Digital acceptance on the platform carries the same legal weight as a physical signature. 
b. Venue: Disputes shall be instituted exclusively in the proper courts of Pasig City."""

    else:
        pdf.cell(0, 10, "MASTER RENTER AGREEMENT", ln=True, align='C')
        pdf.set_font("Helvetica", 'B', 10)
        pdf.cell(0, 6, "DriveElite, a Peer-to-Peer Car Rentals", ln=True, align='C')
        pdf.ln(5)
        
        pdf.set_font("Helvetica", '', 8)
        body_text = f"""KNOW ALL MEN BY THESE PRESENTS:
This agreement (the "Agreement") is made and executed by and between:

{data['full_name'].upper()}, of legal age, citizen of {data['nationality'].upper()}, with postal address at {data['address']}, hereinafter referred to as the "LESSEE";

-and-

DriveElite Peer-to-Peer Car Rentals, a company registered under the laws of the Republic of the Philippines, hereinafter referred to as the 'AGENCY' (acting as the authorized digital platform and booking agent on behalf of the vehicle's registered OWNER).

THEREFORE, the LESSEE hereby agrees to the following Master Terms and Conditions for all current and future vehicle bookings made through the DriveElite platform:

1. GENERAL USE & RESTRICTIONS
- Luzon Exclusivity: The LESSEE shall use the subject vehicle for personal purposes only and strictly within the Luzon region. Inter-island transfers are strictly prohibited.
- Authorized Drivers: The vehicle must only be driven by the registered LESSEE or an authorized driver whose identity was fully disclosed and approved by the AGENCY prior to the trip.
- Prohibited Areas & Conditions: The LESSEE shall not allow the vehicle to travel to areas where roads are not passable or use the vehicle during natural calamities, excessively heavy rains, storms, or flooding.
- Prohibited Activities: Smoking and the transport of animals inside the vehicle are strictly prohibited. The vehicle must not be operated by any person under the influence of alcohol or drugs.
[WARNING] PENALTY FOR MISUSE: Failure to follow any of the above guidelines will result in a fine with a maximum penalty of PHP 50,000.00 per infringement, absolute forfeiture of the Security Deposit, and immediate termination of the Car Rental Agreement.

2. DEPOSITS & FINANCIAL OBLIGATIONS
- Security Deposit: A physical cash deposit of PHP 5,000.00 shall be collected by the driver/owner upon vehicle handover. This deposit covers minor incidentals and will be refunded upon the safe return of the vehicle, provided no violations occurred.
- Interest Penalty: Default in the payment of any obligations under this Agreement when due shall bear interest at the rate of twenty percent (20%) per month, computed daily and compounded monthly until fully paid.

3. PLATFORM SERVICE FEE
The LESSEE acknowledges that for rental periods of seven (7) days or longer, a {renter_fee_val} Platform Service Fee is applied to the base rental rate to cover system infrastructure, customer support, and payment processing handled by {legal_entity}. This fee is expressly waived for short-term rentals of six (6) days or fewer.

4. CANCELLATION POLICY
Cancellation refunds for the Rental Fee shall be processed strictly in accordance with the following schedule:
- 0 to 2 days / No Show: 0% Refund
- 3 to 6 days prior to pick-up: 25% Refund
- 7 to 14 days prior to pick-up: 50% Refund
- 15 to 29 days prior to pick-up: 75% Refund
- 30 days or more prior to pick-up: 100% Refund

5. RETURN OF VEHICLE & PENALTIES
Excluding normal wear and tear, the following charges apply upon return:
- Missing Fuel: Charged at current market pricing per Liter.
- Missing RFID Card: PHP 500.00 per card.
- Late Return: Less than 3 hours incurs PHP 200.00 per hour. Greater than 3 hours incurs 50% of the daily rental fee.
- Extra Cleaning (Normal): Sedan: PHP 200 | Crossover/MPV: PHP 300 | SUV/Van: PHP 500
- Extra Cleaning (Smoking): Sedan: PHP 3,000 | Crossover/MPV: PHP 4,000 | SUV/Van: PHP 5,000
- Minor Damage (Per Panel): Sedan: PHP 2,500 | Crossover/MPV: PHP 3,000 | SUV/Van: PHP 3,500
- Lost/Damaged Keys: Replacement or emergency unlock services will incur a fee ranging from PHP 3,000.00 to PHP 15,000.00.

6. DAMAGE, MAJOR LOSS, OR THEFT
In the event of damage, major loss, total loss, or theft of the Rental Vehicle, the LESSEE must immediately secure a Police Report, a notarized affidavit explaining the incident, and provide a copy of their driver's license. The LESSEE must notify DriveElite within 24 hours of the incident.
In the case of total loss (including theft), the LESSEE assumes financial responsibility and shall pay 30% of the Fair Market Value of the vehicle as determined by the AGENCY/OWNER.

7. TRAFFIC VIOLATIONS, TOLLS, AND SURVIVAL OF LIABILITY
- Full Liability: The LESSEE assumes full financial and legal responsibility for any and all traffic violations, No Contact Apprehension Policy (NCAP) tickets, tollway penalties, towing fees, and LTO/MMDA alarms incurred during the exact dates and times of the rental period.
- Survival Clause: The LESSEE acknowledges that traffic citations are often delayed. The LESSEE's liability for these violations strictly survives the termination of this Agreement and the return of the Security Deposit. If a violation from the rental period is reported at any point in the future, the LESSEE remains legally bound to reimburse the OWNER/AGENCY immediately upon demand.
- LTO Demerit Transfer: In the event of an LTO alarm or traffic citation, the LESSEE explicitly agrees to accept any corresponding demerit points to their personal Driver's License. The LESSEE agrees to fully cooperate and sign any necessary documents to clear the OWNER's vehicle and license from said violations."""

    pdf.multi_cell(0, 4, body_text)
    pdf.ln(5)
    
    # 4. Digital Signature
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(0, 10, f"DIGITALLY SIGNED BY {'OWNER' if is_affiliate else 'RENTER'}:", ln=True)
    
    temp_sig = f"/data/uploads/temp_{data['username']}.png"
    with open(temp_sig, "wb") as f:
        f.write(sig_bytes)
    pdf.image(temp_sig, w=40)
    os.remove(temp_sig)
    
    pdf.set_font("Helvetica", '', 9)
    pdf.cell(0, 5, f"{data['full_name'].upper()}", ln=True)
    pdf.cell(0, 5, f"Date Signed: {date_str}", ln=True)
    
    pdf.output(pdf_filename)
    return pdf_filename

# ==========================================
# 4. 🔐 OTP VERIFICATION SCREEN
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
                
            except sqlite3.IntegrityError:
                st.error("🚨 That Username is already taken! Please refresh and choose a different username.")
            except Exception as e:
                st.error(f"⚠️ Registration failed due to a system error: {e}")
            
            # Admin Alerts
            try:
                admin_phone = "09688811400" 
                admin_email = "contact@driveelite.ph"
                new_role = payload[2] 
                new_name = payload[3] 
                
                from database_utils import send_sms_alert, send_alert_email
                send_sms_alert(admin_phone, f"DriveElite Admin: A new {new_role} ({new_name}) just registered! Please review their documents.")
                send_alert_email(admin_email, f"🚨 New {new_role} Registration: {new_name}", f"Hello Admin,\n\nA new {new_role} named {new_name} has successfully verified their account.\n\nPlease log into the Admin Command Center to review their ID and License.")
            except Exception:
                pass
            
            with st.spinner("Processing documents and emailing your copy..."):
                try:
                    un, role, email = payload[0], payload[2], payload[4]
                    prefix = "MOA" if role == "AFFILIATE" else "RENTER"
                    final_p = f"/data/uploads/{prefix}_{un}.pdf"
                            
                    send_welcome_email(email, role, final_p)
                    
                    with open(final_p, "rb") as f:
                        file_bytes = f.read()
                        
                    st.download_button(
                        label="📄 DOWNLOAD SIGNED CONTRACT", 
                        data=file_bytes, 
                        file_name=f"DriveElite_{prefix}.pdf", 
                        type="primary"
                    )
                                
                except Exception as e:
                    st.error(f"Account saved, but contract email failed: {e}")
            
            # --- NEW ONBOARDING FEEDBACK ---
            st.success("✅ Verification Successful! Your agreement has been signed.")
            st.info("⏳ **Next Step:** Your account is now under review by our Admin team.")
            st.warning("✉️ You will receive an email with your direct login link as soon as your account is approved. You may safely close this window.")
            
            st.session_state.otp_pending = False
            
            if f"temp_{payload[2].lower()}_data" in st.session_state:
                del st.session_state[f"temp_{payload[2].lower()}_data"]
                
            st.stop() # Halts the app so they just read the message!
        else:
            st.error("🚨 Invalid OTP. Please try again.")

# ==========================================
# 5. 🚗 MAIN REGISTRATION SCREEN
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
    except Exception:
        pass 
        
    st.divider()
    reg_type = st.radio("I want to register as a:", ["Select...", "Affiliate", "Renter"], horizontal=True)
    st.divider()

    if reg_type in ["Affiliate", "Renter"]:
        step_key = f"{reg_type.lower()}_step"
        if step_key not in st.session_state: st.session_state[step_key] = 1

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
                        
                        # --- DIRECT TO PDF ENGINE ---
                        try:
                            create_legit_pdf_contract(data, reg_type, sig_bytes, conn)
                        except Exception as e:
                            st.error(f"PDF Generation Error: {e}")
                        
                        st.session_state.reg_payload = (
                            data["username"], data["password"], reg_type.upper(), data["full_name"], 
                            data["email"], data["age"], data["nationality"], data["address"], 
                            data["area_code"], data["contact"], data["gov_id"], data["lic_id"], sig_bytes
                        )
                        st.session_state.verify_contact = data["contact"]
                        
                        # Send OTP
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
