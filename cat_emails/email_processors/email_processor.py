from typing import Tuple
import logging
from ..email_scanner_consumer import categorize_email_ell_marketing, categorize_email_ell_generic

# Configure logger
logger = logging.getLogger(__name__)

def _sanitize_category(category: str) -> str:
    """Remove special characters from category name.
    
    Args:
        category: The category string to sanitize
        
    Returns:
        The sanitized category string with special characters removed
    """
    chars_to_remove = '"\'*=+-_'
    for char in chars_to_remove:
        category = category.replace(char, '')
    return category

def process_single_email(fetcher, msg) -> bool:
    """Process a single email message and handle its categorization and deletion."""
    # Get the email body
    try:
        body = fetcher.get_email_body(msg)
    except Exception as e:
        logger.error(f"Error fetching email body: {e}")
        body = ""  # or handle error appropriately
    pre_categorized = False
    deletion_candidate = False  # Default to not deleting

    if not body:  # Handle empty or None body
        category = "Uncategorized"
    else:
        # Check domain lists
        from_header = str(msg.get('From', ''))
        if fetcher._is_domain_blocked(from_header):
            category = "Blocked_Domain"
            pre_categorized = True
            deletion_candidate = True
        elif fetcher._is_domain_allowed(from_header):
            category = "Allowed_Domain"
            pre_categorized = True
            deletion_candidate = False
        
        # Categorize the email if not pre-categorized
        if not pre_categorized:
            contents_without_links = fetcher.remove_http_links(f"{msg.get('Subject')}. {body}")
            contents_without_images = fetcher.remove_images_from_email(contents_without_links)
            contents_without_encoded = fetcher.remove_encoded_content(contents_without_images)
            contents_cleaned = contents_without_encoded
            category = categorize_email_ell_marketing(contents_cleaned)
            if category:
                category = _sanitize_category(category)
                
                # Check if category is blocked
                if fetcher._is_category_blocked(category):
                    deletion_candidate = True
                else:
                    # if length of category is more than 30 characters
                    if len(category) > 30:
                        category2 = categorize_email_ell_generic(contents_cleaned)
                        if category2:
                            category = _sanitize_category(category2)
                            if fetcher._is_category_blocked(category):
                                deletion_candidate = True
            else:
                category = "Uncategorized"

    # Track categories and add label
    message_id = msg.get("Message-ID")
    try:
        if message_id is not None and not deletion_candidate:  # Only add label if we have a message ID and it's not being deleted
            fetcher.add_label(message_id, category)
    except Exception as e:
        logger.error(f"Error adding label to email: {e}")
        deletion_candidate = False
    finally:
        # Ensure the category count is incremented exactly once
        fetcher.stats['categories'][category] += 1
    
    # Delete the email if it's a deletion candidate
    if deletion_candidate:
        try:
            if fetcher.delete_email(message_id):
                logger.info(f"Successfully deleted email with ID {message_id}")
            else:
                logger.error(f"Failed to delete email with ID {message_id}")
        except Exception as e:
            logger.error(f"Error deleting email: {e}")
            deletion_candidate = False
    
    return deletion_candidate
