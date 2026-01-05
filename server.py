#!/usr/bin/env python3
"""
Google Drive MCP Server

Provides tools to search, list, and read files from Google Drive
via the Model Context Protocol (MCP).
"""

import sys
import io
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

# Scopes required for the Drive API
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Paths
SCRIPT_DIR = Path(__file__).parent
CLIENT_SECRETS_FILE = SCRIPT_DIR / 'client_secrets.json'
TOKEN_FILE = SCRIPT_DIR / 'token.json'

# Export MIME types for Google Workspace files
EXPORT_MIME_TYPES = {
    'application/vnd.google-apps.document': 'text/plain',
    'application/vnd.google-apps.spreadsheet': 'text/csv',
    'application/vnd.google-apps.presentation': 'text/plain',
    'application/vnd.google-apps.drawing': 'image/png',
}

# Initialize MCP server
mcp = FastMCP("gdrive")


def get_credentials() -> Credentials:
    """Get valid user credentials from storage or OAuth flow."""
    creds = None
    
    # Load existing token
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    
    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CLIENT_SECRETS_FILE.exists():
                raise FileNotFoundError(
                    f"client_secrets.json not found at {CLIENT_SECRETS_FILE}. "
                    "Please follow the setup instructions."
                )
            
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CLIENT_SECRETS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    
    return creds


def get_drive_service():
    """Build and return a Google Drive API service instance."""
    creds = get_credentials()
    return build('drive', 'v3', credentials=creds)


