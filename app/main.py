from app.crawler.site_crawler import crawl_website
from app.crawler.fetcher import fetch_page
from app.crawler.sitemap import discover_sitemap
from app.analyzer.seo_analyzer import analyze_seo
from app.analyzer.aeo_analyzer import analyze_aeo
from app.analyzer.technical_seo_analyzer import analyze_technical_seo
import httpx

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import engine, SessionLocal
from app.models.audit import Audit

from io import BytesIO
from xml.sax.saxutils import escape

from fastapi import Body
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether
)

from app.analyzer.geo_analyzer import (
    analyze_business_identity,
    analyze_contact_location,
    analyze_schema_markup,
    analyze_trust_signals,
    calculate_geo_score
)
app = FastAPI(
    title="TruckSEO Intelligence",
    description="AI-powered SEO, AEO and GEO website auditor",
    version="1.0.0"
)


# Frontend dashboard
STATIC_DIR = Path(__file__).parent / "static"

app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static"
)

@app.get("/dashboard", include_in_schema=False)
def dashboard():
    return FileResponse(STATIC_DIR / "index.html")


# Database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Request model
class AuditCreate(BaseModel):
    website_url: str


# Response model
class AuditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    website_url: str
    status: str
    created_at: datetime


@app.get("/")
def home():
    return {
        "message": "TruckSEO Intelligence API is running",
        "status": "success"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


# Check database connection
@app.get("/db-health")
def database_health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"database": "connected"}
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed"
        )


# Create a new audit
@app.post("/audits", response_model=AuditResponse)
def create_audit(data: AuditCreate, db: Session = Depends(get_db)):
    audit = Audit(website_url=data.website_url)

    db.add(audit)
    db.commit()
    db.refresh(audit)

    return audit


# Get all audits
@app.get("/audits", response_model=list[AuditResponse])
def get_audits(db: Session = Depends(get_db)):
    return db.query(Audit).order_by(Audit.id.desc()).all()


# Crawl a single webpage
@app.post("/crawl")
def crawl_single_page(data: AuditCreate):
    try:
        return fetch_page(data.website_url)

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except (httpx.HTTPError, OSError, RuntimeError) as error:
        raise HTTPException(status_code=502, detail=str(error))


# Crawl an entire website
@app.post("/crawl-site")
def crawl_entire_site(data: AuditCreate):
    try:
        return crawl_website(data.website_url, max_pages=20)

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except Exception as error:
        raise HTTPException(status_code=502, detail=str(error))


# Discover sitemap URLs
@app.post("/discover-sitemap")
def sitemap_discovery(data: AuditCreate):
    try:
        urls = discover_sitemap(data.website_url)

        return {
            "website_url": data.website_url,
            "total_urls": len(urls),
            "sitemap_urls": urls
        }

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except Exception as error:
        raise HTTPException(status_code=502, detail=str(error))


# Analyze SEO of a single webpage
@app.post("/analyze-seo")
def analyze_website_seo(data: AuditCreate):
    try:
        page_data = fetch_page(data.website_url)

        seo_report = analyze_seo(page_data)

        return seo_report

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except (httpx.HTTPError, OSError, RuntimeError) as error:
        raise HTTPException(status_code=502, detail=str(error))



# Analyze AEO of a single webpage
@app.post("/analyze-aeo")
def analyze_website_aeo(data: AuditCreate):
    try:
        page_data = fetch_page(data.website_url)

        aeo_report = analyze_aeo(page_data)

        return aeo_report

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except (httpx.HTTPError, OSError, RuntimeError) as error:
        raise HTTPException(status_code=502, detail=str(error))


# Analyze GEO of a single webpage
@app.post("/analyze-geo")
def analyze_website_geo(data: AuditCreate):
    try:
        page_data = fetch_page(data.website_url)

        identity_report = analyze_business_identity(page_data)
        contact_report = analyze_contact_location(page_data)
        schema_report = analyze_schema_markup(page_data)
        trust_report = analyze_trust_signals(page_data)

        geo_score = calculate_geo_score(
            identity_report,
            contact_report,
            schema_report,
            trust_report
        )

        return {
            "url": data.website_url,
            "geo_score": geo_score["geo_score"],
            "category_scores": geo_score["category_scores"],
            "business_identity": identity_report,
            "contact_location": contact_report,
            "schema_markup": schema_report,
            "trust_signals": trust_report,
            "issues": geo_score["issues"],
            "recommendations": geo_score["recommendations"]
        }

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except (httpx.HTTPError, OSError, RuntimeError) as error:
        raise HTTPException(status_code=502, detail=str(error))


# Analyze technical SEO across a website
@app.post("/analyze-technical-seo")
def analyze_website_technical_seo(data: AuditCreate):
    try:
        crawl_result = crawl_website(data.website_url, max_pages=20)

        return analyze_technical_seo(
            crawl_result,
            data.website_url
        )

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except (httpx.HTTPError, OSError, RuntimeError) as error:
        raise HTTPException(status_code=502, detail=str(error))


@app.post("/download-report", include_in_schema=False)
def download_report(report: dict = Body(...)):
    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#17365D"),
        spaceAfter=12
    )

    story = []

    website_url = escape(str(report.get("website_url", "Unknown")))
    audit_date = datetime.now().strftime("%d %B %Y, %I:%M %p")

    story.append(Paragraph("TruckSEO Intelligence", title_style))
    story.append(Paragraph("Website Audit Report", styles["Heading2"]))
    story.append(Paragraph(f"Website: {website_url}", styles["Normal"]))
    story.append(Paragraph(f"Audit Date: {audit_date}", styles["Normal"]))
    story.append(Spacer(1, 15))

    results = report.get("results", {})

    score_keys = {
        "SEO": "seo_score",
        "AEO": "aeo_score",
        "GEO": "geo_score",
        "Technical SEO": "technical_seo_score"
    }

    score_data = [["Category", "Score"]]

    for category, key in score_keys.items():
        result = results.get(category, {})
        score = result.get(key, "N/A")
        score_data.append([category, f"{score}/100" if isinstance(score, (int, float)) else "N/A"])

    score_table = Table(score_data, colWidths=[80 * mm, 55 * mm])
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))

    story.append(Paragraph("Performance Scores", styles["Heading2"]))
    story.append(score_table)
    story.append(Spacer(1, 15))

    for category, result in results.items():
        story.append(Paragraph(escape(str(category)), styles["Heading2"]))

        issues = result.get("issues", [])
        recommendations = result.get("recommendations", [])

        story.append(Paragraph("Issues", styles["Heading3"]))

        for issue in issues:
            story.append(Paragraph(
                f"&bull; {escape(str(issue))}",
                styles["Normal"]
            ))
            story.append(Spacer(1, 4))

        story.append(Paragraph("Recommendations", styles["Heading3"]))

        for recommendation in recommendations:
            story.append(Paragraph(
                f"&bull; {escape(str(recommendation))}",
                styles["Normal"]
            ))
            story.append(Spacer(1, 4))

        story.append(Spacer(1, 12))

    document.build(story)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="truckseo-audit-report.pdf"'
        }
    )