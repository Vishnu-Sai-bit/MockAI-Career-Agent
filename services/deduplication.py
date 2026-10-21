"""
High-Performance Job Deduplication & ATS Link Prioritization Engine
Generates composite hash of normalized_company + normalized_title + location_cluster.
Filters out identical cross-postings and preserves direct employer ATS links.
"""

import re
import hashlib
from typing import Dict, Any, List, Optional
from services.job_deduplicator import JobDeduplicator

DIRECT_ATS_PLATFORMS = {
    "greenhouse", "lever", "ashby", "workday", "smartrecruiters",
    "workable", "recruitee", "bamboohr", "personio"
}

class JobDeduplicationEngine(JobDeduplicator):
    """
    Composite Hash Deduplication & ATS Link Hierarchy Prioritizer.
    """

    @staticmethod
    def normalize_string(text: str) -> str:
        if not text:
            return ""
        # Lowercase, remove punctuation and extra spaces
        cleaned = re.sub(r"[^\w\s]", "", text.lower())
        return " ".join(cleaned.split())

    @classmethod
    def get_location_cluster(cls, location: str) -> str:
        if not location:
            return "unknown"
        norm = cls.normalize_string(location)
        if any(w in norm for w in ["remote", "worldwide", "anywhere", "telecommute", "work from home"]):
            return "remote"
        # Major metro clusters
        clusters = {
            "bangalore": ["bangalore", "bengaluru"],
            "hyderabad": ["hyderabad"],
            "pune": ["pune"],
            "mumbai": ["mumbai", "bombay"],
            "delhi": ["delhi", "noida", "gurgaon", "gurugram", "ncr"],
            "chennai": ["chennai", "madras"],
            "san francisco": ["san francisco", "sf", "bay area", "oakland", "san jose"],
            "new york": ["new york", "nyc", "manhattan", "brooklyn"],
            "london": ["london", "uk"]
        }
        for cluster, aliases in clusters.items():
            if any(a in norm for a in aliases):
                return cluster
        return norm.split()[0] if norm.split() else "unknown"

    @classmethod
    def generate_composite_hash(cls, company: str, title: str, location: str) -> str:
        """
        Generates composite hash: normalized_company + normalized_title + location_cluster.
        """
        norm_company = cls.normalize_string(company)
        norm_title = cls.normalize_string(title)
        loc_cluster = cls.get_location_cluster(location)
        key = f"{norm_company}:{norm_title}:{loc_cluster}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    @classmethod
    def prioritize_direct_ats(cls, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Given a list of job dicts, deduplicates by composite hash and prefers
        direct ATS platforms (Greenhouse, Lever, Ashby, Workday, etc.) over aggregators.
        """
        by_hash: Dict[str, Dict[str, Any]] = {}
        for r in records:
            c_hash = cls.generate_composite_hash(
                r.get("company", ""),
                r.get("title", ""),
                r.get("location", "")
            )
            r["composite_dedup_hash"] = c_hash
            if c_hash not in by_hash:
                by_hash[c_hash] = r
            else:
                existing = by_hash[c_hash]
                # If current record is direct ATS and existing is not, replace it
                is_curr_ats = r.get("source_platform", "").lower() in DIRECT_ATS_PLATFORMS
                is_exist_ats = existing.get("source_platform", "").lower() in DIRECT_ATS_PLATFORMS
                if is_curr_ats and not is_exist_ats:
                    by_hash[c_hash] = r

        return list(by_hash.values())

# Export both class names for seamless compatibility
JobDeduplicator = JobDeduplicationEngine
