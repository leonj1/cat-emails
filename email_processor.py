from typing import Tuple

def process_single_email(fetcher, msg) -> bool:
    """Process a single email message and handle its categorization and deletion."""
    # Get the email body
    body = fetcher.get_email_body(msg)
    pre_categorized = False
    deletion_candidate = True
    
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
        category = category.replace('"', '').replace("'", "").replace('*', '').replace('=', '').replace('+', '').replace('-', '').replace('_', '')
        
        # Check if category is blocked
        if fetcher._is_category_blocked(category):
            deletion_candidate = True
        else:
            # if length of category is more than 30 characters
            if len(category) > 30:
                category = categorize_email_ell_marketing2(contents_cleaned)
                category = category.replace('"', '').replace("'", "").replace('*', '').replace('=', '').replace('+', '').replace('-', '').replace('_', '')
                if fetcher._is_category_blocked(category):
                    deletion_candidate = True

    fetcher.add_label(msg.get("Message-ID"), category)
    
    # Track categories
    fetcher.stats['categories'][category] += 1
    
    # Return whether email should be deleted
    return deletion_candidate
