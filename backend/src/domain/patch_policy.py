import difflib
from pathlib import PurePosixPath
from src.domain.models import Policy, Check, Outcome


def validate_path(path: str):
    p = PurePosixPath(path)
    if not path or p.is_absolute() or ".." in p.parts or "\\" in path or str(p) != path:
        raise ValueError("Unsafe or non-canonical path")


def check_patch(base: str, candidate: str, path: str, policy: Policy) -> Check:
    try:
        validate_path(path)
        if path != policy.allowed_path:
            raise ValueError("Path outside frozen integration allowlist")
        changed = [
            line
            for line in difflib.ndiff(base.splitlines(), candidate.splitlines())
            if line[:2] in {"+ ", "- "}
        ]
        if not changed or len(changed) > policy.max_changed_lines:
            raise ValueError("Empty or over-budget patch")
        for line in changed:
            if line.startswith("+ ") and any(
                x in line
                for x in [
                    "@ts-ignore",
                    "@ts-nocheck",
                    " as any",
                    "process.env",
                    "node:",
                    "require(",
                    "eval(",
                    "https://",
                    "http://",
                    "test.skip",
                    "it.skip",
                ]
            ):
                raise ValueError("Forbidden code or privilege expansion")
        return Check(
            id="POLICY",
            outcome=Outcome.PASS,
            reason="Single registered fixture integration path; bounded edit; no protected artifacts changed",
        )
    except ValueError as exc:
        return Check(id="POLICY", outcome=Outcome.FAIL, reason=str(exc))
