import httpx
import xml.etree.ElementTree as ET

from urllib.parse import urljoin, urlsplit

from app.crawler.fetcher import validate_url


REQUEST_TIMEOUT = 10
MAX_LINK_CHECKS = 20


def safe_get(url):
    validate_url(url)

    return httpx.get(
        url,
        timeout=REQUEST_TIMEOUT,
        follow_redirects=False,
        trust_env=False,
        headers={"User-Agent": "TruckSEO-Intelligence/1.0"}
    )


def get_origin(url):
    parsed = urlsplit(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def check_robots_and_sitemap(website_url):
    origin = get_origin(website_url)
    robots_url = urljoin(origin, "/robots.txt")

    result = {
        "robots_status": None,
        "robots_found": False,
        "sitemap_status": None,
        "sitemap_found": False,
        "sitemap_url_count": 0,
        "issues": []
    }

    sitemap_urls = []

    try:
        response = safe_get(robots_url)
        result["robots_status"] = response.status_code

        if response.status_code == 200:
            result["robots_found"] = True

            for line in response.text.splitlines():
                line = line.strip()

                if line.lower().startswith("sitemap:"):
                    sitemap_urls.append(
                        line.split(":", 1)[1].strip()
                    )
        else:
            result["issues"].append("robots.txt is missing or unavailable")

    except Exception:
        result["issues"].append("Could not access robots.txt")

    if not sitemap_urls:
        sitemap_urls.append(urljoin(origin, "/sitemap.xml"))

    sitemap_url = sitemap_urls[0]
    result["sitemap_url"] = sitemap_url

    try:
        response = safe_get(sitemap_url)
        result["sitemap_status"] = response.status_code

        if response.status_code == 200:
            root = ET.fromstring(response.content)

            if root.tag.split("}")[-1].lower() in (
                "urlset", "sitemapindex"
            ):
                result["sitemap_found"] = True

                result["sitemap_url_count"] = sum(
                    1 for element in root.iter()
                    if element.tag.split("}")[-1].lower() == "loc"
                )
            else:
                result["issues"].append("Sitemap XML format is invalid")
        else:
            result["issues"].append("XML sitemap is missing or unavailable")

    except Exception:
        result["issues"].append("Could not read or parse XML sitemap")

    return result


def check_internal_links(pages):
    links = set()

    for page in pages:
        for link in page.get("internal_links", []):
            links.add(link)

    checked = []
    broken_links = []
    redirects = []

    for link in sorted(links)[:MAX_LINK_CHECKS]:
        current_url = link
        redirect_chain = []
        status = None

        try:
            for _ in range(6):
                response = safe_get(current_url)
                status = response.status_code

                if status in (301, 302, 303, 307, 308):
                    location = response.headers.get("location")

                    if not location:
                        break

                    next_url = urljoin(current_url, location)

                    if urlsplit(next_url).hostname != urlsplit(link).hostname:
                        redirect_chain.append(next_url)
                        break

                    redirect_chain.append(next_url)
                    current_url = next_url
                    continue

                break

            checked.append({
                "url": link,
                "status": status,
                "final_url": current_url,
                "redirect_chain": redirect_chain
            })

            if status is None or status >= 400:
                broken_links.append(link)

            if redirect_chain:
                redirects.append({
                    "url": link,
                    "destination": current_url,
                    "redirect_count": len(redirect_chain)
                })

        except Exception:
            checked.append({
                "url": link,
                "status": None,
                "final_url": current_url,
                "redirect_chain": redirect_chain
            })
            broken_links.append(link)

    return {
        "checked_count": len(checked),
        "checked_links": checked,
        "broken_links": broken_links,
        "redirects": redirects,
        "not_checked_count": max(0, len(links) - len(checked))
    }


def analyze_technical_seo(crawl_result, website_url):
    pages = crawl_result.get("pages", [])

    issues = []
    recommendations = []

    scores = {
        "canonical": 100,
        "robots": 100,
        "sitemap": 100,
        "links": 100,
        "redirects": 100,
        "https": 100,
        "images": 100,
        "metadata": 100,
        "crawlability": 100
    }

    if not pages:
        return {
            "url": website_url,
            "technical_seo_score": 0,
            "pages_analyzed": 0,
            "category_scores": {key: 0 for key in scores},
            "issues": ["No website pages could be crawled"],
            "recommendations": [
                "Check website availability and allow search engine crawlers"
            ]
        }

    # Canonical URL analysis
    for page in pages:
        canonical = page.get("canonical_url")
        page_url = page.get("url", website_url)

        if not canonical:
            scores["canonical"] -= 20
            issues.append(f"Missing canonical URL: {page_url}")
            recommendations.append(
                "Add a canonical link tag to identify the preferred page URL"
            )
        else:
            canonical_url = urljoin(page_url, canonical)

            if urlsplit(canonical_url).hostname != urlsplit(page_url).hostname:
                scores["canonical"] -= 20
                issues.append(f"Canonical URL points to another domain: {page_url}")
                recommendations.append(
                    "Review canonical URLs to ensure they point to the correct domain"
                )

    # Robots meta analysis
    for page in pages:
        robots = (page.get("robots_meta") or "").lower()
        page_url = page.get("url", website_url)

        if "noindex" in robots:
            scores["robots"] -= 20
            issues.append(f"Page blocks search indexing: {page_url}")
            recommendations.append(
                "Review the noindex directive on pages that should appear in search results"
            )

    # robots.txt and sitemap analysis
    site_files = check_robots_and_sitemap(website_url)

    if not site_files["robots_found"]:
        scores["robots"] -= 30
        issues.extend(site_files["issues"][:1])
        recommendations.append(
            "Create a valid robots.txt file and review crawler access rules"
        )

    if not site_files["sitemap_found"]:
        scores["sitemap"] -= 50
        issues.append("XML sitemap was not found or could not be validated")
        recommendations.append(
            "Create and submit a valid XML sitemap"
        )

    # Internal links and redirects
    link_report = check_internal_links(pages)

    if link_report["broken_links"]:
        scores["links"] -= min(
            100, len(link_report["broken_links"]) * 20
        )
        issues.append(
            f"Found {len(link_report['broken_links'])} broken internal links"
        )
        recommendations.append(
            "Fix broken internal links or redirect them to relevant pages"
        )

    if link_report["redirects"]:
        scores["redirects"] -= min(
            100, len(link_report["redirects"]) * 15
        )
        issues.append(
            f"Found {len(link_report['redirects'])} redirected internal links"
        )
        recommendations.append(
            "Update internal links to point directly to their final destinations"
        )

    # HTTPS analysis
    if urlsplit(website_url).scheme.lower() != "https":
        scores["https"] = 0
        issues.append("Website is using HTTP instead of HTTPS")
        recommendations.append(
            "Secure the website with HTTPS and a valid SSL certificate"
        )

    # Image optimization
    image_count = 0
    missing_alt = 0

    for page in pages:
        for image in page.get("images", []):
            image_count += 1

            if not (image.get("alt") or "").strip():
                missing_alt += 1

    if missing_alt:
        scores["images"] -= min(100, missing_alt * 15)
        issues.append(
            f"{missing_alt} of {image_count} images have missing ALT text"
        )
        recommendations.append(
            "Add meaningful descriptive ALT text to website images"
        )

    # Duplicate titles and descriptions
    titles = [
        page.get("title", "").strip().lower()
        for page in pages if page.get("title")
    ]

    descriptions = [
        page.get("meta_description", "").strip().lower()
        for page in pages if page.get("meta_description")
    ]

    duplicate_titles = len(titles) - len(set(titles))
    duplicate_descriptions = len(descriptions) - len(set(descriptions))

    if duplicate_titles:
        scores["metadata"] -= min(100, duplicate_titles * 25)
        issues.append(f"Found {duplicate_titles} duplicate page titles")
        recommendations.append(
            "Write unique and descriptive titles for every important page"
        )

    if duplicate_descriptions:
        scores["metadata"] -= min(100, duplicate_descriptions * 25)
        issues.append(
            f"Found {duplicate_descriptions} duplicate meta descriptions"
        )
        recommendations.append(
            "Write unique meta descriptions for important pages"
        )

    # Crawlability
    if crawl_result.get("total_pages", 0) == 0:
        scores["crawlability"] = 0
        issues.append("No pages were successfully crawled")
        recommendations.append(
            "Investigate crawl errors and website accessibility"
        )

    scores = {
        key: max(0, min(100, value))
        for key, value in scores.items()
    }

    overall_score = round(sum(scores.values()) / len(scores))

    return {
        "url": website_url,
        "technical_seo_score": overall_score,
        "pages_analyzed": len(pages),
        "category_scores": scores,
        "site_files": site_files,
        "link_analysis": link_report,
        "image_analysis": {
            "total_images": image_count,
            "missing_alt_text": missing_alt
        },
        "metadata_analysis": {
            "duplicate_titles": duplicate_titles,
            "duplicate_descriptions": duplicate_descriptions
        },
        "issues": list(dict.fromkeys(issues)),
        "recommendations": list(dict.fromkeys(recommendations))
    }


