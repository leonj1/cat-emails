#!/usr/bin/env python3
"""
Migrate existing JSON archive files to the SQLite database.
"""
import os
import json
import logging
from utils.logger import get_logger
from datetime import datetime
from pathlib import Path
from collections import defaultdict

from services.database_service import DatabaseService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = get_logger(__name__)


def parse_json_archive(file_path: Path) -> dict:
    """Parse a JSON archive file and extract summary data."""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            logger.warning(f"Skipping {file_path}: Not a list format")
            return None
        
        # Initialize counters
        category_stats = defaultdict(lambda: {'count': 0, 'deleted': 0, 'archived': 0})
        sender_stats = defaultdict(lambda: {'count': 0, 'deleted': 0, 'archived': 0, 'name': ''})
        domain_stats = defaultdict(lambda: {'count': 0, 'deleted': 0, 'archived': 0, 'is_blocked': False})
        
        total_processed = len(data)
        total_deleted = 0
        total_archived = 0
        
        # Process each email record
        for email in data:
            if not isinstance(email, dict):
                continue
            
            category = email.get('category', 'Unknown')
            sender = email.get('sender', '')
            action = email.get('action', 'KEPT')
            sender_domain = email.get('sender_domain', '')
            
            # Update category stats
            category_stats[category]['count'] += 1
            
            # Update action counts
            if action == 'DELETED':
                total_deleted += 1
                category_stats[category]['deleted'] += 1
                if sender:
                    sender_stats[sender]['deleted'] += 1
                if sender_domain:
                    domain_stats[sender_domain]['deleted'] += 1
            else:
                total_archived += 1
                category_stats[category]['archived'] += 1
                if sender:
                    sender_stats[sender]['archived'] += 1
                if sender_domain:
                    domain_stats[sender_domain]['archived'] += 1
            
            # Update sender stats
            if sender:
                sender_stats[sender]['count'] += 1
                sender_stats[sender]['name'] = sender.split('@')[0] if '@' in sender else sender
            
            # Update domain stats
            if sender_domain:
                domain_stats[sender_domain]['count'] += 1
                # Check if it's a blocked domain based on category
                if email.get('was_pre_categorized') and category == 'Blocked_Domain':
                    domain_stats[sender_domain]['is_blocked'] = True
        
        # Extract timestamp from filename or use first email's timestamp
        timestamp = None
        
        # Try to get timestamp from filename (e.g., tracked_20241217_080001.json)
        filename = file_path.stem
        if 'tracked_' in filename:
            try:
                date_str = filename.replace('tracked_', '')
                timestamp = datetime.strptime(date_str, '%Y%m%d_%H%M%S')
            except:
                pass
        
        # If no timestamp from filename, try to get from first email
        if not timestamp and data:
            try:
                first_email_time = data[0].get('processed_at')
                if first_email_time:
                    timestamp = datetime.fromisoformat(first_email_time.replace('Z', '+00:00'))
            except:
                pass
        
        # Default to file modification time
        if not timestamp:
            timestamp = datetime.fromtimestamp(file_path.stat().st_mtime)
        
        return {
            'date': timestamp,
            'total_processed': total_processed,
            'total_deleted': total_deleted,
            'total_archived': total_archived,
            'total_skipped': 0,
            'processing_duration': 0,
            'scan_hours': 2,  # Default assumption
            'categories': dict(category_stats),
            'senders': dict(sender_stats),
            'domains': dict(domain_stats)
        }
        
    except Exception as e:
        logger.error(f"Failed to parse {file_path}: {str(e)}")
        return None


def migrate_archives(archive_dir: str = "./email_summaries/archives", 
                    db_path: str = "./email_summaries/summaries.db"):
    """Migrate all JSON archives to database."""
    
    archive_path = Path(archive_dir)
    if not archive_path.exists():
        logger.error(f"Archive directory not found: {archive_dir}")
        return
    
    # Initialize database service
    db_service = DatabaseService(db_path=db_path)
    
    # Find all JSON files
    json_files = list(archive_path.glob("tracked_*.json"))
    logger.info(f"Found {len(json_files)} archive files to migrate")
    
    successful = 0
    failed = 0
    
    for json_file in sorted(json_files):
        logger.info(f"Processing {json_file.name}...")
        
        # Parse JSON file
        summary_data = parse_json_archive(json_file)
        if not summary_data:
            failed += 1
            continue
        
        try:
            # Save to database
            # Update the date in summary_data
            summary_data_copy = summary_data.copy()
            summary_data_copy['date'] = summary_data['date']
            
            # Create the summary with the specific date
            with db_service.Session() as session:
                from models.database import EmailSummary, CategorySummary, SenderSummary, DomainSummary
                
                summary = EmailSummary(
                    date=summary_data['date'],
                    total_emails_processed=summary_data['total_processed'],
                    total_emails_deleted=summary_data['total_deleted'],
                    total_emails_archived=summary_data['total_archived'],
                    total_emails_skipped=summary_data.get('total_skipped', 0),
                    processing_duration_seconds=summary_data.get('processing_duration', 0),
                    scan_interval_hours=summary_data.get('scan_hours', 0)
                )
                
                # Add category summaries
                for category, stats in summary_data.get('categories', {}).items():
                    cat_summary = CategorySummary(
                        category_name=category,
                        email_count=stats['count'],
                        deleted_count=stats.get('deleted', 0),
                        archived_count=stats.get('archived', 0)
                    )
                    summary.categories.append(cat_summary)
                
                # Add sender summaries (limit to top 100 to avoid huge imports)
                sender_items = list(summary_data.get('senders', {}).items())
                for sender_email, stats in sender_items[:100]:
                    sender_summary = SenderSummary(
                        sender_email=sender_email,
                        sender_name=stats.get('name', ''),
                        email_count=stats['count'],
                        deleted_count=stats.get('deleted', 0),
                        archived_count=stats.get('archived', 0)
                    )
                    summary.senders.append(sender_summary)
                
                # Add domain summaries
                for domain, stats in summary_data.get('domains', {}).items():
                    domain_summary = DomainSummary(
                        domain=domain,
                        email_count=stats['count'],
                        deleted_count=stats.get('deleted', 0),
                        archived_count=stats.get('archived', 0),
                        is_blocked=stats.get('is_blocked', False)
                    )
                    summary.domains.append(domain_summary)
                
                session.add(summary)
                session.commit()
            
            logger.info(f"Successfully migrated {json_file.name} (Date: {summary_data['date']})")
            successful += 1
            
        except Exception as e:
            logger.error(f"Failed to migrate {json_file.name}: {str(e)}")
            failed += 1
    
    logger.info(f"Migration complete: {successful} successful, {failed} failed")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate JSON archives to database')
    parser.add_argument('--archive-dir', default='./email_summaries/archives',
                       help='Directory containing JSON archive files')
    parser.add_argument('--db-path', default='./email_summaries/summaries.db',
                       help='Path to the database file')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be migrated without actually doing it')
    
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
        archive_path = Path(args.archive_dir)
        if archive_path.exists():
            json_files = list(archive_path.glob("tracked_*.json"))
            logger.info(f"Would migrate {len(json_files)} files:")
            for f in sorted(json_files):
                logger.info(f"  - {f.name}")
        else:
            logger.error(f"Archive directory not found: {args.archive_dir}")
    else:
        migrate_archives(args.archive_dir, args.db_path)


if __name__ == "__main__":
    main()