"""
Company Directory Service:
Aggregates company profiles, verified job volume, locations, ATS platforms,
and provides logo domain resolution and dream company integration.
"""
import re
from typing import Dict, Any, List, Optional, Set
from collections import defaultdict
from urllib.parse import urlparse

from extensions import db
from models.job import Job
from services.dream_company_service import DreamCompanyService

COMMON_LEGAL_SUFFIXES = [
    r"\bgmbh\b", r"\binc\b", r"\bllc\b", r"\bltd\b", r"\bcorp\b",
    r"\bco\b", r"\bag\b", r"\bholding\b", r"\bgroup\b", r"\btechnologies\b"
]

US_STATES = {
    "ca", "tx", "wa", "ny", "ma", "il", "co", "fl", "ga", "va", "dc", "nc",
    "pa", "oh", "nj", "mi", "md", "or", "ut", "az", "mn", "wi", "tn", "mo"
}

INDIA_KEYWORDS = [
    "india", "bengaluru", "bangalore", "hyderabad", "mumbai", "pune",
    "delhi", "noida", "gurgaon", "gurugram", "chennai", "kolkata"
]

MNC_KEYWORDS = {
    "stripe", "databricks", "cloudflare", "gitlab", "coinbase", "elastic", "airbnb", 
    "pinterest", "robinhood", "palantir", "figma", "reddit", "nvidia", "twilio", 
    "spotify", "inmobi", "autodesk", "avery dennison", "wise", "adobe", "servicenow", 
    "uber", "bank of america", "centene", "meta", "dell", "cognizant", "accenture", 
    "openai", "anthropic", "perplexity", "discord", "instacart", "supabase", "linear", 
    "bunq", "wikimedia", "brex", "groww", "google", "microsoft", "amazon", "apple", 
    "salesforce", "cisco", "intel", "sap", "ibm", "samsara", "binance"
}

KNOWN_COMPANY_DOMAINS = {
    "stripe": "stripe.com",
    "gitlab": "gitlab.com",
    "nvidia": "nvidia.com",
    "spotify": "spotify.com",
    "autodesk": "autodesk.com",
    "avery dennison": "averydennison.com",
    "linear": "linear.app",
    "adobe": "adobe.com",
    "bunq": "bunq.com",
    "elevenlabs": "elevenlabs.io",
    "openai": "openai.com",
    "binance": "binance.com",
    "ashby": "ashbyhq.com",
    "hellofresh": "hellofresh.com",
    "canonical": "canonical.com",
    "mozilla": "mozilla.org",
    "clickup": "clickup.com",
    "dropbox": "dropbox.com",
    "fastly": "fastly.com",
    "fivetran": "fivetran.com",
    "grafana labs": "grafana.com",
    "reddit": "reddit.com",
    "servicenow": "servicenow.com",
    "uber": "uber.com",
    "bank of america": "bankofamerica.com",
    "monzo": "monzo.com",
    "samsara": "samsara.com",
    "chainguard": "chainguard.dev",
    "deepgram": "deepgram.com",
    "stackadapt": "stackadapt.com",
    "anthropic": "anthropic.com",
    "perplexity": "perplexity.ai",
    "wikimedia": "wikimedia.org",
    "wise": "wise.com",
    "brex": "brex.com",
    "groww": "groww.in",
    "netflix": "netflix.com",
    "atlassian": "atlassian.com",
    "postman": "postman.com",
    "snapchat": "snap.com",
    "snap": "snap.com",
    "mongodb": "mongodb.com",
    "confluent": "confluent.io",
    "doordash": "doordash.com",
    "notion": "notion.so",
    "canva": "canva.com",
    "vercel": "vercel.com",
    "replit": "replit.com",
    "cursor": "cursor.com",
    "deel": "deel.com",
    "posthog": "posthog.com",
    "sentry": "sentry.io",
    "cohere": "cohere.com",
    "visa": "visa.com",
    "bosch": "bosch.com",
    "block": "block.xyz",
    "deliveroo": "deliveroo.co.uk",
    "bolt": "bolt.eu",
    "hitachi": "hitachi.com",
    "dxc": "dxc.com",
    "iqvia": "iqvia.com",
    "jll": "jll.com",
    "thermo fisher": "thermofisher.com",
    "cisco": "cisco.com",
    "medtronic": "medtronic.com",
    "santander": "santander.com",
    "wells fargo": "wellsfargo.com",
    "ecolab": "ecolab.com",
    "airbus": "airbus.com",
    "dbs bank": "dbs.com",
    "leidos": "leidos.com",
    "thales": "thalesgroup.com",
    "stryker": "stryker.com"
}

