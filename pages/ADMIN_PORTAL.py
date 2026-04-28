import sys
import os
import smtplib
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import streamlit as st
import pandas as pd
import datetime
import numpy as np
import time
import random
import math
from PIL import Image

# ==========================================
# 1. PAGE CONFIG
# ==========================================
st.set_page_config(page_title="DriveElite Admin", layout="wide")

# ==========================================
# 2. DIRECTORY VISIBILITY
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# ==========================================
# 3. IMPORT CUSTOM MODULES
# =========================================

from database_utils import get_connection, init_db, patch_database
from tiered_discounts import init_discount_db, render_admin_discount_table
 


try:
    from finance import get_days_before_pickup, calculate_moa_cancellation_40_60
except ImportError:
    st.error("Missing finance.py!")

# ==========================================
# 4. INITIALIZE DATABASE
# ==========================================
conn = get_connection()
init_db()
patch_database()
init_discount_db(conn)

# ==========================================
# 5. UTILITY FUNCTIONS (INCLUDING POS RECEIPTS)
# ==========================================
def display_document(file_path, title):
    if file_path and str(file_path).strip() and os.path.exists(file_path):
        if str(file_path).lower().endswith('.pdf'):
            with open(file_path, "rb") as f:
                safe_key = f"dl_{str(file_path).replace('/', '_').replace('.', '_')}_{title.replace(' ', '')}"
                st.download_button(f"📄 Download {title} (PDF)", f.read(), file_name=os.path.basename(file_path), mime="application/pdf", key=safe_key)
        else:
            st.image(file_path, caption=title, use_container_width=True)
    else:
        st.warning(f"No {title} provided.")

def email_receipt_to_user(target_email, receipt_text, subject):
    sender_email = "rdalbaojr@gmail.com" 
    try:
        app_password = st.secrets["email_app_password"]
        msg = EmailMessage()
        msg.set_content(receipt_text)
        msg['Subject'] = subject
        msg['From'] = f"DriveElite Finance <{sender_email}>"
        msg['To'] = target_email
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, app_password)
            smtp.send_message(msg)
        return True
    except:
        return False

def generate_pos_receipt(b_data):
    date_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    receipt = f"""
================================
      DRIVEELITE PLATFORM       
       OFFICIAL RECEIPT         
================================
DATE: {date_now}
REF NO: #{b_data['booking_ref']}
STATUS: {b_data['status']}
