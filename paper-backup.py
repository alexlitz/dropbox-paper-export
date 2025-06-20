import requests
import json
import shutil
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description='Export Dropbox Paper Notes.')
    parser.add_argument('-d','--dest', help='Where to store the data.', required=True)
    parser.add_argument('-f','--force', help='Force deletion of destination folder.', action='store_true')
    parser.add_argument('-k','--api-key', help='Dropbox API access token.', required=True)
    parser.add_argument('-p','--path', help='Dropbox folder path to export.', default='/Migrated Paper Docs')
    args = parser.parse_args()

    # Use the API key from command line argument
    apikey = args.api_key
    backup_path = Path(args.dest)
    dropbox_path = args.path

    if args.force:
        shutil.rmtree(backup_path, ignore_errors=True)
    else:
        if backup_path.exists():
            response = input('Destination directory already exists. Delete it? (y/n): ')
            if response.lower() != 'y':
                print('Exiting without making changes.')
                return
            shutil.rmtree(backup_path, ignore_errors=True)

    # Set up headers for API calls
    headers = {
        'Authorization': f'Bearer {apikey}',
        'Content-Type': 'application/json'
    }

    # List the contents of the specified folder
    list_url = "https://api.dropboxapi.com/2/files/list_folder"
    list_data = {
        'path': dropbox_path,
        'recursive': True
    }

    resp = requests.post(list_url, headers=headers, json=list_data)
    if resp.status_code != 200:
        print(f'Error listing {dropbox_path} folder: {resp.status_code} {resp.text}')
        return

    folder_contents = resp.json()
    all_files = folder_contents.get('entries', [])
    
    # Handle pagination if there are more entries
    while folder_contents.get('has_more', False):
        cursor = folder_contents.get('cursor')
        continue_data = {'cursor': cursor}
        resp = requests.post("https://api.dropboxapi.com/2/files/list_folder/continue", 
                           headers=headers, json=continue_data)
        if resp.status_code == 200:
            folder_contents = resp.json()
            all_files.extend(folder_contents.get('entries', []))
        else:
            break
    
    print(f"Found {len(all_files)} total entries in {dropbox_path}")
    
    # Show all entries for debugging
    for i, entry in enumerate(all_files):
        print(f"  Entry {i+1}: {entry.get('name', 'NO_NAME')} (type: {entry.get('.tag', 'NO_TAG')})")
        if entry.get('.tag') == 'folder':
            print(f"    Path: {entry.get('path_lower', 'NO_PATH')}")
    
    # If we still don't see 7 folders, try listing the root directory
    if len(all_files) < 7:
        print("\nTrying to list root directory...")
        root_data = {'path': '', 'recursive': False}
        resp = requests.post(list_url, headers=headers, json=root_data)
        if resp.status_code == 200:
            root_contents = resp.json()
            print(f"Root directory has {len(root_contents.get('entries', []))} entries:")
            for entry in root_contents.get('entries', [])[:10]:
                if 'paper' in entry.get('name', '').lower():
                    print(f"  Found: {entry.get('name')} (type: {entry.get('.tag')})")
    
    paper_files = [f for f in all_files if f.get('.tag') == 'file' and f['name'].endswith('.paper')]
    print(f"Found {len(paper_files)} .paper files")
    
    # Download all files in the folder (not just .paper files)
    download_url = "https://content.dropboxapi.com/2/files/download"
    backup_path.mkdir(parents=True, exist_ok=True)

    all_paper_files = [f for f in all_files if f.get('.tag') == 'file']
    print(f"Downloading {len(all_paper_files)} files...")

    for file_meta in all_paper_files:
        file_path = file_meta['path_lower']
        file_name = file_meta['name']
        
        # Create download headers
        download_headers = {
            'Authorization': f'Bearer {apikey}',
            'Dropbox-API-Arg': json.dumps({'path': file_path})
        }
        
        # Retry logic for 409 conflicts
        max_retries = 3
        for attempt in range(max_retries):
            # Use export endpoint for .paper files, regular download for others
            if file_name.endswith('.paper'):
                export_url = "https://content.dropboxapi.com/2/files/export"
                export_headers = {
                    'Authorization': f'Bearer {apikey}',
                    'Dropbox-API-Arg': json.dumps({'path': file_path, 'export_format': 'markdown'})
                }
                resp = requests.post(export_url, headers=export_headers)
            else:
                resp = requests.post(download_url, headers=download_headers)
            
            if resp.status_code == 200:
                break
            elif resp.status_code == 409:
                # Handle unsupported file error - these are likely Paper docs that need special handling
                error_data = resp.json() if resp.text else {}
                if error_data.get('error', {}).get('.tag') == 'unsupported_file':
                    print(f'Skipping unsupported file: {file_name}')
                    break
                elif attempt < max_retries - 1:
                    print(f'Conflict downloading {file_name}, retrying... (attempt {attempt + 1})')
                    import time
                    time.sleep(1)  # Wait 1 second before retry
                    continue
                else:
                    print(f'Error downloading {file_name}: {resp.status_code} - {resp.text[:100]}')
                    break
            else:
                print(f'Error downloading {file_name}: {resp.status_code} - {resp.text[:100]}')
                break
        else:
            continue  # Skip this file if all retries failed
            
        # Only save if we got a successful response
        if resp.status_code == 200:
            # Save the file (change extension from .paper to .md)
            output_name = file_name.replace('.paper', '.md')
            
            # Create the full directory structure based on the file path
            relative_path = file_path.replace(dropbox_path.lower() + '/', '')
            file_dir = Path(relative_path).parent
            
            # Create target directory maintaining hierarchy
            if file_dir != Path('.'):
                target_dir = backup_path / file_dir
                target_dir.mkdir(parents=True, exist_ok=True)
                output_path = target_dir / output_name
            else:
                output_path = backup_path / output_name
            
            output_path.write_text(resp.text, encoding='utf-8')
            print(f'saved "{output_name}" to "{output_path.parent}"')

if __name__ == "__main__":
    main()