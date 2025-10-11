#!/usr/bin/env python3
"""
Generate historical email processing reports from the database.
"""
import os
import sys
import argparse
import logging
from utils.logger import get_logger
from datetime import datetime, timedelta
from tabulate import tabulate

from services.database_service import DatabaseService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = get_logger(__name__)


def format_summary(summary: dict, title: str) -> str:
    """Format a summary dict into a readable report."""
    output = [f"\n{'='*60}"]
    output.append(f"{title.center(60)}")
    output.append(f"{'='*60}")
    
    # Period info
    period = summary['period']
    output.append(f"Period: {period['start'].strftime('%Y-%m-%d')} to {period['end'].strftime('%Y-%m-%d')}")
    output.append("")
    
    # Metrics
    metrics = summary['metrics']
    output.append("OVERALL METRICS:")
    output.append(f"  Total Emails Processed: {metrics['total_processed']:,}")
    output.append(f"  Total Emails Deleted: {metrics['total_deleted']:,}")
    output.append(f"  Total Emails Archived: {metrics['total_archived']:,}")
    if metrics['total_processed'] > 0:
        deletion_rate = (metrics['total_deleted'] / metrics['total_processed']) * 100
        output.append(f"  Deletion Rate: {deletion_rate:.1f}%")
    output.append(f"  Average Processing Time: {metrics['avg_processing_seconds']:.1f} seconds")
    output.append("")
    
    # Top Categories
    if summary['categories']:
        output.append("TOP CATEGORIES:")
        category_data = []
        for cat in summary['categories'][:10]:
            category_data.append([
                cat['name'],
                f"{cat['count']:,}",
                f"{cat['deleted']:,}",
                f"{(cat['deleted']/cat['count']*100) if cat['count'] > 0 else 0:.1f}%"
            ])
        output.append(tabulate(
            category_data,
            headers=['Category', 'Count', 'Deleted', 'Delete Rate'],
            tablefmt='simple'
        ))
        output.append("")
    
    # Top Domains
    if summary['domains']:
        output.append("TOP DOMAINS:")
        domain_data = []
        for dom in summary['domains'][:10]:
            domain_data.append([
                dom['domain'],
                f"{dom['count']:,}",
                f"{dom['deleted']:,}",
                "Yes" if dom['is_blocked'] else "No"
            ])
        output.append(tabulate(
            domain_data,
            headers=['Domain', 'Count', 'Deleted', 'Blocked'],
            tablefmt='simple'
        ))
        output.append("")
    
    # Top Senders
    if summary['senders']:
        output.append("TOP SENDERS:")
        sender_data = []
        for sender in summary['senders'][:5]:
            email = sender['email']
            if len(email) > 40:
                email = email[:37] + "..."
            sender_data.append([
                email,
                sender['name'] or 'N/A',
                f"{sender['count']:,}",
                f"{sender['deleted']:,}"
            ])
        output.append(tabulate(
            sender_data,
            headers=['Email', 'Name', 'Count', 'Deleted'],
            tablefmt='simple'
        ))
        output.append("")
    
    return "\n".join(output)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Generate historical email processing reports')
    parser.add_argument('--period', choices=['daily', 'weekly', 'monthly', 'custom'], 
                       default='daily', help='Report period')
    parser.add_argument('--days-ago', type=int, default=0, 
                       help='Days/weeks/months ago (0 = current)')
    parser.add_argument('--start-date', help='Start date for custom period (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date for custom period (YYYY-MM-DD)')
    parser.add_argument('--db-path', default='./email_summaries/summaries.db',
                       help='Path to the database file')
    parser.add_argument('--export', help='Export report to file')
    
    args = parser.parse_args()
    
    # Initialize database service
    db_service = DatabaseService(db_path=args.db_path)
    
    try:
        # Generate report based on period
        if args.period == 'daily':
            if args.days_ago == 0:
                summary = db_service.get_daily_summary()
                title = f"Daily Summary for {datetime.utcnow().strftime('%Y-%m-%d')}"
            else:
                target_date = datetime.utcnow() - timedelta(days=args.days_ago)
                summary = db_service.get_daily_summary(target_date)
                title = f"Daily Summary for {target_date.strftime('%Y-%m-%d')}"
                
        elif args.period == 'weekly':
            summary = db_service.get_weekly_summary(args.days_ago)
            if args.days_ago == 0:
                title = "Weekly Summary (Current Week)"
            else:
                title = f"Weekly Summary ({args.days_ago} weeks ago)"
                
        elif args.period == 'monthly':
            summary = db_service.get_monthly_summary(args.days_ago)
            if args.days_ago == 0:
                title = "Monthly Summary (Current Month)"
            else:
                title = f"Monthly Summary ({args.days_ago} months ago)"
                
        elif args.period == 'custom':
            if not args.start_date or not args.end_date:
                logger.error("Custom period requires --start-date and --end-date")
                sys.exit(1)
            
            start = datetime.strptime(args.start_date, '%Y-%m-%d')
            end = datetime.strptime(args.end_date, '%Y-%m-%d')
            summary = db_service.get_summary_by_period(start, end)
            title = f"Custom Summary ({args.start_date} to {args.end_date})"
        
        # Format and display report
        report = format_summary(summary, title)
        
        if args.export:
            with open(args.export, 'w') as f:
                f.write(report)
            logger.info(f"Report exported to {args.export}")
        else:
            print(report)
            
        # Show recent processing runs
        print("\nRECENT PROCESSING RUNS:")
        runs = db_service.get_processing_runs(limit=10)
        if runs:
            run_data = []
            for run in runs:
                run_data.append([
                    run['started_at'].strftime('%Y-%m-%d %H:%M'),
                    f"{run['duration_seconds']:.1f}s" if run['duration_seconds'] else 'N/A',
                    f"{run['emails_processed']:,}",
                    f"{run['emails_deleted']:,}",
                    "✓" if run['success'] else "✗"
                ])
            print(tabulate(
                run_data,
                headers=['Started', 'Duration', 'Processed', 'Deleted', 'Success'],
                tablefmt='simple'
            ))
        
    except Exception as e:
        logger.error(f"Failed to generate report: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()