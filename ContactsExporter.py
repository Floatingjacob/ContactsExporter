import os
import base64
import textwrap
import requests
import subprocess
import json
import imghdr
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
output_directory = "./generated_vcards"
photo_cache_directory = "./photo_cache"
os.makedirs(output_directory, exist_ok=True)
os.makedirs(photo_cache_directory, exist_ok=True)

SCOPES = ['https://www.googleapis.com/auth/contacts.readonly']

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    )
}
def load_decoded_credentials():
    try:
        result = subprocess.run(
            ["./decoder"],
            capture_output=True,
            check=True
        )
        hex_data = result.stdout.decode('utf-8').strip()
        if not hex_data:
            raise ValueError("Decoder returned empty hex string!")
        decoded_bytes = bytes.fromhex(hex_data)
        decoded_json_str = decoded_bytes.decode('utf-8')
        client_config = json.loads(decoded_json_str)
        decoded_bytes = None
        decoded_json_str = None
        return client_config
    except subprocess.CalledProcessError as e:
        print(f"Error running decoder: {e}")
        exit(1)
    except Exception as e:
        print(f"Error processing decoded data: {e}")
        exit(1)
def get_google_people_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        client_config = load_decoded_credentials()
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    service = build('people', 'v1', credentials=creds)
    return service
def download_photo(url, contact_id):
    safe_id = "".join(c for c in contact_id if c.isalnum() or c in ('@', '.', '_', '-'))
    filepath = os.path.join(photo_cache_directory, f"{safe_id}.img")
    if os.path.exists(filepath):
        with open(filepath, 'rb') as f:
            return f.read()
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(resp.content)
            return resp.content
        else:
            print(f"Failed to download photo for {contact_id}: HTTP {resp.status_code}")
    except Exception as e:
        print(f"Exception downloading photo for {contact_id}: {e}")
    return None

def create_vcard(name, emails, phones, photo_bytes=None):
    if not name or name.strip() == "":
        if emails:
            name = emails[0]
        elif phones:
            name = phones[0]
        else:
            name = "No Name"

    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"FN:{name}"
    ]

    for email in emails:
        lines.append(f"EMAIL;TYPE=INTERNET:{email}")

    for phone in phones:
        lines.append(f"TEL;TYPE=CELL:{phone}")

    if photo_bytes:
        img_type = imghdr.what(None, h=photo_bytes)
        if img_type:
            img_type = img_type.upper()
        else:
            img_type = "JPEG"

        b64_photo = base64.b64encode(photo_bytes).decode('utf-8')
        b64_lines = textwrap.wrap(b64_photo, 75)
        photo_block = f"PHOTO;ENCODING=BASE64;{img_type}:\n " + "\n ".join(b64_lines)
        lines.append(photo_block)

    lines.append("END:VCARD")
    return "\n".join(lines)

def fetch_and_generate_vcards(service):
    print("Fetching Google Contacts...")

    page_token = None
    total_contacts = 0
    photos_embedded = 0
    vcards = []

    while True:
        results = service.people().connections().list(
            resourceName='people/me',
            pageSize=2000,
            pageToken=page_token,
            personFields='names,emailAddresses,phoneNumbers,photos'
        ).execute()

        connections = results.get('connections', [])
        for person in connections:
            total_contacts += 1

            names = person.get('names', [])
            full_name = names[0]['displayName'] if names else None

            emails = [e['value'] for e in person.get('emailAddresses', [])]
            phones = [p['value'] for p in person.get('phoneNumbers', [])]

            photos = person.get('photos', [])
            photo_url = None
            for photo in photos:
                if not photo.get('default', True):
                    photo_url = photo.get('url')
                    break
            if not photo_url and photos:
                photo_url = photos[0].get('url')

            photo_bytes = None
            if photo_url:
                contact_id = emails[0] if emails else f"contact_{total_contacts}"
                photo_bytes = download_photo(photo_url, contact_id)
                if photo_bytes:
                    photos_embedded += 1

            vcard_str = create_vcard(full_name, emails, phones, photo_bytes)
            vcards.append(vcard_str)

            print(f"Processed contact #{total_contacts}: {full_name or 'No Name'}")

        page_token = results.get('nextPageToken')
        if not page_token:
            break

    merged_output_path = os.path.join(output_directory, "all_contacts.vcf")
    with open(merged_output_path, 'w', encoding='utf-8') as merged_file:
        merged_file.write("\n".join(vcards))

    print("\n=== Summary ===")
    print(f"Total contacts fetched: {total_contacts}")
    print(f"Photos embedded: {photos_embedded}")
    print(f"vCards merged into: {merged_output_path}")
    print("================")

def main():
    service = get_google_people_service()
    fetch_and_generate_vcards(service)

if __name__ == '__main__':
    main()