@mcp.tool()
def search_drive(query: str, max_results: int = 20) -> str:
    """
    Search Google Drive for files matching a query.
    
    Searches both file names and file contents (for Google Docs, Sheets, etc.).
    
    Args:
        query: Search terms to find in file names or contents
        max_results: Maximum number of results to return (default: 20, max: 100)
    
    Returns:
        JSON array of matching files with id, name, mimeType, modifiedTime, and webViewLink
    """
    try:
        service = get_drive_service()
        
        # Cap results at 100
        max_results = min(max_results, 100)
        
        # Build search query - search both name and full text
        # The fullText operator searches file content for Google Workspace files
        search_query = f"(name contains '{query}' or fullText contains '{query}') and trashed = false"
        
        results = service.files().list(
            q=search_query,
            orderBy='modifiedTime desc',
            pageSize=max_results,
            fields="files(id, name, mimeType, modifiedTime, webViewLink, parents)"
        ).execute()
        
        items = results.get('files', [])
        
        if not items:
            return json.dumps({"message": f"No files found matching '{query}'", "files": []})
        
        # Format results
        output = []
        for item in items:
            output.append({
                'id': item.get('id'),
                'name': item.get('name'),
                'mimeType': item.get('mimeType'),
                'modifiedTime': item.get('modifiedTime'),
                'webViewLink': item.get('webViewLink'),
            })
        
        return json.dumps({"count": len(output), "files": output}, indent=2)
        
    except HttpError as error:
        return json.dumps({"error": str(error)})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def list_recent_files(hours: int = 24, max_results: int = 25) -> str:
    """
    List files recently modified in Google Drive.
    
    Args:
        hours: Number of hours to look back (default: 24)
        max_results: Maximum number of results to return (default: 25, max: 100)
    
    Returns:
        JSON array of recently modified files with id, name, mimeType, modifiedTime, and webViewLink
    """
    try:
        service = get_drive_service()
        
        # Cap results at 100
        max_results = min(max_results, 100)
        
        # Calculate the time threshold
        threshold_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        threshold_time_str = threshold_time.strftime('%Y-%m-%dT%H:%M:%S')
        
        # Build query
        query = f"modifiedTime >= '{threshold_time_str}' and trashed = false"
        
        results = service.files().list(
            q=query,
            orderBy='modifiedTime desc',
            pageSize=max_results,
            fields="files(id, name, mimeType, modifiedTime, webViewLink)"
        ).execute()
        
        items = results.get('files', [])
        
        if not items:
            return json.dumps({
                "message": f"No files modified in the last {hours} hours",
                "files": []
            })
        
        # Format results
        output = []
        for item in items:
            output.append({
                'id': item.get('id'),
                'name': item.get('name'),
                'mimeType': item.get('mimeType'),
                'modifiedTime': item.get('modifiedTime'),
                'webViewLink': item.get('webViewLink'),
            })
        
        return json.dumps({
            "hours": hours,
            "count": len(output),
            "files": output
        }, indent=2)
        
    except HttpError as error:
        return json.dumps({"error": str(error)})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_file_content(file_id: str) -> str:
    """
    Get the content of a file from Google Drive.
    
    For Google Docs, Sheets, and Slides, exports as plain text or CSV.
    For other files (PDF, images, etc.), returns metadata only.
    
    Args:
        file_id: The Google Drive file ID
    
    Returns:
        The file content as text, or metadata if content cannot be extracted
    """
    try:
        service = get_drive_service()
        
        # Get file metadata
        file_metadata = service.files().get(
            fileId=file_id,
            fields='id, name, mimeType, modifiedTime, webViewLink, size'
        ).execute()
        
        mime_type = file_metadata.get('mimeType', '')
        file_name = file_metadata.get('name', 'Unknown')
        
        # Check if it's a Google Workspace file that needs export
        if mime_type in EXPORT_MIME_TYPES:
            export_mime = EXPORT_MIME_TYPES[mime_type]
            
            # Export the file
            request = service.files().export_media(
                fileId=file_id, 
                mimeType=export_mime
            )
            
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            
            content = fh.getvalue().decode('utf-8', errors='replace')
            
            return json.dumps({
                "name": file_name,
                "mimeType": mime_type,
                "exportedAs": export_mime,
                "content": content
            }, indent=2)
        
        # For text-based files, try to download directly
        elif mime_type.startswith('text/') or mime_type == 'application/json':
            request = service.files().get_media(fileId=file_id)
            
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            
            content = fh.getvalue().decode('utf-8', errors='replace')
            
            return json.dumps({
                "name": file_name,
                "mimeType": mime_type,
                "content": content
            }, indent=2)
        
        else:
            # For binary files, return metadata only
            return json.dumps({
                "name": file_name,
                "mimeType": mime_type,
                "size": file_metadata.get('size', 'Unknown'),
                "webViewLink": file_metadata.get('webViewLink'),
                "note": "Binary file - content not extracted. Use webViewLink to view."
            }, indent=2)
        
    except HttpError as error:
        return json.dumps({"error": str(error)})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_file_metadata(file_id: str) -> str:
    """
    Get detailed metadata for a file in Google Drive.
    
    Args:
        file_id: The Google Drive file ID
    
    Returns:
        JSON object with file metadata including name, type, size, dates, and sharing info
    """
    try:
        service = get_drive_service()
        
        file_metadata = service.files().get(
            fileId=file_id,
            fields='id, name, mimeType, modifiedTime, createdTime, size, webViewLink, owners, shared, permissions'
        ).execute()
        
        return json.dumps({
            "id": file_metadata.get('id'),
            "name": file_metadata.get('name'),
            "mimeType": file_metadata.get('mimeType'),
            "size": file_metadata.get('size', 'N/A'),
            "createdTime": file_metadata.get('createdTime'),
            "modifiedTime": file_metadata.get('modifiedTime'),
            "webViewLink": file_metadata.get('webViewLink'),
            "shared": file_metadata.get('shared', False),
            "owners": [o.get('displayName', o.get('emailAddress', 'Unknown')) 
                      for o in file_metadata.get('owners', [])]
        }, indent=2)
        
    except HttpError as error:
        return json.dumps({"error": str(error)})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def list_folder_contents(folder_id: str = "root", max_results: int = 50) -> str:
    """
    List contents of a folder in Google Drive.
    
    Args:
        folder_id: The Google Drive folder ID (default: "root" for My Drive root)
        max_results: Maximum number of results to return (default: 50, max: 100)
    
    Returns:
        JSON array of files and folders within the specified folder
    """
    try:
        service = get_drive_service()
        
        # Cap results at 100
        max_results = min(max_results, 100)
        
        # Build query for files in this folder
        query = f"'{folder_id}' in parents and trashed = false"
        
        results = service.files().list(
            q=query,
            orderBy='folder,name',
            pageSize=max_results,
            fields="files(id, name, mimeType, modifiedTime, webViewLink)"
        ).execute()
        
        items = results.get('files', [])
        
        # Separate folders and files
        folders = []
        files = []
        
        for item in items:
            entry = {
                'id': item.get('id'),
                'name': item.get('name'),
                'mimeType': item.get('mimeType'),
                'modifiedTime': item.get('modifiedTime'),
                'webViewLink': item.get('webViewLink'),
            }
            
            if item.get('mimeType') == 'application/vnd.google-apps.folder':
                folders.append(entry)
            else:
                files.append(entry)
        
        return json.dumps({
            "folder_id": folder_id,
            "folder_count": len(folders),
            "file_count": len(files),
            "folders": folders,
            "files": files
        }, indent=2)
        
    except HttpError as error:
        return json.dumps({"error": str(error)})
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()

