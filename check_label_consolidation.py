#!/usr/bin/env python3
"""
Check Gmail Label Consolidation
Fetches Gmail labels and returns proposed consolidation mapping
"""
import os
import sys
import argparse
import json
import logging
import imaplib
from typing import List, Dict

from label_consolidation.models import ConsolidationConfig
from label_consolidation.label_consolidation_service import LabelConsolidationService

# Configure minimal logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


class GmailLabelChecker:
    """Minimal Gmail label fetcher for consolidation checking"""
    
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.imap = None
        
    def connect(self) -> bool:
        """Connect to Gmail IMAP server"""
        try:
            self.imap = imaplib.IMAP4_SSL('imap.gmail.com', 993)
            self.imap.login(self.email, self.password)
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Gmail: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from Gmail"""
        if self.imap:
            try:
                self.imap.logout()
            except:
                pass
    
    def fetch_labels(self) -> List[str]:
        """Fetch all labels from Gmail"""
        if not self.imap:
            return []
        
        try:
            status, folders = self.imap.list()
            
            if status != 'OK':
                return []
            
            labels = []
            for folder_info in folders:
                folder_str = folder_info.decode('utf-8')
                
                # Extract label name (last quoted string)
                parts = folder_str.split('"')
                if len(parts) >= 2:
                    label = parts[-2]
                    
                    # Skip system folders
                    if label.startswith('[Gmail]/'):
                        continue
                    
                    # Handle nested labels - keep full path for accuracy
                    labels.append(label)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_labels = []
            for label in labels:
                if label not in seen:
                    seen.add(label)
                    unique_labels.append(label)
            
            return unique_labels
            
        except Exception as e:
            logger.error(f"Error fetching labels: {e}")
            return []


def main():
    parser = argparse.ArgumentParser(
        description='Check Gmail label consolidation proposals'
    )
    parser.add_argument('--max-labels', '-m', type=int, default=25,
                       help='Maximum number of consolidated labels (default: 25)')
    
    args = parser.parse_args()
    
    # Get credentials from environment
    email = os.getenv('GMAIL_EMAIL')
    password = os.getenv('GMAIL_PASSWORD')
    
    if not email or not password:
        print(json.dumps({
            "error": "Missing credentials",
            "message": "GMAIL_EMAIL and GMAIL_PASSWORD environment variables are required"
        }))
        sys.exit(1)
    
    # Connect and fetch labels
    checker = GmailLabelChecker(email, password)
    if not checker.connect():
        print(json.dumps({
            "error": "Connection failed",
            "message": "Failed to connect to Gmail. Check credentials and network connection."
        }))
        sys.exit(1)
    
    try:
        labels = checker.fetch_labels()
        
        if not labels:
            print(json.dumps({
                "error": "No labels found",
                "message": "No labels were found in the Gmail account"
            }))
            sys.exit(1)
        
        # Configure consolidation
        config = ConsolidationConfig(
            max_categories=args.max_labels,
            similarity_threshold=0.8,
            normalization_aggressive=True
        )
        
        # Perform consolidation
        service = LabelConsolidationService(config)
        result = service.consolidate(labels)
        
        # Prepare output
        output = {
            "status": "success",
            "original_count": result.original_count,
            "consolidated_count": result.final_count,
            "reduction_percentage": round(result.reduction_percentage, 1),
            "max_labels_requested": args.max_labels,
            "consolidation_mapping": result.mapping,
            "consolidated_groups": [
                {
                    "category": group.canonical_name,
                    "member_count": group.member_count,
                    "members": sorted([label.original_name for label in group.original_labels])
                }
                for group in sorted(result.label_groups, 
                                  key=lambda g: g.member_count, 
                                  reverse=True)
            ]
        }
        
        print(json.dumps(output, indent=2, sort_keys=True))
        
    finally:
        checker.disconnect()


if __name__ == "__main__":
    main()