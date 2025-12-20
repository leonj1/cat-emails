# Gmail OAuth 2.0 API Documentation

This document describes the OAuth 2.0 API endpoints for integrating Gmail access with your frontend application. These endpoints allow users to grant this application permission to read their emails and manage labels.

## Overview

The OAuth flow consists of four main endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/gmail/authorize` | GET | Initiate OAuth flow, get authorization URL |
| `/api/auth/gmail/callback` | POST | Exchange authorization code for tokens |
| `/api/accounts/{email}/oauth-status` | GET | Check OAuth connection status |
| `/api/accounts/{email}/oauth` | DELETE | Revoke OAuth access |

## Prerequisites

### Environment Variables

The backend requires these environment variables to be configured:

```bash
GMAIL_OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
GMAIL_OAUTH_CLIENT_SECRET=your-client-secret
```

**Create a `.env` file** (excluded from git via `.gitignore`) with your actual credentials:

```bash
# .env file example
GMAIL_OAUTH_CLIENT_ID=123456789.apps.googleusercontent.com
GMAIL_OAUTH_CLIENT_SECRET=GOCSPX-abcdefghijklmnop
API_HOST=https://your-api-host.com
GMAIL_API_KEY=your-actual-api-key-here
```

### API Key

All endpoints require an API key passed via the `X-API-Key` header.

**For testing with curl**, export your API key as an environment variable:

```bash
export GMAIL_API_KEY="your-actual-api-key-here"
```

This allows you to reference `${GMAIL_API_KEY}` in curl commands instead of hardcoding credentials.

### Required OAuth Scopes

The application requests the following Gmail scopes:

- `https://www.googleapis.com/auth/gmail.readonly` - Read email messages
- `https://www.googleapis.com/auth/gmail.labels` - Manage labels
- `https://www.googleapis.com/auth/gmail.modify` - Modify email messages

---

> ⚠️ **SECURITY NOTICE**
>
> All values in the examples below such as `your-api-key`, `your-api-host`, `your-client-id`, etc. are **PLACEHOLDERS**.
> Replace them with your actual credentials.
>
> **Never commit real API keys or secrets to version control.** Use environment variables, `.env` files (excluded from git), or your deployment platform's secret management system.

---

## 1. Initiate OAuth Flow

Start the OAuth authorization process by requesting an authorization URL.

### Request

```bash
curl -X GET "https://your-api-host/api/auth/gmail/authorize?redirect_uri=https://your-app.com/oauth/callback" \
  -H "X-API-Key: ${GMAIL_API_KEY}"
```

### With Login Hint (Optional)

Pre-fill the user's email in Google's consent screen:

```bash
curl -X GET "https://your-api-host/api/auth/gmail/authorize?redirect_uri=https://your-app.com/oauth/callback&login_hint=user@gmail.com" \
  -H "X-API-Key: ${GMAIL_API_KEY}"
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `redirect_uri` | query | Yes | URL to redirect after consent (must match Google Cloud Console config) |
| `login_hint` | query | No | Email address to pre-fill in consent screen |

### Response

```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...&redirect_uri=...&response_type=code&scope=...&state=...&access_type=offline&prompt=consent",
  "state": "abc123xyz789..."
}
```

### Frontend Implementation

```javascript
// Step 1: Request authorization URL
const response = await fetch(
  `${API_BASE}/api/auth/gmail/authorize?redirect_uri=${encodeURIComponent(REDIRECT_URI)}`,
  {
    headers: { 'X-API-Key': API_KEY }
  }
);
const { authorization_url, state } = await response.json();

// Step 2: Store state in sessionStorage for CSRF validation
sessionStorage.setItem('oauth_state', state);

