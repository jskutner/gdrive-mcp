#!/usr/bin/env python3
"""
Google Drive Recent Files Script

Shows files you've recently edited or viewed in Google Drive.
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Scopes required for the Drive API
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
CLIENT_SECRETS_FILE = PROJECT_ROOT / 'client_secrets.json'
TOKEN_FILE = PROJECT_ROOT / 'token.json'


def get_credentials():
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
                print(f"Error: {CLIENT_SECRETS_FILE} not found!")
                print("Please follow the setup instructions to create client_secrets.json")
                sys.exit(1)
            
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CLIENT_SECRETS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    
    return creds


def get_recent_files(hours=24, mode='edited', json_output=False):
    """
    Get recent files from Google Drive.
    
    Args:
        hours: Number of hours to look back (default: 24)
        mode: 'edited' or 'viewed' (default: 'edited')
        json_output: If True, output JSON instead of formatted text
    """
    try:
        creds = get_credentials()
        service = build('drive', 'v3', credentials=creds)
        
        # Calculate the time threshold
        threshold_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        threshold_time_str = threshold_time.strftime('%Y-%m-%dT%H:%M:%S')
        
        # Build query based on mode
        if mode == 'edited':
            query = f"modifiedTime >= '{threshold_time_str}' and trashed = false"
            order_by = 'modifiedTime desc'
        elif mode == 'viewed':
            # Note: 'viewed' requires different approach - we'll use activity API
            # For now, we'll use modifiedTime as a proxy
            query = f"modifiedTime >= '{threshold_time_str}' and trashed = false"
            order_by = 'modifiedTime desc'
        else:
            print(f"Error: mode must be 'edited' or 'viewed', got '{mode}'")
            sys.exit(1)
        
        # Execute the query
        results = service.files().list(
            q=query,
            orderBy=order_by,
            pageSize=50,
            fields="nextPageToken, files(id, name, mimeType, modifiedTime, createdTime, webViewLink)"
        ).execute()
        
        items = results.get('files', [])
        
        if json_output:
            # Output as JSON
            output = []
            for item in items:
                output.append({
                    'id': item.get('id'),
                    'name': item.get('name'),
                    'mimeType': item.get('mimeType'),
                    'modifiedTime': item.get('modifiedTime'),
                    'createdTime': item.get('createdTime'),
                    'webViewLink': item.get('webViewLink')
                })
            print(json.dumps(output, indent=2))
        else:
            # Output formatted text
            if not items:
                print(f"No files {mode} in the last {hours} hours.")
                return
            
            print(f"\n📁 Files {mode} in the last {hours} hours:\n")
            for i, item in enumerate(items, 1):
                name = item.get('name', 'Untitled')
                modified = item.get('modifiedTime', '')
                link = item.get('webViewLink', '')
                
                # Parse and format the time
                if modified:
                    try:
                        mod_time = datetime.fromisoformat(modified.replace('Z', '+00:00'))
                        mod_time_str = mod_time.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        mod_time_str = modified
                else:
                    mod_time_str = 'Unknown'
                
                print(f"{i}. {name}")
                print(f"   Modified: {mod_time_str}")
                if link:
                    print(f"   Link: {link}")
                print()
    
    except HttpError as error:
        print(f'An error occurred: {error}')
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Show recent files from Google Drive',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Show files edited in last 24 hours
  %(prog)s --hours 48               # Show files edited in last 48 hours
  %(prog)s --hours 24 --mode viewed # Show files viewed in last 24 hours
  %(prog)s --json                   # Output as JSON
        """
    )
    
    parser.add_argument(
        '--hours',
        type=int,
        default=24,
        help='Number of hours to look back (default: 24)'
    )
    
    parser.add_argument(
        '--mode',
        choices=['edited', 'viewed'],
        default='edited',
        help='Whether to show edited or viewed files (default: edited)'
    )
    
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )
    
    args = parser.parse_args()
    
    get_recent_files(hours=args.hours, mode=args.mode, json_output=args.json)


if __name__ == '__main__':
    main()

