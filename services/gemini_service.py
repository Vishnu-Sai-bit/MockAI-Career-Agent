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
    DEFAULT_MODELS = ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-flash-latest"]

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

    def generate_text(self, prompt: str, timeout: int = 20) -> Optional[str]:
        """
        Invokes Google Gemini REST API with the active key.
        Falls back across available model versions.
        """
        if os.environ.get("PYTEST_CURRENT_TEST") and not self._explicit_key:
            return None

        try:
            if current_app and current_app.config.get("TESTING") and not self._explicit_key:
                return None
        except Exception:
            pass

        api_key = self.get_api_key()
        if not api_key:
            return None

        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }

        for model_name in self.DEFAULT_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            try:
                resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
                else:
                    logger.warning(f"Gemini model {model_name} returned status {resp.status_code}: {resp.text[:150]}")
            except Exception as e:
                logger.warning(f"Gemini REST error on model {model_name}: {e}")
                continue

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
    "location": "City, State/Country",
    "headline": "Concise professional title (e.g. Senior Full-Stack Engineer)",
    "summary": "Professional executive summary of experience and core competencies",
    "experience_years": 4.5,
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
        raw_resp = self.generate_text(prompt, timeout=25)
        if raw_resp:
            return self._clean_and_parse_json(raw_resp)
        return None

    def _clean_and_parse_json(self, raw_resp: str) -> Optional[Dict[str, Any]]:
        text = raw_resp.strip()
        # Remove markdown code fences if present e.g. ```json ... ```
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text)

        try:
            data = json.loads(text.strip())
            return data
        except json.JSONDecodeError as ex:
            logger.error(f"JSON decode error from Gemini response: {ex}. Raw snippet: {text[:200]}")
            m = re.search(r"(\{.*\})", text, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(1))
                except Exception:
                    pass
        return None
