import os
import sys
import time
import subprocess
import streamlit as st
from loguru import logger

from ui.data_page import EMAILS_FILE, PROXIES_FILE

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "profile_creator.log")

def tail(file_path: str, n: int = 100):
    """Returns the last `n` lines of a file."""
    if not os.path.exists(file_path):
        return ""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            return "".join(lines[-n:])
    except Exception as e:
        logger.error(f"Error tailing file {file_path}: {e}")
        return f"Error reading log file: {e}"

def run_creation_process(max_accounts: int, delay: int, dry_run: bool, log_container: st.container):
    """
    Runs the main profile creation script as a subprocess and streams its logs.
    """
    # Ensure log directory exists
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Base command for running the main script
    command = [
        sys.executable,  # Use the same python interpreter running streamlit
        "-m", "src.main",
        "--emails", EMAILS_FILE,
        "--proxies", PROXIES_FILE,
        "--max-accounts", str(max_accounts),
        "--delay", str(delay)
    ]
    if dry_run:
        command.append("--dry-run")
        
    logger.info(f"Running command: {' '.join(command)}")

    # Clear previous log file
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w"):
            pass
            
    try:
        # The main script's logger should be configured to output to LOG_FILE.
        # We start the process and then tail the log file.
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        
        # Stream logs to the UI
        while process.poll() is None:
            log_content = tail(LOG_FILE, 200)
            log_container.code(log_content, language="log")
            time.sleep(0.5)
            
        # Final update to the log view
        log_content = tail(LOG_FILE, 500)
        log_container.code(log_content, language="log")

        if process.returncode == 0:
            st.success("✅ Account creation process completed successfully!")
        else:
            st.error(f"❌ Process exited with error code {process.returncode}.")

    except Exception as e:
        st.error(f"Failed to start the creation process: {e}")
        logger.error(f"Error in run_creation_process: {e}")

if __name__ == "__main__":
    # This part allows the script to be called from the command line itself,
    # which is how the Streamlit app will execute it.
    if len(sys.argv) < 6:
        print("Usage: python -m ui.run_worker <emails_csv> <proxies_json> <max_accounts> <delay> <dry_run>")
        sys.exit(1)
        
    emails = sys.argv[1]
    proxies = sys.argv[2]
    max_acc = int(sys.argv[3])
    run_delay = int(sys.argv[4])
    is_dry_run = sys.argv[5].lower() == 'true'

    run_creation_process(
        max_accounts=max_acc,
        delay=run_delay,
        dry_run=is_dry_run,
        log_container=st.empty(),
    ) 