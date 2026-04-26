import streamlit as st
import pandas as pd

def init_discount_db(conn):
    """Creates the discount_tiers table and seeds it with default values if empty."""
    try:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS discount_tiers (
                tier_name TEXT PRIMARY KEY,
                min_days INTEGER,
                discount_pct REAL
            )
        ''')
        
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM discount_tiers")
        if cursor.fetchone()[0] == 0:
            conn.executemany("INSERT INTO discount_tiers VALUES (?, ?, ?)", [
                ('3 Days to 6 Days', 3, 0.05),
                ('1 Week (7+ Days)', 7, 0.10),
                ('2 Weeks (14+ Days)', 14, 0.15),
                ('1 Month (30+ Days)', 30, 0.20)
            ])
            conn.commit()
    except Exception as e:
        pass

def render_admin_discount_table(conn):
    """Displays the interactive table in the Admin Dashboard to tweak pricing rules."""
    st.subheader("⚙️ Dynamic Pricing & Discounts")
    st.caption("Adjust the minimum days and discount percentages below. Changes apply instantly.")

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

    if st.button("Save Discount Rules", type="primary"):
        conn.execute("DELETE FROM discount_tiers") 
        for _, row in edited_tiers.iterrows():
            
            # --- THE FIX: Convert Pandas/Numpy data types to standard Python types ---
            t_name = str(row['tier_name'])
            m_days = int(row['min_days'])
            d_pct = float(row['discount_pct'])
            
            conn.execute("INSERT INTO discount_tiers (tier_name, min_days, discount_pct) VALUES (?, ?, ?)", 
                         (t_name, m_days, d_pct))
        conn.commit()
        st.success("✅ Discount tiers successfully updated!")

def calculate_tiered_pricing(base_daily_rate, total_days, conn):
    """
    Fetches live discount rules, applies them, and calculates the 
    7% Renter markup and 18% Affiliate deduction.
    """
    # 1. Fetch live discounts from the database
    tiers_df = pd.read_sql_query("SELECT min_days, discount_pct FROM discount_tiers ORDER BY min_days DESC", conn)
    
    # 2. Find the correct discount tier
    discount = 0.0
    for _, row in tiers_df.iterrows():
        if total_days >= row['min_days']:
            discount = float(row['discount_pct'])
            break
            
    # 3. Calculate Base Total
    raw_base_total = base_daily_rate * total_days
    discounted_base_total = raw_base_total * (1 - discount)

    # 4. Split the Margins (7% Renter / 18% Affiliate)
    renter_total = discounted_base_total * 1.07 
    affiliate_total = discounted_base_total * 0.82 
    platform_profit = renter_total - affiliate_total
    
    return {
        "days": total_days,
        "discount_percent": int(discount * 100),
        "renter_total": renter_total,
        "affiliate_total": affiliate_total,
        "platform_profit": platform_profit
    }
