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
        Defaults to Indian Rupee (INR / ₹) standards.
        """
        loc_str = location or "Bengaluru, India"
        loc_lower = loc_str.lower()
        is_us = any(term in loc_lower for term in ["usa", "san francisco", "new york", "united states", "seattle", "austin"])

        prompt = f"""You are a principal compensation consultant and compensation benchmark analyst.
Estimate the competitive market salary percentiles for this role.
If the location is in the US (e.g. San Francisco, USA), output USD.
Otherwise, provide all compensation figures in Indian Rupees (INR / ₹) adhering to modern tech industry standards (e.g. 10 LPA - 50 LPA depending on role & tenure).

ROLE DETAILS:
Title: {title}
Location: {loc_str}
Experience: {experience_years} years
Key Skills: {', '.join(skills[:8]) if skills else 'Software Engineering'}

Format output as a valid JSON object:
{{
  "currency": "{'USD' if is_us else 'INR'}",
  "percentile_25": {95000 if is_us else 1200000},
  "median": {125000 if is_us else 1600000},
  "percentile_75": {150000 if is_us else 2200000},
  "percentile_90": {175000 if is_us else 2800000},
  "market_demand_rating": "Very High / High / Moderate",
  "salary_drivers": [
    "Key factor or skill driving compensation premium (e.g. distributed systems, AI)",
    "Geographic or remote market factor"
  ],
  "negotiation_leverage_summary": "1-2 sentence assessment of candidate leverage in this market segment."
}}
"""
        parsed = self.gemini.generate_json(prompt, timeout=8)
        if isinstance(parsed, dict) and "median" in parsed:
            # If not US and output has USD, normalize to INR
            if not is_us and parsed.get("currency") == "USD":
                rate = 83.33
                parsed["currency"] = "INR"
                for k in ["percentile_25", "median", "percentile_75", "percentile_90"]:
                    if k in parsed and isinstance(parsed[k], (int, float)) and parsed[k] < 500000:
                        parsed[k] = round(parsed[k] * rate, -4)
            return parsed

        # Deterministic benchmark calculation
        if is_us:
            base_usd = 85000.0 + min(experience_years * 12000.0, 100000.0)
            return {
                "currency": "USD",
                "percentile_25": round(base_usd * 0.85, -3),
                "median": round(base_usd, -3),
                "percentile_75": round(base_usd * 1.20, -3),
                "percentile_90": round(base_usd * 1.40, -3),
                "market_demand_rating": "High",
                "salary_drivers": [f"Deep proficiency in {', '.join(skills[:3]) if skills else 'core competencies'}", "Competitive US tech market"],
                "negotiation_leverage_summary": "Strong leverage for candidates demonstrating measurable business impact and clean architecture."
            }

        # Default: Indian Rupee (INR / ₹)
        base_inr = 800000.0 + min(experience_years * 250000.0, 2700000.0)
        return {
            "currency": "INR",
            "percentile_25": round(base_inr * 0.80, -4),
            "median": round(base_inr, -4),
            "percentile_75": round(base_inr * 1.30, -4),
            "percentile_90": round(base_inr * 1.65, -4),
            "market_demand_rating": "High",
            "salary_drivers": [
                f"Specialized experience in {', '.join(skills[:3]) if skills else 'Tech & AI'}",
                "Fast-growing Indian tech hub premium & remote competitiveness"
            ],
            "negotiation_leverage_summary": "High market demand for proven contributors with strong problem-solving fundamentals."
        }

    def generate_counter_offer(self, company: str, role: str, current_offer_base: float, target_base: float, justification: str, currency: str = "INR") -> Dict[str, Any]:
        """
        Drafts a professional, gracious counter-offer negotiation email.
        """
        curr_sym = "₹" if currency.upper() in ["INR", "RUPEE"] else currency
        target_val = float(target_base)
        if target_val >= 100000 and curr_sym == "₹":
            target_str = f"₹{target_val:,.0f} ({target_val / 100000:.1f} LPA)"
        else:
            target_str = f"{curr_sym}{target_val:,.0f}"

        prompt = f"""You are a master executive negotiation coach.
Draft a tactful, highly professional counter-offer email for a candidate negotiating a job offer.

DETAILS:
Company: {company}
Role: {role}
Current Offered Base: {current_offer_base}
Target Requested Base: {target_str}
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
        parsed = self.gemini.generate_json(prompt, timeout=8)
        if isinstance(parsed, dict) and "email_body" in parsed:
            return parsed

        # Deterministic Fallback
        body = f"""Dear Hiring Team at {company},

Thank you very much for offering me the role of {role}. I am genuinely excited about the team's mission and confident that my technical background will allow me to deliver immediate impact to {company}.

After carefully evaluating the compensation package and considering the market value for this role, I would like to discuss the base salary. Given my specialized experience and the value I look forward to contributing, I was hoping we could meet closer to {target_str}.

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
