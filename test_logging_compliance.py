#!/usr/bin/env python3
"""
Test to validate that all log statements in the project are using or compatible 
with the central logging service.

This script scans all Python files and checks for:
1. Direct usage of logging.getLogger() instead of get_logger()
2. Usage of logging.basicConfig() outside of allowed files
3. Direct imports of logging that should be migrated
4. Files that are compliant with centralized logging

Run this test to ensure the entire codebase follows centralized logging standards.
"""

import os
import re
import ast
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Set
from dataclasses import dataclass, field

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


@dataclass
class FileAnalysis:
    """Results of analyzing a single Python file."""
    filepath: str
    uses_logging_getLogger: List[int] = field(default_factory=list)
    uses_logging_basicConfig: List[int] = field(default_factory=list)
    uses_get_logger: List[int] = field(default_factory=list)
    imports_logging: List[int] = field(default_factory=list)
    imports_central_logger: List[int] = field(default_factory=list)
    creates_logger_instances: List[Tuple[int, str]] = field(default_factory=list)
    
    @property
    def is_compliant(self) -> bool:
        """Check if file is compliant with centralized logging."""
        # Files that are part of the logging infrastructure are always compliant
        if self.is_infrastructure_file:
            return True
        
        # If using get_logger, it's compliant
        if self.uses_get_logger:
            return True
        
        # If not using any logging, it's compliant
        if not self.uses_logging_getLogger and not self.creates_logger_instances:
            return True
        
        # Main entry points can use logging.basicConfig if they also initialize central logging
        if self.is_entry_point and self.imports_central_logger:
            return True
        
        return False
    
    @property
    def is_infrastructure_file(self) -> bool:
        """Check if this is a logging infrastructure file."""
        infrastructure_files = {
            'utils/logger.py',
            'services/logging_service.py',
            'services/logging_factory.py',
            'clients/logs_collector_client.py',
            'test_centralized_logging.py',
            'test_logging_compliance.py',
            'examples/centralized_logging_example.py',
            'examples/logging_service_example.py',
            'tests/test_logging_service.py'
        }
        return any(self.filepath.endswith(f) for f in infrastructure_files)
    
    @property
    def is_entry_point(self) -> bool:
        """Check if this is a main entry point file."""
        entry_points = {
            'api_service.py',
            'gmail_fetcher.py',
            'email_scanner_producer.py',
            'email_scanner_consumer.py',
            'send_emails.py',
            'send_summary_report.py',
            'gmail_label_fetcher.py',
            'verify_email_password.py',
            'generate_historical_report.py',
            'migrate_json_archives.py',
            'frontend/web_dashboard.py'
        }
        return any(self.filepath.endswith(f) for f in entry_points)
    
    @property
    def needs_migration(self) -> bool:
        """Check if this file needs migration to centralized logging."""
        if self.is_compliant:
            return False
        
        # File needs migration if it uses logging but not centralized
        return bool(self.uses_logging_getLogger or self.creates_logger_instances)


