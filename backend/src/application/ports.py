"""Capabilities used by application services; adapters are wired only in bootstrap."""

from dataclasses import dataclass
from typing import Protocol

from src.domain.models import Check, ValidationEvidence


@dataclass(frozen=True)
class FixtureInputs:
    source: str
    mappings: dict
    old_contract: dict
    new_contract: dict
    identities: dict[str, str]


class Analyzer(Protocol):
    def analyze(self, source: str, scenario: str, repair: bool = False) -> dict: ...


class Verifier(Protocol):
    def behavior(
        self, source: str, scenario: str, version: str, check_id: str, reproduce: bool = False
    ) -> Check: ...

    def static_check(self, source: str) -> Check: ...


class ContractDetector(Protocol):
    def detect(self, old: dict, new: dict) -> dict: ...


class EvidenceStore(Protocol):
    def export(self, evidence: ValidationEvidence, dossier: dict, patch: str) -> None: ...
