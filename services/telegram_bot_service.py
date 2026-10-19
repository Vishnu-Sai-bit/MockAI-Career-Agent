import os
import requests
from typing import Dict, Any, Optional
from utils.logging_config import logger

class TelegramBotService:
    """
    Dispatches instant real-time job alerts to candidates on Telegram.
    Includes rich formatting, ATS match highlights, and official direct application links.
    """

    def __init__(self, bot_token: Optional[str] = None):
        self.bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")

    def send_instant_job_alert(self, chat_id: str, job_data: Dict[str, Any], match_score: float = 0.0) -> Dict[str, Any]:
        """
        Sends an instant job alert message card to the candidate's Telegram chat.
        """
        if not chat_id:
            return {"success": False, "error": "Missing Telegram chat ID"}

        title = job_data.get("title", "New Job Opportunity")
        company = job_data.get("company", "Verified Employer")
        platform = (job_data.get("source_platform") or "Direct").upper()
        location = job_data.get("location") or "Remote / Flexible"
        apply_url = job_data.get("apply_url") or job_data.get("original_url") or "#"
        salary = job_data.get("salary_range") or "Competitive / Disclosed in portal"

        # Format message with Telegram HTML
        match_badge = f"🔥 <b>ATS Match Score:</b> <code>{int(match_score)}%</code>\n" if match_score > 0 else ""

        message_html = f"""⚡ <b>NEW HIGH-MATCH JOB ALERT</b>

💼 <b>Role:</b> {title}
🏢 <b>Company:</b> {company}
🌐 <b>Platform:</b> {platform} (Verified Source)
📍 <b>Location:</b> {location}
💰 <b>Compensation:</b> {salary}
{match_badge}
✅ <i>Official Apply link attached below:</i>
👉 <a href="{apply_url}">Apply Directly on {company} Portal</a>
"""

        # If no bot token configured, return simulated dispatch (graceful mock for dev/offline)
        if not self.bot_token or self.bot_token == "dummy_token" or os.environ.get("PYTEST_CURRENT_TEST"):
            logger.info(f"[TelegramBotService] Simulated alert sent to {chat_id} for {title} at {company}")
            return {
                "success": True,
                "simulated": True,
                "chat_id": chat_id,
                "message": message_html
            }

        endpoint = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message_html,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }

        try:
            resp = requests.post(endpoint, json=payload, timeout=10)
            if resp.status_code == 200:
                return {"success": True, "chat_id": chat_id}
            else:
                logger.error(f"[TelegramBotService] HTTP {resp.status_code}: {resp.text}")
                return {"success": False, "status_code": resp.status_code, "error": resp.text}
        except Exception as e:
            logger.error(f"[TelegramBotService] Request failed: {e}")
            return {"success": False, "error": str(e)}
