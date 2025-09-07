from datetime import datetime, time as datetime_time
import pytz
from typing import Literal

class SummaryScheduleService:
    """Service that determines whether it's time to send summary reports.
    Defaults to US Eastern Time and a 30-minute window around configured times.
    """

    def __init__(self, tz_name: str = 'America/New_York', window_minutes: int = 30):
        self.tz = pytz.timezone(tz_name)
        self.window_minutes = window_minutes

    def should_send_summary(
        self,
        last_morning_sent: datetime,
        last_evening_sent: datetime,
        last_weekly_sent: datetime,
        morning_hour: int,
        morning_minute: int,
        evening_hour: int,
        evening_minute: int,
    ) -> Literal["morning", "evening", "weekly", ""]:
        """Check if it's time to send a summary report.

        Returns one of: "morning", "evening", "weekly", or "" if no report needed.
        """
        # Current time in configured TZ
        now_tz = datetime.now(self.tz)
        current_time = now_tz.time()
        current_day = now_tz.strftime('%A')

        # Convert last sent times to configured TZ for comparison
        if last_morning_sent.tzinfo is None:
            last_morning_sent = pytz.utc.localize(last_morning_sent).astimezone(self.tz)
        else:
            last_morning_sent = last_morning_sent.astimezone(self.tz)

        if last_evening_sent.tzinfo is None:
            last_evening_sent = pytz.utc.localize(last_evening_sent).astimezone(self.tz)
        else:
            last_evening_sent = last_evening_sent.astimezone(self.tz)

        if last_weekly_sent.tzinfo is None:
            last_weekly_sent = pytz.utc.localize(last_weekly_sent).astimezone(self.tz)
        else:
            last_weekly_sent = last_weekly_sent.astimezone(self.tz)

        # Morning/Evening report time windows
        morning_start = datetime_time(morning_hour, morning_minute)
        morning_end = datetime_time(morning_hour, min(morning_minute + self.window_minutes, 59))

        evening_start = datetime_time(evening_hour, evening_minute)
        evening_end = datetime_time(evening_hour, min(evening_minute + self.window_minutes, 59))

        # Weekly report (Friday evening window)
        if current_day == 'Friday' and evening_start <= current_time <= evening_end:
            days_since_weekly = (now_tz.date() - last_weekly_sent.date()).days
            if days_since_weekly >= 7:
                return "weekly"

        # Morning window (if not already sent today)
        if morning_start <= current_time <= morning_end:
            if last_morning_sent.date() < now_tz.date():
                return "morning"

        # Evening window (if not already sent today)
        if evening_start <= current_time <= evening_end:
            if last_evening_sent.date() < now_tz.date():
                return "evening"

        return ""

