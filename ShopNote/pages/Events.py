import streamlit as st
from datetime import datetime
from db_helper import get_connection, fetch_table
from auth import check_login

check_login()

st.title("📅 Shop Events Logger")
st.write("Record operational events to track chronologically alongside your sales history.")

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

# The form now only asks for the Narration description
with st.form("log_event_form", clear_on_submit=True):
    e_narration = st.text_input("Narration", placeholder="e.g., 3-hour Power Outage, Restocked components, network down...")

    if st.form_submit_button("Record Event"):
        if e_narration.strip():
            # Automatically grab the exact current local date and time
            combined_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            conn = get_connection()
            cursor = conn.cursor()
            # ✅ FIXED: Swapped SQLite "?" with PostgreSQL "%s" placeholders
            cursor.execute(
                "INSERT INTO events (narration, date_time) VALUES (%s, %s)",
                (e_narration.strip(), combined_timestamp)
            )
            conn.commit()
            conn.close()
            
            st.success("Successfully logged event narration!")
            st.rerun()
        else:
            st.warning("Please fill out the Narration box before logging.")

st.subheader("📋 History")
events_df = fetch_table("events")

if not events_df.empty:
    # Sort history newest action steps first
    events_df = events_df.sort_values(by="date_time", ascending=False)
    
    # Rename display columns cleanly
    final_view = events_df[["date_time", "narration"]].rename(
        columns={"date_time": "Date & Time", "narration": "Narration"}
    )
    st.dataframe(final_view, use_container_width=True, hide_index=True)
else:
    st.info("No shop event narrations recorded yet.")
