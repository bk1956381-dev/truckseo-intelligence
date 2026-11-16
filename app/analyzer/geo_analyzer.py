
def get_business_schema(structured_data):
    """
    Find Organization or LocalBusiness information
    inside website structured data.
    """

    business_types = {
        "Organization",
        "LocalBusiness"
    }

    def search_nodes(data):
        results = []

        for item in data:
            if not isinstance(item, dict):
                continue

            schema_type = item.get("@type", [])

            if isinstance(schema_type, str):
                schema_type = [schema_type]

            normalized_types = [
                str(value).split("/")[-1]
                for value in schema_type
            ]

            if business_types.intersection(normalized_types):
                results.append(item)

            graph = item.get("@graph", [])

            if isinstance(graph, list):
                results.extend(search_nodes(graph))

        return results

    return search_nodes(structured_data or [])


def analyze_business_identity(page):
    """
    Analyze business identity signals for GEO.
    """

    passed_checks = []
    issues = []
    recommendations = []

    structured_data = page.get("structured_data", [])
    business_nodes = get_business_schema(structured_data)

    business_name = None
    business_description = None

    # Extract business name and description
    for node in business_nodes:
        if not business_name and node.get("name"):
            business_name = node.get("name")

        if not business_description and node.get("description"):
            business_description = node.get("description")

    # Check business name
    if business_name:
        passed_checks.append("Business name found in structured data")
    else:
        issues.append("Business name missing from Organization/LocalBusiness schema")
        recommendations.append(
            "Add Organization or LocalBusiness schema with the business name."
        )

    # Check business description
    if business_description:
        passed_checks.append("Business description found in structured data")
    elif page.get("meta_description"):
        passed_checks.append("Business description available through meta description")
        business_description = page.get("meta_description")
    else:
        issues.append("Business description is missing")
        recommendations.append(
            "Add a clear business description to the website and structured data."
        )

    # Check page identity
    title = page.get("title")
    headings = page.get("headings", {})
    h1_headings = headings.get("h1", [])

    if title and h1_headings:
        passed_checks.append("Website title and main heading are available")
    else:
        issues.append("Website identity is unclear because title or H1 is missing")
        recommendations.append(
            "Add a descriptive website title and one clear main heading (H1)."
        )

    return {
        "business_identity": {
            "name": business_name,
            "description": business_description
        },
        "passed_checks": passed_checks,
        "issues": issues,
        "recommendations": recommendations
    }




import re


def analyze_contact_location(page):
    """
    Check whether business contact and location
    information is available.
    """

    passed_checks = []
    issues = []
    recommendations = []

    text = page.get("text", "")
    structured_data = page.get("structured_data", [])

    business_nodes = get_business_schema(structured_data)

    phone = None
    email = None
    address = None

    # Find phone number in structured data
    for node in business_nodes:
        if not phone and node.get("telephone"):
            phone = node.get("telephone")

        # Find email in structured data
        if not email and node.get("email"):
            email = node.get("email")

        # Find business address
        if not address and node.get("address"):
            address = node.get("address")

    # Search visible website text for contact details
    if not phone:
        phone_pattern = r"(?<!\w)(?:\+?\d[\d\s().-]{6,}\d)"
        phone_matches = re.findall(phone_pattern, text)

        for match in phone_matches:
            digits = re.sub(r"\D", "", match)

            if 7 <= len(digits) <= 15:
                phone = match.strip()
                break

    if not email:
        email_pattern = r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}"
        email_match = re.search(email_pattern, text)

        if email_match:
            email = email_match.group(0)

    # Check phone
    if phone:
        passed_checks.append("Business phone number found")
    else:
        issues.append("Business phone number is missing")
        recommendations.append(
            "Display a business phone number on the website."
        )

    # Check email
    if email:
        passed_checks.append("Business email found")
    else:
        issues.append("Business email is missing")
        recommendations.append(
            "Add a business contact email to the website."
        )

    # Extract address details
    address_details = {}

    if isinstance(address, dict):
        address_details = address
    elif isinstance(address, str) and address.strip():
        address_details = {"full_address": address.strip()}

    # Check physical address
    if address_details:
        passed_checks.append("Business address found")
    else:
        issues.append("Business address is missing")
        recommendations.append(
            "Add a complete business address to structured data."
        )

    # Check city and country
    city = address_details.get("addressLocality")
    country = address_details.get("addressCountry")

    if city and country:
        passed_checks.append("Business city and country found")
    else:
        issues.append("Business city or country is missing")
        recommendations.append(
            "Include the business city and country in its address."
        )

    return {
        "contact_location": {
            "phone": phone,
            "email": email,
            "address": address_details,
            "city": city,
            "country": country
        },
        "passed_checks": passed_checks,
        "issues": issues,
        "recommendations": recommendations
    }



