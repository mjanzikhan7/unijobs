"""Docstring length limits, checked by walking the AST.

Keeps docstrings short, so the code stays easy to read. Every backend app is checked, except
tests and migrations. A docstring should say why, in a few plain sentences.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]

_EXCLUDED_DIRS = frozenset({"migrations", "tests"})

_INCLUDED_ROOTS = frozenset(
    {
        "accounts",
        "analytics",
        "api",
        "config",
        "crawler",
        "institutions",
        "jobs",
        "screening",
        "shared",
    }
)
_INCLUDED_FILES: frozenset[str] = frozenset()

_ADAPTER_MODULE_CEILING = 12
_MODULE_CEILING = 15
_CLASS_CEILING = 5
_FUNCTION_CEILING = 6
_PURE_DOMAIN_FUNCTION_CEILING = 10

_PURE_DOMAIN_FILES = frozenset({"jobs/domain.py", "screening/domain.py", "crawler/differ.py"})

_EXEMPT: frozenset[str] = frozenset(
    {
        "crawler/differ.py::<module>",
        "crawler/differ.py::vacancy_content_hash",
    }
)


@dataclass(frozen=True)
class _Violation:
    path: str
    qualname: str
    ceiling: int
    actual: int

    def __str__(self) -> str:
        return f"{self.path}::{self.qualname} — {self.actual} lines (ceiling {self.ceiling})"


def _docstring_line_count(node: ast.AST) -> int | None:
    doc = ast.get_docstring(node, clean=True)
    return None if doc is None else len(doc.splitlines())


def _in_scope(relative: Path) -> bool:
    if _EXCLUDED_DIRS & set(relative.parts):
        return False
    return relative.parts[0] in _INCLUDED_ROOTS or str(relative) in _INCLUDED_FILES


def _iter_backend_modules() -> list[Path]:
    return [
        path
        for path in sorted(BACKEND_ROOT.rglob("*.py"))
        if _in_scope(path.relative_to(BACKEND_ROOT))
    ]


def _module_ceiling(relative: Path) -> int:
    is_adapter = relative.parent == Path("crawler/adapters")
    return _ADAPTER_MODULE_CEILING if is_adapter else _MODULE_CEILING


def _function_ceiling(relative_str: str) -> int:
    is_pure_domain = relative_str in _PURE_DOMAIN_FILES
    return _PURE_DOMAIN_FUNCTION_CEILING if is_pure_domain else _FUNCTION_CEILING


def _check_module(path: Path) -> list[_Violation]:
    relative = path.relative_to(BACKEND_ROOT)
    relative_str = str(relative)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative_str)

    violations: list[_Violation] = []

    module_lines = _docstring_line_count(tree)
    if module_lines is not None:
        ceiling = _module_ceiling(relative)
        if module_lines > ceiling and f"{relative_str}::<module>" not in _EXEMPT:
            violations.append(_Violation(relative_str, "<module>", ceiling, module_lines))

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            lines = _docstring_line_count(node)
            exempt = f"{relative_str}::{node.name}" in _EXEMPT
            if lines is not None and lines > _CLASS_CEILING and not exempt:
                violations.append(_Violation(relative_str, node.name, _CLASS_CEILING, lines))
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            lines = _docstring_line_count(node)
            if lines is None:
                continue
            ceiling = _function_ceiling(relative_str)
            if lines > ceiling and f"{relative_str}::{node.name}" not in _EXEMPT:
                violations.append(_Violation(relative_str, node.name, ceiling, lines))

    return violations


def test_no_docstring_exceeds_its_ceiling() -> None:
    violations = [v for path in _iter_backend_modules() for v in _check_module(path)]

    assert not violations, "\n" + "\n".join(str(violation) for violation in violations)
