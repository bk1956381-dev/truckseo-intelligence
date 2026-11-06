from urllib.parse import urljoin, urlparse, urldefrag


def extract_internal_links(base_url: str, links: list):
    base_domain = urlparse(base_url).hostname
    internal_links = set()

    for link in links:
        absolute_url = urljoin(base_url, link)
        absolute_url, _ = urldefrag(absolute_url)

        parsed = urlparse(absolute_url)

        if parsed.scheme not in ("http", "https"):
            continue

        if parsed.hostname != base_domain:
            continue

        internal_links.add(absolute_url)

    return sorted(internal_links)