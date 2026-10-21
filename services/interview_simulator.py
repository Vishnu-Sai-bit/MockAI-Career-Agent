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

