import streamlit as st
import pandas as pd
import random
import datetime
from database_utils import get_connection

# Connect to database
conn = get_connection()

st.title("🚗 Welcome to DriveElite")
st.write("Join the premier peer-to-peer car rental network. Select your account type below to begin.")

reg_type = st.radio("I want to register as a:", ["Select...", "Affiliate", "Renter"])
st.divider()

# ==========================================
# AFFILIATE REGISTRATION BLOCK
# ==========================================
if reg_type == "Affiliate":
    st.subheader("💼 Affiliate Partner Registration")
    with st.form("affiliate_reg_form"):
        st.write("*Personal Information*")
        c1, c2, c3 = st.columns(3)
        first_name = c1.text_input("First Name").title()
        middle_name = c2.text_input("Middle Name").title()
        surname = c3.text_input("Surname").title()
        
        # We use [3, 1, 1, 3] to make the middle two boxes much narrower!
        c4, c5, c6, c7 = st.columns([3, 1, 1, 3])
        
        dob = c4.date_input("Date of Birth", min_value=datetime.date(1920, 1, 1), max_value=datetime.date.today())
        age = c5.text_input("Age", max_chars=2) 
        nationality = c6.text_input("Nat.", max_chars=3).upper() # Automatically forces it to uppercase (e.g. PHI)
        contact = c7.text_input("Contact Number")
        
        # Changing text_input to text_area makes it a multi-line expanding box!
        address = st.text_area("Complete Home Address")
        
        st.write("*Account Details*")
        username = st.text_input("Choose a Username")
        p1, p2 = st.columns(2)
        password = p1.text_input("Password", type="password")
        confirm_password = p2.text_input("Confirm Password", type="password")
        
        st.write("*Required Documents*")
        gov_id = st.file_uploader("Upload Valid Government ID", type=['jpg', 'png', 'jpeg'])
        lic_id = st.file_uploader("Upload Driver's License", type=['jpg', 'png', 'jpeg'])
        
        st.divider()
        # The new Expander system!
        with st.expander("📜 CLICK HERE TO READ AFFILIATE POLICIES (Required)"):
            st.markdown("""
            * *Vehicle Condition:* Cars must be registered, insured, safe, and clean.
            * *Platform Fee:* DriveElite retains an 18% fee. You receive 82%.
            * *Payouts:* Processed once journey is "COMPLETED".
            * *Handover:* You must verify Renter ID and complete the digital checklist.
            * *GPS:* For your security, GPS must be installed minus audio.
            * *Visibility:* Cars listed as "LIVE" must be ready to book.
            """)
        agreed = st.checkbox("✅ I have read, understood, and agree to the Affiliate Policies")
        
        if st.form_submit_button("Submit Partner Registration", type="primary"):
            full_name = f"{first_name} {middle_name} {surname}".replace("  ", " ").strip()
            today = datetime.date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            
            if not agreed:
                st.error("🚨 Registration Blocked: You must check the agreement box above the submit button.")
            elif password != confirm_password:
                st.error("🚨 Passwords do not match. Please try again.")
            elif not all([first_name, surname, username, password, gov_id, lic_id, contact]):
                st.error("🚨 Please fill out all required fields and upload BOTH IDs.")
            else:
                user_check = pd.read_sql_query("SELECT username FROM users WHERE username=?", conn, params=(username,))
                if not user_check.empty:
                    st.error("🚨 Username taken. Please choose another.")
                else:
                    # Fixed 'AFFILIATE' role, added the missing verify_contact line!
                    st.session_state.reg_payload = (username, password, 'AFFILIATE', full_name, age, nationality, address, contact, gov_id.read(), lic_id.read())
            
                    # --- ADD THESE 4 LINES BACK! ---
                    st.session_state.verify_contact = contact
                    st.session_state.generated_otp = str(random.randint(100000, 999999))
                    st.session_state.otp_pending = True
                    st.rerun()
            # -------------------------------
