#!/usr/bin/env python3
"""
Lightweight logging compliance test for CI/CD pipelines.

This test validates that all Python files in the project are using
centralized logging correctly. It's designed to be fast and provide
clear pass/fail results for continuous integration.

Exit codes:
  0 - All files are compliant
  1 - Some files need migration
  2 - Error during scanning
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Set, Tuple

# Files that are allowed to use logging.getLogger() directly
ALLOWED_EXCEPTIONS = {
    'utils/logger.py',
    'services/logging_service.py',
    'services/logging_factory.py',
    'clients/logs_collector_client.py',
    'test_centralized_logging.py',
    'test_logging_compliance.py',
    'test_logging_compliance_ci.py',
    'examples/centralized_logging_example.py',
    'examples/logging_service_example.py',
    'tests/test_logging_service.py',
    'migrate_to_central_logging.py'
}

# Directories to skip
SKIP_DIRS = {
    '__pycache__', '.git', '.venv', 'venv', 'env',
    'node_modules', '.pytest_cache', 'egg-info',
    'logdir', 'scratch', 'build', 'dist', '.tox'
}

def check_file_compliance(filepath: Path, project_root: Path) -> Tuple[bool, List[str]]:
    """
    Check if a single file is compliant with centralized logging.
    
    Returns:
        (is_compliant, list_of_violations)
    """
    relative_path = str(filepath.relative_to(project_root))
    
    # Check if this file is in the allowed exceptions
    if any(relative_path.endswith(exception) for exception in ALLOWED_EXCEPTIONS):
        return True, []
    
    violations = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
        
        # Check for logging.getLogger usage
        for line_no, line in enumerate(lines, 1):
            if 'logging.getLogger' in line and not line.strip().startswith('#'):
                violations.append(f"Line {line_no}: Uses logging.getLogger()")
        
        # If file uses get_logger from utils.logger, it's compliant
        if 'from utils.logger import' in content and 'get_logger' in content:
            # File is using centralized logging
            return True, []
        
        # If file has violations, it's not compliant
        if violations:
            return False, violations
        
        # File doesn't use logging at all, so it's compliant
        return True, []
        
    except Exception as e:
        # Error reading file, treat as violation
        return False, [f"Error reading file: {e}"]


def scan_project(project_root: str = ".") -> Tuple[List[Path], List[Tuple[Path, List[str]]]]:
    """
    Scan all Python files in the project for compliance.
    
    Returns:
        (list_of_compliant_files, list_of_non_compliant_files_with_violations)
    """
    project_path = Path(project_root)
    compliant = []
    non_compliant = []
    
    for root, dirs, files in os.walk(project_path):
        # Skip certain directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        
        for file in files:
            if file.endswith('.py'):
                filepath = Path(root) / file
                
                is_compliant, violations = check_file_compliance(filepath, project_path)
                
                if is_compliant:
                    compliant.append(filepath)
                else:
                    non_compliant.append((filepath, violations))
    
    return compliant, non_compliant


def main():
    """Run the compliance check for CI/CD."""
    try:
        print("🔍 Checking logging compliance...")
        
        compliant, non_compliant = scan_project()
        
        total_files = len(compliant) + len(non_compliant)
        compliance_rate = (len(compliant) / total_files * 100) if total_files > 0 else 100
        
        print(f"📊 Results: {len(compliant)}/{total_files} files compliant ({compliance_rate:.1f}%)")
        
        if non_compliant:
            print(f"\n❌ FAILED: {len(non_compliant)} files are not using centralized logging:\n")
            
            for filepath, violations in non_compliant[:10]:  # Show first 10
                relative_path = filepath.relative_to(Path("."))
                print(f"  ⚠️  {relative_path}")
                for violation in violations[:3]:  # Show first 3 violations per file
                    print(f"      {violation}")
            
            if len(non_compliant) > 10:
                print(f"\n  ... and {len(non_compliant) - 10} more files")
            
            print("\n💡 To fix: Replace 'logging.getLogger' with 'get_logger' from utils.logger")
            print("   Or run: python3 test_logging_compliance.py to generate a migration script")
            
            return 1  # Failure
        else:
            print("\n✅ SUCCESS: All files are using centralized logging correctly!")
            return 0  # Success
            
    except Exception as e:
        print(f"\n🚨 ERROR: Failed to scan project: {e}")
        return 2  # Error


if __name__ == "__main__":
    sys.exit(main())
