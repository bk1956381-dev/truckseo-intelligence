from app.analyzer import technical_seo_analyzer as analyzer


class FakeResponse:
    def __init__(self, status_code, text="", content=b"", headers=None):
        self.status_code = status_code
        self.text = text
        self.content = content
        self.headers = headers or {}


def test_technical_seo_complete_website(monkeypatch):
    sitemap = b"""<?xml version="1.0"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url><loc>https://example.com/</loc></url>
    </urlset>"""

    def fake_get(url):
        if url.endswith("/robots.txt"):
            return FakeResponse(
                200,
                text="User-agent: *\nAllow: /\nSitemap: https://example.com/sitemap.xml"
            )
        if url.endswith("/sitemap.xml"):
            return FakeResponse(200, content=sitemap)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(analyzer, "safe_get", fake_get)

    pages = [{
        "url": "https://example.com/",
        "title": "ABC Trucking",
        "meta_description": "Professional trucking services",
        "canonical_url": "https://example.com/",
        "robots_meta": "index, follow",
        "images": [{"src": "truck.jpg", "alt": "ABC trucking fleet"}],
        "internal_links": []
    }]

    result = analyzer.analyze_technical_seo(
        {"total_pages": 1, "pages": pages},
        "https://example.com/"
    )

    assert result["technical_seo_score"] == 100
    assert result["pages_analyzed"] == 1
    assert result["issues"] == []


def test_technical_seo_missing_pages():
    result = analyzer.analyze_technical_seo(
        {"total_pages": 0, "pages": []},
        "https://example.com/"
    )

    assert result["technical_seo_score"] == 0
    assert result["pages_analyzed"] == 0


def test_technical_seo_detects_problems(monkeypatch):
    def fake_get(url):
        return FakeResponse(404)

    monkeypatch.setattr(analyzer, "safe_get", fake_get)

    pages = [
        {
            "url": "http://example.com/",
            "title": "ABC Trucking",
            "meta_description": "Trucking services",
            "canonical_url": None,
            "robots_meta": "noindex",
            "images": [{"src": "truck.jpg", "alt": ""}],
            "internal_links": []
        },
        {
            "url": "http://example.com/about",
            "title": "ABC Trucking",
            "meta_description": "Trucking services",
            "canonical_url": None,
            "robots_meta": "",
            "images": [],
            "internal_links": []
        }
    ]

    result = analyzer.analyze_technical_seo(
        {"total_pages": 2, "pages": pages},
        "http://example.com/"
    )

    assert result["technical_seo_score"] < 100
    assert result["metadata_analysis"]["duplicate_titles"] == 1
    assert result["metadata_analysis"]["duplicate_descriptions"] == 1
    assert result["image_analysis"]["missing_alt_text"] == 1
    assert len(result["issues"]) > 0
