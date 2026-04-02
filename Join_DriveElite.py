import streamlit as st
import pandas as pd
import os
import datetime
import random
import time
from database_utils import get_connection

os.makedirs("uploads", exist_ok=True)
def save_file(uploaded_file):
    if uploaded_file:
        path = os.path.join("uploads", uploaded_file.name)
        with open(path, "wb") as f: f.write(uploaded_file.getbuffer())
        return path
    return None

st.set_page_config(page_title="DriveElite Registration", layout="wide")
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); }
    div[data-baseweb="input"] > div, div[data-baseweb="base-input"], textarea {
        background-color: #ffffff !important; border: 2px solid #cbd5e1 !important; border-radius: 6px !important;
    }
</style>
""", unsafe_allow_html=True)

conn = get_connection()

if 'otp_pending' not in st.session_state: st.session_state.otp_pending = False
if 'reg_payload' not in st.session_state: st.session_state.reg_payload = None
if 'generated_otp' not in st.session_state: st.session_state.generated_otp = ""
if 'verify_contact' not in st.session_state: st.session_state.verify_contact = ""

# ==========================================
# OTP VERIFICATION SCREEN
# ==========================================
if st.session_state.otp_pending:
    st.title("🔒 Phone Number Verification")
    st.write("For security purposes, please verify your contact number to complete your registration.")
    
    st.success(f"📱 *MOCK SMS GATEWAY:* Sent OTP '{st.session_state.generated_otp}' to {st.session_state.verify_contact}")
    
    with st.form("otp_form"):
        user_otp = st.text_input("Enter the 6-Digit OTP sent to your phone", max_chars=6)
        
        c1, c2 = st.columns(2)
        if c1.form_submit_button("VERIFY & COMPLETE REGISTRATION", type="primary", use_container_width=True):
            if user_otp == st.session_state.generated_otp:
                try:
                    p = st.session_state.reg_payload
                    conn.execute("INSERT INTO users (username, password, role, full_name, age, contact_number, address, nationality, id_img, license_img, admin_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')", p)
                    conn.commit()
                    
                    st.success("🎉 Phone Verified! Registration Successful. Pending Admin approval.")
                    st.session_state.otp_pending = False
                    time.sleep(3)
                    st.rerun()
                except Exception as e:
                    st.error("⚠️ Username is already taken. Please go back and choose another.")
            else:
                st.error("❌ Incorrect OTP. Please try again.")
                
        if c2.form_submit_button("CANCEL & GO BACK", use_container_width=True):
            st.session_state.otp_pending = False
            st.rerun()

# ==========================================
# MAIN REGISTRATION SCREEN
# ==========================================
else:
    st.title("🚗 Welcome to DriveElite")
    st.write("Join the premier peer-to-peer car rental network. Select your account type below to begin.")

    reg_type = st.radio("I want to register as a:", ["Select...", "Affiliate", "Renter"], horizontal=True)
    st.divider()

    if reg_type == "Affiliate":
        with st.sidebar:
            st.header("💼 Affiliate Policies")
            st.markdown("""
            * *Vehicle Condition:* Cars must be registered, insured, safe, and clean.
            * *Platform Fee:* DriveElite retains an 18% fee. You receive 82%.
            * *Payouts:* Processed once journey is "COMPLETED".
            * *Handover:* You must verify Renter ID and complete the digital checklist.
            * *GPS:* For your security, GPS must be installed minus audio.
            * *Visibility:* Cars listed as "LIVE" must be ready to book.
            """)
            st.info("You must agree to these terms to register.")

        st.subheader("💼 Affiliate Partner Registration")
        with st.form("affiliate_reg_form"):
            st.write("*Personal Information*")
            c1, c2, c3 = st.columns(3)
            first_name = c1.text_input("First Name").title()
            middle_name = c2.text_input("Middle Name").title()
            surname = c3.text_input("Surname").title()
            
            c4, c5, c6 = st.columns([2, 1, 2])
            dob = c4.date_input("Date of Birth", min_value=datetime.date(1930, 1, 1), max_value=datetime.date(2008, 1, 1), value=datetime.date(2000, 1, 1))
            age = c5.number_input("Age", min_value=18, max_value=99, step=1)
            contact = c6.text_input("Contact Number (e.g. 0917...)")
            
            c_addr, c_nat = st.columns([3, 1])
            address = c_addr.text_area("Full Address")
            nationality = c_nat.text_input("Nationality", value="Filipino")
            
            st.write("*Account Details*")
            username = st.text_input("Choose a Username").lower()
            c7, c8 = st.columns(2)
            password = c7.text_input("Create a Password", type="password")
            confirm_password = c8.text_input("Confirm Password", type="password")
            
            st.write("*Identity Verification (2 IDs Required)*")
            c9, c10 = st.columns(2)
            gov_id = c9.file_uploader("Upload Passport / Govt ID", type=['jpg', 'png'])
            lic_id = c10.file_uploader("Upload Driver's License", type=['jpg', 'png'])
            
            st.divider()
            agreed = st.checkbox("✅ I have read, understood, and agree to the Affiliate Policies & 15% Platform Fee rules in the sidebar.")
            
            if st.form_submit_button("Submit Partner Registration", type="primary"):
                full_name = f"{first_name} {middle_name} {surname}".replace("  ", " ").strip()
                
                if not agreed: st.error("🚨 Registration Blocked: You must agree to the terms in the sidebar.")
                elif password != confirm_password: st.error("🚨 Passwords do not match. Please try again.")
                elif first_name and surname and username and password and gov_id and lic_id and contact and nationality:
                    if not pd.read_sql_query("SELECT username FROM users WHERE username=?", conn, params=(username,)).empty:
                        st.error("⚠️ Username taken. Please choose another.")
                    else:
                        st.session_state.reg_payload = (username, password, 'AFFILIATE', full_name, age, contact, address, nationality.title(), save_file(gov_id), save_file(lic_id))
                        st.session_state.verify_contact = contact
                        st.session_state.generated_otp = str(random.randint(100000, 999999))
                        st.session_state.otp_pending = True
                        st.rerun()
                else: st.error("⚠️ Please fill out all required fields and upload BOTH IDs.")

    elif reg_type == "Renter":
        with st.sidebar:
            st.header("📝 Renter Policies")
            st.markdown("""
            * *Fuel Policy:* Return with same fuel level. Missing fuel incurs a refill cost + ₱500 fee.
            * *Cleanliness:* Return clean. Excessive dirt incurs up to ₱600 fee.
            * *Damage:* You are fully responsible for damages incurred during booking.
            * *Late Returns:* 30-min grace period. Then strict ₱300/hour late fee.
            * *RFID:* Load Approximated RFID Amount for your convenience. If not Loaded +₱200 Load fee.
            * *Speed Limit:* Observe speed limit at all times to avoid penalties.
            * *Permitted Use:* Personal transport only. No racing/towing and interisland travel is strictly prohibited.
            """)
            st.info("You must agree to these terms to register.")

        st.subheader("🚙 Renter Registration")
        with st.form("renter_reg_form"):
            st.write("*Personal Information*")
            c1, c2, c3 = st.columns(3)
            first_name = c1.text_input("First Name").title()
            middle_name = c2.text_input("Middle Name").title()
            surname = c3.text_input("Surname").title()
            
            c4, c5, c6 = st.columns([2, 1, 2])
            dob = c4.date_input("Date of Birth", min_value=datetime.date(1930, 1, 1), max_value=datetime.date(2008, 1, 1), value=datetime.date(2000, 1, 1))
            age = c5.number_input("Age", min_value=18, max_value=99, step=1)
            contact = c6.text_input("Contact Number (e.g. 0917...)")
            
            c_addr, c_nat = st.columns([3, 1])
            address = c_addr.text_area("Full Address")
            nationality = c_nat.text_input("Nationality", value="Filipino")
            
            st.write("*Account Details*")
            username = st.text_input("Choose a Username").lower()
            c7, c8 = st.columns(2)
            password = c7.text_input("Create a Password", type="password")
            confirm_password = c8.text_input("Confirm Password", type="password")
            
            st.write("*Identity Verification (2 IDs Required)*")
            c9, c10 = st.columns(2)
            gov_id = c9.file_uploader("Upload Passport / Govt ID", type=['jpg', 'png'])
            lic_id = c10.file_uploader("Upload Driver's License", type=['jpg', 'png'])
            
            st.divider()
            agreed = st.checkbox("✅ I have read, understood, and agree to the DriveElite Renter Policies shown in the sidebar.")
            
            if st.form_submit_button("Submit Registration", type="primary"):
                full_name = f"{first_name} {middle_name} {surname}".replace("  ", " ").strip()
                
                if not agreed: st.error("🚨 Registration Blocked: You must agree to the terms in the sidebar.")
                elif password != confirm_password: st.error("🚨 Passwords do not match. Please try again.")
                elif first_name and surname and username and password and gov_id and lic_id and contact and nationality:
                    if not pd.read_sql_query("SELECT username FROM users WHERE username=?", conn, params=(username,)).empty:
                        st.error("⚠️ Username taken. Please choose another.")
                    else:
                        st.session_state.reg_payload = (username, password, 'RENTER', full_name, age, contact, address, nationality.title(), save_file(gov_id), save_file(lic_id))
                        st.session_state.verify_contact = contact
                        st.session_state.generated_otp = str(random.randint(100000, 999999))
                        st.session_state.otp_pending = True
                        st.rerun()
                else: st.error("⚠️ Please fill out all required fields and upload BOTH IDs.")
