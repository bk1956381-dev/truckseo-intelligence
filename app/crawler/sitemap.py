
import httpx
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, urljoin

from app.crawler.fetcher import validate_url


def get_sitemap_locations(base_url: str):
    robots_url = urljoin(base_url, "/robots.txt")
    sitemap_locations = []

    try:
        validate_url(robots_url)

        response = httpx.get(
            robots_url,
            timeout=15,
            follow_redirects=False,
            headers={"User-Agent": "TruckSEO-Intelligence/1.0"}
        )

        if response.status_code == 200:
            for line in response.text.splitlines():
                if line.lower().startswith("sitemap:"):
                    location = line.split(":", 1)[1].strip()
                    sitemap_locations.append(location)

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

    # Limit sitemap response size to 2 MB
    if len(response.content) > 2_000_000:
        raise ValueError("Sitemap exceeds 2 MB limit")

    root = ET.fromstring(response.content)

    urls = []
    child_sitemaps = []

    root_type = root.tag.split("}")[-1].lower()

    for element in root.iter():
        if element.tag.split("}")[-1].lower() != "loc":
            continue

        if not element.text:
            continue

        location = element.text.strip()
        parsed_location = urlparse(location)

        if parsed_location.hostname != base_domain:
            continue

        if root_type == "sitemapindex":
            child_sitemaps.append(location)

        elif root_type == "urlset":
            urls.append(location)

    return {
        "urls": urls,
        "sitemaps": child_sitemaps
    }


def discover_sitemap(website_url: str):
    parsed = urlparse(website_url)

    base_url = f"{parsed.scheme}://{parsed.netloc}"
    base_domain = parsed.hostname

    if not base_domain:
        return []

    discovered_urls = set()
    sitemap_queue = get_sitemap_locations(base_url)
    visited_sitemaps = set()

    # Limit sitemap files to prevent excessive requests
    max_sitemaps = 10

    while sitemap_queue and len(visited_sitemaps) < max_sitemaps:
        sitemap_url = sitemap_queue.pop(0)

        if sitemap_url in visited_sitemaps:
            continue

        visited_sitemaps.add(sitemap_url)

        try:
            result = parse_sitemap(sitemap_url, base_domain)

            discovered_urls.update(result["urls"])

            for child in result["sitemaps"]:
                if child not in visited_sitemaps:
                    sitemap_queue.append(child)

        except (httpx.HTTPError, ET.ParseError, ValueError):
            continue

    return sorted(discovered_urls)
