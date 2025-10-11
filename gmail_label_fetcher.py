#!/usr/bin/env python3
"""
Gmail Label Fetcher and Consolidator
Connects to Gmail via IMAP and consolidates labels into categories
"""
import os
import sys
import argparse
import logging
from utils.logger import get_logger
import imaplib
import getpass
import json
import csv
from typing import List, Optional
from datetime import datetime
from pathlib import Path

from label_consolidation.models import ConsolidationConfig, ConsolidationResult
from label_consolidation.label_consolidation_service import LabelConsolidationService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = get_logger(__name__)


class GmailLabelFetcher:
    """Fetches labels from Gmail via IMAP"""
    
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.imap = None
        
    def connect(self) -> bool:
        """Connect to Gmail IMAP server"""
        try:
            logger.info(f"Connecting to Gmail IMAP for {self.email}")
            self.imap = imaplib.IMAP4_SSL('imap.gmail.com', 993)
            self.imap.login(self.email, self.password)
            logger.info("Successfully connected to Gmail")
            return True
        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP authentication failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from Gmail"""
        if self.imap:
            try:
                self.imap.logout()
            except:
                pass
    
    def fetch_labels(self) -> List[str]:
        """Fetch all labels/folders from Gmail"""
        if not self.imap:
            logger.error("Not connected to Gmail")
            return []
        
        try:
            logger.info("Fetching Gmail labels...")
            status, folders = self.imap.list()
            
            if status != 'OK':
                logger.error(f"Failed to fetch labels: {status}")
                return []
            
            labels = []
            for folder_info in folders:
                # Parse folder info
                # Format: (\\HasNoChildren) "/" "Label Name"
                folder_str = folder_info.decode('utf-8')
                
                # Extract label name (last quoted string)
                parts = folder_str.split('"')
                if len(parts) >= 2:
                    label = parts[-2]
                    
                    # Skip system folders
                    if label.startswith('[Gmail]/'):
                        continue
                    
                    # Handle nested labels (Gmail uses / as separator)
                    # Convert "Parent/Child" to just "Child" for consolidation
                    if '/' in label:
                        label = label.split('/')[-1]
                    
                    labels.append(label)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_labels = []
            for label in labels:
                if label not in seen:
                    seen.add(label)
                    unique_labels.append(label)
            
            logger.info(f"Found {len(unique_labels)} unique labels")
            return unique_labels
            
        except Exception as e:
            logger.error(f"Error fetching labels: {e}")
            return []
    
    def get_label_info(self, label: str) -> dict:
        """Get information about a specific label (like message count)"""
        try:
            # Select the folder
            status, data = self.imap.select(f'"{label}"', readonly=True)
            if status == 'OK':
                # Get message count
                message_count = int(data[0])
                return {
                    'label': label,
                    'message_count': message_count
                }
        except:
            pass
        return {'label': label, 'message_count': 0}


def format_consolidation_result(result: ConsolidationResult, format_type: str = 'text') -> str:
    """Format consolidation results for output"""
    if format_type == 'json':
        return json.dumps({
            'original_count': result.original_count,
            'final_count': result.final_count,
            'reduction_percentage': result.reduction_percentage,
            'mapping': result.mapping,
            'groups': [
                {
                    'name': group.canonical_name,
                    'member_count': group.member_count,
                    'members': [label.original_name for label in group.original_labels]
                }
                for group in result.label_groups
            ],
            'timestamp': result.timestamp.isoformat()
        }, indent=2)
    
    elif format_type == 'csv':
        output = []
        output.append("Original Label,Consolidated Category,Group Size")
        for original, consolidated in sorted(result.mapping.items()):
            group = result.get_group_for_label(original)
            group_size = group.member_count if group else 1
            output.append(f'"{original}","{consolidated}",{group_size}')
        return '\n'.join(output)
    
    else:  # text format
        output = []
        output.append("=" * 60)
        output.append("GMAIL LABEL CONSOLIDATION REPORT")
        output.append("=" * 60)
        output.append(f"Original labels: {result.original_count}")
        output.append(f"Consolidated categories: {result.final_count}")
        output.append(f"Reduction: {result.reduction_percentage:.1f}%")
        output.append(f"Consolidation ratio: {result.consolidation_ratio:.2f}")
        output.append("")
        
        # Show each consolidated group
        output.append("CONSOLIDATED GROUPS:")
        output.append("-" * 60)
        
        # Sort groups by size (largest first)
        sorted_groups = sorted(result.label_groups, 
                             key=lambda g: g.member_count, 
                             reverse=True)
        
        for i, group in enumerate(sorted_groups, 1):
            output.append(f"\n{i}. {group.canonical_name.upper()} ({group.member_count} labels)")
            
            # Show up to 10 members
            members = [label.original_name for label in group.original_labels]
            if len(members) <= 10:
                for member in sorted(members):
                    output.append(f"   - {member}")
            else:
                # Show first 8 and indicate there are more
                for member in sorted(members)[:8]:
                    output.append(f"   - {member}")
                output.append(f"   ... and {len(members) - 8} more")
        
        if result.warnings:
            output.append("\nWARNINGS:")
            for warning in result.warnings:
                output.append(f"  - {warning}")
        
        return '\n'.join(output)


def main():
    parser = argparse.ArgumentParser(
        description='Fetch and consolidate Gmail labels into categories'
    )
    parser.add_argument('--email', '-e', 
                       help='Gmail email address (or set GMAIL_EMAIL env var)')
    parser.add_argument('--max-categories', '-m', type=int, default=25,
                       help='Maximum number of consolidated categories (default: 25)')
    parser.add_argument('--similarity-threshold', '-s', type=float, default=0.8,
                       help='Similarity threshold for grouping (0.0-1.0, default: 0.8)')
    parser.add_argument('--output', '-o', choices=['text', 'json', 'csv'], 
                       default='text', help='Output format')
    parser.add_argument('--output-file', '-f', 
                       help='Save output to file instead of printing')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--dry-run', action='store_true',
                       help='Test with sample data instead of connecting to Gmail')
    
    args = parser.parse_args()
    
    if args.verbose:
        get_logger().setLevel(logging.DEBUG)
    
    # Handle dry run mode
    if args.dry_run:
        logger.info("Running in dry-run mode with sample data")
        labels = [
            "Announcements", "announcement", "Announcement.", "announcements-list",
            "Work", "work-related", "Work Stuff", "Office", "work-",
            "Personal", "personal-emails", "Personal stuff",
            "Newsletter", "Newsletters", "newsletter-subscription",
            "Receipts", "Order Receipts", "Purchase Receipts", "receipt",
            "Social", "Social Media", "Facebook", "Twitter", "LinkedIn",
            "Finance", "Banking", "Bank Statements", "Financial",
            "Travel", "Flight Bookings", "Hotel Reservations", "travel-plans",
            "Support", "Customer Support", "Help Desk", "support-tickets",
            "Marketing", "Promotions", "Ads", "Advertising", "marketing-emails",
            "Dev", "Development", "GitHub", "dev-notifications",
            "Important", "IMPORTANT", "important!", "Priority",
            "Spam", "Junk", "spam-likely",
            "Archive", "Archived", "old-emails",
            "ToDo", "To Do", "Action Items", "todo-list",
            "Projects", "Project A", "Project B", "project-updates",
            "Team", "Team Updates", "team-communications",
            "Clients", "Client Emails", "Customer Emails",
            "Invoices", "Invoice", "Billing",
            "Meeting", "Meetings", "Calendar", "meeting-invites"
        ]
    else:
        # Get email from args or environment
        email = args.email or os.getenv('GMAIL_EMAIL')
        if not email:
            logger.error("Email address required. Use --email or set GMAIL_EMAIL env var")
            sys.exit(1)
        
        # Get password
        password = os.getenv('GMAIL_PASSWORD')
        if not password:
            password = getpass.getpass(f"Enter password for {email}: ")
        
        # Connect and fetch labels
        fetcher = GmailLabelFetcher(email, password)
        if not fetcher.connect():
            logger.error("Failed to connect to Gmail")
            sys.exit(1)
        
        try:
            labels = fetcher.fetch_labels()
            if not labels:
                logger.error("No labels found")
                sys.exit(1)
        finally:
            fetcher.disconnect()
    
    # Configure consolidation
    config = ConsolidationConfig(
        max_categories=args.max_categories,
        similarity_threshold=args.similarity_threshold
    )
    
    # Perform consolidation
    logger.info(f"Consolidating {len(labels)} labels into max {config.max_categories} categories")
    service = LabelConsolidationService(config)
    result = service.consolidate(labels)
    
    # Format output
    output = format_consolidation_result(result, args.output)
    
    # Save or print output
    if args.output_file:
        output_path = Path(args.output_file)
        output_path.write_text(output)
        logger.info(f"Results saved to {output_path}")
    else:
        print(output)
    
    # Print summary stats if verbose
    if args.verbose and service.stats:
        stats = service.stats
        print(f"\nProcessing Statistics:")
        print(f"  - Processing time: {stats.processing_time_seconds:.2f}s")
        print(f"  - Duplicate labels found: {stats.duplicate_labels_found}")
        print(f"  - Semantic groups created: {stats.semantic_groups_created}")
        print(f"  - Forced merges: {stats.forced_merges}")
        print(f"  - Largest group: {stats.largest_group_size} labels")
        print(f"  - Average group size: {stats.average_group_size:.1f} labels")


if __name__ == "__main__":
    main()