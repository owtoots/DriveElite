# finance.py
from datetime import datetime

def get_days_before_pickup(scheduled_pickup_str):
    """Calculates days left before the trip starts."""
    date_format = "%Y-%m-%d %H:%M:%S"
    pickup_datetime = datetime.strptime(scheduled_pickup_str, date_format)
    cancellation_datetime = datetime.now()
    
    time_difference = pickup_datetime - cancellation_datetime
    days_left = time_difference.days
    
    if days_left < 0:
        days_left = 0
        
    return days_left

def calculate_moa_cancellation_40_60(gross_rental_paid, logistics_paid, exact_gateway_fee, days_before_pickup):
    """Calculates the exact 40/60 penalty split and renter refund."""
    if days_before_pickup >= 30:
        penalty_percent = 0.0    
    elif 15 <= days_before_pickup <= 29:
        penalty_percent = 0.25   
    elif 7 <= days_before_pickup <= 14:
        penalty_percent = 0.50   
    elif 3 <= days_before_pickup <= 6:
        penalty_percent = 0.75   
    else: 
        penalty_percent = 1.00   

    penalty_amount = gross_rental_paid * penalty_percent
    renter_refund = max((gross_rental_paid + logistics_paid) - penalty_amount - exact_gateway_fee, 0.0)

    if penalty_amount > 0:
        platform_fee = penalty_amount * 0.40
        affiliate_gross_penalty = penalty_amount * 0.60
        
        if renter_refund == 0.0:
            affiliate_net_payout = max(affiliate_gross_penalty - exact_gateway_fee, 0.0)
        else:
            affiliate_net_payout = affiliate_gross_penalty
    else:
        platform_fee = 0.0
        affiliate_net_payout = 0.0

    return {
        "penalty_applied": penalty_amount,
        "renter_refund": renter_refund,
        "nucleuz_platform_fee": platform_fee,
        "affiliate_compensation": affiliate_net_payout
    }
