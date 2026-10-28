import json
from typing import Dict, Any, List, Optional
from models.job import Job
from models.resume import Resume
from models.user import CandidateProfile
from services.gemini_service import GeminiService
from utils.logging_config import logger

class InterviewSimulator:
    def __init__(self, gemini_service: Optional[GeminiService] = None):
        self.gemini = gemini_service or GeminiService()

    def generate_interview_questions(self, job: Job, profile: Optional[CandidateProfile] = None) -> List[Dict[str, Any]]:
        """
        Generates role-specific behavioral, technical, and scenario questions tailored to the vacancy.
        """
        candidate_skills = (profile.skills if profile and profile.skills else []) or []
        skills_str = ", ".join(candidate_skills) if candidate_skills else "software engineering, problem solving, architecture"
        primary_skill = candidate_skills[0] if candidate_skills else "software engineering"

        prompt = f"""You are a principal bar raiser and senior engineering hiring manager.
Generate 4 high-yield interview questions for an interview for the role of {job.title} at {job.company}.
Tailor the questions to test the candidate's actual skills ({skills_str}) against the company's job requirements.

JOB DESCRIPTION:
{job.description[:3000]}

Format output as a valid JSON array of objects:
[
  {{
    "id": 1,
    "type": "Technical Architecture / Behavioral / System Design / Problem Solving",
    "question": "The interview question",
    "evaluation_criteria": "What the interviewer is specifically listening for (e.g. STAR method, trade-offs, ownership)",
    "star_guide": {{
      "situation": "Hint on establishing context",
      "task": "Hint on identifying the challenge",
      "action": "Hint on highlighting personal technical decisions",
      "result": "Hint on quantifying impact"
    }}
  }}
]
"""
        parsed = self.gemini.generate_json(prompt, timeout=8)
        if isinstance(parsed, dict):
            for k in ["questions", "interview_questions", "items", "data"]:
                if isinstance(parsed.get(k), list):
                    parsed = parsed[k]
                    break
        if isinstance(parsed, list) and len(parsed) > 0:
            return parsed

        # Deterministic fallback
        return [
            {
                "id": 1,
                "type": "Behavioral / Ownership",
                "question": f"Tell me about a complex project where you leveraged {primary_skill} under tight deadlines. How did you prioritize?",
                "evaluation_criteria": "Look for clear context, personal ownership, trade-off analysis, and measurable deliverables.",
                "star_guide": {
                    "situation": "Describe the business problem and timeline constraints.",
                    "task": "Explain your specific role and objective.",
                    "action": "Detail the technical choices and execution steps you took.",
                    "result": "State the measurable outcome (e.g. latency reduced by 30%, shipped on time)."
                }
            },
            {
                "id": 2,
                "type": "Technical Deep Dive",
                "question": f"In the context of {job.company}'s position as a leader in its space, how would you design a scalable system using modern architectural patterns?",
                "evaluation_criteria": "Assesses scalability, failure modes, data partitioning, and monitoring.",
                "star_guide": {
                    "situation": "Contextualize high-throughput requirements.",
                    "task": "Define reliability goals and service level objectives.",
                    "action": "Explain design patterns, caching, asynchronous queues.",
                    "result": "Highlight system resilience and cost efficiency."
                }
            },
            {
                "id": 3,
                "type": "Problem Solving & Debugging",
                "question": "Describe a scenario where a critical bug or performance bottleneck occurred in production. How did you diagnose and permanently resolve it?",
                "evaluation_criteria": "Methodical root cause analysis, logging, post-mortem hygiene.",
                "star_guide": {
                    "situation": "Production outage or latency spike under load.",
                    "task": "Identify root cause without disrupting active users.",
                    "action": "Instrument profiling, identify bottleneck, deploy patch.",
                    "result": "System restored with zero data loss and automated regression tests added."
                }
            },
            {
                "id": 4,
                "type": "Cultural Fit & Collaboration",
                "question": f"Why are you specifically excited about joining {job.company}, and how do your long-term engineering goals align with our team?",
                "evaluation_criteria": "Genuine company research, alignment with team mission, growth mindset.",
                "star_guide": {
                    "situation": "Current career inflection point and interest in the company domain.",
                    "task": "Desire to solve challenging domain problems.",
                    "action": "Active continuous learning and team mentoring.",
                    "result": "Long-term commitment to delivering company success."
                }
            }
        ]

    def evaluate_star_answer(self, question: str, user_answer: str, job: Job, duration_seconds: Optional[float] = None) -> Dict[str, Any]:
        """
        Evaluates a candidate's response according to the STAR method:
        - Situation (Context)
        - Task (Goal / Challenge)
        - Action (Specific execution & ownership)
        - Result (Measurable outcome)
        Also evaluates speech delivery cadence and filler words.
        """
        speech_analytics = self.analyze_speech_delivery(user_answer, duration_seconds)

        prompt = f"""You are an elite interview coach evaluating a candidate's answer for the role of {job.title} at {job.company}.
Evaluate the candidate's answer using the STAR method (Situation, Task, Action, Result).

QUESTION:
\"{question}\"

CANDIDATE'S ANSWER:
\"{user_answer}\"

Output MUST be a single valid JSON object adhering to this schema:
{{
  "overall_score": 82,
  "star_breakdown": {{
    "situation": {{"score": 85, "feedback": "Evaluation of context setting"}},
    "task": {{"score": 80, "feedback": "Evaluation of challenge clarity"}},
    "action": {{"score": 85, "feedback": "Evaluation of personal action verbs and technical ownership"}},
    "result": {{"score": 75, "feedback": "Evaluation of whether outcomes were quantified and measurable"}}
  }},
  "strengths": [
    "Clear strength point 1",
    "Clear strength point 2"
  ],
  "areas_for_improvement": [
    "Specific area to improve (e.g., more numbers, clearer technical trade-offs)",
    "Another improvement suggestion"
  ],
  "improved_exemplar_answer": "A revised, highly polished version of the candidate's answer demonstrating ideal STAR formulation."
}}
"""
        parsed = self.gemini.generate_json(prompt, timeout=8)
        if isinstance(parsed, dict) and "overall_score" in parsed:
            parsed["speech_analytics"] = speech_analytics
            return parsed

        # Deterministic fallback evaluation
        length = len(user_answer.split())
        has_numbers = any(char.isdigit() for char in user_answer)
        score = min(85, max(50, length * 2 + (15 if has_numbers else 0)))

        return {
            "overall_score": score,
            "star_breakdown": {
                "situation": {"score": 75, "feedback": "Good context provided. Try to specify the exact team and project stakes."},
                "task": {"score": 70, "feedback": "Clearly state the primary challenge you were directly responsible for solving."},
                "action": {"score": 80, "feedback": "Strong focus on your personal technical implementation and engineering choices."},
                "result": {"score": 65 if not has_numbers else 80, "feedback": "Quantify the outcome with percentages, revenue, latency, or throughput metrics."}
            },
            "strengths": [
                "Clear communicative tone and relevance to the question prompt",
                "Demonstrates practical hands-on problem solving orientation"
            ],
            "areas_for_improvement": [
                "Include concrete metrics to validate the outcome (e.g. 40% performance gain)",
                "Explicitly describe alternatives considered before choosing your approach"
            ],
            "improved_exemplar_answer": f"In my recent role, our team faced a major challenge where (Situation)... My specific responsibility was to (Task)... I spearheaded the architecture by (Action)... As a direct result, we achieved (Result: e.g. 99.9% uptime and a 35% reduction in latency).",
            "speech_analytics": speech_analytics
        }

    def analyze_speech_delivery(self, answer_text: str, duration_seconds: Optional[float] = None) -> Dict[str, Any]:
        """
        Analyzes spoken speech delivery: detects filler words, speaking cadence/WPM, and delivery clarity.
        """
        import re

        text_clean = (answer_text or "").lower()
        words = re.findall(r'\b[a-z\']+\b', text_clean)
        word_count = len(words)

        FILLER_WORDS = [
            "um", "uh", "like", "you know", "basically", "actually",
            "literally", "sort of", "kind of", "i mean", "honestly"
        ]

        detected_fillers = {}
        total_filler_count = 0
        for filler in FILLER_WORDS:
            pattern = r'\b' + re.escape(filler) + r'\b'
            matches = len(re.findall(pattern, text_clean))
            if matches > 0:
                detected_fillers[filler] = matches
                total_filler_count += matches

        filler_ratio = (total_filler_count / word_count * 100) if word_count > 0 else 0.0

        # WPM Calculation
        if duration_seconds and duration_seconds > 0:
            wpm = round((word_count / duration_seconds) * 60, 1)
        else:
            # Assume normal conversational reading pace ~130 WPM
            wpm = 135.0

        if wpm < 110:
            pace_rating = "Slightly Deliberate / Slow"
            pace_tip = "Try to maintain steady momentum to keep the interviewer fully engaged."
        elif 110 <= wpm <= 160:
            pace_rating = "Optimal Cadence"
            pace_tip = "Excellent pacing. Clear and easy for the interviewer to digest."
        else:
            pace_rating = "Fast Paced"
            pace_tip = "Slow down slightly and pause after key milestones to let technical points sink in."

        # Delivery score (deduct for excessive fillers or extreme pacing)
        delivery_score = max(50, min(100, int(95 - (filler_ratio * 4) - (abs(wpm - 135) * 0.15))))

        return {
            "word_count": word_count,
            "estimated_wpm": wpm,
            "pace_rating": pace_rating,
            "pace_tip": pace_tip,
            "total_filler_words": total_filler_count,
            "filler_ratio_percent": round(filler_ratio, 1),
            "detected_fillers": detected_fillers,
            "delivery_score": delivery_score
        }

    def generate_followup_question(self, question: str, user_answer: str, job: Job) -> Dict[str, Any]:
        """
        Generates an adaptive, probing follow-up question based on the candidate's actual answer.
        Simulates an experienced hiring manager digging deeper into trade-offs, architecture, or edge cases.
        """
        prompt = f"""You are a principal bar raiser and senior hiring manager interviewing for {job.title} at {job.company}.
The candidate just answered the initial interview question. Formulate a challenging, realistic follow-up question that directly references and probes their specific answer.

ORIGINAL QUESTION:
"{question}"

CANDIDATE'S ANSWER:
"{user_answer}"

Output MUST be a single valid JSON object:
{{
  "followup_question": "Challenging follow-up question probing a specific decision, metric, or failure mode they mentioned",
  "interviewer_intent": "Why the interviewer is asking this (e.g. testing resilience under failure, understanding trade-offs)",
  "suggested_focus": "Key technical point candidate should address in their response"
}}
"""
        parsed = self.gemini.generate_json(prompt, timeout=8)
        if isinstance(parsed, dict) and "followup_question" in parsed:
            return parsed

        # Fallback dynamic follow-up
        answer_words = user_answer.lower().split()
        if any(w in answer_words for w in ["database", "sql", "redis", "cache", "latency", "storage"]):
            return {
                "followup_question": "You mentioned performance and data handling in your answer. How did you handle consistency guarantees, cache invalidation, and failure modes when traffic spiked?",
                "interviewer_intent": "Assessing system resilience, trade-off awareness, and disaster recovery planning.",
                "suggested_focus": "Explain read/write consistency, timeout policies, circuit breakers, and fallback strategies."
            }
        elif any(w in answer_words for w in ["team", "conflict", "stakeholder", "deadline", "product"]):
            return {
                "followup_question": "You touched upon collaboration and timelines. If a senior peer or stakeholder fundamentally disagreed with your technical proposal, how did you resolve the deadlock without sacrificing delivery velocity?",
                "interviewer_intent": "Evaluating conflict resolution, persuasion through data, and emotional intelligence.",
                "suggested_focus": "Highlight objective proof-of-concept benchmarks, active listening, and customer-first alignment."
            }
        else:
            return {
                "followup_question": f"Looking back at your approach for that initiative, what is one major architectural trade-off or alternative you considered, and why was your chosen solution optimal for {job.company}'s scale?",
                "interviewer_intent": "Probing technical depth, architectural reflection, and decision-making rigor.",
                "suggested_focus": "Contrast your chosen path against at least one viable alternative and cite concrete trade-offs."
            }

    def generate_questions_to_ask_interviewer(self, job: Job, profile: Optional[CandidateProfile] = None) -> List[Dict[str, Any]]:
        """
        Generates high-impact, insightful questions for the candidate to ask the interviewer.
        Shows genuine research, technical curiosity, and executive maturity.
        """
        prompt = f"""You are an elite interview coach preparing a candidate for an interview for {job.title} at {job.company}.
Generate 5 strategic, high-impact questions the candidate should ask the interviewer at the end of the round.
Avoid generic questions; tailor them specifically to {job.company}'s engineering scale, culture, and business domain.

Format output as a valid JSON array of objects:
[
  {{
    "id": 1,
    "category": "Engineering Culture / Architecture & Scale / Product Roadmap / First 90 Days / Team Velocity",
    "question": "The exact question to ask the interviewer",
    "why_ask": "What this question signals to the interviewer and what valuable insight it reveals to the candidate"
  }}
]
"""
        parsed = self.gemini.generate_json(prompt, timeout=8)
        if isinstance(parsed, dict):
            for k in ["questions", "items", "data"]:
                if isinstance(parsed.get(k), list):
                    parsed = parsed[k]
                    break
        if isinstance(parsed, list) and len(parsed) >= 3:
            return parsed

        # Deterministic high-yield fallback
        return [
            {
                "id": 1,
                "category": "Architecture & Technical Debt",
                "question": f"At {job.company}'s current trajectory, what is the single biggest architectural challenge or technical debt bottleneck your team is working to overcome this quarter?",
                "why_ask": "Demonstrates that you think about long-term system maintainability and want to hit the ground running solving real pain points."
            },
            {
                "id": 2,
                "category": "Team Velocity & Culture",
                "question": f"How does the team balance shipping customer-facing features rapidly with engineering excellence, testing rigor, and infrastructure refactoring?",
                "why_ask": "Reveals whether engineering culture is sustainable and shows you care about high standards."
            },
            {
                "id": 3,
                "category": "First 90 Days Success Metrics",
                "question": f"If I join as {job.title}, what does exceptional performance look like in my first 90 days, and what is one milestone that would make you say 'we made a fantastic hire'?",
                "why_ask": "Demonstrates focus on tangible business outcomes and provides clear clarity on expectations."
            },
            {
                "id": 4,
                "category": "Engineering Autonomy & Decision Making",
                "question": "How are architectural and toolchain decisions made across the team? Do individual engineers have autonomy to propose RFCs and drive tech adoption?",
                "why_ask": "Signals technical leadership and an ownership mindset."
            },
            {
                "id": 5,
                "category": "Product Roadmap & Business Impact",
                "question": f"What upcoming initiative or product capability at {job.company} are you personally most excited to see the engineering team ship over the next 12 months?",
                "why_ask": "Ends the interview on a high, inspiring note and engages the interviewer's personal passion."
            }
        ]

    def generate_interview_cheat_sheet(self, job: Job, profile: Optional[CandidateProfile] = None) -> Dict[str, Any]:
        """
        Assembles a comprehensive, 1-page interview prep cheat sheet for rapid pre-interview review.
        """
        candidate_skills = (profile.skills if profile and profile.skills else []) or []
        skills_str = ", ".join(candidate_skills[:6]) if candidate_skills else "system design, problem solving"

        questions = self.generate_interview_questions(job, profile)
        reverse_questions = self.generate_questions_to_ask_interviewer(job, profile)

        return {
            "company": job.company,
            "role_title": job.title,
            "location": job.location or "Global / Remote",
            "work_mode": job.work_mode,
            "experience_level": job.experience_level,
            "candidate_skills": candidate_skills,
            "core_talking_points": [
                f"Anchor technical examples around your experience with {skills_str}.",
                "State measurable results in the first 30 seconds of every STAR story.",
                "Use 'I architected / I delivered' rather than ambiguous team references.",
                f"Reference {job.company}'s market leadership and specific industry challenges."
            ],
            "prepared_questions": questions,
            "questions_for_interviewer": reverse_questions,
            "pre_interview_checklist": [
                "Test microphone, camera, and quiet environment 15 minutes before the call.",
                "Have 2 quantified impact stories (latency, revenue, uptime, or users served) ready in mind.",
                "Review the 3 strategic reverse-questions you plan to ask the interviewer.",
                "Keep a clean glass of water and notepad within reach."
            ]
        }

