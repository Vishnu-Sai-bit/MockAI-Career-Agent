"""
Company Discovery & Multi-Platform Harvester Service:
Enables broad-spectrum ingestion across all platforms (Greenhouse, Lever, Ashby,
Workday, SmartRecruiters, Workable, Recruitee, and Open Feeds).
Solves the 'only scrape some companies' limitation by:
1. Maintaining an extensive multi-platform company directory (100+ employers).
2. Auto-detecting new company tenants from incoming job URLs.
3. Providing on-demand dynamic company ingestion for any employer the user requests.
"""
import re
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs

from extensions import db
from models.job_source import JobSource
from models.job import Job
from utils.logging_config import logger

# Multi-Platform Directory of Known Verified Company Tenants
PLATFORM_COMPANY_CATALOG = {
    "greenhouse": [
        ("stripe", "Stripe"), ("gitlab", "GitLab"), ("figma", "Figma"), ("reddit", "Reddit"),
        ("discord", "Discord"), ("databricks", "Databricks"), ("coinbase", "Coinbase"),
        ("cloudflare", "Cloudflare"), ("inmobi", "InMobi"), ("twilio", "Twilio"),
        ("robinhood", "Robinhood"), ("elastic", "Elastic"), ("pinterest", "Pinterest"),
        ("instacart", "Instacart"), ("anthropic", "Anthropic"), ("wikimedia", "Wikimedia Foundation"),
        ("wise", "Wise"), ("brex", "Brex"), ("groww", "Groww"), ("uber", "Uber"),
        ("snap", "Snapchat"), ("mongodb", "MongoDB"), ("confluent", "Confluent"),
        ("doordash", "DoorDash"), ("notion", "Notion"), ("canva", "Canva"),
        ("scaleai", "Scale AI"), ("plaid", "Plaid"), ("affirm", "Affirm"),
        ("asana", "Asana"), ("hashicorp", "HashiCorp"), ("datadog", "Datadog"),
        ("pagerduty", "PagerDuty"), ("box", "Box"), ("coursera", "Coursera"),
        ("samsara", "Samsara"), ("fastly", "Fastly"), ("lyft", "Lyft"),
        ("duolingo", "Duolingo"), ("klarna", "Klarna"), ("roblox", "Roblox"),
        ("zapier", "Zapier"), ("airtable", "Airtable"), ("gusto", "Gusto"),
        ("toast", "Toast"), ("miro", "Miro"), ("webflow", "Webflow"),
        ("chime", "Chime"), ("airbnb", "Airbnb")
    ],
    "lever": [
        ("spotify", "Spotify"), ("palantir", "Palantir"), ("netflix", "Netflix"),
        ("atlassian", "Atlassian"), ("postman", "Postman"), ("yelp", "Yelp"),
        ("eventbrite", "Eventbrite"), ("udemy", "Udemy"), ("benchling", "Benchling"),
        ("coupa", "Coupa"), ("twitch", "Twitch"), ("quora", "Quora"),
        ("kustomer", "Kustomer"), ("ironclad", "Ironclad")
    ],
    "ashby": [
        ("openai", "OpenAI"), ("linear", "Linear"), ("supabase", "Supabase"),
        ("ramp", "Ramp"), ("perplexity", "Perplexity AI"), ("vercel", "Vercel"),
        ("replit", "Replit"), ("cursor", "Cursor"), ("deel", "Deel"),
        ("posthog", "PostHog"), ("sentry", "Sentry"), ("cohere", "Cohere"),
        ("mistral", "Mistral AI"), ("resend", "Resend"), ("vanta", "Vanta"),
        ("modal", "Modal Labs"), ("elevenlabs", "ElevenLabs")
    ],
    "workday": [
        ("nvidia", "NVIDIA"), ("adobe", "Adobe"), ("autodesk", "Autodesk"),
        ("target", "Target"), ("salesforce", "Salesforce"), ("cisco", "Cisco"),
        ("intel", "Intel"), ("mastercard", "Mastercard"), ("walmart", "Walmart"),
        ("nike", "Nike"), ("hp", "HP"), ("dell", "Dell"), ("accenture", "Accenture")
    ],
    "smartrecruiters": [
        ("averydennison", "Avery Dennison"), ("visa", "Visa"), ("bosch", "Bosch"),
        ("square", "Block (Square)"), ("ikea", "IKEA"), ("linkedin", "LinkedIn")
    ],
    "workable": [
        ("skroutz", "Skroutz"), ("deliveroo", "Deliveroo"), ("bolt", "Bolt"),
        ("transfergo", "TransferGo"), ("taxfix", "Taxfix")
    ],
    "recruitee": [
        ("bunq", "bunq"), ("mollie", "Mollie"), ("messagebird", "MessageBird")
    ]
}

