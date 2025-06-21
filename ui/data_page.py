import os
import streamlit as st
import pandas as pd
import json
from loguru import logger

# --- Constants ---
TMP_DIR = ".tmp"
EMAILS_FILE = os.path.join(TMP_DIR, "emails.csv")
PROXIES_FILE = os.path.join(TMP_DIR, "proxies.json")

# --- Utility Functions ---
def ensure_tmp_dir():
    """Ensures the temporary directory exists."""
    os.makedirs(TMP_DIR, exist_ok=True)

def load_emails_df():
    """Loads emails into a DataFrame from the temporary CSV."""
    if os.path.exists(EMAILS_FILE):
        try:
            return pd.read_csv(EMAILS_FILE)
        except pd.errors.EmptyDataError:
            return pd.DataFrame(columns=["email"])
    return pd.DataFrame(columns=["email"])

def load_proxies_df():
    """Loads proxies into a DataFrame from the temporary JSON."""
    if os.path.exists(PROXIES_FILE):
        try:
            with open(PROXIES_FILE, "r") as f:
                data = json.load(f)
            return pd.DataFrame(data)
        except (json.JSONDecodeError, KeyError):
            return pd.DataFrame(columns=["proxy_soft", "proxy_host", "proxy_port", "proxy_user", "proxy_password"])
    return pd.DataFrame(columns=["proxy_soft", "proxy_host", "proxy_port", "proxy_user", "proxy_password"])

# --- Main Page Rendering ---
def render_data_page():
    """Renders the data management page for emails and proxies."""
    ensure_tmp_dir()
    st.header("💾 Data Input")
    st.write("Upload or manually edit the email addresses and proxies for account creation.")

    tab1, tab2 = st.tabs(["📧 E-mails", "🌐 Proxies"])

    # --- E-mails Tab ---
    with tab1:
        st.subheader("Manage Email Addresses")
        
        uploaded_emails_file = st.file_uploader("Upload Emails CSV", type="csv", key="emails_uploader")
        if uploaded_emails_file is not None:
            with open(EMAILS_FILE, "wb") as f:
                f.write(uploaded_emails_file.getvalue())
            st.success(f"Uploaded `{uploaded_emails_file.name}` successfully!")
            # Use a button to avoid rerunning and clearing the uploader state immediately
            if st.button("Load Uploaded Emails into Editor"):
                st.rerun()

        st.markdown("---")
        st.write("#### Email Editor")
        
        # Load existing or create new DataFrame for emails
        emails_df = load_emails_df()
        
        edited_emails_df = st.data_editor(
            emails_df,
            num_rows="dynamic",
            use_container_width=True,
            key="emails_editor"
        )

        if st.button("Save Email Data"):
            # Ensure the 'email' column exists and handle potential empty DataFrame
            if 'email' not in edited_emails_df.columns and not edited_emails_df.empty:
                 st.error("The 'email' column is missing.")
            else:
                edited_emails_df.to_csv(EMAILS_FILE, index=False)
                st.success(f"Emails saved to `{EMAILS_FILE}`")

    # --- Proxies Tab ---
    with tab2:
        st.subheader("Manage Proxies")

        uploaded_proxies_file = st.file_uploader("Upload Proxies JSON", type="json", key="proxies_uploader")
        if uploaded_proxies_file is not None:
            with open(PROXIES_FILE, "wb") as f:
                f.write(uploaded_proxies_file.getvalue())
            st.success(f"Uploaded `{uploaded_proxies_file.name}` successfully!")
            if st.button("Load Uploaded Proxies into Editor"):
                st.rerun()
        
        st.markdown("---")
        st.write("#### Proxy Editor")

        # Load existing or create new DataFrame for proxies
        proxies_df = load_proxies_df()

        edited_proxies_df = st.data_editor(
            proxies_df,
            column_config={
                "proxy_password": st.column_config.TextColumn("Password"),
            },
            num_rows="dynamic",
            use_container_width=True,
            key="proxies_editor"
        )

        if st.button("Save Proxy Data"):
            # Convert DataFrame to the expected JSON format
            proxies_list = edited_proxies_df.to_dict(orient="records")
            with open(PROXIES_FILE, "w") as f:
                json.dump(proxies_list, f, indent=4)
            st.success(f"Proxies saved to `{PROXIES_FILE}`") 