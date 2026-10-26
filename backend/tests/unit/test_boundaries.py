"""Architecture rules are executable constraints, not only directory naming."""

import ast

from src.config.paths import ROOT


def test_domain_and_application_have_no_outward_imports():
    source = ROOT / "backend/src"
    for layer in ("domain", "application"):
        for file in (source / layer).rglob("*.py"):
            tree = ast.parse(file.read_text())
            for node in ast.walk(tree):
                imports = (
                    [node.module]
                    if isinstance(node, ast.ImportFrom)
                    else [alias.name for alias in node.names]
                    if isinstance(node, ast.Import)
                    else []
                )
                for module in filter(None, imports):
                    if layer == "domain":
                        assert not module.startswith("src.application"), (file, module)
                    assert not module.startswith(
                        (
                            "src.infrastructure",
                            "src.api",
                            "src.bootstrap",
                            "src.config",
                        )
                    ), (file, module)
                    assert module.split(".")[0] not in {
                        "subprocess",
                        "httpx",
                        "fastapi",
                        "sqlalchemy",
                        "boto3",
                        "temporalio",
                    }, (file, module)


def test_workspace_source_locations_are_real():
    assert (ROOT / "backend/pyproject.toml").is_file()
    assert (ROOT / "frontend/package.json").is_file()
    assert (ROOT / "infra").is_dir()
    assert not (ROOT / "services").exists()
    assert not (ROOT / "apps").exists()


def test_entrypoints_do_not_import_vendor_adapters_or_evaluate_checks():
    for layer in ["cli", "api"]:
        for file in (ROOT / "backend/src" / layer).rglob("*.py"):
            tree = ast.parse(file.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    assert not node.module.startswith(
                        (
                            "src.infrastructure",
                            "src.domain.assessment",
                            "src.domain.fixture_acceptance",
                        )
                    ), (file, node.module)
    assert not (ROOT / "backend/src/migratelens").exists()
