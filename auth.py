import streamlit as st
from db_helper import get_connection, hash_password

def check_login():
    """Validates user sessions by querying encrypted user credentials and active locks in SQLite."""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    # 1. READ DISK AUTOLOGIN STATUS
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT is_logged_in FROM session_lock WHERE id = 1")
        db_status = cursor.fetchone()
        if db_status and db_status[0] == 1:  # Extracted index element safely
            st.session_state["authenticated"] = True
    except Exception:
        pass
    finally:
        conn.close()

    # 2. IF UNAUTHENTICATED: Open inline security form block gate
    if not st.session_state["authenticated"]:
        st.markdown("""
            <style>
            [data-testid="stSidebarNav"] { display: none !important; }
            section[data-testid="stSidebar"] { display: none !important; }
            .login-card {
                background-color: rgba(128, 128, 128, 0.08);
                border: 1px solid rgba(128, 128, 128, 0.2);
                border-radius: 12px;
                padding: 25px;
                margin: 40px auto;
                max-width: 450px;
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
            }
            </style>
        """, unsafe_allow_html=True)

        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.title("🔒 ShopNote Databook Login")
        st.write("Please authenticate your profile credentials to access your databook records.")

        with st.form("inline_authentication_gate", clear_on_submit=False):
            user_input = st.text_input("Username / ID Token", placeholder="e.g., admin").strip()
            pass_input = st.text_input("Password", type="password", placeholder="••••••••")
            
            if st.form_submit_button("Sign In Securely", type="primary", use_container_width=True):
                if user_input and pass_input:
                    # Encrypt the text submission into matching hash configuration signatures
                    hashed_attempt = hash_password(pass_input)
                    
                    # Target SQL string mapping verification query
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT username FROM users WHERE username = ? AND password_hash = ?", (user_input, hashed_attempt))
                    match = cursor.fetchone()
                    conn.close()
                    
                    if match:
                        st.session_state["authenticated"] = True
                        
                        # Lock session state parameter parameters to disk
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("UPDATE session_lock SET is_logged_in = 1 WHERE id = 1")
                        conn.commit()
                        conn.close()
                        
                        st.success("Access Granted! Decrypting session records...")
                        st.rerun()
                    else:
                        st.error("Invalid Username or Password! Access Denied.")
                else:
                    st.warning("Please fill out all input fields.")
                    
        st.markdown('</div>', unsafe_allow_html=True)
        st.stop()

    # 3. ✅ GLOBAL SIDEBAR ICON OVERRIDE & ENHANCED SIZING RULES
    st.markdown("""
        <style>
        /* 1. Target the button bounding box to make the interactive clicking area larger */
        button[data-testid="sidebar-collapse-button"] {
            width: 55px !important;
            height: 55px !important;
            top: 10px !important;
            left: 10px !important;
            background-color: rgba(128, 128, 128, 0.1) !important; /* Slight background highlight */
            border-radius: 8px !important;
        }
        
        /* 2. Scale up the underlying SVG frame size dimensions */
        button[data-testid="sidebar-collapse-button"] svg {
            width: 32px !important;
            height: 32px !important;
            transform: none !important;
            transition: none !important;
        }
        
        /* 3. Inject the three-bar hamburger configuration path vector */
        button[data-testid="sidebar-collapse-button"] svg path {
            d: path("M 3 5 A 1.0001 1.0001 0 1 0 3 7 L 21 7 A 1.0001 1.0001 0 1 0 21 5 L 3 5 z M 3 11 A 1.0001 1.0001 0 1 0 3 13 L 21 13 A 1.0001 1.0001 0 1 0 21 11 L 3 11 z M 3 17 A 1.0001 1.0001 0 1 0 3 19 L 21 19 A 1.0001 1.0001 0 1 0 21 17 L 3 17 z") !important;
        }
        </style>
    """, unsafe_allow_html=True)
