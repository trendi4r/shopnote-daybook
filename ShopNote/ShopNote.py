import streamlit as st
import pandas as pd
from datetime import date
from db_helper import init_db, fetch_table, get_connection
from auth import check_login

print("DATABASE_URL =", st.secrets["DATABASE_URL"])

st.set_page_config(page_title="ShopNote Daybook", layout="wide")

# 1. RUN DATABASE INITIALIZATION FIRST (Creates the 'users' table on your disk)
init_db()

# 2. NOW RUN THE SECURITY GUARD LOG IN CHECK AFTER TABLES ARE SECURED
check_login()

# --- SIDEBAR LOGOUT SIGN OUT UTILITY ---
with st.sidebar:
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("🚪 Sign Out / Lock Session", use_container_width=True):
        st.session_state["authenticated"] = False
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE session_lock SET is_logged_in = 0 WHERE id = 1")
        conn.commit()
        conn.close()
        
        st.rerun()

st.title("📊 ShopNote")
st.write("Welcome back! Here is your integrated shop overview, daily sales patterns, and chronological history ledger.")

# Fetch latest table records
stock_df = fetch_table("stock")
sales_df = fetch_table("sales")
events_df = fetch_table("events")

# --- GLOBAL CRITICAL LOW STOCK SCANNER WARNING BANNER ---
if not stock_df.empty:
    critical_low_df = stock_df[stock_df["stock"] < 3]
    if not critical_low_df.empty:
        low_items_list = ", ".join([f"'{row['name']}' ({row['stock']} left)" for idx, row in critical_low_df.iterrows()])
        st.error(f"🚨 **Critical Low Stock Alert (< 3 pieces):** Please replenish {low_items_list} immediately!")

# 1. RUN CONSOLIDATED REVENUE & RETURN CALCULATIONS
if not sales_df.empty and not stock_df.empty:
    merged_sales = pd.merge(sales_df, stock_df, on="product_id", how="inner")
    merged_sales["Total_Amount"] = merged_sales["quantity"] * merged_sales["sale_price"]
    
    # Calculate high-level core sums
    realized_revenue = merged_sales[merged_sales["payment_status"] == "Paid"]["Total_Amount"].sum()
    pending_revenue = merged_sales[merged_sales["payment_status"] == "Pending"]["Total_Amount"].sum()
    returned_volumes = merged_sales[merged_sales["payment_status"] == "Returned"]["quantity"].sum()
else:
    realized_revenue = 0.0
    pending_revenue = 0.0
    returned_volumes = 0

# --- 2. NEW: DATE RANGE REVENUE CALCULATOR ---
st.subheader("📆 Calculate Paid Revenue Between Dates")

if not sales_df.empty and not stock_df.empty:
    # Safely convert database string dates to actual datetime objects for precise comparison
    merged_sales["clean_date"] = pd.to_datetime(merged_sales["date"].str.slice(0, 10)).dt.date
    
    # Render side-by-side date picker input boxes
    col_start, col_end = st.columns(2)
    with col_start:
        start_date = st.date_input("Start Date", date.today().replace(day=1)) # Defaults to first day of the current month
    with col_end:
        end_date = st.date_input("End Date", date.today())
        
    if start_date <= end_date:
        # Filter rows that fall within the selected date range and are fully 'Paid'
        range_filtered_df = merged_sales[
            (merged_sales["clean_date"] >= start_date) & 
            (merged_sales["clean_date"] <= end_date) & 
            (merged_sales["payment_status"] == "Paid")
        ]
        
        range_paid_revenue = range_filtered_df["Total_Amount"].sum()
        
        # Display the custom timeframe revenue result inside a prominent banner
        st.info(f"💰 Total Paid Revenue from **{start_date}** to **{end_date}**: **₦{range_paid_revenue:,.2f}**")
    else:
        st.error("Error: Start Date cannot be later than End Date.")
else:
    st.caption("No sales records available to run date range calculations.")

st.markdown("---")

# 3. DAILY SALES PERFORMANCE PATTERN ROLL-UP
st.subheader("🗓️ Daily Sales")

if not sales_df.empty and not stock_df.empty:
    merged_sales["Day"] = merged_sales["date"].str.slice(0, 10)
    merged_sales["Paid_Amount"] = merged_sales.apply(
        lambda row: row["Total_Amount"] if row["payment_status"] == "Paid" else 0.0, axis=1
    )
    
    daily_pattern_df = merged_sales.groupby("Day").agg(
        total_transactions=('sale_id', 'count'),
        paid_daily_revenue=('Paid_Amount', 'sum')
    ).reset_index()
    
    daily_pattern_df = daily_pattern_df.sort_values(by="Day", ascending=False)
    
    display_daily_df = daily_pattern_df.copy()
    display_daily_df["Paid Revenue"] = display_daily_df["paid_daily_revenue"].map("₦{:,.2f}".format)
    display_daily_df = display_daily_df.rename(columns={"Day": "Business Date", "total_transactions": "Transactions Logged"})
    
    st.dataframe(
        display_daily_df[["Business Date", "Transactions Logged", "Paid Revenue"]],
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No transaction records exist yet to calculate daily sales patterns.")

st.markdown("---")

# 4. NEATLY DESIGNED METRICS SUMMARY TABLE
st.subheader("📋 Summary")
summary_table_data = pd.DataFrame({
    "Metric Category": [
        "📦 Products",
        "💰 Sales",
        "💵 Paid Revenue",
        "⏳ Pending Revenue",
        "🔄 Total Return"
    ],
    "Current Count / Balance Value": [
        f"{len(stock_df)} Items",
        f"{len(sales_df)} Transactions",
        f"₦{realized_revenue:,.2f}",
        f"₦{pending_revenue:,.2f}",
        f"{returned_volumes:,} Units"
    ]
})
st.dataframe(summary_table_data, use_container_width=True, hide_index=True)

st.markdown("---")

# 5. CHRONOLOGICAL MASTER TIMELINE HISTORY LEDGER
st.subheader("📜 Complete History Ledger (Sales & Events)")

if not sales_df.empty and not stock_df.empty:
    merged_sales["narration"] = merged_sales["narration"].fillna("").apply(lambda x: f" | Note: {x}" if x != "" else "")
    
    sales_history = pd.DataFrame({
        "Date & Time": merged_sales["date"],
        "Activity Type": "💰 Sale (" + merged_sales["payment_status"] + ")",
        "Description": "Sold " + merged_sales["quantity"].astype(str) + "x " + merged_sales["name"] + " via " + merged_sales["payment_method"] + merged_sales["narration"],
        "Financial Impact": "₦" + merged_sales["Total_Amount"].map("{:,.2f}".format)
    })
    
    if not events_df.empty:
        events_history = pd.DataFrame({
            "Date & Time": events_df["date_time"],
            "Activity Type": "⚠️ Shop Event",
            "Description": events_df["narration"],
            "Financial Impact": "N/A"
        })
        master_history = pd.concat([sales_history, events_history], ignore_index=True)
    else:
        master_history = sales_history

    master_history = master_history.sort_values(by="Date & Time", ascending=False)
    st.dataframe(master_history, use_container_width=True, hide_index=True)
else:
    st.info("No activity records exist yet. Use the sidebar menu to add stock profiles, log new sales, or record shop events.")
