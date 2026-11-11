
from urllib.parse import urljoin, urlsplit, urlunsplit


def normalize_url(url: str):
    try:
        parsed = urlsplit(url)

        scheme = parsed.scheme.lower()
        hostname = parsed.hostname

        if scheme not in ("http", "https") or not hostname:
            return None

        if parsed.username or parsed.password:
            return None

        port = parsed.port
        hostname = hostname.lower()

        if ":" in hostname:
            hostname = f"[{hostname}]"

        if port and not (
            (scheme == "http" and port == 80)
            or (scheme == "https" and port == 443)
        ):
            hostname = f"{hostname}:{port}"

        return urlunsplit((
            scheme,
            hostname,
            parsed.path or "/",
            parsed.query,
            ""
        ))

    except ValueError:
        return None


def extract_internal_links(base_url: str, links: list):
    base_domain = urlsplit(base_url).hostname

    if not base_domain:
        return []

    base_domain = base_domain.lower()
    internal_links = set()

    for link in links:
        absolute_url = urljoin(base_url, link)
        normalized_url = normalize_url(absolute_url)

        if not normalized_url:
            continue

        parsed = urlsplit(normalized_url)

        if parsed.hostname != base_domain:
            continue

        internal_links.add(normalized_url)

    return sorted(internal_links)
