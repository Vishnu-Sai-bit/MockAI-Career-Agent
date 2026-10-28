"""
Robust Live Job Availability and Soft-Closure Checker.
Detects HTTP status codes (404, 410, etc.), direct ATS verification (Workday CXS, Greenhouse, Lever),
redirect traps (e.g. ?not_found=true), and in-page closure phrases
("the page you are looking for doesn't exist", "job not found", "no longer available", "position has been closed").
"""
import re
from typing import Tuple, Optional
from urllib.parse import urlparse, parse_qs, urljoin
import requests

CLOSED_PHRASES = (
    "no longer available",
    "job not found",
    "posting has expired",
    "page not found",
    "the page you are looking for doesn't exist",
    "the page you are looking for does not exist",
    "page you are looking for doesn't exist",
    "page you are looking for does not exist",
    "doesn't exist",
    "does not exist",
    "we couldn't find the page",
    "we couldn't find that page",
    "page could not be found",
    "sorry, we can't find that page",
    "sorry, we couldn't find that page",
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
    "document not found",
    "job_posting_anchor_id=",
    "\"errorcode\": \"s21\"",
    "\"errorcode\":\"s21\"",
    "not found: job_posting"
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

def _parse_workday_cxs_endpoint(url: str) -> Optional[str]:
    """
    Constructs internal Workday CXS detail endpoint from a public job URL.
    Workday web pages return HTTP 200 with an empty SPA shell even when a job is 404.
    The CXS API returns true HTTP 404 ("not found: Job_Posting_Anchor_ID=...")
    or HTTP 200 with jobPostingInfo.
    """
    try:
        parsed = urlparse(url)
        host = parsed.netloc
        if not host or "myworkdayjobs.com" not in host.lower():
            return None
        
        parts = host.split(".")
        if len(parts) < 3:
            return None
        tenant = parts[0]
        
        clean_path = parsed.path.strip("/")
        path_segments = [p for p in clean_path.split("/") if p]
        if path_segments and path_segments[-1].lower() == "apply":
            path_segments = path_segments[:-1]
        
        if "job" not in path_segments:
            return None
            
        job_idx = path_segments.index("job")
        prefix = path_segments[:job_idx]
        
        # Filter out locale codes like en-US, fr-FR, es, etc.
        locale_re = re.compile(r"^[a-z]{2}(-[A-Za-z]{2,4})?$", re.I)
        site_parts = [p for p in prefix if not locale_re.match(p)]
        site = site_parts[0] if site_parts else "External"
        
        job_path = "/" + "/".join(path_segments[job_idx:])
        return f"https://{host}/wday/cxs/{tenant}/{site}{job_path}"
    except Exception:
        return None

def _parse_lever_api_endpoint(url: str) -> Optional[str]:
    try:
        parsed = urlparse(url)
        if "jobs.lever.co" not in parsed.netloc.lower():
            return None
        parts = [p for p in parsed.path.strip("/").split("/") if p]
        if len(parts) >= 2:
            company = parts[0]
            job_id = parts[1].split("?")[0].split("#")[0]
            if job_id and job_id.lower() != "apply":
                return f"https://api.lever.co/v0/postings/{company}/{job_id}"
    except Exception:
        pass
    return None

def _parse_greenhouse_api_endpoint(url: str) -> Optional[str]:
    try:
        parsed = urlparse(url)
        if "boards.greenhouse.io" not in parsed.netloc.lower():
            return None
        parts = [p for p in parsed.path.strip("/").split("/") if p]
        if len(parts) >= 3 and parts[1].lower() == "jobs":
            company = parts[0]
            job_id = parts[2].split("?")[0].split("#")[0]
            if job_id and job_id.lower() != "apply":
                return f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs/{job_id}"
    except Exception:
        pass
    return None

def check_url_live(url: str, timeout: int = 6, max_redirects: int = 5) -> Tuple[bool, int, str]:
    """
    Checks if a job URL is live and accessible.
    Supports authoritative ATS endpoint inspection for Workday (CXS API),
    Greenhouse, and Lever, as well as general HTTP status and in-page closure phrases.
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

    # 1. Authoritative ATS Direct API Verification
    # Workday CXS Detail Endpoint
    cxs_url = _parse_workday_cxs_endpoint(url)
    if cxs_url:
        try:
            resp = session.get(cxs_url, headers={"Accept": "application/json"}, timeout=timeout)
            if resp.status_code in (404, 410):
                return False, 404, f"Job posting returned HTTP {resp.status_code} (Expired/Not Found: The page you are looking for doesn't exist)"
            elif resp.status_code == 400 and ("not found" in resp.text.lower() or "errorcode" in resp.text.lower()):
                return False, 404, f"Job posting returned HTTP 404 (Expired/Not Found: The page you are looking for doesn't exist)"
            elif resp.status_code == 200:
                try:
                    data = resp.json()
                    if "errorCode" in data:
                        msg = data.get("message") or "The page you are looking for does not exist"
                        return False, 404, f"Job posting returned HTTP 404 (Expired/Not Found: {msg})"
                    if "jobPostingInfo" in data:
                        return True, 200, "Workday CXS verified live and active"
                except Exception:
                    pass
                return True, 200, "Workday CXS verified live and active"
        except requests.exceptions.RequestException:
            # Fall back to HTML navigation if network error
            pass

    # Greenhouse Direct Job Endpoint
    gh_url = _parse_greenhouse_api_endpoint(url)
    if gh_url:
        try:
            resp = session.get(gh_url, headers={"Accept": "application/json"}, timeout=timeout)
            if resp.status_code in (404, 410):
                return False, 404, f"Job posting returned HTTP {resp.status_code} (Expired/Not Found)"
            elif resp.status_code == 200:
                return True, 200, "Greenhouse API verified live and active"
        except requests.exceptions.RequestException:
            pass

    # Lever Direct Job Endpoint
    lev_url = _parse_lever_api_endpoint(url)
    if lev_url:
        try:
            resp = session.get(lev_url, headers={"Accept": "application/json"}, timeout=timeout)
            if resp.status_code in (404, 410):
                return False, 404, f"Job posting returned HTTP {resp.status_code} (Expired/Not Found)"
            elif resp.status_code == 200:
                return True, 200, "Lever API verified live and active"
        except requests.exceptions.RequestException:
            pass

    # 2. Standard HTTP and In-Page Verification
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
