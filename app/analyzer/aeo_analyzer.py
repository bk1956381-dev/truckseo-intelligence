
def get_schema_nodes(data):
    """Find all JSON-LD objects, including objects inside @graph."""
    nodes = []

    if isinstance(data, dict):
        nodes.append(data)

        for value in data.values():
            nodes.extend(get_schema_nodes(value))

    elif isinstance(data, list):
        for item in data:
            nodes.extend(get_schema_nodes(item))

    return nodes


def get_schema_types(structured_data):
    """Collect all Schema.org @type values."""
    schema_types = set()

    for item in structured_data:
        for node in get_schema_nodes(item):
            types = node.get("@type", [])

            if isinstance(types, str):
                types = [types]

            for schema_type in types:
                if isinstance(schema_type, str):
                    schema_types.add(schema_type.split("/")[-1])

    return schema_types



def count_faq_answers(structured_data):
    """Count FAQ questions that contain accepted answers."""
    answer_count = 0

    for item in structured_data:
        for node in get_schema_nodes(item):
            types = node.get("@type", [])

            if isinstance(types, str):
                types = [types]

            normalized_types = [
                schema_type.split("/")[-1]
                for schema_type in types
                if isinstance(schema_type, str)
            ]

            if "FAQPage" not in normalized_types:
                continue

            questions = node.get("mainEntity", [])

            if isinstance(questions, dict):
                questions = [questions]

            if not isinstance(questions, list):
                continue

            for question in questions:
                if not isinstance(question, dict):
                    continue

                answer = question.get("acceptedAnswer")

                if isinstance(answer, dict) and answer.get("text"):
                    answer_count += 1

    return answer_count




def analyze_aeo(page: dict) -> dict:
    """Analyze one webpage for Answer Engine Optimization readiness."""

    score = 100
    passed_checks = []
    issues = []
    skipped_checks = []
    recommendations = []

    structured_data = page.get("structured_data", [])

    # 1. Structured data check
    if structured_data:
        passed_checks.append("Structured data exists")
    else:
        score -= 10
        issues.append("Structured data is missing")
        recommendations.append(
            "Add relevant Schema.org structured data."
        )

    schema_types = get_schema_types(structured_data)

    # 2. FAQ schema check
    if "FAQPage" in schema_types:
        passed_checks.append("FAQPage schema exists")

        # 3. FAQ answers check
        answer_count = count_faq_answers(structured_data)

        if answer_count > 0:
            passed_checks.append(
                f"Found {answer_count} FAQ answers"
            )
        else:
            score -= 10
            issues.append("FAQ schema has no accepted answers")
            recommendations.append(
                "Add clear answers to FAQ questions."
            )
    else:
        score -= 15
        issues.append("FAQPage schema is missing")
        recommendations.append(
            "Add FAQPage schema if the website has relevant FAQs."
        )
        skipped_checks.append("FAQ answers check")

    # 4. Question-based headings
    headings = page.get("headings", {})
    all_headings = headings.get("h1", []) + headings.get("h2", [])

    question_words = (
        "what ", "why ", "how ", "when ", "where ",
        "who ", "which ", "can ", "does ", "do ",
        "is ", "are "
    )

    question_headings = [
        heading for heading in all_headings
        if heading.strip().lower().startswith(question_words)
        or "?" in heading
    ]

    if question_headings:
        passed_checks.append(
            f"Found {len(question_headings)} question-based headings"
        )
    else:
        score -= 10
        issues.append("Question-based headings are missing")
        recommendations.append(
            "Use relevant customer questions as content headings."
        )

    # 5. Organization or LocalBusiness schema
    business_types = {"Organization", "LocalBusiness"}

    if schema_types.intersection(business_types):
        passed_checks.append(
            "Organization or LocalBusiness schema exists"
        )
    else:
        score -= 15
        issues.append(
            "Organization or LocalBusiness schema is missing"
        )
        recommendations.append(
            "Add appropriate business or organization structured data."
        )

    # 6. Lists and organized content
    if "lists" not in page:
        skipped_checks.append("Content lists check")
    elif page["lists"]:
        passed_checks.append("Content lists exist")
    else:
        score -= 5
        issues.append("No content lists found")
        recommendations.append(
            "Use lists to organize important information."
        )

    # 7. Direct answers following questions
    if question_headings:
        faq_sections = page.get("faq_sections", [])

        answered_questions = [
            section for section in faq_sections
            if section.get("question", "").strip()
            and section.get("answer", "").strip()
        ]

        if answered_questions:
            passed_checks.append(
                f"Found {len(answered_questions)} question-answer sections"
            )
        else:
            score -= 10
            issues.append("Direct answers to questions are missing")
            recommendations.append(
                "Provide clear answers immediately after question headings."
            )
    else:
        skipped_checks.append("Direct answers check")

    return {
        "url": page.get("url"),
        "aeo_score": max(0, score),
        "passed_checks": passed_checks,
        "issues": issues,
        "skipped_checks": skipped_checks,
        "recommendations": recommendations
    }





