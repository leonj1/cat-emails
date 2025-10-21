#!/usr/bin/env python3
"""
Test script to verify EmailProcessorService refactoring.
This script validates that EmailProcessorService now accepts
EmailCategorizerInterface instead of a Callable.
"""

import ast
import sys
from pathlib import Path
from typing import Optional, Set, Dict, Any

# Add the repo to the path
REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))


class ASTAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze Python code structure."""

    def __init__(self):
        self.imports: Set[str] = set()
        self.from_imports: Dict[str, Set[str]] = {}
        self.class_defs: Dict[str, ast.ClassDef] = {}
        self.function_defs: Dict[str, ast.FunctionDef] = {}

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            if node.module not in self.from_imports:
                self.from_imports[node.module] = set()
            for alias in node.names:
                self.from_imports[node.module].add(alias.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.class_defs[node.name] = node
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.function_defs[node.name] = node
        self.generic_visit(node)


def parse_file(file_path: Path) -> Optional[ast.Module]:
    """Parse a Python file and return its AST."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return ast.parse(content, filename=str(file_path))
    except FileNotFoundError:
        print(f"✗ File not found: {file_path}")
        return None
    except IOError as e:
        print(f"✗ Error reading file: {e}")
        return None
    except SyntaxError as e:
        print(f"✗ Syntax error in file {file_path}: {e}")
        return None


def get_init_params(class_node: ast.ClassDef) -> Optional[Dict[str, Any]]:
    """Extract __init__ method parameters and their type annotations."""
    for item in class_node.body:
        if isinstance(item, ast.FunctionDef) and item.name == '__init__':
            params = {}
            for arg in item.args.args:
                if arg.arg != 'self':
                    annotation = None
                    if arg.annotation:
                        annotation = ast.unparse(arg.annotation)
                    params[arg.arg] = annotation
            return params
    return None


def check_method_calls(class_node: ast.ClassDef, attribute: str, method: str) -> bool:
    """Check if a class contains calls to a specific method on an attribute."""
    for node in ast.walk(class_node):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if (isinstance(node.func.value, ast.Attribute) and
                    node.func.value.attr == attribute and
                    node.func.attr == method):
                    return True
    return False


def test_email_processor_service_signature():
    """Test that EmailProcessorService constructor accepts EmailCategorizerInterface."""

    print("Testing EmailProcessorService refactoring...")
    print("=" * 60)

    file_path = REPO_ROOT / 'services' / 'email_processor_service.py'

    # Parse the file
    tree = parse_file(file_path)
    if tree is None:
        return False

    # Analyze the AST
    analyzer = ASTAnalyzer()
    analyzer.visit(tree)

    # Check 1: Verify EmailCategorizerInterface is imported
    if ('services.email_categorizer_interface' in analyzer.from_imports and
        'EmailCategorizerInterface' in analyzer.from_imports['services.email_categorizer_interface']):
        print("✓ Import check: EmailCategorizerInterface is imported")
    else:
        print("✗ Import check: EmailCategorizerInterface is NOT imported")
        print(f"  Found imports: {analyzer.from_imports}")
        return False

    # Check 2: Verify Callable is not imported from typing
    if ('typing' in analyzer.from_imports and
        'Callable' in analyzer.from_imports['typing']):
        print("✗ Typing check: Callable is still imported (should be removed)")
        return False
    else:
        print("✓ Typing check: Callable is NOT imported (good!)")

    # Check 3: Verify EmailProcessorService class exists
    if 'EmailProcessorService' not in analyzer.class_defs:
        print("✗ Class check: EmailProcessorService class not found")
        return False

    class_node = analyzer.class_defs['EmailProcessorService']

    # Check 4: Verify constructor parameter type hint
    init_params = get_init_params(class_node)
    if init_params is None:
        print("✗ Constructor check: __init__ method not found")
        return False

    if 'email_categorizer' in init_params:
        annotation = init_params['email_categorizer']
        if annotation == 'EmailCategorizerInterface':
            print("✓ Constructor check: Parameter uses EmailCategorizerInterface")
        else:
            print(f"✗ Constructor check: Parameter type is '{annotation}', expected 'EmailCategorizerInterface'")
            return False
    else:
        print("✗ Constructor check: email_categorizer parameter not found")
        print(f"  Found parameters: {list(init_params.keys())}")
        return False

    # Check 5: Verify the old callable parameter is gone
    if 'categorize_fn' in init_params:
        print("✗ Legacy check: Old categorize_fn parameter still exists")
        return False
    else:
        print("✓ Legacy check: Old Callable parameter is removed")

    # Check 6: Verify method call uses the interface
    if check_method_calls(class_node, 'email_categorizer', 'categorize'):
        print("✓ Method call check: Uses email_categorizer.categorize()")
    else:
        print("✗ Method call check: Does not use email_categorizer.categorize()")
        return False

    print("=" * 60)
    print("All checks passed! ✓")
    return True

