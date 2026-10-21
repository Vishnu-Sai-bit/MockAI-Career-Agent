import re
from typing import Dict, Any, List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from models.job import Job
from models.resume import Resume
from models.user import CandidateProfile

class JobMatcher:
    # Component weights:
    # M = 0.35S + 0.20E + 0.15K + 0.10P + 0.10L + 0.10Q
    W_SKILLS = 0.35
    W_EXPERIENCE = 0.20
    W_KEYWORDS = 0.15
    W_PROJECTS = 0.10
    W_LOCATION = 0.10
    W_QUALIFICATIONS = 0.10

    def compute_match(
        self,
        resume: Resume,
        profile: CandidateProfile,
        job: Job
    ) -> Dict[str, Any]:
        """
        Calculates explainable ATS Job Compatibility Score (M) and breakdown.
        Formula: M = 0.35S + 0.20E + 0.15K + 0.10P + 0.10L + 0.10Q
        """
        resume_data = resume.parsed_data or {}
        candidate_skills = [s.lower() for s in (resume_data.get("skills") or (profile.skills if profile else []) or [])]
        candidate_years = float(resume_data.get("experience_years") or (profile.experience_years if profile else 0.0) or 0.0)
        candidate_projects = resume_data.get("projects") or (profile.projects if profile else []) or []
        candidate_education = resume_data.get("education") or (profile.education if profile else []) or []
        resume_raw_text = resume.raw_text or ""

        # 1. Skills Alignment (S - 35%)
        s_score, skill_details = self._score_skills(candidate_skills, job)

        # 2. Experience Alignment (E - 20%)
        e_score, exp_details = self._score_experience(candidate_years, job)

        # 3. Title / Role & Keyword Coverage (K - 15%)
        candidate_headline = (resume_data.get("headline") or (profile.headline if profile else "") or "")
        k_score = self._score_keyword_coverage(resume_raw_text, job.description, candidate_headline, job.title)

        # 4. Project & Practical Evidence (P - 10%)
        p_score, proj_details = self._score_projects(candidate_projects, job)

        # 5. Location & Work-Mode Fit (L - 10%)
        l_score, loc_flags = self._score_location_and_work_mode(profile, job)

        # 6. Resume Quality & Qualification Alignment (Q - 10%)
        # Q (10%): The calculated Resume Quality Score from Phase 2
        if resume and getattr(resume, "ats_quality_score", None) is not None and resume.ats_quality_score >= 70.0:
            q_score = float(resume.ats_quality_score)
        else:
            from services.resume_analyzer import ResumeAnalyzer
            analyzer = ResumeAnalyzer()
            eval_data = dict(resume_data)
            if profile:
                if profile.skills and not eval_data.get("skills"):
                    eval_data["skills"] = profile.skills
                if profile.experience_years and not eval_data.get("experience_years"):
                    eval_data["experience_years"] = profile.experience_years
                if profile.education and not eval_data.get("education"):
                    eval_data["education"] = profile.education
            analysis = analyzer.analyze_resume_quality(resume_raw_text, eval_data)
            raw_q = float(analysis.get("overall_quality_score", 75.0))
            q_score = max(raw_q, 75.0 if not candidate_education else 90.0)

        # Weighted ATS compatibility calculation
        total_score = round(
            self.W_SKILLS * s_score +
            self.W_EXPERIENCE * e_score +
            self.W_KEYWORDS * k_score +
            self.W_PROJECTS * p_score +
            self.W_LOCATION * l_score +
            self.W_QUALIFICATIONS * q_score,
            2
        )
        total_score = max(0.0, min(100.0, total_score))

        # Generate transparent, explainable narrative
        explanation, eligibility_flags = self._generate_explanation(
            total_score,
            skill_details,
            exp_details,
            loc_flags,
            job
        )

        return {
            "match_score": total_score,
            "score_breakdown": {
                "skills": round(s_score, 1),
                "experience": round(e_score, 1),
                "keyword_coverage": round(k_score, 1),
                "projects": round(p_score, 1),
                "location": round(l_score, 1),
                "qualifications": round(q_score, 1),
                "quality_score_q": round(q_score, 1)
            },
            "skill_match_details": skill_details,
            "match_explanation": explanation,
            "eligibility_flags": eligibility_flags
        }

    def _score_skills(self, candidate_skills: List[str], job: Job) -> Tuple[float, Dict[str, Any]]:
        req_skills = [s.lower() for s in (job.required_skills or [])]
        pref_skills = [s.lower() for s in (job.preferred_skills or [])]

        matched_req = [s.title() for s in req_skills if any(cs in s or s in cs for cs in candidate_skills)]
        missing_req = [s.title() for s in req_skills if s.title() not in matched_req]

        matched_pref = [s.title() for s in pref_skills if any(cs in s or s in cs for cs in candidate_skills)]
        missing_pref = [s.title() for s in pref_skills if s.title() not in matched_pref]

        # If job has no parsed required skills, check matching candidate skills in description
        if not req_skills:
            job_desc_lower = job.description.lower()
            matched_desc = [s.title() for s in candidate_skills if s in job_desc_lower]
            s_score = min(100.0, max(50.0, len(matched_desc) * 12.0))
            return s_score, {
                "matched_required": matched_desc,
                "missing_required": [],
                "matched_preferred": [],
                "missing_preferred": []
            }

        # (Matched Skills from Resume / Total Required Skills in Job Posting) * 100
        req_overlap = (len(matched_req) / len(req_skills)) * 100.0
        # Preferred skills bonus (up to 10%)
        if pref_skills and matched_pref:
            bonus = min(10.0, (len(matched_pref) / len(pref_skills)) * 10.0)
            score = min(100.0, req_overlap + bonus)
        else:
            score = req_overlap

        return min(100.0, max(0.0, score)), {
            "matched_required": matched_req,
            "missing_required": missing_req,
            "matched_preferred": matched_pref,
            "missing_preferred": missing_pref
        }

    def _score_experience(self, cand_years: float, job: Job) -> Tuple[float, str]:
        exp_lvl = (job.experience_level or "mid").lower()
        title_lower = job.title.lower()

        # Parse target years if explicitly stated in description e.g. "5+ years", "2-4 years"
        years_match = re.search(r"(\d+)\+?\s*years?(?:\s+of)?\s+experience", job.description, re.IGNORECASE)
        target_years = int(years_match.group(1)) if years_match else None

        if target_years is None:
            if "entry" in exp_lvl or any(w in title_lower for w in ["entry", "fresher", "intern", "junior", "graduate"]):
                target_years = 0
            elif "senior" in exp_lvl or "sr." in title_lower:
                target_years = 5
            elif "lead" in exp_lvl or any(w in title_lower for w in ["lead", "principal", "architect", "staff"]):
                target_years = 8
            else:
                target_years = 2

        # Experience Alignment (E - 20%):
        # Case 1: Entry / Fresher Role (0-2 years)
        if "entry" in exp_lvl or target_years <= 1 or any(w in title_lower for w in ["entry", "fresher", "intern", "junior", "graduate"]):
            if cand_years <= 2.0:
                score = 100.0
                detail = f"Perfect fit for Entry-level / Fresher position ({cand_years:.1f} yrs experience - 100% alignment)."
            elif cand_years <= 4.0:
                score = 85.0
                detail = f"Has {cand_years:.1f} yrs experience; eligible for junior/entry role (85% alignment)."
            else:
                score = 70.0
                detail = f"Candidate has {cand_years:.1f} yrs experience; standing above entry-level bracket (70% alignment)."

        # Case 2: Mid-Level Role (2-5 years)
        elif "mid" in exp_lvl or (2 <= target_years < 5):
            if 1.5 <= cand_years <= 5.0:
                score = 100.0
                detail = f"Fits target mid-level experience range ({cand_years:.1f} yrs vs {target_years} yrs targeted - 100% alignment)."
            elif cand_years < 1.5:
                ratio = max(0.25, cand_years / max(target_years, 2))
                score = max(35.0, round(ratio * 70.0, 1))
                detail = f"Position targets {target_years}+ yrs mid-level experience; candidate has {cand_years:.1f} yrs ({score:.0f}% alignment)."
            else:
                score = 90.0
                detail = f"Experienced candidate ({cand_years:.1f} yrs) eligible for mid-level position (90% alignment)."

        # Case 3: Senior Role (5-8 years)
        elif "senior" in exp_lvl or (5 <= target_years < 8):
            if 5.0 <= cand_years <= 9.0:
                score = 100.0
                detail = f"Fits senior experience range ({cand_years:.1f} yrs vs {target_years} yrs targeted - 100% alignment)."
            elif cand_years > 9.0:
                score = 95.0
                detail = f"Extensive senior experience ({cand_years:.1f} yrs - 95% alignment)."
            else:
                ratio = cand_years / max(target_years, 5)
                score = max(25.0, round(ratio * 100.0, 1))
                detail = f"Position requires {target_years}+ yrs senior experience; candidate has {cand_years:.1f} yrs ({score:.0f}% alignment)."

        # Case 4: Lead / Staff / Principal (8+ years)
        else:
            if cand_years >= 8.0:
                score = 100.0
                detail = f"Fits leadership tenure requirement ({cand_years:.1f} yrs - 100% alignment)."
            else:
                ratio = cand_years / max(target_years, 8)
                score = max(20.0, round(ratio * 100.0, 1))
                detail = f"Position requires {target_years}+ yrs lead experience; candidate has {cand_years:.1f} yrs ({score:.0f}% alignment)."

        return score, detail

    def _score_keyword_coverage(self, resume_text: str, job_desc: str, candidate_headline: str = "", job_title: str = "") -> float:
        if not resume_text and not candidate_headline:
            return 50.0
        try:
            # Token cosine similarity between candidate headline and job title
            title_sim = 0.0
            if candidate_headline and job_title:
                try:
                    t_vec = TfidfVectorizer(stop_words="english")
                    t_mat = t_vec.fit_transform([candidate_headline, job_title])
                    title_sim = float(cosine_similarity(t_mat[0:1], t_mat[1:2])[0][0])
                except Exception:
                    pass

            # Body keyword similarity
            vectorizer = TfidfVectorizer(stop_words="english", max_features=100)
            tfidf_matrix = vectorizer.fit_transform([resume_text or candidate_headline, job_desc or job_title])
            desc_sim = float(cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0])

            combined_sim = max(title_sim, desc_sim) if title_sim > 0 else desc_sim
            score = min(100.0, max(30.0, combined_sim * 150.0))
            return score
        except Exception:
            return 60.0

    def _score_projects(self, projects: List[Any], job: Job) -> Tuple[float, str]:
        # Project & Practical Evidence: whether resume shows applying tools in projects (>= 3 projects = 95%)
        if not projects:
            return 50.0, "No projects detailed on resume."
        count = len(projects)
        if count >= 3:
            return 95.0, f"{count} projects demonstrated with practical tool application (95% evidence)."
        elif count == 2:
            return 80.0, "2 projects detailed on resume (80% evidence)."
        elif count == 1:
            return 65.0, "1 project detailed on resume (65% evidence)."
        return 50.0, "No projects detailed on resume."

    def _score_location_and_work_mode(self, profile: CandidateProfile, job: Job) -> Tuple[float, List[str]]:
        # Location & Work-Mode Fit:
        # 100% for Remote/Worldwide or matching city; 85% for major metro tech hubs (Bangalore, Hyderabad, etc.)
        flags = []
        user_modes = [m.lower() for m in (profile.work_modes if profile and profile.work_modes else ["remote", "hybrid", "on-site"])]
        job_mode = (job.work_mode or "on-site").lower()
        job_loc = (job.location or "").lower()

        # 100% for Remote or Worldwide
        if job_mode == "remote" or any(w in job_loc for w in ["remote", "worldwide", "anywhere"]):
            flags.append("🌐 Remote / Worldwide eligible (100% location fit).")
            return 100.0, flags

        cand_loc = (profile.location or "").lower() if profile else ""
        pref_cities = [c.lower() for c in (profile.preferred_cities or [])] if profile else []

        # 100% for matching city
        if cand_loc and (cand_loc in job_loc or job_loc in cand_loc):
            flags.append(f"📍 Matches present city: {job.location or 'Local Office'} (100% location fit).")
            return 100.0, flags

        if pref_cities and any(c in job_loc for c in pref_cities if c):
            flags.append(f"🎯 Matches preferred work city: {job.location} (100% location fit).")
            return 100.0, flags

        # 85% for major metro tech hubs (Bangalore, Hyderabad, Pune, Mumbai, Delhi, Gurgaon, San Francisco, Seattle, etc.)
        METRO_HUBS = [
            "bangalore", "bengaluru", "hyderabad", "pune", "mumbai", "delhi", "noida",
            "gurgaon", "gurugram", "chennai", "san francisco", "seattle", "austin", "new york"
        ]
        if any(hub in job_loc for hub in METRO_HUBS):
            flags.append(f"🏢 Located in major tech hub: {job.location or 'Metro Hub'} (85% location fit).")
            return 85.0, flags

        flags.append(f"Requires {job_mode} presence in {job.location or 'office'}.")
        return 70.0, flags

    def _score_qualifications(self, education: List[Any], job: Job) -> Tuple[float, str]:
        # Qualifications: Relevant academic degree, engineering background, or equivalent standing
        if not education:
            return 75.0, "Degree not explicitly stated."
        return 90.0, "Educational background aligns with standard qualifications."

    def _generate_explanation(
        self,
        total_score: float,
        skill_details: Dict[str, Any],
        exp_details: str,
        loc_flags: List[str],
        job: Job
    ) -> Tuple[str, List[str]]:
        matched = skill_details.get("matched_required", [])
        missing = skill_details.get("missing_required", [])

        # Match Categorization:
        # 80% – 98%: Strong Match (High probability of passing ATS recruiter screening)
        # 65% – 79%: Moderate Match (Core qualifications met; may need minor keyword tailoring)
        # Below 65%: Potential Fit (Noticeable skill or experience gaps)
        if total_score >= 80:
            tier = "Strong Match (High probability of passing ATS recruiter screening)"
        elif total_score >= 65:
            tier = "Moderate Match (Core qualifications met; may need minor keyword tailoring)"
        else:
            tier = "Potential Fit (Noticeable skill or experience gaps)"

        parts = [f"{tier} — {total_score:.1f}% compatibility."]
        if matched:
            parts.append(f"Skills matched: {', '.join(matched[:5])}.")
        if missing:
            parts.append(f"Missing evidence in resume for: {', '.join(missing[:4])}.")
        parts.append(exp_details)

        explanation = " ".join(parts)
        return explanation, loc_flags
