# Google Drive MCP Server

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that provides tools to search, list, and read files from Google Drive. Use it with Claude Desktop, Cursor, or any MCP-compatible client.

## Features

| Tool | Description |
|------|-------------|
| `search_drive` | Full-text search across file names and contents |
| `list_recent_files` | Show recently modified files |
| `get_file_content` | Download and return file content as text |
| `get_file_metadata` | Get detailed file information |
| `list_folder_contents` | Browse folder contents |

## Prerequisites

- Python 3.11+
- A Google account with Google Drive access

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/gdrive-mcp.git
cd gdrive-mcp
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Create Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Enable the **Google Drive API**:
   - Go to **APIs & Services → Library**
   - Search for "Google Drive API" → Click **Enable**
4. Create OAuth credentials:
   - Go to **APIs & Services → Credentials**
   - Click **+ Create Credentials → OAuth client ID**
   - If prompted, configure the OAuth consent screen:
     - User Type: **External**
     - Add your email as a test user
   - Application type: **Desktop app**
   - Click **Create**
5. Download the JSON file and save it as `client_secrets.json` in the project root

### 4. Configure Your MCP Client

#### For Cursor

Add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "gdrive": {
      "command": "python3",
      "args": ["/path/to/gdrive-mcp/server.py"]
    }
  }
}
```

#### For Claude Desktop

Add to your Claude Desktop config:

```json
{
  "mcpServers": {
    "gdrive": {
      "command": "python3",
      "args": ["/path/to/gdrive-mcp/server.py"]
    }
  }
}
```

**Note:** Replace `/path/to/gdrive-mcp` with the actual path where you cloned the repo.

### 5. Authenticate

On first use, the server will:
1. Open a browser window for Google OAuth
2. Ask you to sign in and grant "View files in Google Drive" permission
3. Save the token to `token.json` for future use

## Usage Examples

Once configured, you can ask your AI assistant:

- "Search my Google Drive for quarterly reports"
- "Show me files I've modified in the last 48 hours"
- "Get the content of file with ID xyz123"
- "List the contents of my Drive root folder"

## File Structure

```
gdrive-mcp/
├── server.py               # MCP server (main entry point)
├── requirements.txt        # Python dependencies
├── client_secrets.json     # Your OAuth credentials (do not commit!)
├── client_secrets.example.json  # Template for credentials
├── token.json              # Auth token (auto-generated, do not commit!)
├── README.md               # This file
└── _tools/                 # Standalone CLI scripts (optional)
    ├── gdrive_download.py
    └── gdrive_recent.py
```

## Security Notes

- **Never commit** `client_secrets.json` or `token.json` — they contain sensitive credentials
- Each user must create their own Google Cloud project and OAuth credentials
- The server only requests read-only access (`drive.readonly` scope)

## Troubleshooting

### "Access blocked" error during OAuth
- Go to Google Cloud Console → APIs & Services → OAuth consent screen
- Add your email to **Test Users**

### Token expired
- Delete `token.json` and restart the server to re-authenticate

### Module not found errors
- Ensure you're using the same Python that has the dependencies installed
- Try using the full path to Python: `/usr/bin/python3` or similar

## License

MIT
