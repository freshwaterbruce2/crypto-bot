"""
Code Duplication Prevention System
Automated detection and prevention of duplicate code patterns
"""

import ast
import hashlib
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DuplicateDetector:
    """Detects duplicate code patterns across the codebase"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.function_signatures: dict[str, list[tuple[str, int]]] = {}
        self.code_hashes: dict[str, list[tuple[str, int, str]]] = {}
        self.duplicate_threshold = 0.8  # 80% similarity threshold

    def scan_project(self) -> dict[str, Any]:
        """Scan entire project for duplicate code"""
        results = {
            'duplicate_functions': [],
            'duplicate_code_blocks': [],
            'similar_patterns': [],
            'total_files_scanned': 0,
            'total_duplicates_found': 0
        }

        python_files = list(self.project_root.rglob('*.py'))
        results['total_files_scanned'] = len(python_files)

        for file_path in python_files:
            try:
                self._analyze_file(file_path)
            except Exception as e:
                logger.warning(f"Error analyzing {file_path}: {e}")

        # Find duplicates
        results['duplicate_functions'] = self._find_duplicate_functions()
        results['duplicate_code_blocks'] = self._find_duplicate_code_blocks()
        results['similar_patterns'] = self._find_similar_patterns()

        total_duplicates = (len(results['duplicate_functions']) +
                          len(results['duplicate_code_blocks']) +
                          len(results['similar_patterns']))
        results['total_duplicates_found'] = total_duplicates

        return results

    def _analyze_file(self, file_path: Path):
        """Analyze a single Python file for patterns"""
        try:
            with open(file_path, encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    self._record_function(node, file_path)
                elif isinstance(node, (ast.ClassDef, ast.For, ast.While, ast.If)):
                    self._record_code_block(node, file_path, content)

        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")

    def _record_function(self, node: ast.FunctionDef, file_path: Path):
        """Record function signature and body"""
        func_name = node.name
        line_no = node.lineno

        # Create function signature
        args = [arg.arg for arg in node.args.args]
        f"{func_name}({', '.join(args)})"

        # Store function location
        if func_name not in self.function_signatures:
            self.function_signatures[func_name] = []
        self.function_signatures[func_name].append((str(file_path), line_no))

        # Hash function body for content comparison
        body_code = ast.unparse(node) if hasattr(ast, 'unparse') else str(node)
        body_hash = hashlib.md5(body_code.encode()).hexdigest()

        if body_hash not in self.code_hashes:
            self.code_hashes[body_hash] = []
        self.code_hashes[body_hash].append((str(file_path), line_no, func_name))

    def _record_code_block(self, node: ast.AST, file_path: Path, content: str):
        """Record code block patterns"""
        try:
            # Get the code block as string
            if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                start_line = node.lineno - 1
                end_line = getattr(node, 'end_lineno', node.lineno)
                lines = content.split('\n')[start_line:end_line]
                block_code = '\n'.join(lines)

                # Hash the normalized code block
                normalized = self._normalize_code(block_code)
                if len(normalized) > 100:  # Only check substantial blocks
                    block_hash = hashlib.md5(normalized.encode()).hexdigest()

                    if block_hash not in self.code_hashes:
                        self.code_hashes[block_hash] = []
                    self.code_hashes[block_hash].append((str(file_path), node.lineno, 'code_block'))
        except Exception:
            pass  # Skip problematic blocks

    def _normalize_code(self, code: str) -> str:
        """Normalize code for comparison (remove whitespace, comments, etc.)"""
        lines = []
        for line in code.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                # Remove extra whitespace
                line = ' '.join(line.split())
                lines.append(line)
        return '\n'.join(lines)

    def _find_duplicate_functions(self) -> list[dict[str, Any]]:
        """Find functions with identical names in multiple files"""
        duplicates = []

        for func_name, locations in self.function_signatures.items():
            if len(locations) > 1:
                # Check if these are actually different implementations
                unique_files = {loc[0] for loc in locations}
                if len(unique_files) > 1:
                    duplicates.append({
                        'function_name': func_name,
                        'locations': locations,
                        'duplicate_count': len(locations),
                        'files_affected': list(unique_files)
                    })

        return sorted(duplicates, key=lambda x: x['duplicate_count'], reverse=True)

    def _find_duplicate_code_blocks(self) -> list[dict[str, Any]]:
        """Find identical code blocks across files"""
        duplicates = []

        for code_hash, locations in self.code_hashes.items():
            if len(locations) > 1:
                unique_files = {loc[0] for loc in locations}
                if len(unique_files) > 1:
                    duplicates.append({
                        'code_hash': code_hash,
                        'locations': locations,
                        'duplicate_count': len(locations),
                        'files_affected': list(unique_files)
                    })

        return sorted(duplicates, key=lambda x: x['duplicate_count'], reverse=True)

    def _find_similar_patterns(self) -> list[dict[str, Any]]:
        """Find similar code patterns using fuzzy matching"""
        similar_patterns = []

        # This is a simplified implementation
        # In production, you'd use more sophisticated similarity algorithms

        return similar_patterns

    def generate_report(self, results: dict[str, Any]) -> str:
        """Generate a readable duplicate code report"""
        report = []
        report.append("=" * 60)
        report.append("DUPLICATE CODE DETECTION REPORT")
        report.append("=" * 60)
        report.append(f"Files Scanned: {results['total_files_scanned']}")
        report.append(f"Total Duplicates Found: {results['total_duplicates_found']}")
        report.append("")

        # Duplicate functions
        if results['duplicate_functions']:
            report.append("DUPLICATE FUNCTIONS:")
            report.append("-" * 30)
            for dup in results['duplicate_functions'][:10]:  # Top 10
                report.append(f"Function: {dup['function_name']}")
                report.append(f"Duplicates: {dup['duplicate_count']}")
                report.append(f"Files: {', '.join(dup['files_affected'])}")
                report.append("")

        # Duplicate code blocks
        if results['duplicate_code_blocks']:
            report.append("DUPLICATE CODE BLOCKS:")
            report.append("-" * 30)
            for dup in results['duplicate_code_blocks'][:10]:  # Top 10
                report.append(f"Hash: {dup['code_hash'][:16]}...")
                report.append(f"Duplicates: {dup['duplicate_count']}")
                report.append(f"Files: {', '.join(dup['files_affected'])}")
                report.append("")

        return "\n".join(report)


class DuplicationPrevention:
    """Prevents code duplication through automated checks"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.detector = DuplicateDetector(project_root)
        self.whitelist_patterns = set()
        self.max_allowed_duplicates = 2

    def add_whitelist_pattern(self, pattern: str):
        """Add a pattern to the duplication whitelist"""
        self.whitelist_patterns.add(pattern)

    def check_file_before_commit(self, file_path: str) -> dict[str, Any]:
        """Check a file for potential duplications before commit"""
        try:
            # Run duplicate detection on the specific file
            results = self.detector.scan_project()

            # Check if the file introduces new duplications
            file_duplicates = []
            for dup in results['duplicate_functions']:
                if file_path in dup['files_affected']:
                    file_duplicates.append(dup)

            return {
                'file_path': file_path,
                'introduces_duplicates': len(file_duplicates) > 0,
                'duplicates_found': file_duplicates,
                'recommendation': self._generate_recommendation(file_duplicates)
            }

        except Exception as e:
            logger.error(f"Error checking file {file_path}: {e}")
            return {
                'file_path': file_path,
                'introduces_duplicates': False,
                'error': str(e)
            }

    def _generate_recommendation(self, duplicates: list[dict[str, Any]]) -> str:
        """Generate recommendations for fixing duplicates"""
        if not duplicates:
            return "No duplicates detected."

        recommendations = []
        for dup in duplicates:
            func_name = dup['function_name']
            count = dup['duplicate_count']

            if count > self.max_allowed_duplicates:
                recommendations.append(
                    f"CRITICAL: Function '{func_name}' appears {count} times. "
                    f"Consider creating a utility function or base class."
                )
            else:
                recommendations.append(
                    f"WARNING: Function '{func_name}' appears {count} times. "
                    f"Monitor for further duplication."
                )

        return "\n".join(recommendations)

    def create_refactoring_plan(self, results: dict[str, Any]) -> dict[str, Any]:
        """Create a plan for refactoring duplicate code"""
        plan = {
            'high_priority': [],
            'medium_priority': [],
            'low_priority': [],
            'estimated_effort': 'medium',
            'suggested_actions': []
        }

        # Categorize duplicates by priority
        for dup in results['duplicate_functions']:
            if dup['duplicate_count'] >= 5:
                plan['high_priority'].append(dup)
            elif dup['duplicate_count'] >= 3:
                plan['medium_priority'].append(dup)
            else:
                plan['low_priority'].append(dup)

        # Generate suggested actions
        if plan['high_priority']:
            plan['suggested_actions'].append("Create base utility classes for highly duplicated functions")

        if plan['medium_priority']:
            plan['suggested_actions'].append("Consolidate medium-priority duplicates into shared modules")

        if plan['low_priority']:
            plan['suggested_actions'].append("Monitor low-priority duplicates for future consolidation")

        return plan


def scan_for_duplicates(project_root: str = None) -> dict[str, Any]:
    """Convenience function to scan for duplicates"""
    if project_root is None:
        project_root = Path.cwd()

    detector = DuplicateDetector(project_root)
    return detector.scan_project()


def generate_duplicate_report(project_root: str = None) -> str:
    """Generate a duplicate code report"""
    if project_root is None:
        project_root = Path.cwd()

    detector = DuplicateDetector(project_root)
    results = detector.scan_project()
    return detector.generate_report(results)


def check_for_new_duplicates(file_path: str, project_root: str = None) -> dict[str, Any]:
    """Check if a file introduces new duplicates"""
    if project_root is None:
        project_root = Path.cwd()

    prevention = DuplicationPrevention(project_root)
    return prevention.check_file_before_commit(file_path)
