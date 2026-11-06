import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import socket
import ipaddress

from app.crawler.link_extractor import extract_internal_links


def validate_url(url: str):
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Invalid HTTP/HTTPS website URL")

    addresses = socket.getaddrinfo(
        parsed.hostname, None, type=socket.SOCK_STREAM
    )

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])

        if not ip.is_global:
            raise ValueError("Private or unsafe IP address blocked")


def fetch_page(url: str):
    validate_url(url)

    with httpx.Client(
        timeout=15,
        follow_redirects=False,
        headers={"User-Agent": "TruckSEO-Intelligence/1.0"}
    ) as client:

        with client.stream("GET", url) as response:
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")

            if "text/html" not in content_type.lower():
                raise ValueError("URL did not return HTML")

            chunks = []
            total_size = 0

            for chunk in response.iter_bytes():
                total_size += len(chunk)

                if total_size > 2_000_000:
                    raise ValueError("Page exceeds 2 MB limit")

                chunks.append(chunk)

            html = b"".join(chunks)

    soup = BeautifulSoup(html, "lxml")

    links = [
        link.get("href")
        for link in soup.find_all("a", href=True)
    ]

    internal_links = extract_internal_links(url, links)

    return {
        "url": url,
        "title": soup.title.get_text(strip=True) if soup.title else None,
        "meta_description": (
            soup.find("meta", attrs={"name": "description"}).get("content")
            if soup.find("meta", attrs={"name": "description"})
            else None
        ),
        "headings": {
            "h1": [h.get_text(" ", strip=True) for h in soup.find_all("h1")],
            "h2": [h.get_text(" ", strip=True) for h in soup.find_all("h2")]
        },
        "text": soup.get_text(" ", strip=True)[:10000],
        "links": links,
        "internal_links": internal_links
    }