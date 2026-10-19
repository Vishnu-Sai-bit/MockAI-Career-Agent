import json
from typing import Dict, Any, Optional
from services.gemini_service import GeminiService
from utils.logging_config import logger

class SalaryIntelligenceService:
    def __init__(self, gemini_service: Optional[GeminiService] = None):
        self.gemini = gemini_service or GeminiService()

    def estimate_market_salary(self, title: str, location: str, experience_years: float, skills: list) -> Dict[str, Any]:
        """
        Estimates market compensation percentiles for a role based on skills, geography, and tenure.
        """
        prompt = f"""You are a principal compensation consultant and compensation benchmark analyst.
Estimate the competitive market salary percentiles for this role.

ROLE DETAILS:
Title: {title}
Location: {location}
Experience: {experience_years} years
Key Skills: {', '.join(skills[:8])}

Format output as a valid JSON object:
{{
  "currency": "USD / INR / EUR",
  "percentile_25": 95000,
  "median": 125000,
  "percentile_75": 150000,
  "percentile_90": 175000,
  "market_demand_rating": "Very High / High / Moderate",
  "salary_drivers": [
    "Key factor or skill driving compensation premium (e.g. distributed systems, AI)",
    "Geographic or remote market factor"
  ],
  "negotiation_leverage_summary": "1-2 sentence assessment of candidate leverage in this market segment."
}}
"""
        raw_resp = self.gemini.generate_text(prompt, timeout=20)
        if raw_resp:
            parsed = self.gemini._clean_and_parse_json(raw_resp)
            if isinstance(parsed, dict) and "median" in parsed:
                return parsed

        # Deterministic benchmark calculation
        base_usd = 85000.0 + min(experience_years * 12000.0, 100000.0)
        is_india = "india" in location.lower() or "bengaluru" in location.lower() or "hyderabad" in location.lower()
        if is_india:
            curr = "INR"
            base = (base_usd * 0.25) * 85.0  # approximate purchasing power parity
            return {
                "currency": "INR",
                "percentile_25": round(base * 0.85, -4),
                "median": round(base, -4),
                "percentile_75": round(base * 1.25, -4),
                "percentile_90": round(base * 1.50, -4),
                "market_demand_rating": "High",
                "salary_drivers": [f"Specialized experience in {', '.join(skills[:3]) if skills else 'Tech'}", "Fast-growing Indian tech hub premium"],
                "negotiation_leverage_summary": "High demand for proven hands-on technical contributors with clean problem-solving fundamentals."
            }

        return {
            "currency": "USD",
            "percentile_25": round(base_usd * 0.85, -3),
            "median": round(base_usd, -3),
            "percentile_75": round(base_usd * 1.20, -3),
            "percentile_90": round(base_usd * 1.40, -3),
            "market_demand_rating": "High",
            "salary_drivers": [f"Deep proficiency in {', '.join(skills[:3]) if skills else 'core competencies'}", "Competitive global tech market"],
            "negotiation_leverage_summary": "Strong leverage for candidates demonstrating measurable business impact and clean architecture."
        }

    def generate_counter_offer(self, company: str, role: str, current_offer_base: float, target_base: float, justification: str) -> Dict[str, Any]:
        """
        Drafts a professional, gracious counter-offer negotiation email.
        """
        prompt = f"""You are a master executive negotiation coach.
Draft a tactful, highly professional counter-offer email for a candidate negotiating a job offer.

DETAILS:
Company: {company}
Role: {role}
Current Offered Base: {current_offer_base}
Target Requested Base: {target_base}
Candidate Justification / Value: {justification}

Output MUST be a single valid JSON object:
{{
  "subject": "Counter-offer email subject line",
  "email_body": "Full professional negotiation email text formatted with polite gratitude, strong value articulation, and reasonable request.",
  "talking_points": [
    "Key talking point if discussing on the phone",
    "Alternative non-salary perks to negotiate (e.g. sign-on bonus, equity, remote flexibility)"
  ]
}}
"""
        raw_resp = self.gemini.generate_text(prompt, timeout=20)
        if raw_resp:
            parsed = self.gemini._clean_and_parse_json(raw_resp)
            if isinstance(parsed, dict) and "email_body" in parsed:
                return parsed

        # Deterministic Fallback
        body = f"""Dear Hiring Team at {company},

Thank you very much for offering me the role of {role}. I am genuinely excited about the team's mission and confident that my technical background will allow me to deliver immediate impact to {company}.

After carefully evaluating the compensation package and considering the market value for this role, I would like to discuss the base salary. Given my specialized experience and the value I look forward to contributing, I was hoping we could meet closer to ${target_base:,.0f}.

I am very enthusiastic about joining the team and am confident we can find an agreement that works for both sides. Thank you again for your time and support throughout this process.

Warm regards,
Candidate"""

        return {
            "subject": f"Offer Discussion — {role} at {company}",
            "email_body": body,
            "talking_points": [
                "Express genuine excitement for the role before discussing numbers",
                "Frame the request around value contribution and market alignment",
                "Keep options open for a sign-on bonus or additional stock options if base is firm"
            ]
        }
