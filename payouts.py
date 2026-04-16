import requests
import json
import streamlit as st
import datetime

def generate_settlement_receipt(
    transaction_ref, 
    vehicle_name, 
    rental_days, 
    gross_rental_amount, 
    payment_method, 
    exact_gateway_fee, 
    is_corporate=False
):
    """
    Calculates the exact payout and generates a receipt for the Affiliate.
    """
    
    # 1. Handle EWT (5% if corporate, 0% if regular)
    ewt_percentage = 5.0 if is_corporate else 0.0
    total_ewt_withheld = gross_rental_amount * (ewt_percentage / 100)
    
    # 2. Base 82% / 18% Split
    platform_fee = gross_rental_amount * 0.18
    affiliate_gross_share = gross_rental_amount * 0.82
    
    # 3. Affiliate's deductions
    affiliate_ewt_deduction = total_ewt_withheld * 0.82
    gateway_surcharge = exact_gateway_fee
    
    # 4. Final Net Cash Remitted
    net_payout = affiliate_gross_share - affiliate_ewt_deduction - gateway_surcharge

    # 5. Build the Receipt String
    receipt_text = f"""
    ================================================
    DRIVEELITE AFFILIATE SETTLEMENT STATEMENT
    ================================================
    Transaction Ref : {transaction_ref}
    Vehicle         : {vehicle_name}
    Rental Period   : {rental_days} Days
    Payment Mode    : {payment_method.upper()}
    ------------------------------------------------
    GROSS CALCULATION
    Gross Rental Amount                 : ₱{gross_rental_amount:,.2f}
    Less: EWT Withheld by Renter ({ewt_percentage}%)  : -₱{total_ewt_withheld:,.2f}
    ------------------------------------------------
    AFFILIATE SETTLEMENT BREAKDOWN
    Affiliate Gross Share (82%)         : ₱{affiliate_gross_share:,.2f}
    Less: Affiliate EWT Share (82%)     : -₱{affiliate_ewt_deduction:,.2f}
    Less: Gateway Surcharge             : -₱{gateway_surcharge:,.2f}
    ------------------------------------------------
    NET CASH REMITTED TO AFFILIATE      : ₱{net_payout:,.2f}
    ================================================
    """
    
    return receipt_text, net_payout

# --- STREAMLIT UI EXAMPLE ---
# You can test this directly in your app to see how it looks.

st.markdown("### 📄 Settlement Preview")

# Example 1: A Regular Renter paying via GCash (₱250 fee on ₱10k)
receipt_gcash, payout_gcash = generate_settlement_receipt(
    transaction_ref="BK-98765432",
    vehicle_name="2020 Nissan Terra VE",
    rental_days=4,
    gross_rental_amount=10000.00,
    payment_method="GCash",
    exact_gateway_fee=250.00,
    is_corporate=False
)

# Example 2: A Corporate Renter paying via Credit Card (₱350 fee on ₱10k)
receipt_corp, payout_corp = generate_settlement_receipt(
    transaction_ref="BK-98765433",
    vehicle_name="2020 Nissan Terra VE",
    rental_days=4,
    gross_rental_amount=10000.00,
    payment_method="Credit Card",
    exact_gateway_fee=350.00,
    is_corporate=True
)

# Display in Streamlit using st.code for a clean, monospaced receipt look
st.write("**Scenario 1: Regular Renter via GCash**")
st.code(receipt_gcash, language="text")

st.write("**Scenario 2: Corporate Renter via Credit Card (with EWT)**")
st.code(receipt_corp, language="text")
How this protects your database:
No Guesswork: By passing exact_gateway_fee as an argument, your code just reads whatever PayMongo charged in reality. It doesn't try to guess percentages, which prevents math errors from throwing off your accounting.

Corporate Switch: The is_corporate=True/False flag automatically triggers the EWT math. If a normal person rents the car, the EWT lines simply show ₱0.00, keeping the receipt clean without breaking the structure.

The Format: Using st.code() in Streamlit forces the text into a monospaced font, making the decimals line up perfectly like a traditional printed receipt.
