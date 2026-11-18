
import json
import os
import logging

from dotenv import load_dotenv

load_dotenv(override=True)


# Connect detected problems with services the company can offer.
SERVICE_RULES = [
    {
        "keywords": ["title", "meta description", "keyword", "heading", "content"],
        "service": "On-Page SEO Optimization",
        "priority": "High",
    },
    {
        "keywords": ["sitemap", "robots", "canonical", "crawl", "index", "noindex"],
        "service": "Technical SEO Optimization",
        "priority": "High",
    },
    {
        "keywords": ["broken link", "redirect", "https"],
        "service": "Technical Website Optimization",
        "priority": "Medium",
    },
    {
        "keywords": ["alt text", "image"],
        "service": "Image SEO Optimization",
        "priority": "Medium",
    },
    {
        "keywords": ["faq", "question", "answer", "schema", "structured data"],
        "service": "AEO and Schema Optimization",
        "priority": "Medium",
    },
    {
        "keywords": [
            "business identity", "organization", "location", "address",
            "contact", "trust", "local"
        ],
        "service": "Local SEO and GEO Optimization",
        "priority": "High",
    },
    {
        "keywords": ["ai search", "generative", "citation", "llm"],
        "service": "GEO Optimization",
        "priority": "Medium",
    },
]


def collect_findings(reports):
    """Collect existing issues and recommendations from all analyzers."""
    findings = []

    def walk(value, category):
        if isinstance(value, dict):
            for key, item in value.items():
                key_lower = key.lower()

                if key_lower in ("issues", "recommendations"):
                    if isinstance(item, list):
                        for entry in item:
                            if isinstance(entry, str) and entry.strip():
                                findings.append({
                                    "category": category,
                                    "type": key_lower,
                                    "description": entry.strip(),
                                })
                else:
                    walk(item, category)

        elif isinstance(value, list):
            for item in value:
                walk(item, category)

    for category, report in reports.items():
        walk(report, category)

    # Remove exact duplicate findings.
    unique = {}

    for finding in findings:
        key = (
            finding["category"],
            finding["type"],
            finding["description"].lower(),
        )
        unique[key] = finding

    return list(unique.values())


def map_service(description, category):
    """Choose a relevant service using keyword matching."""
    text = f"{description} {category}".lower()

    for rule in SERVICE_RULES:
        if any(word in text for word in rule["keywords"]):
            return rule["service"], rule["priority"]

    return "SEO Website Improvement", "Medium"


def build_rule_based_recommendations(findings):
    """Create recommendations when AI is unavailable."""
    results = []

    for finding in findings:
        description = finding["description"]

        service, priority = map_service(
            description,
            finding["category"],
        )

        if finding["type"] == "recommendations":
            action = description
        else:
            action = f"Review and fix: {description}"

        results.append({
            "category": finding["category"],
            "problem": description,
            "impact": (
                "This may reduce website visibility, search accessibility, "
                "or the quality of the website experience."
            ),
            "recommendation": action,
            "service_opportunity": service,
            "priority": priority,
        })

    return results


def extract_json_array(content):
    """
    Extract a JSON array from Groq's response.

    Handles:
    - Plain JSON arrays
    - Markdown JSON code blocks
    - Extra text before or after JSON
    """

    # Convert LangChain content blocks into text.
    if isinstance(content, list):
        parts = []

        for part in content:
            if isinstance(part, dict):
                parts.append(part.get("text", ""))
            elif isinstance(part, str):
                parts.append(part)
            else:
                parts.append(str(part))

        content = "\n".join(parts)

    if not isinstance(content, str):
        content = str(content)

    content = content.strip()

    if not content:
        raise ValueError("Groq returned an empty response.")

    decoder = json.JSONDecoder()
    last_error = None

    # Try every opening square bracket until a valid JSON array is found.
    for position, character in enumerate(content):
        if character != "[":
            continue

        try:
            result, _ = decoder.raw_decode(content[position:])

            if isinstance(result, list):
                return result

        except json.JSONDecodeError as error:
            last_error = error

    if last_error:
        raise last_error

    raise ValueError("No valid JSON array found in Groq response.")


