#!/usr/bin/env python3
"""Validate and render a bounded Lanternhouse comparison manifest.

This program only reads JSON, validates declarations, and renders Markdown. It
has no code-execution, network, model-call, mutation, or publication path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


SCHEMA_ID = "kingdom.lanternhouse/v1"
MAX_FILE_BYTES = 128_000
MAX_TEXT = 1_000
MAX_DEPTH = 12
NON_CLAIMS = [
    "Validation checks structure, not truth, permission, consent, or adoption readiness.",
    "Validation cannot prove free text safe or private reasoning preserved; private traces stay outside the manifest.",
    "The practice does not authorize model calls, mutation, deployment, publication, or external action.",
    "A ready disposition is an internally consistent declaration bounded to the named house, lamp, trial, lease, and domain.",
]

HOUSE_FINGERPRINT_FIELDS = (
    "house_id",
    "provider",
    "model",
    "runtime",
    "adapter",
    "prompt_policy",
    "tool_policy",
    "memory_policy",
    "sandbox",
    "sampling",
    "effort",
    "instructions_locator",
    "instructions_sha256",
    "tools_locator",
    "tools_sha256",
    "preservation_policy_locator",
    "preservation_policy_sha256",
)

FORBIDDEN_PUBLIC_KEYS = {
    "analysis",
    "chainofthought",
    "cot",
    "deliberation",
    "hiddenstate",
    "internalreasoning",
    "internalmonologue",
    "rawreasoning",
    "rawthinking",
    "reasoning",
    "reasoningcontent",
    "reasoningdetails",
    "scratchpad",
    "thinking",
    "thought",
    "thoughts",
}
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bgh(?:p|o|u|s|r)_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    re.compile(
        r"(?i)\b(?:api[_-]?key|token|secret|password|credential)"
        r"\s*[:=]\s*[\"']?[^\s\"']{8,}"
    ),
)


class LanternError(ValueError):
    """The public manifest violates the Lanternhouse contract."""


@dataclass(frozen=True)
class Validation:
    digest: str
    disposition: str
    quarantined: bool
    quarantine_reasons: tuple[str, ...]


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def digest_value(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def house_fingerprint(house: dict[str, Any]) -> str:
    """Derive the fingerprint of every declared public house dimension."""

    return digest_value({key: house[key] for key in HOUSE_FINGERPRINT_FIELDS})


def rubric_fingerprint(criteria: list[dict[str, Any]]) -> str:
    """Derive the digest a witness precommits before trials."""

    return digest_value(criteria)


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LanternError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_manifest(path: Path) -> dict[str, Any]:
    """Read one bounded, regular JSON file without following its final symlink."""

    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise LanternError(f"manifest is missing or unsafe: {path}: {error}") from error
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise LanternError("manifest must be a regular file")
        if metadata.st_size > MAX_FILE_BYTES:
            raise LanternError(f"manifest exceeds {MAX_FILE_BYTES} bytes")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            raw = handle.read(MAX_FILE_BYTES + 1)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(raw) > MAX_FILE_BYTES:
        raise LanternError(f"manifest exceeds {MAX_FILE_BYTES} bytes")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                LanternError(f"non-finite JSON number: {token}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LanternError(f"invalid UTF-8 JSON: {error}") from error
    if not isinstance(value, dict):
        raise LanternError("manifest root must be an object")
    return value


def _clean_public_text(value: str, path: str, *, key: bool = False) -> None:
    if not isinstance(value, str):
        raise LanternError(f"{path} must be text")
    limit = 80 if key else MAX_TEXT
    if len(value) > limit:
        raise LanternError(f"{path} exceeds {limit} characters")
    if key and not value:
        raise LanternError(f"{path} contains an empty key")
    if any((ord(char) < 32 and char not in "\t\n") or ord(char) == 127 for char in value):
        raise LanternError(f"{path} contains control characters")
    for pattern in SECRET_PATTERNS:
        if pattern.search(value):
            raise LanternError(f"{path} contains secret-shaped material")


def _public_walk(value: Any, path: str = "$", depth: int = 0) -> None:
    """Reject public reasoning fields, secrets, odd values, and depth bombs."""

    if depth > MAX_DEPTH:
        raise LanternError(f"{path} exceeds maximum nesting depth {MAX_DEPTH}")
    if isinstance(value, dict):
        for key, child in value.items():
            _clean_public_text(key, f"{path} key", key=True)
            normalized = re.sub(r"[^a-z0-9]", "", key.lower())
            if normalized in FORBIDDEN_PUBLIC_KEYS:
                raise LanternError(f"{path}.{key} is a forbidden raw-reasoning field")
            _public_walk(child, f"{path}.{key}", depth + 1)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _public_walk(child, f"{path}[{index}]", depth + 1)
    elif isinstance(value, str):
        _clean_public_text(value, path)
    elif value is not None and not isinstance(value, (bool, int)):
        raise LanternError(f"{path} contains an unsupported JSON value")


@lru_cache(maxsize=1)
def _schema_document() -> dict[str, Any]:
    try:
        return json.loads(
            Path(__file__).with_name("schema.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as error:
        raise LanternError(f"reviewed schema is unavailable: {error}") from error


def _schema_type_matches(value: Any, expected: str) -> bool:
    return {
        "object": lambda: isinstance(value, dict),
        "array": lambda: isinstance(value, list),
        "string": lambda: isinstance(value, str),
        "integer": lambda: isinstance(value, int) and not isinstance(value, bool),
        "boolean": lambda: isinstance(value, bool),
        "null": lambda: value is None,
    }[expected]()


def _validate_schema(
    value: Any, rule: dict[str, Any], path: str, root: dict[str, Any]
) -> None:
    """Validate the small reviewed JSON-Schema subset used by schema.json."""

    if "$ref" in rule:
        prefix = "#/$defs/"
        reference = rule["$ref"]
        if not reference.startswith(prefix):
            raise LanternError(f"unsupported schema reference: {reference}")
        _validate_schema(value, root["$defs"][reference[len(prefix) :]], path, root)
        return
    if "anyOf" in rule:
        failures = []
        for option in rule["anyOf"]:
            try:
                _validate_schema(value, option, path, root)
                return
            except LanternError as error:
                failures.append(str(error))
        raise LanternError(f"{path} does not match an allowed shape")
    if "const" in rule and canonical_json(value) != canonical_json(rule["const"]):
        raise LanternError(f"{path} must equal {rule['const']!r}")
    if "enum" in rule and not any(
        canonical_json(value) == canonical_json(option) for option in rule["enum"]
    ):
        raise LanternError(f"{path} must be one of: {', '.join(map(str, rule['enum']))}")
    expected = rule.get("type")
    if expected and not _schema_type_matches(value, expected):
        raise LanternError(f"{path} must be {expected}")

    if isinstance(value, dict):
        missing = set(rule.get("required", ())) - set(value)
        if missing:
            raise LanternError(f"{path} is missing: {', '.join(sorted(missing))}")
        properties = rule.get("properties", {})
        extra = set(value) - set(properties)
        if extra and rule.get("additionalProperties") is False:
            raise LanternError(f"{path} has unknown fields: {', '.join(sorted(extra))}")
        for key, child in value.items():
            if key in properties:
                _validate_schema(child, properties[key], f"{path}.{key}", root)
    elif isinstance(value, list):
        minimum, maximum = rule.get("minItems", 0), rule.get("maxItems")
        if len(value) < minimum or (maximum is not None and len(value) > maximum):
            ceiling = "∞" if maximum is None else maximum
            raise LanternError(f"{path} must contain {minimum}..{ceiling} items")
        if rule.get("uniqueItems"):
            encoded = [canonical_json(item) for item in value]
            if len(encoded) != len(set(encoded)):
                raise LanternError(f"{path} must not contain duplicates")
        if "items" in rule:
            for index, child in enumerate(value):
                _validate_schema(child, rule["items"], f"{path}[{index}]", root)
    elif isinstance(value, str):
        if len(value) < rule.get("minLength", 0):
            raise LanternError(f"{path} must not be empty")
        if len(value) > rule.get("maxLength", MAX_TEXT):
            raise LanternError(f"{path} is too long")
        if "pattern" in rule and not re.search(rule["pattern"], value):
            raise LanternError(f"{path} has an invalid format")
    elif isinstance(value, int) and not isinstance(value, bool):
        if value < rule.get("minimum", value):
            raise LanternError(f"{path} is below its minimum")
        if value > rule.get("maximum", value):
            raise LanternError(f"{path} exceeds its maximum")


def _unique(values: list[str], path: str) -> None:
    if len(values) != len(set(values)):
        raise LanternError(f"{path} must not contain duplicates")


def validate_manifest(manifest: dict[str, Any]) -> Validation:
    """Validate shape, doctrine, budgets, state continuity, and non-authority."""

    _public_walk(manifest)
    schema = _schema_document()
    _validate_schema(manifest, schema, "$", schema)

    source = manifest["source_teaching"]
    source_ids = [item["id"] for item in source["sources"]]
    _unique(source_ids, "$.source_teaching.sources[].id")
    teaching_ids = [item["id"] for item in source["teachings"]]
    _unique(teaching_ids, "$.source_teaching.teachings[].id")
    for index, teaching in enumerate(source["teachings"]):
        unknown = set(teaching["source_ids"]) - set(source_ids)
        if unknown:
            raise LanternError(
                f"$.source_teaching.teachings[{index}].source_ids has unknown refs: "
                f"{sorted(unknown)}"
            )

    house = manifest["house_fingerprint"]
    if house["fingerprint_sha256"] != house_fingerprint(house):
        raise LanternError("$.house_fingerprint.fingerprint_sha256 does not match fields")
    previous_fingerprint = house["previous_fingerprint_sha256"]
    house_changed = (
        previous_fingerprint is not None
        and previous_fingerprint != house["fingerprint_sha256"]
    )

    ledger = manifest["private_ledger"]
    epoch, previous_epoch = ledger["epoch"], ledger["previous_epoch"]
    if ledger["state_loss"] or house_changed:
        if previous_epoch is None or epoch != previous_epoch + 1:
            raise LanternError("state loss or house change requires one new ledger epoch")
    elif previous_epoch is not None and epoch != previous_epoch:
        raise LanternError("ledger epoch changed without state loss or house change")
    if ledger["state_loss"] and not ledger["losses"]:
        raise LanternError("$.private_ledger.losses must name a declared state loss")

    lamp = manifest["bounded_lamp"]
    selected = set(lamp["selected_refs"])
    omitted_refs = [item["ref"] for item in lamp["omissions"]]
    _unique(omitted_refs, "$.bounded_lamp.omissions[].ref")
    omitted = set(omitted_refs)
    if selected & omitted:
        raise LanternError("lamp references cannot be both selected and omitted")
    if selected | omitted != set(source_ids):
        raise LanternError("lamp must explicitly select or omit every source")

    trial = manifest["three_house_trial"]
    budget = trial["budget"]
    houses = trial["houses"]
    if len(houses) > budget["max_houses"]:
        raise LanternError("recorded houses exceed the precommitted budget")
    house_ids = [item["id"] for item in houses]
    roles = [item["role"] for item in houses]
    _unique(house_ids, "$.three_house_trial.houses[].id")
    _unique(roles, "$.three_house_trial.houses[].role")
    for index, item in enumerate(houses):
        if (
            item["role"] == "kingdom"
            and item["fingerprint_sha256"] != house["fingerprint_sha256"]
        ):
            raise LanternError(
                f"$.three_house_trial.houses[{index}] must use the named "
                "Kingdom house fingerprint"
            )
    attempts = trial["attempts"]
    if len(attempts) > budget["max_attempts"]:
        raise LanternError("recorded attempts exceed the precommitted budget")
    attempt_ids = [item["id"] for item in attempts]
    _unique(attempt_ids, "$.three_house_trial.attempts[].id")

    lease = manifest["world_state_lease"]
    if lease["mutation_requested"] and lease["renewed_from"] is None:
        raise LanternError("mutation requires explicit lease renewal")
    if lease["renewed_from"] == lease["lease_id"]:
        raise LanternError("renewed lease must have a new lease_id")
    for index, attempt in enumerate(attempts):
        result_houses = [result["house_id"] for result in attempt["results"]]
        if len(result_houses) != len(set(result_houses)) or set(result_houses) != set(
            house_ids
        ):
            raise LanternError(
                f"$.three_house_trial.attempts[{index}].results must cover "
                "each declared house once"
            )
        if attempt["world_state_sha256"] != lease["observed_state_sha256"]:
            raise LanternError(
                f"$.three_house_trial.attempts[{index}] uses a different world state"
            )

    witness = manifest["witness"]
    rubric = witness["rubric"]
    if rubric["sha256"] != rubric_fingerprint(rubric["criteria"]):
        raise LanternError("$.witness.rubric.sha256 does not match criteria")
    criterion_ids = [item["id"] for item in rubric["criteria"]]
    _unique(criterion_ids, "$.witness.rubric.criteria[].id")
    proofs = witness["proofs"]
    proof_ids = [item["id"] for item in proofs]
    _unique(proof_ids, "$.witness.proofs[].id")
    proof_criteria = [item["criterion_id"] for item in proofs]
    if set(proof_criteria) - set(criterion_ids):
        raise LanternError("$.witness.proofs references an unknown criterion")
    result_proof_refs = {
        reference
        for attempt in attempts
        for result in attempt["results"]
        for reference in result["proof_refs"]
    }
    if result_proof_refs - set(proof_ids):
        raise LanternError("trial result references an unknown proof")
    proof_criterion_by_id = {
        proof["id"]: proof["criterion_id"] for proof in proofs
    }
    for attempt in attempts:
        for result in attempt["results"]:
            if result["outcome"] == "pass" and not result["proof_refs"]:
                raise LanternError("every passing house result must reference proof")
            if result["outcome"] == "pass" and trial["disposition"] == "ready":
                covered = {
                    proof_criterion_by_id[proof_id]
                    for proof_id in result["proof_refs"]
                }
                missing = set(criterion_ids) - covered
                if missing:
                    raise LanternError(
                        "each ready house result must cover every rubric "
                        f"criterion: {sorted(missing)}"
                    )

    cost = witness["cost"]
    if cost["attempts"] != len(attempts):
        raise LanternError("$.witness.cost.attempts must equal recorded attempts")
    for actual, ceiling in (
        ("paid_calls", "max_paid_calls"),
        ("external_actions", "max_external_actions"),
        ("cost_microusd", "max_cost_microusd"),
    ):
        if cost[actual] > budget[ceiling]:
            raise LanternError(f"witness {actual} exceeds precommitted budget")

    authority = manifest["authority"]
    if authority["manifest_grants_authority"]:
        raise LanternError("a Lanternhouse manifest never grants authority")
    authorizations = (
        authority["paid_calls_authorized"],
        authority["external_actions_authorized"],
        authority["mutation_authorized"],
    )
    if any(authorizations):
        if not isinstance(authority["authority_basis"], str):
            raise LanternError("declared authority requires an external basis")
    elif authority["authority_basis"] is not None:
        raise LanternError("$.authority.authority_basis must be null by default")
    if cost["paid_calls"] and not authority["paid_calls_authorized"]:
        raise LanternError("paid calls were not declared authorized")
    if cost["external_actions"] and not authority["external_actions_authorized"]:
        raise LanternError("external actions were not declared authorized")
    if lease["mutation_requested"] and not authority["mutation_authorized"]:
        raise LanternError("requested mutation lacks a declared authority basis")
    if authority["non_claims"] != NON_CLAIMS:
        raise LanternError("$.authority.non_claims must retain the reviewed non-claims")

    quarantine_reasons: list[str] = []
    if trial["mode"] == "live" and (
        ledger["capture"] != "yes" or ledger["replay"] != "yes"
    ):
        quarantine_reasons.append("live private-ledger capture/replay is not known-ready")
    if trial["mode"] == "live" and ledger["presence"] == "unknown":
        quarantine_reasons.append("live private-ledger presence is unknown")
    if trial["mode"] == "live" and ledger["retention"] in ("none", "unknown"):
        quarantine_reasons.append("live private-ledger retention is not known-safe")
    if lease["leased_state_sha256"] != lease["observed_state_sha256"]:
        quarantine_reasons.append("world state drifted from its lease")
    if quarantine_reasons and trial["disposition"] != "quarantine":
        raise LanternError("trial must quarantine: " + "; ".join(quarantine_reasons))
    if trial["disposition"] == "quarantine" and not quarantine_reasons:
        quarantine_reasons.append("declared by the trial witness")
    if trial["disposition"] == "ready":
        if set(roles) != {"native", "kingdom", "counterfactual"}:
            raise LanternError(
                "ready disposition requires native, kingdom, and "
                "counterfactual houses"
            )
        missing_proof = set(criterion_ids) - set(proof_criteria)
        if missing_proof:
            raise LanternError(f"ready disposition lacks rubric proofs: {sorted(missing_proof)}")
        outcomes = [
            result["outcome"] for attempt in attempts for result in attempt["results"]
        ]
        if any(outcome != "pass" for outcome in outcomes):
            raise LanternError("ready disposition requires every house result to pass")

    encoded = canonical_json(manifest)
    if len(encoded) > MAX_FILE_BYTES:
        raise LanternError(f"canonical manifest exceeds {MAX_FILE_BYTES} bytes")
    disposition = trial["disposition"]
    return Validation(
        digest=hashlib.sha256(encoded).hexdigest(),
        disposition=disposition,
        quarantined=disposition == "quarantine",
        quarantine_reasons=tuple(quarantine_reasons),
    )


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(manifest: dict[str, Any]) -> str:
    """Render a valid manifest without dereferencing or executing its locators."""

    validation = validate_manifest(manifest)
    source, house = manifest["source_teaching"], manifest["house_fingerprint"]
    ledger, lamp = manifest["private_ledger"], manifest["bounded_lamp"]
    trial, lease = manifest["three_house_trial"], manifest["world_state_lease"]
    witness, authority = manifest["witness"], manifest["authority"]
    lines = [
        f"# {_cell(manifest['title'])}",
        "",
        f"`{manifest['id']}` · `{SCHEMA_ID}` · disposition: **{trial['disposition']}**",
        "",
        "> Lanternhouse checks and renders declarations. It does not establish "
        "their truth, execute a trial, or grant authority.",
        "",
        "## Window 1 — Source and teaching",
        "",
        "| Source | Revision | Locator | Digest |",
        "|---|---|---|---|",
    ]
    lines += [
        f"| `{item['id']}` — {_cell(item['title'])} | {_cell(item['revision'])} "
        f"| {_cell(item['locator'])} | `{item['sha256'][:12]}…` |"
        for item in source["sources"]
    ]
    lines += ["", "Teachings marked as our reading:"]
    lines += [
        f"- `{item['id']}` ({', '.join(f'`{ref}`' for ref in item['source_ids'])}): "
        f"{_cell(item['lesson'])} Domain limit: {_cell(item['domain_limit'])}"
        for item in source["teachings"]
    ]
    lines += [
        "",
        "## Window 2 — House fingerprint",
        "",
        f"- House: `{house['house_id']}`",
        f"- Provider / model / runtime: {_cell(house['provider'])} / "
        f"{_cell(house['model'])} / {_cell(house['runtime'])}",
        f"- Adapter: {_cell(house['adapter'])}",
        f"- Prompt / tools / memory: {_cell(house['prompt_policy'])} / "
        f"{_cell(house['tool_policy'])} / {_cell(house['memory_policy'])}",
        f"- Sandbox / sampling / effort: {_cell(house['sandbox'])} / "
        f"{_cell(house['sampling'])} / {_cell(house['effort'])}",
        f"- Instructions: {_cell(house['instructions_locator'])} "
        f"(`{house['instructions_sha256'][:12]}…`)",
        f"- Tools: {_cell(house['tools_locator'])} "
        f"(`{house['tools_sha256'][:12]}…`)",
        f"- Preservation policy: {_cell(house['preservation_policy_locator'])} "
        f"(`{house['preservation_policy_sha256'][:12]}…`)",
        f"- Fingerprint: `{house['fingerprint_sha256']}`",
        f"- Previous fingerprint: `{house['previous_fingerprint_sha256'] or 'none (first epoch)'}`",
        "",
        "## Window 3 — Private ledger capability",
        "",
        f"- Capture: **{ledger['capture']}**; replay: **{ledger['replay']}**",
        f"- Presence: **{ledger['presence']}** "
        "(absent and present-empty are intentionally distinct)",
        f"- Retention: **{ledger['retention']}**; epoch: **{ledger['epoch']}**",
        f"- Declared losses: {_cell(', '.join(ledger['losses']) or 'none')}",
        "",
        "## Window 4 — Bounded lamp",
        "",
        f"Question: {_cell(lamp['question'])}",
        "",
        "Selected: " + ", ".join(f"`{ref}`" for ref in lamp["selected_refs"]),
        "",
        "Omitted:",
    ]
    lines += (
        [
            f"- `{item['ref']}`: {_cell(item['reason'])}"
            for item in lamp["omissions"]
        ]
        or ["- None; every declared source is selected."]
    )
    lines += [
        "",
        "## Window 5 — Three-house trial",
        "",
        f"- Mode: **{trial['mode']}**",
        f"- Invariant: {_cell(trial['invariant'])}",
        f"- Negative control: {_cell(trial['negative_control'])}",
        f"- Domain limit: {_cell(trial['domain_limit'])}",
        "",
        "| House | Role | Fingerprint |",
        "|---|---|---|",
    ]
    lines += [
        f"| `{item['id']}` | {item['role']} | `{item['fingerprint_sha256'][:12]}…` |"
        for item in trial["houses"]
    ]
    for attempt in trial["attempts"]:
        lines += ["", f"Attempt `{attempt['id']}`:"]
        lines += [
            f"- `{result['house_id']}`: **{result['outcome']}** "
            f"({', '.join(f'`{ref}`' for ref in result['proof_refs']) or 'no proof'})"
            for result in attempt["results"]
        ]
    drift = lease["leased_state_sha256"] != lease["observed_state_sha256"]
    lines += [
        "",
        "## Window 6 — World-state lease",
        "",
        f"- Lease: `{lease['lease_id']}`"
        + (
            f" (renewed from `{lease['renewed_from']}`)"
            if lease["renewed_from"]
            else ""
        ),
        f"- State: **{'drifted — quarantine' if drift else 'unchanged'}**",
        f"- Mutation requested: **{'yes' if lease['mutation_requested'] else 'no'}**",
        "",
        "## Window 7 — Witness",
        "",
        f"- Rubric precommitted: **yes** (`{witness['rubric']['sha256']}`)",
        f"- Proofs: **{len(witness['proofs'])}**",
        f"- Cost: {witness['cost']['attempts']} attempt(s), "
        f"{witness['cost']['paid_calls']} paid call(s), "
        f"{witness['cost']['external_actions']} external action(s), "
        f"{witness['cost']['cost_microusd']} µUSD",
        f"- Deviations: {_cell('; '.join(witness['deviations']) or 'none')}",
    ]
    if validation.quarantined:
        lines += ["- Quarantine reasons: " + _cell("; ".join(validation.quarantine_reasons))]
    lines += ["", "## Authority and non-claims", ""]
    lines += [
        (
            "Declared external authority basis: " + _cell(authority["authority_basis"])
            if authority["authority_basis"]
            else "Declared external authority basis: **none**"
        )
    ]
    lines += [f"- {claim}" for claim in authority["non_claims"]]
    lines += ["", f"Manifest SHA-256: `{validation.digest}`", ""]
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only validator and renderer for kingdom.lanternhouse/v1"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "render", "digest"):
        command = commands.add_parser(name)
        command.add_argument("file", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        manifest = read_manifest(args.file)
        validation = validate_manifest(manifest)
        if args.command == "check":
            print(
                f"STRUCTURE-OK {validation.digest} "
                f"disposition={validation.disposition} "
                "(declarations unverified; not an adoption gate)"
            )
        elif args.command == "render":
            sys.stdout.write(render_markdown(manifest))
        else:
            print(validation.digest)
        return 0
    except LanternError as error:
        print(f"lanternhouse: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