def resolve_company_domain(company_name: str, sample_url: str = "") -> str:
    norm_name = company_name.strip().lower()
    for known_k, domain in KNOWN_COMPANY_DOMAINS.items():
        if known_k in norm_name or norm_name in known_k:
            return domain

    # Try extracting domain from job URL if direct ATS
    if sample_url:
        host = urlparse(sample_url).netloc.lower()
        if host and not any(agg in host for agg in ["arbeitnow", "remoteok", "remotive", "adzuna", "jobicy"]):
            # e.g. stripe.com or nvidia.wd5.myworkdayjobs.com -> nvidia.com
            parts = host.split(".")
            if len(parts) >= 2:
                return ".".join(parts[-2:])

    # Clean legal suffixes
    cleaned = norm_name
    for suff in COMMON_LEGAL_SUFFIXES:
        cleaned = re.sub(suff, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[^\w]", "", cleaned).strip()
    return f"{cleaned}.com" if cleaned else "company.com"

class CompanyService:
    def get_companies_directory(
        self,
        search_query: Optional[str] = None,
        filter_type: str = "all",
        sort_by: str = "jobs",
        user_id: Optional[int] = None,
        page: int = 1,
        per_page: int = 24
    ) -> Dict[str, Any]:
        """
        Aggregates active jobs by company and returns a paginated directory
        with metadata, badges, and dream company tracking status.
        """
        active_jobs = Job.query.filter_by(status="active").all()

        # Build dream companies set
        dream_companies: Set[str] = set()
        if user_id:
            dream_companies = DreamCompanyService().get_dream_company_names(user_id)

        # Aggregate jobs by company
        grouped = defaultdict(list)
        for job in active_jobs:
            c = job.company.strip()
            if c:
                grouped[c].append(job)

        company_list = []
        for c_name, jobs in grouped.items():
            locs = set()
            platforms = set()
            has_india = False
            has_us = False
            has_uk = False
            has_germany = False
            has_canada = False
            has_remote = False
            sample_url = ""

            for j in jobs:
                loc = (j.location or "").strip()
                if loc:
                    locs.add(loc)
                c_low = (j.country or "").lower().strip()
                loc_low = f"{loc} {c_low} {j.city or ''}".lower()
                if any(k in loc_low for k in INDIA_KEYWORDS):
                    has_india = True
                if "united states" in loc_low or "usa" in loc_low or c_low in US_STATES or c_low == "us":
                    has_us = True
                if "united kingdom" in loc_low or "uk" in loc_low or "london" in loc_low or c_low == "gb":
                    has_uk = True
                if "germany" in loc_low or "berlin" in loc_low or "munich" in loc_low or c_low == "de":
                    has_germany = True
                if "canada" in loc_low or "toronto" in loc_low or "vancouver" in loc_low or "montreal" in loc_low:
                    has_canada = True
                if "remote" in loc_low or (j.work_mode or "").lower() == "remote":
                    has_remote = True
                if j.source_platform:
                    platforms.add(j.source_platform.title())
                if not sample_url and (j.original_url or j.apply_url):
                    sample_url = j.original_url or j.apply_url

            domain = resolve_company_domain(c_name, sample_url)
            is_dream = c_name.lower().strip() in dream_companies

            # Check if organization qualifies as Multinational Corporation (MNC)
            countries = {j.country.strip().lower() for j in jobs if j.country and j.country.strip()}
            is_mnc = len(countries) >= 2 or len(jobs) >= 15 or any(k in c_name.lower() for k in MNC_KEYWORDS)

            # Top 3 role titles for preview
            sample_titles = [j.title for j in jobs[:3]]

            company_list.append({
                "name": c_name,
                "total_jobs": len(jobs),
                "has_india": has_india,
                "has_us": has_us,
                "has_uk": has_uk,
                "has_germany": has_germany,
                "has_canada": has_canada,
                "has_remote": has_remote,
                "is_mnc": is_mnc,
                "platforms": sorted(list(platforms)),
                "primary_platform": sorted(list(platforms))[0] if platforms else "Direct",
                "top_locations": sorted(list(locs))[:2],
                "sample_titles": sample_titles,
                "domain": domain,
                "logo_url": f"https://www.google.com/s2/favicons?domain={domain}&sz=64",
                "is_dream": is_dream
            })

        # Apply Filters
        if search_query:
            q_clean = search_query.strip().lower()
            company_list = [c for c in company_list if q_clean in c["name"].lower()]

        if filter_type == "mnc":
            company_list = [c for c in company_list if c["is_mnc"]]
        elif filter_type in ("india", "in"):
            company_list = [c for c in company_list if c["has_india"]]
        elif filter_type in ("us", "usa", "united states"):
            company_list = [c for c in company_list if c["has_us"]]
        elif filter_type in ("uk", "gb", "united kingdom"):
            company_list = [c for c in company_list if c["has_uk"]]
        elif filter_type in ("germany", "de"):
            company_list = [c for c in company_list if c["has_germany"]]
        elif filter_type in ("canada", "ca"):
            company_list = [c for c in company_list if c["has_canada"]]
        elif filter_type == "remote":
            company_list = [c for c in company_list if c["has_remote"]]
        elif filter_type == "top":
            company_list = [c for c in company_list if c["total_jobs"] >= 5]
        elif filter_type == "workday":
            company_list = [c for c in company_list if "Workday" in c["platforms"]]
        elif filter_type == "greenhouse":
            company_list = [c for c in company_list if "Greenhouse" in c["platforms"]]
        elif filter_type == "bamboohr":
            company_list = [c for c in company_list if any("bamboo" in p.lower() for p in c["platforms"])]
        elif filter_type == "dream" and user_id:
            company_list = [c for c in company_list if c["is_dream"]]

        # Sorting
        if sort_by == "alpha":
            company_list.sort(key=lambda x: x["name"].lower())
        else:
            # Default: most jobs first, then alpha
            company_list.sort(key=lambda x: (-x["total_jobs"], x["name"].lower()))

        total_matching = len(company_list)
        total_pages = max(1, (total_matching + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))

        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_items = company_list[start_idx:end_idx]

        return {
            "companies": paginated_items,
            "total_companies": total_matching,
            "total_jobs_in_db": len(active_jobs),
            "page": page,
            "pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
            "search_query": search_query or "",
            "filter_type": filter_type,
            "sort_by": sort_by
        }
