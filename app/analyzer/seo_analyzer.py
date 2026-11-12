
def analyze_seo(page: dict) -> dict:
    """
    Analyze one crawled webpage and return an SEO report.
    """

    score = 100
    passed_checks = []
    issues = []
    skipped_checks = []
    recommendations = []

    # 1. Page title
    title = page.get("title")

    if not title or not title.strip():
        score -= 15
        issues.append("Title is missing")
        recommendations.append(
            "Add a descriptive page title."
        )
    else:
        passed_checks.append("Page title exists")

    # 2. Meta description
    description = page.get("meta_description")

    if not description or not description.strip():
        score -= 15
        issues.append("Meta description is missing")
        recommendations.append(
            "Add a relevant meta description."
        )
    else:
        passed_checks.append("Meta description exists")

    # 3. H1 headings
    headings = page.get("headings", {})
    h1 = headings.get("h1", [])

    if not h1:
        score -= 20
        issues.append("H1 heading is missing")
        recommendations.append(
            "Add one main H1 heading."
        )
    elif len(h1) > 1:
        score -= 25
        issues.append(f"Found {len(h1)} H1 headings")
        recommendations.append(
            "Use one clear primary H1 heading."
        )
    else:
        passed_checks.append("Exactly one H1 heading found")

    # 4. H2 headings
    if "h2" not in headings:
        skipped_checks.append("H2 heading check")
    elif not headings["h2"]:
        score -= 5
        issues.append("H2 headings are missing")
        recommendations.append(
            "Add relevant H2 headings to organize content."
        )
    else:
        passed_checks.append("H2 headings exist")

    # 5. Image ALT attributes
    if "images" not in page:
        skipped_checks.append("Image ALT check")
    else:
        images = page.get("images", [])
        missing_alt = [
            image for image in images
            if not image.get("alt", "").strip()
        ]

        if missing_alt:
            score -= 5
            issues.append(
                f"{len(missing_alt)} images are missing ALT text"
            )
            recommendations.append(
                "Add descriptive ALT text to images."
            )
        else:
            passed_checks.append("Image ALT attributes checked")

    # 6. Internal links
    if "internal_links" not in page:
        skipped_checks.append("Internal links check")
    elif not page["internal_links"]:
        score -= 5
        issues.append("No internal links found")
        recommendations.append(
            "Add relevant internal links between pages."
        )
    else:
        passed_checks.append("Internal links exist")

    return {
        "url": page.get("url"),
        "seo_score": max(0, score),
        "passed_checks": passed_checks,
        "issues": issues,
        "skipped_checks": skipped_checks,
        "recommendations": recommendations
    }
