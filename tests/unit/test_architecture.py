import ast
import subprocess
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ArchitectureTests(unittest.TestCase):
    def test_layer_dependencies_point_inward(self) -> None:
        forbidden = {
            "domain": ("app.application", "app.infrastructure", "app.presentation", "app.core", "app.bootstrap", "streamlit", "sqlite3", "ffmpeg"),
            "application": ("app.infrastructure", "app.presentation", "app.core", "app.bootstrap", "streamlit", "sqlite3", "ffmpeg"),
            "infrastructure": ("app.presentation", "app.bootstrap", "streamlit"),
            "presentation": ("app.infrastructure", "app.bootstrap", "app.core"),
            "core": ("app.domain", "app.application", "app.infrastructure", "app.presentation", "streamlit"),
        }
        for layer, prefixes in forbidden.items():
            for path in (PROJECT_ROOT / "app" / layer).rglob("*.py"):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                modules = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
                modules.extend(alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names)
                for module in modules:
                    with self.subTest(file=path.name, dependency=module):
                        self.assertFalse(any(module == prefix or module.startswith(prefix + ".") for prefix in prefixes))

    def test_application_imports_without_streamlit(self) -> None:
        result = subprocess.run(
            [sys.executable, "-B", "-c", "import sys; import app.application.package_preparation, app.application.package_production, app.application.episode_delivery; assert 'streamlit' not in sys.modules"],
            cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_domain_and_application_only_use_standard_library_and_inner_layers(self) -> None:
        for layer in ("domain", "application"):
            for path in (PROJECT_ROOT / "app" / layer).rglob("*.py"):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
                imports.extend(alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names)
                for module in imports:
                    with self.subTest(file=path.name, module=module):
                        self.assertTrue(module.startswith("app.") or module.split(".")[0] in sys.stdlib_module_names)

    def test_no_circular_internal_imports(self) -> None:
        graph: dict[str, set[str]] = {}
        for path in (PROJECT_ROOT / "app").rglob("*.py"):
            parts = list(path.relative_to(PROJECT_ROOT).with_suffix("").parts)
            if parts[-1] == "__init__":
                parts.pop()
            module = ".".join(parts)
            graph[module] = {
                node.module for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
                if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app.")
            }

        visited: set[str] = set()

        def visit(module: str, ancestors: set[str]) -> None:
            self.assertNotIn(module, ancestors, f"Circular dependency: {module}")
            if module in visited:
                return
            for dependency in graph.get(module, set()):
                visit(dependency, ancestors | {module})
            visited.add(module)

        for module in graph:
            visit(module, set())
