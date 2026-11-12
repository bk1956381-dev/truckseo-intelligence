
from app.analyzer.seo_analyzer import analyze_seo


def test_good_page():
    page = {
        "url": "https://example.com",
        "title": "Professional Truck Dispatch Services in the USA",
        "meta_description": (
            "Find professional truck dispatch services in the USA. "
            "Get reliable support for your trucking business today."
        ),
        "headings": {
            "h1": ["Professional Truck Dispatch Services"]
        }
    }

    result = analyze_seo(page)

    assert result["seo_score"] == 100
    assert result["issues"] == []


def test_missing_title():
    page = {
        "url": "https://example.com",
        "title": "",
        "meta_description": "A" * 140,
        "headings": {"h1": ["Welcome"]}
    }

    result = analyze_seo(page)

    assert result["seo_score"] == 85
    assert "Title is missing" in result["issues"]


def test_missing_description():
    page = {
        "url": "https://example.com",
        "title": "A" * 40,
        "meta_description": "",
        "headings": {"h1": ["Welcome"]}
    }

    result = analyze_seo(page)

    assert result["seo_score"] == 85
    assert "Meta description is missing" in result["issues"]


def test_multiple_h1():
    page = {
        "url": "https://example.com",
        "title": "A" * 40,
        "meta_description": "B" * 140,
        "headings": {
            "h1": ["First heading", "Second heading"]
        }
    }

    result = analyze_seo(page)

    assert result["seo_score"] == 75
    assert "Found 2 H1 headings" in result["issues"]


def test_missing_h2():
    page = {
        "url": "https://example.com",
        "title": "A" * 40,
        "meta_description": "B" * 140,
        "headings": {
            "h1": ["Welcome"],
            "h2": []
        },
        "internal_links": ["/about"]
    }

    result = analyze_seo(page)

    assert result["seo_score"] == 95
    assert "H2 headings are missing" in result["issues"]


def test_missing_internal_links():
    page = {
        "url": "https://example.com",
        "title": "A" * 40,
        "meta_description": "B" * 140,
        "headings": {
            "h1": ["Welcome"],
            "h2": ["Our Services"]
        },
        "internal_links": []
    }

    result = analyze_seo(page)

    assert result["seo_score"] == 95
    assert "No internal links found" in result["issues"]


def test_missing_image_alt():
    page = {
        "url": "https://example.com",
        "title": "A" * 40,
        "meta_description": "B" * 140,
        "headings": {
            "h1": ["Welcome"],
            "h2": ["Our Services"]
        },
        "internal_links": ["/about"],
        "images": [
            {
                "src": "https://example.com/truck.jpg",
                "alt": ""
            }
        ]
    }

    result = analyze_seo(page)

    assert result["seo_score"] == 95
    assert "1 images are missing ALT text" in result["issues"]
