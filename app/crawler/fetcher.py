
import httpx
import socket
import ipaddress
import json

from bs4 import BeautifulSoup
from urllib.parse import urlsplit, urljoin

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

    # Extract page title
    title = (
        soup.title.get_text(" ", strip=True)
        if soup.title else None
    )

    # Extract meta description
    meta_tag = soup.find(
        "meta",
        attrs={"name": "description"}
    )

    meta_description = (
        meta_tag.get("content")
        if meta_tag else None
    )

    # Extract hyperlinks
    links = [
        link.get("href")
        for link in soup.find_all("a", href=True)
    ]

    internal_links = extract_internal_links(url, links)

            # Extract images and ALT attributes
    images = []

    for image in soup.find_all("img"):
        image_src = image.get("src")

        images.append({
            "src": urljoin(url, image_src) if image_src else None,
            "alt": image.get("alt", "")
        })
    # Extract HTML lists
    lists = []

    for list_tag in soup.find_all(["ul", "ol"]):
        items = [
            item.get_text(" ", strip=True)
            for item in list_tag.find_all("li", recursive=False)
        ]

        if items:
            lists.append({
                "type": list_tag.name,
                "items": items
            })

    # Extract answers following question-based headings
    faq_sections = []

    question_words = (
        "what ", "why ", "how ", "when ", "where ",
        "who ", "which ", "can ", "does ", "do ",
        "is ", "are "
    )

    for heading in soup.find_all(["h1", "h2", "h3", "h4"]):
        question = heading.get_text(" ", strip=True)

        if not (
            question.lower().startswith(question_words)
            or "?" in question
        ):
            continue

        answer_tag = heading.find_next_sibling(["p", "ul", "ol"])

        if answer_tag:
            answer = answer_tag.get_text(" ", strip=True)

            if answer:
                faq_sections.append({
                    "question": question,
                    "answer": answer[:500]
                })


    # Extract JSON-LD structured data
    structured_data = []

    for script in soup.find_all(
        "script",
        attrs={"type": "application/ld+json"}
    ):
        try:
            json_content = json.loads(
                script.string or script.get_text()
            )

            structured_data.append(json_content)

        except (json.JSONDecodeError, TypeError):
            continue

    # Return extracted page information
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
        "internal_links": internal_links,
        "images": images,
        "structured_data": structured_data,
        "lists": lists,
        "faq_sections": faq_sections
    }