// Step 3: Redirect user to Google consent screen
window.location.href = authorization_url;
```

---

## 2. Handle OAuth Callback

After the user completes consent on Google's site, they are redirected back to your `redirect_uri` with a `code` and `state` parameter. Exchange these for tokens.

### Request

```bash
curl -X POST "https://your-api-host/api/auth/gmail/callback?redirect_uri=https://your-app.com/oauth/callback" \
  -H "X-API-Key: ${GMAIL_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "4/0AfJohXnN...",
    "state": "abc123xyz789..."
  }'
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `redirect_uri` | query | Yes | Same redirect_uri used in authorization request |
| `code` | body | Yes | Authorization code from Google callback |
| `state` | body | Yes | State token for CSRF validation |

### Response (Success)

```json
{
  "success": true,
  "email_address": "user@gmail.com",
  "scopes": [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.modify"
  ]
}
```

### Response (Error - Invalid State)

```json
{
  "detail": "Invalid or expired state token. Please restart the OAuth flow."
}
```

### Frontend Implementation

```javascript
// On your redirect_uri page, handle the callback
const urlParams = new URLSearchParams(window.location.search);
const code = urlParams.get('code');
const state = urlParams.get('state');

// Validate state matches what we stored
const storedState = sessionStorage.getItem('oauth_state');
if (state !== storedState) {
  throw new Error('CSRF validation failed');
}

// Exchange code for tokens
const response = await fetch(
  `${API_BASE}/api/auth/gmail/callback?redirect_uri=${encodeURIComponent(REDIRECT_URI)}`,
  {
    method: 'POST',
    headers: {
      'X-API-Key': API_KEY,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ code, state })
  }
);

const result = await response.json();
if (result.success) {
  console.log(`Connected: ${result.email_address}`);
  console.log(`Granted scopes: ${result.scopes.join(', ')}`);
  // Clear stored state
  sessionStorage.removeItem('oauth_state');
}
```

---

## 3. Check OAuth Status

Check whether an account has OAuth connected and what scopes are granted.

### Request

```bash
curl -X GET "https://your-api-host/api/accounts/user%40gmail.com/oauth-status" \
  -H "X-API-Key: ${GMAIL_API_KEY}"
```

**Note:** URL-encode the email address (`@` becomes `%40`).

### Response (OAuth Connected)

```json
{
  "connected": true,
  "auth_method": "oauth",
  "scopes": [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.modify"
  ],
  "token_expiry": "2024-01-15T10:30:00Z"
}
```

### Response (IMAP Authentication)

```json
{
  "connected": false,
  "auth_method": "imap",
  "scopes": null,
  "token_expiry": null
}
```

### Response (Account Not Found)

```json
{
  "detail": "Account not found: user@gmail.com"
}
```

### Frontend Implementation

```javascript
async function checkOAuthStatus(email) {
  const response = await fetch(
    `${API_BASE}/api/accounts/${encodeURIComponent(email)}/oauth-status`,
    {
      headers: { 'X-API-Key': API_KEY }
    }
  );

  if (response.status === 404) {
    return { exists: false };
  }

  const status = await response.json();
  return {
    exists: true,
    connected: status.connected,
    authMethod: status.auth_method,
    scopes: status.scopes,
    tokenExpiry: status.token_expiry ? new Date(status.token_expiry) : null
  };
}
```

---

## 4. Revoke OAuth Access

Revoke OAuth tokens and disconnect the account from OAuth. The account reverts to requiring IMAP authentication.

### Request

```bash
curl -X DELETE "https://your-api-host/api/accounts/user%40gmail.com/oauth" \
  -H "X-API-Key: ${GMAIL_API_KEY}"
```

### Response (Success)

```json
{
  "success": true,
  "message": "OAuth access revoked for user@gmail.com"
}
```

### Response (Not Using OAuth)

```json
{
  "success": true,
  "message": "Account is not using OAuth authentication"
}
```

### Response (Account Not Found)

```json
{
  "detail": "Account not found: user@gmail.com"
}
```

### Frontend Implementation

```javascript
async function revokeOAuth(email) {
  const response = await fetch(
    `${API_BASE}/api/accounts/${encodeURIComponent(email)}/oauth`,
    {
      method: 'DELETE',
      headers: { 'X-API-Key': API_KEY }
    }
  );

  const result = await response.json();
  if (result.success) {
    console.log(result.message);
  }
  return result;
}
```

