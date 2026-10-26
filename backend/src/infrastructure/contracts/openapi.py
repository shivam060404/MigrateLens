"""Bounded local OpenAPI subset. No remote ref resolution or silent fallback to oasdiff."""

import json
from src.domain.models import digest


def parse_contract(raw: bytes):
    if len(raw) > 1_000_000:
        raise ValueError("Contract exceeds byte budget")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    contract = json.loads(raw, object_pairs_hook=unique)
    if contract.get("openapi") not in {"3.0.3", "3.1.0", "3.1.1"}:
        raise ValueError("Unsupported OpenAPI dialect")

    def walk(value, depth=0):
        if depth > 30:
            raise ValueError("Contract exceeds depth budget")
        if isinstance(value, dict):
            if "$ref" in value:
                raise ValueError(
                    "References require an approved resolver; disabled in fixture subset"
                )
            for item in value.values():
                walk(item, depth + 1)
        elif isinstance(value, list):
            for item in value:
                walk(item, depth + 1)

    walk(contract)
    if not isinstance(contract.get("paths"), dict):
        raise ValueError("Missing paths object")
    return contract


def fixture_contract(scenario: str, version: str):
    endpoint = (
        "/v2/customers/{id}" if scenario == "path" and version == "new" else "/v1/customers/{id}"
    )
    fields = {
        "id": {"type": "string"},
        "name": {"type": ["string", "null"]},
        "tier": {"type": "string"},
        "unrelated": {"type": "object", "properties": {"name": {"type": "string"}}},
    }
    if scenario == "field" and version == "new":
        fields.pop("name")
        fields["profile"] = {
            "type": "object",
            "properties": {"displayName": {"type": ["string", "null"]}},
        }
    if scenario == "ambiguous":
        fields.pop("name")
        fields["nickname" if version == "new" else "legalName"] = {"type": "string"}
    if scenario == "amount-unit":
        fields["balance"] = {
            "type": "integer",
            "x-fixture-unit": "major" if version == "new" else "minor",
        }
    required = ["id"]
    if scenario == "required-field" and version == "new":
        fields["currency"] = {"type": "string"}
        required.append("currency")
    query = "limit" if scenario == "query" and version == "new" else "pageSize"
    if scenario == "pagination":
        query = "cursor" if version == "new" else "offset"
    parameter_schema = (
        {"type": "string"}
        if scenario == "pagination" and version == "new"
        else {"type": "integer", "minimum": 0, "default": 0}
        if scenario == "pagination"
        else {"type": "integer", "minimum": 1, "maximum": 3, "default": 2}
    )
    return {
        "openapi": "3.1.0",
        "info": {"title": "Fictional Northstar", "version": f"{scenario}-{version}-1"},
        "paths": {
            endpoint: {
                "get": {
                    "operationId": "getCustomer",
                    "parameters": [
                        {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}
                    ],
                    "responses": {
                        "200": {
                            "description": "Customer",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": fields,
                                        "required": required,
                                    }
                                }
                            },
                        },
                        "404": {"description": "Missing"},
                        "503": {"description": "Unavailable"},
                    },
                }
            },
            "/customers": {
                "get": {
                    "operationId": "listCustomers",
                    "parameters": [
                        {
                            "name": query,
                            "in": "query",
                            "schema": parameter_schema,
                        }
                    ],
                    "responses": {
                        "200": {"description": "Ordered customers"},
                        "400": {"description": "Invalid parameter"},
                    },
                }
            },
        },
    }


def detect(old: dict, new: dict):
    findings = []

    def walk(a, b, pointer):
        if isinstance(a, dict) and isinstance(b, dict):
            for key in sorted(a.keys() | b.keys()):
                if key in {"description", "summary", "info"}:
                    continue
                escaped = key.replace("~", "~0").replace("/", "~1")
                where = pointer + "/" + escaped
                if key not in b:
                    findings.append(
                        {"kind": "removed", "pointer": where, "runtime_breakage_status": "unknown"}
                    )
                elif key not in a:
                    findings.append(
                        {"kind": "added", "pointer": where, "runtime_breakage_status": "unknown"}
                    )
                else:
                    walk(a[key], b[key], where)
        elif a != b:
            findings.append(
                {"kind": "changed", "pointer": pointer, "runtime_breakage_status": "unknown"}
            )

    walk(old, new, "")
    return {
        "engine": "fixture-structural-1 (not oasdiff)",
        "old_hash": digest(old),
        "new_hash": digest(new),
        "findings": findings,
    }
