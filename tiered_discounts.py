import streamlit as st
import pandas as pd

def init_discount_db(conn):
    """Initializes tables for discounts and platform settings with default values."""
    try:
        # Create Discount Tiers Table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS discount_tiers (
                tier_name TEXT PRIMARY KEY,
                min_days INTEGER,
                discount_pct REAL
            )
        ''')
        
        # Create Platform Settings Table (Fee & Revenue Share)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS platform_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                renter_markup_pct REAL,
                affiliate_share_pct REAL
            )
        ''')
        
        cursor = conn.cursor()
        
        # Seed default discounts if the table is empty
        cursor.execute("SELECT count(*) FROM discount_tiers")
        if cursor.fetchone()[0] == 0:
            default_tiers = [
                ('3-6 Days', 3, 0.05),
                ('1 Week (7+ Days)', 7, 0.10),
                ('2 Weeks (14+ Days)', 14, 0.15),
                ('1 Month (30+ Days)', 30, 0.20)
            ]
            conn.executemany("INSERT INTO discount_tiers VALUES (?, ?, ?)", default_tiers)
            
        # Seed default platform margins if empty (7% Renter Fee, 82% Affiliate Share)
        cursor.execute("SELECT count(*) FROM platform_settings")
        if cursor.fetchone()[0] == 0:
            conn.execute("INSERT INTO platform_settings (id, renter_markup_pct, affiliate_share_pct) VALUES (1, 0.07, 0.82)")
            
        conn.commit()
    except Exception as e:
        st.error(f"Database Initialization Error: {e}")

def render_platform_settings(conn):
    """UI for the Admin to adjust Renter Fees and Affiliate Payouts."""
    st.markdown("#### 1. Platform Revenue Margins")
    st.caption("Adjust the service fee charged to Renters and the share given to Affiliates.")
    
    settings_df = pd.read_sql_query("SELECT * FROM platform_settings WHERE id = 1", conn)
    
    # Fallback to defaults if DB query fails or is empty
    if not settings_df.empty:
        curr_renter_markup = float(settings_df.iloc[0]['renter_markup_pct'])
        curr_affiliate_share = float(settings_df.iloc[0]['affiliate_share_pct'])
    else:
        curr_renter_markup, curr_affiliate_share = 0.07, 0.82

    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            r_input = st.number_input("Renter Platform Fee (%)", 0.0, 100.0, curr_renter_markup * 100, step=1.0, key="fee_r")
            new_r_markup = r_input / 100.0
            st.caption(f"*Renter Multiplier: {1 + new_r_markup:.2f}x*")
        
        with col2:
            a_input = st.number_input("Affiliate Revenue Share (%)", 0.0, 100.0, curr_affiliate_share * 100, step=1.0, key="share_a")
            new_a_share = a_input / 100.0
            st.caption(f"*Platform Cut: {100 - (new_a_share * 100):.0f}%*")
        
        if st.button("Save Platform Margins", type="primary", use_container_width=True):
            try:
                conn.execute("UPDATE platform_settings SET renter_markup_pct = ?, affiliate_share_pct = ? WHERE id = 1", 
                             (new_r_markup, new_a_share))
                conn.commit()
                st.success("✅ Platform margins updated!")
            except Exception as e:
                st.error(f"Failed to update margins: {e}")

def render_admin_discount_table(conn):
    """UI for the Admin to manage duration-based discounts via an interactive table."""
    st.markdown("#### 2. Duration Discount Tiers")
    st.caption("Changes here reflect instantly on the Renter's final price calculation.")

    df_tiers = pd.read_sql_query("SELECT * FROM discount_tiers ORDER BY min_days ASC", conn)

    edited_tiers = st.data_editor(
        df_tiers, 
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "tier_name": st.column_config.TextColumn("Tier Label"),
            "min_days": st.column_config.NumberColumn("Min Days", min_value=1),
            "discount_pct": st.column_config.NumberColumn("Discount (0.10 = 10%)", min_value=0.0, max_value=1.0, format="%.2f")
        }
    )

    if st.button("Save Discount Rules", type="primary"):
        try:
            conn.execute("DELETE FROM discount_tiers") 
            for _, row in edited_tiers.iterrows():
                conn.execute("INSERT INTO discount_tiers (tier_name, min_days, discount_pct) VALUES (?, ?, ?)", 
                             (str(row['tier_name']), int(row['min_days']), float(row['discount_pct'])))
            conn.commit()
            st.success("✅ Discount tiers updated!")
        except Exception as e:
            st.error(f"Failed to save discounts: {e}")

def calculate_tiered_pricing(base_daily_rate, total_days, conn):
    """Calculates final totals, applying Renter Markup ONLY on day 4 and onward."""
    try:
        settings = pd.read_sql_query("SELECT * FROM platform_settings WHERE id = 1", conn)
        r_markup = float(settings.iloc[0]['renter_markup_pct'])
        a_share = float(settings.iloc[0]['affiliate_share_pct'])
    except:
        r_markup, a_share = 0.07, 0.82

    # Find the highest applicable duration discount
    tiers = pd.read_sql_query("SELECT min_days, discount_pct FROM discount_tiers ORDER BY min_days DESC", conn)
    discount = 0.0
    for _, row in tiers.iterrows():
        if total_days >= row['min_days']:
            discount = float(row['discount_pct'])
            break
            
    # Base Calculations
    raw_total = base_daily_rate * total_days
    discounted_base = raw_total * (1 - discount)
    
    # 🚨 THE 4-DAY RULE: Renter only pays the platform fee if booking >= 4 days
    applied_r_markup = r_markup if total_days >= 4 else 0.0
    
    renter_final = discounted_base * (1 + applied_r_markup)
    affiliate_final = discounted_base * a_share
    
    return {
        "days": total_days,
        "discount_percent": int(discount * 100),
        "renter_total": round(renter_final, 2),
        "affiliate_total": round(affiliate_final, 2),
        "platform_profit": round(renter_final - affiliate_final, 2)
    }
