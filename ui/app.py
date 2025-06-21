import os
import sys
import streamlit as st
from loguru import logger

# Add the project root to the Python path to allow absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import subprocess
import pandas as pd

from ui.config import load_config, save_config, AppConfig, GMAIL_CREDS_FILE, PROFILES_OUTPUT_FILE, CONFIG_DIR
from ui.watcher import start_watching
from ui.data_page import render_data_page, TMP_DIR, EMAILS_FILE, PROXIES_FILE
from ui.run_worker import run_creation_process

# --- Page Configuration ---
st.set_page_config(
    page_title="Reddit Profile Creator",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Styling ---
# Removing st_tailwind for now as it's causing import errors.
# The app will use default streamlit styling.
# st_tags(
#     css="""
#     .stApp {
#         background-color: #F0F2F6;
#     }
#     .stApp[theme='dark'] {
#         background-color: #1A202C;
#     }
#     h1, h2 {
#         color: #1a73e8;
#     }
#     .stApp[theme='dark'] h1, .stApp[theme='dark'] h2 {
#         color: #63B3ED;
#     }
#     """
# )

# --- Session State Initialization ---
if "master_password" not in st.session_state:
    st.session_state.master_password = None
if "config" not in st.session_state:
    st.session_state.config = None
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "observer" not in st.session_state:
    st.session_state.observer = None

# --- Main App Logic ---

def show_login_screen():
    """Displays the master password login form."""
    st.title("🔑 Secure Configuration Vault")
    st.write("Enter your master password to load and decrypt the application settings.")
    
    with st.form("login_form"):
        password = st.text_input("Master Password", type="password")
        submitted = st.form_submit_button("Unlock")

        if submitted:
            if not password:
                st.error("Please enter a password.")
            else:
                config = load_config(password)
                if config:
                    st.session_state.master_password = password
                    st.session_state.config = config
                    st.session_state.logged_in = True
                    os.environ["MASTER_PASSWORD"] = password # Make it available to subprocesses
                    st.rerun()
                else:
                    st.error("Failed to decrypt configuration. Please check your password.")

def show_main_app():
    """Displays the main application UI after login."""
    # Start the file watcher if it's not running
    if st.session_state.observer is None:
        # Ensure the output directory exists
        os.makedirs(os.path.dirname(PROFILES_OUTPUT_FILE), exist_ok=True)
        st.session_state.observer = start_watching(PROFILES_OUTPUT_FILE, on_log_change)

    with st.sidebar:
        st.title("Reddit Profile Creator")
        page = st.radio(
            "Navigation",
            ("Configuration", "Data", "Run", "Dashboard"),
            key="navigation_page"
        )
        
        # Dark/Light mode toggle
        # Disabling for now as it causes reruns that can interfere with other components
        # st.toggle("Dark Mode", key="dark_mode")

    if page == "Configuration":
        render_config_page()
    elif page == "Data":
        render_data_page()
    elif page == "Run":
        render_run_page()
    elif page == "Dashboard":
        render_dashboard_page()

def render_config_page():
    """Renders the configuration management page."""
    st.header("⚙️ Application Configuration")
    st.write(
        "Manage API keys, credentials, and other settings. "
        "All sensitive information will be stored encrypted on disk."
    )

    config: AppConfig = st.session_state.config
    
    with st.form("config_form"):
        st.subheader("CAPTCHA Services")
        caps_key = st.text_input(
            "Capsolver API Key",
            value=config.captcha.caps_key,
            type="password"
        )
        captcha_2_key = st.text_input(
            "2Captcha API Key (Optional Fallback)",
            value=config.captcha.captcha_2_key or "",
            type="password"
        )

        st.subheader("AdsPower")
        adspower_base_url = st.text_input(
            "AdsPower Base URL",
            value=config.adspower.base_url
        )
        adspower_group_id = st.text_input(
            "AdsPower Group ID",
            value=config.adspower.group_id
        )
        adspower_access_token = st.text_input(
            "AdsPower Access Token (Optional)",
            value=config.adspower.access_token or "",
            type="password"
        )
        
        st.subheader("Gmail OAuth")
        gmail_creds_file = st.file_uploader(
            "Upload Gmail credentials.json",
            type="json"
        )
        if gmail_creds_file:
            st.success(f"'{gmail_creds_file.name}' uploaded successfully.")
        elif os.path.exists(GMAIL_CREDS_FILE):
            st.info("Gmail credentials file is already on record. Upload a new one to replace it.")

        st.subheader("DataImpulse Proxies")
        dataimpulse_user = st.text_input(
            "DataImpulse Username",
            value=config.dataimpulse.user or ""
        )
        dataimpulse_password = st.text_input(
            "DataImpulse Password",
            value=config.dataimpulse.password or "",
            type="password"
        )
        
        st.subheader("General Settings")
        rotation_interval = st.number_input(
            "Default Rotation Interval (minutes)",
            min_value=1,
            value=config.rotation_interval_minutes
        )

        submitted = st.form_submit_button("Save Encrypted Configuration")

        if submitted:
            # Update config object from form fields
            config.captcha.caps_key = caps_key
            config.captcha.captcha_2_key = captcha_2_key
            config.adspower.base_url = adspower_base_url
            config.adspower.group_id = adspower_group_id
            config.adspower.access_token = adspower_access_token
            config.dataimpulse.user = dataimpulse_user
            config.dataimpulse.password = dataimpulse_password
            config.rotation_interval_minutes = rotation_interval
            
            if gmail_creds_file:
                config.gmail.credentials_json = gmail_creds_file.getvalue().decode("utf-8")

            # Save the updated config
            save_config(config, st.session_state.master_password)
            st.success("Configuration saved and encrypted successfully!")
            # Update session state to reflect changes immediately
            st.session_state.config = load_config(st.session_state.master_password)

def render_run_page():
    """Renders the page for running the creation process."""
    st.header("🚀 Run Profile Creation")

    # --- Check for prerequisites ---
    config_ok = st.session_state.config is not None
    emails_ok = os.path.exists(EMAILS_FILE) and os.path.getsize(EMAILS_FILE) > 0
    proxies_ok = os.path.exists(PROXIES_FILE) and os.path.getsize(PROXIES_FILE) > 0
    
    # --- Display Status Chips ---
    st.write("Current Status:")
    cols = st.columns(3)
    with cols[0]:
        st.metric(label="Configuration", value="✅ Ready" if config_ok else "❌ Missing")
    with cols[1]:
        st.metric(label="Emails", value="✅ Ready" if emails_ok else "❌ Missing")
    with cols[2]:
        st.metric(label="Proxies", value="✅ Ready" if proxies_ok else "❌ Missing")

    st.markdown("---")

    # --- Run Controls ---
    with st.form("run_form"):
        max_accounts = st.number_input(
            "Max accounts to create", min_value=1, value=10
        )
        delay = st.number_input(
            "Delay between accounts (seconds)", min_value=0, value=5
        )
        dry_run = st.checkbox("Dry-run (no registration, just check inputs)")
        
        start_button = st.form_submit_button(
            "Start Account Creation",
            type="primary",
            disabled=not (config_ok and emails_ok and proxies_ok)
        )

    if not (config_ok and emails_ok and proxies_ok):
        st.warning("Please ensure configuration, emails, and proxies are set up before running.")

    # --- Execution Logic ---
    if start_button:
        st.info("Starting background process... Logs will appear below.")
        
        # Placeholder for the real-time log viewer
        log_container = st.empty()
        log_container.code("Log viewer will be implemented here.", language="log")

        run_creation_process(
            max_accounts=max_accounts,
            delay=delay,
            dry_run=dry_run,
            log_container=log_container # Pass the container to the worker
        )

def on_log_change():
    """Callback function to trigger a rerun when the log file changes."""
    st.rerun()

def render_dashboard_page():
    """Renders the dashboard page showing created profiles."""
    st.header("📊 Live Dashboard")
    st.write("This page watches for changes in `profiles.json` and updates automatically.")

    if st.button("Force Refresh"):
        st.rerun()

    if os.path.exists(PROFILES_OUTPUT_FILE):
        try:
            df = pd.read_json(PROFILES_OUTPUT_FILE)
            # Prettify the dataframe for display
            display_df = df[[
                "username", "status", "creation_timestamp", 
                "ip_on_creation", "ip_rotated", "error_message"
            ]].copy()
            display_df["creation_timestamp"] = pd.to_datetime(
                display_df["creation_timestamp"], unit='s'
            ).dt.strftime('%Y-%m-%d %H:%M:%S')

            st.dataframe(display_df, use_container_width=True)
            
            with open(PROFILES_OUTPUT_FILE, "r") as f:
                st.download_button(
                    label="Download Full Log",
                    data=f.read(),
                    file_name="profiles.json",
                    mime="application/json",
                )
        except (ValueError, FileNotFoundError):
            st.info("Log file is empty or corrupted. Waiting for data...")
    else:
        st.info("No log file found. Run a creation process to generate one.")

# --- Entry Point ---
if not st.session_state.logged_in:
    show_login_screen()
else:
    show_main_app() 