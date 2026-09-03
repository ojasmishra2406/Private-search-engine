import os
import requests
import zipfile
import io

def download_python_docs(dest_dir="data"):
    os.makedirs(dest_dir, exist_ok=True)
    url = "https://docs.python.org/3.12/archives/python-3.12-docs-html.zip"
    print(f"Downloading {url}...")
    response = requests.get(url)
    response.raise_for_status()
    
    print("Extracting...")
    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
        zip_ref.extractall(dest_dir)
    print(f"Extracted to {dest_dir}")

if __name__ == "__main__":
    download_python_docs()
