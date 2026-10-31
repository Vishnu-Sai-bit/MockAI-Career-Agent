import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

class CareerAnalyticsService:
    """
    Computes application funnel conversion rates, identifies hiring bottlenecks,
    and generates 1-click Google Calendar / .ics event files for interviews.
    """

    def compute_funnel_metrics(self, app_counts: Dict[str, int]) -> Dict[str, Any]:
        """
        Analyzes the candidate's conversion funnel across application stages:
        saved -> applied -> interviewing -> offer
        """
        saved = app_counts.get("saved", 0)
        applied = app_counts.get("applied", 0)
        interviewing = app_counts.get("interviewing", 0)
        offer = app_counts.get("offer", 0)
        rejected = app_counts.get("rejected", 0)

        total_active_pipeline = applied + interviewing + offer

        # Conversion rates
        applied_to_interview_rate = round((interviewing + offer) / applied * 100, 1) if applied > 0 else 0.0
        interview_to_offer_rate = round(offer / (interviewing + offer) * 100, 1) if (interviewing + offer) > 0 else 0.0

        # Bottleneck diagnosis
        diagnostics = []
        if applied >= 5 and applied_to_interview_rate < 15.0:
            diagnostics.append({
                "type": "warning",
                "stage": "Resume & ATS Screening",
                "message": "Interview conversion rate is below 15%. Recommend tailoring your resume and raising your ATS match score above 80%."
            })
        elif applied >= 3:
            diagnostics.append({
                "type": "success",
                "stage": "Resume Screening",
                "message": f"Solid interview conversion rate ({applied_to_interview_rate}%). Your resume keywords are effectively reaching recruiters."
            })

        if interviewing >= 3 and interview_to_offer_rate < 20.0:
            diagnostics.append({
                "type": "warning",
                "stage": "Interview Rounds",
                "message": "Offer rate is below industry average (25%). Rehearse with our STAR Mock Interview simulator to sharpen impact metrics."
            })

        return {
            "stages": [
                {"name": "Saved Roles", "count": saved, "icon": "bi-bookmark"},
                {"name": "Applied", "count": applied, "icon": "bi-send-check"},
                {"name": "Interviewing", "count": interviewing, "icon": "bi-mic"},
                {"name": "Offers Extended", "count": offer, "icon": "bi-trophy"}
            ],
            "total_in_pipeline": total_active_pipeline,
            "applied_to_interview_rate": applied_to_interview_rate,
            "interview_to_offer_rate": interview_to_offer_rate,
            "diagnostics": diagnostics
        }

    def generate_calendar_links(self, job_title: str, company: str, event_time: datetime, event_type: str = "Interview") -> Dict[str, Any]:
        """
        Creates Google Calendar 1-click web URL and standard iCalendar (.ics) format.
        """
        title = f"{event_type}: {job_title} at {company}"
        description = f"AI Job Agent preparation milestone for {job_title} at {company}. Review STAR answers and company technical portfolio."
        location = "Online / Video Call"

        # ISO format for Google Calendar: YYYYMMDDTHHMMSSZ
        start_utc = event_time.strftime("%Y%m%dT%H%M%SZ")
        end_time = event_time + timedelta(hours=1)
        end_utc = end_time.strftime("%Y%m%dT%H%M%SZ")

        # Google Calendar Web URL
        params = {
            "action": "TEMPLATE",
            "text": title,
            "details": description,
            "location": location,
            "dates": f"{start_utc}/{end_utc}"
        }
        google_url = f"https://calendar.google.com/calendar/render?{urllib.parse.urlencode(params)}"

        # iCalendar (.ics) content
        now_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//AI Job Agent//Career Calendar 2.0//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
