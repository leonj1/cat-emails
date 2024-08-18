# Gmail Categorizer

This Python script logs into a Gmail account, scans emails from the last 24 hours, and categorizes them based on their content.

## Setup

1. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

2. Set up Google Cloud Project and enable Gmail API:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the Gmail API for your project
   - Create credentials (OAuth client ID) for a desktop application
   - Download the client configuration and save it as `credentials.json` in the same directory as the script

3. Run the script:
   ```
   python gmail_categorizer.py
   ```

4. The first time you run the script, it will open a browser window asking you to authorize the application. Grant the necessary permissions.

5. The script will then scan your recent emails and categorize them.

## Categories

The script currently categorizes emails into the following categories:
- Order Receipt
- Advertisement
- Personal Response
- Other

You can modify the `categorize_email` function in `gmail_categorizer.py` to add or change categories as needed.

## Note

This script requires access to your Gmail account. Make sure to review the code and understand what it does before running it with your personal account.
