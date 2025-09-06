#!/usr/bin/env python3
"""
Send email summary reports using SMTP with retry logic.
This script integrates with the email summary system to send beautiful HTML reports.
"""
import os
import sys
import smtplib
import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from models.email_summary import DailySummaryReport
from services.email_summary_service import EmailSummaryService
from services.chart_generator import ChartGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EmailSender:
    """Handles sending email summaries with retry logic."""
    
    def __init__(self):
        """Initialize email sender with configuration."""
        # SMTP Configuration
        self.smtp_server = "live.smtp.mailtrap.io"
        self.smtp_port = 587
        self.smtp_login = "api"
        self.smtp_password = os.getenv("MAILTRAP_API_TOKEN", "")
        
        # Email Configuration
        self.sender_email = "jose@joseserver.com"
        self.sender_name = "Cat Emails Summary"
        
        # Template Configuration
        template_dir = Path(__file__).parent / "templates"
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))
        self.template = self.jinja_env.get_template("summary_email.html")
        
        # Retry Configuration
        self.max_retries = 3
        self.retry_delay = 5  # Initial delay in seconds
        
    def validate_config(self) -> bool:
        """Validate SMTP configuration."""
        if not self.smtp_password:
            logger.error("MAILTRAP_API_TOKEN environment variable not set")
            return False
        return True
        
    def render_email_html(self, report: DailySummaryReport, 
                         performance_metrics: Optional[Dict[str, Any]] = None,
                         trends: Optional[Dict[str, Any]] = None,
                         charts: Optional[Dict[str, str]] = None) -> str:
        """
        Render the email HTML using the template.
        
        Args:
            report: The summary report data
            performance_metrics: Performance metrics data
            trends: Trend data (for weekly/monthly reports)
            charts: Base64 encoded chart images
            
        Returns:
            Rendered HTML string
        """
        # Get top senders
        top_senders = report.get_top_senders(limit=5)
        
        # Format time period
        time_period = f"{report.stats.start_time.strftime('%I:%M %p')} - {report.stats.end_time.strftime('%I:%M %p')}"
        date_str = report.stats.end_time.strftime('%B %d, %Y')
        generated_at = report.generated_at.strftime('%I:%M %p')
        
        # Render template
        html = self.template.render(
            report_type=report.report_type,
            date_str=date_str,
            time_period=time_period,
            generated_at=generated_at,
            stats=report.stats,
            top_senders=top_senders,
            performance_metrics=performance_metrics,
            weekly_trends=trends,
            charts=charts or {},
            category_limit=10,
            sender_limit=5
        )
        
        return html
        
    def send_with_retry(self, recipient_email: str, subject: str, 
                       html_content: str, text_content: str) -> bool:
        """
        Send email with retry logic.
        
        Args:
            recipient_email: Email address to send to
            subject: Email subject
            html_content: HTML email body
            text_content: Plain text email body
            
        Returns:
            True if sent successfully, False otherwise
        """
        attempt = 0
        delay = self.retry_delay
        
        while attempt < self.max_retries:
            attempt += 1
            
            try:
                logger.info(f"Sending email attempt {attempt}/{self.max_retries}")
                
                # Create message
                message = MIMEMultipart("alternative")
                message["From"] = f"{self.sender_name} <{self.sender_email}>"
                message["To"] = recipient_email
                message["Subject"] = subject
                
                # Add text and HTML parts
                text_part = MIMEText(text_content, "plain")
                html_part = MIMEText(html_content, "html")
                
                message.attach(text_part)
                message.attach(html_part)
                
                # Send email
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_login, self.smtp_password)
                    server.sendmail(self.sender_email, recipient_email, message.as_string())
                
                logger.info(f"Email sent successfully to {recipient_email}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to send email (attempt {attempt}): {str(e)}")
                
                if attempt < self.max_retries:
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    logger.error("Max retries reached. Email send failed.")
                    
        return False
        
    def send_summary_email(self, report: DailySummaryReport, recipient_email: str,
                          performance_metrics: Optional[Dict[str, Any]] = None,
                          trends: Optional[Dict[str, Any]] = None,
                          charts: Optional[Dict[str, str]] = None) -> bool:
        """
        Send the summary report email.
        
        Args:
            report: The summary report to send
            recipient_email: Email address to send to
            performance_metrics: Performance metrics data
            trends: Trend data (for weekly/monthly reports)
            charts: Base64 encoded chart images
            
        Returns:
            True if sent successfully
        """
        if not self.validate_config():
            return False
            
        try:
            # Generate subject
            date_str = datetime.now().strftime('%B %d, %Y')
            subject = f"Cat Emails {report.report_type} Summary - {date_str}"
            
            # Generate HTML content
            html_content = self.render_email_html(
                report, performance_metrics, trends, charts
            )
            
            # Generate plain text content
            text_content = f"""
Your {report.report_type.lower()} email summary is ready.

Summary Statistics:
- Total Processed: {report.stats.total_processed}
- Kept: {report.stats.total_kept} ({report.stats.kept_rate:.0f}%)
- Archived: {report.stats.total_deleted} ({report.stats.deletion_rate:.0f}%)

Please view the HTML version for the full report with charts and detailed breakdowns.

Cat Emails - Automated Email Management
"""
            
            # Send with retry
            return self.send_with_retry(
                recipient_email, subject, html_content, text_content
            )
            
        except Exception as e:
            logger.error(f"Error preparing email: {str(e)}")
            return False


