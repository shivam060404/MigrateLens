"""Composition root: the only place binding application ports to concrete adapters."""

import json
import platform
import subprocess
from pathlib import Path

from src.application.fixture_pipeline import FixturePipeline
from src.application.ports import FixtureInputs
from src.config.paths import ROOT
from src.infrastructure.security.fixture_admission import read_reviewed
from src.infrastructure.fixtures.negative_control import IncorrectTierAnalyzer
from src.application.ports import Analyzer
from src.config.settings import Settings
from src.domain.models import digest
from src.infrastructure.analysis.typescript import TypeScriptFixtureAnalyzer
from src.infrastructure.contracts.openapi import detect, fixture_contract, parse_contract
from src.infrastructure.storage.local_evidence import LocalEvidenceStore
from src.infrastructure.verification.fixture_verifier import ExternalFixtureVerifier


class FixtureContractDetector:
    detect = staticmethod(detect)


def implementation_fingerprint(root: Path = ROOT) -> str:
    """Bind named controller/adapter bytes and dependency/tool configuration to each run."""
    paths = sorted(
        set((root / "backend/src").rglob("*.py"))
        | set((root / "backend/analyzer-ts").glob("*.mjs"))
        | {
            root / "backend/analyzer-ts/tsconfig.json",
            root / "backend/analyzer-ts/package.json",
            root / "backend/pyproject.toml",
            root / "backend/requirements.lock",
            root / "pnpm-lock.yaml",
        }
    )
    return digest({str(path.relative_to(root)): digest(path.read_bytes()) for path in paths})


def create_fixture_pipeline(
    scenario: str, output: Path | None = None, *, wrong_patch: bool = False
) -> FixturePipeline:
    settings = Settings()
    old = fixture_contract(scenario, "old")
    new = fixture_contract(scenario, "new")
    if scenario == "unchanged":
        new = json.loads(json.dumps(old))
        new["info"]["description"] = "Documentation only"
    implementation = ROOT / "backend/src"
    inputs = FixtureInputs(
        source=read_reviewed(
            "fixtures/consumers/unsupported/dynamic.ts"
            if scenario == "dynamic"
            else "fixtures/consumers/northstar/src/integrations/customer/client.ts"
        ).decode(),
        mappings=json.loads(read_reviewed("fixtures/provider/mappings.json")),
        old_contract=parse_contract(json.dumps(old).encode()),
        new_contract=parse_contract(json.dumps(new).encode()),
        identities={
            "implementation": implementation_fingerprint(),
            "repair_profile": "deliberately-incorrect-tier" if wrong_patch else "deterministic",
            "test_suite": digest(
                (implementation / "infrastructure/verification/fixture_verifier.py").read_bytes()
                + (implementation / "domain/fixture_acceptance.py").read_bytes()
                + read_reviewed("fixtures/consumers/bridge.mjs")
            ),
            "provider_implementation": digest(
                (implementation / "infrastructure/fixtures/provider.py").read_bytes()
            ),
            "analyzer": digest(
                read_reviewed("backend/analyzer-ts/analyze.mjs")
                + read_reviewed("backend/analyzer-ts/recipes.mjs")
            ),
            "assessment": digest((implementation / "domain/assessment.py").read_bytes()),
            "runner_implementation": digest(
                (implementation / "infrastructure/execution/fixture_runner.py").read_bytes()
                + (implementation / "infrastructure/execution/process.py").read_bytes()
                + (implementation / "infrastructure/security/fixture_admission.py").read_bytes()
            ),
            "python": platform.python_version(),
            "runner": "fixture-host-1 (no image digest)",
            "node": subprocess.check_output(["node", "--version"], text=True).strip(),
        },
    )
    analyzer: Analyzer = TypeScriptFixtureAnalyzer()
    if wrong_patch:
        analyzer = IncorrectTierAnalyzer(analyzer)
    return FixturePipeline(
        inputs=inputs,
        analyzer=analyzer,
        verifier=ExternalFixtureVerifier(),
        detector=FixtureContractDetector(),
        store=LocalEvidenceStore(output) if output else None,
        emergency_stop=settings.emergency_stop,
    )


def run_fixture(scenario: str, output: Path | None = None, *, wrong_patch: bool = False):
    return create_fixture_pipeline(scenario, output, wrong_patch=wrong_patch).run(scenario)


def create_commands(output: Path):
    from src.application.commands import FixtureCommands

    return FixtureCommands(
        lambda scenario, negative: create_fixture_pipeline(scenario, output, wrong_patch=negative)
    )


def create_control_plane(settings: Settings):
    """Bind trusted identity and PostgreSQL only for an explicitly enabled API."""
    from sqlalchemy import create_engine
    from src.application.control import ControlService
    from src.infrastructure.identity.tokens import TokenVerifier
    from src.infrastructure.persistence.database import Database
    from src.infrastructure.persistence.repository import PostgresRepository
    from src.infrastructure.storage.artifacts import LocalArtifactStore

    if (
        not settings.control_api_enabled
        or not settings.identity_public_key_path
        or not settings.database_url
    ):
        raise ValueError("Control API is disabled")
    public_key = Path(settings.identity_public_key_path).read_bytes()
    verifier = TokenVerifier(public_key, settings.identity_issuer, settings.identity_audience)
    engine = create_engine(settings.database_url, pool_pre_ping=True, hide_parameters=True)
    service = ControlService(
        PostgresRepository(Database(engine)),
        artifact_reader=LocalArtifactStore(ROOT / settings.artifact_root),
        emergency_stop=settings.emergency_stop,
    )
    return service, verifier, engine
