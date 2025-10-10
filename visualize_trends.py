#!/usr/bin/env python3
"""
Visualize email processing trends from the database.
Generates text-based charts for category trends, deletion rates, and processing volumes.
"""
import os
import sys
import argparse
import logging
from utils.logger import get_logger
from datetime import datetime, timedelta
from collections import defaultdict

from services.database_service import DatabaseService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = get_logger(__name__)


def generate_ascii_chart(data_points: list, width: int = 60, height: int = 20) -> str:
    """Generate a simple ASCII line chart."""
    if not data_points:
        return "No data available"
    
    # Find min and max values
    values = [v for _, v in data_points]
    min_val = min(values)
    max_val = max(values)
    
    if max_val == min_val:
        max_val = min_val + 1  # Avoid division by zero
    
    # Create chart
    chart_lines = []
    
    # Scale values to chart height
    scaled_values = []
    for _, value in data_points:
        scaled = int((value - min_val) / (max_val - min_val) * (height - 1))
        scaled_values.append(scaled)
    
    # Build chart from top to bottom
    for row in range(height - 1, -1, -1):
        line = ""
        for col, scaled_val in enumerate(scaled_values[:width]):
            if scaled_val >= row:
                line += "█"
            else:
                line += " "
        
        # Add axis label
        if row == height - 1:
            label = f"{max_val:>6.0f} |"
        elif row == 0:
            label = f"{min_val:>6.0f} |"
        else:
            label = "       |"
        
        chart_lines.append(label + line)
    
    # Add bottom axis
    chart_lines.append("       +" + "-" * min(len(scaled_values), width))
    
    return "\n".join(chart_lines)


def show_category_trends(db_service: DatabaseService, days: int = 30):
    """Display category trends over time."""
    print(f"\n{'='*70}")
    print(f"CATEGORY TRENDS (Last {days} days)")
    print(f"{'='*70}\n")
    
    trends = db_service.get_category_trends(days)
    
    if not trends:
        print("No trend data available")
        return
    
    # Show top 5 categories
    sorted_categories = sorted(trends.items(), 
                              key=lambda x: sum(count for _, count in x[1]), 
                              reverse=True)[:5]
    
    for category, data_points in sorted_categories:
        print(f"\n{category}:")
        print("-" * 50)
        
        # Prepare data for chart
        daily_counts = defaultdict(int)
        for date, count in data_points:
            daily_counts[date.date()] += count
        
        # Convert to list and sort by date
        chart_data = sorted([(d, c) for d, c in daily_counts.items()])
        
        # Generate mini chart
        if chart_data:
            values = [c for _, c in chart_data]
            max_val = max(values)
            
            # Create simple bar chart
            for date, count in chart_data[-10:]:  # Last 10 days
                bar_length = int((count / max_val) * 40) if max_val > 0 else 0
                bar = "█" * bar_length
                print(f"{date.strftime('%m/%d')} | {bar} {count}")


def show_processing_volume(db_service: DatabaseService):
    """Show email processing volume trends."""
    print(f"\n{'='*70}")
    print("PROCESSING VOLUME TRENDS")
    print(f"{'='*70}\n")
    
    # Get daily summaries for the last 30 days
    daily_volumes = []
    for days_ago in range(29, -1, -1):
        target_date = datetime.utcnow() - timedelta(days=days_ago)
        summary = db_service.get_daily_summary(target_date)
        
        if summary['metrics']['total_processed'] > 0:
            daily_volumes.append((
                target_date.date(),
                summary['metrics']['total_processed']
            ))
    
    if not daily_volumes:
        print("No processing data available")
        return
    
    # Show chart
    print("Daily Email Processing Volume:")
    print(generate_ascii_chart(daily_volumes, width=50, height=15))
    
    # Show statistics
    total_processed = sum(v for _, v in daily_volumes)
    avg_daily = total_processed / len(daily_volumes) if daily_volumes else 0
    
    print(f"\nStatistics:")
    print(f"  Total Processed (30 days): {total_processed:,}")
    print(f"  Average Daily: {avg_daily:.1f}")
    print(f"  Peak Day: {max(daily_volumes, key=lambda x: x[1])[0]} ({max(v for _, v in daily_volumes):,} emails)")


def show_deletion_rates(db_service: DatabaseService):
    """Show email deletion rate trends."""
    print(f"\n{'='*70}")
    print("DELETION RATE TRENDS")
    print(f"{'='*70}\n")
    
    # Calculate weekly deletion rates
    weekly_rates = []
    for weeks_ago in range(3, -1, -1):
        summary = db_service.get_weekly_summary(weeks_ago)
        metrics = summary['metrics']
        
        if metrics['total_processed'] > 0:
            deletion_rate = (metrics['total_deleted'] / metrics['total_processed']) * 100
            week_label = f"Week -{weeks_ago}" if weeks_ago > 0 else "This Week"
            weekly_rates.append((week_label, deletion_rate))
    
    if not weekly_rates:
        print("No deletion rate data available")
        return
    
    # Show rates
    print("Weekly Deletion Rates:")
    for week, rate in weekly_rates:
        bar_length = int(rate / 2)  # Scale to max 50 chars
        bar = "█" * bar_length
        print(f"{week:>12} | {bar} {rate:.1f}%")


def show_top_domains_summary(db_service: DatabaseService, days: int = 7):
    """Show top domains by email volume."""
    print(f"\n{'='*70}")
    print(f"TOP DOMAINS (Last {days} days)")
    print(f"{'='*70}\n")
    
    start_date = datetime.utcnow() - timedelta(days=days)
    end_date = datetime.utcnow()
    
    summary = db_service.get_summary_by_period(start_date, end_date)
    
    if not summary['domains']:
        print("No domain data available")
        return
    
    print(f"{'Domain':<30} {'Count':>10} {'Deleted':>10} {'Status':>10}")
    print("-" * 60)
    
    for domain in summary['domains'][:15]:
        status = "BLOCKED" if domain['is_blocked'] else "allowed"
        print(f"{domain['domain']:<30} {domain['count']:>10,} {domain['deleted']:>10,} {status:>10}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Visualize email processing trends')
    parser.add_argument('--db-path', default='./email_summaries/summaries.db',
                       help='Path to the database file')
    parser.add_argument('--days', type=int, default=30,
                       help='Number of days to analyze')
    parser.add_argument('--section', choices=['all', 'categories', 'volume', 'deletion', 'domains'],
                       default='all', help='Which section to display')
    
    args = parser.parse_args()
    
    # Initialize database service
    db_service = DatabaseService(db_path=args.db_path)
    
    try:
        if args.section in ['all', 'volume']:
            show_processing_volume(db_service)
        
        if args.section in ['all', 'deletion']:
            show_deletion_rates(db_service)
        
        if args.section in ['all', 'categories']:
            show_category_trends(db_service, args.days)
        
        if args.section in ['all', 'domains']:
            show_top_domains_summary(db_service, args.days)
        
        print("\n")
        
    except Exception as e:
        logger.error(f"Failed to generate visualization: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()