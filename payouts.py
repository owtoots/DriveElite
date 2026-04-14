import requests
import json
import streamlit as st
import datetime

def release_affiliate_payout(payout_ref, amount, bank_code, account_no, account_name):
    # Your Secret Key from the gateway dashboard (keep this secure!)
    API_SECRET_KEY = "sk_test_YOUR_SECRET_KEY_HERE"
    
    # The endpoint for creating a disbursement/transfer
    url = "https://api.paymentgateway.com/v1/disbursements"

    # The payload contains the Affiliate's bank details and the 82% cut
    payload = {
        "external_id": f"PAYOUT-{payout_ref}-{int(datetime.datetime.now().timestamp())}",
        "amount": int(amount), # E.g., 4000
        "bank_code": bank_code, # E.g., "BDO", "BPI", or "GCASH"
        "account_holder_name": account_name,
        "account_number": account_no,
        "description": f"DriveElite Affiliate Settlement: {payout_ref}"
    }
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Basic {API_SECRET_KEY}"
    }

    # Execute the transfer
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        return True, "Payout successfully routed to Affiliate's bank."
    else:
        error_data = response.json()
        return False, f"API Error: {error_data.get('message', 'Transfer failed.')}"
