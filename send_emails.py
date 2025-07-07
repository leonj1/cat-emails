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
                         weekly_trends: Optional[Dict[str, Any]] = None,
                         charts: Optional[Dict[str, str]] = None) -> str:
        """
        Render the email HTML using the template.
        
        Args:
            report: The summary report data
            performance_metrics: Performance metrics data
            weekly_trends: Weekly trend data (for weekly reports)
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
            weekly_trends=weekly_trends,
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
                          weekly_trends: Optional[Dict[str, Any]] = None,
                          charts: Optional[Dict[str, str]] = None) -> bool:
        """
        Send the summary report email.
        
        Args:
            report: The summary report to send
            recipient_email: Email address to send to
            performance_metrics: Performance metrics data
            weekly_trends: Weekly trend data (for weekly reports)
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
                report, performance_metrics, weekly_trends, charts
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
    
    # Initialize services
    summary_service = EmailSummaryService()
    email_sender = EmailSender()
    
    # Generate summary
    report = summary_service.generate_summary(report_type)
    if not report:
        logger.warning("No data to summarize")
        return
    
    # Generate performance metrics
    performance_metrics = summary_service.get_performance_metrics()
    
    # Generate weekly trends for weekly reports
    weekly_trends = None
    if report_type == "Weekly":
        # Calculate weekly trends
        # This would require historical data from the past two weeks
        # For now, we'll use placeholder data
        weekly_trends = {
            'total_change': 12.5,  # 12.5% increase
            'deletion_rate_change': -3.2  # 3.2% decrease in deletion rate
        }
    
    # Generate charts
    chart_generator = ChartGenerator()
    charts = chart_generator.generate_all_charts(
        report, 
        performance_metrics=performance_metrics,
        weekly_data=None  # Would need historical data for weekly charts
    )
    
    # Send email
    if email_sender.send_summary_email(
        report, recipient_email, performance_metrics, weekly_trends, charts
    ):
        # Clear tracked data after successful send
        summary_service.clear_tracked_data()
        logger.info(f"{report_type} summary sent and data cleared")
    else:
        logger.error("Failed to send summary email, keeping tracked data")


if __name__ == "__main__":
    # For testing, allow passing recipient email as argument
    if len(sys.argv) > 1:
        os.environ['GMAIL_EMAIL'] = sys.argv[1]
    
    main()