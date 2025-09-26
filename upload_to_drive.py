
import os
import sys
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'

def main():
    """Handles authentication and file upload to Google Drive."""
    if len(sys.argv) < 2:
        print("Usage: python upload_to_drive.py <file_path>")
        sys.exit(1)

    file_to_upload = sys.argv[1]
    if not os.path.exists(file_to_upload):
        print(f"Error: File not found at {file_to_upload}")
        sys.exit(1)

    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('drive', 'v3', credentials=creds)

        file_metadata = {'name': os.path.basename(file_to_upload)}
        media = MediaFileUpload(file_to_upload, mimetype='application/octet-stream')
        
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(f"File '{os.path.basename(file_to_upload)}' uploaded successfully to Google Drive with File ID: {file.get('id')}")

    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