class LoggingComplianceChecker:
    """Check codebase compliance with centralized logging standards."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.results: List[FileAnalysis] = []
        
        # Patterns to search for
        self.patterns = {
            'logging_getLogger': re.compile(r'logging\.getLogger\s*\('),
            'logging_basicConfig': re.compile(r'logging\.basicConfig\s*\('),
            'get_logger': re.compile(r'get_logger\s*\('),
            'import_logging': re.compile(r'^import\s+logging|^from\s+logging\s+import'),
            'import_central': re.compile(r'from\s+utils\.logger\s+import|from\s+services\.logging_service\s+import'),
            'logger_assignment': re.compile(r'^\s*logger\s*=\s*(.+)$', re.MULTILINE)
        }
        
        # Directories to skip
        self.skip_dirs = {
            '__pycache__', '.git', '.venv', 'venv', 'env',
            'node_modules', '.pytest_cache', 'egg-info',
            'logdir', 'scratch', 'build', 'dist'
        }
        
        # File patterns to skip
        self.skip_files = {
            '*.pyc', '*.pyo', '*.pyd', '.DS_Store', '*.so'
        }
    
    def analyze_file(self, filepath: Path) -> FileAnalysis:
        """Analyze a single Python file for logging compliance."""
        analysis = FileAnalysis(filepath=str(filepath.relative_to(self.project_root)))
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Check for various patterns
            for line_no, line in enumerate(lines, 1):
                # Check for logging.getLogger()
                if self.patterns['logging_getLogger'].search(line):
                    analysis.uses_logging_getLogger.append(line_no)
                
                # Check for logging.basicConfig()
                if self.patterns['logging_basicConfig'].search(line):
                    analysis.uses_logging_basicConfig.append(line_no)
                
                # Check for get_logger()
                if self.patterns['get_logger'].search(line):
                    analysis.uses_get_logger.append(line_no)
                
                # Check for logging imports
                if self.patterns['import_logging'].search(line):
                    analysis.imports_logging.append(line_no)
                
                # Check for central logger imports
                if self.patterns['import_central'].search(line):
                    analysis.imports_central_logger.append(line_no)
                
                # Check for logger assignments
                match = self.patterns['logger_assignment'].search(line)
                if match:
                    assignment = match.group(1).strip()
                    if 'logging.getLogger' in assignment or 'get_logger' in assignment:
                        analysis.creates_logger_instances.append((line_no, assignment))
            
        except Exception as e:
            print(f"Error analyzing {filepath}: {e}", file=sys.stderr)
        
        return analysis
    
    def scan_project(self) -> List[FileAnalysis]:
        """Scan all Python files in the project."""
        self.results = []
        
        for root, dirs, files in os.walk(self.project_root):
            # Skip certain directories
            dirs[:] = [d for d in dirs if d not in self.skip_dirs]
            
            for file in files:
                if file.endswith('.py'):
                    filepath = Path(root) / file
                    
                    # Skip certain files
                    if any(filepath.match(pattern) for pattern in self.skip_files):
                        continue
                    
                    analysis = self.analyze_file(filepath)
                    self.results.append(analysis)
        
        return self.results
    
    def generate_report(self) -> Dict:
        """Generate a compliance report."""
        total_files = len(self.results)
        compliant_files = [r for r in self.results if r.is_compliant]
        needs_migration = [r for r in self.results if r.needs_migration]
        infrastructure_files = [r for r in self.results if r.is_infrastructure_file]
        entry_point_files = [r for r in self.results if r.is_entry_point]
        
        # Files using different logging approaches
        using_logging_getLogger = [r for r in self.results if r.uses_logging_getLogger]
        using_get_logger = [r for r in self.results if r.uses_get_logger]
        using_both = [r for r in self.results if r.uses_logging_getLogger and r.uses_get_logger]
        
        return {
            'summary': {
                'total_files': total_files,
                'compliant_files': len(compliant_files),
                'needs_migration': len(needs_migration),
                'infrastructure_files': len(infrastructure_files),
                'entry_points': len(entry_point_files),
                'compliance_rate': (len(compliant_files) / total_files * 100) if total_files > 0 else 100
            },
            'usage': {
                'using_logging_getLogger': len(using_logging_getLogger),
                'using_get_logger': len(using_get_logger),
                'using_both': len(using_both)
            },
            'files_needing_migration': needs_migration,
            'compliant_files': compliant_files
        }
    
    def print_report(self, report: Dict):
        """Print a formatted compliance report."""
        print("\n" + "=" * 80)
        print("CENTRALIZED LOGGING COMPLIANCE REPORT")
        print("=" * 80)
        
        # Summary
        summary = report['summary']
        print(f"\n📊 SUMMARY")
        print(f"  Total Python files scanned: {summary['total_files']}")
        print(f"  Compliant files: {summary['compliant_files']} ({summary['compliance_rate']:.1f}%)")
        print(f"  Files needing migration: {summary['needs_migration']}")
        print(f"  Infrastructure files: {summary['infrastructure_files']}")
        print(f"  Entry point files: {summary['entry_points']}")
        
        # Usage statistics
        usage = report['usage']
        print(f"\n📈 USAGE STATISTICS")
        print(f"  Files using logging.getLogger(): {usage['using_logging_getLogger']}")
        print(f"  Files using get_logger(): {usage['using_get_logger']}")
        print(f"  Files using both: {usage['using_both']}")
        
        # Files needing migration
        if report['files_needing_migration']:
            print(f"\n⚠️  FILES NEEDING MIGRATION ({len(report['files_needing_migration'])})")
            for analysis in sorted(report['files_needing_migration'], key=lambda x: x.filepath):
                print(f"\n  📄 {analysis.filepath}")
                
                if analysis.uses_logging_getLogger:
                    print(f"     - Uses logging.getLogger() at lines: {analysis.uses_logging_getLogger[:5]}")
                    if len(analysis.uses_logging_getLogger) > 5:
                        print(f"       ... and {len(analysis.uses_logging_getLogger) - 5} more")
                
                if analysis.uses_logging_basicConfig:
                    print(f"     - Uses logging.basicConfig() at lines: {analysis.uses_logging_basicConfig}")
                
                if analysis.creates_logger_instances:
                    print(f"     - Creates logger instances at {len(analysis.creates_logger_instances)} location(s)")
                
                # Suggest migration steps
                print(f"     ✨ Migration: Replace 'logging.getLogger' with 'get_logger' from utils.logger")
        
        # Success cases
        print(f"\n✅ COMPLIANT FILES ({len(report['compliant_files'])})")
        compliant_using_central = [r for r in report['compliant_files'] 
                                   if r.uses_get_logger and not r.is_infrastructure_file]
        if compliant_using_central:
            print("\n  Files correctly using centralized logging:")
            for analysis in sorted(compliant_using_central[:10], key=lambda x: x.filepath):
                print(f"    ✓ {analysis.filepath}")
            if len(compliant_using_central) > 10:
                print(f"    ... and {len(compliant_using_central) - 10} more")
        
        # Overall status
        print("\n" + "=" * 80)
        if summary['compliance_rate'] == 100:
            print("🎉 PERFECT! All files are compliant with centralized logging standards!")
        elif summary['compliance_rate'] >= 90:
            print("👍 GOOD! Most files are compliant. Just a few files need migration.")
        elif summary['compliance_rate'] >= 70:
            print("📝 MODERATE: Several files need migration to centralized logging.")
        else:
            print("⚠️  ACTION NEEDED: Many files need migration to centralized logging.")
        print("=" * 80)
    
    def generate_migration_script(self, report: Dict) -> str:
        """Generate a migration script for non-compliant files."""
        if not report['files_needing_migration']:
            return "# No files need migration!"
        
        script = """#!/usr/bin/env python3