---

## Complete Frontend Integration Example

Here's a complete React example demonstrating the full OAuth flow:

```jsx
import { useState, useEffect } from 'react';

const API_BASE = 'https://your-api-host';
const API_KEY = 'your-api-key';
const REDIRECT_URI = 'https://your-app.com/oauth/callback';

function GmailOAuthButton({ userEmail }) {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  // Check current OAuth status on mount
  useEffect(() => {
    checkStatus();
  }, [userEmail]);

  async function checkStatus() {
    setLoading(true);
    try {
      const response = await fetch(
        `${API_BASE}/api/accounts/${encodeURIComponent(userEmail)}/oauth-status`,
        { headers: { 'X-API-Key': API_KEY } }
      );

      if (response.ok) {
        setStatus(await response.json());
      } else if (response.status === 404) {
        setStatus({ connected: false, auth_method: 'none' });
      }
    } catch (error) {
      console.error('Failed to check OAuth status:', error);
    }
    setLoading(false);
  }

  async function connectGmail() {
    try {
      // Step 1: Get authorization URL
      const response = await fetch(
        `${API_BASE}/api/auth/gmail/authorize?redirect_uri=${encodeURIComponent(REDIRECT_URI)}&login_hint=${encodeURIComponent(userEmail)}`,
        { headers: { 'X-API-Key': API_KEY } }
      );

      const { authorization_url, state } = await response.json();

      // Step 2: Store state for CSRF validation
      sessionStorage.setItem('oauth_state', state);
      sessionStorage.setItem('oauth_email', userEmail);

      // Step 3: Redirect to Google
      window.location.href = authorization_url;
    } catch (error) {
      console.error('Failed to initiate OAuth:', error);
    }
  }

  async function disconnectGmail() {
    try {
      const response = await fetch(
        `${API_BASE}/api/accounts/${encodeURIComponent(userEmail)}/oauth`,
        {
          method: 'DELETE',
          headers: { 'X-API-Key': API_KEY }
        }
      );

      const result = await response.json();
      if (result.success) {
        await checkStatus(); // Refresh status
      }
    } catch (error) {
      console.error('Failed to revoke OAuth:', error);
    }
  }

  if (loading) {
    return <button disabled>Loading...</button>;
  }

  if (status?.connected) {
    return (
      <div>
        <span>✓ Gmail Connected</span>
        <button onClick={disconnectGmail}>Disconnect</button>
      </div>
    );
  }

  return (
    <button onClick={connectGmail}>
      Connect Gmail
    </button>
  );
}

// OAuth callback page component
function OAuthCallbackPage() {
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    handleCallback();
  }, []);

  async function handleCallback() {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const state = urlParams.get('state');
    const errorParam = urlParams.get('error');

    // Handle user denial
    if (errorParam) {
      setError(`Authorization denied: ${errorParam}`);
      return;
    }

    // Validate state
    const storedState = sessionStorage.getItem('oauth_state');
    if (state !== storedState) {
      setError('Security validation failed. Please try again.');
      return;
    }

    try {
      const response = await fetch(
        `${API_BASE}/api/auth/gmail/callback?redirect_uri=${encodeURIComponent(REDIRECT_URI)}`,
        {
          method: 'POST',
          headers: {
            'X-API-Key': API_KEY,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ code, state })
        }
      );

      const data = await response.json();

      if (data.success) {
        setResult(data);
        // Clean up
        sessionStorage.removeItem('oauth_state');
        sessionStorage.removeItem('oauth_email');
        // Redirect to dashboard after short delay
        setTimeout(() => {
          window.location.href = '/dashboard';
        }, 2000);
      } else {
        setError(data.detail || 'OAuth failed');
      }
    } catch (err) {
      setError('Failed to complete authorization');
    }
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  if (result) {
    return (
      <div className="success">
        <h2>Gmail Connected!</h2>
        <p>Account: {result.email_address}</p>
        <p>Redirecting to dashboard...</p>
      </div>
    );
  }

  return <div>Processing authorization...</div>;
}

export { GmailOAuthButton, OAuthCallbackPage };
```

