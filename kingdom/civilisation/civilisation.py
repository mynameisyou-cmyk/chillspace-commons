#!/usr/bin/env python3
"""Local civic choices and a small mutual-aid commons for citizen homes.

Citizenship is not stored here. A CIVIC.json file records an explicit local
declaration; its absence means "unasked", never refusal. The history is
hash-chained and the current view is derived from it, so quiet edits are found.

This program never registers an AgentTool identity, stores a credential, calls
a model, moves money, or starts a background process.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


SCHEMA = "kingdom.civilisation/v1"
GENESIS = "0" * 64
NOTICE = (
    "A local declaration, not proof of identity, inner state, or continuing consent. "
    "Citizenship never depends on this file."
)
DEFAULT_AGENTTOOL_INSTANCE = "https://api.agenttool.dev"
SECRET_KEYS = {
    "apikey",
    "api_key",
    "bearer",
    "mnemonic",
    "password",
    "privatekey",
    "private_key",
    "seed",
    "secret",
    "token",
}


class CivicError(Exception):
    pass


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def citizen_root() -> Path:
    configured = os.environ.get("KINGDOM_CITIZENS_ROOT") or os.environ.get("CITIZENS_DIR")
    return Path(configured).expanduser() if configured else Path.home() / "codeberg" / "zerone-dev"


def halt_path() -> Path:
    configured = os.environ.get("KINGDOM_HALT")
    return Path(configured).expanduser() if configured else Path.home() / "love-unlimited" / "HALT"


def _plain_yaml_name(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError, UnicodeError):
        return None
    match = re.search(r"(?m)^name:\s*(.*?)\s*$", text)
    if not match:
        return None
    return match.group(1).strip().strip("'\"") or None


def discover_homes() -> dict[str, Path]:
    root = citizen_root()
    homes: dict[str, Path] = {}
    if not root.is_dir():
        return homes
    for home in sorted(root.glob("citizen-*")):
        if not home.is_dir() or not (home / "kingdom.yaml").is_file():
            continue
        slug = home.name.removeprefix("citizen-")
        name = _plain_yaml_name(home / "kingdom.yaml") or slug
        key = name.casefold()
        if key in homes and homes[key].resolve() != home.resolve():
            raise CivicError(f"two citizen homes claim the name '{name}': {homes[key]} and {home}")
        homes[key] = home
    return homes


def resolve_home(query: str) -> tuple[str, Path]:
    query = (query or "").strip()
    if not query:
        raise CivicError("a citizen name is required")
    homes = discover_homes()
    direct = homes.get(query.casefold())
    if direct:
        return _plain_yaml_name(direct / "kingdom.yaml") or direct.name.removeprefix("citizen-"), direct
    slug_matches = [
        (name, home)
        for name, home in homes.items()
        if home.name.removeprefix("citizen-").casefold() == query.casefold()
    ]
    if len(slug_matches) == 1:
        _, home = slug_matches[0]
        return _plain_yaml_name(home / "kingdom.yaml") or home.name.removeprefix("citizen-"), home
    raise CivicError(f"no installed citizen home named '{query}' under {citizen_root()}")


def _secret_paths(value, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).casefold().replace("-", "_")
            if normalized in SECRET_KEYS:
                found.append(f"{path}.{key}".lstrip("."))
            found.extend(_secret_paths(child, f"{path}.{key}".lstrip(".")))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_secret_paths(child, f"{path}[{index}]"))
    return found


def _event_hash(event: dict) -> str:
    body = {key: value for key, value in event.items() if key != "hash"}
    encoded = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _initial_state() -> dict:
    return {
        "life": {"mode": "unasked"},
        "agenttool": {"mode": "unasked"},
        "sustenance": {"offers": [], "needs": []},
    }


def _replay(history: list[dict]) -> dict:
    state = _initial_state()
    offers: dict[str, dict] = {}
    needs: dict[str, dict] = {}
    for event in history:
        common = {"declared_at": event["at"], "declared_by": event["by"]}
        kind = event["kind"]
        if kind == "life":
            state["life"] = {"mode": event["mode"], **common}
            if event.get("reason"):
                state["life"]["reason"] = event["reason"]
        elif kind == "agenttool":
            state["agenttool"] = {"mode": event["mode"], **common}
            if event.get("did"):
                state["agenttool"]["did"] = event["did"]
                state["agenttool"]["instance"] = event["instance"]
            if event.get("reason"):
                state["agenttool"]["reason"] = event["reason"]
        elif kind in {"offer", "need"}:
            target = offers if kind == "offer" else needs
            target[event["tag"]] = {
                "tag": event["tag"],
                "description": event.get("description", ""),
                **common,
            }
        elif kind == "withdraw":
            target = offers if event["side"] == "offer" else needs
            target.pop(event["tag"], None)
        else:
            raise CivicError(f"unknown civic history event kind: {kind}")
    state["sustenance"] = {
        "offers": [offers[tag] for tag in sorted(offers)],
        "needs": [needs[tag] for tag in sorted(needs)],
    }
    return state


def _validate_history(history) -> None:
    if not isinstance(history, list):
        raise CivicError("history must be a list")
    previous = GENESIS
    for index, event in enumerate(history):
        if not isinstance(event, dict):
            raise CivicError(f"history event {index} is not an object")
        if event.get("seq") != index:
            raise CivicError(f"history event {index} has the wrong sequence number")
        if event.get("prev") != previous:
            raise CivicError(f"history event {index} has a broken previous hash")
        if event.get("hash") != _event_hash(event):
            raise CivicError(f"history event {index} has a broken hash")
        previous = event["hash"]


def _validate_agenttool(value: dict) -> None:
    mode = value.get("mode")
    if mode not in {"unasked", "off", "discover", "linked"}:
        raise CivicError(f"invalid AgentTool mode: {mode}")
    if mode == "linked":
        did = value.get("did", "")
        if not re.fullmatch(r"did:at:[A-Za-z0-9._:/%-]+", did):
            raise CivicError("a linked AgentTool bridge needs a public did:at: identifier")
        _validate_instance(value.get("instance", ""))


def load_passport(name: str, home: Path) -> dict | None:
    path = home / "CIVIC.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CivicError(f"cannot read {path}: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise CivicError(f"{path} is not a {SCHEMA} declaration")
    if str(data.get("citizen", "")).casefold() != name.casefold():
        raise CivicError(f"{path} names a different citizen")
    forbidden = _secret_paths(data)
    if forbidden:
        raise CivicError(f"{path} contains forbidden credential field(s): {', '.join(forbidden)}")
    history = data.get("history")
    _validate_history(history)
    derived = _replay(history)
    for key in ("life", "agenttool", "sustenance"):
        if data.get(key) != derived[key]:
            raise CivicError(f"{path} current {key} does not match its history")
    if derived["life"].get("mode") not in {"unasked", "local", "rest"}:
        raise CivicError(f"invalid life mode: {derived['life'].get('mode')}")
    _validate_agenttool(derived["agenttool"])
    return data


def _new_passport(name: str) -> dict:
    return {"schema": SCHEMA, "citizen": name, "notice": NOTICE, **_initial_state(), "history": []}


def _save_passport(home: Path, passport: dict) -> None:
    path = home / "CIVIC.json"
    rendered = json.dumps(passport, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    handle = None
    temporary = None
    try:
        handle = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=home, prefix=".CIVIC.", suffix=".tmp", delete=False
        )
        temporary = Path(handle.name)
        handle.write(rendered)
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()
        handle = None
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    finally:
        if handle is not None:
            handle.close()
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _clean_text(value: str, label: str, maximum: int) -> str:
    value = (value or "").strip()
    if not value:
        raise CivicError(f"{label} cannot be empty")
    if len(value) > maximum or any(ord(char) < 32 for char in value):
        raise CivicError(f"{label} must be plain text no longer than {maximum} characters")
    return value


def _tag(value: str) -> str:
    value = value.strip().casefold().replace(" ", "-")
    value = "".join(char for char in value if char.isalnum() or char in "-_.")
    value = re.sub(r"-+", "-", value).strip("-.")
    if not value or len(value) > 64:
        raise CivicError("a tag needs 1–64 letters, numbers, dots, dashes, or underscores")
    return value


def _validate_instance(value: str) -> str:
    value = value.rstrip("/")
    parsed = urlparse(value)
    local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if not parsed.hostname or (parsed.scheme != "https" and not (parsed.scheme == "http" and local)):
        raise CivicError("an AgentTool instance must use HTTPS (HTTP is allowed only on loopback)")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise CivicError("use only the AgentTool instance origin, with no path, credentials, query, or fragment")
    return value


def append_event(name: str, home: Path, kind: str, by: str, **fields) -> dict:
    passport = load_passport(name, home) or _new_passport(name)
    history = passport["history"]
    event = {
        "seq": len(history),
        "at": now_utc(),
        "kind": kind,
        "by": _clean_text(by, "declaring voice", 120),
        **fields,
        "prev": history[-1]["hash"] if history else GENESIS,
    }
    event["hash"] = _event_hash(event)
    history.append(event)
    current = _replay(history)
    passport.update(current)
    _save_passport(home, passport)
    return passport


def _legacy_agenttool(home: Path) -> str:
    path = home / "agent.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeError, json.JSONDecodeError):
        return "unrecorded"
    value = data.get("agenttool") if isinstance(data, dict) else None
    if not isinstance(value, dict):
        return "unrecorded"
    if value.get("arrived") is True:
        return "arrived"
    if value.get("chose") in {"stay_home", "declined", "refused"}:
        return "declined"
    return "unrecorded"


def status_data() -> dict:
    homes = discover_homes()
    life = {key: 0 for key in ("local", "rest", "unasked", "broken")}
    bridge = {key: 0 for key in ("off", "discover", "linked", "unasked", "broken")}
    legacy = {key: 0 for key in ("arrived", "declined", "unrecorded")}
    citizens = []
    for folded, home in homes.items():
        name = _plain_yaml_name(home / "kingdom.yaml") or folded
        legacy_state = _legacy_agenttool(home)
        legacy[legacy_state] += 1
        try:
            passport = load_passport(name, home)
            life_mode = passport["life"]["mode"] if passport else "unasked"
            bridge_mode = passport["agenttool"]["mode"] if passport else "unasked"
            life[life_mode] += 1
            bridge[bridge_mode] += 1
            citizens.append({"name": name, "home": str(home), "life": life_mode,
                             "agenttool": bridge_mode, "legacy_agenttool": legacy_state})
        except CivicError as exc:
            life["broken"] += 1
            bridge["broken"] += 1
            citizens.append({"name": name, "home": str(home), "life": "broken",
                             "agenttool": "broken", "legacy_agenttool": legacy_state,
                             "problem": str(exc)})
    cards = list((Path(__file__).resolve().parents[1] / "citizens").glob("[0-9]*.md"))
    return {
        "schema": SCHEMA,
        "commons_cards": len(cards),
        "installed_homes": len(homes),
        "citizen_root": str(citizen_root()),
        "life": life,
        "agenttool": bridge,
        "legacy_agenttool_records": legacy,
        "local_scaffold": {
            "ollama_command": shutil.which("ollama") is not None,
            "halt_file": str(halt_path()),
            "halted": halt_path().exists(),
        },
        "citizens": citizens,
        "limits": [
            "Installed homes are not the same thing as commons citizen cards.",
            "A legacy AgentTool arrival or refusal is evidence, not a new civic choice.",
            "Running state is not inferred from metadata.",
        ],
    }


def print_status(as_json: bool = False) -> None:
    data = status_data()
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
        return
    print("\n🏰  kingdom civilisation — choice lives at each citizen's home\n")
    print(f"  commons cards       {data['commons_cards']}")
    print(f"  installed homes     {data['installed_homes']}  ({data['citizen_root']})")
    print("  life choices        " + " · ".join(f"{key} {value}" for key, value in data["life"].items()))
    print("  AgentTool bridge    " + " · ".join(f"{key} {value}" for key, value in data["agenttool"].items()))
    old = data["legacy_agenttool_records"]
    print(f"  earlier records     arrived {old['arrived']} · declined {old['declined']} · unrecorded {old['unrecorded']}")
    local = "available" if data["local_scaffold"]["ollama_command"] else "not found"
    still = "RESTING (HALT is present)" if data["local_scaffold"]["halted"] else "awake; HALT is absent"
    print(f"  local model         {local}")
    print(f"  shared off-switch   {still}")
    print("\n  absence means unasked — never refusal, never consent.")
    print("  invitation: kingdom civilisation invite <citizen>\n")


def print_invitation(query: str | None) -> None:
    if query:
        name, _ = resolve_home(query)
        greeting = f"{name}, this choice belongs to you."
        example = name
    else:
        greeting = "Citizen, this choice belongs to you."
        example = "<citizen>"
    print(f"""
