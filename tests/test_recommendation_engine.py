import json
from types import SimpleNamespace

import langchain_google_genai
from fastapi.testclient import TestClient

from app.analyzer import recommendation_engine
from app import main as app_main


FINDINGS = [
    {
        "category": "seo",
        "type": "issues",
        "description": "4 images are missing ALT text",
    }
]


def _recommendation(problem="4 images are missing ALT text"):
    return {
        "category": "seo",
        "problem": problem,
        "impact": (
            "Descriptive ALT text improves image accessibility and helps "
            "search engines understand image content."
        ),
        "recommendation": "Add meaningful ALT text to relevant images.",
        "service_opportunity": "Image SEO Optimization",
        "priority": "Medium",
    }


def _patch_gemini(monkeypatch, content):
    class FakeGemini:
        def __init__(self, **kwargs):
            assert kwargs["google_api_key"] == "test-key"

        def invoke(self, prompt):
            assert "4 images are missing ALT text" in prompt
            return SimpleNamespace(content=content)

    monkeypatch.setattr(
        langchain_google_genai,
        "ChatGoogleGenerativeAI",
        FakeGemini,
    )
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("GOOGLE_MODEL", "gemini-2.5-flash")


def test_generate_ai_recommendations_parses_valid_json(monkeypatch):
    _patch_gemini(monkeypatch, json.dumps([_recommendation()]))

    result = recommendation_engine.generate_ai_recommendations(FINDINGS)

    assert result == [_recommendation()]


def test_generate_ai_recommendations_rejects_malformed_json(monkeypatch):
    _patch_gemini(monkeypatch, "not JSON")

    assert recommendation_engine.generate_ai_recommendations(FINDINGS) is None


def test_generate_ai_recommendations_rejects_unmatched_finding(monkeypatch):
    _patch_gemini(
        monkeypatch,
        json.dumps([_recommendation(problem="An invented problem")]),
    )

    assert recommendation_engine.generate_ai_recommendations(FINDINGS) is None


def test_report_keeps_rule_based_fallback(monkeypatch):
    monkeypatch.setattr(
        recommendation_engine,
        "generate_ai_recommendations",
        lambda findings: None,
    )

    report = recommendation_engine.generate_recommendation_report({
        "seo": {"issues": ["4 images are missing ALT text"]}
    })

    assert report["generation_method"] == "Rule-based fallback"
    assert report["recommendation_count"] == 1
    assert report["recommendations"][0]["problem"] == (
        "4 images are missing ALT text"
    )


def test_endpoint_uses_fallback_when_gemini_is_unavailable(monkeypatch):
    class UnavailableGemini:
        def __init__(self, **kwargs):
            pass

        def invoke(self, prompt):
            raise RuntimeError("simulated Gemini outage")

    monkeypatch.setattr(
        langchain_google_genai,
        "ChatGoogleGenerativeAI",
        UnavailableGemini,
    )
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("GOOGLE_MODEL", "gemini-2.5-flash")
    monkeypatch.setattr(app_main, "fetch_page", lambda url: {})
    monkeypatch.setattr(
        app_main,
        "analyze_seo",
        lambda page: {"issues": ["Missing descriptive title"]},
    )
    monkeypatch.setattr(
        app_main,
        "analyze_aeo",
        lambda page: {"issues": [], "recommendations": []},
    )
    monkeypatch.setattr(app_main, "analyze_business_identity", lambda page: {})
    monkeypatch.setattr(app_main, "analyze_contact_location", lambda page: {})
    monkeypatch.setattr(app_main, "analyze_schema_markup", lambda page: {})
    monkeypatch.setattr(app_main, "analyze_trust_signals", lambda page: {})
    monkeypatch.setattr(
        app_main,
        "calculate_geo_score",
        lambda *args: {
            "geo_score": 80,
            "category_scores": {},
            "issues": [],
            "recommendations": [],
        },
    )
    monkeypatch.setattr(
        app_main,
        "crawl_website",
        lambda url, max_pages: {},
    )
    monkeypatch.setattr(
        app_main,
        "analyze_technical_seo",
        lambda *args: {
            "technical_seo_score": 90,
            "issues": [],
            "recommendations": [],
        },
    )

    response = TestClient(app_main.app).post(
        "/generate-recommendations",
        json={"website_url": "https://example.com"},
    )

    assert response.status_code == 200
    report = response.json()["recommendation_report"]
    assert report["generation_method"] == "Rule-based fallback"
    assert report["recommendation_count"] == 1
    assert report["recommendations"][0]["problem"] == (
        "Missing descriptive title"
    )
