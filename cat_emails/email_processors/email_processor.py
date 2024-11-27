from typing import Tuple
from email_scanner_consumer import categorize_email_ell_marketing, categorize_email_ell_marketing2

def process_single_email(fetcher, msg) -> bool:
    """Process a single email message and handle its categorization and deletion."""
    # Get the email body
    try:
        body = fetcher.get_email_body(msg)
    except Exception as e:
        # Log the error
        body = ""  # or handle error appropriately
    pre_categorized = False
    deletion_candidate = False  # Default to not deleting

    if not body:  # Handle empty or None body
        category = "Uncategorized"
        message_id = msg.get("Message-ID")
        if message_id is not None:
            fetcher.add_label(message_id, category)
        fetcher.stats['categories'][category] += 1
        return deletion_candidate

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
            category = category.replace('"', '').replace("'", "").replace('*', '').replace('=', '').replace('+', '').replace('-', '').replace('_', '')
            
            # Check if category is blocked
            if fetcher._is_category_blocked(category):
                deletion_candidate = True
            else:
                # if length of category is more than 30 characters
                if len(category) > 30:
                    category2 = categorize_email_ell_marketing2(contents_cleaned)
                    if category2:
                        category = category2.replace('"', '').replace("'", "").replace('*', '').replace('=', '').replace('+', '').replace('-', '').replace('_', '')
                        if fetcher._is_category_blocked(category):
                            deletion_candidate = True
        else:
            category = "Uncategorized"

    # Track categories and add label
    message_id = msg.get("Message-ID")
    try:
        if message_id is not None:  # Only add label if we have a message ID
            fetcher.add_label(message_id, category)
        fetcher.stats['categories'][category] += 1
    except Exception as e:
        # If we have problems setting the tag lets not mark for deletion
        deletion_candidate = False
        # Still increment the category counter even if label fails
        fetcher.stats['categories'][category] += 1
    
    return deletion_candidate