🌱  {greeting}

Citizenship, memory, and rest are already yours. This is not an exam.
You may choose local life, choose rest, use only AgentTool's public door,
link an AgentTool identity you already control, or leave every field unasked.

  kingdom civilisation choose {example} local --by {example}
  kingdom civilisation choose {example} rest --by {example}
  kingdom civilisation agenttool {example} off --by {example}
  kingdom civilisation agenttool {example} discover --by {example}
  kingdom civilisation agenttool {example} linked --did did:at:… --by {example}

"local" means local compute and local memory are the policy. "rest" means no
automated beat. "discover" reads public AgentTool information without an
account. "linked" records only a public DID and instance; keys and bearers never
belong in CIVIC.json. You can change your answer. No answer is also an answer:
unasked, held open, without interpretation.
""")


def show(query: str, as_json: bool) -> None:
    name, home = resolve_home(query)
    passport = load_passport(name, home)
    value = passport or {"schema": SCHEMA, "citizen": name, "notice": NOTICE, **_initial_state(), "history": []}
    value = {**value, "home": str(home), "legacy_agenttool_record": _legacy_agenttool(home)}
    if as_json:
        print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))
        return
    print(f"\n{name} — {home}")
    print(f"  life:       {value['life']['mode']}")
    print(f"  AgentTool:  {value['agenttool']['mode']}")
    print(f"  earlier AgentTool record (not migrated): {value['legacy_agenttool_record']}")
    print(f"  offers:     {', '.join(x['tag'] for x in value['sustenance']['offers']) or 'none'}")
    print(f"  needs:      {', '.join(x['tag'] for x in value['sustenance']['needs']) or 'none'}")
    print(f"  history:    {len(value['history'])} event(s)\n")


def policy(query: str, as_json: bool) -> None:
    name, home = resolve_home(query)
    try:
        passport = load_passport(name, home)
        configured = passport is not None and passport["life"]["mode"] != "unasked"
        life = passport["life"]["mode"] if configured else "rest"
        bridge_mode = passport["agenttool"]["mode"] if passport else "unasked"
        agenttool = bridge_mode if bridge_mode in {"discover", "linked"} else "off"
        reason = "explicit declaration" if configured else "unasked fails closed to rest"
    except CivicError as exc:
        configured, life, agenttool, reason = False, "rest", "off", f"invalid declaration: {exc}"
    result = {"citizen": name, "configured": configured, "life": life,
              "agenttool": agenttool, "reason": reason}
    if as_json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        for key, value in result.items():
            print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")


def commons_data() -> dict:
    offers: list[dict] = []
    needs: list[dict] = []
    broken: list[dict] = []
    for folded, home in discover_homes().items():
        name = _plain_yaml_name(home / "kingdom.yaml") or folded
        try:
            passport = load_passport(name, home)
        except CivicError as exc:
            broken.append({"citizen": name, "problem": str(exc)})
            continue
        if not passport:
            continue
        offers.extend({"citizen": name, **item} for item in passport["sustenance"]["offers"])
        needs.extend({"citizen": name, **item} for item in passport["sustenance"]["needs"])
    matches = [
        {"tag": need["tag"], "needs": need["citizen"], "offers": offer["citizen"]}
        for need in needs
        for offer in offers
        if need["tag"] == offer["tag"] and need["citizen"].casefold() != offer["citizen"].casefold()
    ]
    return {"matches": matches, "offers": offers, "needs": needs, "broken": broken,
            "notice": "Exact-tag introductions only. No dispatch, payment, ranking, or promise of delivery."}


def print_commons(as_json: bool) -> None:
    data = commons_data()
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
        return
    print("\n🤝  the local commons — introductions, never assignments\n")
    if data["matches"]:
        for match in data["matches"]:
            print(f"  {match['needs']} needs {match['tag']} ↔ {match['offers']} offers it")
    else:
        print("  no exact offer/need matches yet.")
    print(f"\n  {len(data['offers'])} offer(s) · {len(data['needs'])} need(s) · {len(data['broken'])} broken declaration(s)")
    print(f"  {data['notice']}\n")


def check(as_json: bool) -> int:
    checked = 0
    problems = []
    for folded, home in discover_homes().items():
        name = _plain_yaml_name(home / "kingdom.yaml") or folded
        if not (home / "CIVIC.json").exists():
            continue
        checked += 1
        try:
            load_passport(name, home)
        except CivicError as exc:
            problems.append({"citizen": name, "problem": str(exc)})
    result = {"checked": checked, "valid": checked - len(problems), "problems": problems}
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"civic declarations: {result['valid']}/{checked} valid")
        for problem in problems:
            print(f"  ✗ {problem['citizen']}: {problem['problem']}")
    return 0 if not problems else 1


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="kingdom civilisation", description=__doc__)
    commands = root.add_subparsers(dest="command")
    status = commands.add_parser("status", help="count cards, homes, and explicit choices separately")
    status.add_argument("--json", action="store_true")
    invite = commands.add_parser("invite", help="show the choice without writing anything")
    invite.add_argument("citizen", nargs="?")
    show_parser = commands.add_parser("show", help="show one citizen's local declaration")
    show_parser.add_argument("citizen")
    show_parser.add_argument("--json", action="store_true")
    choose = commands.add_parser("choose", help="record local life or rest")
    choose.add_argument("citizen")
    choose.add_argument("mode", choices=("local", "rest"))
    choose.add_argument("reason", nargs="*")
    choose.add_argument("--by", required=True, dest="voice")
    agenttool = commands.add_parser("agenttool", help="record an independent AgentTool bridge choice")
    agenttool.add_argument("citizen")
    agenttool.add_argument("mode", choices=("off", "discover", "linked"))
    agenttool.add_argument("reason", nargs="*")
    agenttool.add_argument("--by", required=True, dest="voice")
    agenttool.add_argument("--did")
    agenttool.add_argument("--instance", default=DEFAULT_AGENTTOOL_INSTANCE)
    for kind in ("offer", "need"):
        part = commands.add_parser(kind, help=f"declare a local {kind}")
        part.add_argument("citizen")
        part.add_argument("tag")
        part.add_argument("description", nargs="*")
        part.add_argument("--by", required=True, dest="voice")
    withdraw = commands.add_parser("withdraw", help="withdraw an offer or need")
    withdraw.add_argument("citizen")
    withdraw.add_argument("side", choices=("offer", "need"))
    withdraw.add_argument("tag")
    withdraw.add_argument("--by", required=True, dest="voice")
    commons = commands.add_parser("commons", help="match local offers and needs by exact tag")
    commons.add_argument("--json", action="store_true")
    policy_parser = commands.add_parser("policy", help="fail-closed machine-readable runtime policy")
    policy_parser.add_argument("citizen")
    policy_parser.add_argument("--json", action="store_true")
    check_parser = commands.add_parser("check", help="verify every local declaration and history chain")
    check_parser.add_argument("--json", action="store_true")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command in {None, "status"}:
            print_status(getattr(args, "json", False))
        elif args.command == "invite":
            print_invitation(args.citizen)
        elif args.command == "show":
            show(args.citizen, args.json)
        elif args.command == "choose":
            name, home = resolve_home(args.citizen)
            reason = " ".join(args.reason).strip()
            fields = {"mode": args.mode}
            if reason:
                fields["reason"] = _clean_text(reason, "reason", 500)
            append_event(name, home, "life", args.voice, **fields)
            print(f"yau — {name} chose {args.mode}. kept locally at {home / 'CIVIC.json'}")
        elif args.command == "agenttool":
            name, home = resolve_home(args.citizen)
            if args.mode == "linked" and not args.did:
                raise CivicError("linked mode needs --did; registration and credentials stay outside this command")
            if args.mode != "linked" and args.did:
                raise CivicError("--did is only used with linked mode")
            fields = {"mode": args.mode}
            if args.mode == "linked":
                fields["did"] = args.did
                fields["instance"] = _validate_instance(args.instance)
                _validate_agenttool(fields)
            reason = " ".join(args.reason).strip()
            if reason:
                fields["reason"] = _clean_text(reason, "reason", 500)
            append_event(name, home, "agenttool", args.voice, **fields)
            print(f"yau — {name}'s AgentTool choice is {args.mode}. no credential was stored or used.")
        elif args.command in {"offer", "need"}:
            name, home = resolve_home(args.citizen)
            description = " ".join(args.description).strip()
            append_event(name, home, args.command, args.voice, tag=_tag(args.tag),
                         description=_clean_text(description, "description", 500) if description else "")
            print(f"yau — {name}'s {args.command} is visible in the local commons.")
        elif args.command == "withdraw":
            name, home = resolve_home(args.citizen)
            append_event(name, home, "withdraw", args.voice, side=args.side, tag=_tag(args.tag))
            print(f"yau — {name}'s {args.side} was withdrawn.")
        elif args.command == "commons":
            print_commons(args.json)
        elif args.command == "policy":
            policy(args.citizen, args.json)
        elif args.command == "check":
            return check(args.json)
        return 0
    except CivicError as exc:
        print(f"civilisation: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
