import streamlit as st
import pandas as pd
import base64
import io
from PIL import Image
from db_helper import init_db, fetch_table
from auth import check_login

# Initialize Google Font layout themes and global styling parameters
init_db()
check_login()

st.title("🖼️ Visual Inventory Gallery")
st.write("Browse your live inventory items alongside their saved media profiles and catalog statuses.")

# --- FORCE MOBILE VIEW TO DISPLAY 3 ITEMS IN A ROW USING CSS FLEXBOX ---
st.markdown("""
    <style>
    /* 1. Target the master container division holding columns block wrappers */
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: wrap !important;
        justify-content: flex-start !important;
        gap: 6px !important; /* Extremely tight padding gaps for phone view */
        width: 100% !important;
    }
    
    /* 2. Force each single column card container block to take exactly ~31% of the row space */
    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
        flex: 1 1 calc(33.333% - 8px) !important;
        min-width: calc(33.333% - 8px) !important;
        max-width: calc(33.333% - 8px) !important;
        padding: 4px !important;
        margin: 0px !important;
    }
    
    /* 3. Ultra-compact typography sizes matching the micro card grid constraints */
    .gallery-card-title {
        font-size: 11px !important;
        font-weight: 700 !important;
        margin-top: 2px !important;
        margin-bottom: 1px !important;
        line-height: 1.1 !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important; /* Cuts off long names cleanly with dots (...) */
    }
    .gallery-card-text {
        font-size: 9px !important;
        margin-bottom: 1px !important;
        line-height: 1.1 !important;
    }
    
    .image-placeholder {
        background-color: rgba(128,128,128,0.06); 
        aspect-ratio: 1 / 1; 
        display: flex; 
        align-items: center; 
        justify-content: center; 
        border-radius: 4px; 
        border: 1px dashed rgba(128,128,128,0.2);
    }
    </style>
""", unsafe_allow_html=True)

stock_df = fetch_table("stock")

if not stock_df.empty:
    search_query = st.text_input("🔍 Search Image Gallery:", placeholder="Type a product name to search...").strip().lower()
    
    if search_query:
        filtered_df = stock_df[stock_df["name"].str.lower().str.contains(search_query)]
    else:
        filtered_df = stock_df

    if not filtered_df.empty:
        # We loop and draw everything inside a single master horizontal block wrapper row thread
        # The advanced CSS rule above will automatically calculate wrapping positions into clean 3x3 rows
        cols = st.columns(len(filtered_df))
        
        for idx, row in filtered_df.reset_index(drop=True).iterrows():
            with cols[idx]:
                
                # ✅ FIXED CACHED FIELD CHECK: Prevent crashes if database table image schema falls back
                has_image = "image_base64" in row and pd.notna(row["image_base64"]) and row["image_base64"] != ""
                
                # RENDER 4x4 SQUARE IMAGE BLOCK
                if has_image:
                    try:
                        img_bytes = base64.b64decode(row["image_base64"])
                        img_io = io.BytesIO(img_bytes)
                        pil_image = Image.open(img_io)
                        
                        st.image(pil_image, use_container_width=True)
                    except Exception:
                        st.markdown('<div class="image-placeholder"><span style="opacity:0.5; font-size:9px;">⚠️ Error</span></div>', unsafe_allow_html=True)
                else:
                    st.markdown("""
                        <div class="image-placeholder">
                            <span style="opacity: 0.4; font-size: 9px; text-align: center;">📷 No Image</span>
                        </div>
                    """, unsafe_allow_html=True)
                
                # RENDER MICRO CARD TYPOGRAPHY TEXT METADATA
                st.markdown(f'<p class="gallery-card-title" title="{row["name"]}">{row["name"]}</p>', unsafe_allow_html=True)
                
                # ✅ FIXED FIELD REFERENCE: Use 'sale_price' matching your db_helper definitions instead of 'selling_price'
                price_field = "sale_price" if "sale_price" in row else "selling_price"
                st.markdown(f'<p class="gallery-card-text">₦{row[price_field]:,.0f}</p>', unsafe_allow_html=True)
                
                qty = int(row["stock"])
                if qty > 5:
                    st.markdown(f'<p class="gallery-card-text" style="color: #2e7559;">📦 Stock: {qty}</p>', unsafe_allow_html=True)
                elif qty > 0:
                    st.markdown(f'<p class="gallery-card-text" style="color: #d97706;">⚠️ Low: {qty}</p>', unsafe_allow_html=True)
                else:
                    st.markdown('<p class="gallery-card-text" style="color: #dc2424;">🚨 Out</p>', unsafe_allow_html=True)
                
                # Spacing row gap bounds
                st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
    else:
        st.warning("No products found matching your search term.")
else:
    st.info("Your database catalogue is currently blank. Go to the Stock page to register items with images.")