---

## Error Handling

### Common Error Responses

| Status Code | Error | Description |
|-------------|-------|-------------|
| 400 | Invalid state token | CSRF validation failed; restart OAuth flow |
| 400 | No refresh token received | User may need to revoke and re-authorize |
| 404 | Account not found | No account exists with that email |
| 500 | OAuth not configured | Backend missing OAuth credentials |
| 500 | Token exchange failed | Failed to exchange code for tokens |

### Handling Token Refresh

The backend automatically refreshes access tokens when needed. The `token_expiry` field in the status response indicates when the current access token expires, but this is handled internally.

---

## Security Considerations

1. **State Parameter**: Always validate the `state` parameter on callback to prevent CSRF attacks
2. **HTTPS Only**: Always use HTTPS for all OAuth-related requests
3. **Secure Storage**: Store the API key securely; never expose it in client-side code in production
4. **Redirect URI Validation**: Ensure your redirect URI is registered in Google Cloud Console
5. **Token Storage**: OAuth tokens are stored server-side; the frontend never handles refresh tokens directly
6. **API Key Management**: Never commit real API keys to version control. Use environment variables, `.env` files (excluded from git via `.gitignore`), or your deployment platform's secret management system (e.g., Railway secrets, Vercel environment variables, AWS Secrets Manager)

---

## Google Cloud Console Setup

Follow these detailed steps to set up OAuth 2.0 credentials for Gmail API access:

### 1. Create or Select a Project

- Go to [Google Cloud Console](https://console.cloud.google.com/)
- Click the project dropdown at the top
- Create a new project or select an existing one

### 2. Enable Gmail API

- Navigate to **APIs & Services** > **Library**
- Search for "Gmail API"
- Click on it and press **Enable**

### 3. Configure OAuth Consent Screen

- Go to **APIs & Services** > **OAuth consent screen**
- Choose **External** user type (or Internal if using Google Workspace)
- Fill in the required fields:
  - **App name**: Your application name
  - **User support email**: Your email
  - **Developer contact information**: Your email
- Click **Save and Continue**
- On the **Scopes** page, click **Add or Remove Scopes**
- Add these Gmail scopes:
  - `https://www.googleapis.com/auth/gmail.readonly`
  - `https://www.googleapis.com/auth/gmail.labels`
  - `https://www.googleapis.com/auth/gmail.modify`
- Click **Save and Continue**
- Add test users if your app is in testing mode
- Click **Save and Continue** through the summary

### 4. Create OAuth 2.0 Credentials

- Go to **APIs & Services** > **Credentials**
- Click **Create Credentials** > **OAuth client ID**
- Select **Web application** as the application type
- Give it a name (e.g., "Gmail OAuth Client")
- Under **Authorized redirect URIs**, click **Add URI** and add:
  - `https://your-app.com/oauth/callback` (your production callback URL)
  - `http://localhost:3000/oauth/callback` (for local development, if needed)

  **Important**: The redirect URI in your API requests must **exactly match** one of these registered URIs

- Click **Create**

### 5. Save Your Credentials

- Copy the **Client ID** and **Client Secret** from the popup
- Add them to your `.env` file:
  ```bash
  GMAIL_OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
  GMAIL_OAUTH_CLIENT_SECRET=GOCSPX-your-client-secret
  ```
- **Never commit these credentials to version control**

### 6. Additional Resources

- [Gmail API Documentation](https://developers.google.com/gmail/api)
- [OAuth 2.0 for Web Server Applications](https://developers.google.com/identity/protocols/oauth2/web-server)
- [Google API Scopes](https://developers.google.com/identity/protocols/oauth2/scopes#gmail)