def get_all_schema_types(structured_data):
    """
    Collect schema types from JSON-LD,
    including nested @graph objects.
    """

    schema_types = set()

    def scan(data):
        if isinstance(data, list):
            for item in data:
                scan(item)

        elif isinstance(data, dict):
            schema_type = data.get("@type", [])

            if isinstance(schema_type, str):
                schema_type = [schema_type]

            for item in schema_type:
                schema_types.add(str(item).split("/")[-1])

            for key, value in data.items():
                if key == "@graph":
                    scan(value)

    scan(structured_data or [])

    return schema_types


def analyze_schema_markup(page):
    """
    Analyze website structured data for GEO.
    """

    structured_data = page.get("structured_data", [])

    schema_types = get_all_schema_types(structured_data)

    passed_checks = []
    issues = []
    recommendations = []

    # Check whether structured data exists
    if structured_data:
        passed_checks.append("Structured data is present")
    else:
        issues.append("Structured data is missing")
        recommendations.append(
            "Add JSON-LD structured data to the website."
        )

    # Check business schema
    business_types = {"Organization", "LocalBusiness"}

    if schema_types.intersection(business_types):
        passed_checks.append("Business schema is present")
    else:
        issues.append("Organization or LocalBusiness schema is missing")
        recommendations.append(
            "Add Organization or LocalBusiness schema with business details."
        )

    # Check website schema
    website_types = {"WebSite", "WebPage"}

    if schema_types.intersection(website_types):
        passed_checks.append("Website schema is present")
    else:
        issues.append("WebSite or WebPage schema is missing")
        recommendations.append(
            "Add WebSite or WebPage schema to describe the website."
        )

    return {
        "schema_markup": {
            "schema_types": sorted(schema_types),
            "structured_data_count": len(structured_data)
        },
        "passed_checks": passed_checks,
        "issues": issues,
        "recommendations": recommendations
    }


def analyze_trust_signals(page):
    """
    Check basic website trust signals.
    """

    url = page.get("url", "")
    text = page.get("text", "").lower()
    links = page.get("links", [])

    passed_checks = []
    issues = []
    recommendations = []

    # HTTPS check
    if url.startswith("https://"):
        passed_checks.append("Website uses HTTPS")
    else:
        issues.append("Website is not using HTTPS")
        recommendations.append("Secure the website with HTTPS.")

    # Extract link URLs
    link_urls = []

    for link in links:
        if isinstance(link, dict):
            link_urls.append(
                link.get("href", link.get("url", "")).lower()
            )
        elif isinstance(link, str):
            link_urls.append(link.lower())

    # Privacy policy check
    if any("privacy" in link for link in link_urls):
        passed_checks.append("Privacy policy link found")
    else:
        issues.append("Privacy policy link is missing")
        recommendations.append("Add a privacy policy page.")

    # Terms and conditions check
    if any(
        word in link
        for link in link_urls
        for word in ["terms", "conditions"]
    ):
        passed_checks.append("Terms and conditions link found")
    else:
        issues.append("Terms and conditions link is missing")
        recommendations.append("Add a terms and conditions page.")

    # About page check
    if any("about" in link for link in link_urls):
        passed_checks.append("About page link found")
    else:
        issues.append("About page link is missing")
        recommendations.append("Add a clear About Us page.")

    # Reviews/testimonials check
    if any(
        word in text
        for word in ["testimonial", "customer review", "client review"]
    ):
        passed_checks.append("Customer reviews or testimonials found")
    else:
        issues.append("Customer reviews or testimonials are missing")
        recommendations.append(
            "Display genuine customer reviews or testimonials."
        )

    return {
        "trust_signals": {
            "https": url.startswith("https://"),
            "privacy_policy": any("privacy" in link for link in link_urls),
            "terms": any(
                word in link
                for link in link_urls
                for word in ["terms", "conditions"]
            ),
            "about_page": any("about" in link for link in link_urls),
            "reviews": any(
                word in text
                for word in ["testimonial", "customer review", "client review"]
            )
        },
        "passed_checks": passed_checks,
        "issues": issues,
        "recommendations": recommendations
    }




def calculate_geo_score(identity, contact, schema, trust):
    """
    Calculate GEO score out of 100.
    """

    categories = {
        "business_identity": (identity, 30),
        "contact_location": (contact, 25),
        "schema_markup": (schema, 25),
        "trust_signals": (trust, 20)
    }

    category_scores = {}
    total_score = 0
    all_issues = []
    all_recommendations = []

    for category, (result, weight) in categories.items():

        total_checks = (
            len(result["passed_checks"]) +
            len(result["issues"])
        )

        if total_checks:
            score = round(
                len(result["passed_checks"]) / total_checks * weight
            )
        else:
            score = 0

        category_scores[category] = {
            "score": score,
            "max_score": weight
        }

        total_score += score
        all_issues.extend(result["issues"])
        all_recommendations.extend(result["recommendations"])

    return {
        "geo_score": total_score,
        "category_scores": category_scores,
        "issues": all_issues,
        "recommendations": all_recommendations
    }
