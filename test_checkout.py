import streamlit as st
import requests
from requests.auth import HTTPBasicAuth

# IMPORTANT: Paste your actual secret test key inside the quotes below!
SECRET_KEY = 'sk_test_YOUR_ACTUAL_KEY_HERE'

st.title("DriveElite Checkout")
st.write("Vehicle: 2020 Nissan Terra VE")
st.write("Rate: ₱3,500.00 / day")

# When the user clicks the booking button
if st.button("Confirm Booking & Pay"):
    with st.spinner("Preparing secure checkout..."):
        
        # The PayMongo payload
        url = "https://api.paymongo.com/v1/links"
        payload = {
            "data": {
                "attributes": {
                    "amount": 350000, 
                    "description": "DriveElite - 1 Day SUV Rental",
                    "remarks": "Test Booking"
                }
            }
        }
        headers = {"accept": "application/json", "content-type": "application/json"}
        
        # Calling PayMongo
        response = requests.post(url, json=payload, headers=headers, auth=HTTPBasicAuth(SECRET_KEY, ''))
        
        # Handling the response
        if response.status_code == 200:
            checkout_url = response.json()['data']['attributes']['checkout_url']
            st.success("Checkout created successfully!")
            st.markdown(f"### 👉 [Click here to pay via PayMongo]({checkout_url})")
        else:
            st.error("Failed to generate payment link. Please try again.")