BEGIN:VEVENT
UID:{company.replace(' ', '_')}_{job_title.replace(' ', '_')}_{start_utc}@aijobagent.local
DTSTAMP:{now_utc}
DTSTART:{start_utc}
DTEND:{end_utc}
SUMMARY:{title}
DESCRIPTION:{description}
LOCATION:{location}
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""

        return {
            "google_calendar_url": google_url,
            "ics_content": ics_content,
            "event_title": title,
            "formatted_time": event_time.strftime("%A, %B %d, %Y at %I:%M %p UTC")
        }

    def compute_user_activity_streak(self, user_id: int) -> Dict[str, Any]:
        """
        Computes the candidate's activity and consistency heatmap across the last 70 days (10 weeks):
        - Applications tracked / updated
        - Mock interview practice sessions
        - Saved job bookmarks
        Returns heatmap weeks, current streak, longest streak, total actions, and consistency metrics.
        """
        from datetime import date, timedelta
        from collections import defaultdict
        from models.application import Application
        from models.interview import InterviewSession
        from models.job_match import SavedJob

        today = date.today()
        # 70 days (10 weeks)
        start_date = today - timedelta(days=69)

        activity_map = defaultdict(lambda: {"count": 0, "details": []})

        # 1. Applications
        try:
            apps = Application.query.filter(Application.user_id == user_id).all()
            for app in apps:
                if app.created_at:
                    dt = app.created_at.date()
                    if dt >= start_date:
                        activity_map[dt]["count"] += 1
                        company = app.job.company if app.job else "Target Role"
                        activity_map[dt]["details"].append(f"Applied: {company}")
        except Exception:
            pass

        # 2. Mock Interviews
        try:
            interviews = InterviewSession.query.filter(InterviewSession.user_id == user_id).all()
            for iv in interviews:
                if iv.created_at:
                    dt = iv.created_at.date()
                    if dt >= start_date:
                        activity_map[dt]["count"] += 2  # Practice sessions count with high weight
                        activity_map[dt]["details"].append(f"Mock Call: {iv.company}")
        except Exception:
            pass

        # 3. Saved Jobs
        try:
            saved = SavedJob.query.filter(SavedJob.user_id == user_id).all()
            for sj in saved:
                if sj.saved_at:
                    dt = sj.saved_at.date()
                    if dt >= start_date:
                        activity_map[dt]["count"] += 1
                        activity_map[dt]["details"].append("Saved job vacancy")
        except Exception:
            pass

        # Build day items
        days_list = []
        curr = start_date
        while curr <= today:
            cnt = activity_map[curr]["count"]
            if cnt == 0:
                color = "#f1f5f9"
                level = 0
            elif cnt == 1:
                color = "#ede9fe"
                level = 1
            elif cnt in [2, 3]:
                color = "#c4b5fd"
                level = 2
            elif cnt in [4, 5]:
                color = "#a855f7"
                level = 3
            else:
                color = "#7c3aed"
                level = 4

            details = "; ".join(activity_map[curr]["details"][:3]) if activity_map[curr]["details"] else "No activities logged"

            days_list.append({
                "date": curr.strftime("%b %d, %Y"),
                "date_short": curr.strftime("%b %d"),
                "day_name": curr.strftime("%a"),
                "count": cnt,
                "level": level,
                "color": color,
                "details": details
            })
            curr += timedelta(days=1)

        # Calculate streaks
        current_streak = 0
        check = today
        while check >= start_date:
            if activity_map[check]["count"] > 0:
                current_streak += 1
                check -= timedelta(days=1)
            else:
                if check == today:
                    check -= timedelta(days=1)
                    continue
                break

        longest_streak = 0
        temp_streak = 0
        s_day = start_date
        while s_day <= today:
            if activity_map[s_day]["count"] > 0:
                temp_streak += 1
                longest_streak = max(longest_streak, temp_streak)
            else:
                temp_streak = 0
            s_day += timedelta(days=1)

        total_actions = sum(item["count"] for item in activity_map.values())
        active_days = sum(1 for item in activity_map.values() if item["count"] > 0)
        consistency_pct = round((active_days / max(1, len(days_list))) * 100)

        # Group days into 10 columns (weeks)
        weeks = []
        cur_week = []
        for d in days_list:
            cur_week.append(d)
            if len(cur_week) == 7:
                weeks.append(cur_week)
                cur_week = []
        if cur_week:
            weeks.append(cur_week)

        return {
            "weeks": weeks,
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "total_actions": total_actions,
            "active_days": active_days,
            "consistency_pct": consistency_pct
        }
