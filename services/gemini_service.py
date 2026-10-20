import os
import json
import re
from typing import Dict, Any, Optional
import requests
from dotenv import load_dotenv
from flask import current_app
from utils.logging_config import logger

load_dotenv()

class GeminiService:
    # Prioritize fast, high-availability models with instant fallback
    DEFAULT_MODELS = [
        "gemini-3-flash-preview",
        "gemini-3.1-flash-lite-preview",
        "gemma-4-26b-a4b-it",
    ]
    
    # Class-level rate-limit backoff tracker across threads
    _rate_limit_backoff_until = 0.0

    def __init__(self, api_key: Optional[str] = None):
        self._explicit_key = api_key

    def get_api_key(self) -> str:
        if self._explicit_key is not None:
            return self._explicit_key
        try:
            if current_app and current_app.config.get("GEMINI_API_KEY"):
                return current_app.config["GEMINI_API_KEY"]
        except Exception:
            pass
        return os.getenv("GEMINI_API_KEY", "")

    def is_available(self) -> bool:
        key = self.get_api_key()
        return bool(key and len(key.strip()) > 5)

    def generate_text(self, prompt: str, timeout: int = 8, response_mime_type: Optional[str] = None) -> Optional[str]:
        """
        Invokes Google Gemini REST API with the active key.
        Falls back across available fast model versions with strict low timeouts
        so requests never freeze or hang the user experience.
        """
        import time

        if os.environ.get("PYTEST_CURRENT_TEST") and not self._explicit_key:
            return None

        try:
            if current_app and current_app.config.get("TESTING") and not self._explicit_key:
                return None
        except Exception:
            pass

        # If temporarily quota rate-limited, skip network wait and return None immediately
        if time.time() < GeminiService._rate_limit_backoff_until:
            logger.info("GeminiService: rate-limit active, using grounded deterministic fallback.")
            return None

        api_key = self.get_api_key()
        if not api_key:
            return None

        per_model_timeout = min(max(timeout, 3), 6)
        start_time = time.time()
        max_total_wait = 10.0  # Max 10s wait across all attempts
        models_attempted = 0

        for model_name in self.DEFAULT_MODELS:
            if (time.time() - start_time) > max_total_wait or models_attempted >= 2:
                break
            models_attempted += 1

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            
            payload: Dict[str, Any] = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            if response_mime_type:
                payload["generationConfig"] = {"responseMimeType": response_mime_type}

            try:
                resp = requests.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=per_model_timeout
                )
                
                # If model rejected generationConfig (400), retry once without it for that model
                if resp.status_code == 400 and response_mime_type:
                    payload.pop("generationConfig", None)
                    resp = requests.post(
                        url,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                        timeout=per_model_timeout
                    )

                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            text = parts[0].get("text", "")
                            if text and text.strip():
                                return text
                elif resp.status_code == 429:
                    # Rate limited: all models under this API key are throttled. Set 20s backoff and break immediately!
                    logger.warning(f"Gemini API quota rate-limit (429) hit. Backing off for 20s; returning immediate fallback.")
                    GeminiService._rate_limit_backoff_until = time.time() + 20.0
                    break
                elif resp.status_code in (503, 404):
                    logger.warning(f"Gemini model {model_name} unavailable (status {resp.status_code}): trying next model...")
                    continue
                else:
                    logger.warning(f"Gemini model {model_name} status {resp.status_code}: {resp.text[:120]}")
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                logger.warning(f"Gemini timeout/connection error on model {model_name}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Gemini unexpected error on model {model_name}: {e}")
                continue

        return None

    def generate_json(self, prompt: str, timeout: int = 8) -> Optional[Any]:
        """
        Invokes Gemini with JSON response preference, cleans and parses into JSON object or array.
        """
        raw = self.generate_text(prompt, timeout=timeout, response_mime_type="application/json")
        if not raw:
            # Retry without response_mime_type in case models prefer standard text
            raw = self.generate_text(prompt, timeout=timeout)
        if raw:
            return self._clean_and_parse_json(raw)
        return None

    def analyze_resume_deep(self, raw_text: str) -> Optional[Dict[str, Any]]:
        """
        Uses Google Gemini to parse and deeply analyze a resume with professional ATS intelligence.
        Returns parsed profile data and an in-depth AI critique.
        """
        prompt = f"""You are a senior technical recruiter and principal ATS (Applicant Tracking System) intelligence consultant.
Analyze the following resume thoroughly and extract clean, structured data and an in-depth diagnostic critique.

RESUME CONTENT:
\"\"\"
{raw_text[:12000]}
\"\"\"

Output MUST be a single, valid JSON object (and nothing else) adhering exactly to this structure:
{{
  "parsed_data": {{
    "name": "Full candidate name",
    "email": "candidate@example.com",
    "phone": "+1 555-0199",
    "present_address": "City, State/Country where candidate currently lives/resides (e.g. Dharmavaram, Andhra Pradesh, India)",
    "location": "Same as present_address for compatibility",
    "preferred_locations": ["List of preferred work cities if mentioned, e.g. Bengaluru, Hyderabad, Remote; if none stated, empty list []"],
    "open_to_relocation": true,
    "_location_rule": "NOTE: Address found on resume header is the candidate's present/current residential address, NOT a restriction on where they want to work. Candidates from non-metro areas routinely apply for jobs in major tech hubs (e.g. Bengaluru, Hyderabad, Pune, Mumbai) or Remote.",
    "headline": "Concise professional title (e.g. Senior Full-Stack Engineer)",
    "summary": "Professional executive summary of experience and core competencies",
    "experience_years": 0.5,
    "_experience_years_rule": "CRITICAL: Calculate strictly the total duration of actual professional work experience and internships in decimal years (e.g. 6 months = 0.5, 1 year = 1.0, 3 months = 0.25). NEVER include years spent in college, university, high school, or graduation degree! If candidate is a fresher or only has educational projects, set experience_years to 0.0.",
    "skills": ["Python", "Flask", "PostgreSQL", "Docker", "AWS"],
    "work_experience": [
      {{
        "title": "Software Engineer",
        "company": "Tech Corp",
        "duration": "2021 - Present",
        "location": "City, Country",
        "highlights": [
          "Developed core microservices processing 10M+ daily events",
          "Automated deployment pipelines reducing cycle time by 45%"
        ]
      }}
    ],
    "projects": [
      {{
        "name": "AI Career Assistant",
        "tech_stack": ["Python", "Flask", "Gemini", "SQLAlchemy"],
        "description": "Architected intelligent job matching system with 95% ATS compatibility precision."
      }}
    ],
    "education": [
      {{
        "degree": "Bachelor of Technology in Computer Science",
        "institution": "University Name",
        "year": "2021",
        "gpa_or_percentage": "8.5 CGPA"
      }}
    ],
    "certifications": ["Cert 1", "Cert 2"]
  }},
  "ai_critique": {{
    "executive_summary": "Comprehensive 3-4 sentence professional evaluation of resume strength, clarity, and ATS readability.",
    "ats_score_estimate": 85,
    "key_strengths": [
      "Specific technical strength or clear competitive advantage",
      "Evidence of ownership and tangible engineering contributions"
    ],
    "critical_weaknesses_and_gaps": [
      "Identified weakness, missing quantification, or ATS blind spot",
      "Vague bullet points or unproven technology claims"
    ],
    "actionable_bullet_rewrites": [
      {{
        "original_or_concept": "Original vague bullet or underdeveloped concept from resume",
        "recommended_rewrite": "High-impact rewrite starting with strong action verb and quantified outcome",
        "rationale": "Why this rewrite dramatically improves ATS ranking and recruiter engagement"
      }}
    ],
    "ats_formatting_advice": [
      "Actionable formatting recommendation for ATS scanners"
    ]
  }}
}}
"""
        raw_resp = self.generate_text(prompt, timeout=10, response_mime_type="application/json")
        if not raw_resp:
            raw_resp = self.generate_text(prompt, timeout=10)
        if raw_resp:
            return self._clean_and_parse_json(raw_resp)
        return None

    def _clean_and_parse_json(self, raw_resp: str) -> Optional[Any]:
        text = raw_resp.strip()
        # Remove markdown code fences if present e.g. ```json ... ```
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text)

        try:
            return json.loads(text.strip())
        except json.JSONDecodeError as ex:
            logger.warning(f"JSON direct decode error: {ex}. Attempting regex extraction.")
            # Try to find JSON object { ... }
            m_obj = re.search(r"(\{.*\})", text, re.DOTALL)
            if m_obj:
                try:
                    return json.loads(m_obj.group(1))
                except Exception:
                    pass
            # Try to find JSON array [ ... ]
            m_arr = re.search(r"(\[.*\])", text, re.DOTALL)
            if m_arr:
                try:
                    return json.loads(m_arr.group(1))
                except Exception:
                    pass
        return None
