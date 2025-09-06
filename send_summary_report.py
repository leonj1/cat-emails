#!/usr/bin/env python3
"""
Send email summary reports using the configured email provider.
"""
import os
import sys
import logging
from datetime import datetime
from typing import Optional

from models.email_models import EmailAddress, EmailMessage
from models.email_summary import DailySummaryReport
from email_providers.mailfrom_dev import MailfromDevProvider, MailfromDevConfig
from services.email_summary_service import EmailSummaryService


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_html_report(report: DailySummaryReport) -> str:
    """
    Generate beautiful HTML content for the summary report.
    
    Args:
        report: The summary report data
        
    Returns:
        HTML string for the email
    """
    # Get top senders
    top_senders = report.get_top_senders(limit=5)
    
    # Format time period
    time_period = f"{report.stats.start_time.strftime('%I:%M %p')} - {report.stats.end_time.strftime('%I:%M %p')}"
    date_str = report.stats.end_time.strftime('%B %d, %Y')
    
    # Build category rows
    category_rows = ""
    for cat in report.stats.top_categories[:10]:
        category_rows += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #eee;">{cat.category}</td>
            <td style="padding: 12px; border-bottom: 1px solid #eee; text-align: center;">{cat.count}</td>
            <td style="padding: 12px; border-bottom: 1px solid #eee; text-align: center;">{cat.percentage}%</td>
        </tr>
        """
    
    # Build sender rows
    sender_rows = ""
    for sender_data in top_senders:
        sender_rows += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #eee;">{sender_data['sender']}</td>
            <td style="padding: 12px; border-bottom: 1px solid #eee; text-align: center;">{sender_data['count']}</td>
            <td style="padding: 12px; border-bottom: 1px solid #eee; text-align: center;">{sender_data['percentage']:.1f}%</td>
        </tr>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Email Summary Report</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; background-color: #f5f7fa;">
        <div style="max-width: 700px; margin: 40px auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); overflow: hidden;">
            
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 30px; text-align: center;">
                <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 600;">
                    📧 {report.report_type} Email Summary
                </h1>
                <p style="margin: 10px 0 0 0; color: #e0e0ff; font-size: 16px;">
                    {date_str} • {time_period}
                </p>
            </div>
            
            <!-- Summary Stats -->
            <div style="padding: 40px 30px;">
                <div style="display: flex; justify-content: space-around; margin-bottom: 40px; text-align: center;">
                    <div>
                        <h2 style="margin: 0; color: #667eea; font-size: 36px;">{report.stats.total_processed}</h2>
                        <p style="margin: 5px 0 0 0; color: #666; font-size: 14px;">Total Processed</p>
                    </div>
                    <div>
                        <h2 style="margin: 0; color: #48bb78; font-size: 36px;">{report.stats.total_kept}</h2>
                        <p style="margin: 5px 0 0 0; color: #666; font-size: 14px;">Kept ({report.stats.kept_rate:.0f}%)</p>
                    </div>
                    <div>
                        <h2 style="margin: 0; color: #f56565; font-size: 36px;">{report.stats.total_deleted}</h2>
                        <p style="margin: 5px 0 0 0; color: #666; font-size: 14px;">Archived ({report.stats.deletion_rate:.0f}%)</p>
                    </div>
                </div>
                
                <!-- Top Categories -->
                <div style="margin-bottom: 40px;">
                    <h3 style="margin: 0 0 20px 0; color: #2d3748; font-size: 20px;">
                        📊 Top 10 Email Categories
                    </h3>
                    <div style="background-color: #f8f9fa; border-radius: 8px; overflow: hidden;">
                        <table style="width: 100%; border-collapse: collapse;">
                            <thead>
                                <tr style="background-color: #e9ecef;">
                                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #495057;">Category</th>
                                    <th style="padding: 12px; text-align: center; font-weight: 600; color: #495057;">Count</th>
                                    <th style="padding: 12px; text-align: center; font-weight: 600; color: #495057;">Percentage</th>
                                </tr>
                            </thead>
                            <tbody>
                                {category_rows}
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <!-- Top Senders -->
                <div style="margin-bottom: 40px;">
                    <h3 style="margin: 0 0 20px 0; color: #2d3748; font-size: 20px;">
                        👥 Top 5 Email Senders
                    </h3>
                    <div style="background-color: #f8f9fa; border-radius: 8px; overflow: hidden;">
                        <table style="width: 100%; border-collapse: collapse;">
                            <thead>
                                <tr style="background-color: #e9ecef;">
                                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #495057;">Sender/Domain</th>
                                    <th style="padding: 12px; text-align: center; font-weight: 600; color: #495057;">Emails</th>
                                    <th style="padding: 12px; text-align: center; font-weight: 600; color: #495057;">Percentage</th>
                                </tr>
                            </thead>
                            <tbody>
                                {sender_rows}
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <!-- Summary Info -->
                <div style="background-color: #e8f4f8; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                    <p style="margin: 0; color: #0066cc; font-size: 16px; text-align: center;">
                        <strong>Processing Period:</strong> {report.stats.processing_hours:.1f} hours<br>
                        <strong>Report Generated:</strong> {report.generated_at.strftime('%I:%M %p')}
                    </p>
                </div>
            </div>
            
            <!-- Footer -->
            <div style="background-color: #f8f9fa; padding: 30px; text-align: center; border-top: 1px solid #e0e0e0;">
                <p style="margin: 0 0 10px 0; color: #666666; font-size: 14px;">
                    Cat Emails - Automated Email Management
                </p>
                <p style="margin: 0; color: #999999; font-size: 12px;">
                    This is an automated summary report. Emails are categorized and filtered automatically.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


def send_summary_email(report: DailySummaryReport, recipient_email: str) -> bool:
    """
    Send the summary report via email.
    
    Args:
        report: The summary report to send
        recipient_email: Email address to send report to
        
    Returns:
        bool: True if sent successfully
    """
    try:
        # Get SMTP credentials
        smtp_username = os.getenv('SMTP_USERNAME')
        smtp_password = os.getenv('SMTP_PASSWORD')
        
        if not smtp_username or not smtp_password:
            logger.error("SMTP credentials not configured")
            return False
        
        # Configure email provider
        config = MailfromDevConfig(
            smtp_username=smtp_username,
            smtp_password=smtp_password
        )
        provider = MailfromDevProvider(config)
        
        # Create email message
        subject = f"Cat Emails {report.report_type} Summary - {datetime.now().strftime('%B %d, %Y')}"
        
        message = EmailMessage(
            sender=EmailAddress(
                email="noreply@cat-emails.com",
                name="Cat Emails Summary"
            ),
            to=[EmailAddress(email=recipient_email)],
            subject=subject,
            text=f"Your {report.report_type.lower()} email summary is ready. "
                 f"Processed {report.stats.total_processed} emails. "
                 f"Please view the HTML version for the full report.",
            html=generate_html_report(report),
            headers={
                "X-Cat-Emails-Report": report.report_type,
                "X-Report-ID": report.report_id
            }
        )
        
        # Send email
        result = provider.send_email(message)
        
        if hasattr(result, 'status') and result.status == 'success':
            logger.info(f"Summary email sent successfully to {recipient_email}")
            return True
        else:
            logger.error(f"Failed to send summary email: {result.error_message}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending summary email: {str(e)}")
        return False


def main():
    """Main function to generate and send summary report."""
    # Get configuration
    recipient_email = os.getenv('SUMMARY_RECIPIENT_EMAIL')
    if not recipient_email:
        logger.error("SUMMARY_RECIPIENT_EMAIL not configured")
        sys.exit(1)
    
    # Determine report type based on current hour
    current_hour = datetime.now().hour
    if 6 <= current_hour < 12:
        report_type = "Morning"
    elif 18 <= current_hour < 24:
        report_type = "Evening"
    else:
        report_type = "Daily"
    
    # Initialize summary service  
    gmail_email = os.getenv('GMAIL_EMAIL')
    summary_service = EmailSummaryService(gmail_email=gmail_email)
    
    # Generate summary
    report = summary_service.generate_summary(report_type)
    if not report:
        logger.warning("No data to summarize")
        return
    
    # Send email
    if send_summary_email(report, recipient_email):
        # Clear tracked data after successful send
        summary_service.clear_tracked_data()
        logger.info(f"{report_type} summary sent and data cleared")
    else:
        logger.error("Failed to send summary email, keeping tracked data")


if __name__ == "__main__":
    main()