def generate_ai_recommendations(findings):
    """Generate AI recommendations using Groq."""
    if not findings:
        return None

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        logging.warning("GROQ_API_KEY is not configured.")
        return None

    prompt = f"""
You are an expert SEO consultant for trucking and logistics companies.

Analyze these verified website audit findings:

{json.dumps(findings, ensure_ascii=False)}

Return exactly one recommendation for each finding, in the same order.

Each recommendation must contain these six fields:
- category
- problem
- impact
- recommendation
- service_opportunity
- priority

Rules:
1. Copy category exactly from the supplied finding.
2. Copy description exactly into problem.
3. Give practical and specific recommendations.
4. Explain business impact in simple language.
5. Match the service to the actual problem.
6. Priority must be High, Medium, or Low.
7. Only use supplied findings. Never invent website problems.
8. Do not promise Google rankings.
9. Return a JSON array, not a JSON object.
10. Do not include Markdown or explanatory text.
"""

    try:
        from langchain_groq import ChatGroq

        llm = ChatGroq(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
            api_key=api_key,
            temperature=0,
            timeout=60,
            max_retries=2,
        )

        response = llm.invoke(prompt)

        # Extract JSON even if Groq includes extra text.
        result = extract_json_array(response.content)

        required_fields = (
            "category",
            "problem",
            "impact",
            "recommendation",
            "service_opportunity",
            "priority",
        )

        if len(result) != len(findings):
            logging.warning(
                "Groq returned %s recommendations; expected %s.",
                len(result),
                len(findings),
            )
            return None

        validated = []

        for recommendation, finding in zip(result, findings):

            if not isinstance(recommendation, dict):
                logging.warning("Groq returned a non-object recommendation.")
                return None

            if not all(
                isinstance(recommendation.get(field), str)
                and recommendation[field].strip()
                for field in required_fields
            ):
                logging.warning("Groq returned missing or invalid fields.")
                return None

            if (
                recommendation["category"] != finding["category"]
                or recommendation["problem"] != finding["description"]
            ):
                logging.warning(
                    "Groq returned a mismatched finding."
                )
                return None

            if recommendation["priority"] not in (
                "High", "Medium", "Low"
            ):
                logging.warning("Groq returned an invalid priority.")
                return None

            validated.append({
                field: recommendation[field]
                for field in required_fields
            })

        logging.info(
            "Groq successfully generated %s recommendations.",
            len(validated),
        )

        return validated

    except json.JSONDecodeError as error:
        logging.error(
            "Groq JSON parsing failed at line %s, column %s: %s",
            error.lineno,
            error.colno,
            error.msg,
        )
        return None

    except Exception as error:
        logging.error(
            "Groq recommendation generation failed: %s: %s",
            type(error).__name__,
            str(error)[:500],
        )
        return None


def generate_recommendation_report(reports):
    """Combine findings, service opportunities, and AI output."""
    findings = collect_findings(reports)

    rule_based = build_rule_based_recommendations(findings)
    ai_results = generate_ai_recommendations(findings)

    recommendations = ai_results if ai_results is not None else rule_based

    service_counts = {}

    for item in recommendations:
        service = item.get(
            "service_opportunity",
            "SEO Website Improvement",
        )

        service_counts[service] = service_counts.get(service, 0) + 1

    return {
        "total_findings": len(findings),
        "recommendation_count": len(recommendations),
        "generation_method": (
            "AI-generated" if ai_results is not None
            else "Rule-based fallback"
        ),
        "recommendations": recommendations,
        "service_opportunities": [
            {
                "service": service,
                "finding_count": count,
            }
            for service, count in service_counts.items()
        ],
    }
