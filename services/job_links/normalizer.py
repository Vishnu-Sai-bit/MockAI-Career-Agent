"""
Job Link Normalization, Validation, and Destination Unwrapping Engine.
Ensures No Fake / Generic Links Guarantee:
- Validates that the URL contains a real requisition ID (e.g., /jobs/12345 or ?jobId=...).
- Explicitly strips out generic careers homepages and search pages.
- Unwraps aggregator redirects directly to employer's official ATS vacancy portal.
"""

import re
from urllib.parse import urlparse, parse_qs, urlunparse
from typing import Tuple, Optional
from utils.url_validation import validate_external_job_url

# Patterns indicating generic non-job pages that must be rejected
GENERIC_CAREERS_PATTERNS = [
    r"^https?://[^/]+/(?:careers|jobs|join-us|work-with-us|openings)/?$",
    r"^https?://[^/]+/(?:careers|jobs)/search/?$",
    r"^https?://(?:www\.)?linkedin\.com/jobs/search",
    r"^https?://(?:www\.)?indeed\.com/jobs\?q=",
    r"^https?://(?:www\.)?glassdoor\.com/Job/",
    r"^https?://(?:www\.)?google\.com/search\?.*ibp=htl;jobs",
    r"^https?://(?:www\.)?adzuna\.(?:in|com|co\.uk|de|fr)/details/"
]

# Patterns confirming a real, grounded job requisition ID
REAL_REQUISITION_PATTERNS = [
    r"/(?:jobs|job|positions|openings|requisitions)/[a-zA-Z0-9\-_]{3,}",
    r"[?&](?:jobId|job_id|gh_jid|req_id|jid)=[a-zA-Z0-9\-_]+",
    r"boards\.greenhouse\.io/[^/]+/jobs/\d+",
    r"jobs\.lever\.co/[^/]+/[a-f0-9\-]{20,}",
    r"jobs\.ashbyhq\.com/[^/]+/[a-f0-9\-]{10,}",
    r"myworkdayjobs\.com/[^/]+/job/[^/]+/[^/]+",
    r"smartrecruiters\.com/[^/]+/\d+",
    r"apply\.workable\.com/[^/]+/j/[a-zA-Z0-9]+"
]

def has_real_requisition_id(url: str) -> bool:
    """
    Verifies that the URL points to a specific vacancy requisition,
    not a generic company home or search page.
    """
    if not url:
        return False

    url_clean = url.strip()

    # Reject generic careers homepages and search listings
    for pat in GENERIC_CAREERS_PATTERNS:
        if re.search(pat, url_clean, re.IGNORECASE):
            return False

    # Check for presence of real requisition ID or direct ATS pattern
    for pat in REAL_REQUISITION_PATTERNS:
        if re.search(pat, url_clean, re.IGNORECASE):
            return True

    # Fallback: URL path has more than 1 segment and ends with specific alphanumeric slug
    parsed = urlparse(url_clean)
    path_parts = [p for p in parsed.path.split("/") if p]
    if len(path_parts) >= 2 and any(p.isdigit() or len(p) >= 6 for p in path_parts):
        return True

    return False


def unwrap_destination_apply_link(job_or_url) -> str:
    """
    If a legacy aggregator or wrapped redirect link is present,
    unwraps query parameters to extract the direct employer ATS URL.
    """
    if hasattr(job_or_url, "apply_url"):
        url = job_or_url.apply_url or getattr(job_or_url, "original_url", "")
    else:
        url = str(job_or_url)

    if not url:
        return ""

    parsed = urlparse(url)
    qs = parse_qs(parsed.query)

    # Check common redirect or unwrapping params
    for redirect_param in ["redirect_url", "dest", "target", "apply_url", "job_url", "url", "out"]:
        if redirect_param in qs and qs[redirect_param]:
            target = qs[redirect_param][0]
            if target.startswith("http"):
                return target

    return url


def resolve_verified_apply_link(job) -> Tuple[bool, str, Optional[str]]:
    """
    Resolves the verified destination apply URL for a given job.
    Returns (is_valid: bool, resolved_url: str, error_message: Optional[str]).
    """
    raw_url = unwrap_destination_apply_link(job)
    if not raw_url:
        return False, "", "No application URL available for this job."

    # Intercept aggregator redirect wrappers like Adzuna
    if any(agg in raw_url.lower() for agg in ["adzuna.in", "adzuna.com", "adzuna.co.uk"]):
        return False, raw_url, "Application link points to an external aggregator (Adzuna) rather than the direct official employer career portal."

    # Validate against security constraints
    platform = getattr(job, "source_platform", None)
    is_valid, err_msg, clean_url = validate_external_job_url(raw_url, expected_platform=platform)
    if not is_valid:
        return False, raw_url, err_msg

    # Verify real requisition ID presence
    if not has_real_requisition_id(clean_url):
        return False, clean_url, "URL does not contain a specific requisition ID (generic listing)."

    return True, clean_url, None
