from collections import deque
from app.crawler.fetcher import fetch_page
from app.crawler.link_extractor import normalize_url


def crawl_website(start_url: str, max_pages: int = 20):
    max_pages = min(max(1, max_pages), 20)

    normalized_start = normalize_url(start_url)

    if not normalized_start:
        raise ValueError("Invalid starting URL")

    visited = set()
    queue = deque([normalized_start])
    pages = []

    while queue and len(pages) < max_pages:
        url = queue.popleft()

        if url in visited:
            continue

        visited.add(url)

        try:
            page_data = fetch_page(url)
            pages.append(page_data)

            for link in page_data["internal_links"]:
                normalized_link = normalize_url(link)

                if normalized_link and normalized_link not in visited:
                    queue.append(normalized_link)

        except Exception as error:
            print(f"Could not crawl {url}: {error}")

    return {
        "start_url": normalized_start,
        "total_pages": len(pages),
        "pages": pages
    }