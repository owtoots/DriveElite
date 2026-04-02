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
st.write(f"Logged in securely as: *{current_user.upper()}* ({role})")

# --- Get list of users from the Database ---
users_df = pd.read_sql_query("SELECT username, role, full_name FROM users WHERE username != ?", conn, params=(current_user,))

contacts = []

# --- Manually insert the Admin into the list! ---
if current_user != "masterom":
    contacts.append("masterom (System Admin) - ADMIN")
    
for _, r in users_df.iterrows():
    name = r['full_name'] if r['full_name'] else r['username']
    contacts.append(f"{r['username']} ({name}) - {r['role']}")

if not contacts:
    st.info("No other users found on the platform yet.")
    st.stop()

# Dropdown to select who to message
selected_contact_str = st.selectbox("Select someone to message:", contacts)

# Extract just the username
receiver_username = selected_contact_str.split(" ")[0]

st.markdown(f"### Chat History with @{receiver_username}")

# --- Fetch Chat History ---
chat_query = """
    SELECT sender, message, ts 
    FROM support_chats 
    WHERE (sender = ? AND receiver = ?) OR (sender = ? AND receiver = ?) 
    ORDER BY ts ASC
"""
chats = pd.read_sql_query(chat_query, conn, params=(current_user, receiver_username, receiver_username, current_user))

# --- BEAUTIFUL FB MESSENGER UI ---
chat_container = st.container(height=450)
with chat_container:
    if chats.empty:
        st.info("Say hello to start the conversation!")
    else:
        for _, c in chats.iterrows():
            if c['sender'] == current_user:
                # FB Style: Your Messages (Blue, Right-aligned)
                st.markdown(f"""
                <div style="display: flex; justify-content: flex-end; margin-bottom: 10px;">
                    <div style="background-color: #0084FF; color: white; padding: 10px 15px; border-radius: 20px 20px 5px 20px; max-width: 75%; font-family: Arial, sans-serif; box-shadow: 0px 2px 5px rgba(0,0,0,0.1);">
                        {c['message']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                # FB Style: Their Messages (Grey, Left-aligned)
                st.markdown(f"""
                <div style="display: flex; justify-content: flex-start; margin-bottom: 10px;">
                    <div style="background-color: #E4E6EB; color: black; padding: 10px 15px; border-radius: 20px 20px 20px 5px; max-width: 75%; font-family: Arial, sans-serif; box-shadow: 0px 2px 5px rgba(0,0,0,0.1);">
                        <small style="color: #65676B;">@{c['sender']}</small><br>
                        {c['message']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

# --- Send a new message ---
with st.form("send_msg", clear_on_submit=True):
    msg = st.text_input("Type your message here...", placeholder="Type here and press Enter to send...")
    if st.form_submit_button("Send Message", type="primary", use_container_width=True):
        if msg.strip():
            conn.execute("INSERT INTO support_chats (sender, receiver, message) VALUES (?, ?, ?)", (current_user, receiver_username, msg))
            conn.commit()
            st.rerun()