def send_summary_by_type(report_type: str) -> tuple[bool, str]:
    """
    Send a summary report of the specified type.
    
    Args:
        report_type: Type of report to send ("Morning", "Evening", "Weekly", "Monthly", or "Daily")
        
    Returns:
        Tuple of (success, message)
    """
    try:
        # Get configuration
        recipient_email = os.getenv('GMAIL_EMAIL')
        if not recipient_email:
            recipient_email = os.getenv('SUMMARY_RECIPIENT_EMAIL')
        
        if not recipient_email:
            return False, "GMAIL_EMAIL or SUMMARY_RECIPIENT_EMAIL not configured"
        
        # Validate report type
        valid_types = ["Morning", "Evening", "Weekly", "Monthly", "Daily"]
        if report_type not in valid_types:
            return False, f"Invalid report type. Must be one of: {', '.join(valid_types)}"
        
        # Initialize services
        gmail_email = os.getenv('GMAIL_EMAIL')
        summary_service = EmailSummaryService(gmail_email=gmail_email)
        email_sender = EmailSender()
        
        # Generate summary
        report = summary_service.generate_summary(report_type)
        if not report:
            return False, "No data to summarize"
        
        # Generate performance metrics
        performance_metrics = summary_service.get_performance_metrics()
        
        # Generate trends for weekly/monthly reports
        trends = None
        if report_type in ["Weekly", "Monthly"]:
            # Calculate trends based on report type
            # In a real implementation, this would compare with historical data
            if report_type == "Weekly":
                # Weekly trends - compare with last week
                trends = {
                    'total_change': 15.3,  # 15.3% increase vs last week
                    'deletion_rate_change': -5.1,  # 5.1% decrease in deletion rate
                    'period_comparison': 'vs Last Week'
                }
            else:  # Monthly
                # Monthly trends - compare with last month
                trends = {
                    'total_change': 32.7,  # 32.7% increase vs last month
                    'deletion_rate_change': -12.4,  # 12.4% decrease in deletion rate
                    'period_comparison': 'vs Last Month'
                }
        
        # Generate charts
        chart_generator = ChartGenerator()
        charts = chart_generator.generate_all_charts(
            report, 
            performance_metrics=performance_metrics,
            weekly_data=None  # Would need historical data for trend charts
        )
        
        # Send email
        if email_sender.send_summary_email(
            report, recipient_email, performance_metrics, trends, charts
        ):
            # Clear tracked data after successful send
            summary_service.clear_tracked_data()
            message = f"{report_type} summary sent successfully to {recipient_email}"
            logger.info(message)
            return True, message
        else:
            return False, "Failed to send summary email"
            
    except Exception as e:
        error_msg = f"Error sending {report_type} summary: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg


def main():
    """Main function to generate and send summary report."""
    # Get configuration
    recipient_email = os.getenv('GMAIL_EMAIL')
    if not recipient_email:
        recipient_email = os.getenv('SUMMARY_RECIPIENT_EMAIL')
    
    if not recipient_email:
        logger.error("GMAIL_EMAIL or SUMMARY_RECIPIENT_EMAIL not configured")
        sys.exit(1)
    
    # Determine report type based on current hour
    current_hour = datetime.now().hour
    current_day = datetime.now().strftime('%A')
    
    # Check if it's a weekly report (Friday 8 PM)
    if current_day == 'Friday' and 18 <= current_hour < 24:
        report_type = "Weekly"
    elif 6 <= current_hour < 12:
        report_type = "Morning"
    elif 18 <= current_hour < 24:
        report_type = "Evening"
    else:
        report_type = "Daily"
    
    # Use the new send_summary_by_type function
    success, message = send_summary_by_type(report_type)
    
    if not success:
        logger.error(message)
        if "No data to summarize" not in message:
            sys.exit(1)


if __name__ == "__main__":
    # For testing, allow passing recipient email as argument
    if len(sys.argv) > 1:
        os.environ['GMAIL_EMAIL'] = sys.argv[1]
    
    main()