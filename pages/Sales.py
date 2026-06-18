import streamlit as st
import pandas as pd
from datetime import datetime
from db_helper import init_db, get_connection, fetch_table
from auth import check_login

# Initialize Google Font typography configurations globally
init_db()
check_login()

st.title("💰 Sales Record Logger")

# --- COMPRESS SPACING LAYOUT FOR QUICK SCANNABILITY ---
st.markdown("""
    <style>
    div[data-testid="stColumn"] { padding: 0px 4px !important; margin: 0px !important; }
    @media (max-width: 768px) {
        div[data-testid="stHorizontalBlock"] { gap: 4px !important; padding: 0px !important; }
        div[data-baseweb="select"] { padding: 2px 4px !important; }
        p, span, label { line-height: 1.2 !important; }
        .stSelectbox select { padding-top: 4px !important; padding-bottom: 4px !important; }
    }
    /* Custom CSS blocks for inventory status highlights */
    .stock-pill {
        padding: 10px 15px;
        border-radius: 8px;
        font-weight: 600;
        margin-bottom: 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .stock-good { background-color: rgba(46, 117, 89, 0.15); border: 1px solid #2e7559; color: #2e7559; }
    .stock-low { background-color: rgba(217, 119, 6, 0.15); border: 1px solid #d97706; color: #d97706; }
    .stock-none { background-color: rgba(220, 38, 38, 0.15); border: 1px solid #dc2424; color: #dc2424; }
    </style>
""", unsafe_allow_html=True)

stock_df = fetch_table("stock")
sales_df = fetch_table("sales")
events_df = fetch_table("events")

if stock_df.empty:
    st.warning("Please add products to your stock inventory before logging activities.")
