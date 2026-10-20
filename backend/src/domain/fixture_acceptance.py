"""Pure acceptance criteria for the synthetic fixture, independent of process transport."""

from src.domain.models import Check, Outcome

# These criteria are frozen and hashed before recipe execution, outside candidate directories.
OPERATIONS = [
    *({"kind": "get", "id": i} for i in ["ada", "null", "missing", "unknown", "boom", "a/b ?"]),
    {"kind": "list"},
    {"kind": "list", "size": 1},
    {"kind": "list", "size": 3},
    {"kind": "list", "size": 0},
]


def expected():
    def customer(identifier, name):
        return {
            "value": {
                "id": identifier,
                "name": name,
                "tier": "standard",
                "unrelatedName": "unrelated-company",
            }
        }

    return [
        customer("ada", "Ada Lovelace"),
        customer("null", None),
        customer("missing", None),
        {"value": None},
        {"error": "provider:503"},
        customer("a/b ?", "Ada Lovelace"),
        {"value": ["ada", "null"]},
        {"value": ["ada"]},
        {"value": ["ada", "null", "missing"]},
        {"error": "provider:400"},
    ]


def assess_behavior(
    actual: object,
    interactions: list[dict],
    scenario: str,
    version: str,
    check_id: str,
    reproduce: bool = False,
    duration_ms: int = 0,
) -> Check:
    if not isinstance(actual, list) or len(actual) != len(OPERATIONS):
        return Check(id=check_id, outcome=Outcome.ERROR, reason="Invalid consumer protocol result")
    target = {"path": [0, 1, 2, 4, 5], "field": [0, 5], "query": [7, 8]}[scenario]
    differences = [i for i, (a, b) in enumerate(zip(actual, expected(), strict=True)) if a != b]
    expected_prefix = (
        "/v2/customers/"
        if scenario == "path" and version == "new" and not reproduce
        else "/v1/customers/"
    )
    expected_paths = [
        expected_prefix + value
        for value in ["ada", "null", "missing", "unknown", "boom", "a%2Fb%20%3F"]
    ] + ["/customers"] * 4
    interaction_match = len(interactions) == len(OPERATIONS) and all(
        observed.get("method") == "GET" and observed.get("path") == path
        for observed, path in zip(interactions, expected_paths, strict=False)
    )
    query_key = (
        "limit" if scenario == "query" and version == "new" and not reproduce else "pageSize"
    )
    expected_queries: list[dict[str, list[str]]] = [{}] * 7 + [
        {query_key: ["1"]},
        {query_key: ["3"]},
        {query_key: ["0"]},
    ]
    interaction_match = interaction_match and all(
        observed.get("query") == query
        for observed, query in zip(interactions, expected_queries, strict=False)
    )
    passed = interaction_match and (
        any(i in target for i in differences) if reproduce else not differences
    )
    return Check(
        id=check_id,
        outcome=Outcome.PASS if passed else Outcome.FAIL,
        reason=(
            "Targeted incompatibility reproduced"
            if reproduce and passed
            else "External behavioral assertions matched"
            if passed
            else "Required behavior or provider interaction did not match"
        ),
        observations={
            "mismatch_indices": differences,
            "actual": actual,
            "interactions": interactions,
            "provider_build": f"northstar-{scenario}-{version}-1",
            "provider_kind": "fixture",
        },
        duration_ms=duration_ms,
    )
