
from app.analyzer.geo_analyzer import (
    analyze_business_identity,
    analyze_contact_location,
    analyze_schema_markup,
    analyze_trust_signals,
    calculate_geo_score
)


def test_geo_analyzer_complete_website():
    page = {
        "url": "https://example.com",
        "title": "ABC Trucking",
        "meta_description": "Professional trucking services",
        "text": "Contact us at support@example.com. Read our customer testimonials.",
        "headings": {"h1": ["Professional Trucking Services"]},
        "links": [
            {"href": "/privacy-policy"},
            {"href": "/terms"},
            {"href": "/about"}
        ],
        "structured_data": [
            {
                "@type": "Organization",
                "name": "ABC Trucking",
                "description": "Professional trucking services",
                "telephone": "+1234567890",
                "email": "support@example.com",
                "address": {
                    "addressLocality": "Dallas",
                    "addressCountry": "USA"
                }
            },
            {"@type": "WebSite"}
        ]
    }

    identity = analyze_business_identity(page)
    contact = analyze_contact_location(page)
    schema = analyze_schema_markup(page)
    trust = analyze_trust_signals(page)

    result = calculate_geo_score(identity, contact, schema, trust)

    assert identity["issues"] == []
    assert contact["issues"] == []
    assert schema["issues"] == []
    assert trust["issues"] == []
    assert result["geo_score"] == 100


def test_geo_analyzer_missing_information():
    page = {
        "url": "http://example.com",
        "title": "",
        "meta_description": "",
        "text": "",
        "headings": {"h1": []},
        "links": [],
        "structured_data": []
    }

    identity = analyze_business_identity(page)
    contact = analyze_contact_location(page)
    schema = analyze_schema_markup(page)
    trust = analyze_trust_signals(page)

    result = calculate_geo_score(identity, contact, schema, trust)

    assert result["geo_score"] == 0
    assert len(result["issues"]) > 0
