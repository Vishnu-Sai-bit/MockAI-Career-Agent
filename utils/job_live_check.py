"""
Robust Live Job Availability and Soft-Closure Checker.
Detects HTTP status codes (404, 410, etc.), redirect traps (e.g. ?not_found=true),
and in-page closure phrases ("job not found", "no longer available", "position has been closed").
"""
from typing import Tuple
from urllib.parse import urlparse, parse_qs
import requests

CLOSED_PHRASES = (
    "no longer available",
    "job not found",
    "posting has expired",
    "page not found",
    "no longer open",
    "position is closed",
    "position has been closed",
    "position has been filled",
    "this job is closed",
    "this job is no longer open",
    "this posting is no longer active",
    "no longer accepting applications",
    "job opening has been closed",
    "we could not find the job you were looking for",
    "job does not exist",
    "this position is no longer available",
    "the job you are looking for is no longer",
    "job posting has been removed",
    "this requisition is no longer available",
    "this role is no longer open",
    "this job has expired",
    "posting is no longer active",
    "job is no longer accepting applications",
    "position is no longer accepting applications",
    "the requisition is closed",
    "this listing has expired",
    "this opportunity has expired",
    "404 - page not found",
    "404 not found",
    "job is unlisted",
    "position you are looking for is no longer open",
    "the job you are trying to view is no longer available",
)

CLOSED_URL_SIGNALS = (
    "not_found=true",
    "job_closed=true",
    "expired=true",
    "status=closed",
    "/not-found",
    "/page-not-found",
    "/job-closed",
    "/404"
)

def check_url_live(url: str, timeout: int = 6, max_redirects: int = 5) -> Tuple[bool, int, str]:
    """
    Checks if a job URL is live and accessible.
    Returns (is_active: bool, http_status: int, details: str).
    """
    if not url:
        return False, 0, "No URL provided"

    # Fast check of initial URL query params and paths
    low_initial = url.lower()
    for sig in CLOSED_URL_SIGNALS:
        if sig in low_initial:
            return False, 404, f"URL signal indicates closed/not found: '{sig}'"

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9"
    })

    current_url = url
    try:
        for _ in range(max_redirects):
            resp = session.get(current_url, timeout=timeout, allow_redirects=False, stream=False)
            
            # Handle redirects
            if resp.status_code in (301, 302, 303, 307, 308):
                loc = resp.headers.get("Location")
                if not loc:
                    break
                if loc.startswith("/"):
                    from urllib.parse import urljoin
                    current_url = urljoin(current_url, loc)
                else:
                    current_url = loc
                
                low_next = current_url.lower()
                for sig in CLOSED_URL_SIGNALS:
                    if sig in low_next:
                        return False, 404, f"Redirected to closed/not found URL: '{sig}'"
                continue

            # Terminal response reached
            final_low = current_url.lower()
            for sig in CLOSED_URL_SIGNALS:
                if sig in final_low:
                    return False, 404, f"Final destination URL indicates closed/not found: '{sig}'"

            if resp.status_code in (404, 410):
                return False, resp.status_code, f"Job posting returned HTTP {resp.status_code} (Expired/Not Found)"

            if resp.status_code == 200:
                body_sample = resp.text[:120000].lower()
                for phrase in CLOSED_PHRASES:
                    if phrase in body_sample:
                        return False, 200, f"Posting content indicates closure: '{phrase}'"
                return True, 200, "Posting verified live and active"

            # 403 or 429: bot management / WAF / rate limit
            # Real users on browsers will be able to view, so do not mark as closed
            if resp.status_code in (403, 429):
                return True, resp.status_code, f"Reachable (bot-protected HTTP {resp.status_code})"

            return True, resp.status_code, f"Returned status {resp.status_code}"

        return True, 200, "Redirect chain completed"
    except requests.exceptions.RequestException as e:
        return False, 0, f"Connection failed: {str(e)}"
