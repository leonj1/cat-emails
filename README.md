# Gmail Categorizer

This Python script logs into a Gmail account using IMAP, scans emails from the last 24 hours, and categorizes them based on their content.

## Setup and Usage

1. Set up environment variables:
   - Set `GMAIL_EMAIL` to your Gmail email address
   - Set `GMAIL_PASSWORD` to your Gmail password or an app-specific password

   You can set these variables in your shell:
   ```
   export GMAIL_EMAIL=your.email@gmail.com
   export GMAIL_PASSWORD=your_password_or_app_specific_password
   ```

2. Set up the project:
   ```
   make setup
   ```
   This will install the required packages.

3. Run the script:
   ```
   make run
   ```
   or simply:
   ```
   make
   ```

4. The script will connect to your Gmail account, scan your recent emails, and categorize them.

## Categories

The script currently categorizes emails into the following categories:
- Order Receipt
- Advertisement
- Personal Response
- Other

You can modify the `categorize_email` function in `gmail_categorizer.py` to add or change categories as needed.

## Note

This script requires access to your Gmail account. Make sure to review the code and understand what it does before running it with your personal account. If you're using 2-factor authentication, you'll need to create an app-specific password for this script.

## Security Considerations

- Never share your Gmail password or app-specific password with others.
- Be cautious when setting environment variables, especially on shared systems.
- Consider using OAuth2 for more secure authentication in a production environment.