class CompanyDiscoveryService:
    def get_catalog_stats(self) -> Dict[str, Any]:
        """Returns statistics on all cataloged companies across platforms including Workday, Greenhouse, and BambooHR directories."""
        breakdown = {plat: len(comps) for plat, comps in PLATFORM_COMPANY_CATALOG.items()}
        try:
            from services.workday_directory_service import workday_directory
            w_stats = workday_directory.get_stats()
            breakdown["workday_directory"] = w_stats["total_companies"]
        except Exception:
            w_stats = {"total_companies": 0}

        try:
            from services.greenhouse_directory_service import greenhouse_directory
            gh_stats = greenhouse_directory.get_stats()
            breakdown["greenhouse_directory"] = gh_stats["total_companies"]
        except Exception:
            gh_stats = {"total_companies": 0}

        try:
            from services.bamboohr_directory_service import bamboohr_directory
            bb_stats = bamboohr_directory.get_stats()
            breakdown["bamboohr_directory"] = bb_stats["total_companies"]
        except Exception:
            bb_stats = {"total_companies": 0}

        catalog_base = sum(len(comps) for plat, comps in PLATFORM_COMPANY_CATALOG.items() if plat not in ("workday", "greenhouse"))
        total = catalog_base + w_stats["total_companies"] + gh_stats["total_companies"] + bb_stats["total_companies"]

        return {
            "total_supported_employers": total,
            "platform_breakdown": breakdown
        }

    def detect_platform_from_url(self, url: str) -> Optional[Tuple[str, str]]:
        """
        Extracts (platform, company_key) from any job or career page URL.
        Example: https://boards.greenhouse.io/stripe/jobs/123 -> ('greenhouse', 'stripe')
        """
        if not url:
            return None
        parsed = urlparse(url.lower())
        host = parsed.netloc
        path = parsed.path.strip("/")
        qs = parse_qs(parsed.query)

        # Greenhouse
        if "greenhouse.io" in host:
            if "for" in qs and qs["for"]:
                return ("greenhouse", qs["for"][0].strip())
            parts = [p for p in path.split("/") if p]
            if len(parts) >= 1 and parts[0] != "embed":
                return ("greenhouse", parts[0])
            elif len(parts) >= 2 and parts[0] == "embed":
                return ("greenhouse", parts[1])

        # Lever
        if "lever.co" in host:
            parts = [p for p in path.split("/") if p]
            if len(parts) >= 1:
                return ("lever", parts[0])

        # Ashby
        if "ashbyhq.com" in host:
            parts = [p for p in path.split("/") if p]
            if len(parts) >= 1:
                return ("ashby", parts[0])

        # Workday
        if "myworkdayjobs.com" in host:
            sub = host.split(".")[0]
            return ("workday", sub)

        # SmartRecruiters
        if "smartrecruiters.com" in host:
            parts = [p for p in path.split("/") if p]
            if len(parts) >= 1:
                return ("smartrecruiters", parts[0])

        # Workable
        if "workable.com" in host:
            parts = [p for p in path.split("/") if p]
            if len(parts) >= 1:
                return ("workable", parts[0])

        # Recruitee
        if "recruitee.com" in host:
            sub = host.split(".")[0]
            return ("recruitee", sub)

        # BambooHR
        if "bamboohr.com" in host:
            sub = host.split(".")[0]
            return ("bamboohr", sub)

        return None

    def register_all_catalog_sources(self) -> int:
        """
        Ensures all 100+ cataloged employers across all platforms
        are registered in job_sources table.
        """
        added = 0
        for platform, companies in PLATFORM_COMPANY_CATALOG.items():
            for c_key, c_name in companies:
                existing = JobSource.query.filter_by(platform=platform, company_key=c_key).first()
                if not existing:
                    s = JobSource(
                        platform=platform,
                        company_key=c_key,
                        name=f"{c_name} ({platform.title()})",
                        is_active=True
                    )
                    db.session.add(s)
                    added += 1
        if added > 0:
            db.session.commit()
        return added
