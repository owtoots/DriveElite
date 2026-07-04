# -------------------------------------------------------------
                                    # CHECKOUT STAGE 1: VALIDATE BPI PAYMENT 
                                    # -------------------------------------------------------------
                                    elif st.session_state[stage_key] == 1:
                                        
                                        # 1. Safely grab the booking reference from session state FIRST
                                        b_ref = st.session_state.get(ref_key)
                                        
                                        # 2. SUCCESS CONFIRMATION BOX
                                        st.markdown(f"""
                                        <div style="background-color: #F0FDF4; border: 1px solid #BBF7D0; padding: 20px; border-radius: 12px; border-left: 6px solid #16A34A; margin-bottom: 20px;">
                                            <h4 style="color: #166534; margin-top: 0; margin-bottom: 8px;">✅ Reservation Confirmed (Ref: #{b_ref})</h4>
                                            <p style="color: #15803D; font-size: 15px; margin-bottom: 0; line-height: 1.5;">
                                                Thank you for booking with DriveElite. We have notified the vehicle's Affiliate of your confirmed schedule. 
                                                Kindly expect a direct message via the built-in DriveElite chat system within the next few hours to finalize your logistics and key handover.
                                            </p>
                                        </div>
                                        """, unsafe_allow_html=True)
                                        
                                        # 3. MANUAL BANK TRANSFER CONTAINER
                                        with st.container(border=True):
                                            st.markdown("### 🏦 Manual Bank Transfer")
                                            st.write("**Bank:** BPI")
                                            st.write("**Account Name:** Romeo Albao Jr.")
                                            st.write("**Account Number:** 0180 0206 08")
                                            
                                            # Fetch the owed amount safely now that we have b_ref
                                            amt_df = pd.read_sql_query("SELECT amount FROM bookings WHERE booking_ref = ?", conn, params=(b_ref,))
                                            owed_amount = float(amt_df.iloc[0]['amount']) if not amt_df.empty else 0.0
                                            st.write(f"**Amount to Transfer:** :green[**₱{owed_amount:,.2f}**]")
                                            
                                            s1, c_img, s2 = st.columns([1, 1, 1])
                                            with c_img:
                                                try: 
                                                    st.image("bpi_qr.png", use_container_width=True)
                                                except: 
                                                    st.info("[BPI QR IMAGE GOES HERE]")
                                            
                                            st.divider()
                                            st.write("#### 📤 Upload Proof of Payment")
                                            st.caption("Upload a screenshot of your transfer. Admin will lock your schedule upon validation.")
                                            
                                            receipt_file = st.file_uploader("Upload Receipt", type=['jpg', 'png', 'jpeg'], key=f"rec_{car['id']}_{cat}")
                                            
                                            c_back, c_val = st.columns([1, 2])
                                            
                                            # Cancel Booking Logic
                                            if c_back.button("Cancel Booking", key=f"canc_{car['id']}_{cat}", use_container_width=True):
                                                conn.execute("DELETE FROM bookings WHERE booking_ref = ?", (b_ref,))
                                                conn.commit()
                                                st.session_state[stage_key] = 0
                                                del st.session_state[ref_key]
                                                st.rerun()
                                            
                                            # Validate Payment Logic
                                            if c_val.button("2. VALIDATE PAYMENT SENT", type="primary", use_container_width=True, key=f"val_{car['id']}_{cat}"):
                                                if receipt_file:
                                                    receipt_bytes = receipt_file.read()
                                                    with st.spinner("Transmitting to Admin..."):
                                                        conn.execute("UPDATE bookings SET receipt_img = ?, status = 'VERIFYING' WHERE booking_ref = ?", (receipt_bytes, b_ref))
                                                        conn.commit()
                                                        
                                                        # (Your email and chat message insertion code goes here!)
                                                        
                                                        st.toast("✅ Receipt Sent to Admin!")
                                                        st.session_state[stage_key] = 0
                                                        del st.session_state[ref_key]
                                                        st.session_state.just_booked_ref = b_ref
                                                        st.rerun()
                                                else:
                                                    st.error("🚨 Please upload a screenshot of your receipt.")

                                        # 4. RETURN TO LANDING PAGE BUTTON
                                        st.write("") # Add a little spacing
                                        if st.button("🏠 RETURN TO LANDING PAGE", key=f"return_main_{car['id']}_{cat}", type="primary", use_container_width=True):
                                            st.session_state.current_page = "JOIN"
                                            st.rerun()
