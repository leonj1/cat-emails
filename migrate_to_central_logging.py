#!/usr/bin/env python3
"""
Auto-generated migration script to update files to use centralized logging.
Review changes before committing!
"""

import re
from pathlib import Path

def migrate_file(filepath):
    """Migrate a single file to use centralized logging."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    original = content
    
    # Replace logging.getLogger with get_logger
    content = re.sub(
        r'logging\.getLogger',
        'get_logger',
        content
    )
    
    # Update imports
    if 'get_logger' in content and 'from utils.logger import get_logger' not in content:
        # Add import after other imports
        if 'import logging' in content:
            content = re.sub(
                r'(import logging.*?)\n',
                r'\1\nfrom utils.logger import get_logger\n',
                content,
                count=1
            )
        else:
            # Add at the beginning after module docstring
            lines = content.split('\n')
            import_added = False
            for i, line in enumerate(lines):
                if not line.startswith('#') and not line.startswith('"""'):
                    lines.insert(i, 'from utils.logger import get_logger')
                    import_added = True
                    break
            if import_added:
                content = '\n'.join(lines)
    
    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
        return True
    return False

# Files to migrate
files_to_migrate = [
    'test_logging_compliance_ci.py',
]

if __name__ == '__main__':
    migrated = 0
    for filepath in files_to_migrate:
        path = Path(filepath)
        if path.exists():
            if migrate_file(path):
                print(f"✓ Migrated: {filepath}")
                migrated += 1
            else:
                print(f"⊘ No changes needed: {filepath}")
        else:
            print(f"✗ File not found: {filepath}")
    
    print(f"\n{'='*60}")
    print(f"Migration complete! {migrated} files updated.")
    print(f"Please review the changes before committing.")
