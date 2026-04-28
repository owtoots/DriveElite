import streamlit as st
import pandas as pd

def init_discount_db(conn):
    """Creates the discount tiers and platform settings tables."""
    try:
        # 1. Discount Tiers Table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS discount_tiers (
                tier_name TEXT PRIMARY KEY,
                min_days INTEGER,
                discount_pct REAL
            )
        ''')
        
        # 2. NEW: Platform Settings Table (For Fees & Margins)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS platform_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                renter_markup_pct REAL,
                affiliate_share_pct REAL
            )
        ''')
        
        cursor = conn.cursor()
        
        # Seed default discounts if empty
        cursor.execute("SELECT count(*) FROM discount_tiers")
        if cursor.fetchone()[0] == 0:
            conn.executemany("INSERT INTO discount_tiers VALUES (?, ?, ?)", [
                ('3 Days to 6 Days', 3, 0.05),
                ('1 Week (7+ Days)', 7, 0.10),
                ('2 Weeks (14+ Days)', 14, 0.15),
                ('1 Month (30+ Days)', 30, 0.20)
            ])
            
        # Seed default margins if empty (7% Renter Fee, 82% Affiliate Share)
        cursor.execute("SELECT count(*) FROM platform_settings")
        if cursor.fetchone()[0] == 0:
            conn.execute("INSERT INTO platform_settings (id, renter_markup_pct, affiliate_share_pct) VALUES (1, 0.07, 0.82)")
            
        conn.commit()
    except Exception as e:
        pass

def render_admin_discount_table(conn):
    """Displays the interactive UI in the Admin Dashboard to tweak pricing rules."""
    st.subheader("⚙️ Dynamic Pricing, Fees & Margins")
    
    # ==========================================
    # PART 1: PLATFORM FEES & REVENUE SHARE
    # ==========================================
    st.markdown("#### 1. Platform Revenue Margins")
    st.caption("Set the service fee charged to RENTERS and the revenue share paid to AFFILIATES.")
    
    settings_df = pd.read_sql_query("SELECT * FROM platform_settings WHERE id = 1", conn)
    
    if not settings_df.empty:
        current_renter_markup = float(settings_df.iloc[0]['renter_markup_pct'])
        current_affiliate_share = float(settings_df.iloc[0]['affiliate_share_pct'])
    else:
        current_renter_markup = 0.07
        current_affiliate_share = 0.82

    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            new_r_markup = st.number_input("Renter Platform Fee (%)", min_value=0.0, max_value=100.0, value=current_renter_markup * 100, step=1.0, help="E.g., 10...", key="admin_renter_markup_input")
            st.caption(f"*Multiplier applied to Renter: {1 + new_r_markup:.2f}x*")
        with col2:
            new_a_share = st.number_input("Affiliate Revenue Share (%)", min_value=0.0, max_value=100.0, value=current_affiliate_share * 100, step=1.0, help="E.g., 82% means the platform keeps 18%.") / 100.0
            st.caption(f"*Platform Cut: {100 - (new_a_share * 100):.0f}% | Affiliate Payout: {new_a_share * 100:.0f}%*")

        if st.button("Save Platform Margins", type="primary", key="save_margins", use_container_width=True):
            try:
                conn.execute("UPDATE platform_settings SET renter_markup_pct = ?, affiliate_share_pct = ? WHERE id = 1", (new_r_markup, new_a_share))
                conn.commit()
                st.success("✅ Platform margins successfully updated!")
            except Exception as e:
                st.error(f"🚨 HIDDEN ERROR REVEALED: {str(e)}")

    st.divider()

    # ==========================================
    # PART 2: DURATION DISCOUNT TIERS
    # ==========================================
    st.markdown("#### 2. Duration Discount Tiers")
    st.caption("Adjust the minimum days and discount percentages. Changes apply instantly to new bookings.")

    df_tiers = pd.read_sql_query("SELECT * FROM discount_tiers ORDER BY min_days ASC", conn)

    edited_tiers = st.data_editor(
        df_tiers, 
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "tier_name": st.column_config.TextColumn("Tier Name"),
            "min_days": st.column_config.NumberColumn("Minimum Days", min_value=1),
            "discount_pct": st.column_config.NumberColumn("Discount % (e.g., 0.10 for 10%)", min_value=0.0, max_value=1.0, step=0.01, format="%.2f")
        }
    )

    if st.button("Save Discount Rules", type="primary", key="save_discounts"):
        try:
            conn.execute("DELETE FROM discount_tiers") 
            for _, row in edited_tiers.iterrows():
                t_name = str(row['tier_name'])
                m_days = int(row['min_days'])
                d_pct = float(row['discount_pct'])
                conn.execute("INSERT INTO discount_tiers (tier_name, min_days, discount_pct) VALUES (?, ?, ?)", (t_name, m_days, d_pct))
            conn.commit()
            st.success("✅ Discount tiers successfully updated!")
        except Exception as e:
            st.error(f"🚨 HIDDEN ERROR REVEALED: {str(e)}")

def calculate_tiered_pricing(base_daily_rate, total_days, conn):
    """
    Fetches live discount rules and dynamic platform margins to calculate the final totals.
    """
    # 1. Fetch live margins from the database
    try:
        settings_df = pd.read_sql_query("SELECT * FROM platform_settings WHERE id = 1", conn)
        renter_markup = float(settings_df.iloc[0]['renter_markup_pct'])
        affiliate_share = float(settings_df.iloc[0]['affiliate_share_pct'])
    except:
        renter_markup = 0.07  # Fallback to 7%
        affiliate_share = 0.82 # Fallback to 82%

    # 2. Fetch live discounts from the database
    tiers_df = pd.read_sql_query("SELECT min_days, discount_pct FROM discount_tiers ORDER BY min_days DESC", conn)
    
    # 3. Find the correct discount tier
    discount = 0.0
    for _, row in tiers_df.iterrows():
        if total_days >= row['min_days']:
            discount = float(row['discount_pct'])
            break
            
    # 4. Calculate Base Total
    raw_base_total = base_daily_rate * total_days
    discounted_base_total = raw_base_total * (1 - discount)

    # 5. Apply the Dynamic Margins
    renter_total = discounted_base_total * (1 + renter_markup) 
    affiliate_total = discounted_base_total * affiliate_share 
    platform_profit = renter_total - affiliate_total
    
    return {
        "days": total_days,
        "discount_percent": int(discount * 100),
        "renter_total": renter_total,
        "affiliate_total": affiliate_total,
        "platform_profit": platform_profit
    }
