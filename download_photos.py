import os
import requests
from bs4 import BeautifulSoup
import urllib.parse
from urllib.parse import urlparse

# --- Constants ---\n
TARGET_URL = "https://dereklin.com/books/"
DOWNLOAD_DIR = "dereklin_book_photos"
ALLOWED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp")

# --- Helper Functions ---
def create_directory_if_not_exists(directory_name):
    if not os.path.exists(directory_name):
        os.makedirs(directory_name)
        print(f"Directory '{directory_name}' created.")
    else:
        print(f"Directory '{directory_name}' already exists.")

def get_filename_from_url(url):
    path = urlparse(url).path
    filename = os.path.basename(path)
    if not filename:
        # If no filename in path, try to generate one or use a default
        # For now, let's use the last part of the URL if possible, or a generic name
        filename = url.split('/')[-1]
        if '?' in filename:
            filename = filename.split('?')[0]
        if not filename or not any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
            # Fallback if still no good filename
            return f"image_{hash(url)}.png" # Default to png if extension unknown
    return filename

# --- Main Logic ---
def download_all_photos(url, download_folder):
    print(f"Attempting to download photos from: {url}")
    create_directory_if_not_exists(download_folder)

    try:
        response = requests.get(url, timeout=30) # Added timeout
        response.raise_for_status()  # Raise an exception for HTTP errors
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
        return

    soup = BeautifulSoup(response.content, 'html.parser')
    img_tags = soup.find_all('img')

    if not img_tags:
        print("No image tags found on the page.")
        return

    print(f"Found {len(img_tags)} image tags. Processing...")
    downloaded_count = 0

    for img_tag in img_tags:
        img_url_relative = img_tag.get('src')
        if not img_url_relative:
            print(f"Skipping img tag with no src: {img_tag}")
            continue

        # Construct absolute URL
        img_url_absolute = urllib.parse.urljoin(url, img_url_relative)

        # Filter by extension
        if not any(img_url_absolute.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
            print(f"Skipping non-image or unsupported extension: {img_url_absolute}")
            continue

        # Get filename
        filename = get_filename_from_url(img_url_absolute)
        filepath = os.path.join(download_folder, filename)

        try:
            print(f"Downloading {img_url_absolute} to {filepath}...")
            img_response = requests.get(img_url_absolute, stream=True, timeout=30)
            img_response.raise_for_status()
            with open(filepath, 'wb') as f:
                for chunk in img_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Successfully downloaded {filename}")
            downloaded_count += 1
        except requests.exceptions.RequestException as e:
            print(f"Error downloading {img_url_absolute}: {e}")
        except IOError as e:
            print(f"Error saving file {filepath}: {e}")

    print(f"\nDownload process finished. {downloaded_count} images downloaded to '{download_folder}'.")

# --- Script Execution ---
if __name__ == "__main__":
    download_all_photos(TARGET_URL, DOWNLOAD_DIR)
