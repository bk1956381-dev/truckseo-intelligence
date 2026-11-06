import httpx
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, urljoin

from app.crawler.fetcher import validate_url
from app.crawler.sitemap import discover_sitemap


def get_sitemap_locations(base_url: str):
    robots_url = urljoin(base_url, "/robots.txt")
    sitemap_locations = []

    try:
        validate_url(robots_url)

        response = httpx.get(
            robots_url,
            timeout=15,
            follow_redirects=False
        )

        if response.status_code == 200:
            for line in response.text.splitlines():
                if line.lower().startswith("sitemap:"):
                    sitemap_locations.append(
                        line.split(":", 1)[1].strip()
                    )

    except (httpx.HTTPError, ValueError):
        pass

    if not sitemap_locations:
        sitemap_locations.append(
            urljoin(base_url, "/sitemap.xml")
        )

    return list(dict.fromkeys(sitemap_locations))


def parse_sitemap(sitemap_url: str, base_domain: str):
    validate_url(sitemap_url)

    response = httpx.get(
        sitemap_url,
        timeout=15,
        follow_redirects=False,
        headers={"User-Agent": "TruckSEO-Intelligence/1.0"}
    )

    response.raise_for_status()

    root = ET.fromstring(response.content)

    urls = []

    for element in root.iter():
        if element.tag.endswith("loc") and element.text:
            location = element.text.strip()

            if urlparse(location).hostname == base_domain:
                urls.append(location)

    return urls


def discover_sitemap(website_url: str):
    parsed = urlparse(website_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    base_domain = parsed.hostname

    if not base_domain:
        return []

    discovered_urls = set()

    for sitemap_url in get_sitemap_locations(base_url):
        try:
            discovered_urls.update(
                parse_sitemap(sitemap_url, base_domain)
            )
        except (httpx.HTTPError, ET.ParseError, ValueError):
            continue

    return sorted(discovered_urls)