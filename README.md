# Gmail Categorizer

This Python script logs into a Gmail account using IMAP, scans emails from the last 24 hours, and categorizes them based on their content. It can be run locally or within a Docker container.

## Setup and Usage

### Local Setup

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

### Docker Setup

1. Copy the `.env.example` file to `.env` in the project root:
   ```
   cp .env.example .env
   ```
   Then edit the `.env` file with your actual Gmail credentials:
   ```
   GMAIL_EMAIL=your.email@gmail.com
   GMAIL_PASSWORD=your_password_or_app_specific_password
   ```

2. Build the Docker image:
   ```
   make build
   ```

3. Run the script in a Docker container:
   ```
   make docker-run
   ```

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
- When using Docker, ensure that your `.env` file is not committed to version control.
