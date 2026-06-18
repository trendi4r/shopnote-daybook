import streamlit as st
import pandas as pd
from db_helper import fetch_table
from auth import check_login

check_login()

st.title("📈 Total Sales & Revenue Analytics")

sales_df = fetch_table("sales")
stock_df = fetch_table("stock")

if not sales_df.empty and not stock_df.empty:
    merged_df = pd.merge(sales_df, stock_df, on="product_id", how="inner")
    merged_df["Total Amount (₦)"] = merged_df["quantity"] * merged_df["sale_price"]
    
    # Segregate Revenue Metrics
    paid_revenue = merged_df[merged_df["payment_status"] == "Paid"]["Total Amount (₦)"].sum()
    pending_revenue = merged_df[merged_df["payment_status"] == "Pending"]["Total Amount (₦)"].sum()
    returned_units = merged_df[merged_df["payment_status"] == "Returned"]["quantity"].sum()

    # Display Metrics KPI Board
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Realized Revenue (Paid)", f"₦{paid_revenue:,.2f}")
    col2.metric("⏳ Outstanding Revenue (Pending)", f"₦{pending_revenue:,.2f}")
    col3.metric("🔄 Returned Product Volumes", f"{returned_units:,} units")
    
    st.markdown("---")
    
    # Filter Controls
    st.subheader("🔍 Filter Sales Performance Records")
    status_filter = st.multiselect(
        "Filter by Payment/Transaction Status:", 
        options=["Paid", "Pending", "Returned"], 
        default=["Paid", "Pending", "Returned"]
    )
    
    filtered_df = merged_df[merged_df["payment_status"].isin(status_filter)]
    
    if not filtered_df.empty:
        st.subheader("Sales Revenue Trend Graph")
        chart_data = filtered_df.groupby("date")["Total Amount (₦)"].sum().reset_index()
        st.line_chart(data=chart_data, x="date", y="Total Amount (₦)")
        
        st.subheader("Annotated Sales Breakdown List")
        filtered_df["Total Cost"] = filtered_df["Total Amount (₦)"].map("₦{:,.2f}".format)
        filtered_df["narration"] = filtered_df["narration"].fillna("").replace("", "No notes")
        
        final_table_view = filtered_df[[
            "name", "quantity", "Total Cost", "payment_status", "narration", "date"
        ]]
        
        # Sort Chronologically Newest First
        final_table_view = final_table_view.sort_values(by="date", ascending=False)
        st.dataframe(final_table_view, use_container_width=True, hide_index=True)
    else:
        st.warning("Please check at least one status option filter box above to visualize metrics trends.")
else:
    st.info("No sales records available yet to generate a financial analytics dashboard panel.")
