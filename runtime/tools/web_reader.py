import requests
from bs4 import BeautifulSoup
import hashlib

from runtime_paths import aoia_state_home


def cache_name(url: str):
    cache_dir = aoia_state_home() / "web_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{hashlib.md5(url.encode()).hexdigest()}.txt"

def fetch_page(url: str):
    cache_file = cache_name(url)

    if cache_file.exists():
        return cache_file.read_text()

    response = requests.get(
        url,
        timeout=20,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    soup = BeautifulSoup(response.text, "html.parser")

    text = soup.get_text(separator="\n")

    cleaned = "\n".join(
        line.strip()
        for line in text.splitlines()
        if line.strip()
    )

    cache_file.write_text(cleaned)

    return cleaned[:15000]

if name == "main":
    url = input("URL: ")
    print(fetch_page(url))
