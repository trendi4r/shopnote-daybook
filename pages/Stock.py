import streamlit as st
import pandas as pd
import base64
import io
from PIL import Image  # Native image editor library
from db_helper import init_db, get_connection, fetch_table
from auth import check_login

# Initialize Google Font layout rules and navigation padding themes
init_db()
check_login()   # <- Must run second!

st.title("📦 Product Stock Management")

stock_df = fetch_table("stock")

# Global Scanner warning banner
if not stock_df.empty:
    critical_low_df = stock_df[stock_df["stock"] < 3]
    if not critical_low_df.empty:
        low_items_text = ", ".join([f"'{row['name']}' ({row['stock']} left)" for idx, row in critical_low_df.iterrows()])
        st.error(f"🚨 **Critical Low Stock Warning (< 3 pieces):** Please replenish {low_items_text} immediately!")

# Add New Inventory Expander Form
with st.expander("➕ Add New Inventory Profile", expanded=False):
    st.info("System Assigned ID: Generated automatically by Cloud Database sequences on creation.")
    with st.form("add_stock_form", clear_on_submit=True):
        p_name = st.text_input("Product Name", placeholder="e.g., Wireless Mouse")
        p_stock = st.number_input("Initial Stock Quantity", min_value=0, value=0, step=1)
        
        # Reference 'sale_price' matching your db_helper mappings
        p_sell = st.number_input("Selling Price (₦)", min_value=0.0, value=0.0, step=50.0)
        
        # ✅ UPDATED LABEL: Reflects the new 5MB limit clearly to the operator
        p_image = st.file_uploader("Upload Product Image (Optional - Max 5MB)", type=["jpg", "png", "jpeg"])
        
        if st.form_submit_button("Add Product"):
            if p_name.strip():
                img_str = None
                is_file_size_valid = True
                
                if p_image is not None:
                    bytes_data = p_image.read()
                    file_size_mb = len(bytes_data) / (1024 * 1024)
                    
                    # ✅ UPDATED CONDITIONAL: Allows file assets up to 5MB safely
                    if file_size_mb > 5.0:
                        st.error(f"❌ Upload Failed: Your image size is **{file_size_mb:.2f}MB**. It must be smaller than **5MB** to save.")
                        is_file_size_valid = False
                    else:
                        # --- PIL AUTOMATIC 1:1 SQUARE CROPPING ENGINE ---
                        raw_image = Image.open(io.BytesIO(bytes_data))
                        width, height = raw_image.size
                        
                        min_dimension = min(width, height)
                        
                        left = (width - min_dimension) / 2
                        top = (height - min_dimension) / 2
                        right = (width + min_dimension) / 2
                        bottom = (height + min_dimension) / 2
                        
                        cropped_image = raw_image.crop((left, top, right, bottom))
                        final_square_image = cropped_image.resize((400, 400), Image.Resampling.LANCZOS)
                        
                        buffered_io = io.BytesIO()
                        final_square_image.convert("RGB").save(buffered_io, format="JPEG", quality=85)
                        processed_bytes = buffered_io.getvalue()
                        
                        img_str = base64.b64encode(processed_bytes).decode("utf-8")
                
                if is_file_size_valid:
                    conn = get_connection()
                    cursor = conn.cursor()
                    try:
                        # Omitted 'product_id' generation fields to let SERIAL sequences trigger automatically
                        # Alter table schema dynamically to support extended metadata columns if missing
                        try:
                            cursor.execute("ALTER TABLE stock ADD COLUMN IF NOT EXISTS image_base64 TEXT;")
                            cursor.execute("ALTER TABLE stock ADD COLUMN IF NOT EXISTS returned_stock INTEGER DEFAULT 0;")
                            cursor.execute("ALTER TABLE stock ADD COLUMN IF NOT EXISTS manufacturer_stock INTEGER DEFAULT 0;")
                            conn.commit()
                        except Exception:
                            pass

                        # Swapped SQLite "?" with PostgreSQL "%s" placeholders
                        cursor.execute(
                            """INSERT INTO stock (name, stock, sale_price, returned_stock, manufacturer_stock, image_base64) 
                               VALUES (%s, %s, %s, %s, %s, %s)""",
                            (p_name.strip(), p_stock, p_sell, 0, 0, img_str)
                        )
                        conn.commit()
                        st.success(f"Successfully saved '{p_name}' to system cloud memory!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Database Error: {e}")
                    finally:
                        conn.close()
            else:
                st.warning("Please type a valid Product Name.")

