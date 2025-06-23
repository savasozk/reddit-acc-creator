import json
import random
from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st
from loguru import logger

from src.adspower import AdsPowerAPI
from src.config import settings

def get_proxy_config() -> Optional[Dict[str, Any]]:
    """Loads the first proxy from the proxies.json file."""
    try:
        with open(".tmp/proxies.json", "r") as f:
            proxies = json.load(f)
        if not proxies:
            st.warning("`.tmp/proxies.json` is empty. No proxy will be used for creation.")
            return None
        
        first_proxy = proxies[0]
        proxy_config = {
            "proxy_soft": "other", "proxy_type": "http",
            "proxy_host": first_proxy.get("proxy_host"), "proxy_port": first_proxy.get("proxy_port"),
            "proxy_user": first_proxy.get("proxy_user"), "proxy_pass": first_proxy.get("proxy_password"),
        }
        return proxy_config
    except FileNotFoundError:
        st.warning("`.tmp/proxies.json` not found. Please add proxies on the Data page before creating a profile.")
        return None
    except (json.JSONDecodeError, IndexError) as e:
        st.error(f"Error reading or parsing `.tmp/proxies.json`: {e}")
        return None

def get_fingerprint_config() -> Dict[str, Any]:
    """Generates a default fingerprint configuration."""
    return {
        "kernel": "chromium", "platform": "windows", "os_version": "10",
        "language": ["en-US"], "resolution": random.choice(["1920x1080", "1600x900"]),
        "fonts": ["all"], "webrtc": "proxy", "webgl": "1", "canvas": "1",
    }


def render_adspower_page():
    """Renders the AdsPower automation page."""
    st.header("🚀 AdsPower Automation")

    try:
        api = AdsPowerAPI()
        st.success("Successfully connected to AdsPower Local API.")
    except ConnectionError:
        st.error("Could not connect to AdsPower. Please ensure it's running (headless or GUI) and the Local API is enabled.")
        return

    group_id = settings.adspower_group_id
    if not group_id:
        st.warning("`ADSPOWER_GROUP_ID` is not set in your .env file. Showing all profiles.")

    st.subheader("Profile Management")
    
    if st.button("🔄 Refresh List"):
        st.rerun()

    profile_list = api.list_profiles(group_id=group_id)

    if not profile_list:
        st.info("No profiles found in the specified group or AdsPower.")
    else:
        df = pd.DataFrame(profile_list)[['user_id', 'name', 'created_time']]
        st.dataframe(df, use_container_width=True, hide_index=True)

        profile_options = {p['name']: p['user_id'] for p in profile_list}
        selected_name = st.selectbox("Select a profile to manage:", options=profile_options.keys())
        
        if selected_name:
            selected_id = profile_options[selected_name]
            col1, col2 = st.columns(2)
            with col1:
                if st.button("▶️ Launch Selected", use_container_width=True):
                    with st.spinner(f"Starting browser for '{selected_name}'..."):
                        if api.start_browser(user_id=selected_id):
                            st.success(f"Browser for '{selected_name}' started.")
                        else:
                            st.error("Failed to start browser. Check logs.")
            with col2:
                if st.button("⏹️ Stop Selected", use_container_width=True):
                    with st.spinner(f"Stopping browser for '{selected_name}'..."):
                        if api.stop_browser(user_id=selected_id):
                            st.success(f"Browser for '{selected_name}' stopped.")
                        else:
                            st.error("Failed to stop browser. Check logs.")
    
    st.markdown("---")
    st.subheader("Create New Profile")
    with st.expander("Expand to create a new profile"):
        new_profile_name = st.text_input("New Profile Name:", f"Profile-{random.randint(1000, 9999)}")

        if st.button("🛠️ Create and Launch Profile"):
            if not new_profile_name:
                st.warning("Please provide a name for the new profile.")
            else:
                proxy_config = get_proxy_config()
                if proxy_config and group_id:
                    with st.spinner(f"Creating profile '{new_profile_name}'..."):
                        profile_id = api.create_profile(
                            name=new_profile_name,
                            group_id=group_id,
                            proxy_config=proxy_config,
                            fingerprint_config=get_fingerprint_config(),
                        )
                    if profile_id:
                        st.success(f"Profile '{new_profile_name}' created with ID: {profile_id}")
                        with st.spinner("Launching browser..."):
                            api.start_browser(user_id=profile_id)
                        st.rerun() # Refresh the page to show the new profile
                    else:
                        st.error("Failed to create profile. Check logs for details.")
                else:
                    if not proxy_config:
                        st.error("Cannot create profile without proxy configuration from the Data page.")
                    if not group_id:
                        st.error("Cannot create profile without `ADSPOWER_GROUP_ID` set in your .env file.") 