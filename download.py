from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import io
import os
import pickle
import sys
import argparse

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# using 
USE_ID = False

def main():
    parser = argparse.ArgumentParser(description="Download Files in Folder from Google Drive", 
                                    epilog="You can download folder by 'Folder Name' or 'Folder ID'\n")

    parser.add_argument("SOURCE", help="source folder on google drive", type=str)

    parser.add_argument("DEST", help="local folder name")
    
    parser.add_argument("-id", "--using_id", help="using folder id", action='store_true')

    args = parser.parse_args()

    if args.SOURCE is None:
        print("no target folder name")  
        return
    else:
        print("Input\nSOURCE: {}\nDEST: {}\nusing id: {}\n".format(args.SOURCE, args.DEST, args.using_id))  

    service = get_google_credentials()

    folder_id, folder_name = search_folders(service, args)

    download_folder(service, args.DEST, folder_id, folder_name)

def get_google_credentials():
    '''https://developers.google.com/drive/api/v3/quickstart/python'''
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=1337)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token, protocol=0)
    service = build('drive', 'v3', credentials=creds)
    return service

def get_full_path(service, folder):
    if not 'parents' in folder:
        return folder['name']
    files = service.files().get(fileId=folder['parents'][0], fields='id, name, parents').execute()
    path = files['name'] + ' > ' + folder['name']
    while 'parents' in files:
        files = service.files().get(fileId=files['parents'][0], fields='id, name, parents').execute()
        path = files['name'] + ' > ' + path
    return path

def search_folders(service, args):
    '''
        if specify fileId, return target directly
        else choose specify fileId
    '''
    if args.using_id:
        folder = service.files().get(fileId=args.SOURCE, fields='id, name, parents').execute()
        print("Full Path: {}\n".format(get_full_path(service, folder)))
        return folder['id'], folder['name']
    else:
        folder = service.files().list(
                q=f"name contains '{args.SOURCE}' and mimeType='application/vnd.google-apps.folder'",
                fields='files(id, name, parents)').execute()
        
        total = len(folder['files'])
        if total != 1:
            print(f'{total} folders found')
            if total == 0:
                sys.exit(1)
            prompt = 'Please select the folder you want to download:\n\n'
            for i in range(total):
                prompt += f'[{i}]: {get_full_path(service, folder["files"][i])}\n'
            prompt += '\nYour choice: '
            choice = int(input(prompt))
            if 0 <= choice and choice < total:
                folder_id = folder['files'][choice]['id']
                folder_name = folder['files'][choice]['name']
            else:
                sys.exit(1)
        else:
            folder_id = folder['files'][0]['id']
            folder_name = folder['files'][0]['name']
            print("Full Path: {}".format(get_full_path(service, folder['files'][0])))
            print("folder id: {}\nfolder name: {}\n".format(folder_id, folder_name))
        return folder_id, folder_name

def download_folder(service, destination, folder_id, folder_name):
    # check local folder exists
    if not os.path.exists(os.path.join(destination, folder_name)):
        os.makedirs(os.path.join(destination, folder_name))
    destination = os.path.join(destination, folder_name)

    result = []
    page_token = None
    while True:
        files = service.files().list(
                q=f"'{folder_id}' in parents",
                fields='nextPageToken, files(id, name, mimeType)',
                pageToken=page_token,
                pageSize=1000).execute()
        result.extend(files['files'])
        page_token = files.get("nextPageToken")
        if not page_token:
            break

    result = sorted(result, key=lambda k: k['name'])

    total = len(result)
    current = 1
    for item in result:
        file_id = item['id']
        filename = item['name']
        mime_type = item['mimeType']
        print(f'{file_id} {filename} {mime_type} ({current}/{total})')
        # when exist child folder on google drive, download recursive
        if mime_type == 'application/vnd.google-apps.folder':
            download_folder(service, destination, file_id, filename)
        # if file exist on local, skip it
        elif not os.path.isfile(os.path.join(destination, filename)):
            download_file(service, file_id, destination, filename, mime_type)
        current += 1

def download_file(service, file_id, destination, filename, mime_type):
    if 'vnd.google-apps' in mime_type:
        request = service.files().export_media(fileId=file_id,
                mimeType='application/pdf')
        filename += '.pdf'
    else:
        request = service.files().get_media(fileId=file_id)
    
    local_name = os.path.join(destination, filename)
    fh = io.FileIO(local_name, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        try:
            status, done = downloader.next_chunk()
        except Exception as e:
            print(e)
            fh.close()
            os.remove(local_name)
            sys.exit(1)
        print(f'\rDownload {int(status.progress() * 100)}%.', end='')
        sys.stdout.flush()
    print('')

if __name__ == '__main__':
    main()