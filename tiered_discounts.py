import streamlit as st
import os
import shutil
from database_utils import get_connection

st.set_page_config(page_title="Factory Reset", layout="centered")

st.markdown("<h1 style='text-align: center;'>🧹 DriveElite Factory Reset</h1>", unsafe_allow_html=True)
st.warning("⚠️ **WARNING:** This will permanently delete ALL test users, vehicles, bookings, chats, and uploaded photos. It will reset the system to Day 1.")

if st.button("🚨 WIPE ALL TEST DATA & GO LIVE 🚨", type="primary", use_container_width=True):
    conn = get_connection()
    
    # 1. Clear all data from the tables
    tables_to_wipe = ['platform_users', 'vehicles', 'bookings', 'chat_messages', 'drivers', 'admin_promos']
    
    for table in tables_to_wipe:
        try:
            conn.execute(f"DELETE FROM {table}")
            # Reset the ID counters back to 1
            conn.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'") 
        except Exception as e:
            pass # Ignores errors if a table happens to be empty
            
    conn.commit()
    st.success("✅ Database wiped clean. IDs reset to 1.")

    # 2. Delete all test photos and PDFs
    if os.path.exists("uploads"):
        try:
            shutil.rmtree("uploads") # Deletes the folder and everything in it
            os.makedirs("uploads")   # Recreates the empty folder
            st.success("✅ Uploads vault cleared. All test IDs, car photos, and PDFs are gone.")
        except Exception as e:
            st.error(f"Could not clear uploads folder: {e}")

    st.balloons()
    st.info("🎉 **DriveElite is officially a clean slate!** You can now delete this RESET.py file from your GitHub.")
