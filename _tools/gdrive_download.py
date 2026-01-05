#!/usr/bin/env python3
"""
Google Drive File Download Script

Downloads/exports files from Google Drive.
"""

import os
import sys
import argparse
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
import io

# Scopes required for the Drive API
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
CLIENT_SECRETS_FILE = PROJECT_ROOT / 'client_secrets.json'
TOKEN_FILE = PROJECT_ROOT / 'token.json'

# Export MIME types for Google Workspace files
EXPORT_MIME_TYPES = {
    'application/vnd.google-apps.document': {
        'text/plain': '.txt',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
        'application/pdf': '.pdf',
        'text/html': '.html',
    },
    'application/vnd.google-apps.spreadsheet': {
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
        'text/csv': '.csv',
        'application/pdf': '.pdf',
    },
    'application/vnd.google-apps.presentation': {
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
        'application/pdf': '.pdf',
        'text/plain': '.txt',
    },
    'application/vnd.google-apps.drawing': {
        'image/png': '.png',
        'image/jpeg': '.jpg',
        'application/pdf': '.pdf',
    },
}


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


def find_file_by_name(service, name):
    """Find a file by name in Google Drive."""
    try:
        results = service.files().list(
            q=f"name = '{name}' and trashed = false",
            fields="files(id, name, mimeType)"
        ).execute()
        
        items = results.get('files', [])
        if not items:
            return None
        if len(items) > 1:
            print(f"Warning: Multiple files found with name '{name}'. Using the first one.")
        return items[0]
    except HttpError as error:
        print(f'An error occurred while searching: {error}')
        return None


def download_file(service, file_id, file_name, mime_type, output_path, export_format=None):
    """Download or export a file from Google Drive."""
    try:
        # Check if it's a Google Workspace file that needs export
        if mime_type.startswith('application/vnd.google-apps.'):
            # Get available export formats
            export_options = EXPORT_MIME_TYPES.get(mime_type, {})
            
            if not export_options:
                print(f"Error: No export format available for {mime_type}")
                return False
            
            # Determine export format
            if export_format:
                # User specified format
                if export_format not in export_options:
                    print(f"Error: Export format '{export_format}' not available for this file type.")
                    print(f"Available formats: {', '.join(export_options.keys())}")
                    return False
                export_mime = export_format
            else:
                # Default: use text/plain if available, otherwise first option
                if 'text/plain' in export_options:
                    export_mime = 'text/plain'
                else:
                    export_mime = list(export_options.keys())[0]
            
            extension = export_options[export_mime]
            
            # Export the file
            print(f"Exporting as {export_mime}...")
            request = service.files().export_media(fileId=file_id, mimeType=export_mime)
        else:
            # Regular file - download directly
            extension = ''
            print(f"Downloading file...")
            request = service.files().get_media(fileId=file_id)
        
        # Determine output file path
        if output_path.is_dir():
            # Output is a directory, create filename
            if extension:
                output_file = output_path / f"{file_name}{extension}"
            else:
                # Try to get extension from original file
                output_file = output_path / file_name
        else:
            # Output is a specific file path
            output_file = output_path
        
        # Download the file
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            if status:
                print(f"  Download progress: {int(status.progress() * 100)}%")
        
        # Write to file
        with open(output_file, 'wb') as f:
            f.write(fh.getvalue())
        
        print(f"✓ File saved to: {output_file}")
        return True
        
    except HttpError as error:
        print(f'An error occurred: {error}')
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Download/export files from Google Drive',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "My Document"                    # Download by name (auto-detect format)
  %(prog)s "My Document" --format text/plain # Export as plain text
  %(prog)s --id FILE_ID --output ./file.txt # Download by file ID
        """
    )
    
    parser.add_argument(
        'file_name',
        nargs='?',
        help='Name of the file to download'
    )
    
    parser.add_argument(
        '--id',
        dest='file_id',
        help='File ID (alternative to file name)'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=Path,
        help='Output file or directory path (default: current directory)',
        default=Path.cwd()
    )
    
    parser.add_argument(
        '--format',
        help='Export format MIME type (e.g., text/plain, application/pdf)'
    )
    
    args = parser.parse_args()
    
    if not args.file_name and not args.file_id:
        parser.error("Either file_name or --id must be provided")
    
    try:
        creds = get_credentials()
        service = build('drive', 'v3', credentials=creds)
        
        # Get file info
        if args.file_id:
            try:
                file_metadata = service.files().get(
                    fileId=args.file_id,
                    fields='id, name, mimeType'
                ).execute()
                file_info = file_metadata
            except HttpError as error:
                print(f'Error getting file: {error}')
                sys.exit(1)
        else:
            file_info = find_file_by_name(service, args.file_name)
            if not file_info:
                print(f"Error: File '{args.file_name}' not found in Google Drive")
                sys.exit(1)
        
        file_id = file_info['id']
        file_name = file_info['name']
        mime_type = file_info['mimeType']
        
        print(f"Found file: {file_name} (ID: {file_id})")
        print(f"Type: {mime_type}")
        
        # Download/export the file
        success = download_file(
            service, file_id, file_name, mime_type,
            args.output, args.format
        )
        
        if not success:
            sys.exit(1)
    
    except HttpError as error:
        print(f'An error occurred: {error}')
        sys.exit(1)


if __name__ == '__main__':
    main()