def test_account_email_processor_service():
    """Test that AccountEmailProcessorService also uses the interface."""

    print("\nTesting AccountEmailProcessorService refactoring...")
    print("=" * 60)

    file_path = REPO_ROOT / 'services' / 'account_email_processor_service.py'

    # Parse the file
    tree = parse_file(file_path)
    if tree is None:
        return False

    # Analyze the AST
    analyzer = ASTAnalyzer()
    analyzer.visit(tree)

    # Check 1: Verify EmailCategorizerInterface is imported
    if ('services.email_categorizer_interface' in analyzer.from_imports and
        'EmailCategorizerInterface' in analyzer.from_imports['services.email_categorizer_interface']):
        print("✓ Import check: EmailCategorizerInterface is imported")
    else:
        print("✗ Import check: EmailCategorizerInterface is NOT imported")
        print(f"  Found imports: {analyzer.from_imports}")
        return False

    # Check 2: Verify AccountEmailProcessorService class exists
    if 'AccountEmailProcessorService' not in analyzer.class_defs:
        print("✗ Class check: AccountEmailProcessorService class not found")
        return False

    class_node = analyzer.class_defs['AccountEmailProcessorService']

    # Check 3: Verify constructor parameter
    init_params = get_init_params(class_node)
    if init_params is None:
        print("✗ Constructor check: __init__ method not found")
        return False

    if 'email_categorizer' in init_params:
        annotation = init_params['email_categorizer']
        if annotation == 'EmailCategorizerInterface':
            print("✓ Constructor check: Parameter uses EmailCategorizerInterface")
        else:
            print(f"✗ Constructor check: Parameter type is '{annotation}', expected 'EmailCategorizerInterface'")
            return False
    else:
        print("✗ Constructor check: email_categorizer parameter not found")
        print(f"  Found parameters: {list(init_params.keys())}")
        return False

    # Check 4: Verify it stores the categorizer
    # This checks if self.email_categorizer is assigned in __init__
    for item in class_node.body:
        if isinstance(item, ast.FunctionDef) and item.name == '__init__':
            for node in ast.walk(item):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if (isinstance(target, ast.Attribute) and
                            isinstance(target.value, ast.Name) and
                            target.value.id == 'self' and
                            target.attr == 'email_categorizer'):
                            print("✓ Storage check: Stores email_categorizer as instance variable")
                            print("=" * 60)
                            print("All checks passed! ✓")
                            return True

    print("✗ Storage check: Does not store email_categorizer")
    return False

def test_factory_interfaces():
    """Test that factory classes also use the interface."""

    print("\nTesting Factory classes refactoring...")
    print("=" * 60)

    # Test EmailProcessorFactory
    factory_file_path = REPO_ROOT / 'services' / 'email_processor_factory.py'
    factory_tree = parse_file(factory_file_path)
    if factory_tree is None:
        return False

    factory_analyzer = ASTAnalyzer()
    factory_analyzer.visit(factory_tree)

    # Check factory imports
    if ('services.email_categorizer_interface' in factory_analyzer.from_imports and
        'EmailCategorizerInterface' in factory_analyzer.from_imports['services.email_categorizer_interface']):
        print("✓ Factory import check: EmailCategorizerInterface is imported")
    else:
        print("✗ Factory import check: EmailCategorizerInterface is NOT imported")
        print(f"  Found imports: {factory_analyzer.from_imports}")
        return False

    # Check factory parameter - look for any method with email_categorizer parameter
    found_param = False
    for class_name, class_node in factory_analyzer.class_defs.items():
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef):
                for arg in item.args.args:
                    if arg.arg == 'email_categorizer' and arg.annotation:
                        annotation = ast.unparse(arg.annotation)
                        if annotation == 'EmailCategorizerInterface':
                            found_param = True
                            break
                if found_param:
                    break
        if found_param:
            break

    if found_param:
        print("✓ Factory parameter check: Uses EmailCategorizerInterface")
    else:
        print("✗ Factory parameter check: Does not use EmailCategorizerInterface")
        return False

    # Test EmailProcessorFactoryInterface
    interface_file_path = REPO_ROOT / 'services' / 'email_processor_factory_interface.py'
    interface_tree = parse_file(interface_file_path)
    if interface_tree is None:
        return False

    interface_analyzer = ASTAnalyzer()
    interface_analyzer.visit(interface_tree)

    # Check interface imports
    if ('services.email_categorizer_interface' in interface_analyzer.from_imports and
        'EmailCategorizerInterface' in interface_analyzer.from_imports['services.email_categorizer_interface']):
        print("✓ Factory interface import check: EmailCategorizerInterface is imported")
    else:
        print("✗ Factory interface import check: EmailCategorizerInterface is NOT imported")
        print(f"  Found imports: {interface_analyzer.from_imports}")
        return False

    # Check interface parameter - look for any method with email_categorizer parameter
    found_param = False
    for class_name, class_node in interface_analyzer.class_defs.items():
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef):
                for arg in item.args.args:
                    if arg.arg == 'email_categorizer' and arg.annotation:
                        annotation = ast.unparse(arg.annotation)
                        if annotation == 'EmailCategorizerInterface':
                            found_param = True
                            break
                if found_param:
                    break
        if found_param:
            break

    if found_param:
        print("✓ Factory interface parameter check: Uses EmailCategorizerInterface")
    else:
        print("✗ Factory interface parameter check: Does not use EmailCategorizerInterface")
        return False

    print("=" * 60)
    print("All checks passed! ✓")
    return True

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("EMAILPROCESSORSERVICE REFACTORING VALIDATION")
    print("=" * 60)

    all_passed = True

    # Run all tests
    all_passed &= test_email_processor_service_signature()
    all_passed &= test_account_email_processor_service()
    all_passed &= test_factory_interfaces()

    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("✓✓✓ ALL TESTS PASSED! ✓✓✓")
        print("EmailProcessorService has been successfully refactored to use")
        print("EmailCategorizerInterface instead of Callable[[str, str], str]")
    else:
        print("✗✗✗ SOME TESTS FAILED ✗✗✗")
        print("Please review the failures above")
    print("=" * 60)

    sys.exit(0 if all_passed else 1)