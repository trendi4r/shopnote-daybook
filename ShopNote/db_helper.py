import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib

def get_connection():
    """Establishes a secure connection to your permanent cloud database."""
    # Pulls the secret URI string securely from Streamlit Secrets
    return psycopg2.connect(st.secrets["DATABASE_URL"])

def hash_password(password):
    """Encrypts raw text submissions into secure matching SHA-256 string signatures."""
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    """Initializes tables on the permanent Supabase cloud instance if they do not exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. CREATE CORE BUSINESS TABLES USING POSTGRESQL SYNTAX
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock (
            product_id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            stock INTEGER DEFAULT 0,
            sale_price NUMERIC(15, 2) DEFAULT 0.00
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            sale_id SERIAL PRIMARY KEY,
            product_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            payment_status TEXT NOT NULL,
            payment_method TEXT NOT NULL,
            narration TEXT,
            date TEXT NOT NULL
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            event_id SERIAL PRIMARY KEY,
            date_time TEXT NOT NULL,
            narration TEXT NOT NULL
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS session_lock (
            id INTEGER PRIMARY KEY,
            is_logged_in INTEGER DEFAULT 0
        );
    """)
    
    # 2. SEED DEFAULT USER ACCOUNT (admin / admin123) IF USERS TABLE IS EMPTY
    cursor.execute("SELECT COUNT(*) FROM users;")
    if cursor.fetchone()[0] == 0:
        default_hash = hash_password("admin123")
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s);", ("admin", default_hash))
    
    # 3. SEED DEFAULT GLOBAL SESSION LOCK STATE IF EMPTY
    cursor.execute("SELECT COUNT(*) FROM session_lock WHERE id = 1;")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO session_lock (id, is_logged_in) VALUES (1, 0);")
        
    conn.commit()
    cursor.close()
    conn.close()

def fetch_table(table_name):
    """Fetches records from a specific database table and transforms them smoothly into a Pandas DataFrame."""
    import pandas as pd
    
    # Restrict table names to avoid any raw text SQL injection vulnerabilities
    allowed_tables = ["stock", "sales", "events", "users"]
    if table_name not in allowed_tables:
        return pd.DataFrame()
        
    conn = get_connection()
    try:
        # Use a SQL string query template safe for static structural names
        query = f"SELECT * FROM {table_name};"
        df = pd.read_sql_query(query, conn)
        return df
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()
