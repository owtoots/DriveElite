import streamlit as st
import pandas as pd
import time

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

        # Create Platform Settings Table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS platform_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                payment_mode TEXT,
                renter_markup_pct REAL,
                affiliate_share_pct REAL,
                operator_name TEXT
            )
        ''')
        
        # Patch missing columns
        for col, ctype in [('payment_mode', 'TEXT'), ('operator_name', 'TEXT')]:
            try: conn.execute(f"ALTER TABLE platform_settings ADD COLUMN {col} {ctype}"); conn.commit()
            except: pass
        
        cursor = conn.cursor()
        
        # Seed default discounts
        cursor.execute("SELECT count(*) FROM discount_tiers")
        if cursor.fetchone()[0] == 0:
            default_tiers = [
                ('3-6 Days', 3, 0.05),
                ('1 Week (7+ Days)', 7, 0.10),
                ('2 Weeks (14+ Days)', 14, 0.15),
                ('1 Month (30+ Days)', 30, 0.20)
            ]
            conn.executemany("INSERT INTO discount_tiers VALUES (?, ?, ?)", default_tiers)
            
        # Seed default platform margins
        cursor.execute("SELECT count(*) FROM platform_settings")
        if cursor.fetchone()[0] == 0:
            conn.execute("INSERT INTO platform_settings (id, payment_mode, renter_markup_pct, affiliate_share_pct, operator_name) VALUES (1, 'MANUAL_QR', 0.07, 0.82, 'DriveElite Platform')")
            
        conn.commit()
    except Exception as e:
        st.error(f"Database Initialization Error: {e}")

def render_platform_settings(conn):
    """UI for the Admin to adjust Renter Fees, Affiliate Payouts, and Operator Name."""
    st.markdown("### 1. Platform Details & Revenue Margins")
    st.caption("Adjust the service fee charged to Renters, the share given to Affiliates, and the entity name printed on official receipts.")

    init_discount_db(conn)

    try:
        settings_df = pd.read_sql_query("SELECT renter_markup_pct, affiliate_share_pct, operator_name FROM platform_settings WHERE id = 1", conn)
        if not settings_df.empty:
            raw_r = settings_df.iloc[0]['renter_markup_pct']
            curr_renter_markup = float(raw_r) * 100 if pd.notnull(raw_r) else 7.0
            
            raw_a = settings_df.iloc[0]['affiliate_share_pct']
            curr_affiliate_share = float(raw_a) * 100 if pd.notnull(raw_a) else 82.0
            
            raw_op = settings_df.iloc[0]['operator_name']
            curr_operator = str(raw_op) if pd.notnull(raw_op) else "DriveElite Platform"
        else:
            curr_renter_markup, curr_affiliate_share, curr_operator = 7.0, 82.0, "DriveElite Platform"
    except:
        curr_renter_markup, curr_affiliate_share, curr_operator = 7.0, 82.0, "DriveElite Platform"

    with st.container(border=True):
        with st.form("settings_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                new_r_pct = st.number_input("Renter Platform Fee (%)", value=curr_renter_markup, step=1.0)
                st.caption(f"*Renter Multiplier: {1 + (new_r_pct/100.0):.2f}x*")
            with col2:
                new_a_pct = st.number_input("Affiliate Revenue Share (%)", value=curr_affiliate_share, step=1.0)
                st.caption(f"*Platform Cut: {100 - new_a_pct}%*")
            with col3:
                new_operator = st.text_input("Receipt Issuing Entity", value=curr_operator)
                st.caption("*Printed on Contracts & PDFs*")
            
            st.write("") 
            if st.form_submit_button("SAVE PLATFORM SETTINGS", type="primary", use_container_width=True):
                try:
                    check = pd.read_sql_query("SELECT id FROM platform_settings WHERE id = 1", conn)
                    
                    if check.empty:
                        conn.execute("""
                            INSERT INTO platform_settings (id, renter_markup_pct, affiliate_share_pct, operator_name, payment_mode) 
                            VALUES (1, ?, ?, ?, 'MANUAL_QR')
                        """, (new_r_pct / 100.0, new_a_pct / 100.0, new_operator))
                    else:
                        conn.execute("""
                            UPDATE platform_settings 
                            SET renter_markup_pct = ?, affiliate_share_pct = ?, operator_name = ? 
                            WHERE id = 1
                        """, (new_r_pct / 100.0, new_a_pct / 100.0, new_operator))
                        
                    conn.commit()
                    st.success(f"✅ Settings Saved! Platform Fee is now {new_r_pct}%.")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"🚨 Error saving settings: {e}")

def render_admin_discount_table(conn):
    st.markdown("### 2. Duration Discount Tiers")
    st.caption("Changes here reflect instantly on the Renter's final price calculation.")
    
    init_discount_db(conn)
    
    try:
        df = pd.read_sql_query("SELECT * FROM discount_tiers ORDER BY min_days ASC", conn)
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
        
        if st.button("SAVE DISCOUNT RULES", type="primary", use_container_width=True):
            conn.execute("DELETE FROM discount_tiers")
            edited_df.to_sql("discount_tiers", conn, if_exists="append", index=False)
            st.success("✅ Discount rules updated successfully!")
            time.sleep(1)
            st.rerun()
    except Exception as e:
        st.error(f"Error loading discount tiers: {e}")
