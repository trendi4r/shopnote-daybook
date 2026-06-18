import streamlit as st

# Simple user database
USERS = {
    "admin": "1234",
    "staff": "5678"
}

def login():
    st.title("🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in USERS and USERS[username] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success("Login Successful")
            st.rerun()
        else:
            st.error("Invalid Username or Password")