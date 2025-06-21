# Reddit Profile Creator

This project is a sophisticated, open-source automation tool for mass-creating Reddit accounts. It is designed with a strong focus on stealth, security, and robustness, leveraging a modern technology stack to handle browser automation, CAPTCHA solving, and email verification.

## 🌟 Features

- **Stealthy Browser Automation**: Uses `Zendriver` to control a browser at a low level, making automation difficult to detect.
- **Anti-Fingerprinting**: Integrates with AdsPower to manage unique browser fingerprints for each profile.
- **Advanced CAPTCHA Solving**: Primarily uses the fast and cheap CapSolver, with an automatic fallback to the reliable 2Captcha.
- **Secure Email Verification**: Interacts with the Gmail API using OAuth2 and encrypted refresh tokens, avoiding insecure methods like IMAP.
- **Robust Error Handling**: The entire process is wrapped in error handling to gracefully manage failures.
- **Detailed Logging**: Every created profile, along with its status, is logged to `profiles.json`. IP rotation is tracked and recorded.
- **Secure by Design**: Passwords are saved with Argon2 hashing, and sensitive tokens are encrypted with Fernet.
- **Type-Safe & Linted**: The codebase is fully type-annotated and enforced with `ruff` and `mypy`.
- **Containerized**: Comes with `Dockerfile` and `docker-compose.yml` for easy and consistent deployment.

## 🛠️ Setup Instructions

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/reddit_profile_creator.git
    cd reddit_profile_creator
    ```

2.  **Install Python dependencies:**
    It is recommended to use a virtual environment.
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    pip install -r requirements.txt
    ```

3.  **Set up AdsPower:**
    - Download and install the [AdsPower](https://www.adspower.com/) client.
    - Start AdsPower and enable the Local API from the settings.

4.  **Configure Environment Variables:**
    - Create a `.env` file in the root directory by copying the template below.
    - Fill in your API keys and other settings.

5.  **Set up Gmail API Credentials:**
    - Follow the [Google API Python Quickstart](https://developers.google.com/gmail/api/quickstart/python) to create a project and enable the Gmail API.
    - Download the `credentials.json` file and place it in the root of the project directory.
    - The first time you run the application, it will open a browser window for you to authorize access to your Gmail account. After authorization, `token.json` and `encrypted_refresh_token.bin` will be created.

## `.env` Template

Create a file named `.env` and populate it with your keys:

```dotenv
# --- CAPTCHA Settings ---
# Your API key for CapSolver (required)
CAPS_KEY="your_capsolver_api_key"

# Your API key for 2Captcha (optional, for fallback)
CAPTCHA_2_KEY="your_2captcha_api_key"

# --- AdsPower Settings ---
# The Group ID from AdsPower where you want to store the profiles
ADSPOWER_GROUP_ID="your_adspower_group_id"

# --- Logging ---
LOG_LEVEL="INFO"
```

## ▶️ Usage

The main entry point is `src/main.py`. Before running, you should configure the `creation_tasks` list within the `run()` function in that file to specify the profiles you want to create.

```bash
python -m src.main
```

The script will then execute the creation process for each task, and the results will be logged in `profiles.json`.

## empfohlen UI Workflow

For the best experience, use the built-in web interface.

1.  **Start the UI:**
    ```bash
    streamlit run ui/app.py
    ```

2.  **Step 1: Configure Settings**
    - Navigate to the **Configuration** page.
    - Enter your API keys for CAPTCHA solvers and any other required settings.
    - Click "Save Encrypted Configuration".

    *Screenshot Placeholder: A view of the filled-out configuration page.*

3.  **Step 2: Provide Data**
    - Navigate to the **Data** page.
    - In the **E-mails** tab, either upload a CSV file or use the table editor to add email addresses. Click "Save Email Data".
    - In the **Proxies** tab, either upload a JSON file or use the table editor to add your proxies. Click "Save Proxy Data".

    *Screenshot Placeholder: A view of the data page showing the email and proxy editors.*

4.  **Step 3: Run the Creator**
    - Navigate to the **Run** page.
    - Verify that the status indicators for Configuration, Emails, and Proxies all show "✅ Ready".
    - Click the "Start Account Creation" button.
    - Watch the logs in real-time to monitor the progress.

    *Screenshot Placeholder: The run page showing the "Start" button and the live log viewer.*

---
*Disclaimer: This tool is for educational purposes only. Mass-creating accounts may be against the terms of service of some websites. The user assumes all responsibility for the use of this software.* 