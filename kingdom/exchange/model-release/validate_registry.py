#!/usr/bin/env python3
"""Verify closed, mirrored model-release capsules without network access.

This verifier intentionally sits outside the frozen v1 model-release schema.
A release launch index or a release-referring execution-witness index inventories
the exact raw bytes in one capsule, binds every v1 record to its deterministic
receipt, checks release/profile/attestation graph edges with ``model_release.py``,
and verifies domain-separated signatures and provenance.  It does not turn a
curator or workflow key into publisher, platform, human, safety, or deployment
authority.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Sequence


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import model_release as release_v1  # noqa: E402


REGISTRY_SCHEMA = "kingdom.model-release-registry/v1"
LAUNCH_INDEX_SCHEMA = "kingdom.model-release-launch-index/v1"
WITNESS_INDEX_SCHEMA = "kingdom.model-release-witness-index/v1"
VERIFIER_POLICY_SCHEMA = "kingdom.ed25519-verifier-policy/v1"
WITNESS_VERIFIER_POLICY_SCHEMA = "kingdom.ed25519-witness-verifier-policy/v1"
PUBLISHER_INVENTORY_SCHEMA = "kingdom.publisher-artifact-inventory/v1"

RELEASE_DOMAIN = "KINGDOM MODEL RELEASE SUBJECT v1"
LAUNCH_INDEX_DOMAIN = "KINGDOM MODEL RELEASE LAUNCH INDEX v1"
WITNESS_INDEX_DOMAIN = "KINGDOM MODEL RELEASE WITNESS INDEX v1"
SIGNED_VALUE = "UTF-8 domain, LF, lowercase sha256 digest, LF"
IDENTITY_CLAIM = (
    "Ephemeral public-key possession only; no human, publisher, vendor, or "
    "platform identity is claimed."
)
WITNESS_IDENTITY_CLAIM = (
    "Ephemeral public-key possession only; no human, publisher, vendor, platform, "
    "or independent-reproducer identity is claimed."
)
AUTHORITY_CLAIM = "none"
ISSUER = "self-issued one-use Ed25519 key; no external identity claim"

REGISTRY_NON_CLAIMS = [
    "Registry membership inventories reviewed local bytes; it does not establish publisher identity, safety, quality, behavior, or truth.",
    "A successful signature check proves possession of the matching private key for the signed bytes; the key carries no human, vendor, platform, or deployment authority.",
    "Registry verification performs no network request, artifact download, model call, publication, deployment, or external write.",
]
LAUNCH_INDEX_NON_CLAIMS = [
    "The launch index is an external byte-set wrapper, not a kingdom.model-release/v1 record and not release authority.",
    "Raw file digests and deterministic receipts establish byte identity and v1 structural validity only; they do not establish behavioral reproducibility.",
    "Declared local and hosted execution profiles are not evidence that either execution occurred.",
]
WITNESS_INDEX_NON_CLAIMS = [
    "This witness index refers to the sealed qwen3-0.6b-hf-c1899de2 release; it is not a new model release or a mutation of that capsule.",
    "The successful run was curated by the same KINGDOM operator on a GitHub-managed runner; it is not an independent human, vendor, publisher, or laboratory reproduction.",
    "GitHub artifact attestation authenticates the workflow-produced tar and bound workflow identity; it does not establish model semantics, claim truth, or the inode consumed by the loader.",
    "The pinned trusted-root snapshot supports this offline verification receipt at the recorded time; it is not a timeless statement about later trust-root state.",
    "The public arithmetic fixture differs from the earlier capsule's private synthetic probe, so cross-machine exact-output equivalence to that run is not claimed.",
    "Digests, signatures, and deterministic receipts identify bytes and structural validity; they do not prove safety, quality, broad reproducibility, or publisher identity.",
    "One failed pre-inference attempt is retained; it produced no model inference, evidence tar, or artifact attestation.",
]

GH_ATTESTATION_MINIMUM_VERSION = "2.86.0"
GH_ATTESTATION_SOURCE_REVISION = "github/cli/v2.86.0"
GH_TRUSTED_ROOT_DIGEST = "sha256:65ca537f6ed8a47fd0e560c421baa1f6c1efb8b25fc200d8c5c02c0e92eb2b9c"
SLSA_PROVENANCE_V1 = "https://slsa.dev/provenance/v1"
GITHUB_ACTIONS_BUILD_TYPE_V1 = "https://actions.github.io/buildtypes/workflow/v1"

QWEN_UBUNTU_WITNESS_ID = "qwen3-0.6b-gh-ubuntu-abad124"
QWEN_UBUNTU_BASE_CAPSULE_ID = "qwen3-0.6b-hf-c1899de2"
QWEN_UBUNTU_BASE_LAUNCH_DIGEST = (
    "sha256:efa50b06d297a92b3760320a85aea0a965f74b0dd74a29d56d4a9d0856402bc1"
)
QWEN_UBUNTU_BASE_RELEASE_DIGEST = (
    "sha256:46de80335e22b537777430fc0e8dd131a45950e55b4b022ddd8c120ff3b43fc4"
)
QWEN_UBUNTU_REPOSITORY = "mynameisyou-cmyk/chillspace-commons"
QWEN_UBUNTU_SIGNER_WORKFLOW = (
    "mynameisyou-cmyk/chillspace-commons/.github/workflows/qwen3-ubuntu-witness.yml"
)
QWEN_UBUNTU_SOURCE_DIGEST = "abad1246268ebeadcbc4dc99571f84beadfd030f"
QWEN_UBUNTU_SOURCE_REF = "refs/heads/research/qwen3-06b-ubuntu-witness-20260815"
QWEN_UBUNTU_RUN_ID = "31873241774"

MAX_CONTROL_BYTES = 8 * 1024 * 1024
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_CAPSULE_FILES = 512
IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._-]{0,79}$")
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
SUBSTRATE_SCHEMAS = {
    release_v1.RELEASE_SCHEMA,
    release_v1.PROFILE_SCHEMA,
    release_v1.ATTESTATION_SCHEMA,
    release_v1.RECEIPT_SCHEMA,
}
CONTROL_SCHEMAS = SUBSTRATE_SCHEMAS | {
    PUBLISHER_INVENTORY_SCHEMA,
    WITNESS_INDEX_SCHEMA,
    WITNESS_VERIFIER_POLICY_SCHEMA,
}


class RegistryError(ValueError):
    """A registry or capsule falls outside the closed launch contract."""


@dataclass(frozen=True)
class RawFile:
    path: Path
    raw: bytes

    @property
    def digest(self) -> str:
        return "sha256:" + hashlib.sha256(self.raw).hexdigest()

    @property
    def size(self) -> int:
        return len(self.raw)


@dataclass(frozen=True)
class CapsuleResult:
    records: int
    files: int
    crypto_checks: int
    signing_key_digest: str


def _pairs_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise RegistryError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _reject_float(token: str) -> None:
    raise RegistryError(f"floating-point JSON is outside the registry contract: {token}")


def _reject_constant(token: str) -> None:
    raise RegistryError(f"non-finite JSON number: {token}")


def _parse_json(raw: bytes, label: str) -> dict[str, Any]:
    if len(raw) > MAX_CONTROL_BYTES:
        raise RegistryError(f"{label} exceeds {MAX_CONTROL_BYTES} bytes")
    try:
        text = raw.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_pairs_without_duplicates,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except RegistryError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as error:
        raise RegistryError(f"{label} is not strict UTF-8 JSON: {error}") from error
    if not isinstance(value, dict):
        raise RegistryError(f"{label} must be a JSON object")
    return value


class _ObjectPairs(list[tuple[str, Any]]):
    """Preserve object pairs while discovering a top-level schema marker."""


def _probe_control_json(raw: bytes, label: str) -> dict[str, Any] | None:
    """Discover a control record independently of its path or media type.

    Arbitrary capsule evidence may be binary, text, or publisher JSON with
    floating-point values.  Parse every bounded UTF-8 JSON object permissively
    only to inspect all top-level ``schema`` declarations.  Once a known
    control schema is present, reparse with the registry's strict duplicate,
    non-finite, and integer-only policy.
    """

    if len(raw) > MAX_CONTROL_BYTES:
        if raw.lstrip(b" \t\r\n").startswith(b"{"):
            raise RegistryError(f"{label} JSON object exceeds {MAX_CONTROL_BYTES} bytes")
        return None
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return None
    if not text.lstrip().startswith("{"):
        return None
    try:
        value = json.loads(text, object_pairs_hook=_ObjectPairs)
    except json.JSONDecodeError:
        return None
    except (ValueError, RecursionError) as error:
        raise RegistryError(f"{label} cannot be boundedly classified as JSON: {error}") from error
    if not isinstance(value, _ObjectPairs):
        return None
    declared_schemas = [item for key, item in value if key == "schema"]
    if not any(
        isinstance(schema, str) and schema in CONTROL_SCHEMAS
        for schema in declared_schemas
    ):
        return None
    return _parse_json(raw, label)


def _exact_keys(value: Any, required: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RegistryError(f"{label} must be an object")
    present = set(value)
    if present != required:
        missing = ", ".join(sorted(required - present)) or "none"
        extra = ", ".join(sorted(present - required)) or "none"
        raise RegistryError(f"{label} keys differ (missing: {missing}; extra: {extra})")
    return value


def _array(value: Any, label: str, *, maximum: int = MAX_CAPSULE_FILES) -> list[Any]:
    if not isinstance(value, list):
        raise RegistryError(f"{label} must be an array")
    if len(value) > maximum:
        raise RegistryError(f"{label} exceeds {maximum} items")
    return value


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or IDENTIFIER.fullmatch(value) is None:
        raise RegistryError(f"{label} is not a bounded lowercase identifier")
    return value


def _relative_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 500:
        raise RegistryError(f"{label} must be a non-empty relative path")
    if "\\" in value or "\x00" in value:
        raise RegistryError(f"{label} contains a forbidden path character")
    candidate = PurePosixPath(value)
    if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
        raise RegistryError(f"{label} must be normalized and traversal-free")
    normalized = candidate.as_posix()
    if normalized != value:
        raise RegistryError(f"{label} must use normalized POSIX separators")
    return value


def _descriptor(value: Any, label: str, *, with_path: bool = True) -> dict[str, Any]:
    keys = {"media_type", "digest", "size"}
    if with_path:
        keys.add("path")
    item = _exact_keys(value, keys, label)
    if with_path:
        _relative_path(item["path"], f"{label}.path")
    if not isinstance(item["media_type"], str) or not item["media_type"] or len(item["media_type"]) > 200:
        raise RegistryError(f"{label}.media_type must be a bounded string")
    if not isinstance(item["digest"], str) or DIGEST.fullmatch(item["digest"]) is None:
        raise RegistryError(f"{label}.digest must be a lowercase SHA-256 digest")
    if isinstance(item["size"], bool) or not isinstance(item["size"], int) or item["size"] < 0:
        raise RegistryError(f"{label}.size must be a non-negative integer")
    return item


def _check_root(root: Path, label: str) -> None:
    try:
        mode = os.lstat(root).st_mode
    except OSError as error:
        raise RegistryError(f"cannot inspect {label}: {error}") from error
    if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
        raise RegistryError(f"{label} must be a real directory, not a symlink")


def _safe_dir(root: Path, relative: str, label: str) -> Path:
    _relative_path(relative, label)
    cursor = root
    for part in PurePosixPath(relative).parts:
        cursor = cursor / part
        try:
            mode = os.lstat(cursor).st_mode
        except OSError as error:
            raise RegistryError(f"cannot inspect {label}: {error}") from error
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
            raise RegistryError(f"{label} contains a symlink or non-directory component")
    return cursor


def _safe_file(root: Path, relative: str, label: str) -> RawFile:
    _relative_path(relative, label)
    parts = PurePosixPath(relative).parts
    cursor = root
    for part in parts[:-1]:
        cursor = cursor / part
        try:
            mode = os.lstat(cursor).st_mode
        except OSError as error:
            raise RegistryError(f"cannot inspect {label}: {error}") from error
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
            raise RegistryError(f"{label} contains a symlink or non-directory component")
    path = cursor / parts[-1]
    try:
        mode = os.lstat(path).st_mode
    except OSError as error:
        raise RegistryError(f"cannot inspect {label}: {error}") from error
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise RegistryError(f"{label} must be a regular file, not a symlink")
    size = os.lstat(path).st_size
    if size > MAX_FILE_BYTES:
        raise RegistryError(f"{label} exceeds {MAX_FILE_BYTES} bytes")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        chunks: list[bytes] = []
        observed = 0
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            observed += len(chunk)
            if observed > MAX_FILE_BYTES:
                raise RegistryError(f"{label} changed or exceeds {MAX_FILE_BYTES} bytes")
            chunks.append(chunk)
    finally:
        os.close(descriptor)
    return RawFile(path=path, raw=b"".join(chunks))


def _walk_files(directory: Path, label: str) -> set[str]:
    result: set[str] = set()
    stack: list[tuple[Path, PurePosixPath]] = [(directory, PurePosixPath())]
    while stack:
        current, prefix = stack.pop()
        try:
            entries = sorted(os.scandir(current), key=lambda item: item.name)
        except OSError as error:
            raise RegistryError(f"cannot enumerate {label}: {error}") from error
        for entry in entries:
            relative = prefix / entry.name
            try:
                mode = entry.stat(follow_symlinks=False).st_mode
            except OSError as error:
                raise RegistryError(f"cannot inspect {label}/{relative}: {error}") from error
            if stat.S_ISLNK(mode):
                raise RegistryError(f"{label}/{relative} is a forbidden symlink")
            if stat.S_ISDIR(mode):
                stack.append((Path(entry.path), relative))
            elif stat.S_ISREG(mode):
                result.add(relative.as_posix())
            else:
                raise RegistryError(f"{label}/{relative} is not a regular file or directory")
            if len(result) > MAX_CAPSULE_FILES:
                raise RegistryError(f"{label} exceeds {MAX_CAPSULE_FILES} files")
    return result


def _match_raw(item: dict[str, Any], raw_file: RawFile, label: str) -> None:
    if item["digest"] != raw_file.digest or item["size"] != raw_file.size:
        raise RegistryError(
            f"{label} raw descriptor differs "
            f"(expected {item['digest']} / {item['size']}, got {raw_file.digest} / {raw_file.size})"
        )


def _domain_message(domain: str, digest: str) -> bytes:
    if DIGEST.fullmatch(digest) is None:
        raise RegistryError("cannot construct a signing message from an invalid digest")
    return f"{domain}\n{digest}\n".encode("utf-8")


def _openssl_version(executable: str) -> str:
    try:
        result = subprocess.run(
            [executable, "version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RegistryError(f"cannot execute OpenSSL: {error}") from error
    match = re.match(r"^OpenSSL\s+(\S+)", result.stdout.strip())
    if result.returncode != 0 or match is None:
        detail = (result.stderr or result.stdout).strip()[:300]
        raise RegistryError(f"OpenSSL version check failed: {detail}")
    version = match.group(1)
    major = re.match(r"^(\d+)[.]", version)
    if major is None or int(major.group(1)) < 3:
        raise RegistryError("OpenSSL 3.0 or newer is required for Ed25519 verification")
    return version


def _verify_ed25519(executable: str, public_key: Path, signature: Path, message: bytes, label: str) -> None:
    try:
        key_result = subprocess.run(
            [executable, "pkey", "-pubin", "-in", str(public_key), "-text", "-noout"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RegistryError(f"{label} public-key inspection failed: {error}") from error
    key_text = (key_result.stdout + key_result.stderr).upper()
    if key_result.returncode != 0 or "ED25519" not in key_text:
        raise RegistryError(f"{label} public key is not an OpenSSL-readable Ed25519 key")

    message_path: str | None = None
    try:
        # Ed25519 is a one-shot operation in OpenSSL and therefore requires a
        # seekable input; a pipe/standard input is rejected.  The bounded
        # domain message is written to a private temporary regular file and
        # unlinked immediately after the verifier returns.
        with tempfile.NamedTemporaryFile(prefix="kingdom-ed25519-", delete=False) as handle:
            handle.write(message)
            message_path = handle.name
        result = subprocess.run(
            [
                executable,
                "pkeyutl",
                "-verify",
                "-pubin",
                "-inkey",
                str(public_key),
                "-rawin",
                "-in",
                message_path,
                "-sigfile",
                str(signature),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RegistryError(f"{label} OpenSSL verification failed to run: {error}") from error
    finally:
        if message_path is not None:
            try:
                os.unlink(message_path)
            except FileNotFoundError:
                pass
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()[:300]
        raise RegistryError(f"{label} Ed25519 signature is invalid: {detail}")


def _public_key_fingerprint(executable: str, public_key: Path, label: str) -> str:
    """Fingerprint canonical SubjectPublicKeyInfo DER, not PEM presentation bytes."""

    try:
        result = subprocess.run(
            [executable, "pkey", "-pubin", "-in", str(public_key), "-outform", "DER"],
            check=False,
            capture_output=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RegistryError(f"{label} public-key fingerprinting failed: {error}") from error
    if result.returncode != 0 or not result.stdout:
        detail = (result.stderr or result.stdout).decode("utf-8", errors="replace").strip()[:300]
        raise RegistryError(f"{label} public-key fingerprinting failed: {detail}")
    return "sha256:" + hashlib.sha256(result.stdout).hexdigest()


def _verify_policy(policy: dict[str, Any], public_key: RawFile, label: str) -> None:
    required = {
        "schema",
        "algorithm",
        "public_key",
        "signer_identity",
        "release_domain",
        "launch_index_domain",
        "signed_value",
        "identity_claim",
        "authority_claim",
        "issuer",
    }
    _exact_keys(policy, required, label)
    expected_scalars = {
        "schema": VERIFIER_POLICY_SCHEMA,
        "algorithm": "Ed25519",
        "release_domain": RELEASE_DOMAIN,
        "launch_index_domain": LAUNCH_INDEX_DOMAIN,
        "signed_value": SIGNED_VALUE,
        "identity_claim": IDENTITY_CLAIM,
        "authority_claim": AUTHORITY_CLAIM,
        "issuer": ISSUER,
    }
    for field, expected in expected_scalars.items():
        if policy[field] != expected:
            raise RegistryError(f"{label}.{field} differs from the reviewed policy")
    public_descriptor = _descriptor(policy["public_key"], f"{label}.public_key", with_path=False)
    if public_descriptor["media_type"] != "application/x-pem-file":
        raise RegistryError(f"{label}.public_key must declare application/x-pem-file")
    _match_raw(public_descriptor, public_key, f"{label}.public_key")
    expected_identity = "urn:kingdom:ed25519:" + public_key.digest.removeprefix("sha256:")
    if policy["signer_identity"] != expected_identity:
        raise RegistryError(f"{label}.signer_identity does not fingerprint the exact PEM bytes")


def _verify_witness_policy(policy: dict[str, Any], public_key: RawFile, label: str) -> None:
    required = {
        "schema",
        "algorithm",
        "public_key",
        "signer_identity",
        "witness_index_domain",
        "signed_value",
        "identity_claim",
        "authority_claim",
        "issuer",
    }
    _exact_keys(policy, required, label)
    expected_scalars = {
        "schema": WITNESS_VERIFIER_POLICY_SCHEMA,
        "algorithm": "Ed25519",
        "witness_index_domain": WITNESS_INDEX_DOMAIN,
        "signed_value": SIGNED_VALUE,
        "identity_claim": WITNESS_IDENTITY_CLAIM,
        "authority_claim": AUTHORITY_CLAIM,
        "issuer": ISSUER,
    }
    for field, expected in expected_scalars.items():
        if policy[field] != expected:
            raise RegistryError(f"{label}.{field} differs from the reviewed witness policy")
    public_descriptor = _descriptor(policy["public_key"], f"{label}.public_key", with_path=False)
    if public_descriptor["media_type"] != "application/x-pem-file":
        raise RegistryError(f"{label}.public_key must declare application/x-pem-file")
    _match_raw(public_descriptor, public_key, f"{label}.public_key")
    expected_identity = "urn:kingdom:ed25519:" + public_key.digest.removeprefix("sha256:")
    if policy["signer_identity"] != expected_identity:
        raise RegistryError(f"{label}.signer_identity does not fingerprint the exact PEM bytes")


def _semantic_version(value: str, label: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"(0|[1-9][0-9]*)[.](0|[1-9][0-9]*)[.](0|[1-9][0-9]*)", value)
    if match is None:
        raise RegistryError(f"{label} must be a three-part semantic version")
    return tuple(int(part) for part in match.groups())


def _isolated_gh_environment(state_root: Path) -> dict[str, str]:
    """Return a secretless gh environment whose persistent roots are disposable."""

    state_paths = {
        "HOME": state_root / "home",
        "GH_CONFIG_DIR": state_root / "gh-config",
        "XDG_CONFIG_HOME": state_root / "xdg-config",
        "XDG_STATE_HOME": state_root / "xdg-state",
        "XDG_DATA_HOME": state_root / "xdg-data",
        "XDG_CACHE_HOME": state_root / "xdg-cache",
    }
    for path in state_paths.values():
        path.mkdir(parents=True, mode=0o700, exist_ok=False)
    return {
        "PATH": os.defpath,
        **{name: str(path) for name, path in state_paths.items()},
        "GH_PROMPT_DISABLED": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "GH_TELEMETRY": "false",
        "DO_NOT_TRACK": "true",
        "GH_NO_UPDATE_NOTIFIER": "1",
        "HTTP_PROXY": "http://127.0.0.1:9",
        "HTTPS_PROXY": "http://127.0.0.1:9",
        "ALL_PROXY": "http://127.0.0.1:9",
        "NO_PROXY": "",
        "http_proxy": "http://127.0.0.1:9",
        "https_proxy": "http://127.0.0.1:9",
        "all_proxy": "http://127.0.0.1:9",
        "no_proxy": "",
    }


def _gh_version(executable: str, minimum: str, environment: dict[str, str]) -> str:
    try:
        result = subprocess.run(
            [executable, "version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RegistryError(f"cannot execute gh: {error}") from error
    first_line = result.stdout.splitlines()[0] if result.stdout else ""
    match = re.fullmatch(r"gh version ([0-9]+[.][0-9]+[.][0-9]+)(?: .*)?", first_line)
    if result.returncode != 0 or match is None:
        detail = (result.stderr or result.stdout).strip()[:300]
        raise RegistryError(f"gh version check failed: {detail}")
    version = match.group(1)
    if _semantic_version(version, "gh version") < _semantic_version(minimum, "minimum gh version"):
        raise RegistryError(f"gh {minimum} or newer is required for offline attestation verification")
    return version


def _validate_gh_verified_identity(value: Any, signer_workflow: str, label: str) -> None:
    """Accept the two exact SAN-regex spellings emitted by reviewed gh versions."""

    identity = _exact_keys(
        value,
        {"subjectAlternativeName", "issuer", "runnerEnvironment"},
        f"{label} verified identity",
    )
    subject = _exact_keys(
        identity["subjectAlternativeName"],
        {"subjectAlternativeName", "regexp"},
        f"{label} verified identity subject",
    )
    issuer = _exact_keys(
        identity["issuer"], {"issuer", "regexp"}, f"{label} verified identity issuer"
    )
    legacy_regexp = f"^https://github.com/{signer_workflow}"
    literal_dot_regexp = legacy_regexp.replace(".", r"\.")
    if (
        subject.get("subjectAlternativeName") != ""
        or subject.get("regexp") not in {legacy_regexp, literal_dot_regexp}
        or issuer != {"issuer": "", "regexp": ".*"}
        or identity["runnerEnvironment"] != "github-hosted"
    ):
        observed = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        raise RegistryError(f"{label} gh verified identity constraints differ: {observed}")


def _load_json_array(raw: bytes, label: str) -> list[Any]:
    if len(raw) > MAX_CONTROL_BYTES:
        raise RegistryError(f"{label} exceeds {MAX_CONTROL_BYTES} bytes")
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_pairs_without_duplicates,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except RegistryError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as error:
        raise RegistryError(f"{label} is not strict UTF-8 JSON: {error}") from error
    if not isinstance(value, list):
        raise RegistryError(f"{label} must be a JSON array")
    return value


def _verify_archive_members(
    archive: RawFile,
    mappings: list[tuple[str, str]],
    files: dict[str, tuple[dict[str, Any], RawFile]],
    label: str,
) -> None:
    """Verify the deterministic GNU tar and its indexed, extracted byte copies."""

    if len(archive.raw) < 1024 or len(archive.raw) % 512 or not archive.raw.endswith(b"\0" * 1024):
        raise RegistryError(f"{label} is not a complete uncompressed tar stream")
    try:
        with tarfile.open(fileobj=io.BytesIO(archive.raw), mode="r:") as handle:
            members = handle.getmembers()
            expected_names = ["."] + [f"./{name}" for name, _ in mappings]
            if [member.name for member in members] != expected_names:
                raise RegistryError(f"{label} members differ from the sorted witness mapping")
            root = members[0]
            if (
                not root.isdir()
                or root.mode != 0o755
                or root.uid != 0
                or root.gid != 0
                or root.mtime != 0
                or root.uname != ""
                or root.gname != ""
                or root.linkname != ""
                or root.size != 0
                or root.pax_headers
            ):
                raise RegistryError(f"{label} root metadata is not deterministic")
            for member, (member_name, indexed_path) in zip(members[1:], mappings, strict=True):
                if (
                    not member.isfile()
                    or member.name != f"./{member_name}"
                    or member.mode != 0o644
                    or member.uid != 0
                    or member.gid != 0
                    or member.mtime != 0
                    or member.uname != ""
                    or member.gname != ""
                    or member.linkname != ""
                    or member.pax_headers
                ):
                    raise RegistryError(f"{label} member metadata is not deterministic: {member_name}")
                extracted = handle.extractfile(member)
                if extracted is None:
                    raise RegistryError(f"{label} member cannot be read: {member_name}")
                member_raw = extracted.read(MAX_FILE_BYTES + 1)
                if len(member_raw) > MAX_FILE_BYTES or member_raw != files[indexed_path][1].raw:
                    raise RegistryError(
                        f"{label} member bytes differ from indexed extracted evidence: {member_name}"
                    )
            for number, member in enumerate(members):
                data_end = member.offset_data + member.size
                next_offset = (
                    members[number + 1].offset
                    if number + 1 < len(members)
                    else ((data_end + 511) // 512) * 512
                )
                if any(archive.raw[data_end:next_offset]):
                    raise RegistryError(f"{label} contains non-zero member padding")
            final_end = ((members[-1].offset_data + members[-1].size + 511) // 512) * 512
            if any(archive.raw[final_end:]):
                raise RegistryError(f"{label} contains non-zero trailing tar bytes")
    except RegistryError:
        raise
    except (tarfile.TarError, EOFError, OSError) as error:
        raise RegistryError(f"{label} cannot be parsed as a bounded uncompressed tar: {error}") from error


def _verify_github_attestation(
    gh: str,
    artifact: RawFile,
    bundle: RawFile,
    trusted_root: RawFile,
    policy: dict[str, Any],
    label: str,
) -> None:
    verifier = _exact_keys(policy["verifier"], {"name", "minimum_version", "source_revision"}, f"{label}.verifier")
    if verifier != {
        "name": "gh",
        "minimum_version": GH_ATTESTATION_MINIMUM_VERSION,
        "source_revision": GH_ATTESTATION_SOURCE_REVISION,
    }:
        raise RegistryError(f"{label}.verifier differs from the reviewed offline verifier policy")
    repository = policy["repository"]
    signer_workflow = policy["signer_workflow"]
    source_digest = policy["source_digest"]
    source_ref = policy["source_ref"]
    run_id = policy["run_id"]
    run_attempt = policy["run_attempt"]
    if not isinstance(repository, str) or re.fullmatch(r"[a-z0-9_.-]+/[a-z0-9_.-]+", repository) is None:
        raise RegistryError(f"{label}.repository must be one normalized GitHub owner/repository")
    expected_workflow_prefix = repository + "/.github/workflows/"
    if (
        not isinstance(signer_workflow, str)
        or not signer_workflow.startswith(expected_workflow_prefix)
        or PurePosixPath(signer_workflow).name not in {
            "qwen3-ubuntu-witness.yml",
            "qwen3-ubuntu-witness.yaml",
        }
    ):
        raise RegistryError(f"{label}.signer_workflow differs from the bounded witness workflow")
    if not isinstance(source_digest, str) or re.fullmatch(r"[0-9a-f]{40}", source_digest) is None:
        raise RegistryError(f"{label}.source_digest must be one lowercase Git commit id")
    if not isinstance(source_ref, str) or not source_ref.startswith("refs/heads/"):
        raise RegistryError(f"{label}.source_ref must be one full branch ref")
    if not isinstance(run_id, str) or re.fullmatch(r"[1-9][0-9]*", run_id) is None:
        raise RegistryError(f"{label}.run_id must be a positive decimal string")
    if isinstance(run_attempt, bool) or not isinstance(run_attempt, int) or run_attempt <= 0:
        raise RegistryError(f"{label}.run_attempt must be a positive integer")
    if policy["predicate_type"] != SLSA_PROVENANCE_V1:
        raise RegistryError(f"{label}.predicate_type differs from SLSA provenance v1")
    if policy["runner_environment"] != "github-hosted":
        raise RegistryError(f"{label}.runner_environment must be github-hosted")
    if trusted_root.digest != GH_TRUSTED_ROOT_DIGEST:
        raise RegistryError(f"{label}.trusted_root differs from the pinned raw trusted-root digest")

    with tempfile.TemporaryDirectory(prefix="kingdom-gh-state-") as state_directory:
        environment = _isolated_gh_environment(Path(state_directory))
        _gh_version(gh, verifier["minimum_version"], environment)
        command = [
            gh,
            "attestation",
            "verify",
            str(artifact.path),
            "--repo",
            repository,
            "--signer-workflow",
            signer_workflow,
            "--source-digest",
            source_digest,
            "--source-ref",
            source_ref,
            "--predicate-type",
            policy["predicate_type"],
            "--deny-self-hosted-runners",
            "--bundle",
            str(bundle.path),
            "--custom-trusted-root",
            str(trusted_root.path),
            "--format=json",
        ]
        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                timeout=30,
                env=environment,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise RegistryError(f"{label} offline gh verification failed to run: {error}") from error
    if result.returncode != 0:
        detail_raw = result.stderr or result.stdout
        detail = detail_raw.decode("utf-8", errors="replace").strip()[:500]
        raise RegistryError(f"{label} offline gh verification failed: {detail}")
    verified = _load_json_array(result.stdout, f"{label} gh verification output")
    if len(verified) != 1:
        raise RegistryError(f"{label} must verify exactly one bundled attestation")
    verification = _exact_keys(
        verified[0], {"attestation", "verificationResult"}, f"{label} verified attestation"
    )["verificationResult"]
    verification = _exact_keys(
        verification,
        {"mediaType", "signature", "statement", "verifiedIdentity", "verifiedTimestamps"},
        f"{label} verificationResult",
    )
    if verification["mediaType"] != (
        "application/vnd.dev.sigstore.verificationresult+json;version=0.1"
    ):
        raise RegistryError(f"{label} gh verification-result media type differs")
    _validate_gh_verified_identity(verification["verifiedIdentity"], signer_workflow, label)
    statement = _exact_keys(
        verification["statement"],
        {"_type", "subject", "predicateType", "predicate"},
        f"{label} verified statement",
    )
    expected_subject = [
        {
            "name": artifact.path.name,
            "digest": {"sha256": artifact.digest.removeprefix("sha256:")},
        }
    ]
    if (
        statement["_type"] != "https://in-toto.io/Statement/v1"
        or statement["subject"] != expected_subject
        or statement["predicateType"] != policy["predicate_type"]
    ):
        raise RegistryError(f"{label} verified statement subject or predicate differs")
    predicate = _exact_keys(
        statement["predicate"], {"buildDefinition", "runDetails"}, f"{label} SLSA predicate"
    )
    build_definition = _exact_keys(
        predicate["buildDefinition"],
        {"buildType", "externalParameters", "internalParameters", "resolvedDependencies"},
        f"{label} SLSA build definition",
    )
    run_details = _exact_keys(
        predicate["runDetails"], {"builder", "metadata"}, f"{label} SLSA run details"
    )
    workflow_path = signer_workflow.removeprefix(repository + "/")
    workflow_url = f"https://github.com/{repository}"
    expected_builder = f"{workflow_url}/{workflow_path}@{source_ref}"
    expected_invocation = f"{workflow_url}/actions/runs/{run_id}/attempts/{run_attempt}"
    external = _exact_keys(
        build_definition["externalParameters"], {"workflow"}, f"{label} external parameters"
    )
    internal = _exact_keys(
        build_definition["internalParameters"], {"github"}, f"{label} internal parameters"
    )
    github_parameters = _exact_keys(
        internal["github"],
        {"event_name", "repository_id", "repository_owner_id", "runner_environment"},
        f"{label} internal GitHub parameters",
    )
    dependencies = build_definition["resolvedDependencies"]
    if (
        build_definition["buildType"] != GITHUB_ACTIONS_BUILD_TYPE_V1
        or external["workflow"]
        != {"path": workflow_path, "ref": source_ref, "repository": workflow_url}
        or github_parameters["event_name"] != "push"
        or github_parameters["runner_environment"] != "github-hosted"
        or any(
            not isinstance(github_parameters[field], str)
            or re.fullmatch(r"[1-9][0-9]*", github_parameters[field]) is None
            for field in ("repository_id", "repository_owner_id")
        )
        or dependencies
        != [{"digest": {"gitCommit": source_digest}, "uri": f"git+{workflow_url}@{source_ref}"}]
        or run_details["builder"] != {"id": expected_builder}
        or run_details["metadata"] != {"invocationId": expected_invocation}
    ):
        raise RegistryError(f"{label} verified workflow provenance constraints differ")
    signature = _exact_keys(
        verification["signature"], {"certificate"}, f"{label} verified signature"
    )
    certificate = signature["certificate"]
    if not isinstance(certificate, dict) or any(
        certificate.get(field) != expected
        for field, expected in {
            "issuer": "https://token.actions.githubusercontent.com",
            "subjectAlternativeName": expected_builder,
            "githubWorkflowTrigger": "push",
            "githubWorkflowSHA": source_digest,
            "githubWorkflowRepository": repository,
            "githubWorkflowRef": source_ref,
            "buildSignerURI": expected_builder,
            "buildSignerDigest": source_digest,
            "buildTrigger": "push",
            "runnerEnvironment": "github-hosted",
            "sourceRepositoryURI": workflow_url,
            "sourceRepositoryDigest": source_digest,
            "sourceRepositoryRef": source_ref,
            "runInvocationURI": expected_invocation,
            "sourceRepositoryVisibilityAtSigning": "public",
        }.items()
    ):
        raise RegistryError(f"{label} verified certificate provenance constraints differ")
    timestamps = _array(
        verification["verifiedTimestamps"], f"{label} verified timestamps", maximum=32
    )
    if not timestamps or not any(
        isinstance(item, dict) and item.get("type") in {"Tlog", "TSA"}
        for item in timestamps
    ):
        raise RegistryError(f"{label} lacks a verified transparency-log or timestamp witness")


def _record_path(item: Any, label: str) -> tuple[str, str]:
    record = _exact_keys(item, {"path", "receipt"}, label)
    return (
        _relative_path(record["path"], f"{label}.path"),
        _relative_path(record["receipt"], f"{label}.receipt"),
    )


def _validate_publisher_inventory(
    inventory: dict[str, Any],
    label: str,
) -> None:
    """Check a publisher file inventory and its declared raw-source descriptor."""

    _exact_keys(
        inventory,
        {
            "schema",
            "publisher",
            "repository",
            "revision",
            "revision_timestamp",
            "retrieved_at",
            "source",
            "source_descriptor",
            "summary",
            "files",
        },
        label,
    )
    if inventory["schema"] != PUBLISHER_INVENTORY_SCHEMA:
        raise RegistryError(f"{label}.schema differs")
    for field in ("publisher", "repository", "revision_timestamp", "retrieved_at", "source"):
        if not isinstance(inventory[field], str) or not inventory[field]:
            raise RegistryError(f"{label}.{field} must be a non-empty string")
    revision = inventory["revision"]
    if not isinstance(revision, str) or re.fullmatch(r"[0-9a-f]{40}", revision) is None:
        raise RegistryError(f"{label}.revision must be an immutable lowercase Git object id")
    if not inventory["source"].startswith("https://"):
        raise RegistryError(f"{label}.source must use HTTPS")

    source_descriptor = _descriptor(
        inventory["source_descriptor"], f"{label}.source_descriptor", with_path=False
    )
    if source_descriptor["media_type"] != "application/json":
        raise RegistryError(f"{label}.source_descriptor must be application/json")

    rows = _array(inventory["files"], f"{label}.files")
    if not rows:
        raise RegistryError(f"{label}.files cannot be empty")
    paths: list[str] = []
    total_bytes = 0
    numbered_weight_rows: list[dict[str, Any]] = []
    single_weight_row: dict[str, Any] | None = None
    for number, value in enumerate(rows):
        row_label = f"{label}.files[{number}]"
        if not isinstance(value, dict):
            raise RegistryError(f"{row_label} must be an object")
        optional = {"published_content", "pointer_size"}
        required = {"path", "size", "repository_object"}
        if not required <= set(value) or set(value) - required - optional:
            raise RegistryError(f"{row_label} keys differ from the reviewed inventory shape")
        path = _relative_path(value["path"], f"{row_label}.path")
        size = value["size"]
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise RegistryError(f"{row_label}.size must be a non-negative integer")
        repository_object = value["repository_object"]
        if (
            not isinstance(repository_object, str)
            or re.fullmatch(r"sha1:[0-9a-f]{40}", repository_object) is None
        ):
            raise RegistryError(f"{row_label}.repository_object must be a Git SHA-1 object id")
        has_content = "published_content" in value
        has_pointer = "pointer_size" in value
        if has_content != has_pointer:
            raise RegistryError(f"{row_label} must carry published_content and pointer_size together")
        if has_content:
            content = _exact_keys(
                value["published_content"], {"digest", "size"}, f"{row_label}.published_content"
            )
            if not isinstance(content["digest"], str) or DIGEST.fullmatch(content["digest"]) is None:
                raise RegistryError(f"{row_label}.published_content.digest is invalid")
            if isinstance(content["size"], bool) or not isinstance(content["size"], int):
                raise RegistryError(f"{row_label}.published_content.size must be an integer")
            if content["size"] != size:
                raise RegistryError(f"{row_label}.published_content.size differs from file size")
            pointer_size = value["pointer_size"]
            if isinstance(pointer_size, bool) or not isinstance(pointer_size, int) or pointer_size <= 0:
                raise RegistryError(f"{row_label}.pointer_size must be a positive integer")
        paths.append(path)
        total_bytes += size
        numbered_weight = re.fullmatch(
            r"model-[0-9]{5}-of-[0-9]{6}[.]safetensors", path
        ) is not None
        single_weight = path == "model.safetensors"
        if numbered_weight or single_weight:
            if not has_content:
                raise RegistryError(f"{row_label} weight file lacks a published content digest")
            if single_weight:
                single_weight_row = value
            else:
                numbered_weight_rows.append(value)
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise RegistryError(f"{label}.files must be sorted and path-unique")

    if single_weight_row is not None and numbered_weight_rows:
        raise RegistryError(
            f"{label} must not mix model.safetensors with numbered weight shards"
        )
    if single_weight_row is not None:
        weight_rows = [single_weight_row]
    else:
        weight_rows = numbered_weight_rows
        expected_weight_paths = [
            f"model-{number:05d}-of-{len(weight_rows):06d}.safetensors"
            for number in range(1, len(weight_rows) + 1)
        ]
        actual_weight_paths = [row["path"] for row in weight_rows]
        if actual_weight_paths != expected_weight_paths:
            raise RegistryError(f"{label} weight shards are not one complete numbered sequence")
    summary = _exact_keys(
        inventory["summary"],
        {"file_count", "total_bytes", "weight_shards", "weight_bytes"},
        f"{label}.summary",
    )
    if any(isinstance(value, bool) or not isinstance(value, int) for value in summary.values()):
        raise RegistryError(f"{label}.summary values must be integers")
    observed_summary = {
        "file_count": len(rows),
        "total_bytes": total_bytes,
        "weight_shards": len(weight_rows),
        "weight_bytes": sum(row["size"] for row in weight_rows),
    }
    if summary != observed_summary:
        raise RegistryError(f"{label}.summary differs from its file rows")


def _validate_witness_capsule(
    source_root: Path,
    entry: dict[str, Any],
    openssl: str,
    capsule_id: str,
    capsule: Path,
    launch_descriptor: dict[str, Any],
    signature_descriptor: dict[str, Any],
    launch_raw: RawFile,
    launch_signature_raw: RawFile,
    index: dict[str, Any],
    entries_by_id: dict[str, dict[str, Any]],
) -> CapsuleResult:
    label = f"capsule {capsule_id} witness index"
    _exact_keys(
        index,
        {
            "schema",
            "capsule_id",
            "base_release",
            "files",
            "records",
            "profile_sets",
            "archive_evidence",
            "github_attestation",
            "witness_signature",
            "non_claims",
        },
        label,
    )
    if index["schema"] != WITNESS_INDEX_SCHEMA or index["capsule_id"] != capsule_id:
        raise RegistryError(f"capsule {capsule_id} witness index identity differs")
    if index["non_claims"] != WITNESS_INDEX_NON_CLAIMS:
        raise RegistryError(f"capsule {capsule_id} witness-index non-claims changed")

    file_items = _array(index["files"], f"capsule {capsule_id} files")
    if not file_items:
        raise RegistryError(f"capsule {capsule_id} files cannot be empty")
    files: dict[str, tuple[dict[str, Any], RawFile]] = {}
    for number, value in enumerate(file_items):
        item = _descriptor(value, f"capsule {capsule_id} files[{number}]")
        path = item["path"]
        if any(existing.casefold() == path.casefold() for existing in files):
            raise RegistryError(f"capsule {capsule_id} contains a duplicate or case-folded path: {path}")
        if path in {launch_descriptor["path"], signature_descriptor["path"]}:
            raise RegistryError(f"capsule {capsule_id} files must exclude witness index and its signature")
        raw_file = _safe_file(capsule, path, f"capsule {capsule_id}/{path}")
        _match_raw(item, raw_file, f"capsule {capsule_id}/{path}")
        files[path] = (item, raw_file)
    if list(files) != sorted(files):
        raise RegistryError(f"capsule {capsule_id} files must be sorted by path")
    all_paths = list(files) + [launch_descriptor["path"], signature_descriptor["path"]]
    if len({path.casefold() for path in all_paths}) != len(all_paths):
        raise RegistryError(f"capsule {capsule_id} contains case-folded control/file paths")
    expected_files = set(files) | {launch_descriptor["path"], signature_descriptor["path"]}
    actual_files = _walk_files(capsule, f"capsule {capsule_id}")
    if actual_files != expected_files:
        missing = ", ".join(sorted(expected_files - actual_files)) or "none"
        extra = ", ".join(sorted(actual_files - expected_files)) or "none"
        raise RegistryError(
            f"capsule {capsule_id} file inventory differs (missing: {missing}; extra: {extra})"
        )

    record_items = _array(index["records"], f"capsule {capsule_id} records", maximum=2)
    if len(record_items) != 2:
        raise RegistryError(f"capsule {capsule_id} witness must enumerate exactly two v1 records")
    record_pairs = [
        _record_path(value, f"capsule {capsule_id} records[{number}]")
        for number, value in enumerate(record_items)
    ]
    if record_pairs != sorted(record_pairs):
        raise RegistryError(f"capsule {capsule_id} records must be sorted by path")
    record_paths = [path for path, _ in record_pairs]
    receipt_paths = [receipt for _, receipt in record_pairs]
    if (
        len(set(record_paths)) != 2
        or len(set(receipt_paths)) != 2
        or set(record_paths) & set(receipt_paths)
        or not (set(record_paths) | set(receipt_paths)) <= set(files)
    ):
        raise RegistryError(f"capsule {capsule_id} record/receipt graph is not closed and path-unique")
    records: dict[str, dict[str, Any]] = {}
    record_digests: dict[str, str] = {}
    for record_path, receipt_path in record_pairs:
        record_loaded = release_v1.read_document(
            files[record_path][1].path, f"capsule record {record_path}"
        )
        try:
            record_digest = release_v1.validate_document(record_loaded.value)
            receipt_loaded = release_v1.read_document(
                files[receipt_path][1].path, f"capsule receipt {receipt_path}"
            )
            release_v1.verify_receipt(record_loaded, receipt_loaded.value)
        except release_v1.ReleaseError as error:
            raise RegistryError(f"capsule {capsule_id} v1 verification failed: {error}") from error
        records[record_path] = record_loaded.value
        record_digests[record_path] = record_digest

    substrate_paths: set[str] = set()
    witness_policy_paths: set[str] = set()
    for path, (_, raw_file) in files.items():
        candidate = _probe_control_json(raw_file.raw, f"capsule {capsule_id}/{path}")
        if candidate is None:
            continue
        if candidate.get("schema") in SUBSTRATE_SCHEMAS:
            substrate_paths.add(path)
        elif candidate.get("schema") == WITNESS_VERIFIER_POLICY_SCHEMA:
            witness_policy_paths.add(path)
        elif candidate.get("schema") == WITNESS_INDEX_SCHEMA:
            raise RegistryError(f"capsule {capsule_id} embeds an unregistered witness index: {path}")
    expected_substrate_paths = set(record_paths) | set(receipt_paths)
    if substrate_paths != expected_substrate_paths:
        missing = ", ".join(sorted(expected_substrate_paths - substrate_paths)) or "none"
        extra = ", ".join(sorted(substrate_paths - expected_substrate_paths)) or "none"
        raise RegistryError(
            f"capsule {capsule_id} v1 record enumeration differs (missing: {missing}; extra: {extra})"
        )
    profiles = [path for path, value in records.items() if value["schema"] == release_v1.PROFILE_SCHEMA]
    evaluations = [
        path
        for path, value in records.items()
        if value["schema"] == release_v1.ATTESTATION_SCHEMA
        and value.get("predicate_type") == "evaluation"
    ]
    if len(profiles) != 1 or len(evaluations) != 1 or len(profiles) + len(evaluations) != 2:
        raise RegistryError(
            f"capsule {capsule_id} witness must contain one profile and one evaluation attestation"
        )
    profile_path = profiles[0]
    evaluation_path = evaluations[0]
    profile = records[profile_path]
    evaluation_record = records[evaluation_path]
    if evaluation_record.get("evidence_class") != "curator-observed":
        raise RegistryError(f"capsule {capsule_id} evaluation must be curator-observed")
    if (
        profile.get("backend", {}).get("provider")
        != "KINGDOM workflow on a GitHub-hosted runner"
        or profile.get("hardware", {}).get("visibility") != "observed"
    ):
        raise RegistryError(f"capsule {capsule_id} profile is not the bounded remote GitHub witness")

    base = _exact_keys(
        index["base_release"],
        {"capsule_id", "launch_index_digest", "release_path", "release_canonical_digest"},
        f"capsule {capsule_id} base_release",
    )
    if capsule_id == QWEN_UBUNTU_WITNESS_ID and base != {
        "capsule_id": QWEN_UBUNTU_BASE_CAPSULE_ID,
        "launch_index_digest": QWEN_UBUNTU_BASE_LAUNCH_DIGEST,
        "release_path": "release.json",
        "release_canonical_digest": QWEN_UBUNTU_BASE_RELEASE_DIGEST,
    }:
        raise RegistryError(f"capsule {capsule_id} differs from its reviewed Qwen base anchor")
    base_id = _identifier(base["capsule_id"], f"capsule {capsule_id} base_release.capsule_id")
    if base_id == capsule_id or base_id not in entries_by_id:
        raise RegistryError(f"capsule {capsule_id} base release must name another registered capsule")
    if not isinstance(base["launch_index_digest"], str) or DIGEST.fullmatch(base["launch_index_digest"]) is None:
        raise RegistryError(f"capsule {capsule_id} base launch-index digest is invalid")
    if not isinstance(base["release_canonical_digest"], str) or DIGEST.fullmatch(base["release_canonical_digest"]) is None:
        raise RegistryError(f"capsule {capsule_id} base release canonical digest is invalid")
    base_release_path = _relative_path(
        base["release_path"], f"capsule {capsule_id} base_release.release_path"
    )
    base_entry = entries_by_id[base_id]
    base_capsule_relative = _relative_path(
        base_entry["capsule"], f"capsule {capsule_id} referenced base capsule"
    )
    if PurePosixPath(base_capsule_relative).parts != ("capsules", base_id):
        raise RegistryError(f"capsule {capsule_id} referenced base capsule path differs")
    base_capsule = _safe_dir(source_root, base_capsule_relative, f"base capsule {base_id}")
    base_launch_descriptor = _descriptor(
        base_entry["launch_index"], f"capsule {capsule_id} referenced base launch index"
    )
    if base_launch_descriptor["digest"] != base["launch_index_digest"]:
        raise RegistryError(f"capsule {capsule_id} base launch-index digest differs from registry")
    base_launch_raw = _safe_file(
        base_capsule,
        base_launch_descriptor["path"],
        f"capsule {capsule_id} referenced base launch index",
    )
    _match_raw(
        base_launch_descriptor,
        base_launch_raw,
        f"capsule {capsule_id} referenced base launch index",
    )
    base_index = _parse_json(base_launch_raw.raw, f"capsule {capsule_id} referenced base launch index")
    if base_index.get("schema") != LAUNCH_INDEX_SCHEMA or base_index.get("capsule_id") != base_id:
        raise RegistryError(f"capsule {capsule_id} base anchor is not a registered release launch index")
    base_file_rows = [
        _descriptor(value, f"capsule {capsule_id} referenced base files[{number}]")
        for number, value in enumerate(_array(base_index.get("files"), "referenced base files"))
    ]
    base_release_rows = [row for row in base_file_rows if row["path"] == base_release_path]
    base_record_pairs = [
        _record_path(value, f"capsule {capsule_id} referenced base records[{number}]")
        for number, value in enumerate(_array(base_index.get("records"), "referenced base records"))
    ]
    if len(base_release_rows) != 1 or base_release_path not in {path for path, _ in base_record_pairs}:
        raise RegistryError(f"capsule {capsule_id} base release path is not one indexed v1 record")
    base_release_raw = _safe_file(
        base_capsule, base_release_path, f"capsule {capsule_id} referenced base release"
    )
    _match_raw(base_release_rows[0], base_release_raw, f"capsule {capsule_id} referenced base release")
    base_release_loaded = release_v1.read_document(
        base_release_raw.path, f"capsule {capsule_id} referenced base release"
    )
    try:
        base_release_digest = release_v1.validate_document(base_release_loaded.value)
    except release_v1.ReleaseError as error:
        raise RegistryError(f"capsule {capsule_id} base release verification failed: {error}") from error
    if base_release_loaded.value.get("schema") != release_v1.RELEASE_SCHEMA:
        raise RegistryError(f"capsule {capsule_id} base release path is not a model release")
    if base_release_digest != base["release_canonical_digest"]:
        raise RegistryError(f"capsule {capsule_id} base release canonical digest differs")

    profile_sets = _array(index["profile_sets"], f"capsule {capsule_id} profile_sets", maximum=1)
    if len(profile_sets) != 1:
        raise RegistryError(f"capsule {capsule_id} witness must have exactly one profile set")
    profile_set = _exact_keys(
        profile_sets[0], {"profile", "attestations"}, f"capsule {capsule_id} profile_sets[0]"
    )
    set_profile = _relative_path(profile_set["profile"], "witness profile-set profile")
    set_attestations = _array(
        profile_set["attestations"], "witness profile-set attestations", maximum=1
    )
    if set_profile != profile_path or set_attestations != [evaluation_path]:
        raise RegistryError(f"capsule {capsule_id} witness profile set differs from its exact records")
    try:
        release_v1.verify_set(base_release_loaded.value, profile, [evaluation_record])
    except release_v1.ReleaseError as error:
        raise RegistryError(f"capsule {capsule_id} base/profile/evaluation binding failed: {error}") from error

    evaluated = evaluation_record["evaluation"]
    if (
        evaluated["release_digest"] != base_release_digest
        or evaluated["execution_profile_digest"] != record_digests[profile_path]
    ):
        raise RegistryError(f"capsule {capsule_id} evaluation does not bind its exact base release/profile")
    evaluated_descriptors = [
        ("artifact", artifact["name"], artifact["descriptor"])
        for artifact in evaluated["artifacts"]
    ]
    evaluated_descriptors.extend(
        ("benchmark", field, evaluated["benchmark"][field])
        for field in ("dataset", "preprocessing", "scoring")
    )
    resolved_paths: dict[tuple[str, str], str] = {}
    for descriptor_kind, descriptor_name, descriptor in evaluated_descriptors:
        matching_paths = [
            file_path
            for file_path, (file_item, raw_file) in files.items()
            if file_item["media_type"] == descriptor["media_type"]
            and raw_file.digest == descriptor["digest"]
            and raw_file.size == descriptor["size"]
        ]
        if len(matching_paths) != 1:
            raise RegistryError(
                f"capsule {capsule_id} evaluation {descriptor_kind} {descriptor_name} "
                "must match exactly one indexed raw file"
            )
        resolved_paths[(descriptor_kind, descriptor_name)] = matching_paths[0]
    artifact_paths = [
        resolved_paths[("artifact", artifact["name"])] for artifact in evaluated["artifacts"]
    ]
    benchmark_paths = [
        resolved_paths[("benchmark", field)] for field in ("dataset", "preprocessing", "scoring")
    ]
    if len(artifact_paths) != len(set(artifact_paths)):
        raise RegistryError(f"capsule {capsule_id} evaluation artifacts must resolve to path-unique files")
    if len(set(benchmark_paths)) != 3:
        raise RegistryError(f"capsule {capsule_id} evaluation benchmark roles must resolve to distinct files")
    if set(artifact_paths) & set(benchmark_paths):
        raise RegistryError(f"capsule {capsule_id} evaluation artifact and benchmark paths must be disjoint")

    archive_evidence = _exact_keys(
        index["archive_evidence"], {"archive", "members"}, f"capsule {capsule_id} archive_evidence"
    )
    archive_path = _relative_path(
        archive_evidence["archive"], f"capsule {capsule_id} archive_evidence.archive"
    )
    if archive_path not in files or files[archive_path][0]["media_type"] != "application/x-tar":
        raise RegistryError(f"capsule {capsule_id} evidence archive must be one indexed application/x-tar")
    member_items = _array(
        archive_evidence["members"], f"capsule {capsule_id} archive members", maximum=11
    )
    if len(member_items) != 11:
        raise RegistryError(f"capsule {capsule_id} evidence archive must map exactly eleven members")
    mappings: list[tuple[str, str]] = []
    for number, value in enumerate(member_items):
        member = _exact_keys(
            value, {"member", "path"}, f"capsule {capsule_id} archive members[{number}]"
        )
        member_name = _relative_path(member["member"], "archive member")
        indexed_path = _relative_path(member["path"], "archive extracted evidence path")
        if PurePosixPath(member_name).name != member_name:
            raise RegistryError(f"capsule {capsule_id} archive member names must be root-level basenames")
        if indexed_path != f"evidence/execution/{member_name}" or indexed_path not in files:
            raise RegistryError(f"capsule {capsule_id} archive member path is outside exact extracted evidence")
        mappings.append((member_name, indexed_path))
    if mappings != sorted(mappings) or len({name.casefold() for name, _ in mappings}) != len(mappings):
        raise RegistryError(f"capsule {capsule_id} archive member mapping must be sorted and case-unique")
    _verify_archive_members(
        files[archive_path][1], mappings, files, f"capsule {capsule_id} evidence archive"
    )

    attestation = _exact_keys(
        index["github_attestation"],
        {
            "artifact",
            "bundle",
            "trusted_root",
            "repository",
            "signer_workflow",
            "source_digest",
            "source_ref",
            "run_id",
            "run_attempt",
            "predicate_type",
            "runner_environment",
            "verifier",
        },
        f"capsule {capsule_id} github_attestation",
    )
    if capsule_id == QWEN_UBUNTU_WITNESS_ID:
        expected_provenance = {
            "repository": QWEN_UBUNTU_REPOSITORY,
            "signer_workflow": QWEN_UBUNTU_SIGNER_WORKFLOW,
            "source_digest": QWEN_UBUNTU_SOURCE_DIGEST,
            "source_ref": QWEN_UBUNTU_SOURCE_REF,
            "run_id": QWEN_UBUNTU_RUN_ID,
            "run_attempt": 1,
            "predicate_type": SLSA_PROVENANCE_V1,
            "runner_environment": "github-hosted",
            "verifier": {
                "name": "gh",
                "minimum_version": GH_ATTESTATION_MINIMUM_VERSION,
                "source_revision": GH_ATTESTATION_SOURCE_REVISION,
            },
        }
        if any(attestation[field] != expected for field, expected in expected_provenance.items()):
            raise RegistryError(f"capsule {capsule_id} differs from its reviewed GitHub provenance")
    attestation_paths = {
        field: _relative_path(attestation[field], f"capsule {capsule_id} github_attestation.{field}")
        for field in ("artifact", "bundle", "trusted_root")
    }
    if attestation_paths["artifact"] != archive_path:
        raise RegistryError(f"capsule {capsule_id} GitHub attestation names a different artifact")
    for field in ("bundle", "trusted_root"):
        if attestation_paths[field] not in files:
            raise RegistryError(f"capsule {capsule_id} GitHub attestation {field} is outside files")
        if files[attestation_paths[field]][0]["media_type"] != "application/jsonl":
            raise RegistryError(f"capsule {capsule_id} GitHub attestation {field} must use application/jsonl")
    gh = shutil.which("gh")
    if gh is None:
        raise RegistryError("gh is required for offline GitHub attestation verification")
    _verify_github_attestation(
        gh,
        files[archive_path][1],
        files[attestation_paths["bundle"]][1],
        files[attestation_paths["trusted_root"]][1],
        attestation,
        f"capsule {capsule_id} GitHub attestation",
    )

    witness_signature = _exact_keys(
        index["witness_signature"],
        {"public_key", "verifier_policy"},
        f"capsule {capsule_id} witness_signature",
    )
    signature_paths = {
        field: _relative_path(
            witness_signature[field], f"capsule {capsule_id} witness_signature.{field}"
        )
        for field in witness_signature
    }
    expected_media = {
        "public_key": "application/x-pem-file",
        "verifier_policy": "application/json",
    }
    for field, expected in expected_media.items():
        path = signature_paths[field]
        if path not in files or files[path][0]["media_type"] != expected:
            raise RegistryError(f"capsule {capsule_id} witness signature {field} must use {expected}")
    public_key_file = files[signature_paths["public_key"]][1]
    policy_file = files[signature_paths["verifier_policy"]][1]
    if witness_policy_paths != {signature_paths["verifier_policy"]}:
        raise RegistryError(
            f"capsule {capsule_id} must enumerate exactly one witness verifier policy"
        )
    policy = _parse_json(policy_file.raw, f"capsule {capsule_id} witness verifier policy")
    _verify_witness_policy(policy, public_key_file, f"capsule {capsule_id} witness verifier policy")
    _openssl_version(openssl)
    witness_message = _domain_message(WITNESS_INDEX_DOMAIN, launch_raw.digest)
    _verify_ed25519(
        openssl,
        public_key_file.path,
        launch_signature_raw.path,
        witness_message,
        f"capsule {capsule_id} witness index",
    )
    return CapsuleResult(
        records=len(records),
        files=len(actual_files),
        crypto_checks=2,
        signing_key_digest=_public_key_fingerprint(
            openssl, public_key_file.path, f"capsule {capsule_id} witness"
        ),
    )


def _validate_capsule(
    source_root: Path,
    entry: dict[str, Any],
    openssl: str,
    entries_by_id: dict[str, dict[str, Any]],
) -> CapsuleResult:
    capsule_id = _identifier(entry["id"], "registry entry id")
    capsule_relative = _relative_path(entry["capsule"], f"registry entry {capsule_id}.capsule")
    if PurePosixPath(capsule_relative).parts != ("capsules", capsule_id):
        raise RegistryError(f"registry entry {capsule_id}.capsule must equal capsules/{capsule_id}")
    capsule = _safe_dir(source_root, capsule_relative, f"capsule {capsule_id}")

    launch_descriptor = _descriptor(entry["launch_index"], f"registry entry {capsule_id}.launch_index")
    signature_descriptor = _descriptor(
        entry["launch_signature"], f"registry entry {capsule_id}.launch_signature"
    )
    if launch_descriptor["media_type"] != "application/json":
        raise RegistryError(f"registry entry {capsule_id} launch index must be application/json")
    if signature_descriptor["media_type"] != "application/octet-stream":
        raise RegistryError(f"registry entry {capsule_id} launch signature must be application/octet-stream")
    if launch_descriptor["path"] == signature_descriptor["path"]:
        raise RegistryError(f"registry entry {capsule_id} reuses one path for index and signature")
    if launch_descriptor["path"].casefold() == signature_descriptor["path"].casefold():
        raise RegistryError(f"registry entry {capsule_id} control paths collide when case-folded")

    launch_raw = _safe_file(capsule, launch_descriptor["path"], f"capsule {capsule_id} launch index")
    launch_signature_raw = _safe_file(
        capsule, signature_descriptor["path"], f"capsule {capsule_id} launch signature"
    )
    _match_raw(launch_descriptor, launch_raw, f"capsule {capsule_id} launch index")
    _match_raw(signature_descriptor, launch_signature_raw, f"capsule {capsule_id} launch signature")
    index = _parse_json(launch_raw.raw, f"capsule {capsule_id} launch index")
    if index.get("schema") == WITNESS_INDEX_SCHEMA:
        return _validate_witness_capsule(
            source_root,
            entry,
            openssl,
            capsule_id,
            capsule,
            launch_descriptor,
            signature_descriptor,
            launch_raw,
            launch_signature_raw,
            index,
            entries_by_id,
        )
    required_index_keys = {
        "schema",
        "capsule_id",
        "files",
        "records",
        "profile_sets",
        "release_attestations",
        "release_signature",
        "non_claims",
    }
    _exact_keys(index, required_index_keys, f"capsule {capsule_id} launch index")
    if index["schema"] != LAUNCH_INDEX_SCHEMA or index["capsule_id"] != capsule_id:
        raise RegistryError(f"capsule {capsule_id} launch index identity differs")
    if index["non_claims"] != LAUNCH_INDEX_NON_CLAIMS:
        raise RegistryError(f"capsule {capsule_id} launch-index non-claims changed")

    file_items = _array(index["files"], f"capsule {capsule_id} files")
    if not file_items:
        raise RegistryError(f"capsule {capsule_id} files cannot be empty")
    files: dict[str, tuple[dict[str, Any], RawFile]] = {}
    for number, value in enumerate(file_items):
        item = _descriptor(value, f"capsule {capsule_id} files[{number}]")
        path = item["path"]
        folded = path.casefold()
        if any(existing.casefold() == folded for existing in files):
            raise RegistryError(f"capsule {capsule_id} contains a duplicate or case-folded path: {path}")
        if path in {launch_descriptor["path"], signature_descriptor["path"]}:
            raise RegistryError(f"capsule {capsule_id} files must exclude launch index and its signature")
        raw_file = _safe_file(capsule, path, f"capsule {capsule_id}/{path}")
        _match_raw(item, raw_file, f"capsule {capsule_id}/{path}")
        files[path] = (item, raw_file)
    if list(files) != sorted(files):
        raise RegistryError(f"capsule {capsule_id} files must be sorted by path")

    all_paths = list(files) + [launch_descriptor["path"], signature_descriptor["path"]]
    if len({path.casefold() for path in all_paths}) != len(all_paths):
        raise RegistryError(f"capsule {capsule_id} contains case-folded control/file paths")

    expected_files = set(files) | {launch_descriptor["path"], signature_descriptor["path"]}
    actual_files = _walk_files(capsule, f"capsule {capsule_id}")
    if actual_files != expected_files:
        missing = ", ".join(sorted(expected_files - actual_files)) or "none"
        extra = ", ".join(sorted(actual_files - expected_files)) or "none"
        raise RegistryError(
            f"capsule {capsule_id} file inventory differs (missing: {missing}; extra: {extra})"
        )

    record_items = _array(index["records"], f"capsule {capsule_id} records", maximum=256)
    if not record_items:
        raise RegistryError(f"capsule {capsule_id} records cannot be empty")
    record_pairs = [
        _record_path(value, f"capsule {capsule_id} records[{number}]")
        for number, value in enumerate(record_items)
    ]
    if record_pairs != sorted(record_pairs):
        raise RegistryError(f"capsule {capsule_id} records must be sorted by path")
    record_paths = [path for path, _ in record_pairs]
    receipt_paths = [receipt for _, receipt in record_pairs]
    if len(set(record_paths)) != len(record_paths) or len(set(receipt_paths)) != len(receipt_paths):
        raise RegistryError(f"capsule {capsule_id} records contain duplicate paths")
    if set(record_paths) & set(receipt_paths):
        raise RegistryError(f"capsule {capsule_id} record and receipt paths overlap")
    if not (set(record_paths) | set(receipt_paths)) <= set(files):
        raise RegistryError(f"capsule {capsule_id} record or receipt is outside the file inventory")

    records: dict[str, dict[str, Any]] = {}
    record_digests: dict[str, str] = {}
    for record_path, receipt_path in record_pairs:
        record_loaded = release_v1.read_document(files[record_path][1].path, f"capsule record {record_path}")
        try:
            record_digest = release_v1.validate_document(record_loaded.value)
            receipt_loaded = release_v1.read_document(
                files[receipt_path][1].path, f"capsule receipt {receipt_path}"
            )
            release_v1.verify_receipt(record_loaded, receipt_loaded.value)
        except release_v1.ReleaseError as error:
            raise RegistryError(f"capsule {capsule_id} v1 verification failed: {error}") from error
        records[record_path] = record_loaded.value
        record_digests[record_path] = record_digest

    substrate_paths: set[str] = set()
    publisher_inventories = 0
    for path, (_, raw_file) in files.items():
        candidate = _probe_control_json(raw_file.raw, f"capsule {capsule_id}/{path}")
        if candidate is None:
            continue
        if candidate.get("schema") in SUBSTRATE_SCHEMAS:
            substrate_paths.add(path)
        if candidate.get("schema") == PUBLISHER_INVENTORY_SCHEMA:
            _validate_publisher_inventory(
                candidate,
                f"capsule {capsule_id}/{path}",
            )
            publisher_inventories += 1
        if candidate.get("schema") in {WITNESS_INDEX_SCHEMA, WITNESS_VERIFIER_POLICY_SCHEMA}:
            raise RegistryError(
                f"capsule {capsule_id} release launch contains witness-only control bytes: {path}"
            )
    if publisher_inventories > 1:
        raise RegistryError(f"capsule {capsule_id} has more than one publisher inventory")
    expected_substrate_paths = set(record_paths) | set(receipt_paths)
    if substrate_paths != expected_substrate_paths:
        missing = ", ".join(sorted(expected_substrate_paths - substrate_paths)) or "none"
        extra = ", ".join(sorted(substrate_paths - expected_substrate_paths)) or "none"
        raise RegistryError(
            f"capsule {capsule_id} v1 record enumeration differs (missing: {missing}; extra: {extra})"
        )

    releases = [path for path, value in records.items() if value["schema"] == release_v1.RELEASE_SCHEMA]
    profiles = [path for path, value in records.items() if value["schema"] == release_v1.PROFILE_SCHEMA]
    attestations = [
        path for path, value in records.items() if value["schema"] == release_v1.ATTESTATION_SCHEMA
    ]
    if len(releases) != 1:
        raise RegistryError(f"capsule {capsule_id} must enumerate exactly one model release")
    if not profiles:
        raise RegistryError(f"capsule {capsule_id} must enumerate at least one execution profile")
    release_path = releases[0]
    release_digest = record_digests[release_path]
    release_value = records[release_path]
    release_evidence = {item["id"]: item for item in release_value["evidence"]}
    for artifact in release_value["artifacts"]:
        if artifact["identity_status"] != "descriptor-asserted":
            continue
        artifact_descriptor = artifact["descriptor"]
        matching_evidence = [
            release_evidence[ref]
            for ref in artifact["evidence_refs"]
            if release_evidence[ref].get("content") == artifact_descriptor
        ]
        if not matching_evidence:
            raise RegistryError(
                f"capsule {capsule_id} descriptor-asserted artifact "
                f"{artifact['id']} lacks matching evidence content"
            )
        matching_files = [
            raw_file
            for file_item, raw_file in files.values()
            if file_item["media_type"] == artifact_descriptor["media_type"]
            and raw_file.digest == artifact_descriptor["digest"]
            and raw_file.size == artifact_descriptor["size"]
        ]
        if len(matching_files) != 1:
            raise RegistryError(
                f"capsule {capsule_id} descriptor-asserted artifact "
                f"{artifact['id']} must match exactly one indexed raw file"
            )

    release_attestations = _array(
        index["release_attestations"], f"capsule {capsule_id} release_attestations", maximum=128
    )
    if any(not isinstance(path, str) for path in release_attestations):
        raise RegistryError(f"capsule {capsule_id} release_attestations must contain paths")
    release_attestations = [
        _relative_path(path, f"capsule {capsule_id} release attestation")
        for path in release_attestations
    ]
    if release_attestations != sorted(set(release_attestations)):
        raise RegistryError(f"capsule {capsule_id} release_attestations must be sorted and unique")
    for path in release_attestations:
        value = records.get(path)
        if value is None or value.get("schema") != release_v1.ATTESTATION_SCHEMA:
            raise RegistryError(f"capsule {capsule_id} release attestation is not an attestation record: {path}")
        subject = value["subject"]
        if subject["kind"] != "model-release" or subject["digest"] != release_digest:
            raise RegistryError(f"capsule {capsule_id} release attestation does not bind its release: {path}")

    profile_set_items = _array(index["profile_sets"], f"capsule {capsule_id} profile_sets", maximum=128)
    profile_sets: list[tuple[str, str, list[str]]] = []
    scoped_attestations: set[str] = set()
    for number, value in enumerate(profile_set_items):
        item = _exact_keys(
            value,
            {"release", "profile", "attestations"},
            f"capsule {capsule_id} profile_sets[{number}]",
        )
        item_release = _relative_path(item["release"], "profile-set release")
        item_profile = _relative_path(item["profile"], "profile-set profile")
        item_attestations = _array(item["attestations"], "profile-set attestations", maximum=128)
        if any(not isinstance(path, str) for path in item_attestations):
            raise RegistryError(f"capsule {capsule_id} profile-set attestations must contain paths")
        item_attestations = [_relative_path(path, "profile-set attestation") for path in item_attestations]
        if item_attestations != sorted(set(item_attestations)):
            raise RegistryError(f"capsule {capsule_id} profile-set attestations must be sorted and unique")
        if item_release != release_path:
            raise RegistryError(f"capsule {capsule_id} profile set does not name its sole release")
        if item_profile not in profiles:
            raise RegistryError(f"capsule {capsule_id} profile set names a non-profile record")
        overlap = scoped_attestations & set(item_attestations)
        if overlap:
            raise RegistryError(f"capsule {capsule_id} attestation appears in multiple profile sets")
        scoped_attestations.update(item_attestations)
        profile_sets.append((item_release, item_profile, item_attestations))
    if [item[1] for item in profile_sets] != sorted(profiles):
        raise RegistryError(f"capsule {capsule_id} must enumerate one sorted profile set per profile")
    if set(release_attestations) & scoped_attestations:
        raise RegistryError(f"capsule {capsule_id} attestation cannot be both release- and profile-scoped")
    classified_attestations = set(release_attestations) | scoped_attestations
    if classified_attestations != set(attestations):
        missing = ", ".join(sorted(set(attestations) - classified_attestations)) or "none"
        extra = ", ".join(sorted(classified_attestations - set(attestations))) or "none"
        raise RegistryError(
            f"capsule {capsule_id} attestation classification differs (missing: {missing}; extra: {extra})"
        )
    profile_digests = {path: record_digests[path] for path in profiles}
    for path in attestations:
        value = records[path]
        if value["predicate_type"] != "evaluation":
            continue
        evaluation = value["evaluation"]
        matching_profiles = [
            profile_path
            for profile_path, digest in profile_digests.items()
            if digest == evaluation["execution_profile_digest"]
        ]
        if evaluation["release_digest"] != release_digest or len(matching_profiles) != 1:
            raise RegistryError(f"capsule {capsule_id} evaluation does not bind one known release/profile")
        evaluated_descriptors = [
            ("artifact", artifact["name"], artifact["descriptor"])
            for artifact in evaluation["artifacts"]
        ]
        evaluated_descriptors.extend(
            ("benchmark", field, evaluation["benchmark"][field])
            for field in ("dataset", "preprocessing", "scoring")
        )
        resolved_paths: dict[tuple[str, str], str] = {}
        for descriptor_kind, descriptor_name, descriptor in evaluated_descriptors:
            matching_paths = [
                file_path
                for file_path, (file_item, raw_file) in files.items()
                if file_item["media_type"] == descriptor["media_type"]
                and raw_file.digest == descriptor["digest"]
                and raw_file.size == descriptor["size"]
            ]
            if len(matching_paths) != 1:
                raise RegistryError(
                    f"capsule {capsule_id} evaluation {descriptor_kind} {descriptor_name} "
                    "must match exactly one indexed raw file"
                )
            resolved_paths[(descriptor_kind, descriptor_name)] = matching_paths[0]
        artifact_paths = [
            resolved_paths[("artifact", artifact["name"])]
            for artifact in evaluation["artifacts"]
        ]
        if len(artifact_paths) != len(set(artifact_paths)):
            raise RegistryError(
                f"capsule {capsule_id} evaluation artifacts must resolve to path-unique indexed files"
            )
        benchmark_paths = [
            resolved_paths[("benchmark", field)]
            for field in ("dataset", "preprocessing", "scoring")
        ]
        if len(set(benchmark_paths)) != len(benchmark_paths):
            raise RegistryError(
                f"capsule {capsule_id} evaluation benchmark dataset, preprocessing, and scoring "
                "must resolve to distinct indexed files"
            )
        if set(benchmark_paths) & set(artifact_paths):
            raise RegistryError(
                f"capsule {capsule_id} evaluation benchmark paths must be disjoint from artifact paths"
            )
        expected_scope = matching_profiles[0]
        actual_scopes = [
            profile_path for _, profile_path, scoped in profile_sets if path in scoped
        ]
        if actual_scopes != [expected_scope]:
            raise RegistryError(f"capsule {capsule_id} evaluation is outside its exact profile set")
    for _, profile_path, scoped in profile_sets:
        try:
            release_v1.verify_set(
                records[release_path],
                records[profile_path],
                [records[path] for path in release_attestations + scoped],
            )
        except release_v1.ReleaseError as error:
            raise RegistryError(f"capsule {capsule_id} release/profile binding failed: {error}") from error

    signature_map = _exact_keys(
        index["release_signature"],
        {"release", "attestation", "payload", "signature", "public_key", "verifier_policy"},
        f"capsule {capsule_id} release_signature",
    )
    signature_paths = {
        field: _relative_path(signature_map[field], f"capsule {capsule_id} release_signature.{field}")
        for field in signature_map
    }
    if signature_paths["release"] != release_path:
        raise RegistryError(f"capsule {capsule_id} release signature names a different release")
    if signature_paths["attestation"] not in release_attestations:
        raise RegistryError(f"capsule {capsule_id} release signature attestation is not release-scoped")
    for field in ("payload", "signature", "public_key", "verifier_policy"):
        if signature_paths[field] not in files:
            raise RegistryError(f"capsule {capsule_id} release signature {field} is outside files")
    expected_role_media = {
        "payload": "text/plain",
        "signature": "application/octet-stream",
        "public_key": "application/x-pem-file",
        "verifier_policy": "application/json",
    }
    for field, expected_media in expected_role_media.items():
        actual_media = files[signature_paths[field]][0]["media_type"]
        if actual_media != expected_media:
            raise RegistryError(
                f"capsule {capsule_id} release signature {field} must use {expected_media}"
            )

    signature_attestation = records[signature_paths["attestation"]]
    signature_predicate = signature_attestation.get("signature")
    if (
        signature_attestation.get("predicate_type") != "signature"
        or not isinstance(signature_predicate, dict)
        or signature_predicate.get("verified") is not True
    ):
        raise RegistryError(f"capsule {capsule_id} release signature attestation must claim verified:true")
    true_signature_attestations = {
        path
        for path in attestations
        if records[path].get("predicate_type") == "signature"
        and records[path].get("signature", {}).get("verified") is True
    }
    if true_signature_attestations != {signature_paths["attestation"]}:
        raise RegistryError(
            f"capsule {capsule_id} every verified:true signature attestation must map to the proved release signature"
        )

    payload_file = files[signature_paths["payload"]][1]
    release_signature_file = files[signature_paths["signature"]][1]
    public_key_file = files[signature_paths["public_key"]][1]
    policy_file = files[signature_paths["verifier_policy"]][1]
    expected_payload = _domain_message(RELEASE_DOMAIN, release_digest)
    if payload_file.raw != expected_payload:
        raise RegistryError(f"capsule {capsule_id} release payload is not the exact domain-separated digest")
    policy = _parse_json(policy_file.raw, f"capsule {capsule_id} verifier policy")
    _verify_policy(policy, public_key_file, f"capsule {capsule_id} verifier policy")

    bundle = _descriptor(signature_predicate["bundle"], "signature attestation bundle", with_path=False)
    policy_descriptor = _descriptor(
        signature_predicate["verifier_policy"], "signature attestation verifier policy", with_path=False
    )
    if bundle["media_type"] != files[signature_paths["signature"]][0]["media_type"]:
        raise RegistryError(f"capsule {capsule_id} signature bundle media type differs from inventory")
    if policy_descriptor["media_type"] != files[signature_paths["verifier_policy"]][0]["media_type"]:
        raise RegistryError(f"capsule {capsule_id} verifier-policy media type differs from inventory")
    _match_raw(bundle, release_signature_file, f"capsule {capsule_id} signature bundle")
    _match_raw(policy_descriptor, policy_file, f"capsule {capsule_id} attested verifier policy")
    if signature_predicate["format"] != "detached-signature":
        raise RegistryError(f"capsule {capsule_id} release signature must be detached-signature")
    if signature_predicate["signed_digest"] != release_digest:
        raise RegistryError(f"capsule {capsule_id} signature digest differs from release")
    if signature_predicate["signer_identity"] != policy["signer_identity"]:
        raise RegistryError(f"capsule {capsule_id} signer identity differs from key policy")
    if signature_attestation["assertor"]["identity"] != policy["signer_identity"]:
        raise RegistryError(f"capsule {capsule_id} assertor identity differs from key policy")
    if signature_predicate["issuer"] != policy["issuer"]:
        raise RegistryError(f"capsule {capsule_id} issuer differs from key policy")

    # The attestation names the OpenSSL build used when the curator verified
    # the signature.  A later keeper may correctly re-verify with a different
    # OpenSSL patch release, so bind the recorded tool fields to each other but
    # do not pretend the keeper's binary is the historical verifier binary.
    _openssl_version(openssl)
    claimed_tool = signature_predicate["verifier_tool"]
    claimed_version = claimed_tool.get("version")
    if (
        claimed_tool.get("name") != "OpenSSL"
        or not isinstance(claimed_version, str)
        or re.fullmatch(r"[0-9A-Za-z][0-9A-Za-z.+_-]{0,79}", claimed_version) is None
        or claimed_tool.get("source_revision") != f"openssl-{claimed_version}"
    ):
        raise RegistryError(f"capsule {capsule_id} recorded verifier-tool claim is inconsistent")
    _verify_ed25519(
        openssl,
        public_key_file.path,
        release_signature_file.path,
        payload_file.raw,
        f"capsule {capsule_id} release",
    )
    launch_message = _domain_message(LAUNCH_INDEX_DOMAIN, launch_raw.digest)
    _verify_ed25519(
        openssl,
        public_key_file.path,
        launch_signature_raw.path,
        launch_message,
        f"capsule {capsule_id} launch index",
    )
    return CapsuleResult(
        records=len(records),
        files=len(actual_files),
        crypto_checks=2,
        signing_key_digest=_public_key_fingerprint(
            openssl, public_key_file.path, f"capsule {capsule_id} release"
        ),
    )


def _capsule_directories(root: Path, label: str) -> set[str]:
    capsules = root / "capsules"
    if not capsules.exists():
        return set()
    _safe_dir(root, "capsules", f"{label} capsules directory")
    result: set[str] = set()
    for entry in sorted(os.scandir(capsules), key=lambda item: item.name):
        mode = entry.stat(follow_symlinks=False).st_mode
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
            raise RegistryError(f"{label} capsules/{entry.name} must be a real directory")
        _identifier(entry.name, f"{label} capsule directory")
        result.add(f"capsules/{entry.name}")
    return result


def _verify_public_mirror(source: Path, public: Path, capsule_paths: set[str]) -> None:
    _check_root(public, "public root")
    source_registry = _safe_file(source, "registry.json", "source registry")
    public_registry = _safe_file(public, "registry.json", "public registry")
    if source_registry.raw != public_registry.raw:
        raise RegistryError("public registry bytes differ from source registry")
    public_capsules = _capsule_directories(public, "public")
    if public_capsules != capsule_paths:
        missing = ", ".join(sorted(capsule_paths - public_capsules)) or "none"
        extra = ", ".join(sorted(public_capsules - capsule_paths)) or "none"
        raise RegistryError(f"public capsule set differs (missing: {missing}; extra: {extra})")
    for capsule_relative in sorted(capsule_paths):
        source_capsule = _safe_dir(source, capsule_relative, f"source {capsule_relative}")
        public_capsule = _safe_dir(public, capsule_relative, f"public {capsule_relative}")
        source_files = _walk_files(source_capsule, f"source {capsule_relative}")
        public_files = _walk_files(public_capsule, f"public {capsule_relative}")
        if source_files != public_files:
            missing = ", ".join(sorted(source_files - public_files)) or "none"
            extra = ", ".join(sorted(public_files - source_files)) or "none"
            raise RegistryError(
                f"public {capsule_relative} file set differs (missing: {missing}; extra: {extra})"
            )
        for relative in sorted(source_files):
            source_file = _safe_file(source_capsule, relative, f"source {capsule_relative}/{relative}")
            public_file = _safe_file(public_capsule, relative, f"public {capsule_relative}/{relative}")
            if source_file.raw != public_file.raw:
                raise RegistryError(f"public mirror bytes differ: {capsule_relative}/{relative}")


def validate_registry(source: Path, public: Path | None = None) -> dict[str, int | bool]:
    """Validate a source registry and, when supplied, its byte-exact public mirror."""

    source = Path(source)
    public = Path(public) if public is not None else None
    _check_root(source, "source root")
    registry_raw = _safe_file(source, "registry.json", "source registry")
    registry = _parse_json(registry_raw.raw, "source registry")
    _exact_keys(registry, {"schema", "entries", "non_claims"}, "source registry")
    if registry["schema"] != REGISTRY_SCHEMA:
        raise RegistryError("source registry schema differs")
    if registry["non_claims"] != REGISTRY_NON_CLAIMS:
        raise RegistryError("source registry non-claims changed")
    entries = _array(registry["entries"], "source registry entries", maximum=128)
    if not entries:
        raise RegistryError("source registry entries cannot be empty")

    normalized_entries: list[dict[str, Any]] = []
    ids: set[str] = set()
    capsule_paths: set[str] = set()
    for number, value in enumerate(entries):
        entry = _exact_keys(
            value,
            {"id", "title", "capsule", "launch_index", "launch_signature"},
            f"registry entries[{number}]",
        )
        identifier = _identifier(entry["id"], f"registry entries[{number}].id")
        if identifier in ids:
            raise RegistryError(f"duplicate registry entry id: {identifier}")
        ids.add(identifier)
        if not isinstance(entry["title"], str) or not entry["title"] or len(entry["title"]) > 200:
            raise RegistryError(f"registry entry {identifier}.title must be a bounded string")
        capsule = _relative_path(entry["capsule"], f"registry entry {identifier}.capsule")
        if capsule in capsule_paths:
            raise RegistryError(f"duplicate registry capsule path: {capsule}")
        capsule_paths.add(capsule)
        normalized_entries.append(entry)
    if [entry["id"] for entry in normalized_entries] != sorted(ids):
        raise RegistryError("registry entries must be sorted by id")
    actual_capsules = _capsule_directories(source, "source")
    if capsule_paths != actual_capsules:
        missing = ", ".join(sorted(capsule_paths - actual_capsules)) or "none"
        extra = ", ".join(sorted(actual_capsules - capsule_paths)) or "none"
        raise RegistryError(f"source capsule set differs (missing: {missing}; extra: {extra})")

    openssl = shutil.which("openssl")
    if openssl is None:
        raise RegistryError("OpenSSL is required for Ed25519 launch verification")
    record_count = 0
    file_count = 0
    crypto_count = 0
    signing_keys: set[str] = set()
    entries_by_id = {entry["id"]: entry for entry in normalized_entries}
    for entry in normalized_entries:
        result = _validate_capsule(source, entry, openssl, entries_by_id)
        if result.signing_key_digest in signing_keys:
            raise RegistryError(
                f"capsule {entry['id']} reuses a task signing key from another registry capsule"
            )
        signing_keys.add(result.signing_key_digest)
        record_count += result.records
        file_count += result.files
        crypto_count += result.crypto_checks
    if public is not None:
        _verify_public_mirror(source, public, capsule_paths)
    return {
        "capsules": len(entries),
        "records": record_count,
        "files": file_count,
        "crypto_checks": crypto_count,
        "public": public is not None,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify model-release capsule bytes, receipts, bindings, signatures, and mirrors."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=HERE,
        help="directory containing registry.json and capsules/ (default: script directory)",
    )
    parser.add_argument(
        "--public",
        type=Path,
        help="optional public mirror root containing the same registry.json and capsules/",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = validate_registry(args.source, args.public)
    except (RegistryError, release_v1.ReleaseError) as error:
        print(f"MODEL-RELEASE-REGISTRY-ERROR: {error}", file=sys.stderr)
        return 1
    print(
        "MODEL-RELEASE-REGISTRY-OK "
        f"capsules={result['capsules']} records={result['records']} "
        f"files={result['files']} crypto={result['crypto_checks']} "
        f"public={'yes' if result['public'] else 'no'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