\"\"\"
Auto-generated migration script to update files to use centralized logging.
Review changes before committing!
\"\"\"

import re
from pathlib import Path

def migrate_file(filepath):
    \"\"\"Migrate a single file to use centralized logging.\"\"\"
    with open(filepath, 'r') as f:
        content = f.read()
    
    original = content
    
    # Replace logging.getLogger with get_logger
    content = re.sub(
        r'logging\\.getLogger',
        'get_logger',
        content
    )
    
    # Update imports
    if 'get_logger' in content and 'from utils.logger import get_logger' not in content:
        # Add import after other imports
        if 'import logging' in content:
            content = re.sub(
                r'(import logging.*?)\\n',
                r'\\1\\nfrom utils.logger import get_logger\\n',
                content,
                count=1
            )
        else:
            # Add at the beginning after module docstring
            lines = content.split('\\n')
            import_added = False
            for i, line in enumerate(lines):
                if not line.startswith('#') and not line.startswith('\"\"\"'):
                    lines.insert(i, 'from utils.logger import get_logger')
                    import_added = True
                    break
            if import_added:
                content = '\\n'.join(lines)
    
    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
        return True
    return False

# Files to migrate
files_to_migrate = [
"""
        for analysis in report['files_needing_migration']:
            script += f"    '{analysis.filepath}',\n"
        
        script += """]

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
    
    print(f"\\n{'='*60}")
    print(f"Migration complete! {migrated} files updated.")
    print(f"Please review the changes before committing.")
"""
        return script


def main():
    """Run the compliance check."""
    checker = LoggingComplianceChecker()
    
    print("🔍 Scanning project for logging compliance...")
    checker.scan_project()
    
    report = checker.generate_report()
    checker.print_report(report)
    
    # Generate migration script if needed
    if report['files_needing_migration']:
        script_path = Path('migrate_to_central_logging.py')
        script = checker.generate_migration_script(report)
        
        print(f"\n📝 Migration script generated: {script_path}")
        print("   Run it with: python3 migrate_to_central_logging.py")
        
        with open(script_path, 'w') as f:
            f.write(script)
        
        os.chmod(script_path, 0o755)
    
    # Return exit code based on compliance
    if report['summary']['compliance_rate'] == 100:
        return 0  # Success
    else:
        return 1  # Indicate files need migration


if __name__ == "__main__":
    sys.exit(main())
