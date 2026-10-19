import urllib.parse
from datetime import datetime, timezone
from typing import Dict, Any, List
from services.gemini_service import GeminiService

class OutreachService:
    """
    Automates recruiter discovery, LinkedIn outreach, and anti-ghosting follow-up emails.
    """

    def __init__(self):
        self.gemini = GeminiService()

    def generate_recruiter_personas(self, company: str, job_title: str) -> Dict[str, Any]:
        """
        Constructs target recruiter titles and ready-to-click LinkedIn search URLs.
        """
        company_clean = company.strip()
        title_clean = job_title.strip()

        # Potential search queries
        queries = [
            f"{company_clean} Technical Recruiter",
            f"{company_clean} Talent Acquisition {title_clean.split()[0]}",
            f"{company_clean} Engineering Manager",
            f"{company_clean} Head of Talent"
        ]

        search_links = []
        for q in queries:
            encoded = urllib.parse.quote_plus(q)
            url = f"https://www.linkedin.com/search/results/people/?keywords={encoded}&origin=GLOBAL_SEARCH_HEADER"
            search_links.append({
                "target_persona": q,
                "linkedin_search_url": url
            })

        return {
            "company": company_clean,
            "job_title": title_clean,
            "search_targets": search_links
        }

    def generate_outreach_templates(self, candidate_name: str, candidate_skills: List[str], company: str, job_title: str) -> Dict[str, Any]:
        """
        Generates tailored LinkedIn Connection notes (<300 chars) and InMail outreach.
        """
        primary_skill = candidate_skills[0] if candidate_skills else "Software Engineering"
        top_skills_str = ", ".join(candidate_skills[:3]) if candidate_skills else "Python, Cloud & APIs"

        prompt = f"""You are an executive career coach helping a candidate connect with a recruiter.
Candidate: {candidate_name}
Target Role: {job_title} at {company}
Top Skills: {top_skills_str}

Requirements:
1. Generate a concise LinkedIn Connection Request Note (MAXIMUM 280 CHARACTERS).
2. Generate an engaging, professional InMail message (under 120 words).
3. Return as JSON:
{{
  "linkedin_note": "text here under 280 chars",
  "inmail_subject": "subject line",
  "inmail_body": "body text"
}}
"""
        res = self.gemini.generate_json(prompt)
        if res and "linkedin_note" in res:
            return {
                "linkedin_note": res.get("linkedin_note", "")[:295],
                "inmail_subject": res.get("inmail_subject", f"Regarding {job_title} role at {company}"),
                "inmail_body": res.get("inmail_body", "")
            }

        # Deterministic fallback
        note = f"Hi! I recently came across the {job_title} role at {company}. With strong background in {top_skills_str}, I’d love to connect and share how my expertise can support your engineering goals. Best, {candidate_name}"[:290]

        inmail_body = f"""Hi [Hiring Manager / Recruiter Name],

I hope this note finds you well.

I noticed the {job_title} opening on {company}'s career portal and wanted to reach out directly. With hands-on experience in {top_skills_str}, I have built scalable systems delivering high performance and business value.

I would appreciate the chance to discuss how my skill set aligns with your upcoming initiatives. Please find my portfolio and resume attached in my application.

Best regards,
{candidate_name}"""

        return {
            "linkedin_note": note,
            "inmail_subject": f"Inquiry regarding {job_title} position — {candidate_name}",
            "inmail_body": inmail_body
        }

    def generate_followup_email(self, candidate_name: str, company: str, job_title: str, application_date: datetime = None, stage: str = "7day") -> Dict[str, Any]:
        """
        Generates contextual follow-up emails:
        - '7day': 1-week polite inquiry
        - '14day': 2-week value-add check-in (anti-ghosting)
        - 'post_interview': 24h post-interview appreciation note
        """
        app_date_str = application_date.strftime("%B %d") if application_date else "recently"

        if stage == "post_interview":
            subject = f"Thank you for the interview — {candidate_name} ({job_title})"
            body = f"""Dear [Interviewer / Hiring Team],

Thank you for taking the time to speak with me today about the {job_title} opportunity at {company}.

I really enjoyed our discussion regarding the team's upcoming milestones and technical challenges. The conversation reinforced my enthusiasm for joining {company}, especially given my background in solving similar scalability and development problems.

Please don't hesitate to reach out if you need any additional information from my side. I look forward to hearing about the next steps.

Warm regards,
{candidate_name}"""
        elif stage == "14day":
            subject = f"Following up on {job_title} application — {candidate_name}"
            body = f"""Dear [Hiring Manager / Talent Team],

I hope your week is off to a great start.

I am writing to politely follow up on my application for the {job_title} position submitted on {app_date_str}. I remain very enthusiastic about the possibility of contributing to {company}'s team.

I recently published updates to my technical portfolio showcasing work closely related to your tech stack. I've attached my latest resume for your review.

Could you kindly share an update on the hiring timeline for this role?

Best regards,
{candidate_name}"""
        else: # 7day default
            subject = f"Checking in regarding {job_title} application — {candidate_name}"
            body = f"""Dear {company} Talent Team,

I hope you are doing well.

I submitted my application for the {job_title} opening on {app_date_str} and wanted to briefly reiterate my strong interest in joining {company}. 

Given the team's inspiring trajectory, I am confident my technical expertise would allow me to make an immediate, positive impact.

I understand you are likely reviewing many applications, and I appreciate your time and consideration.

Warm regards,
{candidate_name}"""

        return {
            "stage": stage,
            "subject": subject,
            "body": body,
            "company": company,
            "job_title": job_title
        }