st.markdown("---")

# --- INTERACTIVE RETURN DECISION LOGIC PANEL ---
st.subheader("🔄 Returned Stock Decisions")

# Dynamic structural checks for tracking returned arrays
if not stock_df.empty and "returned_stock" in stock_df.columns:
    products_with_returns = stock_df[stock_df["returned_stock"] > 0]
else:
    products_with_returns = pd.DataFrame()

if not products_with_returns.empty:
    st.info("Choose an action for returned items:")
    for idx, row in products_with_returns.iterrows():
        col_name, col_count, col_sellable, col_manufacture = st.columns([2, 1.5, 2.5, 2.5])
        with col_name:
            st.write(f"**{row['name']}**")
        with col_count:
            st.write(f"⚠️ {row['returned_stock']} in returns")
        with col_sellable:
            if st.button(f"♻️ Put back to Sellable", key=f"to_sell_{row['product_id']}"):
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE stock SET stock = stock + returned_stock, returned_stock = 0 WHERE product_id = %s", (int(row["product_id"]),))
                conn.commit()
                conn.close()
                st.toast("Transferred back to active inventory!")
                st.rerun()
        with col_manufacture:
            if st.button(f"🏭 Send to Manufacturer", key=f"to_manu_{row['product_id']}"):
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE stock SET manufacturer_stock = manufacturer_stock + returned_stock, returned_stock = 0 WHERE product_id = %s", (int(row["product_id"]),))
                conn.commit()
                conn.close()
                st.toast("Logged as returned to factory!")
                st.rerun()
else:
    st.caption("No returned inventory records currently require operational decisions.")

st.markdown("---")

# --- MAIN CATALOG SPREADSHEET TABLE VIEW ---
st.subheader("📋 Inventory Catalog")
fresh_stock = fetch_table("stock")

if not fresh_stock.empty:
    # Handle optional schema fallbacks
    price_col = "sale_price" if "sale_price" in fresh_stock.columns else "selling_price"
    ret_col = "returned_stock" if "returned_stock" in fresh_stock.columns else "stock"
    manu_col = "manufacturer_stock" if "manufacturer_stock" in fresh_stock.columns else "stock"
    
    if ret_col not in fresh_stock.columns: fresh_stock[ret_col] = 0
    if manu_col not in fresh_stock.columns: fresh_stock[manu_col] = 0

    fresh_stock["Item_Total_Value"] = fresh_stock["stock"] * fresh_stock[price_col].astype(float)
    total_shop_worth = fresh_stock["Item_Total_Value"].sum()
    st.info(f"💎 **Total Active Stock Valuation:** **₦{total_shop_worth:,.2f}**")

    suggestion_list = fresh_stock.apply(lambda r: f"{r['name']} ({r['product_id']})", axis=1).tolist()
    search_options = ["All Products"] + suggestion_list
    selected_suggestion = st.selectbox("🔍 Live Product Search & Auto-Suggest:", options=search_options, index=0)

    filtered_stock = fresh_stock if selected_suggestion == "All Products" else fresh_stock[fresh_stock["product_id"] == int(selected_suggestion.split("(")[-1].replace(")", "").strip())]

    if not filtered_stock.empty:
        display_stock_df = filtered_stock.copy()
        display_stock_df["Selling Price"] = display_stock_df[price_col].astype(float).map("₦{:,.2f}".format)
        display_stock_df = display_stock_df.rename(columns={
            "name": "Product Name", 
            "stock": "Sellable Stock Count", 
            ret_col: "Returned Stock (Pending Decision)"
        })
        
        st.dataframe(
            display_stock_df[["Product Name", "Sellable Stock Count", "Selling Price", "Returned Stock (Pending Decision)"]],
            use_container_width=True, hide_index=True
        )

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("🏭 Factory Returns Log")
    factory_returns_df = fresh_stock[fresh_stock[manu_col] > 0]
    
    if not factory_returns_df.empty:
        factory_display_df = factory_returns_df.copy().rename(columns={
            "name": "Product Name", 
            manu_col: "Factory Stock Units"
        })
        st.dataframe(
            factory_display_df[["Product Name", "Factory Stock Units"]],
            use_container_width=True, hide_index=True
        )
    else:
        st.info("No factory dispatch return configurations recorded.")
else:
    st.info("Your data catalog is blank. Use the expansion panel form above to initialize tracking parameters.")
