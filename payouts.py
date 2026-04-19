import smtplib
from email.message import EmailMessage
import streamlit as st

def generate_standard_receipt(transaction_ref, vehicle_name, gross_rental_amount, delivery_fee, return_fee, payment_method, exact_gateway_fee, is_corporate=False):
    """Generates the text receipt for a completed 18/82 trip settlement."""
    
    # --- MOA Logic ---
    # Standard EWT is usually 2% for individuals or 5% for corps in PH
    ewt_percentage = 5.0 if is_corporate else 2.0 
    total_ewt_withheld = gross_rental_amount * (ewt_percentage / 100)
    
    # 1. Rental Revenue after Tax
    net_rental_revenue = gross_rental_amount - total_ewt_withheld
    
    # 2. Affiliate gets 82% of Net Rental + 100% of Logistics Fees
    affiliate_net_rental_share = net_rental_revenue * 0.82
    affiliate_logistics_share = delivery_fee + return_fee
    
    # 3. Final Payout (Subtracting the CC Surcharge they agreed to absorb)
    net_payout = affiliate_net_rental_share + affiliate_logistics_share - exact_gateway_fee

    receipt_text = f"""
================================================
  DRIVEELITE AFFILIATE SETTLEMENT STATEMENT
================================================
Transaction Ref : {transaction_ref}
Vehicle         : {vehicle_name}
Payment Mode    : {payment_method.upper()}
------------------------------------------------
Gross Rental    : ₱{gross_rental_amount:,.2f}
Tax Withheld    : -₱{total_ewt_withheld:,.2f} ({int(ewt_percentage)}% EWT)
Logistics Fees  : +₱{affiliate_logistics_share:,.2f}
CC Surcharge    : -₱{exact_gateway_fee:,.2f}
------------------------------------------------
NET Payout      : ₱{net_payout:,.2f}
================================================
Status: SETTLED VIA GCASH/BANK
Date: {st.datetime.date.today().strftime('%B %d, %Y')}
    """
    return receipt_text, net_payout

def email_receipt_to_affiliate(affiliate_email, receipt_text, transaction_ref):
    """Sends the generated settlement statement via Gmail using secure secrets."""
    msg = EmailMessage()
    msg.set_content(receipt_text)
    msg['Subject'] = f"DriveElite Settlement Complete - Ref: {transaction_ref}"
    msg['From'] = "DriveElite Finance <rdalbaojrh@gmail.com>"
    msg['To'] = affiliate_email

    try:
        # COORDINATED: Using the same secret key from your Dashboard
        EMAIL_ADDRESS = "rdalbaojrh@gmail.com"
        EMAIL_APP_PASSWORD = st.secrets["email_app_password"] 
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Payout Email Error: {e}")
        return False
