
from collections import deque

from app.crawler.fetcher import fetch_page
from app.crawler.link_extractor import normalize_url
from app.crawler.sitemap import discover_sitemap


def crawl_website(start_url: str, max_pages: int = 20):
    max_pages = min(max(1, max_pages), 20)

    normalized_start = normalize_url(start_url)

    if not normalized_start:
        raise ValueError("Invalid starting URL")

    visited = set()
    queue = deque([normalized_start])
    queued = {normalized_start}
    pages = []

    # Discover sitemap URLs
    try:
        sitemap_urls = discover_sitemap(normalized_start)

        for sitemap_url in sitemap_urls:
            normalized_url = normalize_url(sitemap_url)

            if normalized_url and normalized_url not in queued:
                queue.append(normalized_url)
                queued.add(normalized_url)

    except Exception as error:
        print(f"Sitemap discovery failed: {error}")

    # Prevent unlimited attempts if many URLs fail
    max_attempts = max_pages * 3
    attempts = 0

    while queue and len(pages) < max_pages and attempts < max_attempts:
        url = queue.popleft()

        if url in visited:
            continue

        visited.add(url)
        attempts += 1

        try:
            page_data = fetch_page(url)
            pages.append(page_data)

            for link in page_data["internal_links"]:
                normalized_link = normalize_url(link)

                if (
                    normalized_link
                    and normalized_link not in visited
                    and normalized_link not in queued
                ):
                    queue.append(normalized_link)
                    queued.add(normalized_link)

        except Exception as error:
            print(f"Could not crawl {url}: {error}")

    return {
        "start_url": normalized_start,
        "total_pages": len(pages),
        "pages": pages
    }
