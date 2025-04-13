from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = "./gothic-doodad-456615-d8-5e334deccd14.json"

def upload_to_drive(file_storage, course_id):
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)
        
        # Create or find course folder
        folder_name = f"Course_{course_id}"
        folder_query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
        folders = service.files().list(q=folder_query).execute().get('files', [])
        
        if not folders:
            folder_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
            folder = service.files().create(body=folder_metadata, fields='id').execute()
            folder_id = folder['id']
        else:
            folder_id = folders[0]['id']
        
        # Upload file
        file_metadata = {'name': file_storage.filename, 'parents': [folder_id]}
        file_content = file_storage.read()
        media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype=file_storage.mimetype)
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,webViewLink'
        ).execute()
        
        # Set public permissions
        permission = {'type': 'anyone', 'role': 'reader'}
        service.permissions().create(fileId=file['id'], body=permission).execute()
        
        return file.get('webViewLink')
    except Exception as e:
        print(f"Google Drive upload error: {e}")
        return None