#!/usr/bin/env python3
"""Validate and interpret the bounded Openweight Constellation expedition.

This module is deliberately local, deterministic, stdlib-only, and read-only.
It validates an authored JSON contract against its reviewed JSON Schema and
can return one advisory Nen card from explicitly declared evidence. It never
reads repository prose, discovers signals, calls a network, executes a card,
or creates authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import stat
from pathlib import Path
from typing import Any, Iterable, Sequence


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCHEMA_PATH = HERE / "expedition.schema.json"
CONTRACT_PATH = HERE / "expeditions" / "openweight-constellation.json"
DIST_DIR = HERE / "dist"
SITE_DIR = ROOT / "site" / "operations" / "dark-continent-ai"
GENERATED_CONTRACT = "openweight-constellation-expedition.json"
GENERATED_SCHEMA = "expedition.schema.json"

CONTRACT_SCHEMA = "kingdom.dark-continent-expedition/v1"
SCHEMA_ID = "https://kingdom.local/schemas/dark-continent-expedition-v1.json"
INTERPRETATION_SCHEMA = "kingdom.nen-expedition-interpretation/v1"
MAX_FILE_BYTES = 256_000
MAX_DECLARED_SIGNALS = 8

PRINCIPLES = ("light", "truth", "consent", "no conquest")
VIRTUES = (
    "honesty",
    "beauty",
    "collaboration",
    "understanding",
    "constructive mutual benefit",
)
TECHNIQUE_SIGNALS = {
    "contract-mantle": ("requirements-may-drift", "single-stable-step"),
    "dependency-perimeter": ("blast-radius-unknown", "perimeter-already-proven"),
    "concealed-trace": ("hidden-seam", "fix-already-authorized"),
    "critical-path-forge": ("one-dominant-blocker", "blocker-still-ambiguous"),
    "godspeed-loop": ("finite-repetitive-loop", "novel-stimulus"),
    "smoke-squad": ("independent-workstreams", "overlapping-writes"),
    "verification-ledger": ("verification-debt", "critical-debt-paid"),
    "vow-forge": ("design-bounded-workflow", "general-capability-request"),
}
HUMAN_ROUTES = {
    "public-hub": "https://openweight-constellation.vercel.app/",
    "worlds": "https://openweight-constellation.vercel.app/#worlds",
    "virtue-loop": "https://openweight-constellation.vercel.app/#virtue-loop",
    "protocol": "https://openweight-constellation.vercel.app/constellation-protocol.json",
    "privacy": "https://openweight-constellation.vercel.app/privacy",
    "terms": "https://openweight-constellation.vercel.app/terms",
}
MACHINE_ROUTES = {
    "mcp-health": "https://openweight-constellation-mcp.axiepro.workers.dev/health",
    "mcp-manifest": "https://openweight-constellation-mcp.axiepro.workers.dev/manifest.json",
    "mcp-endpoint": "https://openweight-constellation-mcp.axiepro.workers.dev/mcp",
}
TOOL_SCHEMAS = {
    "map_constellation": "openweight.constellation/world-map@1",
    "compose_virtue_lens": "karma.virtue-receipt/v1",
    "trace_idea": "openweight.constellation/idea-trace@1",
}
ROOT_FIELDS = {
    "schema",
    "id",
    "operation",
    "name",
    "status",
    "interpretations",
    "realm",
    "boundaries",
    "budget",
    "routes",
    "protocol",
    "feedback_loop",
    "nen_route",
    "crownseed_relationship",
    "proof",
    "exit",
    "non_claims",
}
SUPPORTED_SCHEMA_KEYWORDS = {
    "$schema",
    "$id",
    "$ref",
    "$defs",
    "title",
    "type",
    "additionalProperties",
    "required",
    "properties",
    "const",
    "enum",
    "items",
    "minItems",
    "maxItems",
    "uniqueItems",
    "minLength",
    "maxLength",
    "pattern",
}


class ExpeditionError(ValueError):
    """A contract, schema, or interpretation exceeded the expedition vow."""


def canonical_json(value: Any) -> bytes:
    """Return stable strict JSON bytes for equality, hashes, and output."""

    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def pretty_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
        allow_nan=False,
    ) + "\n"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def reject_constant(token: str) -> None:
    raise ExpeditionError(f"non-finite JSON number: {token}")


def pairs_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ExpeditionError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def read_regular(path: Path, label: str) -> bytes:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise ExpeditionError(f"{label} is missing: {path}") from error
    if not stat.S_ISREG(metadata.st_mode):
        raise ExpeditionError(f"{label} must be a regular non-symlink file: {path}")
    if metadata.st_size > MAX_FILE_BYTES:
        raise ExpeditionError(f"{label} exceeds {MAX_FILE_BYTES} bytes")
    try:
        data = path.read_bytes()
    except OSError as error:
        raise ExpeditionError(f"{label} cannot be read: {path}") from error
    if len(data) > MAX_FILE_BYTES:
        raise ExpeditionError(f"{label} exceeds {MAX_FILE_BYTES} bytes")
    return data


def parse_json(data: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            data,
            object_pairs_hook=pairs_object,
            parse_constant=reject_constant,
        )
    except ExpeditionError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ExpeditionError(f"{label} is not strict UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise ExpeditionError(f"{label} root must be an object")
    return value


def same_json(left: Any, right: Any) -> bool:
    try:
        return canonical_json(left) == canonical_json(right)
    except (TypeError, ValueError):
        return False


def json_type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
        )
    if expected == "null":
        return value is None
    raise ExpeditionError(f"unsupported JSON Schema type: {expected}")


def resolve_ref(root_schema: dict[str, Any], reference: str) -> dict[str, Any]:
    if not reference.startswith("#/"):
        raise ExpeditionError(f"only local JSON Schema refs are allowed: {reference}")
    value: Any = root_schema
    for token in reference[2:].split("/"):
        key = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(value, dict) or key not in value:
            raise ExpeditionError(f"unresolved JSON Schema ref: {reference}")
        value = value[key]
    if not isinstance(value, dict):
        raise ExpeditionError(f"JSON Schema ref is not an object: {reference}")
    return value


def validate_instance(
    value: Any,
    schema: dict[str, Any],
    root_schema: dict[str, Any],
    path: str = "$",
) -> None:
    """Evaluate the small, fail-closed JSON Schema subset used by this contract."""

    unknown = set(schema) - SUPPORTED_SCHEMA_KEYWORDS
    if unknown:
        raise ExpeditionError(
            f"{path} schema uses unsupported keywords: {', '.join(sorted(unknown))}"
        )
    if "$ref" in schema:
        if set(schema) != {"$ref"}:
            raise ExpeditionError(f"{path} combines $ref with unsupported sibling keywords")
        validate_instance(value, resolve_ref(root_schema, schema["$ref"]), root_schema, path)
        return
    if "const" in schema and not same_json(value, schema["const"]):
        raise ExpeditionError(f"{path} differs from its reviewed constant")
    if "enum" in schema and not any(same_json(value, item) for item in schema["enum"]):
        raise ExpeditionError(f"{path} is outside its reviewed enum")

    expected_type = schema.get("type")
    if expected_type is not None and not json_type_matches(value, expected_type):
        raise ExpeditionError(f"{path} must be JSON type {expected_type}")

    if isinstance(value, dict):
        required = schema.get("required", [])
        missing = [key for key in required if key not in value]
        if missing:
            raise ExpeditionError(f"{path} is missing required fields: {', '.join(missing)}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extra = set(value) - set(properties)
            if extra:
                raise ExpeditionError(
                    f"{path} has unreviewed fields: {', '.join(sorted(extra))}"
                )
        for key, item in value.items():
            if key in properties:
                validate_instance(item, properties[key], root_schema, f"{path}.{key}")

    if isinstance(value, list):
        minimum = schema.get("minItems")
        maximum = schema.get("maxItems")
        if minimum is not None and len(value) < minimum:
            raise ExpeditionError(f"{path} has fewer than {minimum} items")
        if maximum is not None and len(value) > maximum:
            raise ExpeditionError(f"{path} has more than {maximum} items")
        if schema.get("uniqueItems"):
            encoded = [canonical_json(item) for item in value]
            if len(encoded) != len(set(encoded)):
                raise ExpeditionError(f"{path} contains duplicate items")
        item_schema = schema.get("items")
        if item_schema is not None:
            for index, item in enumerate(value):
                validate_instance(item, item_schema, root_schema, f"{path}[{index}]")

    if isinstance(value, str):
        minimum = schema.get("minLength")
        maximum = schema.get("maxLength")
        if minimum is not None and len(value) < minimum:
            raise ExpeditionError(f"{path} is shorter than {minimum} characters")
        if maximum is not None and len(value) > maximum:
            raise ExpeditionError(f"{path} is longer than {maximum} characters")
        pattern = schema.get("pattern")
        if pattern is not None and re.search(pattern, value) is None:
            raise ExpeditionError(f"{path} does not match its reviewed pattern")


def exact_route_map(routes: Any, label: str) -> dict[str, str]:
    if not isinstance(routes, list):
        raise ExpeditionError(f"{label} routes must be a list")
    result: dict[str, str] = {}
    for route in routes:
        route_id = route["id"]
        if route_id in result:
            raise ExpeditionError(f"duplicate {label} route id: {route_id}")
        result[route_id] = route["url"]
    return result


def validate_domain_invariants(contract: dict[str, Any], schema: dict[str, Any]) -> None:
    """Check invariants that are semantic rather than merely structural."""

    if schema.get("$id") != SCHEMA_ID:
        raise ExpeditionError("unexpected expedition JSON Schema id")
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        raise ExpeditionError("unexpected JSON Schema dialect")
    if set(schema.get("required", [])) != ROOT_FIELDS:
        raise ExpeditionError("expedition JSON Schema root fields changed")
    if schema.get("additionalProperties") is not False:
        raise ExpeditionError("expedition JSON Schema must fail closed on extra fields")
    if contract["schema"] != CONTRACT_SCHEMA:
        raise ExpeditionError("unexpected expedition contract schema")
    if contract["boundaries"]["principles"] != list(PRINCIPLES):
        raise ExpeditionError("expedition principles changed order or meaning")
    if contract["feedback_loop"]["virtues"] != list(VIRTUES):
        raise ExpeditionError("virtue feedback vocabulary changed")
    if contract["routes"]["references_only"] is not True:
        raise ExpeditionError("public routes must remain inert references")
    if exact_route_map(contract["routes"]["human"], "human") != HUMAN_ROUTES:
        raise ExpeditionError("human routes differ from the reviewed public map")
    if exact_route_map(contract["routes"]["machine"], "machine") != MACHINE_ROUTES:
        raise ExpeditionError("machine routes differ from the reviewed public map")

    tools = contract["protocol"]["tools"]
    actual_tools = {tool["name"]: tool["result_schema"] for tool in tools}
    if actual_tools != TOOL_SCHEMAS or len(tools) != len(TOOL_SCHEMAS):
        raise ExpeditionError("MCP tools differ from the reviewed read-only contract")
    for tool in tools:
        if (
            tool["read_only"] is not True
            or tool["destructive"] is not False
            or tool["open_world"] is not False
        ):
            raise ExpeditionError(f"MCP tool annotations became unsafe: {tool['name']}")

    route = contract["nen_route"]
    techniques = route["techniques"]
    ids = [technique["id"] for technique in techniques]
    if ids != list(TECHNIQUE_SIGNALS):
        raise ExpeditionError("Nen processing order or technique set changed")
    trigger_signals: set[str] = set()
    anti_signals: set[str] = set()
    for technique in techniques:
        expected_trigger, expected_anti = TECHNIQUE_SIGNALS[technique["id"]]
        if technique["trigger"]["signal"] != expected_trigger:
            raise ExpeditionError(f"trigger changed for {technique['id']}")
        if technique["anti_trigger"]["signal"] != expected_anti:
            raise ExpeditionError(f"anti-trigger changed for {technique['id']}")
        trigger_signals.add(expected_trigger)
        anti_signals.add(expected_anti)
    if len(trigger_signals) != len(techniques) or len(anti_signals) != len(techniques):
        raise ExpeditionError("Nen trigger signals must be unique")
    if trigger_signals & anti_signals:
        raise ExpeditionError("a Nen signal cannot be both trigger and anti-trigger")
    if route["automatic_activation"] is not False or route["order_is_rank"] is not False:
        raise ExpeditionError("Nen route cannot activate itself or create rank")

    false_boundaries = {
        key
        for key, value in contract["boundaries"].items()
        if key != "principles" and value is not False
    }
    if false_boundaries:
        raise ExpeditionError(
            "prohibited expedition effects became enabled: "
            + ", ".join(sorted(false_boundaries))
        )
    if any(contract["budget"][key] != 0 for key in ("network_calls", "deployments", "automatic_retries")):
        raise ExpeditionError("expedition external-effect budget must remain zero")
    if contract["budget"]["techniques_per_interpretation"] != 1:
        raise ExpeditionError("an interpretation may return only one Nen technique")
    if contract["feedback_loop"]["person_scoring"] is not False:
        raise ExpeditionError("virtue feedback cannot score people")
    if contract["feedback_loop"]["automatic_enforcement"] is not False:
        raise ExpeditionError("virtue feedback cannot enforce itself")
    crownseed = contract["crownseed_relationship"]
    if (
        crownseed["mode"] != "read-only-complement"
        or crownseed["activation"] is not False
        or crownseed["authority"] is not False
    ):
        raise ExpeditionError("Crownseed boundary changed")


def load_contract() -> tuple[dict[str, Any], dict[str, Any]]:
    schema_data = read_regular(SCHEMA_PATH, "expedition JSON Schema")
    contract_data = read_regular(CONTRACT_PATH, "expedition contract")
    schema = parse_json(schema_data, "expedition JSON Schema")
    contract = parse_json(contract_data, "expedition contract")
    validate_instance(contract, schema, schema)
    validate_domain_invariants(contract, schema)
    return contract, schema


def interpret_technique(
    contract: dict[str, Any],
    declared_signals: Sequence[str],
) -> dict[str, Any]:
    """Return one advisory card, or halt, from explicit controlled evidence."""

    if isinstance(declared_signals, (str, bytes)) or not isinstance(
        declared_signals, Sequence
    ):
        raise ExpeditionError("declared signals must be an explicit sequence")
    signals = list(declared_signals)
    if len(signals) > MAX_DECLARED_SIGNALS:
        raise ExpeditionError(
            f"at most {MAX_DECLARED_SIGNALS} explicit signals may be declared"
        )
    if any(not isinstance(signal, str) or not signal for signal in signals):
        raise ExpeditionError("every declared signal must be non-empty text")
    if len(signals) != len(set(signals)):
        raise ExpeditionError("declared signals must be unique")

    techniques = contract["nen_route"]["techniques"]
    trigger_map = {
        technique["trigger"]["signal"]: technique for technique in techniques
    }
    anti_signals = {
        technique["anti_trigger"]["signal"] for technique in techniques
    }
    known_signals = set(trigger_map) | anti_signals
    unknown = set(signals) - known_signals
    if unknown:
        raise ExpeditionError(
            "unknown explicit signals halt interpretation: "
            + ", ".join(sorted(unknown))
        )

    candidates = [trigger_map[signal] for signal in signals if signal in trigger_map]
    present_anti = sorted(set(signals) & anti_signals)
    result: dict[str, Any] = {
        "schema": INTERPRETATION_SCHEMA,
        "status": "halted",
        "declared_signals": sorted(signals),
        "technique": None,
        "reason": "",
        "automatic_activation": False,
        "authority_granted": False,
        "action_executed": False,
        "non_claim": "This is an interpretation of explicit task evidence, not permission or execution.",
    }
    if present_anti:
        result["reason"] = "anti-trigger:" + ",".join(present_anti)
        return result
    if not candidates:
        result["status"] = "no-match"
        result["reason"] = "no-reviewed-trigger"
        return result
    if len(candidates) > 1:
        result["reason"] = "multiple-triggers-require-fresh-judgment"
        return result

    technique = candidates[0]
    result.update(
        {
            "status": "advisory",
            "technique": {
                "id": technique["id"],
                "name": technique["name"],
                "condition": technique["condition"],
                "budget": technique["budget"],
                "breach": technique["breach"],
                "proof": technique["proof"],
                "exit": technique["exit"],
            },
            "reason": "single-explicit-reviewed-trigger",
        }
    )
    return result


def compare_bytes(left: Path, right: Path, label: str) -> None:
    if read_regular(left, f"{label} source") != read_regular(
        right, f"{label} generated copy"
    ):
        raise ExpeditionError(f"{label} generated copy differs byte-for-byte")


def verify_generated() -> dict[str, Any]:
    contract, schema = load_contract()
    for directory in (DIST_DIR, SITE_DIR):
        compare_bytes(
            CONTRACT_PATH,
            directory / GENERATED_CONTRACT,
            f"{directory.name} expedition contract",
        )
        compare_bytes(
            SCHEMA_PATH,
            directory / GENERATED_SCHEMA,
            f"{directory.name} expedition schema",
        )
        page = read_regular(directory / "index.html", f"{directory.name} page").decode(
            "utf-8"
        )
        for token in (
            GENERATED_CONTRACT,
            GENERATED_SCHEMA,
            "Openweight Constellation",
            "Nen route",
            "This local page does not fetch them, activate a workflow, grant authority, rank anyone, or deploy anything.",
        ):
            if token not in page:
                raise ExpeditionError(
                    f"{directory.name} page lost expedition token: {token}"
                )
        lowered = page.lower()
        for active_seam in ("<script", "<form", "javascript:", "fetch("):
            if active_seam in lowered:
                raise ExpeditionError(
                    f"{directory.name} page gained active seam: {active_seam}"
                )
        if re.search(r"\son[a-z0-9_-]+\s*=", lowered):
            raise ExpeditionError(
                f"{directory.name} page gained an event-handler attribute"
            )
        if 'src="http' in lowered or "src='http" in lowered:
            raise ExpeditionError(
                f"{directory.name} page gained a remote source dependency"
            )
        for routes in contract["routes"].values():
            if not isinstance(routes, list):
                continue
            for route in routes:
                if route["url"] not in page:
                    raise ExpeditionError(
                        f"{directory.name} page lost reviewed route: {route['id']}"
                    )
        for technique in contract["nen_route"]["techniques"]:
            if technique["name"] not in page:
                raise ExpeditionError(
                    f"{directory.name} page lost Nen card: {technique['id']}"
                )
        for virtue in contract["feedback_loop"]["virtues"]:
            if virtue not in page:
                raise ExpeditionError(
                    f"{directory.name} page lost virtue wording: {virtue}"
                )
    return {
        "schema": "kingdom.dark-continent-expedition-verification/v1",
        "expedition": contract["id"],
        "contract_sha256": sha256_bytes(read_regular(CONTRACT_PATH, "contract")),
        "schema_sha256": sha256_bytes(read_regular(SCHEMA_PATH, "schema")),
        "techniques": len(contract["nen_route"]["techniques"]),
        "generated_copies": 4,
        "network_calls": 0,
        "status": "verified",
    }


def summary(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "kingdom.dark-continent-expedition-summary/v1",
        "expedition": contract["id"],
        "status": contract["status"],
        "human_routes": len(contract["routes"]["human"]),
        "machine_routes": len(contract["routes"]["machine"]),
        "techniques": len(contract["nen_route"]["techniques"]),
        "automatic_activation": False,
        "network_calls": 0,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate the local expedition or interpret explicit evidence."
    )
    parser.add_argument(
        "--check-generated",
        action="store_true",
        help="also require byte-identical dist and site copies",
    )
    parser.add_argument(
        "--signal",
        action="append",
        default=[],
        help="explicit reviewed task-shape signal; returns advice only",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        contract, _schema = load_contract()
        if args.check_generated and args.signal:
            raise ExpeditionError("--check-generated and --signal cannot be combined")
        if args.check_generated:
            result = verify_generated()
        elif args.signal:
            result = interpret_technique(contract, args.signal)
        else:
            result = summary(contract)
        print(pretty_json(result), end="")
        return 0
    except ExpeditionError as error:
        parser.exit(2, f"expedition validation failed: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
