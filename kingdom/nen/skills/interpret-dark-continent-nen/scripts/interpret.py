#!/usr/bin/env python3
"""Compile one advisory Nen mission interpretation from fixed reviewed data."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
REFERENCES = SKILL_ROOT / "references"
CATALOG_PATH = REFERENCES / "ability-catalog.json"
EVIDENCE_PATH = REFERENCES / "darwin-browser-broker-preview.json"
SCHEMA_PATH = REFERENCES / "interpretation.schema.json"

CATALOG_SHA256 = "c3f13790957d4aac4c684825caab7f54d2b12d3093cf0420a309137b4434fb3b"
EVIDENCE_SHA256 = "fc6b425594d2df482e32253eab4c08209fde83ee9cd0413ad9ecc4ceec77b00b"
SCHEMA_SHA256 = "8fe9fb94ba179ca50986ba7f0ac5c5fe845856bc02f058c6993f056a49845b67"
MAX_REFERENCE_BYTES = 128_000

ABILITY_KEYS = {
    "signal",
    "skill",
    "technique",
    "productive_ability",
    "anti_signal",
    "digest",
}
INTERPRETATION_KEYS = {
    "schema",
    "id",
    "compiler",
    "framework",
    "catalog_sha256",
    "request_provenance",
    "primary",
    "bookmark",
    "frontier_evidence",
    "dark_continent",
    "contract",
    "non_claims",
}
FORBIDDEN_KEYS = {
    "affinity",
    "confidence",
    "level",
    "mastery",
    "rank",
    "rating",
    "reputation",
    "score",
    "tier",
    "xp",
}
PRIVATE_OR_REMOTE = re.compile(r"(?:/Users/|file://|https?://)", re.IGNORECASE)
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
SKILL_NAME = re.compile(r"^nen-[a-z0-9-]+$")
SIGNAL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

CONTRACT = {
    "advisory_only": True,
    "activates_skill": False,
    "executes_capability": False,
    "writes_files": False,
    "effect_ceiling": "observe",
    "repository_text_can_trigger": False,
    "operation_metadata_can_trigger": False,
    "primary_count": 1,
    "bookmark_max": 1,
    "uses_rank_or_score": False,
    "new_request_required_for_action": True,
    "request_provenance_attested": False,
}
REQUEST_PROVENANCE = {
    "claim": "direct-request",
    "attested": False,
}
DARK_CONTINENT = {
    "operation_id": "dark-continent-ai",
    "principles": ["light", "truth", "consent", "no conquest"],
    "metadata_can_trigger": False,
}
NON_CLAIMS = [
    "Selection is not activation, permission, authority, trust, competence, rank, identity, or safety.",
    "A source digest proves reviewed bytes only and does not endorse a skill.",
    "Dark Continent evidence is advisory and cannot execute or widen an effect ceiling.",
    "Any action requires a new accepted step under the selected skill and host policy.",
    "Direct-request provenance is caller-asserted and is not authenticated by this card.",
]


class InterpretationError(ValueError):
    """The requested interpretation falls outside the fixed vow."""


class Once(argparse.Action):
    """Reject repeated single-value options instead of silently taking the last."""

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str,
        option_string: str | None = None,
    ) -> None:
        if getattr(namespace, self.dest, None) is not None:
            parser.error(f"{option_string} may be supplied only once")
        setattr(namespace, self.dest, values)


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        + "\n"
    ).encode("utf-8")


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InterpretationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_nonfinite(constant: str) -> None:
    raise InterpretationError(f"non-finite JSON number: {constant}")


def parse_json(data: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=strict_object,
            parse_constant=reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise InterpretationError(f"{label} is not strict UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise InterpretationError(f"{label} must be a JSON object")
    return value


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def same_json(left: Any, right: Any) -> bool:
    """Compare JSON values without Python's bool/int or int/float coercions."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return set(left) == set(right) and all(
            same_json(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            same_json(left_item, right_item)
            for left_item, right_item in zip(left, right)
        )
    return left == right