else:
    # --- COMPACT DROP-DOWN LOGGING FORM ---
    with st.expander("📝 Log New Sale", expanded=False):
        product_names_list = stock_df["name"].tolist()
        selected_product_name = st.selectbox("Select Product to Sell", product_names_list, key="sales_prod_select")
        
        product_row = stock_df[stock_df["name"] == selected_product_name].iloc[0]
        
        # ✅ FIXED SCHEMA FIELD: Swapped 'selling_price' with 'sale_price' matching your db_helper definitions
        price_field = "sale_price" if "sale_price" in product_row else "selling_price"
        locked_selling_price = float(product_row[price_field])
        p_id = int(product_row["product_id"])
        current_stock = int(product_row["stock"])

        # --- DYNAMIC INVENTORY HIGHLIGHTER ENGINE ---
        if current_stock > 5:
            st.markdown(f"""
                <div class="stock-pill stock-good">
                    <span>🟢 In Stock: Active Inventory</span>
                    <span><strong>{current_stock} units left</strong> | ₦{locked_selling_price:,.2f}</span>
                </div>
            """, unsafe_allow_html=True)
            is_sold_out = False
        elif current_stock > 0:
            st.markdown(f"""
                <div class="stock-pill stock-low">
                    <span>⚠️ Low Stock Alert: Replenish Soon</span>
                    <span><strong>{current_stock} units left</strong> | ₦{locked_selling_price:,.2f}</span>
                </div>
            """, unsafe_allow_html=True)
            is_sold_out = False
        else:
            st.markdown(f"""
                <div class="stock-pill stock-none">
                    <span>🚨 Out of Stock Emergency</span>
                    <span><strong>0 units available</strong> | Sales Locked</span>
                </div>
            """, unsafe_allow_html=True)
            is_sold_out = True

        with st.form("log_sale_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                s_qty = st.number_input("Quantity Sold", min_value=1, value=1, step=1, disabled=is_sold_out)
                s_method = st.selectbox("Payment Method", ["Bank Transfer", "Cash"], disabled=is_sold_out)
            with col2:
                s_status = st.selectbox("Payment Status", ["Paid", "Pending", "Returned"], disabled=is_sold_out)
            
            s_narration = st.text_input("Narration / Sales Notes", placeholder="e.g., Paid via customer POS transfer...", disabled=is_sold_out)

            if st.form_submit_button("Submit Sale", disabled=is_sold_out):
                if current_stock >= s_qty:
                    new_stock = int(current_stock - s_qty)
                    auto_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    conn = get_connection()
                    cursor = conn.cursor()
                    
                    # ✅ FIXED: Swapped SQLite "?" with PostgreSQL "%s" placeholders
                    cursor.execute("UPDATE stock SET stock = %s WHERE product_id = %s", (new_stock, p_id))
                    
                    if s_status == "Returned":
                        # Ensure your table has this column if you track returned items explicitly on the stock row
                        try:
                            cursor.execute("UPDATE stock SET returned_stock = returned_stock + %s WHERE product_id = %s", (s_qty, p_id))
                        except Exception:
                            pass
                        
                    # ✅ FIXED: Swapped SQLite "?" with PostgreSQL "%s" placeholders
                    cursor.execute(
                        """INSERT INTO sales (product_id, quantity, sale_price, payment_status, payment_method, date, narration) 
                           VALUES (%s, %s, %s, %s, %s, %s, %s)""", 
                        (p_id, s_qty, locked_selling_price, s_status, s_method, auto_timestamp, s_narration.strip())
                    )
                    conn.commit()
                    conn.close()
                    st.success(f"Log Successful: Sold {s_qty}x '{selected_product_name}'!")
                    st.rerun()
                else:
                    st.error(f"Insufficient stock balance! Only {current_stock} units left on shelf slots.")

    # --- UNIFIED TIMELINE PROCESSING ENVIRONMENT ---
    st.markdown("---")
    st.subheader("📋 History")
    
    if not sales_df.empty or not events_df.empty:
        sales_timeline = pd.DataFrame()
        events_timeline = pd.DataFrame()
        
        if not sales_df.empty:
            merged_sales = pd.merge(sales_df, stock_df, on="product_id", how="left")
            
            # Use matching column field handles dynamically
            sales_p_field = "sale_price_x" if "sale_price_x" in merged_sales else "sale_price"
            merged_sales["Total_₦"] = merged_sales["quantity"] * merged_sales[sales_p_field]
            
            sales_timeline = pd.DataFrame({
                "Date & Time": merged_sales["date"],
                "Activity Type": "💰 Sale Transaction",
                "Product / Event": merged_sales["name"].fillna("Unknown Product"),
                "Qty": merged_sales["quantity"],
                "Total Amount": merged_sales["Total_₦"],
                "Payment Method": merged_sales["payment_method"],
                "Narration": merged_sales["narration"].fillna(""),
                "Payment Status": merged_sales["payment_status"],
                "internal_id": merged_sales["sale_id"],
                "product_id": merged_sales["product_id"],
                "is_sale": True
            })

        if not events_df.empty:
            events_timeline = pd.DataFrame({
                "Date & Time": events_df["date_time"],
                "Activity Type": "⚠️ Shop Event",
                "Product / Event": events_df["narration"],
                "Qty": 0,
                "Total Amount": 0.0,
                "Payment Method": "-",
                "Narration": "Operational Log",
                "Payment Status": "-",
                "internal_id": events_df["event_id"],
                "product_id": "-",
                "is_sale": False
            })
            
        # Combine logs and calculate distinct day keys
        master_timeline = pd.concat([sales_timeline, events_timeline], ignore_index=True)
        master_timeline["Date & Time"] = master_timeline["Date & Time"].astype(str)
        master_timeline["Day_Key"] = master_timeline["Date & Time"].str[:10]
        
        # Priority ranking
        master_timeline["Priority"] = 2

        # Pending sales = highest priority
        master_timeline.loc[
            (master_timeline["is_sale"] == True) & (master_timeline["Payment Status"] == "Pending"),
            "Priority"
        ] = 0

        # Paid sales = second priority
        master_timeline.loc[
            (master_timeline["is_sale"] == True) & (master_timeline["Payment Status"] == "Paid"),
            "Priority"
        ] = 1

        # ✅ FIXED: Finished the cut-off sort parameters smoothly 
        master_timeline = master_timeline.sort_values(
            by=["Priority", "Date & Time"],
            ascending=[True, False]
        )
        
        # Display the formatted DataFrame to the user
        display_timeline = master_timeline[[
            "Date & Time", "Activity Type", "Product / Event", 
            "Qty", "Total Amount", "Payment Status", "Payment Method"
        ]].copy()
        
        display_timeline["Total Amount"] = display_timeline["Total Amount"].map("₦{:,.2f}".format)
        st.dataframe(display_timeline, use_container_width=True, hide_index=True)
    else:
        st.info("No transaction records exist yet to populate the operations log.")
