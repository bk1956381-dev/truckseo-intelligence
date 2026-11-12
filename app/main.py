
from app.crawler.site_crawler import crawl_website
from app.crawler.fetcher import fetch_page
from app.crawler.sitemap import discover_sitemap
from app.analyzer.seo_analyzer import analyze_seo

import httpx

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

from app.database import engine, SessionLocal
from app.models.audit import Audit


app = FastAPI(
    title="TruckSEO Intelligence",
    description="AI-powered SEO, AEO and GEO website auditor",
    version="1.0.0"
)


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
