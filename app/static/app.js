
const analyzeBtn = document.getElementById("analyzeBtn");
const websiteInput = document.getElementById("websiteUrl");
const statusMessage = document.getElementById("statusMessage");
const resultsSection = document.getElementById("results");

// Store the latest audit for PDF generation
let latestAudit = null;

const endpoints = [
    { name: "SEO", url: "/analyze-seo", score: "seo_score" },
    { name: "AEO", url: "/analyze-aeo", score: "aeo_score" },
    { name: "GEO", url: "/analyze-geo", score: "geo_score" },
    {
        name: "Technical SEO",
        url: "/analyze-technical-seo",
        score: "technical_seo_score"
    }
];

async function runAnalyzer(endpoint, websiteUrl) {
    const response = await fetch(endpoint.url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            website_url: websiteUrl
        })
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.detail || "Analysis failed");
    }

    return data;
}

function showScore(elementId, score) {
    const element = document.getElementById(elementId);

    if (!element) return;

    if (typeof score === "number") {
        element.textContent = `${score}/100`;
    } else {
        element.textContent = "N/A";
    }
}

function createList(items) {
    const list = document.createElement("ul");

    if (!items || items.length === 0) {
        const item = document.createElement("li");
        item.textContent = "None found";
        list.appendChild(item);
        return list;
    }

    items.forEach(value => {
        const item = document.createElement("li");
        item.textContent = value;
        list.appendChild(item);
    });

    return list;
}

function createFindingCard(name, data) {
    const card = document.createElement("div");
    card.className = "finding-card";

    const heading = document.createElement("h3");
    heading.textContent = name;
    card.appendChild(heading);

    if (name === "Technical SEO") {
        const pages = document.createElement("p");
        pages.textContent =
            `Pages analyzed: ${data.pages_analyzed ?? "N/A"}`;
        card.appendChild(pages);

        if (data.category_scores) {
            const categoryTitle = document.createElement("h4");
            categoryTitle.textContent = "Category Scores";
            card.appendChild(categoryTitle);

            const categories = document.createElement("ul");

            Object.entries(data.category_scores).forEach(
                ([category, score]) => {
                    const item = document.createElement("li");
                    item.textContent =
                        `${category.replaceAll("_", " ")}: ${score}/100`;
                    categories.appendChild(item);
                }
            );

            card.appendChild(categories);
        }
    }

    const issuesTitle = document.createElement("h4");
    issuesTitle.className = "issue-title";
    issuesTitle.textContent = "Issues";
    card.appendChild(issuesTitle);

    card.appendChild(createList(data.issues));

    if (Array.isArray(data.passed_checks)) {
        const passedTitle = document.createElement("h4");
        passedTitle.className = "passed-title";
        passedTitle.textContent = "Passed Checks";
        card.appendChild(passedTitle);

        card.appendChild(createList(data.passed_checks));
    }

    return card;
}

function displayResults(results, websiteUrl) {

    // STEP 1: Save latest audit for PDF download
    latestAudit = {
        website_url: websiteUrl,
        results: results
    };

    resultsSection.classList.remove("hidden");

    document.getElementById("auditedUrl").textContent = websiteUrl;

    const scoreIds = {
        "SEO": "seoScore",
        "AEO": "aeoScore",
        "GEO": "geoScore",
        "Technical SEO": "technicalScore"
    };

    const findingsContainer = document.getElementById("findings");

    const recommendationsContainer =
        document.getElementById("recommendations");

    findingsContainer.replaceChildren();
    recommendationsContainer.replaceChildren();

    const allRecommendations = [];

    endpoints.forEach(endpoint => {

        const result = results[endpoint.name];

        if (!result) {
            showScore(scoreIds[endpoint.name], null);
            return;
        }

        showScore(
            scoreIds[endpoint.name],
            result[endpoint.score]
        );

        const card = createFindingCard(endpoint.name, result);

        findingsContainer.appendChild(card);

        (result.recommendations || []).forEach(recommendation => {
            allRecommendations.push({
                category: endpoint.name,
                text: recommendation
            });
        });
    });

    if (allRecommendations.length === 0) {
        recommendationsContainer.textContent =
            "No recommendations available.";
        return;
    }

    const list = document.createElement("ul");

    allRecommendations.forEach(recommendation => {
        const item = document.createElement("li");

        item.textContent =
            `${recommendation.category}: ${recommendation.text}`;

        list.appendChild(item);
    });

    recommendationsContainer.appendChild(list);
}


// MAIN ANALYZE BUTTON

analyzeBtn.addEventListener("click", async () => {

    const websiteUrl = websiteInput.value.trim();

    if (!websiteUrl) {
        statusMessage.textContent = "Please enter a website URL.";
        return;
    }

    analyzeBtn.disabled = true;
    analyzeBtn.textContent = "Analyzing...";

    statusMessage.textContent =
        "Running four analyzers. Technical SEO may take longer...";

    resultsSection.classList.add("hidden");

    try {

        const responses = await Promise.allSettled(
            endpoints.map(endpoint =>
                runAnalyzer(endpoint, websiteUrl)
            )
        );

        const results = {};
        const failures = [];

        responses.forEach((response, index) => {

            const name = endpoints[index].name;

            if (response.status === "fulfilled") {
                results[name] = response.value;
            } else {
                failures.push(
                    `${name}: ${response.reason.message}`
                );
            }
        });

        if (Object.keys(results).length === 0) {
            throw new Error(failures.join(" | "));
        }

        displayResults(results, websiteUrl);

        if (failures.length > 0) {
            statusMessage.textContent =
                "Some analyzers failed: " + failures.join(" | ");
        } else {
            statusMessage.textContent =
                "Analysis completed successfully!";
        }

    } catch (error) {

        statusMessage.textContent = "Error: " + error.message;

    } finally {

        analyzeBtn.disabled = false;
        analyzeBtn.textContent = "Analyze Website";
    }
});


// STEP 2: PDF DOWNLOAD BUTTON

const downloadPdfBtn =
    document.getElementById("downloadPdfBtn");

if (downloadPdfBtn) {

    downloadPdfBtn.addEventListener("click", async () => {

        if (!latestAudit) {
            alert("Please analyze a website first.");
            return;
        }

        downloadPdfBtn.disabled = true;
        downloadPdfBtn.textContent = "Generating PDF...";

        try {

            const response = await fetch("/download-report", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(latestAudit)
            });

            if (!response.ok) {

                let message = "Could not generate PDF report.";

                try {
                    const errorData = await response.json();
                    message = errorData.detail || message;
                } catch (_) {
                    // Use default error message.
                }

                throw new Error(message);
            }

            const blob = await response.blob();

            const downloadUrl = URL.createObjectURL(blob);

            const link = document.createElement("a");

            link.href = downloadUrl;
            link.download = "truckseo-audit-report.pdf";

            document.body.appendChild(link);

            link.click();

            link.remove();

            URL.revokeObjectURL(downloadUrl);

            downloadPdfBtn.textContent = "PDF Downloaded!";

        } catch (error) {

            alert(error.message);

            downloadPdfBtn.textContent =
                "Download PDF Report";

        } finally {

            downloadPdfBtn.disabled = false;

            if (
                downloadPdfBtn.textContent === "Generating PDF..."
            ) {
                downloadPdfBtn.textContent =
                    "Download PDF Report";
            }
        }
    });
}
