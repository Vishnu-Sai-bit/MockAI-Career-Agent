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
