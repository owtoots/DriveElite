import requests
import json
import streamlit as st
import datetime

# payouts.py
import smtplib
from email.message import EmailMessage

def generate_standard_receipt(transaction_ref, vehicle_name, gross_rental_amount, delivery_fee, return_fee, payment_method, exact_gateway_fee, is_corporate=False):
    """Generates the text receipt for a completed 18/82 trip."""
    grand_total_charged = gross_rental_amount + delivery_fee + return_fee
    ewt_percentage = 5.0 if is_corporate else 0.0
    total_ewt_withheld = gross_rental_amount * (ewt_percentage / 100)
    
    net_rental_revenue = gross_rental_amount - total_ewt_withheld
    affiliate_net_rental_share = net_rental_revenue * 0.82
    affiliate_logistics_share = delivery_fee + return_fee
    gateway_surcharge = exact_gateway_fee 
    
    net_payout = affiliate_net_rental_share + affiliate_logistics_share - gateway_surcharge

    receipt_text = f"""
    ================================================
    DRIVEELITE AFFILIATE SETTLEMENT STATEMENT
    ================================================
    Transaction Ref : {transaction_ref}
    Vehicle         : {vehicle_name}
    Payment Mode    : {payment_method.upper()}
    ------------------------------------------------
    NET CASH REMITTED TO AFFILIATE      :  ₱{net_payout:,.2f}
    ================================================
    """
    return receipt_text, net_payout

def email_receipt_to_affiliate(affiliate_email, receipt_text, transaction_ref):
    """Sends the generated text receipt via Gmail."""
    msg = EmailMessage()
    msg.set_content(receipt_text)
    msg['Subject'] = f"DriveElite Settlement Complete - Ref: {transaction_ref}"
    msg['From'] = "nucleuz.driveelite@gmail.com" 
    msg['To'] = affiliate_email

    try:
        EMAIL_ADDRESS = "nucleuz.driveelite@gmail.com"
        EMAIL_APP_PASSWORD = "your_16_digit_app_password" 
        
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        return False
