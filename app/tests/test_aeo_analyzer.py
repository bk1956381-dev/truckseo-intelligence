
from app.analyzer.aeo_analyzer import (
    analyze_aeo,
    get_schema_types,
    count_faq_answers
)


def test_good_aeo_page():
    page = {
        "url": "https://example.com",
        "structured_data": [
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": "What is truck dispatching?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "It is a service that manages loads."
                        }
                    }
                ]
            },
            {
                "@type": "Organization",
                "name": "Example Trucking"
            }
        ],
        "headings": {
            "h1": ["What is truck dispatching?"],
            "h2": ["How does truck dispatching work?"]
        },
        "faq_sections": [
            {
                "question": "What is truck dispatching?",
                "answer": "It is a service that manages loads."
            }
        ],
        "lists": [
            {
                "type": "ul",
                "items": ["Load planning", "Delivery coordination"]
            }
        ]
    }

    result = analyze_aeo(page)

    assert result["aeo_score"] == 100
    assert len(result["issues"]) == 0
    assert "FAQPage schema exists" in result["passed_checks"]


def test_missing_aeo_information():
    page = {
        "url": "https://example.com",
        "structured_data": [],
        "headings": {
            "h1": ["Welcome to our website"],
            "h2": ["Our services"]
        }
    }

    result = analyze_aeo(page)

    assert result["aeo_score"] == 50
    assert len(result["issues"]) == 4
    assert "FAQ answers check" in result["skipped_checks"]


def test_schema_types():
    data = [
        {
            "@type": "WebSite"
        },
        {
            "@graph": [
                {
                    "@type": "Organization"
                }
            ]
        }
    ]

    result = get_schema_types(data)

    assert "WebSite" in result
    assert "Organization" in result


def test_count_faq_answers():
    data = [
        {
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": "This is an answer."
                    }
                }
            ]
        }
    ]

    assert count_faq_answers(data) == 1


def test_count_faq_answers_with_schema_url():
    data = [
        {
            "@type": "https://schema.org/FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": "This is an answer."
                    }
                }
            ]
        }
    ]

    assert count_faq_answers(data) == 1