# ==========================================
# RENTER REGISTRATION BLOCK
# ==========================================
elif reg_type == "Renter":
    st.subheader("🚗 Renter Registration")
    with st.form("renter_reg_form"):
        st.write("*Personal Information*")
        c1, c2, c3 = st.columns(3)
        first_name = c1.text_input("First Name").title()
        middle_name = c2.text_input("Middle Name").title()
        surname = c3.text_input("Surname").title()
        
        # We use [3, 1, 1, 3] to make the middle two boxes much narrower!
        c4, c5, c6, c7 = st.columns([3, 1, 1, 3])
        
        dob = c4.date_input("Date of Birth", min_value=datetime.date(1920, 1, 1), max_value=datetime.date.today())
        age = c5.text_input("Age", max_chars=2) 
        nationality = c6.text_input("Nat.", max_chars=3).upper() # Automatically forces it to uppercase (e.g. PHI)
        contact = c7.text_input("Contact Number")

        # Changing text_input to text_area makes it a multi-line expanding box!
        address = st.text_area("Complete Home Address")
        
        st.write("*Account Details*")
        username = st.text_input("Choose a Username")
        p1, p2 = st.columns(2)
        password = p1.text_input("Password", type="password")
        confirm_password = p2.text_input("Confirm Password", type="password")
        
        st.write("*Required Documents*")
        gov_id = st.file_uploader("Upload Valid Government ID", type=['jpg', 'png', 'jpeg'])
        lic_id = st.file_uploader("Upload Driver's License", type=['jpg', 'png', 'jpeg'])
        
        st.divider()
        # The new Expander system!
        with st.expander("📜 CLICK HERE TO READ RENTER POLICIES (Required)"):
            st.markdown("""
            * *Fuel Policy:* Return with same fuel level. Missing fuel incurs a refill cost + ₱500 fee.
            * *Cleanliness:* Return clean. Excessive dirt incurs up to ₱600 fee.
            * *Damage:* You are fully responsible for damages incurred during booking.
            * *Late Returns:* 30-min grace period. Then strict ₱300/hour late fee.
            * *RFID:* Load Approximated RFID Amount for your convenience. If not Loaded +₱200 Load fee.
            * *Speed Limit:* Observe speed limit at all times to avoid penalties.
            * *Permitted Use:* Personal transport only. No racing/towing and interisland travel is strictly prohibited.
            """)
        agreed = st.checkbox("✅ I have read, understood, and agree to the Renter Policies")
        
        if st.form_submit_button("Submit Renter Registration", type="primary"):
            full_name = f"{first_name} {middle_name} {surname}".replace("  ", " ").strip()
            today = datetime.date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            
            if not agreed:
                st.error("🚨 Registration Blocked: You must check the agreement box above the submit button.")
            elif password != confirm_password:
                st.error("🚨 Passwords do not match. Please try again.")
            elif not all([first_name, surname, username, password, gov_id, lic_id, contact]):
                st.error("🚨 Please fill out all required fields and upload BOTH IDs.")
            else:
                user_check = pd.read_sql_query("SELECT username FROM users WHERE username=?", conn, params=(username,))
                if not user_check.empty:
                    st.error("🚨 Username taken. Please choose another.")
                else:
            
                    # Fixed 'RENTER' role, added the missing verify_contact line!
                    st.session_state.reg_payload = (username, password, 'RENTER', full_name, age, nationality, address, contact, gov_id.read(), lic_id.read())
            
                    # --- ADD THESE 4 LINES BACK! ---
                    st.session_state.verify_contact = contact
                    st.session_state.generated_otp = str(random.randint(100000, 999999))
                    st.session_state.otp_pending = True
                    st.rerun()
            # -------------------------------
# ==========================================
# OTP VERIFICATION LOGIC
# ==========================================
if st.session_state.get('otp_pending'):
    st.divider()
    st.warning(f"📲 An OTP has been sent to your number: *{st.session_state.verify_contact}*")
    otp_input = st.text_input("Enter 6-digit OTP", key="otp_verify")
    st.caption(f"(For Testing: The OTP is {st.session_state.generated_otp})")
    
    if st.button("Verify OTP"):
        if otp_input == st.session_state.generated_otp:
            payload = st.session_state.reg_payload
            cursor = conn.cursor()
            
            # Now it perfectly matches your database spellings and has 10 question marks!
            cursor.execute('''INSERT INTO users 
                              (username, password, role, full_name, age, nationality, address, contact_number, govt_id_img, license_img) 
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', payload)
            
            conn.commit()
            st.success("✅ Verification successful! Your account is created. Please log in.")
            
            del st.session_state.reg_payload
            del st.session_state.verify_contact
            del st.session_state.generated_otp
            st.session_state.otp_pending = False
            st.rerun()
        else:
            st.error("🚨 Invalid OTP. Please try again.")