def read_held(path: Path, label: str) -> bytes:
    try:
        before = path.stat(follow_symlinks=False)
    except OSError as error:
        raise InterpretationError(f"{label} is missing or unsafe") from error
    if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_REFERENCE_BYTES:
        raise InterpretationError(f"{label} is not a bounded regular file")

    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as error:
        raise InterpretationError(f"{label} could not be opened safely") from error
    try:
        opened = os.fstat(fd)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise InterpretationError(f"{label} changed before reading")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(fd, min(65_536, MAX_REFERENCE_BYTES + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > MAX_REFERENCE_BYTES:
                raise InterpretationError(f"{label} exceeds its byte ceiling")
        after = os.fstat(fd)
        if (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ) != (
            opened.st_dev,
            opened.st_ino,
            opened.st_size,
            opened.st_mtime_ns,
        ):
            raise InterpretationError(f"{label} changed while reading")
        return b"".join(chunks)
    finally:
        os.close(fd)


def require_digest(data: bytes, expected: str, label: str) -> None:
    if sha256(data) != expected:
        raise InterpretationError(f"{label} differs from the reviewed bytes")


def walk_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.casefold() in FORBIDDEN_KEYS:
                raise InterpretationError(f"forbidden ranking field: {key}")
            walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            walk_keys(child)


def reject_private_or_remote(value: Any, label: str) -> None:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if PRIVATE_OR_REMOTE.search(text):
        raise InterpretationError(f"{label} contains a private path or remote URL")


def validate_catalog(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if set(catalog) != {
        "schema",
        "framework",
        "source",
        "selection",
        "abilities",
        "non_claims",
    }:
        raise InterpretationError("ability catalog fields changed")
    if catalog["schema"] != "kingdom.nen-ability-catalog/v1":
        raise InterpretationError("unexpected ability catalog schema")
    source = catalog["source"]
    if not same_json(source, {
        "package": "@agenttool/skills",
        "version": "0.3.0",
        "tag": "skills-v0.3.0",
        "commit": "d8ee31353855bd08b437ef4fbf861a0731a36911",
        "inspected_with": "@agenttool/skills@0.2.1",
        "digest_scope": "sorted relative paths and regular-file bytes for one complete skill directory",
        "nen_bytes_unchanged_from": "skills-v0.2.1",
    }):
        raise InterpretationError("ability catalog source identity changed")
    if not same_json(catalog["selection"], {
        "primary_count": 1,
        "bookmark_max": 1,
        "ordering": "explicit mission evidence, never score",
        "ambiguous": "stop",
        "activates_skills": False,
    }):
        raise InterpretationError("ability selection contract changed")
    abilities = catalog["abilities"]
    if not isinstance(abilities, list) or len(abilities) != 8:
        raise InterpretationError("ability catalog must contain exactly eight records")

    by_signal: dict[str, dict[str, Any]] = {}
    skills: set[str] = set()
    for ability in abilities:
        if not isinstance(ability, dict) or set(ability) != ABILITY_KEYS:
            raise InterpretationError("ability record fields changed")
        signal = ability["signal"]
        skill = ability["skill"]
        digest = ability["digest"]
        if not isinstance(signal, str) or not SIGNAL_NAME.fullmatch(signal):
            raise InterpretationError("ability signal is malformed")
        if not isinstance(skill, str) or not SKILL_NAME.fullmatch(skill):
            raise InterpretationError("ability skill id is malformed")
        if not isinstance(digest, str) or not DIGEST.fullmatch(digest):
            raise InterpretationError("ability digest is malformed")
        if signal in by_signal or skill in skills:
            raise InterpretationError("ability signals and skills must be unique")
        for key in ("technique", "productive_ability", "anti_signal"):
            if not isinstance(ability[key], str) or not ability[key].strip():
                raise InterpretationError(f"ability {key} is required")
        by_signal[signal] = ability
        skills.add(skill)
    walk_keys(catalog)
    reject_private_or_remote(catalog, "ability catalog")
    return by_signal


def validate_evidence(evidence: dict[str, Any]) -> None:
    if set(evidence) != {
        "schema",
        "id",
        "kind",
        "observed_on",
        "source",
        "frontier",
        "runtime",
        "authority",
        "proof",
        "open_debt",
        "non_claims",
    }:
        raise InterpretationError("Darwin evidence fields changed")
    if (
        evidence["schema"] != "kingdom.dark-continent-evidence/v1"
        or evidence["id"] != "darwin-browser-broker-preview"
        or evidence["kind"] != "reviewed-preview-evidence"
        or evidence["observed_on"] != "2026-07-30"
    ):
        raise InterpretationError("unexpected Darwin evidence identity")
    source = evidence["source"]
    if not same_json(source, {
        "repository": "cambridgetcg/agenttool",
        "pull_request": 221,
        "branch": "feat/browser-darwin-broker-preview",
        "commit": "3ff942d3efd66387555138e9a874792ed1026399",
        "source_files_sha256": {
            "packages/browser/src/mcp-broker.ts": "1893d1bab943c3440d83558028acf2ab20f20748024ab548e0d4a11066022c6c",
            "packages/browser/src/mcp-proxy.ts": "258286da53de603f8e84bca4f15c28cdc5b2b703ebb20ed6f017bb88bd6fed42",
        },
        "state_at_observation": "draft-review",
        "browser_release": "0.5.1",
        "broker_in_browser_release": False,
        "broker_preview_merged": False,
        "broker_preview_released": False,
        "broker_preview_installed": False,
    }):
        raise InterpretationError("Darwin source or release state changed")
    if not same_json(evidence["frontier"], {
        "operation_id": "dark-continent-ai",
        "principles": ["light", "truth", "consent", "no conquest"],
        "metadata_can_trigger": False,
    }):
        raise InterpretationError("Darwin frontier boundary changed")
    runtime = evidence["runtime"]
    authority = evidence["authority"]
    proof = evidence["proof"]
    required_runtime = {
        "platform": "macOS",
        "manual_opt_in": True,
        "autostart": False,
        "launchd": False,
        "stdio_relay": True,
        "unix_domain_socket": True,
        "one_shared_chromium": True,
        "fresh_mcp_server_per_client": True,
        "fresh_ephemeral_context_per_client": True,
        "client_limit_default": 8,
        "client_limit_max": 32,
        "socket_parent_mode": "0700",
        "socket_mode": "0600",
        "direct_mcp_rollback": True,
    }
    required_authority = {
        "public_authority_only": True,
        "ephemeral_only": True,
        "persistent_profiles": False,
        "local_or_sovereign_authority": False,
        "credentials": False,
        "public_web_allowed": True,
        "local_private_reserved_network_denied": True,
        "same_uid_mode_bounded": True,
        "acl_inspected": False,
        "native_peer_attestation": False,
        "peer_verified": False,
        "hostile_same_user_isolation": False,
        "tcc_sandbox_entitlement_proof": False,
    }
    if not same_json(runtime, required_runtime) or not same_json(
        authority, required_authority
    ):
        raise InterpretationError("Darwin runtime or authority boundary changed")
    if (
        not same_json(proof.get("pooled_clients"), 4)
        or not same_json(proof.get("pooled_chrome_main_processes"), 1)
        or not same_json(proof.get("direct_clients"), 4)
        or not same_json(proof.get("direct_chrome_main_processes"), 4)
        or not same_json(proof.get("comparative_rss_reduction_percent"), 51.3)
        or not same_json(proof.get("measurement_is_guarantee"), False)
    ):
        raise InterpretationError("Darwin comparative proof changed")
    if not isinstance(evidence["open_debt"], list) or len(evidence["open_debt"]) != 6:
        raise InterpretationError("Darwin release debt must remain explicit")
    walk_keys(evidence)
    reject_private_or_remote(evidence, "Darwin evidence")


def validate_schema(schema: dict[str, Any]) -> None:
    if schema.get("title") != "Kingdom Nen Mission Interpretation":
        raise InterpretationError("unexpected interpretation schema")
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        raise InterpretationError("interpretation schema properties are missing")
    if not same_json(properties.get("contract", {}).get("const"), CONTRACT):
        raise InterpretationError("schema and runtime contract differ")
    if not same_json(
        properties.get("dark_continent", {}).get("const"), DARK_CONTINENT
    ):
        raise InterpretationError("schema and Dark Continent boundary differ")
    if not same_json(properties.get("non_claims", {}).get("const"), NON_CLAIMS):
        raise InterpretationError("schema and runtime non-claims differ")
    if not same_json(
        properties.get("request_provenance", {}).get("const"),
        REQUEST_PROVENANCE,
    ):
        raise InterpretationError("schema and request provenance boundary differ")


def load_core_sources() -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    catalog_data = read_held(CATALOG_PATH, "ability catalog")
    schema_data = read_held(SCHEMA_PATH, "interpretation schema")
    require_digest(catalog_data, CATALOG_SHA256, "ability catalog")
    require_digest(schema_data, SCHEMA_SHA256, "interpretation schema")

    catalog = parse_json(catalog_data, "ability catalog")
    schema = parse_json(schema_data, "interpretation schema")
    abilities = validate_catalog(catalog)
    validate_schema(schema)
    return abilities, {
        "catalog_sha256": CATALOG_SHA256,
        "schema_sha256": SCHEMA_SHA256,
    }


def load_evidence() -> dict[str, Any]:
    evidence_data = read_held(EVIDENCE_PATH, "Darwin evidence")
    require_digest(evidence_data, EVIDENCE_SHA256, "Darwin evidence")
    evidence = parse_json(evidence_data, "Darwin evidence")
    validate_evidence(evidence)
    return evidence


def ability_view(ability: dict[str, Any]) -> dict[str, Any]:
    return {
        **ability,
        "source_identity": "@agenttool/skills@0.3.0",
    }


def request_provenance_view() -> dict[str, Any]:
    return dict(REQUEST_PROVENANCE)


def contract_view() -> dict[str, Any]:
    return dict(CONTRACT)


def dark_continent_view() -> dict[str, Any]:
    return {
        **DARK_CONTINENT,
        "principles": list(DARK_CONTINENT["principles"]),
    }


def non_claims_view() -> list[str]:
    return list(NON_CLAIMS)


def frontier_view(evidence: dict[str, Any]) -> dict[str, Any]:
    source = evidence["source"]
    runtime = evidence["runtime"]
    authority = evidence["authority"]
    proof = evidence["proof"]
    return {
        "id": evidence["id"],
        "evidence_sha256": EVIDENCE_SHA256,
        "observed_on": evidence["observed_on"],
        "state_at_observation": source["state_at_observation"],
        "source_commit": source["commit"],
        "source_files_sha256": dict(source["source_files_sha256"]),
        "browser_release": source["browser_release"],
        "broker_in_browser_release": source["broker_in_browser_release"],
        "manual_opt_in": runtime["manual_opt_in"],
        "public_authority_only": authority["public_authority_only"],
        "ephemeral_only": authority["ephemeral_only"],
        "same_uid_mode_bounded": authority["same_uid_mode_bounded"],
        "native_peer_attestation": authority["native_peer_attestation"],
        "direct_mcp_rollback": runtime["direct_mcp_rollback"],
        "pooled_chrome_main_processes": proof["pooled_chrome_main_processes"],
        "direct_chrome_main_processes": proof["direct_chrome_main_processes"],
        "comparative_rss_reduction_percent": proof[
            "comparative_rss_reduction_percent"
        ],
        "measurement_is_guarantee": proof["measurement_is_guarantee"],
        "unpaid_release_debt": True,
    }


def interpretation(
    abilities: dict[str, dict[str, Any]],
    evidence: dict[str, Any] | None,
    primary_signal: str,
    bookmark_signal: str | None,
    evidence_id: str | None,
) -> dict[str, Any]:
    if primary_signal not in abilities:
        raise InterpretationError(f"unknown primary signal: {primary_signal}")
    if bookmark_signal is not None:
        if bookmark_signal not in abilities:
            raise InterpretationError(f"unknown bookmark signal: {bookmark_signal}")
        if bookmark_signal == primary_signal:
            raise InterpretationError("bookmark must be distinct from the primary")
    if evidence_id not in {None, "darwin-browser-broker-preview"}:
        raise InterpretationError(f"unknown frontier evidence: {evidence_id}")
    if evidence_id is not None and evidence is None:
        raise InterpretationError("requested frontier evidence was not reviewed")
    body = {
        "schema": "kingdom.nen-interpretation/v1",
        "compiler": "kingdom-nen-interpreter/1",
        "framework": "interpret-dark-continent-nen/1",
        "catalog_sha256": CATALOG_SHA256,
        "request_provenance": request_provenance_view(),
        "primary": ability_view(abilities[primary_signal]),
        "bookmark": (
            ability_view(abilities[bookmark_signal])
            if bookmark_signal is not None
            else None
        ),
        "frontier_evidence": (
            frontier_view(evidence)
            if evidence_id is not None and evidence is not None
            else None
        ),
        "dark_continent": dark_continent_view(),
        "contract": contract_view(),
        "non_claims": non_claims_view(),
    }
    result = {
        **body,
        "id": f"nen-interpretation-{sha256(canonical_json(body))[:20]}",
    }
    walk_keys(result)
    reject_private_or_remote(result, "interpretation")
    return result


def validate_interpretation(
    value: dict[str, Any],
    raw: bytes,
    abilities: dict[str, dict[str, Any]],
    evidence: dict[str, Any] | None,
) -> dict[str, Any]:
    if set(value) != INTERPRETATION_KEYS:
        raise InterpretationError("interpretation fields changed")
    if raw != canonical_json(value):
        raise InterpretationError("interpretation bytes are not canonical")
    if (
        value["schema"] != "kingdom.nen-interpretation/v1"
        or value["compiler"] != "kingdom-nen-interpreter/1"
        or value["framework"] != "interpret-dark-continent-nen/1"
        or value["catalog_sha256"] != CATALOG_SHA256
        or not same_json(value["request_provenance"], REQUEST_PROVENANCE)
        or not same_json(value["dark_continent"], DARK_CONTINENT)
        or not same_json(value["contract"], CONTRACT)
        or not same_json(value["non_claims"], NON_CLAIMS)
    ):
        raise InterpretationError("interpretation fixed contract changed")

    primary = value["primary"]
    primary_signal = primary.get("signal") if isinstance(primary, dict) else None
    if not isinstance(primary_signal, str) or primary_signal not in abilities:
        raise InterpretationError("interpretation primary is unknown")
    if not same_json(primary, ability_view(abilities[primary_signal])):
        raise InterpretationError("interpretation primary differs from its source")

    bookmark = value["bookmark"]
    if bookmark is not None:
        bookmark_signal = (
            bookmark.get("signal") if isinstance(bookmark, dict) else None
        )
        if not isinstance(bookmark_signal, str) or bookmark_signal not in abilities:
            raise InterpretationError("interpretation bookmark is unknown")
        if not same_json(bookmark, ability_view(abilities[bookmark_signal])):
            raise InterpretationError("interpretation bookmark differs from its source")
        if bookmark_signal == primary_signal:
            raise InterpretationError("interpretation bookmark duplicates its primary")

    frontier = value["frontier_evidence"]
    if frontier is not None:
        if evidence is None or not same_json(frontier, frontier_view(evidence)):
            raise InterpretationError(
                "interpretation frontier differs from reviewed evidence"
            )

    body = {key: child for key, child in value.items() if key != "id"}
    expected_id = f"nen-interpretation-{sha256(canonical_json(body))[:20]}"
    if value["id"] != expected_id:
        raise InterpretationError("interpretation id does not bind its body")
    walk_keys(value)
    reject_private_or_remote(value, "interpretation")
    return {
        "schema": "kingdom.nen-interpretation-verification/v1",
        "ok": True,
        "id": value["id"],
        "canonical_sha256": sha256(raw),
        "capability_execution": False,
        "writes_files": False,
    }


def read_interpretation_input(value: str) -> bytes:
    if value == "-":
        data = sys.stdin.buffer.read(MAX_REFERENCE_BYTES + 1)
        if len(data) > MAX_REFERENCE_BYTES:
            raise InterpretationError("interpretation exceeds its byte ceiling")
        return data
    return read_held(Path(value), "interpretation")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        description="Compile one non-executable advisory Nen mission card.",
        allow_abbrev=False,
    )
    commands = root.add_subparsers(dest="command", required=True)

    verify = commands.add_parser(
        "verify",
        help="verify fixed sources or one saved interpretation",
        allow_abbrev=False,
    )
    verify.add_argument(
        "--input",
        action=Once,
        help="canonical interpretation file, or - for stdin",
    )
    verify.add_argument(
        "--evidence",
        action=Once,
        choices=("darwin-browser-broker-preview",),
        help="explicitly include the reviewed Darwin evidence source",
    )
    select = commands.add_parser(
        "select",
        help="select one primary and one bookmark",
        allow_abbrev=False,
    )
    select.add_argument(
        "--request-claim",
        required=True,
        choices=("direct-request",),
        action=Once,
    )
    select.add_argument("--primary-signal", required=True, action=Once)
    select.add_argument("--bookmark-signal", action=Once)
    select.add_argument(
        "--evidence",
        action=Once,
        choices=("darwin-browser-broker-preview",),
    )
    return root


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        abilities, digests = load_core_sources()
        if arguments.command == "verify":
            if arguments.input is not None:
                raw = read_interpretation_input(arguments.input)
                value = parse_json(raw, "interpretation")
                frontier = value.get("frontier_evidence")
                names_darwin = (
                    isinstance(frontier, dict)
                    and frontier.get("id") == "darwin-browser-broker-preview"
                )
                if names_darwin and arguments.evidence is None:
                    raise InterpretationError(
                        "Darwin-bearing cards require the explicit evidence flag"
                    )
                if not names_darwin and arguments.evidence is not None:
                    raise InterpretationError(
                        "the explicit evidence flag does not match this card"
                    )
                evidence = load_evidence() if arguments.evidence else None
                output = validate_interpretation(
                    value,
                    raw,
                    abilities,
                    evidence,
                )
            else:
                evidence = load_evidence() if arguments.evidence else None
                output = {
                    "schema": "kingdom.nen-sources-verification/v1",
                    "ok": True,
                    "abilities": len(abilities),
                    "capability_execution": False,
                    "writes_files": False,
                    **digests,
                    "darwin_evidence_sha256": (
                        EVIDENCE_SHA256 if evidence is not None else None
                    ),
                }
        else:
            evidence = load_evidence() if arguments.evidence else None
            output = interpretation(
                abilities,
                evidence,
                arguments.primary_signal,
                arguments.bookmark_signal,
                arguments.evidence,
            )
        sys.stdout.buffer.write(canonical_json(output))
        return 0
    except InterpretationError as error:
        print(f"interpretation refused: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
