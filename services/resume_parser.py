import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from services.skill_extractor import skill_extractor, SKILL_TAXONOMY, CANONICAL_MAPPING

# Export COMMON_SKILLS for backward compatibility across collectors and normalizers
COMMON_SKILLS = [skill for sublist in SKILL_TAXONOMY.values() for skill in sublist]

DEGREE_PATTERNS = [
    r"\b(b\.?tech\.?|b\.?e\.?|b\.?s\.?|bachelor['’]?s?|bba|bca|undergraduate)\b",
    r"\b(m\.?tech\.?|m\.?e\.?|m\.?s\.?|master['’]?s?|mba|mca|postgraduate)\b",
    r"\b(ph\.?d\.?|doctorate|doctoral)\b",
    r"\b(associate['’]?s?|diploma)\b"
]

MONTH_MAP = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6,
    "jul": 7, "july": 7, "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12
}

class ResumeParser:
    def __init__(self):
        self.skill_engine = skill_extractor

    def parse(self, raw_text: str) -> Dict[str, Any]:
        """
        Parses raw text of resume into a clean ResumeData object
        following the 4-stage pipeline.
        """
        cleaned = raw_text.strip()
        lines = [l.strip() for l in cleaned.split("\n") if l.strip()]

        contact_info = self._extract_contact_info(cleaned, lines)
        skills = self.skill_engine.extract_skills(cleaned)
        skills_by_category = self.skill_engine.extract_skills_by_category(cleaned)
        experience_info = self._extract_experience(cleaned, lines)
        education_info = self._extract_education(cleaned, lines)
        projects = self._extract_projects(cleaned, lines)
        certifications = self._extract_certifications(cleaned, lines)
        summary = self._extract_summary(lines)

        return {
            "name": contact_info["name"],
            "email": contact_info["email"],
            "phone": contact_info["phone"],
            "location": contact_info["location"],
            "linkedin": contact_info.get("linkedin", ""),
            "github": contact_info.get("github", ""),
            "portfolio": contact_info.get("portfolio", ""),
            "present_address": contact_info.get("present_address", contact_info["location"]),
            "preferred_locations": contact_info.get("preferred_locations", []),
            "open_to_relocation": contact_info.get("open_to_relocation", True),
            "headline": contact_info["headline"],
            "summary": summary,
            "skills": skills,
            "skills_by_category": skills_by_category,
            "experience_years": experience_info["total_years"],
            "experience": experience_info["roles"],
            "education": education_info,
            "projects": projects,
            "certifications": certifications
        }

    def _extract_contact_info(self, text: str, lines: List[str]) -> Dict[str, Any]:
        email = ""
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        if email_match:
            email = email_match.group(0).lower()

        phone = ""
        phone_match = re.search(r"(\+?\d{1,3}[\s-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}", text)
        if phone_match:
            phone = phone_match.group(0).strip()

        # Link extraction (LinkedIn, GitHub, Portfolio)
        linkedin = ""
        li_match = re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/in/([a-zA-Z0-9\-_%]+)", text, re.IGNORECASE)
        if li_match:
            linkedin = f"https://linkedin.com/in/{li_match.group(1)}"

        github = ""
        gh_match = re.search(r"(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9\-_%]+)", text, re.IGNORECASE)
        if gh_match and gh_match.group(1).lower() not in ("features", "pricing", "marketplace"):
            github = f"https://github.com/{gh_match.group(1)}"

        portfolio = ""
        port_match = re.search(r"(?:https?://)?(?:www\.)?([a-zA-Z0-9\-_]+\.(?:io|dev|me|app|vercel\.app|netlify\.app)(?:/[^\s,;]*)?)", text, re.IGNORECASE)
        if port_match:
            portfolio = f"https://{port_match.group(1)}"

        # Name heuristic: First non-empty 2-to-4 word line that doesn't contain email/phone/url
        name = ""
        headline = ""
        for line in lines[:5]:
            if "@" in line or "http" in line or any(c.isdigit() for c in line if line.count(c) > 3):
                continue
            words = line.split()
            if len(words) in [2, 3, 4] and not name and not any(w.lower() in ("resume", "curriculum", "vitae", "profile") for w in words):
                name = line.title()
            elif name and not headline and len(line) < 60:
                headline = line
                break

        # Location / Address heuristic: explicitly distinguish present/current residential address from preferred locations
        location = ""
        # 1. Check explicit present address patterns
        addr_match = re.search(r"(?:present\s+address|current\s+address|permanent\s+address|residential\s+address|address|location)\s*[:\-]\s*([^\n\r\|]+)", text, re.IGNORECASE)
        if addr_match:
            location = addr_match.group(1).strip()
        else:
            loc_match = re.search(r"\b([A-Z][a-zA-Z]+(?:[\s-][A-Z][a-zA-Z]+)?),\s*([A-Z]{2}|[A-Za-z]+(?:\s*,\s*[A-Za-z]+)?)\b", text)
            if loc_match:
                location = loc_match.group(0)

        # 2. Check for explicit preferred work locations stated in resume
        preferred_locations = []
        pref_match = re.search(r"(?:preferred\s+locations?|target\s+locations?|preferred\s+cities?|desired\s+locations?)\s*[:\-]\s*([^\n\r\|]+)", text, re.IGNORECASE)
        if pref_match:
            preferred_locations = [p.strip() for p in re.split(r"[,/|;]", pref_match.group(1)) if p.strip()]

        # 3. Check for relocation willingness
        open_to_relocation = bool(re.search(r"\b(?:open\s+to\s+relocat|willing\s+to\s+relocat|relocation\s*:\s*yes)\b", text, re.IGNORECASE)) or True

        return {
            "name": name or "Candidate",
            "email": email,
            "phone": phone,
            "linkedin": linkedin,
            "github": github,
            "portfolio": portfolio,
            "location": location,
            "present_address": location,
            "preferred_locations": preferred_locations,
            "open_to_relocation": open_to_relocation,
            "headline": headline
        }

    def _extract_skills(self, text: str) -> List[str]:
        return self.skill_engine.extract_skills(text)

    def _canonicalize_skill(self, skill: str) -> str:
        return self.skill_engine.canonicalize(skill)

    def _extract_experience(self, text: str, lines: List[str]) -> Dict[str, Any]:
        """
        Accurately extracts work experience roles and calculates professional experience duration.
        CRITICAL: Never counts education dates or years since college matriculation as experience!
        """
        # 1. First check for explicit experience duration in the text (e.g. '0.5 years', '6 months experience')
        explicit_months_match = re.search(r"\b([0-9]+)\s*(?:months?|mos?)(?:\s+(?:of\s+)?experience)?\b", text, re.IGNORECASE)
        explicit_years_match = re.search(r"\b([0-9]+(?:\.[0-9]+)?)\+?\s*(?:years?|yrs?)(?:\s+(?:of\s+)?experience)\b", text, re.IGNORECASE)

        # 2. Extract lines belonging specifically to the Experience section
        roles = []
        exp_lines = []
        is_exp_section = False
        current_role = None

        EXP_HEADERS = [
            "experience", "work experience", "professional experience",
            "employment history", "internships", "internship experience", "work history"
        ]
        OTHER_HEADERS = [
            "education", "academic background", "academics", "projects",
            "technical skills", "skills", "certifications", "publications", "achievements"
        ]

        for line in lines:
            line_clean = line.strip().lower()
            if any(line_clean == h or line_clean.startswith(h + " ") or line_clean.startswith(h + ":") for h in EXP_HEADERS):
                is_exp_section = True
                continue
            elif is_exp_section and any(line_clean == h or line_clean.startswith(h + " ") or line_clean.startswith(h + ":") for h in OTHER_HEADERS):
                is_exp_section = False
                if current_role:
                    roles.append(current_role)
                    current_role = None
                break

            if is_exp_section:
                exp_lines.append(line)
                # Check for role header
                if any(kw in line_clean for kw in ["developer", "engineer", "lead", "analyst", "manager", "intern", "specialist", "consultant", "associate", "trainee", "founder", "contractor"]):
                    if current_role:
                        roles.append(current_role)
                    current_role = {"title": line, "details": []}
                elif current_role:
                    current_role["details"].append(line)

        if current_role and current_role not in roles:
            roles.append(current_role)

        # 3. Calculate experience duration strictly from the extracted experience section
        total_months = 0
        date_pattern = re.compile(
            r"(?:(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+)?(20[0-2][0-9]|199[0-9])"
            r"\s*(?:-|–|—|to)\s*"
            r"(?:(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+)?(20[0-2][0-9]|199[0-9]|present|current|now)",
            re.IGNORECASE
        )

        exp_text = " \n ".join(exp_lines)
        matches = date_pattern.findall(exp_text)

        now = datetime.now()
        for start_mon_str, start_yr_str, end_mon_str, end_yr_str in matches:
            start_yr = int(start_yr_str)
            start_mon = MONTH_MAP.get(start_mon_str.lower(), 1) if start_mon_str else 1

            if end_yr_str.lower() in ("present", "current", "now"):
                end_yr = now.year
                end_mon = now.month
            else:
                end_yr = int(end_yr_str)
                end_mon = MONTH_MAP.get(end_mon_str.lower(), 12) if end_mon_str else 12

            diff_months = (end_yr - start_yr) * 12 + (end_mon - start_mon) + 1
            if 0 < diff_months <= 480:  # reasonable cap (up to 40 years)
                total_months += diff_months

        # If date ranges in experience yielded months, convert to years
        if total_months > 0:
            total_years = round(total_months / 12.0, 1)
        elif explicit_months_match:
            total_years = round(int(explicit_months_match.group(1)) / 12.0, 1)
        elif explicit_years_match:
            total_years = round(float(explicit_years_match.group(1)), 1)
        else:
            total_years = 0.0

        return {"total_years": total_years, "roles": roles}

    def _extract_education(self, text: str, lines: List[str]) -> List[Dict[str, str]]:
        education = []
        lowered = text.lower()
        for pat in DEGREE_PATTERNS:
            match = re.search(pat, lowered)
            if match:
                degree_name = match.group(0).title()
                # Try to find nearby school/university name
                school = "Recognized Institution"
                for line in lines:
                    if any(w in line.lower() for w in ["university", "college", "institute", "school"]):
                        school = line
                        break
                education.append({"degree": degree_name, "institution": school})
                break
        return education

    def _extract_projects(self, text: str, lines: List[str]) -> List[Dict[str, str]]:
        projects = []
        is_proj_section = False
        current_proj = None

        for line in lines:
            line_lower = line.lower()
            if "project" in line_lower and len(line_lower) < 25:
                is_proj_section = True
                continue
            elif is_proj_section and any(h in line_lower for h in ["education", "skills", "experience", "certifications"]):
                is_proj_section = False
                if current_proj:
                    projects.append(current_proj)
                break

            if is_proj_section:
                if line.startswith(("-", "*", "•")) or len(line.split()) < 6:
                    if current_proj and len(current_proj["description"]) > 10:
                        projects.append(current_proj)
                    current_proj = {"title": line.strip("-*• "), "description": ""}
                elif current_proj:
                    current_proj["description"] += " " + line

        if current_proj and current_proj not in projects:
            projects.append(current_proj)

        return projects[:5]

    def _extract_certifications(self, text: str, lines: List[str]) -> List[str]:
        certs = []
        cert_definitions = [
            ("AWS Certified", r"\b(?:aws\s+certified|aws\s+solutions\s+architect|aws\s+cloud\s+practitioner|aws\s+developer)\b"),
            ("Azure Fundamentals", r"\b(?:azure\s+fundamentals|az-900|azure\s+certified|azure\s+solutions\s+architect)\b"),
            ("GCP Cloud Architect", r"\b(?:gcp\s+certified|gcp\s+cloud\s+architect|google\s+cloud\s+certified|gcp\s+data\s+engineer)\b"),
            ("CKA (Kubernetes Administrator)", r"\b(?:cka|certified\s+kubernetes\s+administrator|ckad)\b"),
            ("PMP", r"\b(?:pmp|project\s+management\s+professional)\b"),
            ("Scrum Master", r"\b(?:scrum\s+master|certified\s+scrum\s+master|csm|psm\s*i)\b"),
            ("CompTIA", r"\b(?:comptia(?:\s+security\+|\s+network\+|\s+a\+)?)\b"),
            ("CISSP", r"\b(?:cissp|certified\s+information\s+systems\s+security\s+professional)\b"),
            ("Terraform Associate", r"\b(?:hashicorp\s+certified|terraform\s+associate)\b"),
        ]
        for canonical, pat in cert_definitions:
            if re.search(pat, text, re.IGNORECASE):
                certs.append(canonical)
        return list(dict.fromkeys(certs))

    def _extract_summary(self, lines: List[str]) -> str:
        for i, line in enumerate(lines[:10]):
            if any(s in line.lower() for s in ["summary", "profile", "objective", "about me"]):
                if i + 1 < len(lines):
                    return lines[i + 1]
        return ""
