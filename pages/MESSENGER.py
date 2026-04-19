import streamlit as st
import pandas as pd
from database_utils import get_connection

st.set_page_config(page_title="DriveElite Messenger", layout="centered")

if not st.session_state.get('logged_in'):
    st.warning("Please login to access the Messenger.")
    st.stop()

conn = get_connection()
current_user = st.session_state.username
role = st.session_state.get('role', 'USER')

st.title("💬 DRIVEELITE MESSENGER")
st.write(f"Logged in as: *{current_user.upper()}*")

# --- 1. COORDINATED CONTACT LIST ---
# FIXED: Changed 'users' to 'platform_users' and added 'APPROVED' filter
query = "SELECT username, role, full_name FROM platform_users WHERE username != ? AND admin_status = 'APPROVED'"
users_df = pd.read_sql_query(query, conn, params=(current_user,))

contacts = []

# Manually insert Admin if not already in the list
if current_user != "masterom":
    contacts.append("masterom (System Admin) - ADMIN")
    
for _, r in users_df.iterrows():
    name = r['full_name'] if r['full_name'] else r['username']
    contacts.append(f"{r['username']} ({name}) - {r['role']}")

if not contacts:
    st.info("No approved users found to chat with yet.")
    st.stop()

selected_contact_str = st.selectbox("Select someone to message:", contacts)
receiver_username = selected_contact_str.split(" ")[0]

st.divider()

# --- 2. FETCH CHAT HISTORY ---
chat_query = """
    SELECT sender, message, ts 
    FROM support_chats 
    WHERE (sender = ? AND receiver = ?) OR (sender = ? AND receiver = ?) 
    ORDER BY ts ASC
"""
chats = pd.read_sql_query(chat_query, conn, params=(current_user, receiver_username, receiver_username, current_user))

# --- 3. UI CONTAINER ---
chat_container = st.container(height=450)
with chat_container:
    if chats.empty:
        st.info(f"Start a conversation with @{receiver_username}")
    else:
        for _, c in chats.iterrows():
            if c['sender'] == current_user:
                # User's Messages (Blue)
                st.markdown(f"""
                <div style="display: flex; justify-content: flex-end; margin-bottom: 10px;">
                    <div style="background-color: #0084FF; color: white; padding: 10px 15px; border-radius: 18px 18px 4px 18px; max-width: 75%; font-family: sans-serif;">
                        {c['message']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Receiver's Messages (Grey)
                st.markdown(f"""
                <div style="display: flex; justify-content: flex-start; margin-bottom: 10px;">
                    <div style="background-color: #E4E6EB; color: black; padding: 10px 15px; border-radius: 18px 18px 18px 4px; max-width: 75%; font-family: sans-serif;">
                        <small style="color: #65676B; font-weight: bold;">@{c['sender']}</small><br>
                        {c['message']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

# --- 4. MESSAGE INPUT ---
with st.form("send_msg", clear_on_submit=True):
    msg = st.text_input("Message...", placeholder="Type here...")
    if st.form_submit_button("SEND", type="primary", use_container_width=True):
        if msg.strip():
            conn.execute("INSERT INTO support_chats (sender, receiver, message) VALUES (?, ?, ?)", (current_user, receiver_username, msg))
            conn.commit()
            st.rerun()
