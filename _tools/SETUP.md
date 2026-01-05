# Google Drive API Setup Guide

*For setting up Google Drive access in your personal assistant*

---

## Prerequisites
- Python 3.x installed
- A Google account with access to Google Drive

---

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Name it something like "Personal Assistant" → Create
4. Select your new project

---

## Step 2: Enable the Google Drive API

1. In the Cloud Console, go to **APIs & Services → Library**
2. Search for "Google Drive API"
3. Click on it → Click **Enable**

---

## Step 3: Create OAuth Credentials

1. Go to **APIs & Services → Credentials**
2. Click **+ Create Credentials → OAuth client ID**
3. If prompted, configure the OAuth consent screen first:
   - User Type: **External** (or Internal if using a Workspace account)
   - App name: "Personal Assistant"
   - User support email: your email
   - Developer contact: your email
   - Save and continue through the remaining screens
4. Back to Credentials → **+ Create Credentials → OAuth client ID**
5. Application type: **Desktop app**
6. Name: "Personal Assistant Desktop"
7. Click **Create**
8. Click **Download JSON** → save as `client_secrets.json`

---

## Step 4: Place Credentials File

Put `client_secrets.json` in your project root:

```
your-project/
├── _tools/
│   └── gdrive_recent.py
├── client_secrets.json   ← HERE
└── token.json            ← (generated automatically)
```

---

## Step 5: Install Python Dependencies

```bash
pip install google-auth google-auth-oauthlib google-api-python-client
```

Or add to `requirements.txt`:

```
google-auth
google-auth-oauthlib
google-api-python-client
```

---

## Step 6: First Run (Authorization)

Run the script for the first time:

```bash
python _tools/gdrive_recent.py
```

This will:
1. Open a browser window
2. Ask you to sign in with Google
3. Grant permission to "View files in Google Drive"
4. Save the authorization token to `token.json`

After this, subsequent runs won't require browser authorization.

---

## Step 7: Test It

```bash
# Show files you've edited in the last 24 hours
python _tools/gdrive_recent.py

# Show files you've viewed in the last 48 hours
python _tools/gdrive_recent.py --hours 48 --mode viewed

# Get JSON output (for programmatic use)
python _tools/gdrive_recent.py --json
```

---

## Important Notes

| File | Purpose | Share? |
|------|---------|--------|
| `client_secrets.json` | OAuth app credentials | ❌ No — each person creates their own |
| `token.json` | Your personal auth token | ❌ No — personal, auto-generated |
| `gdrive_recent.py` | The script itself | ✅ Yes — can share this |

**Each person needs to:**
1. Create their own Google Cloud project
2. Generate their own `client_secrets.json`
3. Run the script once to generate their own `token.json`

---

## Troubleshooting

### "Access blocked" error
- Your OAuth consent screen may need to add test users
- Go to APIs & Services → OAuth consent screen → Test users → Add your email

### Token expired
- Delete `token.json` and run the script again to re-authorize

### Missing dependencies
- Make sure you've installed all three packages:
  ```bash
  pip install google-auth google-auth-oauthlib google-api-python-client
  ```