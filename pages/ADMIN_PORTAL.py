import sys
import os
import smtplib
from email.message import EmailMessage
import streamlit as st
import pandas as pd
import datetime
import numpy as np
import time
import random
from PIL import Image

==========================================
1. PAGE CONFIG (MUST BE THE VERY FIRST ST COMMAND)
==========================================
st.set_page_config(page_title="DriveElite Admin", layout="wide")

==========================================
2. FORCE ROOT DIRECTORY VISIBILITY (THE PERISCOPE)
==========================================
current_dir = os.path.dirname(os.path.abspath(file))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
if parent_dir not in sys.path:
sys.path.append(parent_dir)

==========================================
3. IMPORT CUSTOM MODULES
==========================================
from database_utils import get_connection, init_db, patch_database
from tiered_discounts import init_discount_db, render_admin_discount_table
try:
from finance import get_days_before_pickup, calculate_moa_cancellation_40_60
except ImportError:
st.error("Missing finance.py! Please ensure the finance script is in your root folder.")

==========================================
4. INITIALIZE DATABASE
==========================================
conn = get_connection()
init_db()
patch_database()
init_discount_db(conn)

==========================================
5. ADMIN UI STARTS HERE
==========================================
st.title("👑 DriveElite Admin Portal")
st.divider()

--- 3. UTILITY FUNCTIONS ---
def display_document(file_path, title):
import os
import streamlit as st
if file_path and str(file_path).strip() and os.path.exists(file_path):
if str(file_path).lower().endswith('.pdf'):
with open(file_path, "rb") as f:
safe_key = f"dl_{str(file_path).replace('/', '').replace('.', '')}_{title.replace(' ', '')}"
st.download_button(f"📄 Download {title} (PDF)", f.read(), file_name=os.path.basename(file_path), mime="application/pdf", key=safe_key)
else:
st.image(file_path, caption=title, use_container_width=True)
else:
st.warning(f"No {title} provided.")
def email_receipt_to_affiliate(affiliate_email, receipt_text, transaction_ref):
sender_email = "rdalbaojr@gmail.com"
