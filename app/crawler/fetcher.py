
import httpx
import socket
import ipaddress

from bs4 import BeautifulSoup
from urllib.parse import urlsplit

from app.crawler.link_extractor import extract_internal_links


MAX_PAGE_SIZE = 2_000_000
REQUEST_TIMEOUT = 15


def validate_url(url: str):
    try:
        parsed = urlsplit(url)

        if parsed.scheme.lower() not in ("http", "https"):
            raise ValueError("Only HTTP and HTTPS URLs are allowed")

        if not parsed.hostname:
            raise ValueError("Invalid website URL")

        if parsed.username or parsed.password:
            raise ValueError("URLs with credentials are not allowed")

        port = parsed.port

        if port and port not in (80, 443):
            raise ValueError("Non-standard ports are not allowed")

        addresses = socket.getaddrinfo(
            parsed.hostname,
            port or (443 if parsed.scheme.lower() == "https" else 80),
            type=socket.SOCK_STREAM
        )

        if not addresses:
            raise ValueError("Website hostname could not be resolved")

        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])

            if not ip.is_global:
                raise ValueError("Private or unsafe IP address blocked")

    except socket.gaierror:
        raise ValueError("Website hostname could not be resolved")

    except ValueError:
        raise

    except Exception:
        raise ValueError("Invalid or unsafe website URL")


def fetch_page(url: str):
    validate_url(url)

    try:
        with httpx.Client(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=False,
            trust_env=False,
            headers={
                "User-Agent": "TruckSEO-Intelligence/1.0"
            }
        ) as client:

            with client.stream("GET", url) as response:
                response.raise_for_status()

                content_type = response.headers.get(
                    "content-type", ""
                )

                if "text/html" not in content_type.lower():
                    raise ValueError("URL did not return HTML")

                chunks = []
                total_size = 0

                for chunk in response.iter_bytes():
                    total_size += len(chunk)

                    if total_size > MAX_PAGE_SIZE:
                        raise ValueError(
                            "Page exceeds 2 MB limit"
                        )

                    chunks.append(chunk)

                html = b"".join(chunks)

    except httpx.TimeoutException:
        raise RuntimeError("Website request timed out")

    except httpx.HTTPStatusError as error:
        raise RuntimeError(
            f"Website returned HTTP {error.response.status_code}"
        )

    except httpx.RequestError:
        raise RuntimeError("Could not connect to website")

    soup = BeautifulSoup(html, "lxml")

    title = (
        soup.title.get_text(" ", strip=True)
        if soup.title else None
    )

    meta_tag = soup.find(
        "meta",
        attrs={"name": "description"}
    )

    meta_description = (
        meta_tag.get("content")
        if meta_tag else None
    )

    links = [
        link.get("href")
        for link in soup.find_all("a", href=True)
    ]

    internal_links = extract_internal_links(url, links)

    return {
        "url": url,
        "title": title,
        "meta_description": meta_description,
        "headings": {
            "h1": [
                h.get_text(" ", strip=True)
                for h in soup.find_all("h1")
            ],
            "h2": [
                h.get_text(" ", strip=True)
                for h in soup.find_all("h2")
            ]
        },
        "text": soup.get_text(" ", strip=True)[:10000],
        "links": links,
        "internal_links": internal_links
    }
